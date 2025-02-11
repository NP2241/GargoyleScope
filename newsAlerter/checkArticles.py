import os
import json
from dotenv import load_dotenv
from googleapiclient.discovery import build
from datetime import datetime, timedelta

def search_news_articles(entity: str):
    """Search for news articles using Google Custom Search API (paid tier)"""
    try:
        # Get credentials from Lambda environment
        api_key = os.environ.get('GOOGLE_API_KEY')
        cse_id = os.environ.get('GOOGLE_CSE_ID')

        # Debug: Print environment variables
        print("\nEnvironment Variables from Lambda:")
        print("-" * 50)
        print(f"API Key loaded: {'Yes' if api_key else 'No'}")
        print(f"API Key preview: {api_key[:10]}... (truncated)" if api_key else "No API Key found")
        print(f"CSE ID loaded: {'Yes' if cse_id else 'No'}")
        print(f"CSE ID: {cse_id}" if cse_id else "No CSE ID found")

        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")
        if not cse_id:
            raise ValueError("GOOGLE_CSE_ID not found in environment variables")

        # Initialize the Custom Search API service
        service = build(
            "customsearch", "v1",
            developerKey=api_key
        )

        # Calculate dates for 48-hour window
        now = datetime.utcnow()
        two_days_ago = now - timedelta(days=2)
        date_restrict = f"d2"  # Last 2 days

        all_articles = []
        start_index = 1
        
        while True:
            # Calculate cost for each query
            cost_per_query = 0.005  # $0.005 per query
            print(f"\nCost Analysis for query {start_index}:")
            print("-" * 50)
            print(f"Cost per query: ${cost_per_query}")

            # Perform the search
            result = service.cse().list(
                q=f'"{entity}"',  # Exact phrase match with quotes
                exactTerms=entity,  # Must contain exact terms
                cx=cse_id,  # Custom Search Engine ID
                dateRestrict=date_restrict,  # Last 48 hours
                start=start_index,  # Starting position
                sort="date",  # Sort by date
                fields="items(title,link,snippet,pagemap/metatags/article:published_time),searchInformation(totalResults)"  # Added total results
            ).execute()
            
            # Get total results count
            total_results = int(result['searchInformation']['totalResults'])
            print(f"Total results found: {total_results}")
            
            # Process results
            if 'items' in result:
                for item in result['items']:
                    article = {
                        'title': item.get('title', ''),
                        'url': item.get('link', ''),
                        'snippet': item.get('snippet', ''),
                        'published_date': None
                    }
                    
                    if 'pagemap' in item and 'metatags' in item['pagemap']:
                        metatags = item['pagemap']['metatags'][0]
                        article['published_date'] = metatags.get('article:published_time', '')

                    all_articles.append(article)
                
                # Check if we need to get more results
                if len(all_articles) < total_results and start_index < 100:  # Google's limit is 100 results
                    start_index += 10  # Google returns 10 results per page
                else:
                    break
            else:
                break

        return {
            'status': 'success',
            'count': len(all_articles),
            'total_results': total_results,
            'articles': all_articles
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
    results = search_news_articles(entity)
    
    print(f"\nSearch Results for '{entity}':")
    print("-" * 50)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main() 