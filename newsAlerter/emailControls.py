import boto3
import os
import json
import email
from email import policy
from email.mime.text import MIMEText

# Load credentials from env.json
def load_credentials():
    try:
        with open('env.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # In Lambda, use environment variables
        return {
            'REGION': os.environ.get('REGION', 'us-west-1')
        }

def get_authorized_sender_info(sender_email: str) -> dict:
    """
    Check if sender is authorized and get their parent entity
    
    Args:
        sender_email (str): Email address of sender
        
    Returns:
        dict: Contains authorization status and parent entity if authorized
    """
    try:
        credentials = load_credentials()
        dynamodb = boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
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

def send_confirmation_email(sender: str, original_message: email.message.EmailMessage, add_results: dict = None, delete_results: dict = None):
    """Send confirmation email about added/deleted entities"""
    try:
        # Create message content
        message = ""
        
        # Handle additions
        if add_results and add_results.get('added_entities'):
            entities = sorted(add_results['added_entities'])  # Sort alphabetically
            message += f"Added {len(entities)} entities:\n"
            for entity in entities:
                message += f"• {entity}\n"
            message += "\n"
            
        # Handle deletions
        if delete_results and delete_results.get('deleted_entities'):
            entities = sorted(delete_results['deleted_entities'])  # Sort alphabetically
            message += f"Deleted {len(entities)} entities:\n"
            for entity in entities:
                message += f"• {entity}\n"
        
        if not message:
            return  # No changes to report
            
        # Create SES client
        ses = boto3.client('ses', region_name=os.getenv('REGION', 'us-west-1'))
        
        # Create email message with headers for threading
        msg = MIMEText(message)
        msg['Subject'] = 'Re: ' + (original_message['subject'] or 'Entity Updates Confirmation')
        msg['From'] = "reports@gargoylescope.com"
        msg['To'] = sender
        
        # Add threading headers
        if original_message['message-id']:
            msg['References'] = original_message['message-id']
            msg['In-Reply-To'] = original_message['message-id']
        
        # Send email
        ses.send_raw_email(
            Source=msg['From'],
            Destinations=[sender],
            RawMessage={'Data': msg.as_string()}
        )
        
    except Exception as e:
        print(f"Error sending confirmation email: {str(e)}")

def send_list_email(sender: str, original_message: email.message.EmailMessage, entities: list):
    """Send email with list of tracked entities"""
    try:
        # Sort entities alphabetically
        sorted_entities = sorted(entities)
        
        # Create message content
        message = f"You are tracking {len(sorted_entities)} entities:\n\n"
        for entity in sorted_entities:
            message += f"• {entity}\n"
            
        # Create SES client
        ses = boto3.client('ses', region_name=os.getenv('REGION', 'us-west-1'))
        
        # Create email message with headers for threading
        msg = MIMEText(message)
        msg['Subject'] = 'Re: ' + (original_message['subject'] or 'Entity List')
        msg['From'] = "reports@gargoylescope.com"
        msg['To'] = sender
        
        # Add threading headers
        if original_message['message-id']:
            msg['References'] = original_message['message-id']
            msg['In-Reply-To'] = original_message['message-id']
        
        # Send email
        ses.send_raw_email(
            Source=msg['From'],
            Destinations=[sender],
            RawMessage={'Data': msg.as_string()}
        )
        
    except Exception as e:
        print(f"Error sending list email: {str(e)}")

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
        if not commands['add'] and not commands['delete'] and not commands['list']:
            print("No valid commands found in email")
            return
            
        # Call handleTable lambda to process commands
        lambda_client = boto3.client('lambda')
        
        # Process ADD/DELETE commands and send confirmation if needed
        add_response = None
        delete_response = None
        if commands['add'] or commands['delete']:
            # Process ADD commands
            if commands['add']:
                response = lambda_client.invoke(
                    FunctionName='handleTable',
                    InvocationType='RequestResponse',
                    Payload=json.dumps({
                        'action': 'add',
                        'parent_entity': auth_info['parent_entity'],
                        'entities': commands['add']
                    })
                )
                add_response = json.loads(json.loads(response['Payload'].read())['body'])
            
            # Process DELETE commands
            if commands['delete']:
                response = lambda_client.invoke(
                    FunctionName='handleTable',
                    InvocationType='RequestResponse',
                    Payload=json.dumps({
                        'action': 'delete',
                        'parent_entity': auth_info['parent_entity'],
                        'entities': commands['delete']
                    })
                )
                delete_response = json.loads(json.loads(response['Payload'].read())['body'])
            
            # Send confirmation email
            send_confirmation_email(sender, msg, add_response, delete_response)
        
        # Process LIST command if requested
        if commands['list']:
            response = lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'action': 'list',
                    'parent_entity': auth_info['parent_entity']
                })
            )
            list_response = json.loads(json.loads(response['Payload'].read())['body'])
            entities = [entity['entity_name'] for entity in list_response['entities']]
            send_list_email(sender, msg, entities)
        
        print(f"Successfully processed commands from {sender}")
        
    except Exception as e:
        print(f"Error processing email: {str(e)}")
        # We still return successfully to avoid retries
        return 