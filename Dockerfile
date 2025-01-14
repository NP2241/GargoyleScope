FROM public.ecr.aws/lambda/python:3.9-arm64

# Copy requirements and install in Lambda's Python path
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
WORKDIR ${LAMBDA_TASK_ROOT}

# Install core dependencies first
RUN pip3 install --upgrade pip && \
    pip3 install "numpy>=1.24.3" && \
    pip3 install --no-cache-dir torch==1.12.1 --extra-index-url https://download.pytorch.org/whl/cpu

# Install transformers and other requirements
RUN pip3 install -r requirements.txt && \
    pip3 install charset_normalizer

# Download and cache the NER model with error handling
RUN python3.9 -c "import os; \
    from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline; \
    model_name='dbmdz/bert-large-cased-finetuned-conll03-english'; \
    print(f'Downloading model {model_name}...'); \
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir='/var/task/model'); \
    model = AutoModelForTokenClassification.from_pretrained(model_name, cache_dir='/var/task/model'); \
    print('Model downloaded successfully')"

# Install NLTK data separately
RUN echo "=== Installing NLTK ===" && \
    pip3 install --no-cache-dir nltk && \
    echo "=== Setting up NLTK data directory ===" && \
    python3.9 -c "import nltk; nltk.download('punkt', download_dir='/var/task/nltk_data')" && \
    python3.9 -c "import nltk; nltk.download('averaged_perceptron_tagger', download_dir='/var/task/nltk_data')"

# Copy function code first, which includes download_model.py
COPY newsAlerter ${LAMBDA_TASK_ROOT}/

# Create model directory with proper permissions
RUN mkdir -p model && \
    chmod 777 model

# Then run the model download script with error output
RUN python3.9 download_model.py 2>&1 | tee model_download.log && \
    echo "=== Model Download Log ===" && \
    cat model_download.log

# Set NLTK data path
ENV NLTK_DATA=/var/task/nltk_data

CMD ["app.lambda_handler"] 