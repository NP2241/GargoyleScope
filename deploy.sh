#!/bin/bash

# First build and push the model service
cd newsAlerter/model_service
chmod +x build.sh
./build.sh
cd ../..

# Then deploy the SAM application
sam build
sam deploy --guided 

# Deploy CloudFormation stack
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name gargoylescope \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    HuggingFaceToken=${HF_TOKEN}

# Get the EC2 instance public DNS
EC2_DNS=$(aws cloudformation describe-stacks \
  --stack-name gargoylescope \
  --query 'Stacks[0].Outputs[?OutputKey==`ModelServerDNS`].OutputValue' \
  --output text)

# Update environment variable
echo "MODEL_ENDPOINT=http://${EC2_DNS}:8080" >> .env 