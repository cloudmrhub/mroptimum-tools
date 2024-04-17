

#Platform:
CORTEX=cancelit-env-1.eba-pmamcuv5.us-east-1.elasticbeanstalk.com
CLOUDMRSTACK=cmr
_NN_=6334d
PROFILE=https://ewjjq013u0.execute-api.us-east-1.amazonaws.com/profile
CLOUDMRCMR=https://ewjjq013u0.execute-api.us-east-1.amazonaws.com/


# Create a bucket
BUCKET_NAME=mro-mainbucket-$_NN_
REGION=us-east-1
COMMONSTACKNAME=MROCommon-$_NN_
BACKSTACKNAME=MROBackstack-$_NN_
FRONTSTACKNAME=MROFrontstack-$_NN_
USAGEPLANSTACKNAME=USAGEPLAN-$_NN_


#check if $BUCKET_NAME exists
aws s3api head-bucket --bucket $BUCKET_NAME --region $REGION
if [ $? -eq 0 ]; then
    echo "Bucket exists"
else
    aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION 
fi




# get the value of the api-token from the cloudformation stack
#APITOKEN=$(aws cloudformation describe-stacks --stack-name $CLOUDMRSTACK --query "Stacks[0].Outputs[?OutputKey=='ApiToken'].OutputValue" --output text)    

TOKEN_KEY=$(aws cloudformation describe-stacks --stack-name $USAGEPLANSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='ApiKey'].OutputValue" --output text)

APITOKEN=$(aws apigateway get-api-key --api-key $TOKEN_KEY --include-value | jq -r '.value')

#cloud formaiton make an api-token



#frontend
PROFILE_SERVER=$(aws cloudformation describe-stacks --stack-name $CLOUDMRSTACK --query "Stacks[0].Outputs[?OutputKey=='ProfileGetAPI'].OutputValue" --output text)
if [ $? -eq 0 ]; then
    echo "Profile server exists"
else
    PROFILE_SERVER=$PROFILE
fi



CLOUDMR_SERVER=$(aws cloudformation describe-stacks --stack-name $CLOUDMRSTACK --query "Stacks[0].Outputs[?OutputKey=='CmrApi'].OutputValue" --output text)
if [ $? -eq 0 ]; then
    echo "cluodmr server exists"
else
    CLOUDMR_SERVER=$CLOUDMRCMR
fi


MRO_SERVER=$(aws cloudformation describe-stacks --stack-name $BACKSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='MROApi'].OutputValue" --output text)


GITTOKENS=$CMRGITTOKEN

PARAMS="GithubToken=$GITTOKENS ApiToken=$APITOKEN CloudmrServer=$CLOUDMR_SERVER MroServer=$MRO_SERVER ProfileServer=$PROFILE_SERVER ApiUrl=aa"


sam build -t Frontend/template.yaml --use-container --build-dir build/front
sam deploy --template-file build/front/template.yaml --stack-name $FRONTSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides $PARAMS
# sam deploy --template-file build/front/template.yaml --stack-name $FRONTSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides $(echo $PARAMS)


FRONTEND_URL=$(aws cloudformation describe-stacks --stack-name $FRONTSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='AmplifyAppDomain'].OutputValue" --output text)

aws amplify update-branch --app-id $APP_ID --branch-name main --environment-variables TOKEN-URL=$API_URL,CLOUDMR_SERVER=$CLOUDMR_SERVER,MRO_SERVER=$MRO_SERVER,PROFILE_SERVER=$PROFILE_SERVER,API_TOKEN=$API_TOKEN