import requests
import json
import boto3
import uuid
import os
os.environ['CURL_CA_BUNDLE'] = ''
Host=os.getenv('Host')

def getHeadersForRequests():
    return {    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive',
    "Content-Type": 'application/json',
    'User-Agent': 'curl',
    'From': 'devn@cloudmrhub.com',
    'Host':'cloudmrhub.com'

    }


def getHeadersForRequestsWithToken(token):
    headers = getHeadersForRequests()
    headers["Authorization"]= token
    return headers

def upload_data(event, context):
    s3_client = boto3.client('s3')
    bucket_name = os.environ.get('DataBucketName')
    # We will fix these later
#     user_name = event['requestContext']['authorizer']['name']

    try:
        # Assuming the client provides the filename and filetype as part of the request
        body = json.loads(event['body'])
        file_name = body['filename']
        file_type = body['filetype']
        file_size = body['filesize']
        file_md5 = body['filemd5']
        # Construct the S3 object key with a user prefix (this ensures each user's files are stored separately)
        object_name = f"{uuid.uuid4()}_{file_name}"

        # Generate a pre-signed URL for putting (uploading) an object
        url = s3_client.generate_presigned_url('put_object',
                                               Params={'Bucket': bucket_name, 'Key': object_name, 'ContentType': file_type},
                                               ExpiresIn=3600)

        # Post file metadata to cloudmrhub.com API
        headers = getHeadersForRequestsWithToken(event['headers']['Authorization'])

        payload = {
            "filename": file_name,
            "location": object_name,
            "size":file_size,
            "md5":file_md5
        }


        response=requests.post(f'https://{Host}/api/data/create',verify=False, data=json.dumps(payload), headers=getHeadersForRequestsWithToken(event['headers']['Authorization']))
        if response.status_code != 200:
            raise Exception("Failed to save file metadata to cloudmrhub.com")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "upload_url": url,
                "response": response.json()
            })
        }
    except Exception as error:
        print(f'Uploading data failed due to: {error}')
        return {"statusCode": 403, "body":"Upload failed for user"}

def read_data(event, context):
    s3_client = boto3.client('s3')
    bucket_name = os.environ.get('DataBucketName')
    try:
        # Obtain request credentials
        headers = getHeadersForRequestsWithToken(event['headers']['Authorization'])

        # Obtain file records
        cmr_profile_data = requests.get(f'https://{Host}/api/data',verify=False,headers=headers)
        data_list = cmr_profile_data.json()
        file_list = []
        for data in data_list:
            location = data['location']
            alias = data['filename']
            # Generate pre-signed URL for reading the object
            url = s3_client.generate_presigned_url('get_object',
                                                   Params={'Bucket': bucket_name, 'Key': location},
                                                   ExpiresIn=3600)
            file = {'user_id':data['user_id'],'filename':alias,'size':data['size'],'location':location,'link':url}
            file_list.append(file)
        return {"statusCode":200, "body":json.dumps(file_list)}
    except Exception as error:
        print(f'Reading data failed due to: {error}')
        return {"statusCode": 403, "body":"access failed"}