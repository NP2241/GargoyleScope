"""
Test suite for the worker Lambda function.

This module contains unit tests and integration tests for the worker function
that processes news articles and performs sentiment analysis.
"""

import pytest
import json
import boto3
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from functions.worker.handler import lambda_handler
from shared.utils import load_credentials


class TestWorker:
    """Test class for the worker function."""
    
    @pytest.fixture
    def sample_event(self):
        """Sample event for testing worker function."""
        return {
            "parent_entity": "Stanford",
            "entities": ["Rangoon Ruby", "Nordstrom"],
            "google_api_key": "test-google-key",
            "google_cse_id": "test-cse-id",
            "openai_api_key": "test-openai-key"
        }
    
    @pytest.fixture
    def mock_credentials(self):
        """Mock credentials for testing."""
        return {
            "WorkerFunction": {
                "OPENAI_API_KEY": "test-openai-key",
                "GOOGLE_API_KEY": "test-google-key",
                "GOOGLE_CSE_ID": "test-cse-id"
            }
        }
    
    @patch('functions.worker.handler.load_credentials')
    @patch('functions.worker.handler.boto3.client')
    def test_lambda_handler_success(self, mock_boto_client, mock_load_creds, sample_event, mock_credentials):
        """Test successful execution of the worker lambda handler."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock DynamoDB responses
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'entities': ['Rangoon Ruby', 'Nordstrom']
            }
        }
        
        # Mock Google Search API response
        with patch('functions.worker.handler.requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'items': [
                    {
                        'title': 'Test Article',
                        'link': 'http://example.com/test',
                        'snippet': 'Test snippet'
                    }
                ]
            }
            mock_get.return_value.status_code = 200
            
            # Mock OpenAI API response
            with patch('functions.worker.handler.openai.ChatCompletion.create') as mock_openai:
                mock_openai.return_value = Mock(
                    choices=[Mock(message=Mock(content='{"sentiment": "positive", "summary": "Test summary", "important": false}'))]
                )
                
                # Execute handler
                result = lambda_handler(sample_event, {})
                
                # Assertions
                assert result['statusCode'] == 200
                assert 'body' in result
                mock_dynamodb.get_item.assert_called()
                mock_get.assert_called()
                mock_openai.assert_called()
    
    @patch('functions.worker.handler.load_credentials')
    def test_lambda_handler_missing_credentials(self, mock_load_creds, sample_event):
        """Test handler behavior when credentials are missing."""
        # Setup mock to raise exception
        mock_load_creds.side_effect = FileNotFoundError("env.json not found")
        
        # Execute handler
        result = lambda_handler(sample_event, {})
        
        # Assertions
        assert result['statusCode'] == 500
        assert 'error' in result['body'].lower()
    
    @patch('functions.worker.handler.load_credentials')
    @patch('functions.worker.handler.boto3.client')
    def test_lambda_handler_no_entities(self, mock_boto_client, mock_load_creds, sample_event, mock_credentials):
        """Test handler behavior when no entities are found."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock empty entities list
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'entities': []
            }
        }
        
        # Execute handler
        result = lambda_handler(sample_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'No entities found' in result['body']
    
    @patch('functions.worker.handler.load_credentials')
    @patch('functions.worker.handler.boto3.client')
    def test_lambda_handler_google_api_error(self, mock_boto_client, mock_load_creds, sample_event, mock_credentials):
        """Test handler behavior when Google API fails."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock DynamoDB response
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'entities': ['Rangoon Ruby']
            }
        }
        
        # Mock Google API error
        with patch('functions.worker.handler.requests.get') as mock_get:
            mock_get.side_effect = Exception("Google API error")
            
            # Execute handler
            result = lambda_handler(sample_event, {})
            
            # Assertions
            assert result['statusCode'] == 500
            assert 'error' in result['body'].lower()
    
    @patch('functions.worker.handler.load_credentials')
    @patch('functions.worker.handler.boto3.client')
    def test_lambda_handler_openai_api_error(self, mock_boto_client, mock_load_creds, sample_event, mock_credentials):
        """Test handler behavior when OpenAI API fails."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock DynamoDB response
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'entities': ['Rangoon Ruby']
            }
        }
        
        # Mock Google Search API response
        with patch('functions.worker.handler.requests.get') as mock_get:
            mock_get.return_value.json.return_value = {
                'items': [
                    {
                        'title': 'Test Article',
                        'link': 'http://example.com/test',
                        'snippet': 'Test snippet'
                    }
                ]
            }
            mock_get.return_value.status_code = 200
            
            # Mock OpenAI API error
            with patch('functions.worker.handler.openai.ChatCompletion.create') as mock_openai:
                mock_openai.side_effect = Exception("OpenAI API error")
                
                # Execute handler
                result = lambda_handler(sample_event, {})
                
                # Assertions
                assert result['statusCode'] == 500
                assert 'error' in result['body'].lower()
    
    def test_article_processing(self):
        """Test individual article processing logic."""
        # This would test the article processing and analysis logic
        # without requiring external API calls
        pass
    
    def test_sentiment_analysis(self):
        """Test sentiment analysis functionality."""
        # This would test the sentiment analysis logic
        pass


class TestWorkerIntegration:
    """Integration tests for the worker function."""
    
    @pytest.mark.integration
    def test_google_search_integration(self):
        """Test integration with Google Custom Search API."""
        # This would require actual Google API credentials
        pass
    
    @pytest.mark.integration
    def test_openai_integration(self):
        """Test integration with OpenAI API."""
        # This would require actual OpenAI API credentials
        pass
    
    @pytest.mark.integration
    def test_dynamodb_integration(self):
        """Test integration with DynamoDB."""
        # This would require actual DynamoDB access
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 