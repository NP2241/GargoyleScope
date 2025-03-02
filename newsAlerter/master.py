import os
import json
from dotenv import load_dotenv
import openai
import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Load environment variables
load_dotenv()

def read_file(file_path):
    """Read and return file contents"""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def send_email_report(html_content: str, subject: str = "News Alert", recipient: str = "neilpendyala@gmail.com"):
    """Send HTML report via SES"""
    try:
        # Check content size
        content_size_kb = len(html_content.encode('utf-8')) / 1024
        if content_size_kb > 100:
            print(f"⚠️ Warning: Email content is {content_size_kb:.1f}KB (recommended max is 100KB)")
            if content_size_kb > 9500:  # Leave some room for headers
                raise Exception(f"Email content too large: {content_size_kb:.1f}KB (max 10MB)")
        
        # Create SES client
        ses = boto3.client('ses', region_name=os.getenv('REGION', 'us-west-1'))
        
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

def generate_html_report(all_entity_articles, entities: list) -> str:
    """Generate HTML report from analyzed articles for multiple entities"""
    # Define color scheme
    colors = {
        'primary': '#FF0000',      # Bright red for important items
        'text': '#000000',         # Pure black for text (was #034748)
        'text_light': '#444444',   # Gray for secondary text
        'text_muted': '#7f8c8d',   # Muted gray for labels
        'link': '#034748',         # Midnight green for links
        'white': '#ffffff',        # White
        'bg_light': '#f0f2f4',     # Darker light gray background
        'bg_pink': '#fff5f5',      # Light pink background
        'border': '#e9ecef'        # Border color
    }
    
    # Read template
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template = read_file(os.path.join(base_dir, 'templates', 'articlescan.html'))
    
    # Sort entities by importance
    sorted_entities = sorted(
        all_entity_articles.items(),
        key=lambda x: sum(1 for _, analysis in x[1] if analysis.get('important', False)),
        reverse=True
    )
    
    # Calculate totals
    entities_with_important = []
    total_important = 0
    total_entities = len(entities)  # Total number of entities being tracked
    
    for entity, articles in sorted_entities:
        important_count = sum(1 for _, analysis in articles if analysis.get('important', False))
        if important_count > 0:
            entities_with_important.append((entity, important_count))
            total_important += important_count
    
    # Stats section
    if total_important == 0:
        # No important articles case
        stats_message = (
            f"We found no important articles "
            f"across all <strong style=\"color: {colors['text']}\">{total_entities}</strong> of your entities."
        )
    else:
        # Has important articles
        stats_message = (
            f"We found <strong style=\"color: {colors['primary']}\">{total_important}</strong> important "
            f"{('article' if total_important == 1 else 'articles')} "
        )
        
        if len(entities_with_important) == 1:
            # Single entity case
            entity_name = entities_with_important[0][0]
            stats_message += f"for <strong style=\"color: {colors['text']}\">{entity_name}</strong>."
        else:
            # Multiple entities case
            stats_message += (
                f"across <strong style=\"color: {colors['text']}\">{len(entities_with_important)}</strong> "
                f"{('entity' if len(entities_with_important) == 1 else 'entities')}."
            )
    
    # Build HTML for all entities
    all_analyses_html = ""
    
    # Stats section
    all_analyses_html += f"""
    <table width="100%" cellpadding="10" cellspacing="0" style="background-color: {colors['bg_light']}; 
           border-radius: 6px; 
           border: 1px solid {colors['border']};">
        <tr>
            <td style="font-family: Helvetica, Arial, sans-serif; 
                       color: {colors['text_light']}; 
                       padding: 25px; 
                       text-align: center; 
                       font-size: 16px;
                       font-weight: 500;
                       line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto;">
                    {stats_message}
                </div>
            </td>
        </tr>
    </table>
    """
    
    # Remove the padding div and handle spacing with margins
    for entity, analyzed_articles in sorted_entities:
        # Filter for important articles only
        important_articles = [(article, analysis) for article, analysis in analyzed_articles if analysis.get('important', False)]
        
        # Only show entity section if it has important articles
        if important_articles:
            # Add entity section with box styling
            all_analyses_html += f"""
            <table width="100%" cellpadding="10" cellspacing="0" style="background-color: {colors['bg_light']}; 
                   border-radius: 6px; 
                   border: 1px solid {colors['border']};
                   margin-top: 20px;">
                <tr>
                    <td style="font-family: Helvetica, Arial, sans-serif; padding: 0;">
                        <h2 style="margin: 0; 
                                  font-size: 22px;
                                  background-color: #034748;
                                  color: {colors['white']}; 
                                  padding: 15px 25px;
                                  border-radius: 6px 6px 0 0;
                                  font-weight: 600;
                                  display: flex;
                                  align-items: center;
                                  justify-content: space-between;">
                            <div>Articles about {entity}</div>
                            <div style="font-weight: normal; 
                                       font-size: 16px;
                                       color: {colors['white']};
                                       text-align: center;
                                       min-width: 150px;">
                                {len(important_articles)} important {('article' if len(important_articles) == 1 else 'articles')}
                            </div>
                        </h2>
                        <div style="padding: 25px;">
            """
            
            # Add important articles for this entity
            for idx, (article, analysis) in enumerate(important_articles, 1):
                article_html = f"""
                <table width="100%" cellpadding="10" cellspacing="0" style="margin-top: 20px; 
                       background-color: {colors['white']}; 
                       border-radius: 4px; 
                       box-shadow: 0 1px 3px rgba(0,0,0,0.1); 
                       border-left: 4px solid {colors['primary']};">
                    <tr>
                        <td style="font-family: Helvetica, Arial, sans-serif; padding: 20px;">
                            <div style="display: flex; 
                                       align-items: center; 
                                       margin-bottom: 15px;
                                       border-bottom: 1px solid {colors['border']};
                                       padding-bottom: 12px;">
                                <h3 style="color: {colors['text']}; 
                                           margin: 0; 
                                           font-size: 18px;
                                           flex-grow: 1;">
                                    #{idx}: {article['title']}
                                </h3>
                                <span style="background-color: {colors['primary']}; 
                                           color: {colors['white']}; 
                                           font-size: 15px;
                                           padding: 4px 10px;
                                           border-radius: 4px;
                                           margin-left: 15px;
                                           font-weight: 500;">
                                    {analysis['sentiment'].title()}
                                </span>
                            </div>
                            <table width="100%" cellpadding="3" cellspacing="0" style="line-height: 1.4;">
                                <tr>
                                    <td style="font-family: Helvetica, Arial, sans-serif; padding: 5px 0;">
                                        <strong style="color: {colors['text']};">URL:</strong> 
                                        <a href="{article['url']}" style="color: {colors['link']}; text-decoration: none;" target="_blank">{article['url']}</a>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-family: Helvetica, Arial, sans-serif; padding: 5px 0;">
                                        <strong style="color: {colors['text']};">AI Summary:</strong>
                                        <span style="color: {colors['text']};">{analysis['summary']}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="font-family: Helvetica, Arial, sans-serif; padding: 5px 0;">
                                        <strong style="color: {colors['text']};">Article Snippet:</strong>
                                        <span style="color: {colors['text']};">{article.get('snippet', 'No snippet available')}</span>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
                """
                all_analyses_html += article_html
            
            # Close the entity section box
            all_analyses_html += """
                    </div>
                </td>
            </tr>
        </table>
        """
    
    # Replace template placeholders
    html = template.replace('{{article_content}}', all_analyses_html)
    html = html.replace('{{relevant_sentences}}', '')
    html = html.replace('{{sentiment}}', 'News Alerter')
    html = html.replace('{{summary}}', '')  # Remove the summary from header
    
    return html

