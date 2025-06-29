"""
Test suite for the handle_table Lambda function.

This module contains unit tests and integration tests for the handle_table function
that manages DynamoDB table operations for entity tracking.
"""

import pytest
import json
import boto3
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from functions.handle_table.handler import lambda_handler
from shared.utils import load_credentials


class TestHandleTable:
    """Test class for the handle_table function."""
    
    @pytest.fixture
    def setup_event(self):
        """Sample event for testing table setup."""
        return {
            "action": "setup",
            "parent_entity": "Stanford"
        }
    
    @pytest.fixture
    def add_event(self):
        """Sample event for testing entity addition."""
        return {
            "action": "add",
            "parent_entity": "Stanford",
            "entities": ["Rangoon Ruby", "Nordstrom"]
        }
    
    @pytest.fixture
    def list_event(self):
        """Sample event for testing entity listing."""
        return {
            "action": "list",
            "parent_entity": "Stanford"
        }
    
    @pytest.fixture
    def delete_event(self):
        """Sample event for testing entity deletion."""
        return {
            "action": "delete",
            "parent_entity": "Stanford",
            "entities": ["Rangoon Ruby"]
        }
    
    @pytest.fixture
    def mock_credentials(self):
        """Mock credentials for testing."""
        return {
            "HandleTableFunction": {
                "AWS_REGION": "us-west-1"
            }
        }
    
    @patch('functions.handle_table.handler.load_credentials')
    @patch('functions.handle_table.handler.boto3.client')
    def test_lambda_handler_setup_success(self, mock_boto_client, mock_load_creds, setup_event, mock_credentials):
        """Test successful table setup."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock successful table creation
        mock_dynamodb.create_table.return_value = {
            'TableDescription': {
                'TableName': 'Stanford_TrackedEntities',
                'TableStatus': 'CREATING'
            }
        }
        
        # Execute handler
        result = lambda_handler(setup_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'Table created successfully' in result['body']
        mock_dynamodb.create_table.assert_called_once()
    
    @patch('functions.handle_table.handler.load_credentials')
    @patch('functions.handle_table.handler.boto3.client')
    def test_lambda_handler_add_entities_success(self, mock_boto_client, mock_load_creds, add_event, mock_credentials):
        """Test successful entity addition."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock successful item update
        mock_dynamodb.update_item.return_value = {
            'Attributes': {
                'entities': ['Rangoon Ruby', 'Nordstrom']
            }
        }
        
        # Execute handler
        result = lambda_handler(add_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'Entities added successfully' in result['body']
        mock_dynamodb.update_item.assert_called()
    
    @patch('functions.handle_table.handler.load_credentials')
    @patch('functions.handle_table.handler.boto3.client')
    def test_lambda_handler_list_entities_success(self, mock_boto_client, mock_load_creds, list_event, mock_credentials):
        """Test successful entity listing."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock successful item retrieval
        mock_dynamodb.get_item.return_value = {
            'Item': {
                'parent_entity': 'Stanford',
                'entities': ['Rangoon Ruby', 'Nordstrom']
            }
        }
        
        # Execute handler
        result = lambda_handler(list_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        response_body = json.loads(result['body'])
        assert 'entities' in response_body
        assert 'Rangoon Ruby' in response_body['entities']
        assert 'Nordstrom' in response_body['entities']
        mock_dynamodb.get_item.assert_called_once()
    
    @patch('functions.handle_table.handler.load_credentials')
    @patch('functions.handle_table.handler.boto3.client')
    def test_lambda_handler_delete_entities_success(self, mock_boto_client, mock_load_creds, delete_event, mock_credentials):
        """Test successful entity deletion."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock successful item update
        mock_dynamodb.update_item.return_value = {
            'Attributes': {
                'entities': ['Nordstrom']  # Rangoon Ruby removed
            }
        }
        
        # Execute handler
        result = lambda_handler(delete_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'Entities deleted successfully' in result['body']
        mock_dynamodb.update_item.assert_called()
    
    @patch('functions.handle_table.handler.load_credentials')
    def test_lambda_handler_missing_credentials(self, mock_load_creds, setup_event):
        """Test handler behavior when credentials are missing."""
        # Setup mock to raise exception
        mock_load_creds.side_effect = FileNotFoundError("env.json not found")
        
        # Execute handler
        result = lambda_handler(setup_event, {})
        
        # Assertions
        assert result['statusCode'] == 500
        assert 'error' in result['body'].lower()
    
    @patch('functions.handle_table.handler.load_credentials')
    @patch('functions.handle_table.handler.boto3.client')
    def test_lambda_handler_invalid_action(self, mock_boto_client, mock_load_creds, mock_credentials):
        """Test handler behavior with invalid action."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Test with invalid action
        invalid_event = {
            "action": "invalid_action",
            "parent_entity": "Stanford"
        }
        
        # Execute handler
        result = lambda_handler(invalid_event, {})
        
        # Assertions
        assert result['statusCode'] == 400
        assert 'Invalid action' in result['body']
    
    @patch('functions.handle_table.handler.load_credentials')
    @patch('functions.handle_table.handler.boto3.client')
    def test_lambda_handler_missing_parent_entity(self, mock_boto_client, mock_load_creds, mock_credentials):
        """Test handler behavior when parent_entity is missing."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Test with missing parent_entity
        invalid_event = {
            "action": "setup"
        }
        
        # Execute handler
        result = lambda_handler(invalid_event, {})
        
        # Assertions
        assert result['statusCode'] == 400
        assert 'parent_entity' in result['body'].lower()
    
    @patch('functions.handle_table.handler.load_credentials')
    @patch('functions.handle_table.handler.boto3.client')
    def test_lambda_handler_dynamodb_error(self, mock_boto_client, mock_load_creds, setup_event, mock_credentials):
        """Test handler behavior when DynamoDB operations fail."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_dynamodb = Mock()
        mock_boto_client.return_value = mock_dynamodb
        
        # Mock DynamoDB error
        mock_dynamodb.create_table.side_effect = Exception("DynamoDB error")
        
        # Execute handler
        result = lambda_handler(setup_event, {})
        
        # Assertions
        assert result['statusCode'] == 500
        assert 'error' in result['body'].lower()
    
    def test_table_name_generation(self):
        """Test that table names are generated correctly."""
        # This would test the table name generation logic
        pass
    
    def test_entity_validation(self):
        """Test entity validation logic."""
        # This would test entity validation
        pass


class TestHandleTableIntegration:
    """Integration tests for the handle_table function."""
    
    @pytest.mark.integration
    def test_dynamodb_integration(self):
        """Test integration with actual DynamoDB."""
        # This would require actual DynamoDB access
        pass
    
    @pytest.mark.integration
    def test_table_lifecycle(self):
        """Test complete table lifecycle (create, add, list, delete)."""
        # This would test the complete workflow
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 