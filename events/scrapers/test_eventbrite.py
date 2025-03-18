import asyncio
import logging
import sys
import os
import json
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import site_scraper functions directly
from site_scraper import generate_css_schema, run_css_schema

async def test_eventbrite_scraper(url):
    """Test the site scraper with the Eventbrite URL."""
    logger.info(f"Testing scraper with URL: {url}")
    
    try:
        # Get GEMINI_API_KEY from environment
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            return []
        
        # Generate CSS schema
        logger.info("Generating CSS schema...")
        schema = await generate_css_schema(url, api_key)
        
        if not schema:
            logger.error("Failed to generate CSS schema")
            return []
        
        logger.info(f"Generated schema: {json.dumps(schema, indent=2)}")
        
        # Test the schema
        logger.info("Testing CSS schema...")
        events = await run_css_schema(url, schema)
        
        logger.info(f"Extracted {len(events)} events")
        
        # Print the first few events
        for i, event in enumerate(events[:5]):
            logger.info(f"Event {i+1}: {json.dumps(event, indent=2)}")
            
        return events
    
    except Exception as e:
        logger.error(f"Error testing scraper: {str(e)}", exc_info=True)
        return []

async def main():
    """Main function to test Eventbrite scraping."""
    url = 'https://www.eventbrite.com/d/oh--cincinnati/all-events/'
    logger.info(f"\n\n{'='*50}\nTesting Eventbrite URL: {url}\n{'='*50}\n")
    events = await test_eventbrite_scraper(url)
    logger.info(f"Total events extracted from {url}: {len(events) if events else 0}")

if __name__ == "__main__":
    asyncio.run(main()) 