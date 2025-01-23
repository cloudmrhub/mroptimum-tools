

#aws configure
FORCEBACK=1


#check if theres a parameter passed
if [ $# -eq 0 ]
  then
    echo "No arguments supplied"
    exit 1
    read -p "Please enter your git token: " GITTOKENS
    echo "Your git token is: $GITTOKENS"
else
    echo "Your git token is: $1"
    GITTOKENS=$1
fi

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



#Build common resources
MRO_REQUESTS_EXPORT=$(aws cloudformation list-exports --query "Exports[?Name=='MRORequests'].Value" --output text)
if [ -z "$MRO_REQUESTS_EXPORT" ]; then
    echo "MRORequests export does not exist. Building and deploying the layer."
    sam build -t common/template.yaml --use-container --build-dir build/common
    echo "Building common resources"
    sam deploy --template-file build/common/template.yaml --stack-name $COMMONSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --region $REGION --resolve-image-repos --s3-bucket $BUCKET_NAME
    echo "Deploying common resources"
    #wait for the stack to be created
    echo "Waiting for stack to be created"
    aws cloudformation wait stack-create-complete --stack-name $COMMONSTACKNAME
else
    echo "MRORequests export exists. Skipping the layer deployment."
fi


REQUESTS_LAYER=$(aws cloudformation list-exports --query "Exports[?Name=='MRORequests'].Value" --output text)
echo "Requests layer is $REQUESTS_LAYER"
echo "common resources deployed"

# REQUESTS_LAYER=$(aws cloudformation describe-stacks --stack-name $COMMONSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='RequestsARN'].OutputValue" --output text)
# check if API_ID exists
API_ID=$(aws cloudformation describe-stacks --stack-name $BACKSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='ApiId'].OutputValue" --output text)

if if [ -z "$API_ID" ] || [ "$FORCEBAKEND" -eq 1 ]; then
    echo "Building backend resources"
    sam build -t backend/template.yaml --use-container --build-dir build/back 
    # sam package --template-file build/back/template.yaml --s3-bucket $BUCKET_NAME --output-template-file build/back/packaged-template.yaml
    # sam deploy --template-file build/back/packaged-template.yaml --stack-name $BACKSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --region $REGION 
    sam deploy --template-file build/back/template.yaml --stack-name $BACKSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides "CortexHost=$CORTEX JobsBucketPName=$JobsBucketPName ResultsBucketPName=$ResultsBucketPName DataBucketPName=$DataBucketPName FailedBucketPName=$FailedBucketPName RequestsLayerARN=$REQUESTS_LAYER"  
    echo "Waiting for stack to be created"
    aws cloudformation wait stack-create-complete --stack-name $BACKSTACKNAME

    API_ID=$(aws cloudformation describe-stacks --stack-name $BACKSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='ApiId'].OutputValue" --output text)
    STAGE_NAME=$(aws cloudformation describe-stacks --stack-name $BACKSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='StageName'].OutputValue" --output text) 

else

    echo "Backend resources already exist"
fi

STAGE_NAME=$(aws cloudformation describe-stacks --stack-name $BACKSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='StageName'].OutputValue" --output text) 

echo "API_ID is $API_ID"
echo "Stage name is $STAGE_NAME"



MROPTIMUM_QUOTA=$(aws apigateway get-usage-plans --query "items[?name=='MROPtmumQuota'].id" --output text)

if [ -z "$MROPTIMUM_QUOTA" ]; then
    echo "Creating usage plan"
    sam build -t usageplan/template.yaml --use-container --build-dir build/usageplan
    sam deploy --template-file build/usageplan/template.yaml --stack-name $USAGEPLANSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides "ApiGatewayApi=$API_ID StageName=$STAGE_NAME"
    aws cloudformation wait stack-create-complete --stack-name $USAGEPLANSTACKNAME
else
    echo "Usage plan already exists"

    TOKEN_KEY=$(aws cloudformation describe-stacks --stack-name $USAGEPLANSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='ApiKey'].OutputValue" --output text)
    echo    "API key is $TOKEN_KEY"
    if [ -z "$TOKEN_KEY" ]; then
        echo "Creating API key"
     EXISTING_API_KEY_ID=$(aws apigateway get-api-keys --name-query "mroptimum-api-key" --query "items[0].id" --output text)
    sam build -t usageplan2/template.yaml --use-container --build-dir build/usageplan2
    sam deploy --template-file build/usageplan2/template.yaml --stack-name $USAGEPLANSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides "ApiGatewayApi=$API_ID StageName=$STAGE_NAME  ExistingUsagePlanId=$MROPTIMUM_QUOTA ExistingApiKeyId=$EXISTING_API_KEY_ID"
    aws cloudformation wait stack-create-complete --stack-name $USAGEPLANSTACKNAME
    else
        echo "API key already exists"
    fi
fi



# # # get the value of the api-token from the cloudformation stack
APITOKEN=$(aws cloudformation describe-stacks --stack-name $CLOUDMRSTACK --query "Stacks[0].Outputs[?OutputKey=='ApiToken'].OutputValue" --output text)    

echo    "API token is $APITOKEN"
APITOKEN=$(aws apigateway get-api-key --api-key $TOKEN_KEY --include-value | jq -r '.value')

echo    "API token is $APITOKEN"

# # #cloud formation make an api-token



#frontend
PROFILE_SERVER=$(aws cloudformation describe-stacks --stack-name $CLOUDMRSTACK --query "Stacks[0].Outputs[?OutputKey=='ProfileGetAPI'].OutputValue" --output text)
if [ $? -eq 0 ]; then
    echo "Profile server exists"
else
    PROFILE_SERVER=$PROFILE
fi

echo "Profile server is $PROFILE_SERVER"


CLOUDMR_SERVER=$(aws cloudformation describe-stacks --stack-name $CLOUDMRSTACK --query "Stacks[0].Outputs[?OutputKey=='CmrApi'].OutputValue" --output text)
if [ $? -eq 0 ]; then
    echo "cluodmr server exists"
else
    CLOUDMR_SERVER=$CLOUDMRCMR
fi


MRO_SERVER=$(aws cloudformation describe-stacks --stack-name $BACKSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='MROApi'].OutputValue" --output text)


# # GITTOKENS=$CMRGITTOKEN


PARAMS="GithubToken=$GITTOKENS ApiToken=$APITOKEN CloudmrServer=$CLOUDMR_SERVER MroServer=$MRO_SERVER ProfileServer=$PROFILE_SERVER StackName=$BACKSTACKNAME"


echo $PARAMS

# FRONTEND_URL=$(aws cloudformation describe-stacks --stack-name $FRONTSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='AmplifyAppDomain'].OutputValue" --output text)
FRONTEND_URL=""
if [ -z "$FRONTEND_URL" ]; then
    echo "Frontend does not exist"  
sam build -t frontend/template.yaml --use-container --build-dir build/front
# sam deploy --template-file build/front/template.yaml --stack-name $FRONTSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides $PARAMS
sam deploy --template-file build/front/template.yaml --stack-name $FRONTSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides $PARAMS
aws cloudformation wait stack-create-complete --stack-name $FRONTSTACKNAME
FRONTEND_URL=$(aws cloudformation describe-stacks --stack-name $FRONTSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='AmplifyAppDomain'].OutputValue" --output text)

else
    echo "Frontend already exists"
fi

echo $FRONTSTACKNAME
echo "Frontend URL is $FRONTEND_URL"

APP_ID=$(aws amplify list-apps --query "apps[?name=='MR Optimum${FRONTSTACKNAME}'].appId" --output text)



BRANCH_NAME="dev"
echo "App ID is $APP_ID"


aws amplify update-branch --app-id $APP_ID --branch-name stable --environment-variables TOKEN-URL=$API_URL,CLOUDMR_SERVER=$CLOUDMR_SERVER,MRO_SERVER=$MRO_SERVER,PROFILE_SERVER=$PROFILE_SERVER,API_TOKEN=$API_TOKEN --no-cli-pager
aws amplify update-branch --app-id $APP_ID --branch-name dev --environment-variables TOKEN-URL=$API_URL,CLOUDMR_SERVER=$CLOUDMR_SERVER,MRO_SERVER=$MRO_SERVER,PROFILE_SERVER=$PROFILE_SERVER,API_TOKEN=$API_TOKEN --no-cli-pager


aws amplify start-job --app-id $APP_ID --branch-name $BRANCH_NAME --job-type RELEASE
echo "Waiting for job to be created"

BRANCH_NAME="stable"
aws amplify start-job --app-id $APP_ID --branch-name $BRANCH_NAME --job-type RELEASE
echo "Waiting for job to be created"
echo "Job completed"

