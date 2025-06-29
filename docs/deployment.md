# Deployment Guide

This guide covers the complete deployment process for GargoyleScope, including infrastructure setup, configuration, and monitoring.

## 📋 Prerequisites

Before deploying, ensure you have:

- **AWS CLI** installed and configured with appropriate permissions
- **Docker** installed and running
- **Required API keys**:
  - OpenAI API key
  - Google Custom Search API key
  - Google Custom Search Engine ID
- **Domain setup** for email functionality (optional but recommended)

## 🚀 Quick Deployment

### 1. Clone and Setup

```bash
git clone <repository-url>
cd GargoyleScope
```

### 2. Configure Environment

```bash
# Copy the example configuration
cp config/env.example.json config/env.json

# Edit with your actual values
nano config/env.json
```

Required configuration values:
- `OPENAI_API_KEY`: Your OpenAI API key
- `GOOGLE_API_KEY`: Your Google Custom Search API key
- `GOOGLE_CSE_ID`: Your Google Custom Search Engine ID
- `EMAIL_FROM`: Sender email address
- `EMAIL_TO`: Recipient email address

### 3. Deploy Infrastructure

```bash
# Run the deployment script
./scripts/deploy.sh
```

This script will:
- Build and push Docker images to ECR
- Deploy CloudFormation stack
- Set up email infrastructure
- Configure S3 triggers and SES rules

## 🏗️ Detailed Deployment Process

### Step 1: Infrastructure Setup

The deployment creates the following AWS resources:

#### Lambda Functions
- **newsAlerter**: Main orchestration function
- **worker**: Article processing and analysis
- **handleTable**: DynamoDB table management
- **emailControls**: Email command processing

#### Supporting Services
- **DynamoDB**: Entity tracking and analysis storage
- **S3**: Email storage bucket
- **SES**: Email processing and delivery
- **EventBridge**: Scheduled execution
- **ECR**: Container image repositories

### Step 2: Email Infrastructure Setup

The deployment automatically configures:

1. **S3 Bucket**: `gargoylescope-incoming-emails`
2. **SES Rule Set**: Processes incoming emails
3. **Receipt Rule**: Routes emails to S3 and triggers Lambda
4. **Lambda Permissions**: Allows S3 to invoke emailControls function

### Step 3: Configuration Verification

After deployment, verify:

```bash
# Check CloudFormation stack status
aws cloudformation describe-stacks --stack-name gargoylescope

# Verify Lambda functions
aws lambda list-functions --query 'Functions[?contains(FunctionName, `gargoylescope`) || contains(FunctionName, `newsAlerter`) || contains(FunctionName, `worker`) || contains(FunctionName, `handleTable`) || contains(FunctionName, `emailControls`)]'

# Check ECR repositories
aws ecr describe-repositories --query 'repositories[?contains(repositoryName, `function`)]'
```

## 🔧 Configuration Options

### Environment Variables

The system uses the following environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for GPT analysis | Yes |
| `GOOGLE_API_KEY` | Google Custom Search API key | Yes |
| `GOOGLE_CSE_ID` | Google Custom Search Engine ID | Yes |
| `EMAIL_FROM` | Sender email address | Yes |
| `EMAIL_TO` | Recipient email address | Yes |
| `AWS_REGION` | AWS region for deployment | Yes |
| `AWS_ACCOUNT_ID` | AWS account ID | Yes |

### CloudFormation Parameters

The deployment accepts the following parameters:

```bash
aws cloudformation deploy \
  --template-file infrastructure/cloudformation/template.yaml \
  --stack-name gargoylescope \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    OpenAiApiKey="your-openai-key" \
    GoogleApiKey="your-google-key" \
    GoogleCseId="your-cse-id" \
    AwsRegion="us-west-1" \
    AwsAccountId="your-account-id"
```

## 📧 Email Setup

### Domain Verification

1. **Verify Domain in SES**:
   ```bash
   aws ses verify-domain-identity --domain yourdomain.com
   ```

2. **Add DNS Records**: Add the provided TXT record to your domain's DNS

3. **Verify Email Address**:
   ```bash
   aws ses verify-email-identity --email-address reports@yourdomain.com
   ```

### Email Commands

Once deployed, you can manage entities via email:

- **ADD entity_name**: Add an entity to monitoring
- **DELETE entity_name**: Remove an entity from monitoring
- **LIST**: List all monitored entities

Send emails to: `reports@yourdomain.com`

## 🧪 Testing Deployment

### 1. Test Lambda Functions

```bash
# Test news_alerter function
aws lambda invoke \
  --function-name newsAlerter \
  --payload '{"test": true}' \
  response.json

# Test handle_table function
aws lambda invoke \
  --function-name handleTable \
  --payload '{"action": "list", "parent_entity": "Stanford"}' \
  response.json
```

### 2. Test Email Commands

Send a test email to `reports@yourdomain.com` with:
```
LIST
```

### 3. Monitor Logs

```bash
# View CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/"

# Get recent logs for a function
aws logs tail /aws/lambda/newsAlerter --follow
```

## 🔄 Updating Deployment

### Code Updates

1. **Update code** in the appropriate function directory
2. **Rebuild and redeploy**:
   ```bash
   ./scripts/deploy.sh
   ```

### Configuration Updates

1. **Update config/env.json**
2. **Redeploy CloudFormation stack**:
   ```bash
   aws cloudformation deploy \
     --template-file infrastructure/cloudformation/template.yaml \
     --stack-name gargoylescope \
     --capabilities CAPABILITY_NAMED_IAM
   ```

## 🧹 Cleanup

To remove all deployed resources:

```bash
./scripts/cleanup.sh
```

This will:
- Delete the CloudFormation stack
- Remove all associated AWS resources
- Clean up ECR repositories (optional)

## 🚨 Troubleshooting

### Common Issues

1. **Docker Build Failures**:
   - Ensure Docker is running
   - Check Dockerfile syntax
   - Verify dependencies in requirements.txt

2. **Lambda Invocation Errors**:
   - Check CloudWatch logs
   - Verify IAM permissions
   - Ensure environment variables are set

3. **Email Processing Issues**:
   - Verify SES domain verification
   - Check S3 bucket permissions
   - Ensure Lambda permissions for S3

4. **API Key Errors**:
   - Verify API keys in config/env.json
   - Check API key permissions and quotas
   - Ensure keys are valid and active

### Debug Commands

```bash
# Check Lambda function status
aws lambda get-function --function-name newsAlerter

# View recent CloudWatch logs
aws logs tail /aws/lambda/newsAlerter --since 1h

# Test DynamoDB connectivity
aws dynamodb list-tables

# Check S3 bucket contents
aws s3 ls s3://gargoylescope-incoming-emails/
```

## 📊 Monitoring

### CloudWatch Metrics

Monitor the following metrics:
- Lambda function invocations and errors
- DynamoDB read/write capacity
- S3 bucket activity
- SES email delivery rates

### Alerts

Set up CloudWatch alarms for:
- Lambda function errors
- High DynamoDB throttling
- Email processing failures

## 🔒 Security Considerations

- **API Keys**: Store securely and rotate regularly
- **IAM Permissions**: Use least privilege principle
- **Network Security**: VPC configuration if needed
- **Data Encryption**: Enable encryption at rest and in transit
- **Access Logging**: Enable CloudTrail for audit trails

## 📈 Scaling

The system automatically scales based on:
- Lambda function invocations
- DynamoDB read/write capacity
- S3 storage requirements

For high-volume deployments, consider:
- DynamoDB on-demand capacity
- Lambda provisioned concurrency
- S3 lifecycle policies 