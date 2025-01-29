FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Install git and required tools
RUN apt-get update && apt-get install -y git

# Set up swap space
RUN dd if=/dev/zero of=/swapfile bs=1M count=8192 && \
    chmod 600 /swapfile && \
    mkswap /swapfile && \
    swapon /swapfile

# Install Python packages
RUN pip install --no-cache-dir \
    transformers==4.36.0 \
    accelerate==0.25.0 \
    bitsandbytes==0.41.0 \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    huggingface-hub

# Set Hugging Face token for authentication
ARG HF_TOKEN
ENV HF_TOKEN=${HF_TOKEN}

# Set up Hugging Face cache directory
ENV HF_HOME=/root/.cache/huggingface

# Copy application code
WORKDIR /app
COPY sentiment.py /app/

# Run the service
CMD ["uvicorn", "sentiment:app", "--host", "0.0.0.0", "--port", "8080"] 