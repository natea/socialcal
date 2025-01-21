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
import argparse
import sys
from urllib.parse import urlparse, urljoin

# Load environment variables from .env file
load_dotenv()

# Set up logging
logger = logging.getLogger(__name__)

def parse_datetime(date_str: str, time_str: str) -> tuple[str, str]:
    """Parse date and time strings into Django's expected format.
    Returns a tuple of (date, time) strings."""
    logger.info(f"Parsing date: '{date_str}' and time: '{time_str}'")
    
    try:
        # Handle multi-day event format
        if '\n' in date_str or date_str.count(',') > 1:
            logger.info("Detected multi-day event format")
            # Split into lines and clean up
            lines = [line.strip() for line in date_str.split('\n') if line.strip()]
            if not lines:
                lines = [part.strip() for part in date_str.split(',') if part.strip()]
            
            # Extract the first date (start date)
            start_date_str = lines[0]
            # Remove day of week if present
            if ',' in start_date_str:
                start_date_str = start_date_str.split(',', 1)[1].strip()
            
            # Parse the start date
            try:
                start_date = datetime.strptime(start_date_str, '%B %d, %Y')
                formatted_date = start_date.strftime('%Y-%m-%d')
                logger.info(f"Parsed start date: {formatted_date}")
            except ValueError as e:
                logger.error(f"Error parsing start date: {str(e)}")
                return "", ""
            
            # Parse the time
            # For multi-day events, time is often included with the date
            # Example: "Saturday, January 25, 2025 10:30 PM"
            time_parts = time_str.strip().split()
            if len(time_parts) >= 2:
                time_str = ' '.join(time_parts[:2])  # Take first time as start time
                try:
                    time_obj = datetime.strptime(time_str, '%I:%M %p')
                    formatted_time = time_obj.strftime('%H:%M:%S')
                    logger.info(f"Parsed start time: {formatted_time}")
                    return formatted_date, formatted_time
                except ValueError as e:
                    logger.error(f"Error parsing time: {str(e)}")
                    return formatted_date, ""
            
            return formatted_date, ""
            
        # Handle single-day event format
        else:
            logger.info("Detected single-day event format")
            # Remove day of week if present
            if ',' in date_str:
                date_str = date_str.split(',', 1)[1].strip()
            
            # Parse the date
            try:
                date_obj = datetime.strptime(date_str, '%B %d, %Y')
                formatted_date = date_obj.strftime('%Y-%m-%d')
                logger.info(f"Parsed date: {formatted_date}")
            except ValueError as e:
                logger.error(f"Error parsing date: {str(e)}")
                return "", ""
            
            # Parse the time
            # Handle format "12:00 PM  3:00 PM"
            time_parts = time_str.strip().split()
            if len(time_parts) >= 2:
                start_time_str = ' '.join(time_parts[:2])  # Take first time as start time
                try:
                    time_obj = datetime.strptime(start_time_str, '%I:%M %p')
                    formatted_time = time_obj.strftime('%H:%M:%S')
                    logger.info(f"Parsed time: {formatted_time}")
                    return formatted_date, formatted_time
                except ValueError as e:
                    logger.error(f"Error parsing time: {str(e)}")
                    return formatted_date, ""
            
            return formatted_date, ""
            
    except Exception as e:
        logger.error(f"Error parsing datetime: {str(e)}")
        return "", ""

class EventListingModel(BaseModel):
    event_title: str = Field(..., description="Title of the event.")
    event_url: str = Field(..., description="URL of the event detail page.")
    event_date: str = Field(..., description="Date of the event (YYYY-MM-DD or MM/DD/YYYY).")
    event_start_time: str = Field(..., description="Start time of the event (HH:MM AM/PM).")
    event_venue: str = Field(..., description="Venue of the event.")
    event_image_url: str = Field(None, description="Image URL of the event.")

