import os
import json
from openai import OpenAI
import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

# Load credentials from env.json
def load_credentials():
    try:
        with open('env.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # In Lambda, use environment variables
        return {
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'GOOGLE_API_KEY': os.environ.get('GOOGLE_API_KEY'),
            'GOOGLE_CSE_ID': os.environ.get('GOOGLE_CSE_ID'),
            'REGION': os.environ.get('REGION', 'us-west-1')
        }

def send_email_report(html_content: str, subject: str = "News Alert", recipient: str = "neilpendyala@gmail.com"):
    """Send HTML report via SES"""
    try:
        credentials = load_credentials()
        # Check content size
        content_size_kb = len(html_content.encode('utf-8')) / 1024
        if content_size_kb > 100:
            print(f"⚠️ Warning: Email content is {content_size_kb:.1f}KB (recommended max is 100KB)")
            if content_size_kb > 9500:  # Leave some room for headers
                raise Exception(f"Email content too large: {content_size_kb:.1f}KB (max 10MB)")
        
        # Create SES client
        ses = boto3.client('ses', region_name=credentials.get('REGION', 'us-west-1'))
        
        # Create message container
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = "reports@gargoylescope.com"
        msg['To'] = recipient
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Check final message size
        message_size_kb = len(msg.as_string().encode('utf-8')) / 1024
        print(f"📧 Final email size: {message_size_kb:.1f}KB")
        
        # Send email
        response = ses.send_raw_email(
            Source=msg['From'],
            Destinations=[recipient],
            RawMessage={'Data': msg.as_string()}
        )
        
        print(f"✅ Email sent! Message ID: {response['MessageId']}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending email: {str(e)}")
        return False

def generate_html_report(entities_with_analysis):
    """Generate HTML report from analyzed entities, focusing on important articles"""
    try:
        # Read email template
        with open('email_preview.html', 'r') as f:
            template = f.read()
            
        all_analyses_html = ""
        important_found = False
        
        # Process each entity
        for entity in entities_with_analysis:
            entity_name = entity['entity_name']
            analysis_data = entity.get('analysis', {})
            articles = analysis_data.get('articles', [])
            
            # Filter for important articles
            important_articles = [
                article for article in articles 
                if article['analysis'].get('important', False)
            ]
            
            # Skip entity if no important articles
            if not important_articles:
                continue
                
            important_found = True
            
            # Create entity section
            all_analyses_html += f"""
            <tr>
                <td style="padding: 20px;">
                    <div class="entity-box">
                        <h2>{entity_name}</h2>
            """
            
            # Add each important article
            for article in important_articles:
                all_analyses_html += f"""
                <div class="article-box">
                    <h3><a href="{article['url']}">{article['title']}</a></h3>
                    <p><strong>Summary:</strong> {article['analysis']['summary']}</p>
                    <p><strong>Sentiment:</strong> {article['analysis']['sentiment']}</p>
                    <div class="snippet">{article['analysis']['highlighted_text']}</div>
                </div>
                """
            
            all_analyses_html += """
                    </div>
                </td>
            </tr>
            """
        
        if not important_found:
            all_analyses_html = """
            <tr>
                <td style="padding: 20px;">
                    <div class="entity-box">
                        <h2>No Important Updates</h2>
                        <p>No significant news or updates were found for any tracked entities.</p>
                    </div>
                </td>
            </tr>
            """
        
        # Replace template placeholders
        html = template.replace('{{article_content}}', all_analyses_html)
        return html
        
    except Exception as e:
        print(f"Error generating HTML report: {str(e)}")
        raise

def send_error_notification(error_message: str, recipient: str = "neilpendyala@gmail.com"):
    """Send error notification email"""
    try:
        credentials = load_credentials()
        # Create SES client
        ses = boto3.client('ses', region_name=credentials.get('REGION', 'us-west-1'))
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "⚠️ GargoyleScope Alert Failed"
        msg['From'] = "reports@gargoylescope.com"
        msg['To'] = recipient
        
        # Create HTML error message
        html_content = f"""
        <html>
        <body style="font-family: Helvetica, Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
            <div style="background-color: #fff; padding: 20px; border-radius: 5px; border-left: 4px solid #ff6b6b;">
                <h2 style="color: #ff6b6b; margin-top: 0;">Daily News Alert Failed</h2>
                <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} PT</p>
                <p><strong>Error Details:</strong></p>
                <pre style="background-color: #f8f8f8; padding: 15px; border-radius: 4px;">{error_message}</pre>
                <p>Please check the AWS CloudWatch logs for more details.</p>
            </div>
        </body>
        </html>
        """
        
        # Add HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        ses.send_raw_email(
            Source=msg['From'],
            Destinations=[recipient],
            RawMessage={'Data': msg.as_string()}
        )
        
        print(f"Error notification sent to {recipient}")
        
    except Exception as e:
        print(f"Failed to send error notification: {str(e)}")

