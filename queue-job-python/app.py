import json
import requests
import boto3
import os
import os
os.environ['CURL_CA_BUNDLE'] = ''

def getHeadersForRequests():
    return {"Content-Type": "application/json","User-Agent": 'My User Agent 1.0','From': 'theweblogin@iam.com'}

def getHeadersForRequestsWithToken(token):
    headers = getHeadersForRequests()
    headers["Authorization"]= token
    return headers
    
def lambda_handler(event, context):
    body = json.loads(event['body'])
    # Get the headers from the event object.
    headers = event['headers']
    # Get the authorization header.
    authorization_header = headers['Authorization']
    # Get the application and pipeline names.
    
    application = 'MR Optimum'
    alias = body['alias']
    task = body['task']
    output = body['output']
    pipelineAPI = os.environ.get("PipelineScheduler")
    
    data2={"application":application,"alias":alias}
    r2=requests.post(pipelineAPI, data=json.dumps(data2), headers=getHeadersForRequestsWithToken(authorization_header))
    R=r2.json()
   
    bucket = os.environ.get("JobBucketName")
    pipeline_id = R["pipeline"]

    # Create a job object.
    
    job= {
        "task": task,
        "output" : output,
        "application" : application,
        "alias":alias,
        "pipeline":pipeline_id,
        'token': authorization_header,
        }
    
    print(job)
    # Write the job to the S3 bucket.
    s3 = boto3.client('s3')
    key = f'{pipeline_id}.json'
    s3.put_object(Bucket=bucket, Key=key, Body=json.dumps(job))

    # Return the response object.
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'Successfully scheduled a job - {}'.format(key),
            'alias': key,
            'job': json.dumps(job)
        }),
                'headers': {
                'Access-Control-Allow-Origin': '*'
        }
    }
