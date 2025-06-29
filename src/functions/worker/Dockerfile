FROM public.ecr.aws/lambda/python:3.8-arm64

# Set environment variables
ENV PYTHONPATH="/var/task"

WORKDIR /var/task

# Install dependencies
RUN pip3 install --upgrade pip setuptools wheel
RUN pip3 install --no-cache-dir --target /var/task \
    openai>=1.0.0 \
    google-api-python-client \
    beautifulsoup4==4.12.2 \
    boto3>=1.26.0 \
    requests==2.31.0

# Copy shared modules
COPY src/shared ./shared/

COPY src/functions/worker/handler.py ./

COPY <<'EOF' /var/task/lambda_function.py
print("=== LAMBDA INITIALIZATION START ===")
print(f"Current directory: {os.path.abspath(os.curdir)}")
print("Attempting to load lambda_function.py from:")
for path in sys.path:
    potential_file = os.path.join(path, "lambda_function.py")
    exists = os.path.exists(potential_file)
    print(f"  - {potential_file} {'(EXISTS)' if exists else '(NOT FOUND)'}")

print("\nDirectory contents:")
for root, dirs, files in os.walk('.'):
    print(f"\nIn {root}:")
    for f in files:
        print(f"  - {f}")

from handler import process_entity

def handler(event, context):
    try:
        return process_entity(event.get('entity'), event.get('parent_entity'), event.get('table'))
    except Exception as e:
        print(f"Error in handler: {str(e)}")
        raise
EOF

CMD ["lambda_function.handler"] 