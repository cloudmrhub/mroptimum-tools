docker build -t docker-image:test_1 .
docker tag docker-image:test_1 629774729342.dkr.ecr.us-east-1.amazonaws.com/mroptimum:latest
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 629774729342.dkr.ecr.us-east-1.amazonaws.com
docker tag docker-image:test_1 629774729342.dkr.ecr.us-east-1.amazonaws.com/mroptimum:latest
docker push 629774729342.dkr.ecr.us-east-1.amazonaws.com/mroptimum:latest

#in case check 
#pluma ~/.aws/credentials
#must have default 
#AWS_ACCESS_KEY_ID=",,"
#AWS_SECRET_ACCESS_KEY=""
#AWS_SESSION_TOKEN="NFE"
