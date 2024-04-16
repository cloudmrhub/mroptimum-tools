$profile = "NYUMCResearcherAdminFullAccess-469266894233"

# Define variables
$NN = "yuelongmro"
$CORTEX = "cancelit-env-1.eba-pmamcuv5.us-east-1.elasticbeanstalk.com"
$CLOUDMRSTACK = "cmr"
$PROFILE = "https://ewjjq013u0.execute-api.us-east-1.amazonaws.com/profile"
$CLOUDMRCMR = "https://ewjjq013u0.execute-api.us-east-1.amazonaws.com/"
$GITTOKENS = ""

$BUCKET_NAME = "mro-mainbucket-$NN"
$REGION = "us-east-1"
$COMMONSTACKNAME = "MROCommon-$NN"
$BACKSTACKNAME = "MROBackstack-$NN"
$FRONTSTACKNAME = "MROFrontstack-$NN"
$USAGEPLANSTACKNAME = "USAGEPLAN-$NN"

$JobsBucketPName = "xx--mroj-$NN"
$ResultsBucketPName = "xx--mror-$NN"
$DataBucketPName = "xx--mrod-$NN"
$FailedBucketPName = "xx--mrof-$NN"

# Check if bucket exists
Try {
    aws s3api head-bucket --bucket $BUCKET_NAME --region $REGION --profile $profile
    Write-Host "Bucket exists"
}
Catch {
    aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION --profile $profile
}

# Build and deploy common resources
sam build -t "Common/template.yaml" --use-container --build-dir "build/common" --profile $profile
Write-Host "Building common resources"
sam deploy --template-file "build/common/template.yaml" --stack-name $COMMONSTACKNAME --capabilities "CAPABILITY_AUTO_EXPAND","CAPABILITY_IAM" --region $REGION --resolve-image-repos --s3-bucket $BUCKET_NAME --profile $profile
Write-Host "Deploying common resources"

# Wait for stack creation
Write-Host "Waiting for stack to be created"
aws cloudformation wait stack-create-complete --stack-name $COMMONSTACKNAME --profile $profile

$REQUESTS_LAYER = aws cloudformation describe-stacks --stack-name $COMMONSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='RequestsARN'].OutputValue" --output text --profile $profile
Write-Host "Requests layer is $REQUESTS_LAYER"
Write-Host "Common resources deployed"

# Build and deploy backend resources
Write-Host "Building backend resources"
sam build -t "Backend/template.yaml" --use-container --build-dir "build/back" --profile $profile
sam deploy --template-file "build/back/template.yaml" --stack-name $BACKSTACKNAME --capabilities "CAPABILITY_AUTO_EXPAND","CAPABILITY_IAM" --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides "CortexHost=$($CORTEX) JobsBucketPName=$($JobsBucketPName) ResultsBucketPName=$($ResultsBucketPName) DataBucketPName=$($DataBucketPName) FailedBucketPName=$($FailedBucketPName) RequestsLayerARN=$($REQUESTS_LAYER)" --profile $profile

# Wait for backend stack creation
Write-Host "Waiting for stack to be created"
aws cloudformation wait stack-create-complete --stack-name $BACKSTACKNAME --profile $profile

# Deploy usage plan
sam build -t "UsagePlan/template.yaml" --use-container --build-dir "build/usageplan" --profile $profile
sam deploy --template-file "build/usageplan/template.yaml" --stack-name $USAGEPLANSTACKNAME --capabilities "CAPABILITY_AUTO_EXPAND","CAPABILITY_IAM" --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides "ApiGatewayApi=$API_ID StageName=$($STAGE_NAME)" --profile $profile

# Final output
$FRONTEND_URL = aws cloudformation describe-stacks --stack-name $FRONTSTACKNAME --query "Stacks[0].Outputs[?OutputKey=='AmplifyAppDomain'].OutputValue" --output text --profile $profile
Write-Host "Frontend URL is $FRONTEND_URL"
