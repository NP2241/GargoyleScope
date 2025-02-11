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

def calculate_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4o") -> float:
    """Calculate cost based on OpenAI's pricing"""
    if model == "gpt-4o":
        input_cost_per_1m = 2.50   # $2.50 per 1M input tokens
        output_cost_per_1m = 10.00  # $10.00 per 1M output tokens
        
        input_cost = (input_tokens * input_cost_per_1m) / 1_000_000  # Convert to per-token cost
        output_cost = (output_tokens * output_cost_per_1m) / 1_000_000
        
        return input_cost + output_cost
    else:
        return 0.0  # Add other model pricing if needed

def analyze_entity(text: str, entity: str, parent_entity: str = "stanford", advanced_response: bool = True):
    """Analyze article text and return analysis with highlighted HTML"""
    try:
        # Set API key and model
        openai.api_key = os.getenv('OPENAI_API_KEY')
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

            Example of irrelevant: If {entity} is "Vance Brown Construction" but article just happens to mention someone named "Vance" and "Brown" separately, mark is_relevant as false.
            """
        else:
            prompt = f"""First determine if this article is actually about {entity}. Then analyze and return a JSON object with:
            1. is_relevant: boolean, true if article is specifically about {entity} (not just mentions the words)
            2. sentiment: overall sentiment (positive/negative/neutral)
            3. summary: 2-3 sentence summary
            4. highlighted_text: original text with positive/negative phrases in HTML spans
            5. important: boolean, true ONLY if (article is relevant AND (mentions lawsuits OR mentions {parent_entity}))

            Example of irrelevant: If {entity} is "Vance Brown Construction" but article just happens to mention someone named "Vance" and "Brown" separately, mark is_relevant as false.
            """

        # Debug print
        print(f"\nAnalyzing text for {entity}:")
        print(f"Parent entity: {parent_entity}")
        print(f"Text snippet: {text[:200]}...")

        # Get response from OpenAI
        response = openai.ChatCompletion.create(
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
            
            # Debug prints
            print(f"Relevant: {analysis.get('is_relevant', False)}")
            if analysis.get('important', False):
                print(f"Important: {analysis['important']}")
                print("Reason: Article is relevant AND (mentions lawsuit or parent entity)")
            
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

def read_file(file_path):
    """Read and return file contents"""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def analyze_search_results(entity: str, search_results: dict):
    """Analyze search results for sentiment and relevance"""
    print(f"\nAnalyzing search results for {entity}:")
    print("-" * 50)

    for article in search_results['articles']:
        print(f"\nAnalyzing article: {article['title']}")
        print("-" * 30)
        
        # Combine title and snippet for analysis
        text_to_analyze = f"{article['title']} {article['snippet']}"
        
        # Analyze the article text
        analysis = analyze_entity(text_to_analyze, entity, advanced_response=False)
        
        # Print analysis
        print(f"Relevance: {'Relevant' if entity.lower() in text_to_analyze.lower() else 'Not directly relevant'}")
        print(f"Sentiment: {analysis['sentiment']}")
        print(f"Summary: {analysis['summary']}")
        print(f"URL: {article['url']}")
        print()

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
    # Read template
    base_dir = os.path.dirname(os.path.abspath(__file__))
    template = read_file(os.path.join(base_dir, 'templates', 'articlescan.html'))
    
    # Sort entities by importance
    sorted_entities = sorted(
        all_entity_articles.items(),
        key=lambda x: sum(1 for _, analysis in x[1] if analysis.get('important', False)),
        reverse=True
    )
    
    # Calculate total important articles
    total_important = sum(
        sum(1 for _, analysis in articles if analysis.get('important', False))
        for _, articles in sorted_entities
    )
    
    # Build HTML for all entities
    all_analyses_html = f"""
    <table width="100%" cellpadding="10" cellspacing="0" style="background-color: #2c3e50 !important; border-radius: 4px; margin-bottom: 30px;">
        <tr>
            <td style="font-family: Arial, sans-serif; color: #ffffff !important; padding: 15px;">
                <h2 style="margin: 0; font-size: 20px; color: #ffffff !important;">Found {total_important} important articles across {len(entities)} entities</h2>
            </td>
        </tr>
    </table>
    """
    
    for entity, analyzed_articles in sorted_entities:
        important_count = sum(1 for _, analysis in analyzed_articles if analysis.get('important', False))
        total_count = len(analyzed_articles)
        
        # Add entity header with importance indicator - force colors with !important
        header_style = "background-color: #e74c3c !important;" if important_count > 0 else "background-color: #2c3e50 !important;"
        all_analyses_html += f"""
        <table width="100%" cellpadding="10" cellspacing="0" style="{header_style} border-radius: 4px; margin: 30px 0 15px 0;">
            <tr>
                <td style="font-family: Arial, sans-serif; color: #ffffff !important; padding: 15px;">
                    <h2 style="margin: 0; font-size: 20px; display: inline-block; color: #ffffff !important;">Articles about {entity}</h2>
                    <span style="float: right; font-weight: bold; color: #ffffff !important;">{important_count} important out of {total_count} articles</span>
                </td>
            </tr>
        </table>
        """
        
        # Add articles for this entity
        for idx, (article, analysis) in enumerate(analyzed_articles, 1):
            is_important = analysis.get('important', False)
            importance_style = """
                border-left: 4px solid #ff6b6b;
                background-color: #fff5f5;
            """ if is_important else ""
            
            article_html = f"""
            <table width="100%" cellpadding="10" cellspacing="0" style="margin-bottom: 20px; background-color: #ffffff; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); {importance_style}">
                <tr>
                    <td style="font-family: Arial, sans-serif; padding: 15px;">
                        <h3 style="color: #2c3e50; margin: 0 0 10px 0; font-size: 18px;">
                            #{idx}: {article['title']}
                            {' <span style="color: #ff6b6b; font-size: 14px;">(Important)</span>' if is_important else ''}
                        </h3>
                        <table width="100%" cellpadding="5" cellspacing="0">
                            <tr>
                                <td style="font-family: Arial, sans-serif;">
                                    <strong style="color: #7f8c8d;">URL:</strong> 
                                    <a href="{article['url']}" style="color: #3498db; text-decoration: none;" target="_blank">{article['url']}</a>
                                </td>
                            </tr>
                            <tr>
                                <td style="font-family: Arial, sans-serif;">
                                    <strong style="color: #7f8c8d;">Sentiment:</strong> 
                                    <span style="color: #2c3e50;">{analysis['sentiment']}</span>
                                </td>
                            </tr>
                            <tr>
                                <td style="font-family: Arial, sans-serif;">
                                    <strong style="color: #7f8c8d;">AI Summary:</strong><br>
                                    <span style="color: #2c3e50; line-height: 1.4;">{analysis['summary']}</span>
                                </td>
                            </tr>
                            <tr>
                                <td style="font-family: Arial, sans-serif;">
                                    <strong style="color: #7f8c8d;">Article Snippet:</strong><br>
                                    <span style="color: #2c3e50; line-height: 1.4;">{article.get('snippet', 'No snippet available')}</span>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>
            """
            all_analyses_html += article_html
    
    # Replace template placeholders
    html = template.replace('{{article_content}}', all_analyses_html)
    html = html.replace('{{relevant_sentences}}', '')
    html = html.replace('{{sentiment}}', 'News Alert')
    html = html.replace('{{summary}}', f'Analysis of recent articles about {", ".join(entities)}')
    
    return html

def analyze_and_format_articles(search_results: dict, entity: str, parent_entity: str):
    """Analyze articles and format for report"""
    analyzed_articles = []
    for article in search_results['articles']:
        text_to_analyze = f"{article['title']} {article['snippet']}"
        analysis = analyze_entity(text_to_analyze, entity, parent_entity, advanced_response=False)
        analyzed_articles.append((article, analysis))
    
    # Sort articles - important ones first
    analyzed_articles.sort(key=lambda x: (not x[1].get('important', False)))
    return analyzed_articles

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
        <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
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

# Update main handler to include search and analysis
def lambda_handler(event, context):
    """Lambda handler for article analysis"""
    try:
        # Check if this is a scheduled event
        if event.get('source') == 'aws.events':
            print("Running scheduled news alert...")
            
            try:
                # Get entities from environment
                entities = [
                    'Rangoon Ruby',
                    'Nordstrom',
                    'Vance Brown Construction'
                ]
                parent_entity = os.getenv('PARENT_ENTITY', 'stanford')
                
                # Store results for all entities
                all_entity_articles = {}
                
                # Run analysis for each entity
                for entity in entities:
                    print(f"\nAnalyzing articles for: {entity}")
                    # Run the analysis
                    from checkArticles import search_news_articles
                    search_results = search_news_articles(entity)
                    analyzed_articles = analyze_and_format_articles(search_results, entity, parent_entity)
                    all_entity_articles[entity] = analyzed_articles
                
                # Generate combined report
                html_report = generate_html_report(all_entity_articles, entities)
                
                # Send email
                if send_email_report(html_report):
                    return {
                        'statusCode': 200,
                        'body': 'Scheduled alert completed successfully'
                    }
                else:
                    raise Exception("Failed to send email report")
                    
            except Exception as e:
                error_msg = f"Failed to generate or send daily alert:\n{str(e)}"
                print(error_msg)
                send_error_notification(error_msg)
                raise  # Re-raise to mark Lambda as failed
        
        # Handle web requests
        elif event.get('path') == '/articlescan.html':
            # Get entities from environment variables or use defaults
            entity = os.getenv('SEARCH_ENTITY', 'Rangoon Ruby')
            parent_entity = os.getenv('PARENT_ENTITY', 'stanford')
            
            print(f"\nSearching for: {entity}")
            print(f"Parent entity: {parent_entity}")
            
            # Search for recent articles
            search_results = search_news_articles(entity)
            
            # Analyze search results and build HTML
            analyzed_articles = []
            for article in search_results['articles']:
                text_to_analyze = f"{article['title']} {article['snippet']}"
                analysis = analyze_entity(text_to_analyze, entity, parent_entity, advanced_response=False)
                analyzed_articles.append((article, analysis))
            
            # Sort articles - important ones first
            analyzed_articles.sort(key=lambda x: (not x[1].get('important', False)))
            
            # Build HTML
            all_analyses_html = ""
            for article, analysis in analyzed_articles:
                importance_class = "important" if analysis.get('important', False) else ""
                article_html = f"""
                <div class="article-box {importance_class}">
                    <h3>Article: {article['title']}</h3>
                    <p><strong>URL:</strong> <a href="{article['url']}" target="_blank">{article['url']}</a></p>
                    <p><strong>Sentiment:</strong> {analysis['sentiment']}</p>
                    <p><strong>Important:</strong> {"Yes" if analysis.get('important', False) else "No"}</p>
                    <p><strong>Summary:</strong> {analysis['summary']}</p>
                    <div class="article-content">
                        {analysis['highlighted_text']}
                    </div>
                </div>
                """
                all_analyses_html += article_html
            
            # Read and update template
            base_dir = os.path.dirname(os.path.abspath(__file__))
            template = read_file(os.path.join(base_dir, 'templates', 'articlescan.html'))
            
            # Replace template placeholders
            html = template.replace('{{article_content}}', all_analyses_html)
            html = html.replace('{{relevant_sentences}}', '')
            html = html.replace('{{sentiment}}', 'Multiple Articles')
            html = html.replace('{{summary}}', f'Analysis of {len(search_results["articles"])} recent articles about {entity}')
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/html'},
                'body': html
            }
        
        # Default return for unmatched events
        return {
            'statusCode': 404,
            'body': 'Not Found'
        }
    
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
