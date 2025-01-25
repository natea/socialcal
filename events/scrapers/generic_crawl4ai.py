import os
import json
import asyncio
import logging
from typing import Dict, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from events.utils.time_parser import format_event_datetime
from django.conf import settings

# Load environment variables from .env file
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

class EventModel(BaseModel):
    event_title: str = Field(..., description="Title of the event.")
    event_description: str = Field(..., description="Description of the event.")
    event_date: str = Field(..., description="Date of the event (YYYY-MM-DD or MM/DD/YYYY).")
    event_start_time: str = Field(..., description="Start time of the event (HH:MM AM/PM).")
    event_end_time: str = Field(..., description="End time of the event (HH:MM AM/PM).")
    event_venue: str = Field(..., description="Venue of the event.")
    event_venue_address: str = Field(..., description="Address of the venue.")
    event_venue_city: str = Field(..., description="City of the venue.")
    event_venue_state: str = Field(..., description="State of the venue.")
    event_venue_zip: str = Field(..., description="Zip code of the venue.")
    event_venue_country: str = Field(..., description="Country of the venue.")
    event_url: str = Field(..., description="URL of the event.")
    event_image_url: str = Field(..., description="Image URL of the event.")

class GenericCrawl4AIScraper:
    def __init__(self, api_token: str = None):
        # Try to get API key in this order:
        # 1. Passed api_token
        # 2. Django settings OPENAI_API_KEY
        # 3. Environment variable OPENAI_API_KEY
        self.api_token = api_token or os.environ.get('OPENAI_API_KEY') or getattr(settings, 'OPENAI_API_KEY', None)
        
        if not self.api_token:
            logger.warning("No OpenAI API key available. Using basic extraction.")
            logger.debug(f"API Token sources checked: passed={bool(api_token)}, env={bool(os.environ.get('OPENAI_API_KEY'))}, settings={bool(getattr(settings, 'OPENAI_API_KEY', None))}")
        else:
            logger.info("OpenAI API key found and configured.")

    async def extract_events(self, url: str) -> List[dict]:
        """Extract events from any website."""
        logger.info(f"Starting event extraction from {url}...")

        browser_config = BrowserConfig(
            headless=True,
            viewport_width=1920,
            viewport_height=1080
        )

        extra_args = {"temperature": 0, "top_p": 0.9, "max_tokens": 2000}

        crawler_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            word_count_threshold=1,
            page_timeout=80000,
            wait_for_images=True,
            extraction_strategy=LLMExtractionStrategy(
                provider="openai/gpt-4o-mini",
                api_token=self.api_token,
                schema=EventModel.model_json_schema(),
                extraction_type="schema",
                instruction="""From the crawled content, carefully extract all events. For each event, you must find:
                1. Title of the event
                2. Full description
                3. Date - IMPORTANT: All dates should be for the current year. If no year is specified in the event listing, assume current year.
                4. Start and end times
                5. Venue details (name, address, city, state, zip, country)
                6. Event URL (the direct link to the event page)
                7. Event image URL - Look for <img> tags and their 'src' attributes, especially in event cards or promotional sections.
                   The image URL should be the full URL path, not a relative path.
                
                Pay special attention to:
                - Dates: Always return dates in YYYY-MM-DD format with the year 2025
                - Times: Return in HH:MM AM/PM format
                - Image URLs: Must be full URL paths, not relative paths
                
                If any field is not found, leave it blank rather than making assumptions.
                Process all events found on the page, do not skip any.""",
                extra_args=extra_args,
            ) if self.api_token else None,  # Only use LLM strategy if API key is available
        )

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                logger.info("Initialized crawler, starting extraction...")
                if not crawler_config.extraction_strategy:
                    logger.warning("No OpenAI API key available. Using basic extraction.")
                    return []  # Return empty list for now - we can implement a basic scraper later if needed
                    
                result = await crawler.arun(
                    url=url,
                    config=crawler_config
                )
                logger.info("Extraction completed successfully")
                
                # Convert the extracted content to list if it's not already
                events_data = result.extracted_content
                if events_data is None:
                    logger.warning("No events data extracted")
                    return []
                
                try:
                    if isinstance(events_data, str):
                        events_data = json.loads(events_data)
                    if not isinstance(events_data, list):
                        if isinstance(events_data, dict):
                            events_data = [events_data]
                        else:
                            logger.warning(f"Invalid events data type: {type(events_data)}")
                            return []
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse events data: {str(e)}")
                    return []

                logger.info(f"Raw events data: {json.dumps(events_data, indent=2)}")

                # Process and format the events
                formatted_events = []
                for event in events_data:
                    try:
                        # Validate event data structure
                        if not isinstance(event, dict) or not all(key in event for key in ['event_title', 'event_date', 'event_start_time']):
                            logger.warning(f"Invalid event data structure: {event}")
                            continue

                        # Use the new time parser utility
                        start_datetime, end_datetime = format_event_datetime(
                            event.get('event_date', ''),
                            event.get('event_start_time', ''),
                            event.get('event_end_time', '')
                        )

                        formatted_event = {
                            'title': event.get('event_title', ''),
                            'description': event.get('event_description', ''),
                            'start_time': start_datetime,
                            'end_time': end_datetime,
                            'venue_name': event.get('event_venue', ''),
                            'venue_address': event.get('event_venue_address', ''),
                            'venue_city': event.get('event_venue_city', ''),
                            'venue_state': event.get('event_venue_state', ''),
                            'venue_zip': event.get('event_venue_zip', ''),
                            'venue_country': event.get('event_venue_country', ''),
                            'url': event.get('event_url', ''),
                            'image_url': event.get('event_image_url', ''),
                        }

                        # Validate that we have at least a title and start time
                        if not formatted_event['title'] or not formatted_event['start_time']:
                            logger.warning(f"Event missing required fields: {formatted_event}")
                            continue

                        logger.info(f"Formatted event: {json.dumps(formatted_event, indent=2)}")
                        formatted_events.append(formatted_event)
                    except Exception as e:
                        logger.error(f"Error processing event: {str(e)}")
                        continue

                logger.info(f"Successfully processed {len(formatted_events)} events")
                return formatted_events

        except Exception as e:
            logger.error(f"Error during crawling: {str(e)}")
            raise

async def scrape_events(url: str) -> List[dict]:
    """Helper function to scrape events from any URL."""
    scraper = GenericCrawl4AIScraper()
    return await scraper.extract_events(url)

if __name__ == "__main__":
    # For testing
    test_url = "https://www.lilypadinman.com"  # Example URL
    asyncio.run(scrape_events(test_url))