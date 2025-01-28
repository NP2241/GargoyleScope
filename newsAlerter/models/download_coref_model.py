import logging
import os
from transformers import AutoTokenizer, AutoModelForTokenClassification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_PATH = '/var/task/model/spanbert-coref'

def ensure_directory():
    """Ensure model directory exists"""
    try:
        os.makedirs(MODEL_PATH, exist_ok=True)
        logger.info(f'Model directory created/verified at {MODEL_PATH}')
    except Exception as e:
        logger.error(f'Failed to create directory {MODEL_PATH}: {str(e)}')
        raise

def download_coref_model():
    """Download and save the SpanBERT coreference model"""
    try:
        model_file = os.path.join(MODEL_PATH, 'pytorch_model.bin')
        if os.path.exists(model_file):
            logger.info('SpanBERT coreference model already exists, skipping download')
            return
            
        # First ensure directory exists
        ensure_directory()
        
        # Download model
        tokenizer = AutoTokenizer.from_pretrained("SpanBERT/spanbert-large-cased")
        model = AutoModelForTokenClassification.from_pretrained("SpanBERT/spanbert-large-cased")
        
        # Save model
        tokenizer.save_pretrained(MODEL_PATH)
        model.save_pretrained(MODEL_PATH)
        
        logger.info('SpanBERT coreference model saved successfully!')
        
    except Exception as e:
        logger.error(f'Error in download_coref_model: {str(e)}')
        raise

if __name__ == "__main__":
    try:
        download_coref_model()
    except Exception as e:
        logger.error(f'Script failed: {str(e)}')
        raise 