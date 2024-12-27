# GargoyleScope

A serverless application that analyzes news article sentiment using AWS Lambda and GDELT API.

## Features
- News article search using GDELT API
- Sentiment analysis of articles
- Similar article grouping
- Real-time progress updates

## Setup
1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Local development:
```bash
sam build --use-container
sam local start-api
```

3. Deploy to AWS:
```bash
sam deploy --guided
```

## Project Structure
- `newsAlerter/` - Main application code
  - `app.py` - Lambda handler and core logic
  - `templates/` - HTML templates
  - `static/` - CSS and other static files
- `template.yaml` - SAM template
- `requirements.txt` - Python dependencies

## Testing
```bash
python -m pytest tests/unit -v
```