def batch_entities(entities: list, batch_size: int = 10) -> list:
    """Split list of entities into batches"""
    return [entities[i:i + batch_size] for i in range(0, len(entities), batch_size)]

def setup_email_list(parent_entity: str, initial_emails: list = None):
    """
    Create and initialize email list table for a parent entity
    
    Args:
        parent_entity (str): Name of the parent entity (e.g., "Stanford")
        initial_emails (list): Initial list of emails (defaults to ["neilpendyala@gmail.com"])
    """
    if initial_emails is None:
        initial_emails = ["neilpendyala@gmail.com"]
        
    credentials = load_credentials()
    # Initialize DynamoDB client
    dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    dynamodb_resource = boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
    
    table_name = "EmailList"
    
    try:
        # Create table if it doesn't exist
        try:
            dynamodb.describe_table(TableName=table_name)
        except dynamodb.exceptions.ResourceNotFoundException:
            response = dynamodb.create_table(
                TableName=table_name,
                AttributeDefinitions=[
                    {
                        'AttributeName': 'parent_entity',
                        'AttributeType': 'S'
                    }
                ],
                KeySchema=[
                    {
                        'AttributeName': 'parent_entity',
                        'KeyType': 'HASH'
                    }
                ],
                BillingMode='PAY_PER_REQUEST'
            )
            print(f"Creating email list table...")
            dynamodb.get_waiter('table_exists').wait(TableName=table_name)
            
        # Get table resource
        table = dynamodb_resource.Table(table_name)
        
        # Add/Update email list for parent entity
        table.put_item(
            Item={
                'parent_entity': parent_entity,
                'email_list': initial_emails
            }
        )
        
        print(f"✅ Email list initialized for {parent_entity}")
        
    except Exception as e:
        print(f"Error setting up email list: {str(e)}")
        raise

