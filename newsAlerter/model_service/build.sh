#!/bin/bash

# Get AWS account ID and region
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(aws configure get region)

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names deepseek-sentiment || \
aws ecr create-repository --repository-name deepseek-sentiment

# Build and push Docker image
aws ecr get-login-password --region $AWS_REGION | \
docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

docker build -t deepseek-sentiment .
docker tag deepseek-sentiment:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/deepseek-sentiment:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/deepseek-sentiment:latest 