FROM public.ecr.aws/lambda/python:3.9-arm64

# Copy requirements and install in Lambda's Python path
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
WORKDIR ${LAMBDA_TASK_ROOT}

# Install core dependencies first
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -U setuptools wheel

# Install PyTorch separately
RUN pip3 install --no-cache-dir torch==1.12.1 --extra-index-url https://download.pytorch.org/whl/cpu

# Install AllenNLP and its models separately
RUN pip3 install --no-cache-dir allennlp==2.10.1 && \
    pip3 install --no-cache-dir allennlp-models==2.10.1

# Install other requirements
RUN pip3 install --no-cache-dir -r requirements.txt && \
    pip3 install --no-cache-dir charset_normalizer

# Download and cache the NER model
RUN python3.9 -c "from transformers import AutoTokenizer, AutoModelForTokenClassification; \
    model_name='dbmdz/bert-large-cased-finetuned-conll03-english'; \
    print(f'Downloading model {model_name}...'); \
    tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir='/var/task/model'); \
    model = AutoModelForTokenClassification.from_pretrained(model_name, cache_dir='/var/task/model'); \
    print('Model downloaded successfully')"

# Install NLTK data
RUN python3.9 -c "import nltk; nltk.download('punkt', download_dir='/var/task/nltk_data')" && \
    python3.9 -c "import nltk; nltk.download('averaged_perceptron_tagger', download_dir='/var/task/nltk_data')"

# Copy function code
COPY newsAlerter ${LAMBDA_TASK_ROOT}/

# Create model directory with proper permissions
RUN mkdir -p model && \
    chmod 777 model

# Set NLTK data path
ENV NLTK_DATA=/var/task/nltk_data

CMD ["app.lambda_handler"] 