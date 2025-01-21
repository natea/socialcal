import logging
import traceback
import json
from datetime import datetime
import pytz
from dateutil import parser
from firecrawl import FirecrawlApp
from typing import Dict, Any, List, Optional
import os
import time
from requests.exceptions import RequestException
from pydantic import BaseModel, Field

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Event(BaseModel):
    """Pydantic model for an event."""
    title: str = Field(..., description="The title of the event, found in h1 headings within each event section")
    date: str = Field(..., description="The event date, found in list items like 'Saturday, January 18, 2025'")
    start_time: str = Field(..., description="Event start time, found in list items like '7:00 PM 10:00 PM 19:00 22:00'. Take the first time (7:00 PM).")
    end_time: Optional[str] = Field(None, description="Event end time, found in list items like '7:00 PM 10:00 PM 19:00 22:00'. Take the second time (10:00 PM).")
    genre: Optional[str] = Field(None, description="Genre tags like 'Jazz, Bebop' or 'Open Mic' if present before the title")
    description: Optional[str] = Field(None, description="Event details like price and seating info")
    venue_name: str = Field(default="The Lilypad")
    venue_address: str = Field(default="1353 Cambridge Street")
    venue_city: str = Field(default="Cambridge")
    venue_state: str = Field(default="MA")
    venue_postal_code: str = Field(default="02139")
    url: str = Field(default="https://www.lilypadinman.com/")

class EventList(BaseModel):
    """Pydantic model for list of events."""
    events: List[Event] = Field(..., description="List of events from the Lilypad website")

