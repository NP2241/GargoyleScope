import os
import logging
import nltk
from nltk.tokenize import sent_tokenize
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
from dotenv import load_dotenv

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

# Set NLTK data path
nltk.data.path.append("/root/nltk_data")

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Initialize coreference resolution model
coref_predictor = None

def get_coref_predictor():
    """Lazy load the coreference resolution model"""
    global coref_predictor
    if coref_predictor is None:
        logger.info("Loading coreference resolution model...")
        coref_predictor = Predictor.from_path(
            "https://storage.googleapis.com/allennlp-public-models/coref-spanbert-large-2021.03.10.tar.gz"
        )
    return coref_predictor

def resolve_coreferences(text, entity_name):
    """Resolve coreferences in text, focusing on references to the target entity"""
    try:
        logger.info("Resolving coreferences...")
        predictor = get_coref_predictor()
        coref_result = predictor.predict(document=text)
        
        # Get clusters and document
        clusters = coref_result.get("clusters", [])
        words = coref_result.get("document", [])
        
        # Find clusters that contain the entity name
        entity_clusters = []
        for cluster in clusters:
            for mention in cluster:
                mention_text = " ".join(words[mention[0]:mention[1]+1])
                if entity_name.lower() in mention_text.lower():
                    entity_clusters.append(cluster)
                    break
        
        # Replace coreferent mentions with the entity name
        resolved_text = text
        for cluster in entity_clusters:
            for mention in cluster:
                mention_text = " ".join(words[mention[0]:mention[1]+1])
                if entity_name.lower() not in mention_text.lower():
                    resolved_text = resolved_text.replace(mention_text, entity_name)
        
        logger.info("Coreference resolution complete")
        return resolved_text
    except Exception as e:
        logger.error(f"Error in coreference resolution: {str(e)}")
        logger.error("Stack trace: ", exc_info=True)
        return text  # Return original text if resolution fails

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

def get_relevant_sentences(text, entity_name):
    """Extract sentences relevant to the target entity using NER"""
    try:
        logger.info(f"Extracting sentences relevant to {entity_name}...")
        resolved_text = text  # For now, just use the original text
        
        ner_pipeline = pipeline("ner", grouped_entities=True)
        entities = ner_pipeline(resolved_text)
        
        # Split text into sentences and filter for relevant ones
        sentences = resolved_text.split('. ')
        relevant_sentences = [
            sent for sent in sentences 
            for entity in entities 
            if entity_name.lower() in entity['word'].lower()
        ]
        
        logger.info(f"Found {len(relevant_sentences)} relevant sentences")
        return relevant_sentences
    except Exception as e:
        logger.error(f"Error in NER: {str(e)}")
        logger.error("Stack trace: ", exc_info=True)
        return text.split('. ')  # Return all sentences if NER fails

def analyze_text(text, entity_name="Rangoon Ruby"):
    """Analyze sentiment of text using our model"""
    try:
        logger.info("Starting sentiment analysis...")
        logger.info(f"Input text: {text[:100]}...")  # Log first 100 chars
        # First, get relevant sentences
        relevant_sentences = get_relevant_sentences(text, entity_name)
        logger.info(f"Found {len(relevant_sentences)} relevant sentences: {relevant_sentences}")
        if not relevant_sentences:
            logger.info("No relevant sentences found")
            return "No sentences found mentioning " + entity_name

        # Load model and tokenizer from local directory
        logger.info("Loading model and tokenizer from /var/task/model")
        tokenizer = AutoTokenizer.from_pretrained('/var/task/model')
        model = AutoModelForSequenceClassification.from_pretrained('/var/task/model')
        model.eval()  # Set to evaluation mode
        
        analyzed_sentences = []
        
        for sentence in relevant_sentences:
            if sentence.strip():
                # Get sentiment for each sentence
                inputs = tokenizer(sentence, return_tensors="pt", truncation=True, padding=True)
                with torch.no_grad():
                    outputs = model(**inputs)
                    scores = torch.nn.functional.softmax(outputs.logits, dim=1)
                    rating = torch.argmax(scores).item() + 1  # Model outputs 1-5 rating
                    
                # Convert 1-5 rating to sentiment and add HTML styling
                if rating >= 4:
                    formatted = f'<span class="positive">{sentence}</span>'
                elif rating <= 2:
                    formatted = f'<span class="negative">{sentence}</span>'
                else:
                    formatted = sentence
                    
                analyzed_sentences.append(formatted)
        
        logger.info("Sentiment analysis complete!")
        return ' '.join(analyzed_sentences)
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        logger.error(f"Stack trace: ", exc_info=True)
        return text

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
