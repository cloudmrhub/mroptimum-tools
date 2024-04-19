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
    console.log(event);
    return await upload_data_init(event);
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

/**
 * Post file metadata to cloudmrhub.com API
 */
async function postMetaData(fileName, fileSize,fileMd5,Key,event){
    // Post file metadata to cloudmrhub.com API
    const headers = getHeadersForRequestsWithToken(event.headers['Authorization']);
    const payload = {
        filename: fileName,
        location: JSON.stringify({ Key, Bucket: process.env.UploadBucket }),
        size: fileSize,
        md5: fileMd5
    };
    // console.log(headers);
    // console.log(payload);
    let response = await axios.post(`https://${HOST}/api/data/create`, payload, {
        headers: headers
    });
    response.data.filename = fileName;
    response.data.database = 's3';
    return response;
}

const upload_data_init = async (event) => {
    try {
        const body = JSON.parse(event.body);
        const fileName = body.filename;
        const fileType = body.filetype;
        const fileSize = body.filesize;
        const fileMd5 = body.filemd5;
        const Key = `${uuidv4()}_${fileName}`;
        const pushCortex = process.env.PushCortex==='True';
        let response = undefined;
        if(pushCortex){
            response = await postMetaData(fileName,fileSize, fileMd5,Key,event);
            if (response.status !== 200) {
                throw new Error("Failed to save file metadata to cloudmrhub.com");
            }
        }
        /**
         * Core logic of multipart upload initialization starts here
         */
        const bucketName = process.env.UploadBucket;
        const partSize = 10 * 1024 * 1024; // 20MB, adjust as needed
        const partCount = Math.ceil(fileSize / partSize);

        // Initialize the multipart upload
        const createMultipartUploadResponse = await s3.createMultipartUpload({
            Bucket: bucketName,
            Key,
            ContentType: fileType // Adjust based on your needs
        }).promise();

        const uploadId = createMultipartUploadResponse.UploadId;

        // Generate pre-signed URLs for each part
        const partUrls = await Promise.all(
            [...Array(partCount).keys()].map(partNumber =>
                s3.getSignedUrlPromise('uploadPart', {
                    Bucket: bucketName,
                    Key,
                    UploadId: uploadId,
                    PartNumber: partNumber + 1,
                    Expires: 3600
                })
            )
        );

        /**
         * Core logic of multipart upload initialization ends here
         */


        return {
            statusCode: 200,
            headers: {
                'Access-Control-Allow-Origin': '*'
            },
            body: JSON.stringify({
                response: response?.data,
                uploadId,
                partUrls,
                Key
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