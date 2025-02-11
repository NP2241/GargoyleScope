import os
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from datetime import datetime, timedelta

def search_news_articles(query: str) -> dict:
    """Search for news articles using Google Custom Search API"""
    try:
        # Create service
        service = build(
            "customsearch", "v1",
            developerKey=os.getenv('GOOGLE_API_KEY')
        )

        # Execute search
        result = service.cse().list(
            q=query,
            cx=os.getenv('GOOGLE_CSE_ID'),
            num=10,  # Explicitly request max 10 results
            sort='date:d',  # Sort by date descending
            dateRestrict='m1'  # Restrict to last month
        ).execute()

        # Extract articles, ensuring no more than 10
        articles = []
        if 'items' in result:
            for item in result['items'][:10]:  # Limit to first 10 even if more are returned
                articles.append({
                    'title': item['title'],
                    'url': item['link'],
                    'snippet': item.get('snippet', '')
                })

        return {
            'articles': articles,
            'total_results': min(len(articles), 10)  # Cap total results at 10
        }

    except Exception as e:
        print(f"Error in search_news_articles: {str(e)}")
        return {'articles': [], 'total_results': 0}

def main():
    """Test function"""
    entity = "Rangoon Ruby"
    results = search_news_articles(entity)
    
    print(f"\nSearch Results for '{entity}':")
    print("-" * 50)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main() 