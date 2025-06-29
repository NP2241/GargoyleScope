import boto3
import os
import json
import email
from email import policy
from email.mime.text import MIMEText

from shared.utils import load_credentials
from shared.database import get_dynamodb_resource, add_entities_to_table, delete_entities_from_table, list_entities_from_table
from shared.email_helpers import send_confirmation_email, send_list_email

def get_authorized_sender_info(sender_email: str) -> dict:
    """
    Check if sender is authorized and get their parent entity
    
    Args:
        sender_email (str): Email address of sender
        
    Returns:
        dict: Contains authorization status and parent entity if authorized
    """
    try:
        dynamodb = get_dynamodb_resource()
        table = dynamodb.Table('EmailList')
        
        # Scan table to find which parent entity this email belongs to
        response = table.scan()
        items = response['Items']
        
        # Handle pagination if needed
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        # Check each parent entity's email list
        for item in items:
            if sender_email in item['email_list']:
                return {
                    'authorized': True,
                    'parent_entity': item['parent_entity']
                }
        
        return {
            'authorized': False,
            'parent_entity': None
        }
        
    except Exception as e:
        print(f"Error checking sender authorization: {str(e)}")
        return {
            'authorized': False,
            'parent_entity': None
        }

def parse_commands(email_content: str) -> dict:
    """Parse email content for ADD, DELETE, and LIST commands"""
    try:
        add_entities = []
        delete_entities = []
        list_requested = False
        
        # Split content into lines and process each line
        lines = email_content.splitlines()
        for line in lines:
            line = line.strip().upper()
            if line.startswith('ADD '):
                entity = line[4:].strip()
                if entity:
                    add_entities.append(entity)
            elif line.startswith('DELETE '):
                entity = line[7:].strip()
                if entity:
                    delete_entities.append(entity)
            elif line == 'LIST':
                list_requested = True
        
        return {
            'add': add_entities,
            'delete': delete_entities,
            'list': list_requested
        }
        
    except Exception as e:
        print(f"Error parsing email commands: {str(e)}")
        return {'add': [], 'delete': [], 'list': False}

def process_email(event, context):
    try:
        # Initialize S3 client
        s3 = boto3.client('s3', region_name=os.getenv('REGION', 'us-west-1'))

        # Initialize Lambda client
        lambda_client = boto3.client('lambda', region_name=os.getenv('REGION', 'us-west-1'))

        # Get S3 info from event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        # Get email from S3
        email_obj = s3.get_object(Bucket=bucket, Key=key)
        email_content = email_obj['Body'].read().decode('utf-8')
        
        # Parse email
        msg = email.message_from_string(email_content, policy=policy.default)
        
        # Get sender
        sender = msg.get('from')
        if not sender:
            print("No sender found in email")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No sender found in email'})
            }
        
        # Extract email address from sender field
        if '<' in sender and '>' in sender:
            sender_email = sender.split('<')[1].split('>')[0]
        else:
            sender_email = sender.strip()
        
        print(f"Processing email from: {sender_email}")
        
        # Check if sender is authorized
        auth_info = get_authorized_sender_info(sender_email)
        if not auth_info['authorized']:
            print(f"Unauthorized sender: {sender_email}")
            return {
                'statusCode': 403,
                'body': json.dumps({'error': 'Unauthorized sender'})
            }
        
        parent_entity = auth_info['parent_entity']
        print(f"Authorized sender for parent entity: {parent_entity}")
        
        # Get email body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_content()
                    break
        else:
            body = msg.get_content()
        
        if not body:
            print("No text content found in email")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No text content found in email'})
            }
        
        # Parse commands
        commands = parse_commands(body)
        print(f"Parsed commands: {commands}")
        
        # Process commands
        add_results = None
        delete_results = None
        list_entities_result = None
        
        # Handle ADD commands
        if commands['add']:
            print(f"Adding entities: {commands['add']}")
            add_results = add_entities_to_table(parent_entity, commands['add'])
        
        # Handle DELETE commands
        if commands['delete']:
            print(f"Deleting entities: {commands['delete']}")
            delete_results = delete_entities_from_table(parent_entity, commands['delete'])
        
        # Handle LIST command
        if commands['list']:
            print("Listing entities")
            entities_data = list_entities_from_table(parent_entity)
            list_entities_result = [entity['entity_name'] for entity in entities_data]
        
        # Send confirmation email
        if add_results or delete_results:
            send_confirmation_email(sender_email, msg, add_results, delete_results)
        
        # Send list email if requested
        if list_entities_result is not None:
            send_list_email(sender_email, msg, list_entities_result)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Email processed successfully',
                'add_results': add_results,
                'delete_results': delete_results,
                'list_entities': list_entities_result
            })
        }
        
    except Exception as e:
        error_message = f"Error processing email: {str(e)}"
        print(f"❌ {error_message}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        } 