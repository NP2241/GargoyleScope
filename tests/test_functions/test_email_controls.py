"""
Test suite for the email_controls Lambda function.

This module contains unit tests and integration tests for the email_controls function
that processes email commands for entity management.
"""

import pytest
import json
import boto3
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add the src directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from functions.email_controls.handler import lambda_handler
from shared.utils import load_credentials


class TestEmailControls:
    """Test class for the email_controls function."""
    
    @pytest.fixture
    def s3_event(self):
        """Sample S3 event for testing email processing."""
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
    def mock_credentials(self):
        """Mock credentials for testing."""
        return {
            "EmailControlsFunction": {
                "AWS_REGION": "us-west-1"
            }
        }
    
    @patch('functions.email_controls.handler.load_credentials')
    @patch('functions.email_controls.handler.boto3.client')
    def test_lambda_handler_s3_event_success(self, mock_boto_client, mock_load_creds, s3_event, mock_credentials):
        """Test successful processing of S3 event."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_s3 = Mock()
        mock_lambda_client = Mock()
        mock_boto_client.side_effect = [mock_s3, mock_lambda_client]
        
        # Mock S3 object retrieval
        mock_s3.get_object.return_value = {
            'Body': Mock(
                read=lambda: b"""
From: test@example.com
To: reports@gargoylescope.com
Subject: Test Email

