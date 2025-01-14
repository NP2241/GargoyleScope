FROM public.ecr.aws/lambda/python:3.9-arm64

# Copy requirements and install in Lambda's Python path
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
WORKDIR ${LAMBDA_TASK_ROOT}

# Install dependencies with verbose output and error logging
RUN pip3 install --upgrade pip && \
    pip3 install numpy==1.21.6 2>&1 | tee numpy_install.log && \
    echo "=== Installing PyTorch ===" && \
    pip3 install --no-cache-dir torch==1.12.1 --extra-index-url https://download.pytorch.org/whl/cpu 2>&1 | tee torch_install.log && \
    echo "=== Installing other dependencies ===" && \
    pip3 install -r requirements.txt 2>&1 | tee requirements_install.log && \
    pip3 install charset_normalizer && \
    echo "=== Installation Logs ===" && \
    cat *_install.log

# Copy function code first, which includes download_model.py
COPY newsAlerter/* ${LAMBDA_TASK_ROOT}/

# Create model directory with proper permissions
RUN mkdir -p model && \
    chmod 777 model

# Then run the model download script with error output
RUN python3.9 download_model.py 2>&1 | tee model_download.log && \
    echo "=== Model Download Log ===" && \
    cat model_download.log

CMD ["app.lambda_handler"] 