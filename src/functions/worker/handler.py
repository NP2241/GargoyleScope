# Worker functions for news alerter 

import os
import json
from openai import OpenAI
import boto3
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import requests

from shared.utils import load_credentials
from shared.database import update_entity_analysis

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
        
        # Prepare analysis data
        analysis_data = {
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
        }
        
        # Update DynamoDB with results
        update_entity_analysis(parent_entity, entity, analysis_data, completed=True)
        
        print(f"✅ Completed processing for {entity}")
        return {
            'entity': entity,
            'articles_found': len(analyzed_articles),
            'important_articles': len([a for _, a in analyzed_articles if a.get('important', False)])
        }
        
    except Exception as e:
        print(f"❌ Error processing entity {entity}: {str(e)}")
        return {
            'entity': entity,
            'error': str(e),
            'articles_found': 0,
            'important_articles': 0
        }

def lambda_handler(event, context):
    """Lambda handler for processing individual entities"""
    try:
        # Extract parameters from event
        entity = event.get('entity')
        parent_entity = event.get('parent_entity')
        
        if not entity or not parent_entity:
            raise Exception("Both 'entity' and 'parent_entity' must be provided in event")
        
        print(f"🚀 Starting processing for entity: {entity}")
        
        # Process the entity
        result = process_entity(entity, parent_entity)
        
        print(f"✅ Processing complete for {entity}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        error_message = f"Error in worker lambda_handler: {str(e)}"
        print(f"❌ {error_message}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({'error': error_message})
        } 