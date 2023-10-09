import axios from 'axios';

export const handler = async (event, context) => {
    try {
        // Perform token validation here (e.g., JWT validation)
        const token = event.authorizationToken;
        console.log('Auth Token:', token)
        console.log('Function Arn:', event.methodArn)
        // console.log(event.headers)
        // const cookie = event.headers?.['Cookie'] || '';
        // console.log('req token', event.authorizationToken)
        // console.log('req cookie(s)', cookie)
        // const cmrProfileResp = await axios({
        //     method: 'get',
        //     url: 'https://cloudmrhub.com/api/auth/profile',
        //     headers: {
        //         Accept: '*/*',
        //         ['Accept-Encoding']: 'gzip, deflate, br',
        //         Authorization: token,
        //         Cookie: cookie,
        //         ['Content-Type']: 'application/json',
        //         From: 'fake.email@gmail.com',
        //         ['User-Agent']: 'My User Agent 1.0'
        //     }
        // });
        // const { data: respData } = cmrProfileResp;

        // if (respData.id && respData.name) {
        //     // If token validation succeeds, generate the policy
        //     console.log(`Authorization succeeded, ID: ${respData.id} NAME: ${respData.name} `)
        //     return generatePolicy('user', 'Allow', event.methodArn);
        // } else {
        //     throw new Error('Authorization with cloud mr failed. Either token is invalid or request has invalid or missing headers (like Cookie, From, User-Agent)');
        // }

        console.log('Authorized Approved.')
        return generatePolicy('user', 'Allow', event.methodArn);


    } catch (error) {
        console.error('Authorization Rejected. Error:', error);
        return generatePolicy('user', 'Deny', event.methodArn);
    }
};

// Help function to generate an IAM policy
const generatePolicy = function(principalId, effect, resource) {
    const authResponse = {};
    
    authResponse.principalId = principalId;
    if (effect && resource) {
    const policyDocument = {
        Version: '2012-10-17',
        Statement: [{
        Action: 'execute-api:Invoke',
        Effect: effect,
        Resource: resource
        }]
    };
    authResponse.policyDocument = policyDocument;
    }
    
    // Optional output with custom properties of the String, Number or Boolean type.
    authResponse.context = {
        "stringKey": "stringval",
        "numberKey": 123,
        "booleanKey": true
    };
    return authResponse;
}
