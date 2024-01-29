import json
import requests
import boto3
import os
import os

os.environ['CURL_CA_BUNDLE'] = ''
import zipfile


def lambda_handler(event, context):
    # Get the bucket name and file key
    location = json.loads(event["body"])
    # {
#                          "id": 0,
#                          "link": "unknown",
#                          "createdAt": "2023-06-03T06:57:33.000000Z",
#                          "updatedAt": "2023-06-03T06:57:33.000000Z",
#                          "status": "unavailable",
#                          "database": "s3",
#                          "fileName": "Miss Camylle Grady_results",
#                          "location": `${JSON.stringify({bucket: bucket, key:keyInBucket})}`
#                      }

    file_key = location['Key']
    bucket_name = location['Bucket']
    # save zip  file to local
    fj = "/tmp/a.zip"
    s3 = boto3.resource("s3")
    s3.Bucket(bucket_name).download_file(file_key, fj)
    archive = zipfile.ZipFile(fj, 'r')
    info = archive.read('info.json')
    info = json.loads(info)
#     {
#                 "filename": "data/NC.nii.gz",
#                 "id": 0,
#                 "dim": 2,
#                 "name": "Noise Covariance",
#                 "type": "output"
#             },
#             {
#                 "filename": "data/snr.nii.gz",
#                 "id": 1,
#                 "dim": 3,
#                 "name": "SNR",
#                 "type": "output"
#             }
    ledge = info['data']
    s3_client = boto3.client('s3')
    for data in ledge:
        file = archive.read(data['filename'])
        target_key = f"unzipped/{file_key}_{data['filename']}"
        s3_client.put_object(Bucket=bucket_name, Key=target_key, Body=file)
        # Generate a pre-signed URL for the uploaded .nii file
        url = s3_client.generate_presigned_url('get_object',Params={'Bucket': bucket_name, 'Key': target_key},
            ExpiresIn=3600)  # URL valid for 1 hour
        data['link'] = url

    return {"statusCode": 200,
            "headers": {
                'Access-Control-Allow-Origin': '*'
            },
            "body":json.dumps(info)
            }
