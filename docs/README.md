# GargoyleScope Documentation

Welcome to the GargoyleScope documentation. This directory contains comprehensive documentation for the serverless AWS-based news monitoring and analysis system.

## 📚 Documentation Structure

### Core Documentation
- **[README.md](./README.md)** - This file, overview of documentation
- **[deployment.md](./deployment.md)** - Deployment guide and infrastructure setup
- **[api-reference.md](./api-reference.md)** - API documentation and function specifications

### Architecture Documentation
- **[architecture.md](./architecture.md)** - System architecture and design decisions
- **[data-flow.md](./data-flow.md)** - Data flow and processing pipeline
- **[security.md](./security.md)** - Security considerations and best practices

### Development Documentation
- **[development.md](./development.md)** - Development setup and guidelines
- **[testing.md](./testing.md)** - Testing strategy and test execution
- **[troubleshooting.md](./troubleshooting.md)** - Common issues and solutions

## 🚀 Quick Start

1. **Setup**: Follow the [deployment guide](./deployment.md) to set up the infrastructure
2. **Configuration**: Configure your environment using the [configuration guide](../config/README.md)
3. **Testing**: Run tests using the [testing guide](./testing.md)
4. **Development**: Follow the [development guidelines](./development.md)

## 🏗️ System Overview

GargoyleScope is a serverless news monitoring system that:

- **Monitors** news articles for specified entities using Google Custom Search
- **Analyzes** sentiment and importance using OpenAI GPT models
- **Stores** data in DynamoDB for tracking and analysis
- **Reports** findings via HTML email reports
- **Manages** entities through email commands

### Key Components

- **news_alerter**: Main orchestration function
- **worker**: Article processing and analysis
- **handle_table**: DynamoDB table management
- **email_controls**: Email command processing

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed and running
- Python 3.8+ for local development
- OpenAI API key
- Google Custom Search API key and CSE ID

## 🔧 Configuration

All configuration is managed through the `config/` directory:

- `env.json` - Production configuration (not in version control)
- `env.example.json` - Template configuration
- `samconfig.toml` - SAM deployment configuration

## 🧪 Testing

The project includes comprehensive test suites:

- **Unit tests**: Test individual function logic
- **Integration tests**: Test AWS service interactions
- **End-to-end tests**: Test complete workflows

Run tests with:
```bash
python -m pytest tests/ -v
```

## 📖 Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Google Custom Search API](https://developers.google.com/custom-search)

## 🤝 Contributing

Please read the [development guidelines](./development.md) before contributing to the project.

## 📞 Support

For issues and questions:
1. Check the [troubleshooting guide](./troubleshooting.md)
2. Review existing GitHub issues
3. Create a new issue with detailed information

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details. 