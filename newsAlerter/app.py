import os
import sys
import logging
import nltk
from nltk.tokenize import sent_tokenize
from dotenv import load_dotenv
import json
import boto3
from pathlib import Path
import requests
import subprocess
import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Debug Python environment
logger.info("=== Python Environment Debug Info ===")
logger.info(f"Python Version: {sys.version}")
logger.info(f"Python Path: {sys.path}")
logger.info(f"Current Working Directory: {os.getcwd()}")
logger.info(f"Directory Contents: {os.listdir('.')}")
logger.info(f"PYTHONPATH Environment Variable: {os.environ.get('PYTHONPATH', 'Not Set')}")
logger.info(f"Lambda Task Root: {os.environ.get('LAMBDA_TASK_ROOT', 'Not Set')}")
logger.info("=== Environment Variables ===")
logger.info(f"AWS_REGION: {os.environ.get('AWS_REGION', 'Not Set')}")
logger.info(f"AWS_ACCOUNT_ID: {os.environ.get('AWS_ACCOUNT_ID', 'Not Set')}")
logger.info(f"ECS_CLUSTER_NAME: {os.environ.get('ECS_CLUSTER_NAME', 'Not Set')}")
logger.info(f"ECS_SUBNET_1: {os.environ.get('ECS_SUBNET_1', 'Not Set')}")
logger.info(f"ECS_SUBNET_2: {os.environ.get('ECS_SUBNET_2', 'Not Set')}")
logger.info(f"ECS_SECURITY_GROUP: {os.environ.get('ECS_SECURITY_GROUP', 'Not Set')}")
logger.info("=== End Debug Info ===")

# Load environment variables
load_dotenv()

# Set NLTK data path
nltk.data.path.append("/root/nltk_data")

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

ecs = boto3.client('ecs')

# Get ECS resource names from environment
ECS_CLUSTER = os.environ['ECS_CLUSTER_NAME']
ECS_SUBNET_1 = os.environ['ECS_SUBNET_1']
ECS_SUBNET_2 = os.environ['ECS_SUBNET_2']
ECS_SECURITY_GROUP = os.environ['ECS_SECURITY_GROUP']

def resolve_coreferences(text, entity_name):
    """Resolve coreferences in text using SpanBERT"""
    return text

def get_relevant_sentences(text, entity_name):
    """Extract sentences relevant to the target entity"""
    try:
        logger.info(f"Extracting sentences relevant to {entity_name}...")
        
        # Split text into sentences
        sentences = sent_tokenize(text)
        logger.info(f"Found {len(sentences)} total sentences")
        
        # Filter sentences containing the entity name
        relevant_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if entity_name.lower() in sent.lower():
                logger.info(f"Found relevant sentence: {sent[:50]}...")
                relevant_sentences.append(sent)
        
        logger.info(f"Found {len(relevant_sentences)} relevant sentences")
        return relevant_sentences
    except Exception as e:
        logger.error(f"Error in sentence extraction: {str(e)}")
        logger.error("Stack trace: ", exc_info=True)
        return [s.strip() for s in text.split('.') if s.strip()]

def ensure_model_service():
    """Ensure model service is running, create if not"""
    try:
        # Skip ECR checks for local development
        if os.environ.get('AWS_SAM_LOCAL'):
            logger.info("Running locally, skipping ECR checks")
            return True
            
        # Check if ECR repository exists
        ecr = boto3.client('ecr')
        logger.info(f"AWS Region: {os.environ.get('AWS_REGION')}")
        logger.info(f"AWS Account: {os.environ.get('AWS_ACCOUNT_ID')}")
        try:
            ecr.describe_repositories(repositoryNames=['deepseek-sentiment'])
        except ecr.exceptions.RepositoryNotFoundException:
            # Create repository
            ecr.create_repository(repositoryName='deepseek-sentiment')
            
            # Build and push image (first time only)
            os.system(f"""
                cd {os.path.dirname(__file__)}/model_service && \
                docker build -t deepseek-sentiment . && \
                aws ecr get-login-password --region {os.environ['AWS_REGION']} | \
                docker login --username AWS --password-stdin {os.environ['AWS_ACCOUNT_ID']}.dkr.ecr.{os.environ['AWS_REGION']}.amazonaws.com && \
                docker tag deepseek-sentiment:latest {os.environ['AWS_ACCOUNT_ID']}.dkr.ecr.{os.environ['AWS_REGION']}.amazonaws.com/deepseek-sentiment:latest && \
                docker push {os.environ['AWS_ACCOUNT_ID']}.dkr.ecr.{os.environ['AWS_REGION']}.amazonaws.com/deepseek-sentiment:latest
            """)
            
        return True
    except Exception as e:
        logger.error(f"Error ensuring model service: {str(e)}")
        return False

