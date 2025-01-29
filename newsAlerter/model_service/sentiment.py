from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, AutoModelForSequenceClassification
from huggingface_hub import hf_hub_download
import torch
import logging
import os
import sys
from tqdm import tqdm
import re

# Configure logging to output to stdout
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = FastAPI()

MODEL_ID = "distilbert-base-uncased-finetuned-sst-2-english"  # ~260MB model for testing

logger.info("Starting sentiment service...")
logger.info(f"Python version: {sys.version}")
logger.info(f"PyTorch version: {torch.__version__}")
logger.info(f"CUDA available: {torch.cuda.is_available()}")

def download_with_progress(model_id):
    """Download model with progress bar"""
    logger.info(f"Starting download of model {model_id}")
    try:
        return AutoModelForSequenceClassification.from_pretrained(  # Note the different model class
            model_id,
            device_map='cpu',
            trust_remote_code=True,
            token=os.getenv('HF_TOKEN')
        )
    except Exception as e:
        logger.error(f"Error during download: {str(e)}")
        raise

# Load model and tokenizer
try:
    logger.info(f"Loading model {MODEL_ID}...")
    model = download_with_progress(MODEL_ID)
    logger.info("Model loaded successfully!")
    
    logger.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    logger.info("Tokenizer loaded successfully!")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    logger.error("Stack trace:", exc_info=True)
    raise

class SentimentRequest(BaseModel):
    text: str

@app.post("/analyze")
async def analyze_sentiment(request: SentimentRequest):
    try:
        logger.info(f"Received request to analyze: {request.text}")
        
        # Create a prompt for sentiment analysis
        prompt = f"""Analyze the sentiment of the following text and return a score between -10 (most negative) and 10 (most positive). Only return the number.

Text: {request.text}

Score:"""
        logger.info(f"Created prompt: {prompt}")

        # Tokenize and get model output
        logger.info("Tokenizing input...")
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
        
        logger.info("Generating response...")
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=10,
                pad_token_id=tokenizer.eos_token_id,
                temperature=0.7,
                do_sample=False  # Make it deterministic for now
            )
            
        # Decode the response
        logger.info("Decoding response...")
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        logger.info(f"Model response: {response}")
        
        # Extract the score using regex
        score_match = re.search(r'Score:\s*([-+]?\d*\.?\d+)', response)
        if score_match:
            score = float(score_match.group(1))
            # Clamp between -10 and 10
            score = max(-10, min(10, score))
            logger.info(f"Extracted score: {score}")
            return {"score": score}
        else:
            logger.error(f"Could not extract score from response: {response}")
            raise ValueError("Could not extract score from model response")
            
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}", exc_info=True)
        logger.error("Full response was: " + response if 'response' in locals() else "No response generated")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Check if model is loaded and ready"""
    if model is None or tokenizer is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return {"status": "healthy", "model": MODEL_ID} 