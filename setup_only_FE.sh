


#Platform:
CORTEX=cancelit-env-1.eba-pmamcuv5.us-east-1.elasticbeanstalk.com
CLOUDMRSTACK=cmr
_NN_=6334



# Create a bucket
BUCKET_NAME=mro-mainbucket-$_NN_
FRONTSTACKNAME=MROFrontstack



#check if $BUCKET_NAME exists
aws s3api head-bucket --bucket $BUCKET_NAME --region $REGION
if [ $? -eq 0 ]; then
    echo "Bucket exists"
else
    aws s3api create-bucket --bucket $BUCKET_NAME --region $REGION 
fi



#frontend

APITOKEN='mroptimum'
#cloud formaiton make an api-token

PROFILE_SERVER=
CLOUDMR_SERVER=
MRO_SERVER=tbd
TOKEN_URL=null

GITTOKENS=token

PARAMS="GithubToken=$GITTOKENS ApiToken=$APITOKEN CloudmrServer=$CLOUDMR_SERVER MroServer=$MRO_SERVER ProfileServer=$PROFILE_SERVER"


sam build -t Frontend/template.yaml --use-container --build-dir build/front
sam deploy --template-file build/front/template.yaml --stack-name $FRONTSTACKNAME --capabilities CAPABILITY_AUTO_EXPAND CAPABILITY_IAM --resolve-image-repos --s3-bucket $BUCKET_NAME --parameter-overrides $PARAMS



