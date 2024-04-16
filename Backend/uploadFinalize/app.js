
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
// const axios = require('axios');

// Main Lambda entry point
exports.handler = async (event) => {
    const { uploadId, parts, Key } = JSON.parse(event.body);
    const bucketName = process.env.UploadBucket; // Replace with your bucket name

    console.log(bucketName);
    console.log(event.body);
    // Sort parts by partNumber as it's required by S3
    parts.sort((a, b) => a.partNumber - b.partNumber);

    const completeMultipartUploadParams = {
        Bucket: bucketName,
        Key: Key,
        UploadId: uploadId,
        MultipartUpload: {
            Parts: parts.map(part => ({
                ETag: part.etag,
                PartNumber: part.partNumber
            }))
        }
    };

    try {
        // Complete the multipart upload
        const completeMultipartUploadResponse = await s3.completeMultipartUpload(completeMultipartUploadParams).promise();

        return {
            statusCode: 200,
            headers: {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'  },
            body: JSON.stringify({
                message: 'Upload completed successfully',
                location: completeMultipartUploadResponse.Location
            })
        };
    } catch (error) {
        console.error('Error completing multipart upload:', error);

        return {
            statusCode: 500,

            headers: {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: 'Error completing upload',
                error: error.message
            })
        };
    }
};

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