def ensure_model_running():
    """Start the model instance if not running"""
    try:
        model_endpoint = os.environ.get('MODEL_ENDPOINT')
        if not model_endpoint:
            # Start instance using manage-model.sh
            subprocess.run(['./manage-model.sh', 'start'], check=True)
            time.sleep(60)  # Wait for instance to start
            
        return True
    except Exception as e:
        logger.error(f"Error starting model instance: {str(e)}")
        return False

def analyze_sentiment(text):
    """Analyze text sentiment using DeepSeek model"""
    try:
        if not ensure_model_running():
            return 0
            
        model_endpoint = os.environ.get('MODEL_ENDPOINT')
        logger.info(f"Using model endpoint: {model_endpoint}")
        response = requests.post(
            f'{model_endpoint}/analyze',
            json={'text': text},
            timeout=30
        )
        return response.json()['score']
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        return 0

def analyze_text(text, entity_name="Rangoon Ruby"):
    """Analyze sentiment of text using our model"""
    try:
        logger.info("Starting text analysis...")
        
        # First resolve coreferences
        text_with_refs = resolve_coreferences(text, entity_name)
        
        # Then do sentiment analysis
        relevant_sentences = get_relevant_sentences(text, entity_name)
        logger.info(f"Found {len(relevant_sentences)} relevant sentences")
        if not relevant_sentences:
            logger.info("No relevant sentences found")
            return text
        
        # Create a map of sentences to their sentiment ratings
        sentiment_map = {}
        
        for sentence in relevant_sentences:
            if sentence.strip():
                score = analyze_sentiment(sentence)
                sentiment_map[sentence.strip()] = score
        
        # Process the full text, highlighting relevant sentences
        processed_text = text_with_refs  # Use the text with resolved references
        # Sort sentences by length (longest first) to avoid partial replacements
        sorted_sentences = sorted(sentiment_map.keys(), key=len, reverse=True)
        for sentence in sorted_sentences:
            score = sentiment_map[sentence]
            if score >= 0:
                processed_text = processed_text.replace(
                    sentence, 
                    f'<span class="positive" data-sentiment="{score:.1f}">{sentence}</span>'
                )
            else:
                processed_text = processed_text.replace(
                    sentence, 
                    f'<span class="negative" data-sentiment="{score:.1f}">{sentence}</span>'
                )
        
        logger.info("Sentiment analysis complete!")
        return processed_text
    except Exception as e:
        logger.error(f"Error in text analysis: {str(e)}")
        return text

def read_file(file_path):
    """Read and return the contents of a file"""
    try:
        logger.info(f"Attempting to read file: {file_path}")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Directory contents: {os.listdir('.')}")
        if os.path.exists(file_path):
            logger.info(f"File exists at {file_path}")
        else:
            logger.info(f"File not found at {file_path}")
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        return "Error loading article text"

def lambda_handler(event, context):
    """Lambda handler for article analysis"""
    logger.info(f"Received event: {event}")
    
    path = event.get('path', '')
    
    # Handle POST request for text analysis
    if event.get('httpMethod') == 'POST' and path == '/analyze':
        try:
            import json
            body = json.loads(event['body'])
            text = body.get('text', '')
            analyzed_text = analyze_text(text)
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'analyzed_text': analyzed_text})
            }
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return {
                'statusCode': 500,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': str(e)})
            }
    
    # Handle the articlescan page route
    if path == '/articlescan.html':
        base_dir = os.path.dirname(os.path.abspath(__file__))
        logger.info(f"Base directory: {base_dir}")
        
        template_path = os.path.join(base_dir, 'templates', 'articlescan.html')
        css_path = os.path.join(base_dir, 'static', 'styles.css')
        test_article_path = os.path.join(base_dir, 'testArticle.txt')
        
        logger.info(f"Loading template from: {template_path}")
        logger.info(f"Loading CSS from: {css_path}")
        logger.info(f"Loading test article from: {test_article_path}")
        
        html_template = read_file(template_path)
        css_content = read_file(css_path)
        article_content = read_file(test_article_path)
        
        # Analyze the test article
        analyzed_text = analyze_text(article_content)
        
        html_content = html_template.replace('{{styles}}', css_content)
        html_content = html_content.replace('{{article_content}}', analyzed_text)
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'text/html'
            },
            'body': html_content
        }
    
    return {
        'statusCode': 404,
        'body': 'Not Found'
    }
