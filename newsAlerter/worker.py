# Worker functions for news alerter 

import os
import json
from dotenv import load_dotenv
import openai
import boto3

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

def analyze_entity(text: str, entity: str, parent_entity: str = "stanford", advanced_response: bool = True):
    """Analyze article text and return analysis with highlighted HTML"""
    try:
        # Set API key and model
        openai.api_key = os.getenv('OPENAI_API_KEY')
        model = os.getenv('OPENAI_MODEL', 'gpt-4o-2024-08-06')
        
        # Create prompt based on response type
        if advanced_response:
            prompt = f"""First determine if this article is actually about {entity}. Then analyze and return a JSON object with:
            1. is_relevant: boolean, true if article is specifically about {entity} (not just mentions the words)
            2. sentiment: overall sentiment (positive/negative/neutral)
            3. summary: 2-3 sentence summary
            4. relevant_sentences: array of relevant quotes
            5. highlighted_text: HTML version with <span class="positive"> or <span class="negative"> tags
            6. important: boolean, true ONLY if (article is relevant AND (mentions lawsuits OR mentions {parent_entity}))
            """
        else:
            prompt = f"""First determine if this article is actually about {entity}. Then analyze and return a JSON object with:
            1. is_relevant: boolean, true if article is specifically about {entity} (not just mentions the words)
            2. sentiment: overall sentiment (positive/negative/neutral)
            3. summary: 2-3 sentence summary
            4. highlighted_text: original text with positive/negative phrases in HTML spans
            5. important: boolean, true ONLY if (article is relevant AND (mentions lawsuits OR mentions {parent_entity}))
            """

        # Get response from OpenAI
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes articles and returns JSON."},
                {"role": "user", "content": f"Article text: {text}\n\nPrompt: {prompt}"}
            ]
        )

        # Parse JSON response
        try:
            content = response.choices[0].message.content.replace('```json', '').replace('```', '').strip()
            analysis = json.loads(content)
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {str(e)}")
            return {
                'is_relevant': False,
                'highlighted_text': "Error parsing response",
                'sentiment': "Analysis failed",
                'summary': "Analysis failed",
                'important': False
            }
            
    except Exception as e:
        print(f"Error in analyze_entity: {str(e)}")
        return {
            'is_relevant': False,
            'highlighted_text': f"Error analyzing article: {str(e)}",
            'sentiment': "Analysis failed",
            'summary': "Analysis failed",
            'important': False
        }

def analyze_search_results(entity: str, search_results: dict):
    """Analyze search results for sentiment and relevance"""
    print(f"\nAnalyzing search results for {entity}:")
    print("-" * 50)

    for article in search_results['articles']:
        print(f"\nAnalyzing article: {article['title']}")
        print("-" * 30)
        
        # Combine title and snippet for analysis
        text_to_analyze = f"{article['title']} {article['snippet']}"
        
        # Analyze the article text
        analysis = analyze_entity(text_to_analyze, entity, advanced_response=False)
        
        # Print analysis
        print(f"Relevance: {'Relevant' if entity.lower() in text_to_analyze.lower() else 'Not directly relevant'}")
        print(f"Sentiment: {analysis['sentiment']}")
        print(f"Summary: {analysis['summary']}")
        print(f"URL: {article['url']}")
        print()

def analyze_and_format_articles(search_results: dict, entity: str, parent_entity: str):
    """Analyze articles and format for report"""
    analyzed_articles = []
    for article in search_results['articles']:
        text_to_analyze = f"{article['title']} {article['snippet']}"
        analysis = analyze_entity(text_to_analyze, entity, parent_entity, advanced_response=False)
        analyzed_articles.append((article, analysis))
    
    # Sort articles - important ones first
    analyzed_articles.sort(key=lambda x: (not x[1].get('important', False)))
    return analyzed_articles 