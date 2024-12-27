import json
import os
import requests
from datetime import datetime
from textblob import TextBlob
from bs4 import BeautifulSoup
from nltk_setup import download_nltk_data
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Download NLTK data when the Lambda container starts
download_nltk_data()

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def format_date_for_gdelt(date_str):
    """Convert YYYY-MM-DD to YYYYMMDDHHMMSS"""
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    return date_obj.strftime('%Y%m%d000000')

def get_article_content(url):
    """Fetch article content"""
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get article text from paragraphs
        paragraphs = soup.find_all('p')
        article_text = ' '.join([p.text for p in paragraphs])
        
        return article_text
    except Exception as e:
        print(f"Error fetching content from {url}: {str(e)}")
        return None

def get_sentiment_category(polarity):
    """Convert polarity score to simple category"""
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    else:
        return "neutral"

def analyze_sentiment(text):
    """Quick sentiment analysis"""
    try:
        if not text:
            return 'neutral'
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        if polarity > 0.1:
            return 'positive'
        elif polarity < -0.1:
            return 'negative'
        return 'neutral'
    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        return 'neutral'

def get_article_preview(url):
    """Get just the first paragraph of content"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            # Just get the first few sentences for quick analysis
            text = response.text[:1000]
            return text
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
    return None

def process_article(article):
    """Process a single article"""
    try:
        url = article.get('url', '')
        preview = get_article_preview(url)
        sentiment = analyze_sentiment(preview)
        
        return {
            'title': article.get('title', 'No title'),
            'url': url,
            'date': article.get('seendate', 'N/A'),
            'sentiment': sentiment
        }
    except Exception as e:
        logger.error(f"Error processing article: {str(e)}")
        return None

def query_gdelt(keyword, start_date, end_date):
    """Query GDELT API with optimized processing"""
    base_url = "https://api.gdeltproject.org/api/v2/doc/doc"
    
    try:
        # Format dates for GDELT
        start_formatted = start_date.replace('-', '')
        end_formatted = end_date.replace('-', '')
        
        params = {
            'query': keyword,
            'mode': 'artlist',
            'format': 'json',
            'starttime': f"{start_formatted}000000",
            'endtime': f"{end_formatted}000000",
            'maxrecords': 10  # Limit initial results for testing
        }
        
        logger.info(f"Querying GDELT with params: {params}")
        response = requests.get(base_url, params=params, timeout=5)
        data = response.json()
        
        if 'articles' not in data:
            logger.warning("No articles found in GDELT response")
            return {'articles': []}

        # Process articles in parallel
        processed_articles = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_article = {
                executor.submit(process_article, article): article 
                for article in data['articles'][:10]  # Process first 10 articles
            }
            
            for future in as_completed(future_to_article):
                result = future.result()
                if result:
                    processed_articles.append(result)

        logger.info(f"Processed {len(processed_articles)} articles")
        return {'articles': processed_articles}

    except Exception as e:
        logger.error(f"GDELT query error: {str(e)}")
        return {'articles': [], 'error': str(e)}

def lambda_handler(event, context):
    """Lambda handler with improved error handling"""
    logger.info(f"Received event: {event}")
    
    if event.get('httpMethod') == 'POST' and event.get('path') == '/search':
        try:
            body = json.loads(event['body'])
            keyword = body['keyword']
            start_date = body['startDate']
            end_date = body['endDate']
            
            results = query_gdelt(keyword, start_date, end_date)
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(results)
            }
        except Exception as e:
            logger.error(f"Handler error: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'error': str(e),
                    'articles': []
                })
            }
    
    # Handle the results page route
    if event.get('path') == '/results' and event.get('httpMethod') == 'GET':
        html_template = read_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'results.html'))
        css_content = read_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'styles.css'))
        html_content = html_template.replace('{{styles}}', css_content)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html'
            },
            'body': html_content
        }

    # Original HTML serving code
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_template = read_file(os.path.join(current_dir, 'templates', 'index.html'))
    css_content = read_file(os.path.join(current_dir, 'static', 'styles.css'))
    html_content = html_template.replace('{{styles}}', css_content)
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html'
        },
        'body': html_content
    }