class GenericScraper:
    def __init__(self, api_key):
        self.app = FirecrawlApp(api_key=api_key)
        self.logger = logging.getLogger(__name__)
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.poll_interval = 2  # seconds for async polling

    def get_schema(self):
        """Return the schema for event extraction using Pydantic models."""
        return {
            'schema': EventList.model_json_schema(),
            'systemPrompt': """You are an expert at extracting event information from web pages.
                You are currently processing the Lilypad's event calendar page.
                
                Pay special attention to:
                1. Event structure:
                   - Each event has a title in h1
                   - Followed by a list containing date and times
                   - The list format is like: "Saturday, January 18, 2025" followed by times
                   - Times are shown as "7:00 PM 10:00 PM 19:00 22:00"
                
                2. Date and time information:
                   - Extract the full date from the list item (e.g., "Saturday, January 18, 2025")
                   - From the time format "7:00 PM 10:00 PM 19:00 22:00":
                     * start_time is the first time (7:00 PM)
                     * end_time is the second time (10:00 PM)
                
                3. Genre and description:
                   - Look for genre tags before the title (e.g., "Jazz, Bebop")
                   - Description includes cover charge and seating info after the date/time list
                   - Common formats: "$15 Cover @ the Door / Start 8:30pm / Doors 8pm / Seated Show"
                
                Each event should be a separate object in the events array.
                Include all events found on the page, even if some fields are missing."""
        }

    def extract_events_with_retry(self, url):
        """Extract events with retry logic."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Attempt {attempt + 1} of {self.max_retries} to extract events from {url}")
                return self.extract_events(url)
            except RequestException as e:
                last_error = e
                self.logger.warning(f"API connection error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)  # Exponential backoff
                    self.logger.info(f"Waiting {wait_time} seconds before retrying...")
                    time.sleep(wait_time)
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
                raise

        self.logger.error(f"Failed to extract events after {self.max_retries} attempts")
        raise last_error or Exception("Failed to extract events")

    def extract_events(self, url):
        """Extract events from the given URL."""
        try:
            self.logger.info(f"Starting event extraction from {url}")
            
            schema = self.get_schema()
            self.logger.debug(f"Using schema: {json.dumps(schema, indent=2)}")
            
            # Call the API with just the extract parameter
            response = self.app.scrape_url(
                url,
                {
                    'extract': {
                        'schema': schema['schema'],
                        'systemPrompt': schema['systemPrompt']
                    }
                }
            )
            
            self.logger.debug(f"Raw API response keys: {list(response.keys())}")
            
            if response.get('error'):
                error_msg = response.get('error', {}).get('message', 'Unknown error')
                self.logger.error(f"API returned error: {error_msg}")
                if "Error connecting to Anthropic" in error_msg:
                    raise RequestException(f"Anthropic API connection error: {error_msg}")
                raise Exception(f"API error: {error_msg}")
            
            # Check for events in different possible response formats
            events_data = None
            
            # Try different possible locations for the events data
            if 'data' in response:
                self.logger.debug("Found 'data' key in response")
                if 'structured' in response['data']:
                    self.logger.debug("Found 'structured' key in data")
                    events_data = response['data']['structured'].get('events', [])
                elif 'extract' in response['data']:
                    self.logger.debug("Found 'extract' key in data")
                    events_data = response['data']['extract'].get('events', [])
            elif 'structured' in response:
                self.logger.debug("Found 'structured' key in root")
                events_data = response['structured'].get('events', [])
            elif 'extract' in response:
                self.logger.debug("Found 'extract' key in root")
                events_data = response['extract'].get('events', [])
            
            if events_data is None:
                self.logger.warning("No events data found in any expected location")
                self.logger.debug(f"Full response structure: {json.dumps(response, indent=2)}")
                return []
            
            self.logger.info(f"Found {len(events_data)} events in raw data")
            
            processed_events = self.process_events(events_data)
            self.logger.info(f"Successfully processed {len(processed_events)} events")
            
            return processed_events
            
        except RequestException:
            raise  # Re-raise connection errors for retry handling
        except Exception as e:
            self.logger.error(f"Error scraping {url}: {str(e)}\n{traceback.format_exc()}")
            return []

    async def extract_events_async(self, url):
        """Asynchronously extract events with polling."""
        try:
            self.logger.info(f"Starting async event extraction from {url}")
            
            schema = self.get_schema()
            self.logger.debug(f"Using schema: {json.dumps(schema, indent=2)}")
            
            # Start async extraction
            response = self.app.async_scrape_url(
                url,
                {
                    'formats': ['extract'],
                    'extract': {
                        'schema': schema['schema'],
                        'systemPrompt': schema['systemPrompt']
                    }
                }
            )
            
            if not response.get('success'):
                error_msg = response.get('error', {}).get('message', 'Unknown error')
                self.logger.error(f"Failed to start async extraction: {error_msg}")
                raise Exception(f"Async extraction failed: {error_msg}")
            
            job_id = response['id']
            self.logger.info(f"Started async extraction job {job_id}")
            
            # Poll for results
            while True:
                status = self.app.get_scrape_status(job_id)
                
                if status.get('status') == 'completed':
                    self.logger.info(f"Async extraction completed for job {job_id}")
                    return self.process_events(status.get('data', {}).get('extract', {}).get('events', []))
                
                elif status.get('status') == 'failed':
                    error_msg = status.get('error', 'Unknown error')
                    self.logger.error(f"Async extraction failed: {error_msg}")
                    raise Exception(f"Async extraction failed: {error_msg}")
                
                self.logger.debug(f"Job {job_id} still processing, waiting {self.poll_interval} seconds...")
                await time.sleep(self.poll_interval)
                
        except Exception as e:
            self.logger.error(f"Error in async extraction: {str(e)}\n{traceback.format_exc()}")
            raise

    async def extract_events_async_with_retry(self, url):
        """Asynchronously extract events with retry logic."""
        last_error = None
        for attempt in range(self.max_retries):
            try:
                self.logger.info(f"Attempt {attempt + 1} of {self.max_retries} to extract events from {url}")
                return await self.extract_events_async(url)
            except RequestException as e:
                last_error = e
                self.logger.warning(f"API connection error on attempt {attempt + 1}: {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (attempt + 1)  # Exponential backoff
                    self.logger.info(f"Waiting {wait_time} seconds before retrying...")
                    await time.sleep(wait_time)
                continue
            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}\n{traceback.format_exc()}")
                raise

        self.logger.error(f"Failed to extract events after {self.max_retries} attempts")
        raise last_error or Exception("Failed to extract events")

    def process_events(self, events_data):
        """Process the extracted events data using Pydantic models."""
        if not events_data or not isinstance(events_data, list):
            self.logger.warning(f"No valid events data found. Received: {events_data}")
            return []

        processed_events = []
        for event_data in events_data:
            try:
                # Create Pydantic model instance
                event = Event(**event_data)
                
                # Parse date and time
                if event.date and event.start_time:
                    try:
                        # Combine date and time
                        date_str = event.date.split(',', 1)[1].strip()  # Remove day of week
                        start_time_str = event.start_time.strip()
                        datetime_str = f"{date_str} {start_time_str}"
                        
                        # Parse with dateutil
                        start_time = parser.parse(datetime_str)
                        event.start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
                        
                        if event.end_time:
                            end_time_str = event.end_time.strip()
                            # Use the same date with end time
                            end_datetime_str = f"{date_str} {end_time_str}"
                            end_time = parser.parse(end_datetime_str)
                            event.end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        self.logger.error(f"Error parsing date/time for event: {e}")
                        self.logger.error(f"Date: {event.date}, Start: {event.start_time}, End: {event.end_time}")
                        continue
                
                processed_events.append(event.model_dump())
                self.logger.info(f"Successfully processed event: {event.title}")
                
            except Exception as e:
                self.logger.error(f"Error processing event: {e}")
                self.logger.error(f"Event data: {event_data}")
                self.logger.error(traceback.format_exc())
                continue
        
        return processed_events 