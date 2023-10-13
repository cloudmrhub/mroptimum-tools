import json
import requests
import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['CURL_CA_BUNDLE'] = ''
Host=os.getenv('Host')
def getHeadersForRequests():
    return {    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive',
    "Content-Type": 'application/json','User-Agent': 'curl','From': 'mailto:devn@cloudmrhub.com','Host':Host}
def getHeadersForRequests2():
    return {"Content-Type": "application/json","User-Agent": "My User Agent 1.0","From": "theweblogin@iam.com","Host":Host}




def getHeadersForRequestsWithToken(token):
    headers = getHeadersForRequests()
    headers["Authorization"]= token
    return headers


def lambda_handler(event, context):
    try:
        token = event["authorizationToken"]
        headers=getHeadersForRequestsWithToken(token)
        url=f'https://{Host}/api/auth/profile'
        print(url)
        print(headers)
        cmr_profile_resp = requests.get(url, headers=headers,verify = False)
        print(cmr_profile_resp.text)
        resp_data = cmr_profile_resp.json()
        print(resp_data)
        del resp_data['info']
        if resp_data.get('id') and resp_data.get('name'):
            return generate_policy(resp_data['id'], 'Allow', resp_data)
        else:
            raise ValueError('Authorization with cloud mr failed. Either token is invalid or request has invalid or missing headers (like Cookie, From, User-Agent)')
    except Exception as error:
        return generate_policy(0, 'Deny', {})

def generate_policy(principal_id, effect, user_profile):
    auth_response = {}
    auth_response['principalId'] = principal_id
    if effect:
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": effect,
                "Resource": '*'

            }]
        }
        auth_response['policyDocument'] = policy_document

    # Optional output with custom properties of the String, Number, or Boolean type.
        # Set the CORS headers
    # response_headers = {
    #     'Access-Control-Allow-Origin': '*',
    #     'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
    #     'Access-Control-Allow-Headers': 'Authorization'
    # }
    auth_response['context'] = user_profile
    # auth_response['headers']: response_headers
    return auth_response