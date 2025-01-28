from lambda_function import *
import json
import os
import boto3

import pynico_eros_montin.pynico as pn
E=pn.Pathable("backend/run-job-python/event_fail.json")
E=E.readJson()
import sys
import cmtools.cmaws as cmaws


def list_bucket(bucket_name,s3):
    # Check if the bucket exists and list its contents
    bucket = s3.Bucket(bucket_name)
    OBJ=[]
    if bucket.creation_date:
        print(f"Bucket '{bucket_name}' exists. Listing contents:")
        for obj in bucket.objects.all():
            OBJ.append(obj.key)
    else:
        print(f"Bucket '{bucket_name}' does not exist.")
    return OBJ

        
LOGIN=pn.Pathable('/g/key.json').readJson()
KID=LOGIN['key_id']
KSC=LOGIN['key']
TOK=LOGIN['token']

s3 = cmaws.getS3Resource(KID,KSC,TOK)



print("Listing all buckets:")
print(list_bucket('mytestcmr', s3))


handler(E, None,s3=s3)