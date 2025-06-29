# GargoyleScope

A serverless AWS-based news monitoring and analysis system with multiple Lambda functions for automated news tracking and sentiment analysis.

## 🚀 Features

- **Automated News Monitoring**: Track news articles for specified entities using Google Custom Search
- **AI-Powered Analysis**: Sentiment analysis and importance assessment using OpenAI GPT models
- **Email-Based Management**: Manage entities through simple email commands (ADD/DELETE/LIST)
- **HTML Email Reports**: Beautiful, formatted email reports with important news highlights
- **DynamoDB Storage**: Persistent storage for entity tracking and analysis data
- **Serverless Architecture**: Fully managed AWS Lambda functions with automatic scaling
- **Email Integration**: SES-based email processing and delivery

## 📋 Prerequisites

- **AWS CLI** installed and configured with appropriate permissions
- **Docker** installed and running
- **Python 3.8+** for local development and testing
- **Required API Keys**:
  - OpenAI API key for GPT analysis
  - Google Custom Search API key and CSE ID
- **Domain setup** for email functionality (optional but recommended)

## 🏗️ Project Structure

```
GargoyleScope/
├── src/                          # Source code
│   ├── functions/                # Lambda function handlers
│   │   ├── news_alerter/         # Main orchestration function
│   │   │   ├── handler.py        # Main orchestration logic
│   │   │   ├── requirements.txt  # Python dependencies
│   │   │   ├── Dockerfile        # Container configuration
│   │   │   └── __init__.py
│   │   ├── worker/               # Article processing worker
│   │   │   ├── handler.py        # Article processing logic
│   │   │   ├── requirements.txt  # Python dependencies
│   │   │   ├── Dockerfile        # Container configuration
│   │   │   └── __init__.py
│   │   ├── handle_table/         # DynamoDB table management
│   │   │   ├── handler.py        # Table operations logic
│   │   │   ├── requirements.txt  # Python dependencies
│   │   │   ├── Dockerfile        # Container configuration
│   │   │   └── __init__.py
│   │   └── email_controls/       # Email command processing
│   │       ├── handler.py        # Email processing logic
│   │       ├── requirements.txt  # Python dependencies
│   │       ├── Dockerfile        # Container configuration
│   │       └── __init__.py
│   ├── shared/                   # Shared utilities and modules
│   │   ├── utils.py              # General utilities
│   │   ├── database.py           # DynamoDB operations
│   │   ├── email_helpers.py      # Email functions
│   │   └── __init__.py
│   └── web/                      # Web assets
│       ├── templates/            # HTML templates
│       │   ├── email_report.html # Main email report template
│       │   ├── email_preview.html # Email preview template
│       │   └── ...
│       └── static/               # Static assets
│           ├── css/              # Stylesheets
│           ├── js/               # JavaScript files
│           └── images/           # Image assets
├── infrastructure/               # Infrastructure as Code
│   ├── cloudformation/           # AWS CloudFormation templates
│   │   ├── template.yaml         # Main CloudFormation template
│   │   ├── spot-spec.json        # EC2 spot instance specification
│   │   └── README.md             # CloudFormation documentation
│   └── terraform/                # Terraform configurations (future)
│       └── README.md             # Terraform documentation
├── config/                       # Configuration files
│   ├── env.json                  # Production configuration (not in version control)
│   ├── env.local.json            # Local development configuration
│   ├── env.example.json          # Configuration template
│   ├── samconfig.toml            # SAM configuration
│   └── README.md                 # Configuration documentation
├── scripts/                      # Shell scripts and deployment utilities
│   ├── deploy.sh                 # Main deployment script
│   ├── cleanup.sh                # Cleanup script
│   └── README.md                 # Scripts documentation
├── tests/                        # Test files
│   ├── conftest.py               # Pytest configuration and fixtures
│   ├── tester.py                 # Legacy test file
│   ├── test_email.py             # Email testing utilities
│   ├── fixtures/                 # Test fixtures and data
│   │   ├── test_event.json       # Sample test events
│   │   └── testArticle.txt       # Sample article data
│   └── test_functions/           # Function-specific tests
│       ├── test_news_alerter.py  # News alerter function tests
│       ├── test_worker.py        # Worker function tests
│       ├── test_handle_table.py  # Handle table function tests
│       └── test_email_controls.py # Email controls function tests
├── docs/                         # Documentation
│   ├── README.md                 # Documentation overview
│   ├── deployment.md             # Deployment guide
│   ├── api-reference.md          # API documentation
│   ├── architecture.md           # System architecture (future)
│   ├── data-flow.md              # Data flow documentation (future)
│   ├── security.md               # Security documentation (future)
│   ├── development.md            # Development guidelines (future)
│   ├── testing.md                # Testing documentation (future)
│   └── troubleshooting.md        # Troubleshooting guide (future)
├── requirements.txt              # Root-level dependencies
├── .gitignore                    # Git ignore rules
└── README.md                     # This file
```

