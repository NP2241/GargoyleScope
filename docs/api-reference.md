# API Reference

This document provides comprehensive API documentation for all GargoyleScope Lambda functions, including input/output specifications, error handling, and usage examples.

## 📋 Table of Contents

- [newsAlerter Function](#newsalerter-function)
- [worker Function](#worker-function)
- [handleTable Function](#handletable-function)
- [emailControls Function](#emailcontrols-function)
- [Error Codes](#error-codes)
- [Common Patterns](#common-patterns)

## 🚀 newsAlerter Function

The main orchestration function that coordinates the news monitoring workflow.

### Function Details
- **Function Name**: `newsAlerter`
- **Runtime**: Python 3.8 (Container)
- **Memory**: 512 MB
- **Timeout**: 5 minutes
- **Trigger**: EventBridge (scheduled)

### Input Event

```json
{
  "version": "0",
  "id": "event-id",
  "detail-type": "Scheduled Event",
  "source": "aws.events",
  "account": "123456789012",
  "time": "2024-01-01T00:00:00Z",
  "region": "us-west-1",
  "resources": ["arn:aws:events:us-west-1:123456789012:rule/daily-news-alert"],
  "detail": {}
}
```

### Output Response

```json
{
  "statusCode": 200,
  "body": "News monitoring completed successfully",
  "headers": {
    "Content-Type": "application/json"
  }
}
```

### Function Flow

1. **Load Configuration**: Read credentials from `env.json`
2. **Invoke Worker**: Call worker function for each entity
3. **Process Results**: Aggregate worker responses
4. **Generate Report**: Create HTML email report
5. **Send Email**: Deliver report via SES

### Error Handling

| Error Code | Description | Resolution |
|------------|-------------|------------|
| 500 | Configuration error | Check `env.json` and API keys |
| 500 | Worker invocation failed | Check worker function logs |
| 500 | Email delivery failed | Verify SES configuration |

### Example Usage

```bash
# Invoke manually
aws lambda invoke \
  --function-name newsAlerter \
  --payload '{}' \
  response.json

# Check logs
aws logs tail /aws/lambda/newsAlerter --follow
```

## 🔧 worker Function

Processes news articles and performs sentiment analysis using OpenAI GPT models.

### Function Details
- **Function Name**: `worker`
- **Runtime**: Python 3.8 (Container)
- **Memory**: 1024 MB
- **Timeout**: 15 minutes
- **Trigger**: Lambda invocation

### Input Event

```json
{
  "parent_entity": "Stanford",
  "entities": ["Rangoon Ruby", "Nordstrom"],
  "google_api_key": "your-google-api-key",
  "google_cse_id": "your-cse-id",
  "openai_api_key": "your-openai-api-key"
}
```

### Output Response

```json
{
  "statusCode": 200,
  "body": {
    "processed_entities": ["Rangoon Ruby", "Nordstrom"],
    "articles_found": 15,
    "articles_analyzed": 12,
    "important_articles": 3,
    "processing_time": "45.2s"
  }
}
```

### Function Flow

1. **Retrieve Entities**: Get entity list from DynamoDB
2. **Search Articles**: Query Google Custom Search API
3. **Analyze Content**: Use OpenAI GPT for sentiment analysis
4. **Store Results**: Save analysis to DynamoDB
5. **Return Summary**: Provide processing statistics

### Error Handling

| Error Code | Description | Resolution |
|------------|-------------|------------|
| 400 | Invalid entity list | Check entity format |
| 500 | Google API error | Verify API key and quota |
| 500 | OpenAI API error | Check API key and model |
| 500 | DynamoDB error | Verify table permissions |

### Example Usage

```bash
# Invoke with test data
aws lambda invoke \
  --function-name worker \
  --payload '{
    "parent_entity": "Stanford",
    "entities": ["Rangoon Ruby"],
    "google_api_key": "test-key",
    "google_cse_id": "test-id",
    "openai_api_key": "test-key"
  }' \
  response.json
```

## 📊 handleTable Function

Manages DynamoDB table operations for entity tracking and analysis storage.

### Function Details
- **Function Name**: `handleTable`
- **Runtime**: Python 3.8 (Container)
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Trigger**: Lambda invocation

### Input Events

#### Setup Table
```json
{
  "action": "setup",
  "parent_entity": "Stanford"
}
```

#### Add Entities
```json
{
  "action": "add",
  "parent_entity": "Stanford",
  "entities": ["Rangoon Ruby", "Nordstrom"]
}
```

#### List Entities
```json
{
  "action": "list",
  "parent_entity": "Stanford"
}
```

#### Delete Entities
```json
{
  "action": "delete",
  "parent_entity": "Stanford",
  "entities": ["Rangoon Ruby"]
}
```

#### Add with Analysis
```json
{
  "action": "add",
  "parent_entity": "Stanford",
  "entities": ["Rangoon Ruby"],
  "analysis": {
    "article": {
      "title": "Article Title",
      "url": "http://example.com/article",
      "snippet": "Article snippet"
    },
    "analysis": {
      "sentiment": "positive",
      "summary": "Article summary",
      "important": true
    }
  },
  "completed": true
}
```

### Output Responses

#### Setup Success
```json
{
  "statusCode": 200,
  "body": "Table Stanford_TrackedEntities created successfully"
}
```

#### List Success
```json
{
  "statusCode": 200,
  "body": {
    "entities": ["Rangoon Ruby", "Nordstrom"],
    "total_count": 2
  }
}
```

#### Add/Delete Success
```json
{
  "statusCode": 200,
  "body": "Entities added/deleted successfully"
}
```

### Function Flow

1. **Validate Action**: Check action type and required parameters
2. **Execute Operation**: Perform DynamoDB operation
3. **Return Result**: Provide operation status and data

### Error Handling

| Error Code | Description | Resolution |
|------------|-------------|------------|
| 400 | Invalid action | Use: setup, add, list, delete |
| 400 | Missing parent_entity | Include parent_entity parameter |
| 500 | DynamoDB error | Check table permissions and status |

### Example Usage

```bash
# Setup table
aws lambda invoke \
  --function-name handleTable \
  --payload '{"action": "setup", "parent_entity": "Stanford"}' \
  response.json

# List entities
aws lambda invoke \
  --function-name handleTable \
  --payload '{"action": "list", "parent_entity": "Stanford"}' \
  response.json

# Add entity
aws lambda invoke \
  --function-name handleTable \
  --payload '{"action": "add", "parent_entity": "Stanford", "entities": ["Rangoon Ruby"]}' \
  response.json
```

## 📧 emailControls Function

Processes email commands for entity management via S3 triggers.

### Function Details
- **Function Name**: `emailControls`
- **Runtime**: Python 3.8 (Container)
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Trigger**: S3 object creation

### Input Event (S3)

```json
{
  "Records": [
    {
      "eventSource": "aws:s3",
      "s3": {
        "bucket": {
          "name": "gargoylescope-incoming-emails"
        },
        "object": {
          "key": "email-123.eml"
        }
      }
    }
  ]
}
```

### Email Commands

#### ADD Command
```
From: user@example.com
To: reports@gargoylescope.com
Subject: Add Entity

ADD Rangoon Ruby
ADD Nordstrom
```

#### DELETE Command
```
From: user@example.com
To: reports@gargoylescope.com
Subject: Delete Entity

DELETE Rangoon Ruby
```

#### LIST Command
```
From: user@example.com
To: reports@gargoylescope.com
Subject: List Entities

LIST
```

### Output Response

```json
{
  "statusCode": 200,
  "body": "Email processed successfully. Commands executed: ADD(2), LIST(1)"
}
```

### Function Flow

1. **Retrieve Email**: Download email from S3
2. **Parse Content**: Extract email body and commands
3. **Execute Commands**: Invoke handleTable function for each command
4. **Return Summary**: Provide processing results

### Error Handling

| Error Code | Description | Resolution |
|------------|-------------|------------|
| 400 | Invalid email format | Check email structure |
| 400 | No valid commands | Use: ADD, DELETE, LIST |
| 500 | S3 access error | Verify bucket permissions |
| 500 | Lambda invocation error | Check handleTable function |

### Example Usage

```bash
# Test with S3 event
aws lambda invoke \
  --function-name emailControls \
  --payload '{
    "Records": [{
      "eventSource": "aws:s3",
      "s3": {
        "bucket": {"name": "gargoylescope-incoming-emails"},
        "object": {"key": "test-email.eml"}
      }
    }]
  }' \
  response.json
```

## ❌ Error Codes

### HTTP Status Codes

| Code | Description | Usage |
|------|-------------|-------|
| 200 | Success | Operation completed successfully |
| 400 | Bad Request | Invalid input parameters |
| 401 | Unauthorized | Missing or invalid credentials |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 500 | Internal Server Error | Server-side error |

### Error Response Format

```json
{
  "statusCode": 500,
  "body": {
    "error": "Error description",
    "error_type": "ValidationError",
    "timestamp": "2024-01-01T00:00:00Z",
    "request_id": "req-123"
  }
}
```

## 🔄 Common Patterns

### Retry Logic

Functions implement exponential backoff for transient failures:

```python
import time
import random

def retry_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            wait_time = (2 ** attempt) + random.uniform(0, 1)
            time.sleep(wait_time)
```

### Logging

All functions use structured logging:

```python
import logging
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_event(event, context):
    logger.info("Function invoked", extra={
        "event": json.dumps(event),
        "request_id": context.aws_request_id,
        "function_name": context.function_name
    })
```

### Response Formatting

Standard response format for all functions:

```python
def format_response(status_code, body, headers=None):
    response = {
        "statusCode": status_code,
        "body": json.dumps(body) if isinstance(body, dict) else body,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        }
    }
    if headers:
        response["headers"].update(headers)
    return response
```

## 📊 Monitoring and Metrics

### CloudWatch Metrics

Each function publishes the following metrics:

- **Invocations**: Number of function invocations
- **Errors**: Number of function errors
- **Duration**: Function execution time
- **Throttles**: Number of throttled invocations

### Custom Metrics

Functions can publish custom metrics:

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_metric(metric_name, value, unit='Count'):
    cloudwatch.put_metric_data(
        Namespace='GargoyleScope',
        MetricData=[{
            'MetricName': metric_name,
            'Value': value,
            'Unit': unit
        }]
    )
```

## 🔒 Security

### IAM Permissions

Each function has minimal required permissions:

- **newsAlerter**: Lambda invoke, SES send
- **worker**: DynamoDB read/write, external API access
- **handleTable**: DynamoDB full access
- **emailControls**: S3 read, Lambda invoke

### Environment Variables

Sensitive data is stored in environment variables:

```python
import os

api_key = os.environ.get('OPENAI_API_KEY')
if not api_key:
    raise ValueError("OPENAI_API_KEY not set")
```

### Input Validation

All functions validate input parameters:

```python
def validate_event(event):
    required_fields = ['action', 'parent_entity']
    for field in required_fields:
        if field not in event:
            raise ValueError(f"Missing required field: {field}")
``` 