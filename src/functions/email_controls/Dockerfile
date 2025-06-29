FROM public.ecr.aws/lambda/python:3.9-arm64

# Set environment variables
ENV PYTHONPATH="/var/task"

WORKDIR /var/task

# Install dependencies
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir --target /var/task \
    requests==2.31.0 \
    boto3>=1.26.0

# Copy shared modules
COPY src/shared ./shared/

COPY src/functions/email_controls/handler.py ./

COPY <<'EOF' /var/task/lambda_function.py
from handler import process_email

def handler(event, context):
    try:
        return process_email(event, context)
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        raise
EOF

CMD ["lambda_function.handler"] 