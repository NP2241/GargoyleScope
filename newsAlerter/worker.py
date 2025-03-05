# Worker functions for news alerter 

import os
import json
from openai import OpenAI
import boto3
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import requests

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

def search_news_articles(entity: str) -> dict:
    """
    Search for news articles about an entity from the last 48 hours
    
    Args:
        entity (str): Entity to search for
        
    Returns:
        dict: Search results containing articles
    """
    try:
        credentials = load_credentials()
        # Get API credentials
        api_key = credentials.get('GOOGLE_API_KEY')
        cse_id = credentials.get('GOOGLE_CSE_ID')
        
        if not api_key or not cse_id:
            raise Exception("Google API credentials not found in environment variables")
            
        # Calculate time range (last 48 hours)
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=48)
        
        # Format the date range for Google's API
        date_restrict = f"sort=date:r:{start_time.strftime('%Y%m%d')}"
        
        # Build search URL
        base_url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': api_key,
            'cx': cse_id,
            'q': entity,
            'num': 10,  # Maximum 10 results
            'dateRestrict': 'd2',  # Last 2 days
            'sort': 'date'  # Sort by date
        }
        
        # Make API request
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        # Parse response
        search_data = response.json()
        
        # Extract articles
        articles = []
        if 'items' in search_data:
            for item in search_data['items'][:10]:  # Ensure max 10 articles
                articles.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', '')
                })
        
        return {
            'articles': articles,
            'total_results': len(articles)
        }
        
    except requests.exceptions.RequestException as e:
        print(f"Error making Google API request: {str(e)}")
        return {'articles': [], 'total_results': 0}
    except Exception as e:
        print(f"Error searching news articles: {str(e)}")
        return {'articles': [], 'total_results': 0}

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

def process_entity(entity: str, parent_entity: str, table: str = None) -> dict:
    """
    Process a single entity: search articles, analyze them, and update DynamoDB
    
    Args:
        entity (str): Entity name to process
        parent_entity (str): Parent entity name
        table: DynamoDB table resource
        
    Returns:
        dict: Processing results
    """
    try:
        print(f"\nProcessing entity: {entity}")
        
        credentials = load_credentials()
        # Initialize clients
        dynamodb = boto3.client('dynamodb', region_name=credentials.get('REGION', 'us-west-1'))
        table = dynamodb.Table(f"{parent_entity}_TrackedEntities")
        
        # Search for articles
        search_results = search_news_articles(entity)
        
        # Analyze articles
        analyzed_articles = []
        for article in search_results['articles']:
            text_to_analyze = f"{article['title']} {article['snippet']}"
            analysis = analyze_entity(text_to_analyze, entity, parent_entity, advanced_response=False)
            analyzed_articles.append((article, analysis))
        
        # Sort articles - important ones first
        analyzed_articles.sort(key=lambda x: (not x[1].get('important', False)))
        
        # Update DynamoDB with results
        table.update_item(
            Key={'entity_name': entity},
            UpdateExpression="SET analysis = :analysis, completed = :completed",
            ExpressionAttributeValues={
                ':analysis': {
                    'timestamp': datetime.now().isoformat(),
                    'articles': [
                        {
                            'title': article['title'],
                            'url': article['url'],
                            'snippet': article['snippet'],
                            'analysis': analysis
                        }
                        for article, analysis in analyzed_articles
                    ]
                },
                ':completed': True
            }
        )
        
        print(f"✅ Successfully processed {entity}")
        return {'success': True}
        
    except Exception as e:
        print(f"❌ Error processing entity {entity}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def lambda_handler(event, context):
    """
    Lambda handler for processing a batch of entities
    
    Expected event format:
    {
        "parent_entity": "Stanford",
        "entities": ["Entity1", "Entity2", ...]  # Batch of up to 10 entities
    }
    """
    try:
        # Get parent_entity and entities from event
        parent_entity = event.get('parent_entity')
        entities = event.get('entities', [])
        
        # Validate inputs
        if not parent_entity:
            raise Exception("parent_entity is required")
        if not entities:
            raise Exception("entities list is required")
            
        # Initialize DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name=os.getenv('REGION', 'us-west-1'))
        table = dynamodb.Table(f"{parent_entity}_TrackedEntities")
        
        # Process each entity
        processed_entities = []
        failed_entities = []
        
        for entity in entities:
            result = process_entity(entity, parent_entity, table)
            if result['success']:
                processed_entities.append(entity)
            else:
                failed_entities.append({
                    'entity': entity,
                    'error': result.get('error', 'Unknown error')
                })
        
        # Prepare response
        response = {
            'message': f'Processed {len(processed_entities)} entities',
            'processed_entities': processed_entities,
            'batch_size': len(entities),
            'successful': len(processed_entities),
            'failed': len(failed_entities)
        }
        
        if failed_entities:
            response['failed_entities'] = failed_entities
            
        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
        
    except Exception as e:
        print(f"Error in worker lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 