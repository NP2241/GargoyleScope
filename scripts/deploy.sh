#!/bin/bash

# Exit on any error
set -e

# Configuration
AWS_REGION="us-west-1"
AWS_ACCOUNT="767397836855"
FUNCTIONS=("newsalerter" "worker" "handletable" "emailcontrols")
STACK_NAME="gargoylescope"

# Clean up any old images first
echo "🧹 Cleaning up old images..."
for FUNC in "${FUNCTIONS[@]}"; do
    docker rmi -f ${FUNC}function:latest 2>/dev/null || true
    docker rmi -f ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FUNC}function:latest 2>/dev/null || true
done

# Create ECR repositories if they don't exist
for FUNC in "${FUNCTIONS[@]}"; do
    REPO_NAME="${FUNC}function"
    echo "🏗️ Creating/verifying ECR repository for ${REPO_NAME}..."
    
    if ! aws ecr describe-repositories --repository-names ${REPO_NAME} 2>/dev/null; then
        aws ecr create-repository --repository-name ${REPO_NAME} \
            --image-scanning-configuration scanOnPush=true
        echo "✅ Created repository ${REPO_NAME}"
    else
        echo "✅ Repository ${REPO_NAME} already exists"
    fi
done

# Login to ECR (do this once, not for each repo)
echo "🔑 Logging into ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo "🚀 Starting deployment process..."

# Force rebuild all images
for FUNC in "${FUNCTIONS[@]}"; do
    echo "🚀 Building and deploying ${FUNC}..."
    
    # Build Docker image
    echo "📦 Building Docker image..."
    # Map function names to directory names
    case "${FUNC}" in
        "newsalerter")
            FUNCTION_DIR="news_alerter"
            ;;
        "handletable")
            FUNCTION_DIR="handle_table"
            ;;
        "emailcontrols")
            FUNCTION_DIR="email_controls"
            ;;
        *)
            FUNCTION_DIR="${FUNC}"
            ;;
    esac
    
    docker build --no-cache -f src/functions/${FUNCTION_DIR}/Dockerfile -t ${FUNC}function:latest .
    
    # Tag image for ECR
    echo "🏷️ Tagging image for ECR..."
    docker tag ${FUNC}function:latest \
        ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FUNC}function:latest
    
    # Push to ECR
    echo "⬆️ Pushing to ECR..."
    docker push ${AWS_ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FUNC}function:latest
done

# Deploy CloudFormation stack
echo "🏗️ Deploying CloudFormation stack..."
aws cloudformation deploy \
  --template-file infrastructure/cloudformation/template.yaml \
  --stack-name ${STACK_NAME} \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    OpenAiApiKey="${OPENAI_API_KEY}" \
    GoogleApiKey="${GOOGLE_API_KEY}" \
    GoogleCseId="${GOOGLE_CSE_ID}" \
    AwsRegion=${AWS_REGION} \
    AwsAccountId=${AWS_ACCOUNT}

# Check if deployment was successful
if [ $? -ne 0 ]; then
    echo "❌ CloudFormation deployment failed"
    exit 1
fi

echo "✅ Deployment complete!"

echo "Setting up email controls infrastructure..."

# Check if bucket already exists
if aws s3 ls "s3://gargoylescope-incoming-emails" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "Creating S3 bucket for incoming emails..."
    aws s3 mb s3://gargoylescope-incoming-emails --region us-west-1
else
    echo "✅ S3 bucket already exists"
fi

echo "Adding bucket policy for SES..."
# Add bucket policy for SES
aws s3api put-bucket-policy \
    --bucket gargoylescope-incoming-emails \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowSESPuts",
            "Effect": "Allow",
            "Principal": {
                "Service": "ses.amazonaws.com"
            },
            "Action": "s3:PutObject",
            "Resource": "arn:aws:s3:::gargoylescope-incoming-emails/*"
        }]
    }'

# Verify SES domain and email are set up
if ! aws ses get-identity-verification-attributes --identities "gargoylescope.com" | grep -q "Success"; then
    echo "⚠️ Warning: gargoylescope.com domain may not be verified in SES"
fi

# Create SES rule set if it doesn't exist
echo "Creating SES rule set..."
if ! aws ses describe-receipt-rule-set --rule-set-name "default-rule-set" --output json --no-cli-pager 2>/dev/null; then
    aws ses create-receipt-rule-set --rule-set-name "default-rule-set" --no-cli-pager
    echo "Created new rule set"
else
    echo "✅ Rule set already exists"
fi

echo "Creating SES receipt rule..."
# Create SES receipt rule
if ! aws ses describe-receipt-rule --rule-set-name "default-rule-set" --rule-name "store-emails" --no-cli-pager 2>/dev/null; then
    aws ses create-receipt-rule \
        --rule-set-name "default-rule-set" \
        --no-cli-pager \
        --rule '{
            "Name": "store-emails",
            "Enabled": true,
            "Recipients": ["reports@gargoylescope.com"],
            "Actions": [{
                "S3Action": {
                    "BucketName": "gargoylescope-incoming-emails"
                }
            }]
        }'
    echo "Created new receipt rule"
else
    echo "✅ Receipt rule already exists"
fi

echo "Adding Lambda permissions..."
# Try to add S3 permission, but don't error if it already exists
aws lambda add-permission \
    --function-name emailControls \
    --statement-id S3InvokeFunction \
    --action lambda:InvokeFunction \
    --principal s3.amazonaws.com \
    --source-arn arn:aws:s3:::gargoylescope-incoming-emails 2>/dev/null || \
    echo "✅ S3 invoke permission already exists (this is expected)"

# Replace ACCOUNT_ID with actual account ID
NOTIFICATION_CONFIG=$(echo '{
    "LambdaFunctionConfigurations": [{
        "LambdaFunctionArn": "arn:aws:lambda:us-west-1:'${AWS_ACCOUNT}':function:emailControls",
        "Events": ["s3:ObjectCreated:*"]
    }]
}')

echo "Configuring S3 trigger..."
# Configure S3 to trigger Lambda
aws s3api put-bucket-notification-configuration \
    --bucket gargoylescope-incoming-emails \
    --notification-configuration "$NOTIFICATION_CONFIG"

# Verify setup
echo "Verifying setup..."
if aws ses get-receipt-rule --rule-set-name "default-rule-set" --rule-name "store-emails" --no-cli-pager 2>/dev/null; then
    echo "✅ SES receipt rule verified"
else
    echo "⚠️ Warning: SES receipt rule verification failed"
fi

echo "✅ Email controls infrastructure set up successfully"