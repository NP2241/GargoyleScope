FROM public.ecr.aws/lambda/python:3.8-arm64

# Set environment variables
ENV PYTHONPATH="/var/task"

WORKDIR /var/task

# Install dependencies first (for better caching)
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir --target /var/task \
    requests==2.31.0 \
    boto3>=1.26.0 \
    openai==1.12.0 \
    google-api-python-client

# Copy shared modules
COPY src/shared ./shared/

# Copy files
COPY src/web/templates/email_preview.html ./
COPY src/functions/news_alerter/handler.py ./

# Before the lambda_function.py copy
RUN echo "=== Installed Python packages ===" && \
    pip3 list && \
    echo "=== Python path ===" && \
    python3 -c "import sys; print('\n'.join(sys.path))"

COPY <<'EOF' /var/task/lambda_function.py
import sys
from importlib.machinery import ModuleSpec
from importlib.util import find_spec

def log_import_attempt(name, path):
    print(f"Attempting to import: {name} from {path}")
    return find_spec(name)

sys.meta_path.insert(0, type('ImportLogger', (), {
    'find_spec': lambda self, name, path, target=None: log_import_attempt(name, path)
}))

try:
    print("=== Starting imports ===")
    from handler import lambda_handler
    print("=== Imports complete ===")
except Exception as e:
    print(f"Error: {type(e).__name__}: {str(e)}")
    raise

def handler(event, context):
    return lambda_handler(event, context)
EOF

# Verify installations
RUN python3.8 -c "import pkg_resources; print('Installed packages:'); [print(p) for p in pkg_resources.working_set]"
RUN ls -la /var/task

CMD ["lambda_function.handler"] 