FROM public.ecr.aws/lambda/python:3.8-arm64

# Set environment variables
ENV PYTHONPATH="/var/task"

WORKDIR /var/task

# Install dependencies first (for better caching)
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir --target /var/task \
    boto3>=1.26.0

# Copy shared modules
COPY src/shared ./shared/

# Copy files
COPY src/functions/handle_table/handler.py ./
COPY config/env.json ./

# Debug: List all files and pip packages
RUN echo "=== Files in /var/task ===" && \
    ls -la /var/task && \
    echo "\n=== Installed pip packages ===" && \
    pip list

COPY <<'EOF' /var/task/lambda_function.py
import os
import sys
from handler import lambda_handler

print("=== Lambda Initialization ===")
print(f"Python version: {sys.version}")
print("Module search paths:")
for path in sys.path:
    print(f"  - {path}")
print("Available modules:")
print(os.listdir(os.path.dirname(__file__)))

def handler(event, context):
    return lambda_handler(event, context)
EOF

CMD ["lambda_function.handler"] 