import json
import os
import boto3
from botocore.exceptions import ClientError
import SimpleITK as sitk
from cm import writeResultsAsCmJSONOutput
from zipfile import ZipFile

RESULTS_BUCKET_NAME = os.environ.get('ResultsBucketName')

# Reads a local file and returns it given the path.
def read_file(file_path):
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(e)
        raise e

# Downloads a file from S3 given a bucket, file key and s3 boto client.
# Returns local path to that file
def download_from_s3(bucket, file, s3=None):
    try: 
        print("Downloading File: " + file + ", Bucket:" + bucket)
        destination_path = '/tmp/' + os.path.basename(file)
        s3.download_file(bucket, file, destination_path)
        print("Completed Downloading File: " + file + ", Bucket:" + bucket)
        return destination_path
    except ClientError as e:
        print(e)
        if e.response['Error']['Code'] == '404':
            # Object doesn't exist, return None or handle as needed
            print("File not found: " + file)
            return None
        else:
            # Other S3-related error occurred, re-raise the exception
            print("Error downloading file: " + file)
            raise e

def handler(event, context):

    try:
        s3_client = boto3.client('s3')

        # Get pipelineId from queryStringParameters
        if event["queryStringParameters"] is None:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": 'queryStringParamter `pipelineId` required. Eg /results?pipelineId=<id>'
                })
            }

        pipelineId = event["queryStringParameters"]["pipelineId"]

        if pipelineId is None:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": 'queryStringParamter `pipelineId` required. Eg /results?pipelineId=<id>'
                })
            }

        # Check for unzipped results in bucket::unzipped/<pipeline>.json
        found_unzipped_result = download_from_s3(RESULTS_BUCKET_NAME, 'unzipped/' + pipelineId + '.json', s3_client)
        # If unzipped result is found, then return a signed url for it
        if found_unzipped_result is not None:
            print("Previously generated result file found: unzipped/" + pipelineId + '.json')
            presigned_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': RESULTS_BUCKET_NAME, 'Key': 'unzipped/' + pipelineId + '.json'},
                ExpiresIn=600
            )
            return {
                "statusCode": 200,
                "body": json.dumps({
                    "message": "Previously generated result file found: unzipped/" + pipelineId + '.json',
                    "url": presigned_url
                }),
            }


        # If unzipped results are not found, generate <pipeline>.json and return
        file_name = 'zipped/' + pipelineId + '.zip'
        result_file_path = download_from_s3(RESULTS_BUCKET_NAME, file_name, s3_client)
        if result_file_path is None:
            return {
                "statusCode": 404,
                "body": json.dumps({
                    "error": "Result for pipeline not found",
                }),
            }

        with ZipFile(result_file_path, 'r') as zip:
            zip.printdir() # print content of zip file
            zip.extractall('/tmp/' + pipelineId) # extract the files
            
            info_json = read_file('/tmp/' + pipelineId + '/info.json')
            print(info_json)
            zip.close()

        reader = sitk.ImageFileReader()
        reader.SetImageIO("NiftiImageIO")

        images = []
        for d in info_json["data"]:
            path_to_file = os.path.join('/tmp', pipelineId, d["filename"])
            image = {}
            image['type'] = 'imaginable2D'
            image['name'] = d['name']
            reader.SetFileName(path_to_file)
            image['imaginable'] = reader.Execute()
            image['output'] = d['name']
            images.append(image)

        json_output = writeResultsAsCmJSONOutput(images, None)
        print(json_output)

        unzipped_file_key = 'unzipped/' + pipelineId + '.json'
        # Upload results to the results unzipped bucket
        s3_client.put_object(
            Bucket=RESULTS_BUCKET_NAME,
            Key=unzipped_file_key,
            Body=json.dumps(json_output)
        )
        print('Uploaded results to: ' + RESULTS_BUCKET_NAME + '::' + unzipped_file_key)

        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': RESULTS_BUCKET_NAME, 'Key': unzipped_file_key},
            ExpiresIn=600
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Result generated successfully.",
                "url": presigned_url
            }),
        }

    except Exception as e:
        print(e)
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": str(e)
            }),
        }
