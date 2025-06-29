# Configuration Directory

This directory contains all configuration files for the GargoyleScope application.

## Files

- `env.json` - Production environment configuration (contains sensitive data)
- `env.local.json` - Local development environment configuration
- `env.example.json` - Example configuration template (no sensitive data)
- `samconfig.toml` - SAM (Serverless Application Model) configuration

## Environment Configuration

### env.example.json
This is a template file that shows the required configuration structure without exposing sensitive data. Use this as a starting point for your own configuration.

### env.json
Contains the actual production configuration with real API keys and credentials. This file should never be committed to version control.

### env.local.json
Contains local development configuration. This file should never be committed to version control.

## Setup

1. Copy the example configuration:
```bash
cp config/env.example.json config/env.json
```

2. Edit `config/env.json` with your actual values:
   - `OPENAI_API_KEY` - Your OpenAI API key
   - `GOOGLE_API_KEY` - Your Google Custom Search API key
   - `GOOGLE_CSE_ID` - Your Google Custom Search Engine ID
   - `GOOGLE_CREDENTIALS` - Your Google service account credentials
   - `EMAIL_FROM` - Sender email address
   - `EMAIL_TO` - Recipient email address

## Security

- Never commit `env.json` or `env.local.json` to version control
- Keep API keys and credentials secure
- Use environment variables in production deployments
- Regularly rotate API keys and credentials 