## 🚀 Quick Start

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

## 🧪 Testing

### Run All Tests

```bash
# Install test dependencies
pip install pytest pytest-mock

# Run all tests
python -m pytest tests/ -v
```

### Run Specific Test Categories

```bash
# Run only unit tests
python -m pytest tests/ -m unit -v

# Run only integration tests
python -m pytest tests/ -m integration -v

# Run tests for specific function
python -m pytest tests/test_functions/test_news_alerter.py -v
```

### Test Email Functionality

```bash
# Test email report generation
python tests/test_email.py all    # All entities have important articles
python tests/test_email.py some   # Only one entity has important articles
python tests/test_email.py none   # No important articles
```

## 📧 Email Commands

Once deployed, manage entities via email:

- **ADD entity_name**: Add an entity to monitoring
- **DELETE entity_name**: Remove an entity from monitoring
- **LIST**: List all monitored entities

Send emails to: `reports@yourdomain.com`

## 🔧 Configuration

### Environment Configuration

All configuration is managed through the `config/` directory:

- `env.json` - Production configuration (not in version control)
- `env.example.json` - Template configuration
- `samconfig.toml` - SAM deployment configuration

### Security

- Never commit `env.json` or `env.local.json` to version control
- Keep API keys and credentials secure
- Use environment variables in production deployments
- Regularly rotate API keys and credentials

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Deployment Guide](docs/deployment.md)** - Complete deployment instructions
- **[API Reference](docs/api-reference.md)** - Function specifications and usage
- **[Configuration Guide](config/README.md)** - Configuration setup and security
- **[Scripts Documentation](scripts/README.md)** - Deployment and utility scripts

## 🏗️ Architecture

### Lambda Functions

- **newsAlerter**: Main orchestration function triggered by EventBridge
- **worker**: Article processing and sentiment analysis
- **handleTable**: DynamoDB table management operations
- **emailControls**: Email command processing via S3 triggers

### AWS Services

- **Lambda**: Serverless function execution
- **DynamoDB**: Entity tracking and analysis storage
- **S3**: Email storage and static asset hosting
- **SES**: Email processing and delivery
- **EventBridge**: Scheduled execution
- **ECR**: Container image repositories

## 🔄 Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/ -v

# Test individual functions
python src/functions/news_alerter/handler.py
```

### Code Organization

- **Functions**: Each Lambda function is self-contained with its own dependencies
- **Shared Modules**: Common utilities shared across functions
- **Tests**: Comprehensive test suites for each function
- **Documentation**: Detailed documentation for all components

## 🚨 Troubleshooting

### Common Issues

1. **Docker Build Failures**: Ensure Docker is running and check Dockerfile syntax
2. **Lambda Invocation Errors**: Check CloudWatch logs and verify IAM permissions
3. **Email Processing Issues**: Verify SES domain verification and S3 permissions
4. **API Key Errors**: Check API key validity and quotas

### Debug Commands

```bash
# Check Lambda function status
aws lambda get-function --function-name newsAlerter

# View recent logs
aws logs tail /aws/lambda/newsAlerter --since 1h

# Test DynamoDB connectivity
aws dynamodb list-tables
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For issues and questions:
1. Check the [troubleshooting guide](docs/troubleshooting.md)
2. Review existing GitHub issues
3. Create a new issue with detailed information
