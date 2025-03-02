import boto3
import os
import json
import email
from email import policy
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_authorized_sender_info(sender_email: str) -> dict:
    """
    Check if sender is authorized and get their parent entity
    
    Args:
        sender_email (str): Email address of sender
        
    Returns:
        dict: Contains authorization status and parent entity if authorized
    """
    try:
        dynamodb = boto3.resource('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
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
    """
    Parse email content for ADD and DELETE commands
    
    Args:
        email_content (str): Raw email content
        
    Returns:
        dict: Contains two lists - entities to add and delete
    """
    try:
        add_entities = []
        delete_entities = []
        
        # Split content into lines and process each line
        lines = email_content.splitlines()
        for line in lines:
            line = line.strip().upper()
            if line.startswith('ADD '):
                entity = line[4:].strip()  # Remove 'ADD ' and whitespace
                if entity:
                    add_entities.append(entity)
            elif line.startswith('DELETE '):
                entity = line[7:].strip()  # Remove 'DELETE ' and whitespace
                if entity:
                    delete_entities.append(entity)
        
        return {
            'add': add_entities,
            'delete': delete_entities
        }
        
    except Exception as e:
        print(f"Error parsing email commands: {str(e)}")
        return {'add': [], 'delete': []}

def lambda_handler(event, context):
    """
    Process incoming emails from S3 (triggered by SES)
    Only processes emails from authorized senders with valid commands
    """
    try:
        # Get S3 info from event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        # Get email from S3
        s3 = boto3.client('s3')
        email_obj = s3.get_object(Bucket=bucket, Key=key)
        email_content = email_obj['Body'].read().decode('utf-8')
        
        # Parse email
        msg = email.message_from_string(email_content, policy=policy.default)
        
        # Get sender
        sender = msg.get('from')
        if not sender:
            print("No sender found, ignoring email")
            return
            
        # Check if sender is authorized
        auth_info = get_authorized_sender_info(sender)
        if not auth_info['authorized']:
            print(f"Unauthorized sender {sender}, ignoring email")
            return
            
        # Get email body
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
        else:
            body = msg.get_payload(decode=True).decode()
            
        if not body:
            print("No email body found")
            return
        
        # Parse commands from email
        commands = parse_commands(body)
        
        # If no valid commands found, ignore email
        if not commands['add'] and not commands['delete']:
            print("No valid commands found in email")
            return
            
        # Call handleTable lambda to process commands
        lambda_client = boto3.client('lambda')
        
        # Process ADD commands
        if commands['add']:
            lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'action': 'add',
                    'parent_entity': auth_info['parent_entity'],
                    'entities': commands['add']
                })
            )
        
        # Process DELETE commands
        if commands['delete']:
            lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'action': 'delete',
                    'parent_entity': auth_info['parent_entity'],
                    'entities': commands['delete']
                })
            )
        
        print(f"Successfully processed commands from {sender}")
        
    except Exception as e:
        print(f"Error processing email: {str(e)}")
        # We still return successfully to avoid retries
        return 