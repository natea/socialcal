import asyncio
import json
import logging
from typing import List, Dict

from .site_scraper import generate_css_schema, run_css_schema
from ..utils.time_parser import format_event_datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_website_scraper(url: str):
    """Test the site scraper with the provided URL."""
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
        for i, event in enumerate(events[:5]):
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

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter website URL to test: ")
    asyncio.run(test_website_scraper(url)) 