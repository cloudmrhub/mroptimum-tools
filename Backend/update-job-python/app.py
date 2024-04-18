import json
import requests
import boto3
import os
import os
os.environ['CURL_CA_BUNDLE'] = ''
import zipfile
pipelineAPI =os.getenv('PipelineCompleted')
pipelineAPIFailed =os.getenv('PipelineFailed')
pipelinescheduleAPI = os.getenv("PipelineScheduler")

mroptimum_result=os.getenv("ResultsBucketName","mroptimum-result")
mroptimum_failed=os.getenv("FailedBucketName","mroptimum-failed")

def getHeadersForRequests():
    return {"Content-Type": "application/json","User-Agent": "My User Agent 1.0","From": "theweblogin@iam.com","Host":os.getenv("Host")}


def getHeadersForRequestsWithToken(token):
    headers = getHeadersForRequests()
    headers["Authorization"]= token
    return headers
    
def lambda_handler(event, context):
    # connect to the s3
    s3 = boto3.client("s3")
    # Get the bucket name and file key
    bucket_name = event["Records"][0]["s3"]["bucket"]["name"]
    file_key = event["Records"][0]["s3"]["object"]["key"]
    #save zip  file to local
    fj="/tmp/a.zip"

    s3 = boto3.resource("s3")
    s3.Bucket(bucket_name).download_file(file_key,fj)
    archive = zipfile.ZipFile(fj, 'r')
    J=archive.read('info.json')
    J=json.loads(J)
    token=J["headers"]["options"]["token"]
    
    
    pipelineid=J["headers"]["options"]["pipelineid"]
    
    if pipelineid==None:
        application = 'MR Optimum'
        alias=J["headers"]["options"]["alias"]
        data2={"application":application,"alias":alias}
        r2=requests.post(pipelinescheduleAPI, data=json.dumps(data2), headers=getHeadersForRequestsWithToken(token))
        R=r2.json()
        pipelineid = R["pipeline"]
        
        #write into to the info.json
    data2={
    "results":f"s3://{bucket_name}/{file_key}",
    "output":f"s3://{bucket_name}/{file_key}",
    "log":"None",
    "options":"None",
    "input":"None"
    }

    
    

    if bucket_name==mroptimum_result:
        url=f'{pipelineAPI}/{pipelineid}'
        r2=requests.post(url, data=json.dumps(data2), headers=getHeadersForRequestsWithToken(token))
        print("ok")
    elif bucket_name==mroptimum_failed:
        url=f'{pipelineAPIFailed}/{pipelineid}'
        r2=requests.post(url, data=json.dumps(data2), headers=getHeadersForRequestsWithToken(token))
        print("failed")
    print (url)
    R=r2.json()
    print(R)