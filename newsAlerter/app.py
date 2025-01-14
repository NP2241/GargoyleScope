import json
import os
import requests
import time
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import logging
import nltk
from nltk.tokenize import sent_tokenize
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

# Download required NLTK data
nltk.download('punkt')

def read_file(file_path):
    """Read and return the contents of a file"""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return "Error loading article text"

def analyze_text(text):
    """Analyze sentiment of text using our model"""
    try:
        logger.info("Starting sentiment analysis...")
        # Load model and tokenizer from local directory
        logger.info("Loading model and tokenizer from /var/task/model")
        tokenizer = AutoTokenizer.from_pretrained('/var/task/model')
        model = AutoModelForSequenceClassification.from_pretrained('/var/task/model')
        model.eval()  # Set to evaluation mode
        
        # Split into sentences
        sentences = sent_tokenize(text)
        logger.info(f"Analyzing {len(sentences)} sentences...")
        analyzed_sentences = []
        
        for sentence in sentences:
            if sentence.strip():
                # Get sentiment for each sentence
                inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding=True)
                with torch.no_grad():
                    outputs = model(**inputs)
                    scores = torch.nn.functional.softmax(outputs.logits, dim=1)
                    rating = torch.argmax(scores).item() + 1  # Model outputs 1-5 rating
                    logger.info(f"\nSentence: {sentence[:50]}...")
                    logger.info(f"Sentiment scores: {[score.item() for score in scores[0]]}")
                    logger.info(f"Rating: {rating}/5")
                    
                # Convert 1-5 rating to sentiment and add HTML styling
                if rating >= 4:
                    logger.info("Sentiment: POSITIVE")
                    formatted = f'<span class="positive">{sentence}</span>'
                elif rating <= 2:
                    logger.info("Sentiment: NEGATIVE")
                    formatted = f'<span class="negative">{sentence}</span>'
                else:
                    logger.info("Sentiment: NEUTRAL")
                    formatted = sentence
                    
                analyzed_sentences.append(formatted)
        
        logger.info("Sentiment analysis complete!")
        return ' '.join(analyzed_sentences)
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        logger.error(f"Stack trace: ", exc_info=True)
        return text

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
            
            # For testing, return mock results
            mock_results = {
                'articles': [
                    {
                        'title': 'Test Article 1',
                        'url': 'http://example.com/1',
                        'date': '2024-01-03',
                        'sentiment': 'positive',
                        'sentiment_score': 0.8
                    },
                    {
                        'title': 'Test Article 2',
                        'url': 'http://example.com/2',
                        'date': '2024-01-03',
                        'sentiment': 'negative',
                        'sentiment_score': -0.6
                    }
                ]
            }
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(mock_results)
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

    # Serve articlescan.html as the main page
    current_dir = os.path.dirname(os.path.abspath(__file__))
    html_template = read_file(os.path.join(current_dir, 'templates', 'articlescan.html'))
    css_content = read_file(os.path.join(current_dir, 'static', 'styles.css'))
    
    # Read and analyze the test article
    article_content = read_file(os.path.join(current_dir, 'testArticle.txt'))
    analyzed_content = analyze_text(article_content)
    
    # Replace both placeholders
    html_content = html_template.replace('{{styles}}', css_content)
    html_content = html_content.replace('{{article_content}}', analyzed_content)
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'text/html'
        },
        'body': html_content
    }