class EventDetailModel(BaseModel):
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

    def normalize_url(self, base_url: str, event_url: str) -> str:
        """Normalize and clean up event URLs."""
        logger.info(f"Normalizing URL - Base: {base_url}, Event: {event_url}")
        
        try:
            # Remove any XML/HTML-like brackets and tags
            event_url = re.sub(r'</?[^>]+/?>', '', event_url)
            event_url = event_url.strip('<>')
            
            # Remove any duplicate slashes, but preserve protocol slashes
            event_url = re.sub(r'([^:])//+', r'\1/', event_url)
            
            # Clean up any malformed parts
            event_url = event_url.replace('<//', '/').replace('/>', '/').replace('</', '/')
            
            # If it's already an absolute URL, just clean it and return
            if event_url.startswith(('http://', 'https://')):
                logger.info(f"URL is already absolute: {event_url}")
                return event_url
            
            # If it starts with a slash, append to domain
            if event_url.startswith('/'):
                # Extract domain from base_url
                parsed_base = urlparse(base_url)
                base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
                full_url = base_domain + event_url
                logger.info(f"Constructed absolute URL from base domain: {full_url}")
                return full_url
            
            # Otherwise, join with base URL
            full_url = urljoin(base_url, event_url)
            logger.info(f"Joined with base URL: {full_url}")
            return full_url
        
        except Exception as e:
            logger.error(f"Error normalizing URL: {str(e)}")
            return event_url

    async def extract_event_listings(self, url: str) -> List[dict]:
        """Extract event listings from the main events page."""
        logger.info(f"Starting event listings extraction from {url}...")
        logger.info("=" * 80)
        logger.info("PHASE 1: EVENT LISTINGS EXTRACTION")
        logger.info("=" * 80)

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
                schema=EventListingModel.model_json_schema(),
                extraction_type="schema",
                instruction="""From the events listing page, extract basic event information:
                1. Title of the event
                2. URL to the event's detail page
                3. Date of the event
                4. Start time
                5. Venue name
                6. Event image URL if available
                
                Focus on finding the links to individual event detail pages.
                These are crucial for the second pass of crawling.
                Look for elements that link to full event details, typically in event cards or listings.
                
                For URLs:
                - Look for <a> tags that link to individual event pages
                - Extract the href attribute exactly as is, do not modify or add to it
                - Do not add any prefixes or suffixes to the URLs
                - Do not wrap URLs in XML/HTML tags
                - Common URL patterns are:
                  * /event/[id]-[slug]
                  * /events/[id]
                  * /[year]/[month]/[slug]
                
                For Images:
                - Look for <img> tags within event cards or listings
                - Check for both src and data-src attributes
                - Look for high-resolution versions in data-* attributes
                - Common locations: event thumbnails, featured images, gallery previews
                - Make sure to get the full absolute URL for images""",
                extra_args=extra_args,
            ),
        )

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                logger.info("Initialized crawler with configuration:")
                logger.info(f"- Browser: Headless={browser_config.headless}, Viewport={browser_config.viewport_width}x{browser_config.viewport_height}")
                logger.info(f"- Cache Mode: {crawler_config.cache_mode}")
                logger.info(f"- Page Timeout: {crawler_config.page_timeout}ms")
                
                logger.info("\nStarting page crawl...")
                result = await crawler.arun(
                    url=url,
                    config=crawler_config
                )
                logger.info("Raw page crawl completed")
                
                # Convert the extracted content to list if it's not already
                listings_data = result.extracted_content
                if isinstance(listings_data, str):
                    logger.info("Parsing JSON string response...")
                    listings_data = json.loads(listings_data)
                if not isinstance(listings_data, list):
                    logger.info("Converting single event to list...")
                    listings_data = [listings_data]

                logger.info(f"\nFound {len(listings_data)} potential event listings")
                
                # Log details about each listing
                normalized_listings = []
                for i, listing in enumerate(listings_data, 1):
                    logger.info(f"\nEvent Listing #{i}:")
                    logger.info(f"- Title: {listing.get('event_title', 'N/A')}")
                    
                    # URL normalization and logging
                    original_url = listing.get('event_url', '')
                    logger.info(f"- Original URL: {original_url}")
                    
                    if original_url:
                        normalized_url = self.normalize_url(url, original_url)
                        logger.info(f"- Normalized URL: {normalized_url}")
                        listing['event_url'] = normalized_url
                    else:
                        logger.error("  ✗ No URL found for this event")
                    
                    # Image URL normalization and logging
                    original_image_url = listing.get('event_image_url', '')
                    logger.info(f"- Original Image URL: {original_image_url}")
                    
                    if original_image_url:
                        normalized_image_url = self.normalize_url(url, original_image_url)
                        logger.info(f"- Normalized Image URL: {normalized_image_url}")
                        listing['event_image_url'] = normalized_image_url
                    else:
                        logger.warning("  ⚠ No image URL found in listing, will try detail page")
                    
                    logger.info(f"- Date: {listing.get('event_date', 'N/A')}")
                    logger.info(f"- Start Time: {listing.get('event_start_time', 'N/A')}")
                    logger.info(f"- Venue: {listing.get('event_venue', 'N/A')}")
                    
                    normalized_listings.append(listing)

                logger.info("\nListings extraction completed successfully")
                return normalized_listings

        except Exception as e:
            logger.error(f"Error during listings crawl: {str(e)}")
            raise

    async def extract_event_details(self, event_url: str) -> dict:
        """Extract detailed event information from an event's detail page."""
        logger.info("=" * 80)
        logger.info(f"PHASE 2: EVENT DETAIL EXTRACTION - {event_url}")
        logger.info("=" * 80)

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
                schema=EventDetailModel.model_json_schema(),
                extraction_type="schema",
                instruction="""From this event detail page, extract complete event information:
                1. Title of the event
                2. Full description
                3. Date
                4. Start and end times
                5. Venue details (name, address, city, state, zip, country)
                6. Event URL
                7. Event image URL
                
                Pay special attention to:
                - The complete event description (look for detailed text blocks)
                - Venue information (often in sidebars or footer sections)
                - Date/time information (check for timezone indicators)
                - Any ticket or pricing information in the description
                
                If any field is not found, leave it blank rather than making assumptions.""",
                extra_args=extra_args,
            ),
        )

        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                logger.info("\nStarting detail page extraction...")
                logger.info(f"Target URL: {event_url}")
                
                result = await crawler.arun(
                    url=event_url,
                    config=crawler_config
                )
                logger.info("Raw detail page crawl completed")
                
                event_data = result.extracted_content
                if isinstance(event_data, str):
                    logger.info("Parsing JSON string response...")
                    event_data = json.loads(event_data)
                if isinstance(event_data, list) and len(event_data) > 0:
                    logger.info("Multiple events found, using first event...")
                    event_data = event_data[0]

                # Log extracted details
                logger.info("\nExtracted Event Details:")
                logger.info(f"- Title: {event_data.get('event_title', 'N/A')}")
                logger.info(f"- Date: {event_data.get('event_date', 'N/A')}")
                logger.info(f"- Start Time: {event_data.get('event_start_time', 'N/A')}")
                logger.info(f"- End Time: {event_data.get('event_end_time', 'N/A')}")
                logger.info(f"- Venue: {event_data.get('event_venue', 'N/A')}")
                logger.info(f"- Address: {event_data.get('event_venue_address', 'N/A')}")
                logger.info(f"- City: {event_data.get('event_venue_city', 'N/A')}")
                logger.info(f"- State: {event_data.get('event_venue_state', 'N/A')}")
                logger.info(f"- ZIP: {event_data.get('event_venue_zip', 'N/A')}")
                logger.info(f"- Country: {event_data.get('event_venue_country', 'N/A')}")
                logger.info(f"- Has Image URL: {'Yes' if event_data.get('event_image_url') else 'No'}")
                
                desc = event_data.get('event_description', '')
                desc_preview = desc[:100] + '...' if len(desc) > 100 else desc
                logger.info(f"- Description Preview: {desc_preview}")

                logger.info("\nDetail extraction completed successfully")
                return event_data

        except Exception as e:
            logger.error(f"Error during detail crawl: {str(e)}")
            raise

    async def extract_events(self, url: str) -> List[dict]:
        """Extract events using a two-pass approach: first get listings, then details."""
        logger.info(f"Starting two-pass event extraction from {url}...")

        try:
            # First pass: Get event listings
            listings = await self.extract_event_listings(url)
            logger.info(f"Found {len(listings)} event listings")

            # Second pass: Get detailed information for each event
            detailed_events = []
            for listing in listings:
                try:
                    event_url = listing.get('event_url')
                    if not event_url:
                        logger.warning(f"No URL found for event: {listing.get('event_title')}")
                        continue

                    # Get detailed event information
                    event_details = await self.extract_event_details(event_url)
                    
                    # Process the event details
                    try:
                        # Parse date and time
                        date, start_time = parse_datetime(
                            event_details.get('event_date', ''),
                            event_details.get('event_start_time', '')
                        )
                        
                        # Parse end time if available
                        _, end_time = parse_datetime(
                            event_details.get('event_date', ''),
                            event_details.get('event_end_time', '')
                        ) if event_details.get('event_end_time') else ("", "")

                        # Combine date and time for Django format with timezone
                        tz = pytz.timezone('America/New_York')
                        start_datetime = None
                        end_datetime = None
                        
                        if date and start_time:
                            try:
                                dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
                                start_dt = tz.localize(dt)
                                start_datetime = start_dt.strftime("%Y-%m-%d %H:%M:%S%z")
                                
                                if not end_time:
                                    end_dt = start_dt + timedelta(hours=2)
                                    end_datetime = end_dt.strftime("%Y-%m-%d %H:%M:%S%z")
                                else:
                                    dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")
                                    end_dt = tz.localize(dt)
                                    end_datetime = end_dt.strftime("%Y-%m-%d %H:%M:%S%z")
                            except Exception as e:
                                logger.error(f"Error creating datetime: {str(e)}")

                        # Handle image URL with fallback logic
                        image_url = listing.get('event_image_url')  # Try listing page image first
                        if not image_url:
                            logger.info("No image URL from listing page, trying detail page...")
                            detail_image_url = event_details.get('event_image_url')
                            if detail_image_url:
                                image_url = self.normalize_url(event_url, detail_image_url)
                                logger.info(f"Found image URL on detail page: {image_url}")
                            else:
                                logger.warning("No image URL found on either listing or detail page")

                        formatted_event = {
                            'title': event_details.get('event_title', ''),
                            'description': event_details.get('event_description', ''),
                            'start_time': start_datetime,
                            'end_time': end_datetime,
                            'venue_name': event_details.get('event_venue', ''),
                            'venue_address': event_details.get('event_venue_address', ''),
                            'venue_city': event_details.get('event_venue_city', ''),
                            'venue_state': event_details.get('event_venue_state', ''),
                            'venue_zip': event_details.get('event_venue_zip', ''),
                            'venue_country': event_details.get('event_venue_country', ''),
                            'url': event_details.get('event_url', ''),
                            'image_url': image_url,
                        }

                        logger.info(f"Formatted event: {json.dumps(formatted_event, indent=2)}")
                        detailed_events.append(formatted_event)
                    except Exception as e:
                        logger.error(f"Error processing event details: {str(e)}")
                        continue

                except Exception as e:
                    logger.error(f"Error getting details for event {listing.get('event_title')}: {str(e)}")
                    continue

            logger.info(f"Successfully processed {len(detailed_events)} events")
            return detailed_events

        except Exception as e:
            logger.error(f"Error during two-pass crawling: {str(e)}")
            raise

