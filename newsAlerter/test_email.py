from newsAlerter.master import generate_html_report
import webbrowser
import os
import sys
import tempfile
import time
import threading

def create_dummy_data(scenario=1):
    """
    Create dummy data for different scenarios:
    1: Multiple important articles across all entities
    2: Only one entity has important articles
    3: No important articles
    """
    
    # Base articles that are never important
    regular_articles = [
        ({'title': 'Regular Update',
          'url': 'http://example.com/regular/1',
          'snippet': 'Standard business update.'
         }, {
          'sentiment': 'neutral',
          'summary': 'Regular business operations update.',
          'important': False
         }),
        # ... add more regular articles as needed
    ]
    
    # Important articles for different scenarios
    rangoon_important = [
        ({'title': 'Health Code Violation at Rangoon Ruby',
          'url': 'http://example.com/rangoon/urgent/1',
          'snippet': 'Major health code violations found at Stanford Shopping Center location.'
         }, {
          'sentiment': 'negative',
          'summary': 'Critical health violations requiring immediate attention.',
          'important': True
         })
    ]
    
    nordstrom_important = [
        ({'title': 'Stanford Store Closure',
          'url': 'http://example.com/nordstrom/urgent/1',
          'snippet': 'Unexpected closure of Stanford Shopping Center location.'
         }, {
          'sentiment': 'negative',
          'summary': 'Major retail location closing immediately.',
          'important': True
         }),
        ({'title': 'Layoffs Announced at Nordstrom',
          'url': 'http://example.com/nordstrom/urgent/2',
          'snippet': 'Significant staff reductions planned for Stanford location.'
         }, {
          'sentiment': 'negative',
          'summary': 'Major workforce changes affecting local store operations.',
          'important': True
         })
    ]
    
    vance_important = [
        ({'title': 'Construction Project Halted',
          'url': 'http://example.com/vance/urgent/1',
          'snippet': 'Stanford project suspended due to safety concerns.'
         }, {
          'sentiment': 'negative',
          'summary': 'Immediate suspension of major construction project.',
          'important': True
         })
    ]
    
    # Scenario configurations
    if scenario == 1:
        # All entities have important articles
        dummy_data = {
            'Rangoon Ruby': rangoon_important + regular_articles,
            'Nordstrom': nordstrom_important + regular_articles,
            'Vance Brown Construction': vance_important + regular_articles
        }
    elif scenario == 2:
        # Only Rangoon Ruby has important articles
        dummy_data = {
            'Rangoon Ruby': rangoon_important + regular_articles,
            'Nordstrom': regular_articles,
            'Vance Brown Construction': regular_articles
        }
    else:  # scenario 3
        # No important articles
        dummy_data = {
            'Rangoon Ruby': regular_articles,
            'Nordstrom': regular_articles,
            'Vance Brown Construction': regular_articles
        }
    
    # Print scenario info
    print(f"\nRunning Scenario {scenario}:")
    if scenario == 1:
        print("All entities have important articles")
    elif scenario == 2:
        print("Only Rangoon Ruby has important articles")
    else:
        print("No important articles")
    
    # Print counts for verification
    for entity, articles in dummy_data.items():
        important_count = sum(1 for _, analysis in articles if analysis.get('important', False))
        print(f"{entity}: {len(articles)} articles ({important_count} important)")
    
    entities = list(dummy_data.keys())
    return dummy_data, entities

def preview_email(scenario=1):
    # Generate dummy data for specified scenario
    dummy_data, entities = create_dummy_data(scenario)
    
    # Generate HTML
    html_content = generate_html_report(dummy_data, entities)
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write(html_content)
        temp_path = f.name
    
    # Open in browser
    webbrowser.open('file://' + os.path.abspath(temp_path))
    
    # Delete the temporary file after a short delay
    def cleanup():
        time.sleep(1)  # Give browser time to load
        os.unlink(temp_path)
    
    threading.Thread(target=cleanup).start()
    
    return html_content

if __name__ == "__main__":
    # Get scenario from command line argument
    if len(sys.argv) != 2 or sys.argv[1] not in ['all', 'some', 'none']:
        print("Usage: python test_email.py [all|some|none]")
        print("  all  - All entities have important articles")
        print("  some - Only one entity has important articles")
        print("  none - No important articles")
        sys.exit(1)
    
    # Convert argument to scenario number
    scenario_map = {
        'all': 1,
        'some': 2,
        'none': 3
    }
    
    scenario = scenario_map[sys.argv[1]]
    preview_email(scenario)