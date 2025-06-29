"""
Pytest configuration and common fixtures for GargoyleScope tests.

This module provides shared fixtures and configuration for all test modules.
"""

import pytest
import json
import os
import sys
from unittest.mock import Mock, patch

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))


@pytest.fixture(scope="session")
def test_credentials():
    """Test credentials for all tests."""
    return {
        "NewsAlerterFunction": {
            "OPENAI_API_KEY": "test-openai-key",
            "GOOGLE_API_KEY": "test-google-key",
            "GOOGLE_CSE_ID": "test-cse-id",
            "EMAIL_FROM": "test@example.com",
            "EMAIL_TO": "test@example.com"
        },
        "WorkerFunction": {
            "OPENAI_API_KEY": "test-openai-key",
            "GOOGLE_API_KEY": "test-google-key",
            "GOOGLE_CSE_ID": "test-cse-id"
        },
        "HandleTableFunction": {
            "AWS_REGION": "us-west-1"
        },
        "EmailControlsFunction": {
            "AWS_REGION": "us-west-1"
        }
    }


@pytest.fixture
def sample_eventbridge_event():
    """Sample EventBridge event for testing."""
    return {
        "version": "0",
        "id": "test-event-id",
        "detail-type": "Scheduled Event",
        "source": "aws.events",
        "account": "123456789012",
        "time": "2024-01-01T00:00:00Z",
        "region": "us-west-1",
        "resources": ["arn:aws:events:us-west-1:123456789012:rule/test-rule"],
        "detail": {}
    }


@pytest.fixture
def sample_s3_event():
    """Sample S3 event for testing."""
    return {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {
                        "name": "gargoylescope-incoming-emails"
                    },
                    "object": {
                        "key": "test-email.eml"
                    }
                }
            }
        ]
    }


@pytest.fixture
def sample_lambda_context():
    """Sample Lambda context for testing."""
    context = Mock()
    context.aws_request_id = "test-request-id"
    context.function_name = "test-function"
    context.function_version = "1"
    context.invoked_function_arn = "arn:aws:lambda:us-west-1:123456789012:function:test-function"
    context.memory_limit_in_mb = 512
    context.remaining_time_in_millis = lambda: 30000
    return context


@pytest.fixture
def mock_boto3_clients():
    """Mock boto3 clients for testing."""
    with patch('boto3.client') as mock_client:
        # Mock different AWS services
        mock_s3 = Mock()
        mock_lambda = Mock()
        mock_dynamodb = Mock()
        mock_ses = Mock()
        mock_cloudwatch = Mock()
        
        # Configure side effect to return different clients based on service name
        def client_side_effect(service_name, **kwargs):
            if service_name == 's3':
                return mock_s3
            elif service_name == 'lambda':
                return mock_lambda
            elif service_name == 'dynamodb':
                return mock_dynamodb
            elif service_name == 'ses':
                return mock_ses
            elif service_name == 'cloudwatch':
                return mock_cloudwatch
            else:
                return Mock()
        
        mock_client.side_effect = client_side_effect
        
        yield {
            's3': mock_s3,
            'lambda': mock_lambda,
            'dynamodb': mock_dynamodb,
            'ses': mock_ses,
            'cloudwatch': mock_cloudwatch
        }


@pytest.fixture
def sample_article_data():
    """Sample article data for testing."""
    return {
        "title": "Test Article Title",
        "link": "http://example.com/test-article",
        "snippet": "This is a test article snippet for testing purposes."
    }


@pytest.fixture
def sample_analysis_data():
    """Sample analysis data for testing."""
    return {
        "sentiment": "positive",
        "summary": "This is a positive test article about the entity.",
        "important": True
    }


@pytest.fixture
def sample_entity_list():
    """Sample entity list for testing."""
    return ["Rangoon Ruby", "Nordstrom", "Vance Brown Construction"]


@pytest.fixture
def sample_email_content():
    """Sample email content for testing."""
    return """
From: test@example.com
To: reports@gargoylescope.com
Subject: Test Email Commands

ADD Rangoon Ruby
ADD Nordstrom
DELETE Vance Brown Construction
LIST
""".strip()


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response for testing."""
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "sentiment": "positive",
                        "summary": "Test summary",
                        "important": False
                    })
                }
            }
        ]
    }


@pytest.fixture
def mock_google_search_response():
    """Mock Google Custom Search API response for testing."""
    return {
        "items": [
            {
                "title": "Test Article 1",
                "link": "http://example.com/article1",
                "snippet": "Test snippet 1"
            },
            {
                "title": "Test Article 2",
                "link": "http://example.com/article2",
                "snippet": "Test snippet 2"
            }
        ]
    }


@pytest.fixture
def mock_dynamodb_item():
    """Mock DynamoDB item for testing."""
    return {
        "parent_entity": "Stanford",
        "entities": ["Rangoon Ruby", "Nordstrom"],
        "last_updated": "2024-01-01T00:00:00Z"
    }


# Test markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# Test collection hooks
def pytest_collection_modifyitems(config, items):
    """Modify test collection to add default markers."""
    for item in items:
        # Add unit marker to tests that don't have integration marker
        if "integration" not in item.keywords:
            item.add_marker(pytest.mark.unit)
        
        # Add slow marker to integration tests
        if "integration" in item.keywords:
            item.add_marker(pytest.mark.slow)


# Test session setup
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    # Set test environment variables
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-1'
    os.environ['PYTHONPATH'] = os.path.join(os.path.dirname(__file__), '../src')
    
    # Create test directories if they don't exist
    test_dirs = ['fixtures', 'outputs']
    for test_dir in test_dirs:
        os.makedirs(os.path.join(os.path.dirname(__file__), test_dir), exist_ok=True)
    
    yield
    
    # Cleanup after tests
    pass 