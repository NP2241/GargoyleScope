import nltk
import os

def download_nltk_data():
    # Create a directory for NLTK data
    if not os.path.exists('/tmp/nltk_data'):
        os.makedirs('/tmp/nltk_data')
    
    # Download required NLTK data
    nltk.data.path.append('/tmp/nltk_data')
    nltk.download('punkt', download_dir='/tmp/nltk_data')
    nltk.download('averaged_perceptron_tagger', download_dir='/tmp/nltk_data') 