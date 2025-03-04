import asyncio
import os
import json
import django
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up Django settings (must be done before imports from Django)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialcal.settings')
django.setup()

# Now import the site_scraper functions
from events.scrapers.site_scraper import generate_css_schema, run_css_schema

async def test_tockify_scraping():
    """Test scraping Tockify events."""
    # Define the URL to scrape
    url = "https://tockify.com/beehive/agenda"
    
    # Get the Gemini API key from environment
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        raise ValueError("No GEMINI_API_KEY found in environment variables")
    
    print(f"Generating CSS schema for {url}...")
    
    # Generate the CSS schema
    schema = await generate_css_schema(url, api_key)
    
    # Print the generated schema
    print(f"Generated schema: {json.dumps(schema, indent=2)}")
    
    # Test the schema by extracting events
    print(f"Testing the schema by extracting events from {url}...")
    events = await run_css_schema(url, schema)
    
    # Print the results
    print(f"Extracted {len(events)} events")
    
    # Print some of the events
    for i, event in enumerate(events[:5]):
        print(f"\nEVENT #{i+1}")
        print(f"Title: {event.get('title', 'N/A')}")
        print(f"Date: {event.get('date', 'N/A')}")
        print(f"Start Time: {event.get('start_time', 'N/A')}")
        print(f"Location: {event.get('location', 'N/A')}")
        print(f"URL: {event.get('url', 'N/A')}")
        print(f"Image URL: {event.get('image_url', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_tockify_scraping()) 