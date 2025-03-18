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
from site_scraper import run_css_schema

async def test_eventbrite_selectors(url):
    """Test different CSS selectors for Eventbrite events."""
    logger.info(f"Testing selectors for URL: {url}")
    
    # Test different CSS schema with various selectors for titles
    # Based on the generated schema but with different title selectors
    schemas = [
        {
            "name": "Schema 1 - event-card-title",
            "baseSelector": ".SearchResultPanelContentEventCard-module__card___Xno0V",
            "title_selector": ".event-card-title" 
        },
        {
            "name": "Schema 2 - direct title selector",
            "baseSelector": ".SearchResultPanelContentEventCard-module__card___Xno0V",
            "title_selector": ".SearchResultPanelContentEventCard-module__eventTitle___Xno0V" 
        },
        {
            "name": "Schema 3 - Typography with title class",
            "baseSelector": ".SearchResultPanelContentEventCard-module__card___Xno0V",
            "title_selector": ".Typography_root__487rx[data-event-title]"
        },
        {
            "name": "Schema 4 - Any Typography that looks like a title",
            "baseSelector": ".SearchResultPanelContentEventCard-module__card___Xno0V",
            "title_selector": ".Typography_root__487rx.Typography_heading-sm__487rx"
        },
        {
            "name": "Schema 5 - Any h3 element",
            "baseSelector": ".SearchResultPanelContentEventCard-module__card___Xno0V",
            "title_selector": "h3"
        }
    ]
    
    try:
        for idx, schema_info in enumerate(schemas):
            logger.info(f"\n\nTesting {schema_info['name']}...")
            
            # Create a complete CSS schema based on the previous working one
            # but with a different title selector
            css_schema = {
              "name": schema_info['name'],
              "baseSelector": schema_info['baseSelector'],
              "fields": [
                {
                  "name": "title",
                  "selector": schema_info['title_selector'],
                  "type": "text"
                },
                {
                  "name": "date",
                  "selector": ".Typography_root__487rx.Typography_body-md-bold__487rx",
                  "type": "text"
                },
                {
                  "name": "start_time",
                  "selector": ".Typography_root__487rx.Typography_body-md-bold__487rx",
                  "type": "text"
                },
                {
                  "name": "end_time",
                  "selector": None,
                  "type": "text"
                },
                {
                  "name": "location",
                  "selector": ".Typography_root__487rx.Typography_body-md__487rx.event-card__clamp-line--one",
                  "type": "text"
                },
                {
                  "name": "description",
                  "selector": ".eds-media-card-content__sub-content-cropped",
                  "type": "text"
                },
                {
                  "name": "url",
                  "selector": ".event-card-link",
                  "type": "attribute",
                  "attribute": "href"
                },
                {
                  "name": "image_url",
                  "selector": ".event-card-image",
                  "type": "attribute",
                  "attribute": "src"
                }
              ]
            }
            
            # Test the schema
            logger.info(f"Testing CSS schema: {json.dumps(css_schema, indent=2)}")
            events = await run_css_schema(url, css_schema)
            
            logger.info(f"Extracted {len(events)} events")
            
            # Check if titles were extracted
            has_titles = False
            for event in events[:3]:
                if event.get('title'):
                    has_titles = True
                    logger.info(f"Found title: {event.get('title')}")
            
            if has_titles:
                logger.info(f"✅ SUCCESS: Schema {idx+1} successfully extracted titles!")
                logger.info(f"Working selector: {schema_info['title_selector']}")
                
                # Print first 3 events with titles
                for i, event in enumerate(events[:3]):
                    if event.get('title'):
                        logger.info(f"Event {i+1}: {json.dumps(event, indent=2)}")
            else:
                logger.info(f"❌ FAILED: Schema {idx+1} did not extract any titles.")
    
    except Exception as e:
        logger.error(f"Error testing selectors: {str(e)}", exc_info=True)

async def main():
    """Main function to test Eventbrite selectors."""
    url = 'https://www.eventbrite.com/d/oh--cincinnati/all-events/'
    logger.info(f"\n\n{'='*50}\nTesting Eventbrite selectors for: {url}\n{'='*50}\n")
    await test_eventbrite_selectors(url)

if __name__ == "__main__":
    asyncio.run(main()) 