# Scripts Directory

This directory contains all shell scripts and deployment utilities for the GargoyleScope application.

## Scripts

- `deploy.sh` - Main deployment script for AWS infrastructure
- `cleanup.sh` - Cleanup script to remove AWS resources

## Usage

### Deployment
To deploy the entire application to AWS:
```bash
./scripts/deploy.sh
```

This script will:
1. Build and push Docker images to ECR
2. Deploy CloudFormation stack
3. Set up email infrastructure
4. Configure S3 triggers and SES rules

### Cleanup
To remove all AWS resources:
```bash
./scripts/cleanup.sh
```

This script will:
1. Delete the CloudFormation stack
2. Remove all associated AWS resources

## Prerequisites

Before running the scripts, ensure you have:
- AWS CLI installed and configured
- Docker installed and running
- Required environment variables set:
  - `OPENAI_API_KEY`
  - `GOOGLE_API_KEY`
  - `GOOGLE_CSE_ID`

## Permissions

All scripts have executable permissions. If you need to restore them:
```bash
chmod +x scripts/*.sh
```

## Troubleshooting

- Ensure AWS credentials are properly configured
- Check that Docker is running
- Verify all required environment variables are set
- Review CloudWatch logs for detailed error information 