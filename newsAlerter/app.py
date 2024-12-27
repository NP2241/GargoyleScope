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
from transformers import pipeline

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Download NLTK data when the Lambda container starts
download_nltk_data()

MODEL_NAME = "distilbert-base-uncased-finetuned-sst-2-english"
MODEL_CACHE_DIR = "/tmp/model"

def get_sentiment_analyzer():
    """Get or initialize sentiment analyzer with caching"""
    if not hasattr(get_sentiment_analyzer, 'analyzer'):
        # Create pipeline and cache it
        get_sentiment_analyzer.analyzer = pipeline(
            "sentiment-analysis",
            model=MODEL_NAME,
            device=-1  # Use CPU
        )
    
    return get_sentiment_analyzer.analyzer

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
    if polarity > 0.3:
        return "positive"
    elif polarity < -0.3:
        return "negative"
    else:
        return "neutral"

def analyze_text_chunk(text, keyword):
    """Analyze sentiment of a single chunk of text"""
    try:
        if not text or not keyword:
            return 0
            
        # Get or initialize analyzer
        sentiment_analyzer = get_sentiment_analyzer()
        
        text_lower = text.lower()
        keyword_lower = keyword.lower()
        
        # Define negative context keywords
        negative_indicators = [
            'case against', 'lawsuit', 'settlement', 'theft', 'violation',
            'unpaid', 'owed', 'debt', 'complaint', 'investigation',
            'allegations', 'accused', 'charged', 'penalty', 'fine',
            'illegal', 'misconduct', 'violation', 'dispute'
        ]
        
        # Split into sentences and find all sentences containing or referring to the keyword
        sentences = text_lower.split('.')
        keyword_sentences = []
        
        for i, sentence in enumerate(sentences):
            if keyword_lower in sentence:
                keyword_sentences.append(sentences[i])
                if i + 1 < len(sentences):
                    next_sent = sentences[i + 1]
                    if any(ref in next_sent.lower() for ref in ['it', 'they', 'their', 'them', 'these', 'those', 'this', 'that']):
                        keyword_sentences.append(sentences[i + 1])
        
        if keyword_sentences:
            # Only analyze sentences containing or referring to the keyword
            relevant_text = ' '.join(keyword_sentences)
            
            # Check for negative context indicators
            context_score = 0
            for indicator in negative_indicators:
                if indicator in text_lower:
                    context_score -= 0.2  # Decrease score for each negative indicator
            
            # Get sentiment scores from DistilBERT
            results = sentiment_analyzer(relevant_text, truncation=True, max_length=512)
            
            # More nuanced sentiment scoring
            score = results[0]['score']  # Get confidence score
            if results[0]['label'] == 'NEGATIVE':
                score = -score
            
            # Apply context adjustment
            score += context_score
            
            # Amplify weak signals
            if abs(score) > 0.5:  # High confidence
                score = score * 1.5
            elif abs(score) > 0.3:  # Medium confidence
                score = score * 1.2
            
            # Ensure score stays in [-1, 1] range
            score = max(min(score, 1.0), -1.0)
            
            # Log the detailed scores for debugging
            logger.info(f"DistilBERT scores for text: {results}")
            logger.info(f"Context adjustment: {context_score}")
            logger.info(f"Final polarity: {score}")
            
            return score
        
        return 0
        
    except Exception as e:
        logger.error(f"Error analyzing chunk: {str(e)}")
        return 0

def calculate_keyword_relevance(text, keyword):
    """Calculate how relevant a chunk of text is to the keyword"""
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    
    # Handle multi-word keywords with flexible matching
    if ' ' in keyword_lower:
        words = keyword_lower.split()
        variations = [
            f" {' '.join(words)} ",     # original order with spaces
            f" {' '.join(reversed(words))} "  # reversed order with spaces
        ]
        
        # Add spaces around text to ensure we match whole phrases
        text_with_spaces = f" {text_lower} "
        
        # Check for exact phrase matches only
        if any(variation in text_with_spaces for variation in variations):
            return 3.0
        
        return 0.0
    
    # Single word keyword
    if f" {keyword_lower} " in f" {text_lower} ":
        return 3.0
    
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
            polarity = analyze_text_chunk(chunk_text, keyword)
            
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
            # Give much higher weight to chunks containing the keyword
            final_weights = []
            for score, weight in zip(chunk_scores, chunk_weights):
                if weight > 1:  # If chunk contains keyword
                    # For keyword-containing chunks, give even more weight to negative sentiment
                    if score < 0:
                        final_weights.append(abs(score * 8) * (weight * 8))
                    else:
                        final_weights.append(abs(score * 2) * (weight * 2))
                else:
                    final_weights.append(abs(score) * weight)
            
            total_weight = sum(final_weights) or 1
            average_polarity = sum(score * weight for score, weight in zip(chunk_scores, final_weights)) / total_weight
        else:
            average_polarity = 0

        score = int(average_polarity * 100)
        
        # Adjust thresholds for VADER's scoring pattern
        if score > 10:
            category = 'positive'
        elif score < -10:  # VADER is good at detecting negative sentiment
            category = 'negative'
        else:
            category = 'neutral'

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
