from app import generate_html_report
import webbrowser
import os
import tempfile

def create_dummy_data():
    # Create dummy articles and analysis
    dummy_data = {
        'Rangoon Ruby': [
            ({'title': 'New Chef Joins Rangoon Ruby Team',
              'url': 'http://example.com/rangoon/1',
              'snippet': 'Acclaimed Burmese chef joins restaurant to revamp menu.'
             }, {
              'sentiment': 'positive',
              'summary': 'Restaurant hires experienced chef to enhance dining experience.',
              'important': False
             }),
            ({'title': 'Weekend Special: Tea Leaf Salad',
              'url': 'http://example.com/rangoon/2',
              'snippet': 'Popular dish now available for weekend brunch service.'
             }, {
              'sentiment': 'neutral',
              'summary': 'Menu update featuring signature dish during weekend hours.',
              'important': False
             }),
            ({'title': 'Local Food Blog Reviews New Menu',
              'url': 'http://example.com/rangoon/3',
              'snippet': 'Detailed review of recently updated menu items and atmosphere.'
             }, {
              'sentiment': 'positive',
              'summary': 'Positive review highlighting new dishes and improvements.',
              'important': False
             }),
            ({'title': 'Holiday Hours Announcement',
              'url': 'http://example.com/rangoon/4',
              'snippet': 'Modified operating hours for upcoming holiday season.'
             }, {
              'sentiment': 'neutral',
              'summary': 'Schedule changes for December holiday period.',
              'important': False
             }),
            ({'title': 'Customer Appreciation Week',
              'url': 'http://example.com/rangoon/5',
              'snippet': 'Special promotions and events planned for loyal customers.'
             }, {
              'sentiment': 'positive',
              'summary': 'Week-long celebration featuring discounts and special menu items.',
              'important': False
             }),
            ({'title': 'Catering Service Expansion',
              'url': 'http://example.com/rangoon/6',
              'snippet': 'Restaurant now offering expanded catering options for events.'
             }, {
              'sentiment': 'positive',
              'summary': 'New catering menu and services announced for private events.',
              'important': False
             }),
            ({'title': 'Local Charity Partnership',
              'url': 'http://example.com/rangoon/7',
              'snippet': 'Restaurant partners with local food bank for holiday giving.'
             }, {
              'sentiment': 'positive',
              'summary': 'Community involvement initiative launched for holiday season.',
              'important': False
             })
        ],
        'Nordstrom': [
            ({'title': 'Holiday Sale Preview',
              'url': 'http://example.com/nordstrom/1',
              'snippet': 'Early access to holiday deals and promotions.'
             }, {
              'sentiment': 'positive',
              'summary': 'Upcoming sale events and special promotions.',
              'important': False
             }),
            ({'title': 'New Designer Collection Launch',
              'url': 'http://example.com/nordstrom/2',
              'snippet': 'Exclusive designer collection now available.'
             }, {
              'sentiment': 'positive',
              'summary': 'Fashion launch featuring new designer partnerships.',
              'important': False
             }),
            ({'title': 'Beauty Department Expansion',
              'url': 'http://example.com/nordstrom/3',
              'snippet': 'Renovated beauty section with new brands.'
             }, {
              'sentiment': 'positive',
              'summary': 'Store improvements and new product offerings.',
              'important': False
             }),
            ({'title': 'Customer Loyalty Program Updates',
              'url': 'http://example.com/nordstrom/4',
              'snippet': 'Changes to rewards program and benefits.'
             }, {
              'sentiment': 'neutral',
              'summary': 'Modified customer rewards structure announced.',
              'important': False
             }),
            ({'title': 'Weekend Pop-up Shop',
              'url': 'http://example.com/nordstrom/5',
              'snippet': 'Local artisan showcase this weekend.'
             }, {
              'sentiment': 'positive',
              'summary': 'Special event featuring local vendors.',
              'important': False
             }),
            ({'title': 'Online Returns Now Available',
              'url': 'http://example.com/nordstrom/6',
              'snippet': 'New in-store service for online purchases.'
             }, {
              'sentiment': 'positive',
              'summary': 'Enhanced return process implemented.',
              'important': False
             }),
            ({'title': 'Seasonal Hiring Event',
              'url': 'http://example.com/nordstrom/7',
              'snippet': 'Job opportunities for holiday season.'
             }, {
              'sentiment': 'neutral',
              'summary': 'Employment opportunities for temporary positions.',
              'important': False
             }),
            ({'title': 'Store Hours Extension',
              'url': 'http://example.com/nordstrom/8',
              'snippet': 'Extended shopping hours announced.'
             }, {
              'sentiment': 'neutral',
              'summary': 'Modified store hours for holiday shopping.',
              'important': False
             })
        ],
        'Vance Brown Construction': [
            ({'title': 'New Residential Development',
              'url': 'http://example.com/vancebrown/1',
              'snippet': 'Housing project announced in Palo Alto.'
             }, {
              'sentiment': 'positive',
              'summary': 'New construction project in planning phase.',
              'important': False
             }),
            ({'title': 'Sustainability Initiative Launch',
              'url': 'http://example.com/vancebrown/2',
              'snippet': 'Green building practices implemented.'
             }, {
              'sentiment': 'positive',
              'summary': 'Environmental focus in construction methods.',
              'important': False
             }),
            ({'title': 'Community Project Completion',
              'url': 'http://example.com/vancebrown/3',
              'snippet': 'Local community center finished ahead of schedule.'
             }, {
              'sentiment': 'positive',
              'summary': 'Successful completion of public facility.',
              'important': False
             }),
            ({'title': 'Industry Award Recognition',
              'url': 'http://example.com/vancebrown/4',
              'snippet': 'Company receives building excellence award.'
             }, {
              'sentiment': 'positive',
              'summary': 'Recognition for construction quality and innovation.',
              'important': False
             }),
            ({'title': 'Safety Record Milestone',
              'url': 'http://example.com/vancebrown/5',
              'snippet': 'One year without workplace incidents.'
             }, {
              'sentiment': 'positive',
              'summary': 'Outstanding safety performance acknowledged.',
              'important': False
             }),
            ({'title': 'Apprenticeship Program Launch',
              'url': 'http://example.com/vancebrown/6',
              'snippet': 'New training initiative for construction careers.'
             }, {
              'sentiment': 'positive',
              'summary': 'Educational program for aspiring builders.',
              'important': False
             }),
            ({'title': 'Equipment Fleet Expansion',
              'url': 'http://example.com/vancebrown/7',
              'snippet': 'Investment in new construction equipment.'
             }, {
              'sentiment': 'neutral',
              'summary': 'Company growth and capability enhancement.',
              'important': False
             }),
            ({'title': 'Project Timeline Update',
              'url': 'http://example.com/vancebrown/8',
              'snippet': 'Status report on current construction projects.'
             }, {
              'sentiment': 'neutral',
              'summary': 'Progress updates on ongoing developments.',
              'important': False
             }),
            ({'title': 'Winter Weather Preparations',
              'url': 'http://example.com/vancebrown/9',
              'snippet': 'Seasonal adjustments to construction schedule.'
             }, {
              'sentiment': 'neutral',
              'summary': 'Modified work plans for winter conditions.',
              'important': False
             })
        ]
    }
    
    # Print counts for verification
    for entity, articles in dummy_data.items():
        print(f"{entity}: {len(articles)} articles")
    
    entities = list(dummy_data.keys())
    return dummy_data, entities

def preview_email():
    # Generate dummy data
    dummy_data, entities = create_dummy_data()
    
    # Force print the data structure
    print("\n=== DEBUG INFO ===")
    for entity, articles in dummy_data.items():
        print(f"\n{entity}:")
        for i, (article, analysis) in enumerate(articles, 1):
            print(f"{i}. {article['title']} (Important: {analysis['important']})")
    
    # Generate HTML
    html_content = generate_html_report(dummy_data, entities)
    
    # Save to a fixed location
    output_path = "email_preview.html"
    with open(output_path, 'w') as f:
        f.write(html_content)
    
    print(f"\nSaved HTML to: {os.path.abspath(output_path)}")
    print(f"File size: {os.path.getsize(output_path)} bytes")
    
    # Open in browser
    webbrowser.open('file://' + os.path.abspath(output_path))
    
    return html_content

if __name__ == "__main__":
    preview_email()