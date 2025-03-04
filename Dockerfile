# Use ARM64 Lambda base image
FROM public.ecr.aws/lambda/python:3.9-arm64

# Add descriptive labels
LABEL org.opencontainers.image.title="GargoyleScope NLP Service" \
      org.opencontainers.image.description="News analysis with DeepSeek sentiment analysis" \
      org.opencontainers.image.vendor="Neil Pendyala" \
      app.type="nlp-service" \
      app.component="news-analyzer" \
      version="1.0"

# Set environment variables
ENV PYTHONPATH="/var/task"
ENV NLTK_DATA=/var/task/nltk_data

# Install dependencies
RUN pip3 install --upgrade pip setuptools wheel

# Install core dependencies
RUN pip3 install --no-cache-dir \
    nltk==3.8.1 \
    requests==2.31.0 \
    boto3>=1.26.0 \
    openai==0.28.0 \
    google-api-python-client

# Print installed version for verification
RUN pip freeze | grep openai

# Download NLTK data
RUN python3.9 -c "import nltk; nltk.download('punkt', download_dir='/var/task/nltk_data')"

# Create package directory
WORKDIR /var/task

# Copy files to root
COPY newsAlerter/*.py ./
COPY newsAlerter/email_preview.html ./

# Create entry point script
COPY <<'EOF' /var/task/lambda_function.py
from master import lambda_handler

def handler(event, context):
    return lambda_handler(event, context)
EOF

CMD ["lambda_function.handler"] 