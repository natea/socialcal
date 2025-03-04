import asyncio
import os
import json
import re
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from django.utils import timezone
from django.conf import settings
from asgiref.sync import sync_to_async

from crawl4ai import (
    AsyncWebCrawler, 
    CrawlerRunConfig,
    JsonCssExtractionStrategy,
    CacheMode
)

# Set up logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Function to transform relative URLs to absolute URLs
def transform_url(url, base_url):
    if not url:
        return None
    
    # Skip base64 encoded images
    if url and isinstance(url, str) and url.startswith('data:image'):
        return None
    
    # Handle background-image CSS property
    if url and isinstance(url, str) and 'background-image:' in url:
        # Extract URL from background-image: url('...')
        match = re.search(r"url\(['\"]?(https?://[^'\")]+)['\"]?\)", url)
        if match:
            url = match.group(1)
        else:
            return None
    
    # If the URL is already absolute, return it as is
    if url and isinstance(url, str) and (url.startswith('http://') or url.startswith('https://')):
        return url
    
    # Parse the base URL to get the domain
    from urllib.parse import urlparse, urljoin
    
    # Make sure base_url is properly formatted
    if base_url and not (base_url.startswith('http://') or base_url.startswith('https://')):
        base_url = 'https://' + base_url
    
    # For any site, ensure we're using the correct base URL (scheme + netloc)
    # This ensures that relative paths like "/path/to/page" work correctly
    try:
        parsed_url = urlparse(base_url)
        # Use the scheme and netloc as the base for relative URLs
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # If the URL starts with a slash, it's relative to the domain root
        if url and isinstance(url, str) and url.startswith('/'):
            absolute_url = f"{base_domain}{url}"
        else:
            # Otherwise use urljoin which handles other relative URL formats
            absolute_url = urljoin(base_url, url)
            
        logger.debug(f"Transformed URL: {url} -> {absolute_url} (base: {base_url})")
        return absolute_url
    except Exception as e:
        logger.error(f"Error transforming URL {url} with base {base_url}: {str(e)}")
        return url

async def generate_css_schema(url: str, api_key: str = None) -> Dict:
    """
    Generate a CSS schema for extracting event information from a website.
    
    Args:
        url: The URL of the website to generate a schema for
        api_key: The API key for the LLM provider (Gemini)
        
    Returns:
        A dictionary containing the CSS schema
    """
    # Use the API key from the settings if not provided
    if not api_key:
        api_key = getattr(settings, 'GEMINI_API_KEY', os.environ.get('GEMINI_API_KEY'))
    
    if not api_key:
        raise ValueError("No API key provided for schema generation")
    
    logger.info(f"Generating CSS schema for {url}")
    
    # Initialize the crawler
    crawler = AsyncWebCrawler()
    
    try:
        # Fetch the HTML content from the target URL
        async with crawler:
            # Simple run to get the HTML content
            fetch_result = await crawler.arun(url)
            
            if not fetch_result.success:
                logger.error(f"Failed to fetch content from {url}")
                return None
                
            html_content = fetch_result.html
            
            if not html_content:
                logger.error("No HTML content found in the response")
                return None
                
            logger.info(f"Successfully fetched HTML content ({len(html_content)} bytes)")
            
            # Define a comprehensive query to guide the LLM
            query = """
            You are an expert web scraper. I need to extract event information from a given URL.
            
            IMPORTANT: Your task is to create a CSS selector schema that will extract ALL events from the page.
            
            First, analyze the HTML structure to identify:
            1. The container elements that hold each individual event
            2. The elements within each container that hold specific event details
            
            Create a CSS selector schema to extract the following fields for EACH event on the page:
            1. Event title
            2. Date (this might be combined with time)
            3. Start time (if available separately)
            4. End time (if available separately)
            5. Location
            6. Description (if available)
            7. URL (the link to the event details)
            8. Image URL (if available)
            
            CRITICAL GUIDELINES:
            - Each selector should target ALL instances of that field across ALL events on the page.
            - Make sure your selectors are specific enough to get the right content but general enough to work for all events.
            - For URLs and images, select the attribute (href, src) not just the element.
            - IMPORTANT: For images, check for both 'src' and 'data-src' attributes, as many sites use lazy loading.
              Look for img tags with class names containing 'image', 'thumbnail', 'photo', 'pic', etc.
            - If date and time are combined in one element, just use the 'date' field to capture both.
            - Test your selectors mentally to ensure they will extract ALL events, not just the first one.
            - Events are typically in elements with class names containing 'event', 'item', or 'entry'
            - Look for repeating patterns of elements with similar structure
            
            Return ONLY a JSON object with field names as keys and CSS selectors as values.
            For example:
            {
              "title": ".event-list .event-item .title",
              "date": ".event-list .event-item .date-time",
              "start_time": ".event-list .event-item .start-time",
              "end_time": ".event-list .event-item .end-time",
              "location": ".event-list .event-item .location",
              "description": ".event-list .event-item .description",
              "url": {"selector": ".event-list .event-item a.event-link", "attribute": "href"},
              "image_url": {"selector": ".event-list .event-item img", "attribute": "src"}
            }
            
            If you need to extract attributes, use the following format:
            {
              "url": {"selector": ".event-item a", "attribute": "href"},
              "image_url": {"selector": ".event-item img", "attribute": "src"}
            }
            
            For images with lazy loading, use data-src attribute:
            {
              "image_url": {"selector": ".event-item img", "attribute": "data-src"}
            }
            
            For background images in style attributes, use:
            {
              "image_url": {"selector": ".event-item .image", "attribute": "style"}
            }
            
            """
            
            # Generate the CSS schema
            css_schema = JsonCssExtractionStrategy.generate_schema(
                html_content,
                schema_type="CSS",
                query=query,
                provider="gemini/gemini-2.0-flash-lite",
                api_token=api_key
            )
            
            # Post-process the schema to remove baseSelector if present
            if isinstance(css_schema, dict) and 'baseSelector' in css_schema:
                logger.warning("Found baseSelector in schema, keeping it for proper event extraction")
                # We'll keep the baseSelector as it's important for extracting multiple events
                
                # If the schema has a 'fields' key, extract the fields and restructure
                if 'fields' in css_schema:
                    fields = css_schema.pop('fields', [])
                    for field in fields:
                        field_name = field.get('name')
                        if not field_name:
                            continue
                            
                        if field.get('type') == 'attribute' and 'attribute' in field:
                            css_schema[field_name] = {
                                'selector': field.get('selector'),
                                'attribute': field.get('attribute')
                            }
                        else:
                            css_schema[field_name] = field.get('selector')
            
            logger.info(f"Generated CSS schema: {json.dumps(css_schema, indent=2)}")
            
            return css_schema
    except Exception as e:
        logger.error(f"Error generating CSS schema: {str(e)}")
        raise

