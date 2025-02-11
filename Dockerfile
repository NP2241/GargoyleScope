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
ENV PYTHONPATH="${LAMBDA_TASK_ROOT}"
ENV NLTK_DATA=${LAMBDA_TASK_ROOT}/nltk_data

# Install dependencies
RUN pip3 install --upgrade pip setuptools wheel

# Install core dependencies
RUN pip3 install --no-cache-dir \
    nltk==3.8.1 \
    python-dotenv==1.0.0 \
    requests==2.31.0 \
    boto3>=1.26.0 \
    beautifulsoup4==4.12.3 \
    openai==0.28.0 \
    google-api-python-client

# Print installed version for verification
RUN pip freeze | grep openai

# Download NLTK data
RUN python3.9 -c "import nltk; nltk.download('punkt', download_dir='${LAMBDA_TASK_ROOT}/nltk_data')"

# Copy application code
COPY newsAlerter ${LAMBDA_TASK_ROOT}/

CMD ["app.lambda_handler"] 