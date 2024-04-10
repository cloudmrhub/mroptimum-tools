import requests
import json
import boto3
import uuid
import os
os.environ['CURL_CA_BUNDLE'] = ''
Host=os.getenv('Host')
deleteDataAPI=os.getenv('deleteDataAPI')
updateDataAPI=os.getenv('updateDataAPI')

def fixCORS(response):
    response['headers'] = {}
    response['headers']['Access-Control-Allow-Origin']='*' # This is required to allow CORS
    response['headers']['Access-Control-Allow-Headers']='*' # This is required to allow CORS
    response['headers']['Access-Control-Allow-Methods']='*' # This is required to allow CORS
    return response

def createResponse(body):
    return json.dumps(body)

def getHeadersForRequests():
    return {    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive',
    "Content-Type": 'application/json',
    'User-Agent': 'curl',
    'From': 'devn@cloudmrhub.com',
    'Host':Host

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
        # Generate a pre-signed URL for putting (uploading) an object
        url = s3_client.generate_presigned_url(ClientMethod='put_object',
                                              Params={'Bucket': bucket_name, 'Key': object_name, 'ACL': 'public-read','ContentType': file_type},ExpiresIn=3600)

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
            "headers": {
                'Access-Control-Allow-Origin': '*'
            },
            "body": json.dumps({
                "upload_url": url,
                "response": response.json()
            })
        }
    except Exception as error:
        print(f'Uploading data failed due to: {error}')
        return {"statusCode": 403,
            "headers": {
                'Access-Control-Allow-Origin': '*'
            }, "body":"Upload failed for user"}


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
            if(data['location'][0]=='{'):
                location = json.loads(data['location'])
                # Generate pre-signed URL for reading the object
                url = s3_client.generate_presigned_url('get_object',
                                                       Params={'Bucket': location['Bucket'], 'Key': location['Key'], 'ResponseContentDisposition':
                                                           f"attachment; filename ={data['filename']}"},
                                                       ExpiresIn=3600)
                data['link'] = url
            data['database'] = 's3'
            # {'user_id':data['user_id'],'filename':alias,'size':data['size'],'location':location,'link':url}
            file_list.append(data)
        return {"statusCode":200,
            "headers": {
                'Access-Control-Allow-Origin': '*'
            }, "body":json.dumps(file_list)}
    except Exception as error:
        print(f'Reading data failed due to: {error}')
        return {"statusCode": 403,
            "headers": {
                'Access-Control-Allow-Origin': '*',
            }, "body":"access failed"}


def deleteData(event, context):
    # get data_id from aws api gateway event get
    print("event")
    print(event['queryStringParameters'])
    s3_client = boto3.client('s3')

    file_id = event['queryStringParameters']['fileid']
    if file_id is None:
        # return "pipeline_id is required" in a json format with anerror code status
        return fixCORS({
            'statusCode':405 ,
            'body': json.dumps('data id is required')
        })
    # Get the headers from the event object.
    headers = event['headers']
    # Get the authorization header.
    print(headers)
    authorization_header = headers['Authorization']
    # Get the application and pipeline names.
    url=f'{deleteDataAPI}/{file_id}'
    print(url)
    r2=requests.get(url,verify=False,headers=getHeadersForRequestsWithToken(authorization_header))
    # if the response is not 200, return the error message
    try:
        OUT=json.dumps(r2.json())
    except:
        OUT=r2.text
    return fixCORS({
        'statusCode':r2.status_code ,
        'body': OUT
    })

def updateData(event, context):
    # get data_id from aws api gateway event get



    body = json.loads(event['body'])
    file_id = body['fileid']
    file_name = body['filename']

    if file_id is None:
        # return "pipeline_id is required" in a json format with anerror code status
        return fixCORS({
            'statusCode':405 ,
            'body': json.dumps('data id is required')
        })
    # Get the headers from the event object.
    headers = event['headers']
    # Get the authorization header.
    print(headers)
    authorization_header = headers['Authorization']
    # Get the application and pipeline names.
    url=f'{updateDataAPI}/{file_id}'
    print(url)
    r2=requests.post(url,verify=False, data=json.dumps({"filename":file_name}), headers=getHeadersForRequestsWithToken(event['headers']['Authorization']))
    print(r2)
    # if the response is not 200, return the error message
    try:
        OUT=json.dumps(r2.json())
    except:
        OUT=r2.text
    return fixCORS({
        'statusCode':r2.status_code ,
        'body': OUT
    })
    