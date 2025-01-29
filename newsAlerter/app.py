import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def analyze_entity(text: str, entity: str):
    print(f"\nAnalyzing article about {entity}...")
    print("-" * 50)
    
    response = client.chat.completions.create(
        model="gpt-4-0125-preview",
        messages=[
            {"role": "system", "content": "You are an expert at analyzing news articles. Extract relevant sentences and provide a brief summary."},
            {"role": "user", "content": f"""Analyze this article about {entity}. Return a JSON object with:
1. All sentences mentioning {entity} (directly or indirectly) and their sentiment (positive/negative)
2. A concise 2-3 sentence summary about {entity}'s role in the article

Article: {text}"""}
        ],
        response_format={ "type": "json_object" }
    )
    
    # Parse and pretty print the JSON response
    analysis = json.loads(response.choices[0].message.content)
    print("\nAnalysis:")
    print("-" * 50)
    print(json.dumps(analysis, indent=2))

def main():
    entity = "Rangoon Ruby"  # Hardcoded but passed as variable
    
    # Read test article
    with open('newsAlerter/testArticle.txt', 'r') as file:
        text = file.read()
    
    analyze_entity(text, entity)

if __name__ == "__main__":
    main()
