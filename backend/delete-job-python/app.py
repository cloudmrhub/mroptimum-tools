import json
import requests
import boto3
import os
import os
os.environ['CURL_CA_BUNDLE'] = ''
def fixCORS(response):
    response['headers'] = {}
    response['headers']['Access-Control-Allow-Origin']='*' # This is required to allow CORS
    response['headers']['Access-Control-Allow-Headers']='*' # This is required to allow CORS
    response['headers']['Access-Control-Allow-Methods']='*' # This is required to allow CORS
    return response

def getHeadersForRequests():
    return {"Content-Type": "application/json","User-Agent": 'My User Agent 1.0','From': 'theweblogin@iam.com'}

def getHeadersForRequestsWithToken(token):
    headers = getHeadersForRequests()
    headers["Authorization"]= token
    return headers
    
def lambda_handler(event, context):
    
    # Get the headers from the event object.
    headers = event['headers']
    # Get the authorization header.
    authorization_header = headers['Authorization']
    # Get the application and pipeline names.
    
    pipelineAPI = os.environ.get("PipelineDeleteAPI")
    try:
        body = json.loads(event['body'])
        ID=body['id']
    except:
        ID = event['queryStringParameters'].get('id')
    if not isinstance(ID,str):
        ID=str(ID)
    pipelineAPI+="/"+ID
    
    r2=requests.post(pipelineAPI, headers=getHeadersForRequestsWithToken(authorization_header))
    try:
        R=r2.json()
        print(R)
    except:
        print(r2.text)
        
    if r2.status_code==404:
        return fixCORS({
        'statusCode': 404,
        'body': json.dumps({
            'message': 'Job not found'
        }),
                'headers': {
                'Access-Control-Allow-Origin': '*'
        }
    })
        
    if r2.status_code!=200:
        return fixCORS({    
        'statusCode': 500,
        'body': json.dumps({
            'message': 'Failed to delete job'
        }),
                'headers': {
                'Access-Control-Allow-Origin': '*'
        }
    }   )
        
    
   
    # Return the response object.
    return fixCORS({
        'statusCode': 200,
        'body': json.dumps({
            'message': f'Successfully delete a job - {ID}'
        }),
                'headers': {
                'Access-Control-Allow-Origin': '*'
        }
    })
