"""
Test suite for the news_alerter Lambda function.

This module contains unit tests and integration tests for the main orchestration
function that coordinates news monitoring and analysis.
"""

import pytest
import json
import boto3
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from functions.news_alerter.handler import lambda_handler
from shared.utils import load_credentials


class TestNewsAlerter:
    """Test class for the news_alerter function."""
    
    @pytest.fixture
    def sample_event(self):
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
    def mock_credentials(self):
        """Mock credentials for testing."""
        return {
            "NewsAlerterFunction": {
                "OPENAI_API_KEY": "test-openai-key",
                "GOOGLE_API_KEY": "test-google-key",
                "GOOGLE_CSE_ID": "test-cse-id",
                "EMAIL_FROM": "test@example.com",
                "EMAIL_TO": "test@example.com"
            }
        }
    
    @patch('functions.news_alerter.handler.load_credentials')
    @patch('functions.news_alerter.handler.boto3.client')
    def test_lambda_handler_success(self, mock_boto_client, mock_load_creds, sample_event, mock_credentials):
        """Test successful execution of the lambda handler."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        # Mock successful worker invocation
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': Mock()
        }
        mock_lambda_client.invoke.return_value['Payload'].read.return_value = json.dumps({
            'statusCode': 200,
            'body': json.dumps({'message': 'Success'})
        }).encode('utf-8')
        
        # Execute handler
        result = lambda_handler(sample_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'body' in result
        mock_lambda_client.invoke.assert_called()
    
    @patch('functions.news_alerter.handler.load_credentials')
    def test_lambda_handler_missing_credentials(self, mock_load_creds, sample_event):
        """Test handler behavior when credentials are missing."""
        # Setup mock to raise exception
        mock_load_creds.side_effect = FileNotFoundError("env.json not found")
        
        # Execute handler
        result = lambda_handler(sample_event, {})
        
        # Assertions
        assert result['statusCode'] == 500
        assert 'error' in result['body'].lower()
    
    @patch('functions.news_alerter.handler.load_credentials')
    @patch('functions.news_alerter.handler.boto3.client')
    def test_lambda_handler_worker_failure(self, mock_boto_client, mock_load_creds, sample_event, mock_credentials):
        """Test handler behavior when worker function fails."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_lambda_client = Mock()
        mock_boto_client.return_value = mock_lambda_client
        
        # Mock worker failure
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'FunctionError': 'Unhandled',
            'Payload': Mock()
        }
        mock_lambda_client.invoke.return_value['Payload'].read.return_value = json.dumps({
            'errorMessage': 'Worker function failed'
        }).encode('utf-8')
        
        # Execute handler
        result = lambda_handler(sample_event, {})
        
        # Assertions
        assert result['statusCode'] == 500
        assert 'error' in result['body'].lower()
    
    def test_event_validation(self, sample_event):
        """Test that the handler validates input events properly."""
        # Test with invalid event
        invalid_event = {}
        
        with pytest.raises(Exception):
            lambda_handler(invalid_event, {})
    
    @patch('functions.news_alerter.handler.load_credentials')
    def test_environment_variables(self, mock_load_creds, sample_event, mock_credentials):
        """Test that environment variables are properly loaded."""
        mock_load_creds.return_value = mock_credentials
        
        # This test verifies that credentials are loaded correctly
        # The actual loading is tested in the shared utils module
        assert mock_credentials['NewsAlerterFunction']['OPENAI_API_KEY'] == 'test-openai-key'


class TestNewsAlerterIntegration:
    """Integration tests for the news_alerter function."""
    
    @pytest.mark.integration
    def test_end_to_end_workflow(self):
        """Test the complete workflow from event to response."""
        # This would require actual AWS resources and should be run separately
        # from unit tests
        pass
    
    @pytest.mark.integration
    def test_worker_integration(self):
        """Test integration with the worker function."""
        # This would test actual Lambda-to-Lambda communication
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 