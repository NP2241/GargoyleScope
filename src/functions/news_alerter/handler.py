import os
import json
from openai import OpenAI
import boto3
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import time

from shared.utils import load_credentials, batch_entities
from shared.email_helpers import send_email_report, send_error_notification, generate_html_report
from shared.database import get_dynamodb_client, get_lambda_client, list_entities_from_table

# Load credentials from env.json
def load_credentials():
    try:
        with open('config/env.json', 'r') as f:
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

def analyze_entity(text: str, entity: str, parent_entity: str = "stanford", advanced_response: bool = True):
    """Analyze article text and return analysis with highlighted HTML"""
    try:
        credentials = load_credentials()
        # Initialize OpenAI client
        client = OpenAI(api_key=credentials.get('OPENAI_API_KEY'))
        model = os.getenv('OPENAI_MODEL', 'gpt-4o-2024-08-06')
        
        # Create prompt based on response type
        if advanced_response:
            prompt = f"""First determine if this article is actually about {entity}. Then analyze and return a JSON object with:
            1. is_relevant: boolean, true if article is specifically about {entity} (not just mentions the words)
            2. sentiment: overall sentiment (positive/negative/neutral)
            3. summary: 2-3 sentence summary
            4. relevant_sentences: array of relevant quotes
            5. highlighted_text: HTML version with <span class="positive"> or <span class="negative"> tags
            6. important: boolean, true ONLY if (article is relevant AND (mentions lawsuits OR mentions {parent_entity}))
            """
        else:
            prompt = f"""First determine if this article is actually about {entity}. Then analyze and return a JSON object with:
            1. is_relevant: boolean, true if article is specifically about {entity} (not just mentions the words)
            2. sentiment: overall sentiment (positive/negative/neutral)
            3. summary: 2-3 sentence summary
            4. highlighted_text: original text with positive/negative phrases in HTML spans
            5. important: boolean, true ONLY if (article is relevant AND (mentions lawsuits OR mentions {parent_entity}))
            """

        # Get response from OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes articles and returns JSON."},
                {"role": "user", "content": f"Article text: {text}\n\nPrompt: {prompt}"}
            ]
        )

        # Parse JSON response
        try:
            content = response.choices[0].message.content.replace('```json', '').replace('```', '').strip()
            analysis = json.loads(content)
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {str(e)}")
            return {
                'is_relevant': False,
                'highlighted_text': "Error parsing response",
                'sentiment': "Analysis failed",
                'summary': "Analysis failed",
                'important': False
            }
            
    except Exception as e:
        print(f"Error in analyze_entity: {str(e)}")
        return {
            'is_relevant': False,
            'highlighted_text': f"Error analyzing article: {str(e)}",
            'sentiment': "Analysis failed",
            'summary': "Analysis failed",
            'important': False
        }

def lambda_handler(event, context):
    """Lambda handler for article analysis"""
    try:
        credentials = load_credentials()
        # Initialize clients
        dynamodb = get_dynamodb_client()
        lambda_client = get_lambda_client()
        
        # Get parent entity from environment or event
        parent_entity = event.get('parent_entity')
        if not parent_entity:
            raise Exception("parent_entity must be provided in event or environment variables")
            
        table_name = f"{parent_entity}_TrackedEntities"
        
        # Get all entities from DynamoDB
        print(f"📋 Getting entities from {table_name}...")
        entities_response = list_entities_from_table(parent_entity)
        
        if not entities_response:
            print("❌ No entities found in table")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'No entities found to process'})
            }
        
        # Filter for entities that need processing
        entities_to_process = [
            entity['entity_name'] for entity in entities_response 
            if not entity.get('completed', False)
        ]
        
        if not entities_to_process:
            print("✅ All entities already processed")
            return {
                'statusCode': 200,
                'body': json.dumps({'message': 'All entities already processed'})
            }
        
        print(f"🔄 Processing {len(entities_to_process)} entities...")
        
        # Process entities in batches
        entity_batches = batch_entities(entities_to_process, batch_size=5)
        
        for batch in entity_batches:
            print(f"📦 Processing batch: {batch}")
            
            # Invoke worker Lambda for each entity in batch
            for entity in batch:
                try:
                    payload = {
                        'entity': entity,
                        'parent_entity': parent_entity,
                        'table': table_name
                    }
                    
                    print(f"🚀 Invoking worker for entity: {entity}")
                    response = lambda_client.invoke(
                        FunctionName='worker',
                        InvocationType='Event',  # Asynchronous
                        Payload=json.dumps(payload)
                    )
                    
                    print(f"✅ Worker invoked for {entity}: {response['StatusCode']}")
                    
                except Exception as e:
                    print(f"❌ Error invoking worker for {entity}: {str(e)}")
                    continue
            
            # Wait between batches to avoid overwhelming the system
            time.sleep(2)
        
        print("✅ All entities queued for processing")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Queued {len(entities_to_process)} entities for processing',
                'entities_processed': len(entities_to_process)
            })
        }
        
    except Exception as e:
        error_message = f"Error in lambda_handler: {str(e)}"
        print(f"❌ {error_message}")
        
        # Send error notification
        try:
            send_error_notification(error_message)
        except Exception as email_error:
            print(f"Failed to send error notification: {str(email_error)}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        }
