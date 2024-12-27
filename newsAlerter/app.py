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

def analyze_text_chunk(text):
    """Analyze sentiment of a single chunk of text"""
    try:
        if not text:
            return 0
        blob = TextBlob(text)
        return blob.sentiment.polarity
    except Exception as e:
        logger.error(f"Error analyzing chunk: {str(e)}")
        return 0

def calculate_keyword_relevance(text, keyword):
    """Calculate how relevant a chunk of text is to the keyword"""
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    
    # Direct keyword presence (highest weight)
    if keyword_lower in text_lower:
        return 3.0
    
    # Handle multi-word keywords (like "rangoon ruby")
    if ' ' in keyword_lower:
        # Create variations of the phrase
        words = keyword_lower.split()
        variations = [
            ' '.join(words),  # original order
            ' '.join(reversed(words))  # reversed order
        ]
        
        # Check if any variation exists in the text
        if any(variation in text_lower for variation in variations):
            return 3.0
        
        # If no exact phrase match (in either order), return base weight
        return 1.0
    
    return 1.0

def analyze_sentiment(text, keyword):
    """Analyze sentiment by breaking text into chunks, with keyword weighting"""
    try:
        if not text:
            logger.warning("No text provided for sentiment analysis")
            return {'category': 'neutral', 'score': 0, 'chunks': []}

        # Split text into sentences and group into chunks
        sentences = TextBlob(text).sentences
        chunk_size = 5  # Number of sentences per chunk
        chunks = [sentences[i:i + chunk_size] for i in range(0, len(sentences), chunk_size)]
        
        # Analyze each chunk
        chunk_scores = []
        chunk_weights = []
        chunk_data = []  # Store detailed chunk information
        
        for chunk in chunks:
            chunk_text = ' '.join(str(sentence) for sentence in chunk)
            
            # Get base sentiment
            polarity = analyze_text_chunk(chunk_text)
            
            # Calculate keyword relevance weight
            keyword_weight = calculate_keyword_relevance(chunk_text, keyword)
            
            # Store chunk data
            chunk_data.append({
                'text': chunk_text,
                'sentiment_score': int(polarity * 100),
                'keyword_weight': keyword_weight,
                'category': 'positive' if polarity > 0.05 else ('negative' if polarity < -0.05 else 'neutral')
            })
            
            # Store both score and weight for final calculation
            chunk_scores.append(polarity)
            chunk_weights.append(keyword_weight)

        # Calculate weighted average
        if chunk_scores:
            final_weights = [abs(score) * weight for score, weight in zip(chunk_scores, chunk_weights)]
            total_weight = sum(final_weights) or 1
            average_polarity = sum(score * weight for score, weight in zip(chunk_scores, final_weights)) / total_weight
        else:
            average_polarity = 0

        score = int(average_polarity * 100)
        category = 'positive' if score > 5 else ('negative' if score < -5 else 'neutral')

        return {
            'category': category,
            'score': score,
            'chunks': chunk_data
        }
    except Exception as e:
        logger.error(f"Sentiment analysis error: {str(e)}")
        return {'category': 'neutral', 'score': 0, 'chunks': []}

def get_article_preview(url):
    """Get full article content for sentiment analysis"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to get article content from paragraphs
            paragraphs = soup.find_all('p')
            # Get all substantial paragraphs (excluding short ones that might be metadata)
            content = ' '.join(p.text for p in paragraphs if len(p.text.split()) > 10)
            
            # If no substantial paragraphs found, try getting main content
            if not content:
                content_div = soup.find('article') or \
                            soup.find('div', class_=['article-content', 'content', 'story-content', 'entry-content', 'story-body'])
                if content_div:
                    content = content_div.get_text(strip=True)

            # Clean up the text
            if content:
                content = ' '.join(content.split())  # Remove extra whitespace
                
                # Debug logging
                logger.info(f"URL: {url}")
                logger.info(f"Content length: {len(content)}")
                logger.info(f"Content preview: {content[:200]}...")
                
                return content

            logger.warning(f"No content found for URL: {url}")
            return None
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
    return None

def process_article(article, keyword):
    """Process a single article"""
    try:
        url = article.get('url', '')
        preview = get_article_preview(url)
        
        # Debug logging
        logger.info(f"Processing article: {article.get('title', 'No title')}")
        logger.info(f"Preview length: {len(preview) if preview else 0}")
        
        sentiment_result = analyze_sentiment(preview, keyword)
        
        return {
            'title': article.get('title', 'No title'),
            'url': url,
            'date': article.get('seendate', 'N/A'),
            'sentiment': sentiment_result['category'],
            'sentiment_score': sentiment_result['score'],
            'keyword': keyword,
            'content_chunks': sentiment_result['chunks']
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
            'maxrecords': 10
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
                executor.submit(lambda a: process_article(a, keyword), article): article 
                for article in data['articles'][:10]
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
    
    path = event.get('path', '')
    
    # Handle the breakdown page route
    if path == '/breakdown.html':
        html_template = read_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'breakdown.html'))
        css_content = read_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'styles.css'))
        html_content = html_template.replace('{{styles}}', css_content)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html'
            },
            'body': html_content
        }
    
    if event.get('httpMethod') == 'POST' and path == '/search':
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
    if path == '/results':
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
