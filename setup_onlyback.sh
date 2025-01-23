


#random part in the stack name
_NN_=v2

# to be filled by cmr

CORTEX=cancelit-env-1.eba-pmamcuv5.us-east-1.elasticbeanstalk.com
CLOUDMRSTACK=cmr

PROFILE=https://ewjjq013u0.execute-api.us-east-1.amazonaws.com/profile
CLOUDMRCMR=https://ewjjq013u0.execute-api.us-east-1.amazonaws.com/



# Create a bucket
BUCKET_NAME=mromainbucket$_NN_
REGION=us-east-1
COMMONSTACKNAME=MROCommon$_NN_
BACKSTACKNAME=MROBackstack$_NN_
FRONTSTACKNAME=MROFrontstack$_NN_
USAGEPLANSTACKNAME=USAGEPLAN$_NN_




JobsBucketPName=mroj$_NN_
ResultsBucketPName=mror$_NN_
DataBucketPName=mrod$_NN_
FailedBucketPName=mrof$_NN_


#check if $BUCKET_NAME exists
aws s3api head-bucket --bucket $BUCKET_NAME --region $REGION
if [ $? -eq 0 ]; then
    echo "Bucket exists"
else
    aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION 
fi




REQUESTS_LAYER=$(aws cloudformation list-exports --query "Exports[?Name=='MRORequests'].Value" --output text)
echo "Requests layer is $REQUESTS_LAYER"
echo "common resources deployed"

# REQUESTS_LAYER=$(aws cloudformation describe-stacks --stack-name $COMMONSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='RequestsARN'].OutputValue" --output text)
# check if API_ID exists


echo "Building backend resources"
sam build -t backend/template.yaml --use-container --build-dir build/back 
sam deploy --template-file build/back/template.yaml --stack-name $BACKSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides "CortexHost=$CORTEX JobsBucketPName=$JobsBucketPName ResultsBucketPName=$ResultsBucketPName DataBucketPName=$DataBucketPName FailedBucketPName=$FailedBucketPName RequestsLayerARN=$REQUESTS_LAYER"  