def get_email_list(parent_entity: str) -> list:
    """Get list of emails for a parent entity"""
    try:
        credentials = load_credentials()
        dynamodb = boto3.resource('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
        table = dynamodb.Table('EmailList')
        
        response = table.get_item(
            Key={
                'parent_entity': parent_entity
            }
        )
        
        if 'Item' not in response:
            # Initialize if not found
            setup_email_list(parent_entity)
            return ["neilpendyala@gmail.com"]
            
        return response['Item']['email_list']
        
    except Exception as e:
        print(f"Error getting email list: {str(e)}")
        return ["neilpendyala@gmail.com"]  # Fallback to default

def lambda_handler(event, context):
    """Lambda handler for article analysis"""
    try:
        credentials = load_credentials()
        # Initialize clients
        dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
        lambda_client = boto3.client('lambda', region_name=credentials.get('REGION', 'us-west-1'))
        
        # Get parent entity from environment or event
        parent_entity = event.get('parent_entity')
        if not parent_entity:
            raise Exception("parent_entity must be provided in event or environment variables")
            
        table_name = f"{parent_entity}_TrackedEntities"
        
        # Check if table exists and create if needed
        try:
            dynamodb.describe_table(TableName=table_name)
            print(f"✅ Table {table_name} exists")
        except dynamodb.exceptions.ResourceNotFoundException:
            print(f"Table {table_name} not found. Creating...")
            # Invoke handleTable lambda to create table
            try:
                response = lambda_client.invoke(
                    FunctionName='handleTable',
                    InvocationType='RequestResponse',
                    Payload=json.dumps({
                        'action': 'setup',
                        'parent_entity': parent_entity
                    })
                )
                
                # Check for lambda execution errors
                if response.get('FunctionError'):
                    error_details = json.loads(response['Payload'].read())
                    raise Exception(f"Table creation lambda failed: {error_details}")
                
                # Parse response
                response_payload = json.loads(response['Payload'].read())
                
                # Check response status
                if response_payload.get('statusCode') != 200:
                    error_body = json.loads(response_payload.get('body', '{}'))
                    raise Exception(f"Failed to create table: {error_body.get('error', 'Unknown error')}")
                
                # Verify table was created
                try:
                    dynamodb.describe_table(TableName=table_name)
                    print(f"✅ Verified table {table_name} was created successfully")
                except dynamodb.exceptions.ResourceNotFoundException:
                    raise Exception(f"Table {table_name} was not created successfully")
                    
            except Exception as e:
                print(f"❌ Error creating table: {str(e)}")
                raise Exception(f"Failed to create required table: {str(e)}")

        # Get entities from HandleTable Lambda
        response = lambda_client.invoke(
            FunctionName='handleTable',
            InvocationType='RequestResponse',
            Payload=json.dumps({'action': 'get_entities'})
        )
        entities = json.loads(response['Payload'].read())
        
        if not entities:
            raise Exception(f"No entities found in table {table_name}")
        
        print(f"Found {len(entities)} entities to process")
        
        # Split entities into batches of 10
        batches = batch_entities(entities)
        print(f"Split into {len(batches)} batches")
        
        # Process each batch with worker lambda
        for i, batch in enumerate(batches, 1):
            print(f"Processing batch {i} with {len(batch)} entities...")
            try:
                worker_response = lambda_client.invoke(
                    FunctionName='worker',
                    InvocationType='Event',  # Asynchronous invocation
                    Payload=json.dumps({
                        'parent_entity': parent_entity,
                        'entities': batch
                    })
                )
                print(f"✅ Triggered worker lambda for batch {i}")
            except Exception as e:
                print(f"❌ Failed to invoke worker lambda for batch {i}: {str(e)}")
                raise
        
        # Wait for all entities to be processed
        max_retries = 30  # 5 minutes (10 second intervals)
        for attempt in range(max_retries):
            # Check completion status
            completion_response = lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'action': 'checkCompleted',
                    'parent_entity': parent_entity
                })
            )
            
            completion_data = json.loads(completion_response['Payload'].read())
            if completion_data['statusCode'] != 200:
                raise Exception(f"Error checking completion status: {completion_data.get('body')}")
                
            completion_body = json.loads(completion_data['body'])
            if completion_body['all_completed']:
                print("✅ All entities have been processed")
                break
                
            if attempt == max_retries - 1:
                raise Exception("Timeout waiting for entity processing to complete")
                
            print(f"Waiting for processing to complete... ({completion_body['completed_entities']}/{completion_body['total_entities']} done)")
            time.sleep(10)
        
        # Get full analysis results
        list_response = lambda_client.invoke(
            FunctionName='handleTable',
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'action': 'list',
                'parent_entity': parent_entity,
                'include_analysis': True
            })
        )
        
        list_data = json.loads(list_response['Payload'].read())
        if list_data['statusCode'] != 200:
            raise Exception(f"Error getting analysis results: {list_data.get('body')}")
        
        # Generate and send report
        entities_with_analysis = json.loads(list_data['body'])['entities']
        html_report = generate_html_report(entities_with_analysis)
        
        if html_report:
            email_list = get_email_list(parent_entity)
            for recipient in email_list:
                send_email_report(
                    html_report,
                    subject=f"News Alert Report - {parent_entity}",
                    recipient=recipient
                )
            print("✅ Report sent successfully to all recipients")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Analysis complete and report sent'
            })
        }
        
    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        error_msg = str(e)
        try:
            send_error_notification(error_msg)
        except Exception as email_error:
            print(f"Failed to send error notification: {str(email_error)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_msg})
        }

def analyze_entity(text: str, entity: str, parent_entity: str = "stanford", advanced_response: bool = True):
    try:
        credentials = load_credentials()
        client = OpenAI(api_key=credentials.get('OPENAI_API_KEY'))
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert analyst..."},
                {"role": "user", "content": f"Analyze this text..."}
            ]
        )
        
        # Process the response as needed
        # For example, you can extract information from the response
        # and store it in the analysis data
        analysis_data = {
            'summary': response.choices[0].message.content,
            'sentiment': 'positive' if 'positive' in response.choices[0].message.content else 'negative',
            'highlighted_text': text[:100]  # Simplified example
        }
        
        return {
            'entity_name': entity,
            'analysis': analysis_data
        }
    except Exception as e:
        print(f"Error analyzing entity: {str(e)}")
        return None
