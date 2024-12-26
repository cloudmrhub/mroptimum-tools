/*
Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

'use strict'

const AWS = require('aws-sdk');
AWS.config.update({ region: process.env.AWS_REGION })
const s3 = new AWS.S3()

// Change this value to adjust the signed URL's expiration
const URL_EXPIRATION_SECONDS = 300

const { v4: uuidv4 } = require('uuid');

process.env['NODE_TLS_REJECT_UNAUTHORIZED'] = '0';
// process.env["NODE_TLS_REJECT_UNAUTHORIZED"] = 1;
const HOST = process.env.Host;
const axios = require('axios');

// Main Lambda entry point
exports.handler = async (event) => {
    return await upload_data(event);
}
const getHeadersForRequests = () => {
    return {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'User-Agent': 'curl',
        'From': 'devn@cloudmrhub.com',
        'Host': HOST
    };
}

const getHeadersForRequestsWithToken = (token) => {
    const headers = getHeadersForRequests();
    headers["Authorization"] = token;
    // console.log(token)
    return headers;
}

const upload_data = async (event) => {
    try {
        const body = JSON.parse(event.body);
        const fileName = body.filename;
        const fileType = body.filetype;
        const fileSize = body.filesize;
        const fileMd5 = body.filemd5;
        const Key = `${uuidv4()}_${fileName}`;

        // Get signed URL from S3
        const s3Params = {
            Bucket: process.env.DataBucketName,
            Key,
            Expires: URL_EXPIRATION_SECONDS,
            ContentType: fileType,
            // This ACL makes the uploaded object publicly readable. You must also uncomment
            // the extra permission for the Lambda function in the SAM template.
            ACL: 'public-read'
        }

        console.log('Params: ', s3Params)
        const uploadURL = await s3.getSignedUrlPromise('putObject', s3Params)
        // console.log(event.headers);
        // Post file metadata to cloudmrhub.com API
        const headers = getHeadersForRequestsWithToken(event.headers['Authorization']);
        const payload = {
            filename: fileName,
            location: JSON.stringify({ Key, Bucket: process.env.DataBucketName }),
            size: fileSize,
            md5: fileMd5
        };
        // console.log(headers);
        // console.log(payload);
        const response = await axios.post(`https://${HOST}/api/data/create`, payload, {
            headers: headers
        });
        console.log("qui")
        console.log(response.status);
        if (response.status !== 200) {
            throw new Error("Failed to save file metadata to cloudmrhub.com");
        }
        response.data.filename = fileName;
        response.data.database = 's3';

        return {
            statusCode: 200,
            headers: {
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                upload_url: uploadURL,
                response: response.data
            })
        };
        // return {statusCode: 200}
    } catch (error) {
        console.error(`Uploading data failed due to: ${error.message}`);
        return {
            statusCode: 403,
            headers: {
                'Access-Control-Allow-Origin': '*'
            },
            body: "Upload failed for user"
        };
    }
}