# CloudFormation Templates

This directory contains AWS CloudFormation templates and related configuration files for the GargoyleScope application.

## Files

- `template.yaml` - Main CloudFormation template defining:
  - Lambda functions (newsAlerter, worker, handleTable, emailControls)
  - IAM roles and policies
  - EventBridge rules for scheduled execution
  - Lambda permissions

- `spot-spec.json` - EC2 spot instance specification for model server
  - Instance type: g4dn.xlarge
  - AMI: ami-0c7217cdde317cfec
  - Security group: model-server-sg

- `samconfig.toml` - SAM (Serverless Application Model) configuration
  - Stack name: gargoylescope
  - Region: us-west-1
  - ECR image repositories for each Lambda function

## Deployment

### Using deploy.sh script (recommended)
```bash
./scripts/deploy.sh
```

### Manual deployment
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

## Parameters

- `OpenAiApiKey` - OpenAI API key for GPT analysis
- `GoogleApiKey` - Google Custom Search API key
- `GoogleCseId` - Google Custom Search Engine ID
- `AwsRegion` - AWS region for deployment
- `AwsAccountId` - AWS account ID for ECR image URIs

## Resources Created

- 4 Lambda functions with container images
- IAM execution role with necessary permissions
- EventBridge rule for daily news alerts (disabled by default)
- Lambda permissions for EventBridge invocation 