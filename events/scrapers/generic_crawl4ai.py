import os
import json
import asyncio
import logging
from typing import Dict, List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, BrowserConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy
from datetime import datetime, timedelta
import pytz
import re

# Load environment variables from .env file
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

def parse_datetime(date_str: str, time_str: str) -> tuple[str, str]:
    """Parse date and time strings into Django's expected format.
    Returns a tuple of (date, time) strings."""
    logger.info(f"Parsing date: '{date_str}' and time: '{time_str}'")
    
    if not date_str or not time_str:
        raise ValueError("Date and time strings cannot be empty")
    
    try:
        # Try to parse the date first
        current_year = datetime.now().year
        
        # Clean up the date string
        date_str = date_str.strip()
        
        # If the date string already includes a year, use that
        if len(date_str.split('/')[-1]) == 4 or len(date_str.split(',')[-1].strip()) == 4:
            # Date already has a year, use it as is
            pass
        else:
            # No year in the date, need to determine appropriate year
            try:
                # Try parsing with current year
                if '/' in date_str:
                    test_date = datetime.strptime(f"{date_str}/{current_year}", "%m/%d/%Y")
                else:
                    test_date = datetime.strptime(f"{date_str}, {current_year}", "%B %d, %Y")
                
                # If the resulting date is more than 1 month in the past, use next year
                one_month_ago = datetime.now() - timedelta(days=30)
                if test_date.date() < one_month_ago.date():
                    current_year += 1
                    logger.info(f"Date would be in the past, using next year: {current_year}")
            except ValueError as e:
                logger.warning(f"Failed to parse date for year check: {str(e)}")
                raise ValueError(f"Invalid date format: {date_str}")
        
        # List of formats to try, in order
        date_formats = [
            ("%Y-%m-%d", date_str),                    # YYYY-MM-DD
            ("%m/%d/%Y", date_str),                    # MM/DD/YYYY
            ("%B %d, %Y", date_str),                   # Month DD, YYYY
            ("%m/%d", f"{date_str}/{current_year}"),   # MM/DD -> MM/DD/YYYY
            ("%B %d", f"{date_str}, {current_year}")   # Month DD -> Month DD, YYYY
        ]
        
        # Try each format until one works
        date_obj = None
        last_error = None
        
        for fmt, d_str in date_formats:
            try:
                date_obj = datetime.strptime(d_str, fmt)
                break
            except ValueError as e:
                last_error = e
                continue
        
        if not date_obj:
            raise ValueError(f"Could not parse date: {date_str}")
        
        # Now parse the time
        try:
            # Convert 12-hour time to 24-hour time
            time_obj = datetime.strptime(time_str, "%I:%M %p")
            time_str_24h = time_obj.strftime("%H:%M:%S")
        except ValueError as e:
            raise ValueError(f"Invalid time format: {time_str}")
        
        return date_obj.strftime("%Y-%m-%d"), time_str_24h
        
    except Exception as e:
        logger.error(f"Error parsing date/time: {str(e)}")
        raise ValueError(f"Invalid date/time format: {str(e)}")

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
        self.api_token = api_token or os.getenv("OPENAI_API_KEY")

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
            ),
        )

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                logger.info("Initialized crawler, starting extraction...")
                result = await crawler.arun(
                    url=url,
                    config=crawler_config
                )
                logger.info("Extraction completed successfully")
                
                # Convert the extracted content to list if it's not already
                events_data = result.extracted_content
                if isinstance(events_data, str):
                    events_data = json.loads(events_data)
                if not isinstance(events_data, list):
                    events_data = [events_data]

                logger.info(f"Raw events data: {json.dumps(events_data, indent=2)}")

                # Process and format the events
                formatted_events = []
                for event in events_data:
                    try:
                        # Parse date and time
                        date, start_time = parse_datetime(
                            event.get('event_date', ''),
                            event.get('event_start_time', '')
                        )
                        
                        # Parse end time if available
                        _, end_time = parse_datetime(
                            event.get('event_date', ''),
                            event.get('event_end_time', '')
                        ) if event.get('event_end_time') else ("", "")

                        # Combine date and time for Django format with timezone
                        tz = pytz.timezone('America/New_York')
                        start_datetime = None
                        end_datetime = None
                        
                        if date and start_time:
                            try:
                                # Create datetime object and make it timezone-aware
                                dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
                                start_dt = tz.localize(dt)
                                start_datetime = start_dt.strftime("%Y-%m-%d %H:%M:%S%z")
                                
                                # If no end time provided, set it to 2 hours after start time
                                if not end_time:
                                    end_dt = start_dt + timedelta(hours=2)
                                    end_datetime = end_dt.strftime("%Y-%m-%d %H:%M:%S%z")
                                else:
                                    dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")
                                    end_dt = tz.localize(dt)
                                    end_datetime = end_dt.strftime("%Y-%m-%d %H:%M:%S%z")
                            except Exception as e:
                                logger.error(f"Error creating datetime: {str(e)}")
                                # Don't skip the event, just leave start/end times as None
                                logger.info("Continuing with null datetime values")

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

                        # Only add events that have valid start and end times
                        #    if start_datetime and end_datetime:
                        #        logger.info(f"Formatted event: {json.dumps(formatted_event, indent=2)}")
                        #        formatted_events.append(formatted_event)
                        #    else:
                        #        logger.warning(f"Skipping event due to missing datetime: {event.get('event_title')}")
                        # Add all events, even those without start/end times
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