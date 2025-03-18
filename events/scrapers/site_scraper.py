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
from bs4 import BeautifulSoup
import aiohttp
import litellm
from litellm import completion

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
        api_key = os.environ.get('GEMINI_API_KEY') or getattr(settings, 'GEMINI_API_KEY', None)
    if not api_key:
        raise ValueError("No API key provided for schema generation")
    
    logger.info(f"Generating CSS schema for {url}")
    
    # Initialize the crawler
    crawler = AsyncWebCrawler(
        use_stealth=True,  # Enables headless browsing for JS-rendered pages
        max_depth=1,
        bypass_robots=True,
    )
    
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
            
            # Define an improved query with better guidance for title detection
            query = """
            You are an expert web scraper. I need to extract event information from a given URL.
            
            The page structure has events listed as cards. Each event card likely contains:
            - Event title (probably in a heading element like h1, h2, h3, or h4, or might have specific CSS classes)
            - Date and time information
            - Location information
            - Possibly an image
            - Possibly a link to the event details
            
            Create a CSS selector schema to extract the following fields for EACH event on the page:
            1. Event title
            2. Date
            3. Start time
            4. End time (if available)
            5. Location
            6. Description (if available)
            7. URL (the link to the event details)
            8. Image URL (if available)
            
            IMPORTANT NOTES FOR TITLE SELECTION:
            - The title is the most important element to identify correctly
            - Check for heading elements (h1, h2, h3, h4) within event cards
            - Look for elements with classes containing words like "title", "heading", or "name"
            - If you can't find specific title classes, fallback to the most prominent text in each card
            - For Eventbrite specifically, titles are often in h3 elements
            
            IMPORTANT NOTES FOR ALL SELECTORS:
            - Your selectors should target EACH individual event item, not just the first one
            - If events are in a list or grid, make sure your selectors will work for ALL events
            - For URLs, select the HREF attribute of the link, not just the element itself
            - For image URLs, select the SRC attribute of the image, not just the element itself
            - AVOID selecting base64-encoded images. Look for real image URLs that start with http:// or https://
            - If there are multiple image sources available, prefer the one with the highest resolution or quality
            - IMPORTANT: Some websites use CSS background-image in style attributes instead of img tags. Look for elements with style attributes containing "background-image: url(...)" and extract those URLs
            - IMPORTANT: Check for both "src" and "data-src" attributes on image elements. Some sites use lazy loading and store the real image URL in data-src
            
            Return ONLY a JSON object with field names as keys and CSS selectors as values.
            For example:
            {
              "title": ".event-card .title",
              "date": ".event-card .date",
              "start_time": ".event-card .start_time",
              "end_time": ".event-card .end_time",
              "location": ".event-card .location",
              "description": ".event-card .description",
              "url": ".event-card a[href]",
              "image_url": ".event-card img[src]"
            }
            
            If you need to extract attributes, use the following format:
            {
              "url": {"selector": ".event-card a", "attribute": "href"},
              "image_url": {"selector": ".event-card img", "attribute": "src"},
              "data_image_url": {"selector": ".event-card img", "attribute": "data-src"}
            }
            
            For background images in style attributes, use:
            {
              "image_url": {"selector": ".event-card .image", "attribute": "style"}
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
            
            # Post-process the schema to validate and enhance it
            enhanced_schema = await _enhance_generated_schema(css_schema, html_content, url)
            
            # Log the generated schema
            logger.info(f"Generated CSS schema: {json.dumps(enhanced_schema, indent=2)}")
            
            return enhanced_schema
    except Exception as e:
        logger.error(f"Error generating CSS schema: {str(e)}")
        raise

async def _enhance_generated_schema(schema: dict, html: str, url: str) -> dict:
    """
    Validate and enhance the generated schema by checking for common title selectors
    and inferring missing selectors.
    """
    if not schema:
        logger.warning("Cannot enhance empty schema")
        return schema

    # Make a copy of the original schema to avoid modifying it directly
    enhanced_schema = schema.copy()
    
    try:
        # Parse HTML with BeautifulSoup to test selectors
        soup = BeautifulSoup(html, 'html.parser')
        
        # Ensure baseSelector exists and works
        base_selector = schema.get('baseSelector')
        if not base_selector or not soup.select(base_selector):
            # Try to find a better base selector
            potential_base_selectors = [
                "article.event-card", "div.event-card", ".SearchResultPanelContentEventCard-module__card", 
                "article[data-event-id]", "div[data-event-id]",
                "div[class*='event-card']", "div[class*='event-listing']",
                "div:has(h3):has(.event-date)", "div:has(h3):has(time)"
            ]
            
            for selector in potential_base_selectors:
                elements = soup.select(selector)
                if elements and len(elements) > 0:
                    logger.info(f"Found {len(elements)} base elements with selector: {selector}")
                    enhanced_schema['baseSelector'] = selector
                    break
        
        # Check if title selector is missing or not working
        title_selector = schema.get('title')
        if isinstance(title_selector, dict):
            title_selector = title_selector.get('selector')
        
        title_elements = []
        if title_selector:
            title_elements = soup.select(f"{base_selector} {title_selector}")
        
        if not title_elements or len(title_elements) == 0:
            # Title selector is not working, try common alternatives
            potential_title_selectors = ["h3", "h2", "h4", ".title", "[class*='title']", "[class*='event-name']"]
            
            for selector in potential_title_selectors:
                title_elements = soup.select(f"{base_selector} {selector}")
                if title_elements and len(title_elements) > 0:
                    logger.info(f"Found {len(title_elements)} title elements with selector: {selector}")
                    enhanced_schema['title'] = selector
                    break
        
        # Check if date selector is extracting promotional text
        date_selector = schema.get('date')
        if isinstance(date_selector, dict):
            date_selector = date_selector.get('selector')
            
        if date_selector:
            date_elements = soup.select(f"{base_selector} {date_selector}")
            
            # Check if date elements contain promotional text
            promo_texts = ["almost full", "going fast", "sales end soon", "save", "share", "popular", "selling fast"]
            date_is_promo = False
            
            if date_elements:
                sample_texts = [el.text.strip().lower() for el in date_elements[:5]]
                date_is_promo = any(any(promo in text for promo in promo_texts) for text in sample_texts)
                
                if date_is_promo:
                    logger.info(f"Date selector '{date_selector}' is extracting promotional text, attempting to find better selector")
            
            # If the date selector is not working or is extracting promo text, try alternatives
            if not date_elements or len(date_elements) == 0 or date_is_promo:
                # Look for elements with month names or time patterns
                month_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
                time_pattern = r'\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)'
                
                # Find all potential date elements
                potential_date_elements = []
                
                for element in soup.select(f"{base_selector} span, {base_selector} p, {base_selector} div, {base_selector} time"):
                    text = element.text.strip()
                    
                    # Skip promotional messages
                    if any(promo in text.lower() for promo in promo_texts):
                        continue
                    
                    # Check for month names or time patterns
                    is_date = bool(re.search(month_pattern, text) or re.search(time_pattern, text))
                    
                    if is_date:
                        # Get the CSS selector for this element
                        for parent in element.parents:
                            if parent.name and soup.select(f"{base_selector} {parent.name}"):
                                css_classes = parent.get('class', [])
                                if css_classes:
                                    class_selector = f"{parent.name}.{'.'.join(css_classes)}"
                                    potential_date_elements.append((class_selector, 1))
                                break
                
                # If no specific date elements found, try common date selectors
                if not potential_date_elements:
                    logger.info("Using fallback date/time selector: span:contains('PM'), span:contains('AM')")
                    enhanced_schema['date'] = "span:contains('PM'), span:contains('AM')"
                    enhanced_schema['start_time'] = "span:contains('PM'), span:contains('AM')"
                else:
                    # Use the most common date selector
                    selector_counts = {}
                    for selector, count in potential_date_elements:
                        selector_counts[selector] = selector_counts.get(selector, 0) + count
                    
                    best_selector = max(selector_counts.items(), key=lambda x: x[1])[0]
                    enhanced_schema['date'] = best_selector
                    enhanced_schema['start_time'] = best_selector
        
        # Ensure all required fields exist
        required_fields = ['title', 'date', 'start_time', 'location', 'url', 'image_url']
        for field in required_fields:
            if field not in enhanced_schema:
                if field == 'url':
                    enhanced_schema[field] = {
                        'selector': 'a',
                        'attribute': 'href'
                    }
                elif field == 'image_url':
                    enhanced_schema[field] = {
                        'selector': 'img',
                        'attribute': 'src'
                    }
                else:
                    enhanced_schema[field] = None
        
        # Ensure the schema structure is compatible with run_css_schema
        # If we're not working with an existing 'fields' format, we need to normalize
        if 'fields' not in enhanced_schema:
            fields = []
            for key, value in list(enhanced_schema.items()):
                if key not in ['name', 'baseSelector', 'fields'] and not key.startswith('_'):
                    field_entry = {
                        'name': key,
                        'type': 'text'
                    }
                    
                    if isinstance(value, dict):
                        field_entry['selector'] = value.get('selector')
                        field_entry['attribute'] = value.get('attribute')
                    else:
                        field_entry['selector'] = value
                    
                    fields.append(field_entry)
            
            enhanced_schema['fields'] = fields
            
            # Retain the top-level keys for compatibility with the old format
            for field in fields:
                field_name = field['name']
                if isinstance(enhanced_schema.get(field_name), dict):
                    # Keep the original structure for dict fields
                    continue
                else:
                    enhanced_schema[field_name] = field['selector']
        
        return enhanced_schema
    
    except Exception as e:
        logger.error(f"Error enhancing schema: {str(e)}")
        return schema  # Return original schema if enhancement fails

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
    
    # Ensure the schema has the required 'fields' key for the crawler
    schema_for_crawler = css_schema.copy()
    if 'fields' not in schema_for_crawler:
        # We need to convert the flattened format to the format with 'fields' list
        fields = []
        field_keys = ['title', 'date', 'start_time', 'end_time', 'location', 'description', 'url', 'image_url']
        
        for key in field_keys:
            if key in schema_for_crawler:
                field_value = schema_for_crawler[key]
                
                # Convert simple selector string to field object
                if isinstance(field_value, str):
                    fields.append({
                        'name': key,
                        'selector': field_value,
                        'type': 'text'
                    })
                # Handle complex selectors with attributes
                elif isinstance(field_value, dict) and 'selector' in field_value:
                    field_obj = {
                        'name': key,
                        'selector': field_value['selector'],
                        'type': 'attribute'
                    }
                    if 'attribute' in field_value:
                        field_obj['attribute'] = field_value['attribute']
                    fields.append(field_obj)
        
        schema_for_crawler['fields'] = fields
        logger.info(f"Added 'fields' list to schema for crawler compatibility")
    
    # Initialize the crawler
    crawler = AsyncWebCrawler(
        use_stealth=True,  # Enables headless browsing for JS-rendered pages
        max_depth=1,
        bypass_robots=True,
    )
    
    try:
        # Add a data-src selector for image URLs if it doesn't exist already
        # This will be processed alongside the normal image_url field
        if "image_url" in css_schema and "data_image_url" not in css_schema:
            # If image_url is a simple selector string
            if isinstance(css_schema["image_url"], str):
                # Create a selector based on the original but with data-src attribute
                base_selector = css_schema["image_url"].replace("[src]", "")
                if "[src]" not in css_schema["image_url"]:
                    # If no attribute specified, add the whole selector
                    css_schema["data_image_url"] = f"{base_selector}[data-src]"
                else:
                    # If src attribute was specifically targeted, create a parallel data-src selector
                    css_schema["data_image_url"] = base_selector + "[data-src]"
            # If image_url is a complex selector with attribute specification
            elif isinstance(css_schema["image_url"], dict) and "selector" in css_schema["image_url"]:
                # Copy the selector but change the attribute to data-src
                css_schema["data_image_url"] = {
                    "selector": css_schema["image_url"]["selector"],
                    "attribute": "data-src"
                }
            
            logger.info(f"Added data-src selector to schema: {json.dumps(css_schema, indent=2)}")
        
        # Use the schema directly without any conversion - this is how crawl4ai_demo.py works
        extraction_strategy = JsonCssExtractionStrategy(schema=css_schema)
        
        # Configure the crawler with settings that match crawl4ai_demo.py
        config = CrawlerRunConfig(
            extraction_strategy=extraction_strategy, 
            verbose=True,
            cache_mode=CacheMode.BYPASS  # Ensure we're not using cached content
        )
        
        # Add URL transformation to the config
        config.field_transformers = {
            "url": lambda url, context: transform_url(url, url),
            "image_url": lambda url, context: transform_url(url, url)
        }
        
        # Create a hook to log extraction details
        async def extraction_hook(result, **kwargs):
            logger.info(f"Extraction Hook - Processing URL: {result.url}")
            if result.extracted_content:
                logger.info(f"Successfully extracted {len(result.extracted_content)} items")
                # Print first item as sample
                if len(result.extracted_content) > 0:
                    logger.info(f"Sample extracted item: {json.dumps(result.extracted_content[0], indent=4, sort_keys=True)}")
            else:
                logger.warning("No content extracted")
                
                # Debug the selectors against the HTML
                logger.info("Debugging selectors against HTML:")
                html_content = result.raw_result.html if hasattr(result, 'raw_result') and hasattr(result.raw_result, 'html') else ""
                if html_content:
                    try:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        
                        # If the schema has a baseSelector, debug that first
                        if 'baseSelector' in css_schema:
                            base_selector = css_schema['baseSelector']
                            base_elements = soup.select(base_selector)
                            logger.info(f"BaseSelector: {base_selector}, Found: {len(base_elements)} elements")
                        
                        # Debug each field in the schema
                        if 'fields' in css_schema and isinstance(css_schema['fields'], list):
                            for field in css_schema['fields']:
                                field_name = field.get('name', 'unknown')
                                selector = field.get('selector', '')
                                try:
                                    elements = soup.select(selector)
                                    logger.info(f"Field: {field_name}, Selector: {selector}, Found: {len(elements)} elements")
                                    if len(elements) > 0 and len(elements) < 3:
                                        logger.info(f"Sample content: {elements[0].text.strip()[:50]}...")
                                except Exception as e:
                                    logger.error(f"Error testing selector '{selector}' for field '{field_name}': {str(e)}")
                    except Exception as e:
                        logger.error(f"Error during HTML debugging: {str(e)}")
        
        # Add the hook to the config
        config.hooks = {"post_extraction": extraction_hook}
        
        # Run the crawler
        async with crawler:
            result = await crawler.arun(url=url, config=config)
            
            if not result.success:
                if hasattr(result, 'error') and result.error:
                    logger.error(f"Failed to extract content: {result.error}")
                else:
                    logger.error("Failed to extract content: Unknown error")
                return []
            
            # Process the extracted content
            extracted_content = result.extracted_content
            
            # If the content is a JSON string, parse it
            if isinstance(extracted_content, str):
                try:
                    extracted_content = json.loads(extracted_content)
                except json.JSONDecodeError:
                    logger.error("Failed to decode JSON response")
                    return []
            
            # Ensure extracted_content is a list
            events = extracted_content if isinstance(extracted_content, list) else [extracted_content]
            
            logger.info(f"Raw extracted events: {len(events)}")
            
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
        import traceback
        logger.error(traceback.format_exc())
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