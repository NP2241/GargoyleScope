import os
import logging
import nltk
import re
from nltk.tokenize import sent_tokenize
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import torch
from dotenv import load_dotenv
from allennlp.predictors.predictor import Predictor

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
                    logger.info(f"Found coreference cluster for {entity_name}:")
                    # Print all mentions in this cluster
                    for ref_mention in cluster:
                        ref_text = " ".join(words[ref_mention[0]:ref_mention[1]+1])
                        logger.info(f"  → Reference: '{ref_text}'")
                    break
        
        # Replace coreferent mentions with the entity name
        resolved_text = text
        for cluster in entity_clusters:
            for mention in cluster:
                mention_text = " ".join(words[mention[0]:mention[1]+1])
                if entity_name.lower() not in mention_text.lower():
                    logger.info(f"Replacing '{mention_text}' with '{entity_name}'")
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
    """Extract sentences relevant to the target entity using NER and coreference resolution"""
    try:
        logger.info(f"Extracting sentences relevant to {entity_name}...")
        
        # First resolve coreferences
        resolved_text = resolve_coreferences(text, entity_name)
        logger.info("Coreference resolution completed")
        
        # Split both original and resolved text into sentences
        original_sentences = sent_tokenize(text)
        resolved_sentences = sent_tokenize(resolved_text)
        logger.info(f"Found {len(original_sentences)} total sentences")
        
        # Filter sentences containing the entity name or its resolved references
        relevant_sentences = []
        for orig_sent, resolved_sent in zip(original_sentences, resolved_sentences):
            orig_sent = orig_sent.strip()
            resolved_sent = resolved_sent.strip()
            
            # Check both original and resolved sentences for entity mentions
            is_relevant = (
                entity_name.lower() in orig_sent.lower() or 
                entity_name.lower() in resolved_sent.lower()
            )
            
            if is_relevant:
                logger.info(f"Found relevant sentence: {orig_sent[:50]}...")
                relevant_sentences.append(orig_sent)
        
        logger.info(f"Found {len(relevant_sentences)} relevant sentences")
        if len(relevant_sentences) < 3:
            logger.warning("Found fewer sentences than expected, dumping all sentences for debug:")
            for i, s in enumerate(original_sentences):
                logger.info(f"Sentence {i}: {s[:50]}...")
        
        return relevant_sentences
    except Exception as e:
        logger.error(f"Error in sentence extraction: {str(e)}")
        logger.error("Stack trace: ", exc_info=True)
        # Return original text split by periods as fallback
        return [s.strip() for s in text.split('.') if s.strip()]

def analyze_text(text, entity_name="Rangoon Ruby"):
    """Analyze sentiment of text using our model"""
    try:
        logger.info("Starting sentiment analysis...")
        logger.info(f"Input text: {text[:100]}...")
        
        # First resolve coreferences in the entire text
        resolved_text = resolve_coreferences(text, entity_name)
        logger.info("Coreference resolution completed")
        
        relevant_sentences = get_relevant_sentences(resolved_text, entity_name)
        logger.info(f"Found {len(relevant_sentences)} relevant sentences")
        if not relevant_sentences:
            logger.info("No relevant sentences found")
            return text
        
        # Load model and tokenizer
        logger.info("Loading model and tokenizer from /var/task/model")
        tokenizer = AutoTokenizer.from_pretrained('/var/task/model')
        model = AutoModelForSequenceClassification.from_pretrained('/var/task/model')
        model.eval()
        
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
                    normalized_score = ((rating - 1) / 4 * 20) - 10
                    sentiment_map[sentence.strip()] = (rating, normalized_score)
        
        # Process the full text, highlighting relevant sentences
        processed_text = text
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
        
        logger.info("Sentiment analysis complete!")
        return processed_text
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
