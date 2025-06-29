import os
import json
from datetime import datetime

def load_credentials():
    """Load credentials from env.json or environment variables"""
    try:
        with open('config/env.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # In Lambda, use environment variables
        return {
            'OPENAI_API_KEY': os.environ.get('OPENAI_API_KEY'),
            'GOOGLE_API_KEY': os.environ.get('GOOGLE_API_KEY'),
            'GOOGLE_CSE_ID': os.environ.get('GOOGLE_CSE_ID'),
            'REGION': os.environ.get('REGION', 'us-west-1')
        }

def batch_entities(entities: list, batch_size: int = 10) -> list:
    """Split list of entities into batches"""
    return [entities[i:i + batch_size] for i in range(0, len(entities), batch_size)]

def get_current_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now().isoformat()

def format_error_message(error: Exception, context: str = "") -> str:
    """Format error message with context"""
    timestamp = get_current_timestamp()
    error_msg = f"[{timestamp}] {context}: {type(error).__name__}: {str(error)}"
    return error_msg 