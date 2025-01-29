import os
import json
from dotenv import load_dotenv
import openai  # Changed from OpenAI import

# Load environment variables
load_dotenv()

def calculate_cost(input_tokens: int, output_tokens: int, model: str = "gpt-4o") -> float:
    """Calculate cost based on OpenAI's pricing"""
    if model == "gpt-4o":
        input_cost_per_1m = 2.50   # $2.50 per 1M input tokens
        output_cost_per_1m = 10.00  # $10.00 per 1M output tokens
        
        input_cost = (input_tokens * input_cost_per_1m) / 1_000_000  # Convert to per-token cost
        output_cost = (output_tokens * output_cost_per_1m) / 1_000_000
        
        return input_cost + output_cost
    else:
        return 0.0  # Add other model pricing if needed

def analyze_entity(text: str, entity: str, advanced_response: bool = True):
    """Analyze article text and return analysis with highlighted HTML"""
    try:
        # Set API key directly
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Create prompt based on response type
        if advanced_response:
            prompt = f"""Analyze this article about {entity}. Return a JSON object with:
1. All sentences mentioning {entity} (directly or indirectly) and their sentiment (positive/negative)
2. A concise 2-3 sentence summary about {entity}'s role in the article

Return in this exact format:
{{
    "sentences": [
        {{"text": "exact sentence here", "sentiment": "positive or negative"}}
    ],
    "summary": "2-3 sentence summary here"
}}"""
        else:
            prompt = f"""Analyze this article about {entity}. Return a JSON object with just a concise 2-3 sentence summary.

Return in this exact format:
{{
    "summary": "2-3 sentence summary here"
}}"""
        
        response = openai.ChatCompletion.create(
            model="gpt-4o",  # Changed to correct GPT-4o model name
            messages=[
                {"role": "system", "content": "You are an expert at analyzing news articles. Extract relevant sentences and provide a brief summary. Return response in JSON format."},
                {"role": "user", "content": prompt + f"\n\nArticle: {text}"}
            ]
        )
        
        # Calculate and print token usage and cost
        input_tokens = response['usage']['prompt_tokens']
        output_tokens = response['usage']['completion_tokens']
        total_tokens = response['usage']['total_tokens']
        cost = calculate_cost(input_tokens, output_tokens)
        
        print("\nToken Usage and Cost (GPT-4o):")
        print("-" * 50)
        print(f"Input Tokens: {input_tokens} (${(input_tokens * 2.50 / 1_000_000):.6f})")
        print(f"Output Tokens: {output_tokens} (${(output_tokens * 10.00 / 1_000_000):.6f})")
        print(f"Total Tokens: {total_tokens}")
        print(f"Total Cost: ${cost:.6f}")
        
        # Print raw response for debugging
        print("\nRaw OpenAI Response:")
        print("-" * 50)
        print(json.dumps(response, indent=2))
        
        # Parse the response - strip markdown formatting
        raw_content = response['choices'][0]['message']['content']
        # Remove markdown json formatting if present
        if raw_content.startswith('```json'):
            raw_content = raw_content.replace('```json\n', '').replace('\n```', '')
        
        # Parse the cleaned JSON
        analysis = json.loads(raw_content)
        
        # Print parsed analysis
        print("\nParsed Analysis:")
        print("-" * 50)
        print(json.dumps(analysis, indent=2))
        
        if advanced_response:
            # Create numbered list of relevant sentences
            relevant_sentences_html = "<ol>"
            for sentence in analysis['sentences']:
                sentiment_class = 'positive' if sentence['sentiment'] == 'positive' else 'negative'
                relevant_sentences_html += f'<li><span class="{sentiment_class}">{sentence["text"]}</span></li>'
            relevant_sentences_html += "</ol>"
            
            # Highlight sentences in the full text
            highlighted_text = text
            for sentence in sorted(analysis['sentences'], key=lambda x: len(x['text']), reverse=True):
                sentiment_class = 'positive' if sentence['sentiment'] == 'positive' else 'negative'
                highlighted_text = highlighted_text.replace(
                    sentence['text'],
                    f'<span class="{sentiment_class}">{sentence["text"]}</span>'
                )
        else:
            relevant_sentences_html = ""
            highlighted_text = text
        
        return {
            'highlighted_text': highlighted_text,
            'relevant_sentences': relevant_sentences_html,
            'summary': analysis['summary']
        }
        
    except Exception as e:
        print(f"Error in analyze_entity: {str(e)}")
        return {
            'highlighted_text': f"Error analyzing article: {str(e)}",
            'relevant_sentences': "Error analyzing sentences",
            'summary': "Analysis failed"
        }

def read_file(file_path):
    """Read and return file contents"""
    try:
        with open(file_path, 'r') as file:
            return file.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

def lambda_handler(event, context):
    """Lambda handler for article analysis"""
    try:
        # Handle articlescan.html route
        if event.get('path') == '/articlescan.html':
            # Read template and article
            base_dir = os.path.dirname(os.path.abspath(__file__))
            template = read_file(os.path.join(base_dir, 'templates', 'articlescan.html'))
            article = read_file(os.path.join(base_dir, 'testArticle.txt'))
            
            # Analyze article
            entity = "Rangoon Ruby"
            analysis = analyze_entity(article, entity, advanced_response=False)
            
            # Replace template placeholders
            html = template.replace('{{article_content}}', analysis['highlighted_text'])
            html = html.replace('{{relevant_sentences}}', analysis['relevant_sentences'])
            html = html.replace('{{summary}}', analysis['summary'])
            
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'text/html'},
                'body': html
            }
            
        return {
            'statusCode': 404,
            'body': 'Not Found'
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
