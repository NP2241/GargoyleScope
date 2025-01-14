import logging
import sys
from transformers import AutoTokenizer, AutoModelForSequenceClassification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    MODEL_NAME = 'nlptown/bert-base-multilingual-uncased-sentiment'
    logger.info('Downloading tokenizer...')
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    logger.info('Downloading model...')
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
    logger.info('Saving model and tokenizer...')
    tokenizer.save_pretrained('/var/task/model')
    model.save_pretrained('/var/task/model')
    logger.info('Model saved successfully!')
except Exception as e:
    logger.error(f'Error downloading model: {str(e)}')
    sys.exit(1) 