async def run_css_schema(url: str, css_schema: Dict) -> List[Dict]:
    """
    Test a CSS schema against a website to extract events.
    
    Args:
        url: The URL of the website to test the schema against
        css_schema: The CSS schema to test
        
    Returns:
        A list of extracted events
    """
    logger.info(f"Testing CSS schema against {url}")
    
    # Check if the schema is valid
    if not css_schema or not isinstance(css_schema, dict) or len(css_schema) == 0:
        logger.error("Invalid or empty CSS schema")
        return []
    
    # Log the schema being used
    logger.info(f"Using CSS schema: {json.dumps(css_schema, indent=2)}")
    
    # Create a deep copy of the schema to avoid modifying the original
    schema_copy = json.loads(json.dumps(css_schema))
    
    # Convert the schema to the format expected by JsonCssExtractionStrategy
    extraction_schema = {
        "fields": []
    }
    
    # If the schema has a baseSelector, use it, otherwise we'll use individual selectors
    if 'baseSelector' in schema_copy:
        base_selector = schema_copy.pop('baseSelector')
        # Handle case where baseSelector might be in a dictionary with a 'name' key
        if isinstance(base_selector, dict) and 'name' in base_selector:
            extraction_schema["baseSelector"] = base_selector['name']
        else:
            extraction_schema["baseSelector"] = base_selector
    else:
        # If there's no baseSelector, we need to add a dummy one that matches all elements
        # This is because the extraction strategy requires a baseSelector
        extraction_schema["baseSelector"] = "html"  # Match the entire document
    
    # Remove any other non-field keys that might cause issues
    for key in ['name', 'fields']:
        if key in schema_copy:
            schema_copy.pop(key)
    
    # Add fields from the CSS schema
    for key, value in schema_copy.items():
        if isinstance(value, dict) and 'selector' in value and 'attribute' in value:
            # Handle fields with attributes
            extraction_schema["fields"].append({
                "name": key,
                "type": "attribute",
                "selector": value["selector"],
                "attribute": value["attribute"]
            })
        else:
            # Handle simple text fields
            extraction_schema["fields"].append({
                "name": key,
                "type": "text",
                "selector": value
            })
    
    # Add generic data-src image detection if not already present
    has_data_src_field = False
    for field in extraction_schema["fields"]:
        # Check if we already have a field that uses data-src attribute
        if field.get('type') == 'attribute' and field.get('attribute') == 'data-src':
            has_data_src_field = True
            break
    
    # If no data-src field exists, add a generic one that looks for common image elements
    if not has_data_src_field:
        # Look for any img tag with data-src attribute
        extraction_schema["fields"].append({
            "name": "data_image_url",
            "type": "attribute",
            "selector": "img[data-src]",
            "attribute": "data-src"
        })
    
    logger.info(f"Converted schema for extraction: {json.dumps(extraction_schema, indent=2)}")
    
    # Initialize the crawler
    crawler = AsyncWebCrawler()
    
    try:
        # Create an extraction strategy with the provided schema
        extraction_strategy = JsonCssExtractionStrategy(schema=extraction_schema)
        
        # Configure the crawler with enhanced settings for dynamic content
        config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy, 
            verbose=True,
            cache_mode=CacheMode.BYPASS,  # Ensure we're not using cached content
            delay_before_return_html=6.0,  # Increase wait time for JavaScript content to load
            wait_for_selector=extraction_schema["baseSelector"]  # Wait for the base selector to be present
        )
        
        # Add URL transformation to the config
        config.field_transformers = {
            "url": lambda url, context: transform_url(url, context.get("url", url)),
            "image_url": lambda url, context: transform_url(url, context.get("url", url)),
            "data_image_url": lambda url, context: transform_url(url, context.get("url", url))
        }
        
        # Run the crawler
        async with crawler:
            result = await crawler.arun(url=url, config=config)
            
            if not result.success:
                if hasattr(result, 'error') and result.error:
                    logger.error(f"Failed to extract content: {result.error}")
                else:
                    logger.error("Failed to extract content: Unknown error")
                return []
            
            # Parse the extracted content
            events = json.loads(result.extracted_content)
            
            # Format the events
            formatted_events = []
            for event in events:
                # Format the event data
                formatted_event = {
                    "title": event.get("title", ""),
                    "description": event.get("description", ""),
                    "date": event.get("date", ""),
                    "start_time": event.get("start_time", ""),
                    "end_time": event.get("end_time", ""),
                    "location": event.get("location", ""),
                    "url": event.get("url", ""),
                    "image_url": event.get("image_url", "")
                }
                
                # Handle case where date field contains both date and time information
                if formatted_event["date"] and (not formatted_event["start_time"] or formatted_event["start_time"] == ""):
                    # Check if date field might contain time information
                    if ':' in formatted_event["date"] or ' at ' in formatted_event["date"].lower() or '-' in formatted_event["date"]:
                        from ..utils.time_parser import extract_date_time_from_string
                        
                        # Extract date, start time, and possibly end time
                        extracted_date, extracted_start, extracted_end = extract_date_time_from_string(formatted_event["date"])
                        
                        if extracted_date:
                            formatted_event["date"] = extracted_date
                        if extracted_start:
                            formatted_event["start_time"] = extracted_start
                        if extracted_end:
                            formatted_event["end_time"] = extracted_end
                            
                        logger.info(f"Extracted from date field - date: '{formatted_event['date']}', "
                                   f"start: '{formatted_event['start_time']}', end: '{formatted_event['end_time']}'")
                
                # Use data-src image if regular image_url is empty
                if not formatted_event["image_url"] and event.get("data_image_url"):
                    formatted_event["image_url"] = event.get("data_image_url")
                
                # Ensure URLs are absolute
                if formatted_event["url"] and isinstance(formatted_event["url"], str):
                    formatted_event["url"] = transform_url(formatted_event["url"], url)
                
                if formatted_event["image_url"] and isinstance(formatted_event["image_url"], str):
                    formatted_event["image_url"] = transform_url(formatted_event["image_url"], url)
                
                # Log the formatted event
                logger.info(f"Formatted event: {formatted_event}")
                
                formatted_events.append(formatted_event)
            
            logger.info(f"Extracted {len(formatted_events)} events")
            
            return formatted_events
    except Exception as e:
        logger.error(f"Error testing CSS schema: {str(e)}")
        logger.error(f"CSS schema that caused the error: {json.dumps(css_schema, indent=2)}")
        return []

async def scrape_with_site_scraper(scraper_id: int) -> List[Dict]:
    """
    Scrape events using a stored site scraper.
    
    Args:
        scraper_id: The ID of the site scraper to use
        
    Returns:
        A list of extracted events
    """
    from ..models import SiteScraper
    
    try:
        # Get the site scraper
        scraper = await sync_to_async(SiteScraper.objects.get)(pk=scraper_id)
        
        # Test the CSS schema
        events = await run_css_schema(scraper.url, scraper.css_schema)
        
        # Update the last tested timestamp and test results
        scraper.last_tested = timezone.now()
        scraper.test_results = {
            'timestamp': timezone.now().isoformat(),
            'events_count': len(events),
            'events': events[:5]  # Store only the first 5 events to avoid storing too much data
        }
        await sync_to_async(scraper.save)()
        
        return events
    except Exception as e:
        logger.error(f"Error scraping with site scraper {scraper_id}: {str(e)}")
        raise 