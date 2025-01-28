import os
import sys
import logging
import nltk
from nltk.tokenize import sent_tokenize
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AutoModelForTokenClassification, pipeline
import torch
from dotenv import load_dotenv
import json
import boto3
from pathlib import Path
from models.initialize_models import init_models

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

predictor = None

MODEL_PATH = '/var/task/model'  # Local mount point

# Add to imports
s3 = boto3.client('s3')
BUCKET_NAME = 'your-model-bucket'
SENTIMENT_KEY = 'models/bert-sentiment-multilingual.tar.gz'
COREF_KEY = 'models/spanbert-coref-model.tar.gz'

# Set environment variables for model paths
os.environ['MODEL_CACHE_DIR'] = '/var/task/model'
os.environ['TORCH_HOME'] = '/var/task/model'

def ensure_directory():
    """Ensure model directory exists"""
    try:
        logger.info(f'Attempting to create directory at {MODEL_PATH}')  # Add more logging
        os.makedirs(MODEL_PATH, exist_ok=True)
        logger.info(f'Directory contents after creation: {os.listdir(MODEL_PATH)}')  # Add more logging
    except Exception as e:
        logger.error(f"Error creating directory: {str(e)}")
        raise

def ensure_model(model_type):
    """Download model from S3 if not in /tmp"""
    try:
        if model_type == 'sentiment':
            model_dir = Path('/var/task/model/bert-sentiment-multilingual')
        else:
            model_dir = Path('/var/task/model/spanbert-coref')

        if not model_dir.exists():
            logger.info(f"Downloading {model_type} model...")
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Download from S3
            if model_type == 'sentiment':
                s3.download_file(BUCKET_NAME, SENTIMENT_KEY, f'/tmp/{model_type}.tar.gz')
            else:
                s3.download_file(BUCKET_NAME, COREF_KEY, f'/tmp/{model_type}.tar.gz')
            
            # Extract
            import tarfile
            with tarfile.open(f'/tmp/{model_type}.tar.gz', 'r:gz') as tar:
                tar.extractall(path=model_dir)
            
            logger.info(f"{model_type} model downloaded and extracted")
        return str(model_dir)
    except Exception as e:
        logger.error(f"Error ensuring model {model_type}: {str(e)}")
        raise

def load_coref_model():
    """Load the coreference model on demand"""
    try:
        logger.info("Loading coreference model...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH + '/spanbert-coref')
        model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH + '/spanbert-coref')
        nlp = pipeline("ner", model=model, tokenizer=tokenizer)
        logger.info("Coreference model loaded successfully!")
        return nlp
    except Exception as e:
        logger.error(f"Error loading coreference model: {str(e)}")
        raise

def resolve_coreferences(text, entity_name):
    """Resolve coreferences in text using SpanBERT"""
    try:
        # Load models
        tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH + '/spanbert-coref')
        model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH + '/spanbert-coref')
        
        # Create pipeline
        nlp = pipeline("ner", model=model, tokenizer=tokenizer)
        
        # Get predictions
        results = nlp(text)
        
        # Process results and replace references
        # ... (we'll need to implement the reference replacement logic)
        
        return processed_text
        
    except Exception as e:
        logger.error(f"Error in coreference resolution: {str(e)}")
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

def analyze_text(text, entity_name="Rangoon Ruby"):
    """Analyze sentiment of text using our model"""
    try:
        logger.info("Starting text analysis...")
        model_path = f'{MODEL_PATH}/bert-sentiment-multilingual'
        logger.info(f"Looking for model in: {model_path}")
        logger.info(f"Directory exists: {os.path.exists(model_path)}")
        if os.path.exists(model_path):
            logger.info(f"Directory contents: {os.listdir(model_path)}")
        
        # Initialize models if needed
        if not os.path.exists('/var/task/model/bert-sentiment-multilingual/pytorch_model.bin'):
            init_models()
        
        # Load models
        tokenizer = AutoTokenizer.from_pretrained(f'{MODEL_PATH}/bert-sentiment-multilingual')
        model = AutoModelForSequenceClassification.from_pretrained(f'{MODEL_PATH}/bert-sentiment-multilingual')
        
        # First resolve coreferences
        text_with_refs = resolve_coreferences(text, entity_name)
        
        # Then do sentiment analysis as before
        relevant_sentences = get_relevant_sentences(text, entity_name)
        logger.info(f"Found {len(relevant_sentences)} relevant sentences")
        if not relevant_sentences:
            logger.info("No relevant sentences found")
            return text
        
        # Create a map of sentences to their sentiment ratings
        sentiment_map = {}
        
        for sentence in relevant_sentences:
            if sentence.strip():
                inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding=True)
                with torch.no_grad():
                    outputs = model(**inputs)
                    scores = torch.nn.functional.softmax(outputs.logits, dim=1)
                    rating = torch.argmax(scores).item() + 1
                    # Convert 1-5 scale to -10 to 10 scale
                    normalized_score = (rating - 3) * 5  # Simpler linear mapping
                    sentiment_map[sentence.strip()] = (rating, normalized_score)
        
        # Process the full text, highlighting relevant sentences
        processed_text = text_with_refs  # Use the text with resolved references
        # Sort sentences by length (longest first) to avoid partial replacements
        sorted_sentences = sorted(sentiment_map.keys(), key=len, reverse=True)
        for sentence in sorted_sentences:
            rating, score = sentiment_map[sentence]
            if rating >= 4:
                processed_text = processed_text.replace(
                    sentence, 
                    f'<span class="positive" data-sentiment="{score:.1f}">{sentence}</span>'
                )
            elif rating <= 2:
                processed_text = processed_text.replace(
                    sentence, 
                    f'<span class="negative" data-sentiment="{score:.1f}">{sentence}</span>'
                )
        
        # Clean up to save space
        del model, tokenizer
        import gc
        gc.collect()
        
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
