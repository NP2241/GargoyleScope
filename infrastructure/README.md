# Infrastructure Directory

This directory contains all infrastructure as code (IaC) files for the GargoyleScope application.

## Directory Structure

- `cloudformation/` - AWS CloudFormation templates and related files
- `terraform/` - Terraform configuration files (if using Terraform)

## CloudFormation

The `cloudformation/` directory contains:
- `template.yaml` - Main CloudFormation template for Lambda functions and IAM roles
- `spot-spec.json` - EC2 spot instance specification
- `samconfig.toml` - SAM (Serverless Application Model) configuration

### Usage

To deploy the CloudFormation stack:
```bash
./scripts/deploy.sh
```

Or manually:
```bash
aws cloudformation deploy \
  --template-file infrastructure/cloudformation/template.yaml \
  --stack-name gargoylescope \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    OpenAiApiKey="your-key" \
    GoogleApiKey="your-key" \
    GoogleCseId="your-id" \
    AwsRegion="us-west-1" \
    AwsAccountId="your-account-id"
```

## Terraform

The `terraform/` directory is ready for Terraform configurations if needed in the future.

## Best Practices

- Keep infrastructure templates version controlled
- Use consistent naming conventions
- Document all parameters and outputs
- Test templates in a staging environment first 