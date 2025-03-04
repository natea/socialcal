import asyncio
import os
import django
import logging
import json
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialcal.settings')
django.setup()

from events.scrapers.site_scraper import generate_css_schema, run_css_schema
from events.utils.time_parser import format_event_datetime

async def test_website_scraper(url):
    """Test the site scraper with a given URL."""
    logger.info(f"Testing scraper with URL: {url}")
    
    try:
        # Generate CSS schema
        logger.info("Generating CSS schema...")
        schema = await generate_css_schema(url)
        
        if not schema:
            logger.error("Failed to generate CSS schema")
            return
        
        logger.info(f"Generated schema: {json.dumps(schema, indent=2)}")
        
        # Test the schema
        logger.info("Testing CSS schema...")
        events = await run_css_schema(url, schema)
        
        logger.info(f"Extracted {len(events)} events")
        
        # Print the first few events
        for i, event in enumerate(events[:3]):
            logger.info(f"Event {i+1}: {json.dumps(event, indent=2)}")
            
            # Test date/time parsing
            if event.get('date'):
                logger.info(f"Testing date/time parsing for event {i+1}...")
                start_datetime, end_datetime = format_event_datetime(
                    event.get('date', ''),
                    event.get('start_time', ''),
                    event.get('end_time', '')
                )
                
                if start_datetime:
                    logger.info(f"Parsed start_datetime: {start_datetime}")
                    logger.info(f"Parsed end_datetime: {end_datetime}")
                else:
                    logger.warning(f"Failed to parse date/time for event {i+1}")
        
        return events
    
    except Exception as e:
        logger.error(f"Error testing scraper: {str(e)}", exc_info=True)
        return []

async def main():
    """Main function to test websites."""
    # Check if a URL was provided as a command-line argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default URL if none provided
        url = 'https://lilypadinman.com/events/'
    
    logger.info(f"\n\n{'='*50}\nTesting website: {url}\n{'='*50}\n")
    events = await test_website_scraper(url)
    logger.info(f"Total events extracted from {url}: {len(events) if events else 0}")

if __name__ == "__main__":
    asyncio.run(main()) 