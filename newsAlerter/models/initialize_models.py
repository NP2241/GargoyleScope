import os
import logging
from pathlib import Path
from .download_model import download_and_save
from .download_coref_model import download_coref_model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def init_models():
    """Initialize models if they don't exist"""
    try:
        # Create directories if they don't exist
        Path('/var/task/model/bert-sentiment-multilingual').mkdir(parents=True, exist_ok=True)
        Path('/var/task/model/spanbert-coref').mkdir(parents=True, exist_ok=True)

        # Download models if they don't exist
        download_and_save()
        download_coref_model()
        
        logger.info("Models initialized successfully")
        
    except Exception as e:
        logger.error(f"Error initializing models: {str(e)}")
        raise 