import os
import logging
from pathlib import Path
from download_model import download_and_save
from download_coref_model import download_coref_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_models():
    """Initialize models if they don't exist in EFS"""
    try:
        # Update paths to use EFS mount
        os.environ['MODEL_CACHE_DIR'] = '/mnt/models'
        os.environ['ALLENNLP_CACHE_ROOT'] = '/mnt/models'
        os.environ['TORCH_HOME'] = '/mnt/models'

        # Create directories if they don't exist
        Path('/mnt/models/bert-sentiment-multilingual').mkdir(parents=True, exist_ok=True)
        Path('/mnt/models/spanbert-coref').mkdir(parents=True, exist_ok=True)

        # Download models if they don't exist
        download_and_save()
        download_coref_model()
        
        logger.info("Models initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing models: {str(e)}")
        raise

if __name__ == "__main__":
    init_models() 