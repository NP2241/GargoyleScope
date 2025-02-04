import os
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

def search_news_articles(entity: str, max_results: int = 10):
    """Search for news articles about the specified entity using Google Custom Search"""
    try:
        # Initialize the Custom Search API service
        service = build(
            "customsearch", "v1",
            developerKey=os.getenv('GOOGLE_API_KEY')
        )

        # Get current date and date from 30 days ago for time filtering
        today = datetime.now()
        month_ago = today - timedelta(days=30)
        date_restrict = f"date:r:{month_ago.strftime('%Y%m%d')}:{today.strftime('%Y%m%d')}"

        # Perform the search
        result = service.cse().list(
            q=f"{entity} news",  # Search query
            cx=os.getenv('GOOGLE_CSE_ID'),  # Custom Search Engine ID
            dateRestrict=date_restrict,
            num=max_results,
            sort="date",  # Sort by date
            fields="items(title,link,snippet,pagemap/metatags/article:published_time)"  # Only get fields we need
        ).execute()

        # Process and format results
        articles = []
        if 'items' in result:
            for item in result['items']:
                article = {
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'snippet': item.get('snippet', ''),
                    'published_date': None
                }
                
                # Try to get the publication date
                if 'pagemap' in item and 'metatags' in item['pagemap']:
                    metatags = item['pagemap']['metatags'][0]
                    article['published_date'] = metatags.get('article:published_time', '')

                articles.append(article)

        return {
            'status': 'success',
            'count': len(articles),
            'articles': articles
        }

    except Exception as e:
        print(f"Error searching articles: {str(e)}")
        return {
            'status': 'error',
            'message': str(e),
            'articles': []
        }

def main():
    """Test function"""
    entity = "Rangoon Ruby"
    results = search_news_articles(entity, max_results=5)
    
    print(f"\nSearch Results for '{entity}':")
    print("-" * 50)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main() 