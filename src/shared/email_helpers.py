import boto3
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from .utils import load_credentials

def get_ses_client():
    """Get SES client with credentials"""
    credentials = load_credentials()
    return boto3.client('ses', region_name=credentials.get('REGION', 'us-west-1'))

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
        ses = get_ses_client()
        
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

def send_error_notification(error_message: str, recipient: str = "neilpendyala@gmail.com"):
    """Send error notification email"""
    try:
        # Create SES client
        ses = get_ses_client()
        
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

def send_confirmation_email(sender: str, original_message, add_results: dict = None, delete_results: dict = None):
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
        ses = get_ses_client()
        
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

def send_list_email(sender: str, original_message, entities: list):
    """Send email with list of tracked entities"""
    try:
        # Sort entities alphabetically
        sorted_entities = sorted(entities)
        
        # Create message content
        message = f"You are tracking {len(sorted_entities)} entities:\n\n"
        for entity in sorted_entities:
            message += f"• {entity}\n"
            
        # Create SES client
        ses = get_ses_client()
        
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

def generate_html_report(entities_with_analysis, template_path: str = '../../web/templates/email_preview.html'):
    """Generate HTML report from analyzed entities, focusing on important articles"""
    try:
        # Read email template
        with open(template_path, 'r') as f:
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