def send_error_notification(error_message: str, recipient: str = "neilpendyala@gmail.com"):
    """Send error notification email"""
    try:
        # Create SES client
        ses = boto3.client('ses', region_name=os.getenv('REGION', 'us-west-1'))
        
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

def lambda_handler(event, context):
    """
    Lambda handler for article analysis
    
    Args:
        event (dict): Lambda event
        context: Lambda context
        
    Required environment variables:
        PARENT_ENTITY: Name of the parent entity (e.g., "Stanford")
    """
    try:
        # Initialize DynamoDB client and Lambda client
        dynamodb = boto3.client('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
        lambda_client = boto3.client('lambda', region_name=os.getenv('REGION', 'us-west-1'))
        
        # Get parent entity from environment or event
        parent_entity = event.get('parent_entity') or os.getenv('PARENT_ENTITY')
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

        # Get list of entities from table
        try:
            response = lambda_client.invoke(
                FunctionName='handleTable',
                InvocationType='RequestResponse',
                Payload=json.dumps({
                    'action': 'list',
                    'parent_entity': parent_entity
                })
            )
            
            # Check for lambda execution errors
            if response.get('FunctionError'):
                error_details = json.loads(response['Payload'].read())
                raise Exception(f"Failed to list entities: {error_details}")
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            if response_payload.get('statusCode') != 200:
                error_body = json.loads(response_payload.get('body', '{}'))
                raise Exception(f"Failed to list entities: {error_body.get('error', 'Unknown error')}")
            
            # Extract entities from response
            response_body = json.loads(response_payload.get('body', '{}'))
            entities = response_body.get('entities', [])
            
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
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': f'Successfully triggered {len(batches)} worker lambdas',
                    'total_entities': len(entities),
                    'batch_count': len(batches)
                })
            }
            
        except Exception as e:
            print(f"❌ Error processing entities: {str(e)}")
            raise

    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
