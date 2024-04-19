

#Platform:
CORTEX=cancelit-env-1.eba-pmamcuv5.us-east-1.elasticbeanstalk.com
CLOUDMRSTACK=cmr
MROPTIMUMSTACK=mrov1s1
FRONTSTACKNAME=frontmod1
PROFILE=https://ewjjq013u0.execute-api.us-east-1.amazonaws.com/profile
CLOUDMRCMR=https://ewjjq013u0.execute-api.us-east-1.amazonaws.com/
BUCKET_NAME=cancelit-mod1-bucket

#check if $BUCKET_NAME exists
aws s3api head-bucket --bucket $BUCKET_NAME --region $REGION
if [ $? -eq 0 ]; then
    echo "Bucket exists"
else
    aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION 
fi





TOKEN_KEY="ApiToken"

APITOKEN="api-token"


#frontend
PROFILE_SERVER=$(aws cloudformation describe-stacks --stack-name $CLOUDMRSTACK --query "Stacks[0].Outputs[?OutputKey=='ProfileGetAPI'].OutputValue" --output text)
CLOUDMR_SERVER=$(aws cloudformation describe-stacks --stack-name $CLOUDMRSTACK --query "Stacks[0].Outputs[?OutputKey=='CmrApi'].OutputValue" --output text)

MRO_SERVER=https://dplk0uo9d0.execute-api.us-east-1.amazonaws.com/Prod
GITTOKENS=$CMRGITTOKEN

PARAMS="GithubToken=$GITTOKENS ApiToken=$APITOKEN CloudmrServer=$CLOUDMR_SERVER MroServer=$MRO_SERVER ProfileServer=$PROFILE_SERVER ApiUrl=aa"


sam build -t Frontend/template.yaml --use-container --build-dir build/frontmod1
sam deploy --template-file build/frontmod1/template.yaml --stack-name $FRONTSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides $PARAMS
# sam deploy --template-file build/front/template.yaml --stack-name $FRONTSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides $(echo $PARAMS)


FRONTEND_URL=$(aws cloudformation describe-stacks --stack-name $FRONTSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='AmplifyAppDomain'].OutputValue" --output text)

aws amplify update-branch --app-id $APP_ID --branch-name main --environment-variables TOKEN-URL=$API_URL,CLOUDMR_SERVER=$CLOUDMR_SERVER,MRO_SERVER=$MRO_SERVER,PROFILE_SERVER=$PROFILE_SERVER,API_TOKEN=$API_TOKEN