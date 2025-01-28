import boto3
import os
import tarfile

s3 = boto3.client('s3')
BUCKET_NAME = 'your-model-bucket'

SENTIMENT_PATH = '/var/task/model/bert-sentiment-multilingual'
COREF_PATH = '/var/task/model/spanbert-coref'

def create_tarfile(source_dir, output_filename):
    with tarfile.open(output_filename, "w:gz") as tar:
        tar.add(source_dir, arcname=os.path.basename(source_dir))

def upload_models():
    # Create tarballs
    create_tarfile(SENTIMENT_PATH, '/tmp/sentiment.tar.gz')
    create_tarfile(COREF_PATH, '/tmp/coref.tar.gz')
    
    # Upload to S3
    s3.upload_file('/tmp/sentiment.tar.gz', BUCKET_NAME, 'models/sentiment.tar.gz')
    s3.upload_file('/tmp/coref.tar.gz', BUCKET_NAME, 'models/coref.tar.gz')

if __name__ == "__main__":
    upload_models() 