ADD Rangoon Ruby
                """.strip()
            )
        }
        
        # Mock successful Lambda invocation
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': Mock()
        }
        mock_lambda_client.invoke.return_value['Payload'].read.return_value = json.dumps({
            'statusCode': 200,
            'body': json.dumps({'message': 'Entity added successfully'})
        }).encode('utf-8')
        
        # Execute handler
        result = lambda_handler(s3_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'Email processed successfully' in result['body']
        mock_s3.get_object.assert_called_once()
        mock_lambda_client.invoke.assert_called_once()
    
    @patch('functions.email_controls.handler.load_credentials')
    @patch('functions.email_controls.handler.boto3.client')
    def test_lambda_handler_add_command(self, mock_boto_client, mock_load_creds, s3_event, mock_credentials):
        """Test processing of ADD command."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_s3 = Mock()
        mock_lambda_client = Mock()
        mock_boto_client.side_effect = [mock_s3, mock_lambda_client]
        
        # Mock S3 object with ADD command
        mock_s3.get_object.return_value = {
            'Body': Mock(
                read=lambda: b"""
From: test@example.com
To: reports@gargoylescope.com
Subject: Add Entity

ADD Rangoon Ruby
ADD Nordstrom
                """.strip()
            )
        }
        
        # Mock successful Lambda invocation
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': Mock()
        }
        mock_lambda_client.invoke.return_value['Payload'].read.return_value = json.dumps({
            'statusCode': 200,
            'body': json.dumps({'message': 'Entities added successfully'})
        }).encode('utf-8')
        
        # Execute handler
        result = lambda_handler(s3_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'Email processed successfully' in result['body']
        # Should be called twice for two ADD commands
        assert mock_lambda_client.invoke.call_count == 2
    
    @patch('functions.email_controls.handler.load_credentials')
    @patch('functions.email_controls.handler.boto3.client')
    def test_lambda_handler_delete_command(self, mock_boto_client, mock_load_creds, s3_event, mock_credentials):
        """Test processing of DELETE command."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_s3 = Mock()
        mock_lambda_client = Mock()
        mock_boto_client.side_effect = [mock_s3, mock_lambda_client]
        
        # Mock S3 object with DELETE command
        mock_s3.get_object.return_value = {
            'Body': Mock(
                read=lambda: b"""
From: test@example.com
To: reports@gargoylescope.com
Subject: Delete Entity

DELETE Rangoon Ruby
                """.strip()
            )
        }
        
        # Mock successful Lambda invocation
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': Mock()
        }
        mock_lambda_client.invoke.return_value['Payload'].read.return_value = json.dumps({
            'statusCode': 200,
            'body': json.dumps({'message': 'Entity deleted successfully'})
        }).encode('utf-8')
        
        # Execute handler
        result = lambda_handler(s3_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'Email processed successfully' in result['body']
        mock_lambda_client.invoke.assert_called_once()
    
    @patch('functions.email_controls.handler.load_credentials')
    @patch('functions.email_controls.handler.boto3.client')
    def test_lambda_handler_list_command(self, mock_boto_client, mock_load_creds, s3_event, mock_credentials):
        """Test processing of LIST command."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_s3 = Mock()
        mock_lambda_client = Mock()
        mock_boto_client.side_effect = [mock_s3, mock_lambda_client]
        
        # Mock S3 object with LIST command
        mock_s3.get_object.return_value = {
            'Body': Mock(
                read=lambda: b"""
From: test@example.com
To: reports@gargoylescope.com
Subject: List Entities

LIST
                """.strip()
            )
        }
        
        # Mock successful Lambda invocation
        mock_lambda_client.invoke.return_value = {
            'StatusCode': 200,
            'Payload': Mock()
        }
        mock_lambda_client.invoke.return_value['Payload'].read.return_value = json.dumps({
            'statusCode': 200,
            'body': json.dumps({'entities': ['Rangoon Ruby', 'Nordstrom']})
        }).encode('utf-8')
        
        # Execute handler
        result = lambda_handler(s3_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'Email processed successfully' in result['body']
        mock_lambda_client.invoke.assert_called_once()
    
    @patch('functions.email_controls.handler.load_credentials')
    @patch('functions.email_controls.handler.boto3.client')
    def test_lambda_handler_invalid_command(self, mock_boto_client, mock_load_creds, s3_event, mock_credentials):
        """Test processing of invalid command."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_s3 = Mock()
        mock_boto_client.side_effect = [mock_s3]
        
        # Mock S3 object with invalid command
        mock_s3.get_object.return_value = {
            'Body': Mock(
                read=lambda: b"""
From: test@example.com
To: reports@gargoylescope.com
Subject: Invalid Command

INVALID_COMMAND
                """.strip()
            )
        }
        
        # Execute handler
        result = lambda_handler(s3_event, {})
        
        # Assertions
        assert result['statusCode'] == 200
        assert 'No valid commands found' in result['body']
    
    @patch('functions.email_controls.handler.load_credentials')
    @patch('functions.email_controls.handler.boto3.client')
    def test_lambda_handler_s3_error(self, mock_boto_client, mock_load_creds, s3_event, mock_credentials):
        """Test handler behavior when S3 operations fail."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_s3 = Mock()
        mock_boto_client.return_value = mock_s3
        
        # Mock S3 error
        mock_s3.get_object.side_effect = Exception("S3 error")
        
        # Execute handler
        result = lambda_handler(s3_event, {})
        
        # Assertions
        assert result['statusCode'] == 500
        assert 'error' in result['body'].lower()
    
    @patch('functions.email_controls.handler.load_credentials')
    def test_lambda_handler_missing_credentials(self, mock_load_creds, s3_event):
        """Test handler behavior when credentials are missing."""
        # Setup mock to raise exception
        mock_load_creds.side_effect = FileNotFoundError("env.json not found")
        
        # Execute handler
        result = lambda_handler(s3_event, {})
        
        # Assertions
        assert result['statusCode'] == 500
        assert 'error' in result['body'].lower()
    
    @patch('functions.email_controls.handler.load_credentials')
    @patch('functions.email_controls.handler.boto3.client')
    def test_lambda_handler_lambda_invocation_error(self, mock_boto_client, mock_load_creds, s3_event, mock_credentials):
        """Test handler behavior when Lambda invocation fails."""
        # Setup mocks
        mock_load_creds.return_value = mock_credentials
        mock_s3 = Mock()
        mock_lambda_client = Mock()
        mock_boto_client.side_effect = [mock_s3, mock_lambda_client]
        
        # Mock S3 object retrieval
        mock_s3.get_object.return_value = {
            'Body': Mock(
                read=lambda: b"""
From: test@example.com
To: reports@gargoylescope.com
Subject: Test Email

ADD Rangoon Ruby
                """.strip()
            )
        }
        
        # Mock Lambda invocation error
        mock_lambda_client.invoke.side_effect = Exception("Lambda invocation error")
        
        # Execute handler
        result = lambda_handler(s3_event, {})
        
        # Assertions
        assert result['statusCode'] == 500
        assert 'error' in result['body'].lower()
    
    def test_email_parsing(self):
        """Test email parsing logic."""
        # This would test the email parsing functionality
        pass
    
    def test_command_extraction(self):
        """Test command extraction from email body."""
        # This would test command extraction logic
        pass


class TestEmailControlsIntegration:
    """Integration tests for the email_controls function."""
    
    @pytest.mark.integration
    def test_s3_integration(self):
        """Test integration with actual S3."""
        # This would require actual S3 access
        pass
    
    @pytest.mark.integration
    def test_lambda_integration(self):
        """Test integration with actual Lambda functions."""
        # This would test actual Lambda-to-Lambda communication
        pass
    
    @pytest.mark.integration
    def test_email_workflow(self):
        """Test complete email processing workflow."""
        # This would test the complete email processing pipeline
        pass


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"]) 