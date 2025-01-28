import logging
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = '/var/task/model/bert-sentiment-multilingual'

def ensure_directory():
    """Ensure model directory exists"""
    try:
        os.makedirs(MODEL_PATH, exist_ok=True)
        logger.info(f'Model directory created/verified at {MODEL_PATH}')
    except Exception as e:
        logger.error(f'Failed to create directory {MODEL_PATH}: {str(e)}')
        raise

def download_and_save():
    """Download and save the model"""
    try:
        logger.info(f'Using MODEL_PATH: {MODEL_PATH}')
        model_file = os.path.join(MODEL_PATH, 'pytorch_model.bin')
        logger.info(f'Checking for model file at: {model_file}')
        if os.path.exists(model_file):
            logger.info('BERT sentiment model already exists, skipping download')
            return
            
        # First ensure directory exists
        ensure_directory()
        
        # Download model
        tokenizer = AutoTokenizer.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
        model = AutoModelForSequenceClassification.from_pretrained("nlptown/bert-base-multilingual-uncased-sentiment")
        
        # Save model
        tokenizer.save_pretrained(MODEL_PATH)
        model.save_pretrained(MODEL_PATH)
        
        logger.info('BERT sentiment model saved successfully!')
        
    except Exception as e:
        logger.error(f'Error in download_and_save: {str(e)}')
        raise

if __name__ == "__main__":
    try:
        download_and_save()
    except Exception as e:
        logger.error(f'Script failed: {str(e)}')
        raise 