async def scrape_events(url: str) -> List[dict]:
    """Helper function to scrape events from any URL."""
    scraper = GenericCrawl4AIScraper()
    return await scraper.extract_events(url)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test the Crawl4AI event scraper')
    parser.add_argument('url', help='URL to scrape')
    parser.add_argument('--mode', choices=['full', 'listings', 'detail'], default='full',
                       help='Scraping mode: full (both passes), listings (first pass only), or detail (single detail page)')
    parser.add_argument('--pretty', action='store_true', help='Pretty print the JSON output')

    args = parser.parse_args()

    async def main():
        try:
            scraper = GenericCrawl4AIScraper()
            
            if args.mode == 'full':
                logger.info(f"Running full two-pass scrape on {args.url}")
                events = await scraper.extract_events(args.url)
                if args.pretty:
                    print(json.dumps(events, indent=2))
                else:
                    print(json.dumps(events))
                logger.info(f"Found {len(events)} events")
                
            elif args.mode == 'listings':
                logger.info(f"Running listings-only scrape on {args.url}")
                listings = await scraper.extract_event_listings(args.url)
                if args.pretty:
                    print(json.dumps(listings, indent=2))
                else:
                    print(json.dumps(listings))
                logger.info(f"Found {len(listings)} event listings")
                
            elif args.mode == 'detail':
                logger.info(f"Running detail-only scrape on {args.url}")
                details = await scraper.extract_event_details(args.url)
                if args.pretty:
                    print(json.dumps(details, indent=2))
                else:
                    print(json.dumps(details))
                logger.info("Detail scrape complete")

        except Exception as e:
            logger.error(f"Error during scraping: {str(e)}")
            sys.exit(1)

    asyncio.run(main()) 