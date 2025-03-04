import asyncio
import os
import json
import re
from typing import Optional, Dict
from dotenv import load_dotenv

#     CacheMode,
#     DisplayMode,
#     MemoryAdaptiveDispatcher,
#     CrawlerMonitor,
#     DefaultMarkdownGenerator,
#     LXMLWebScrapingStrategy,
#     BrowserConfig,
#     LLMContentFilter

load_dotenv()

from crawl4ai import (
    AsyncWebCrawler, 
    CrawlerRunConfig,
    JsonCssExtractionStrategy,
    CacheMode
)

# Function to transform relative URLs to absolute URLs
def transform_url(url, base_url):
    if not url:
        return None
    
    # Skip base64 encoded images
    if url.startswith('data:image'):
        return None
    
    # Handle background-image CSS property
    if 'background-image:' in url:
        # Extract URL from background-image: url('...')
        match = re.search(r"url\(['\"]?(https?://[^'\")]+)['\"]?\)", url)
        if match:
            url = match.group(1)
        else:
            return None
    
    # If the URL is already absolute, return it as is
    if url.startswith('http://') or url.startswith('https://'):
        return url
    
    # Parse the base URL to get the domain
    from urllib.parse import urlparse, urljoin
    
    # Use urljoin to properly handle relative URLs
    return urljoin(base_url, url)

async def demo_json_schema_generation():
    """
    Demonstrates how to use Crawl4AI to generate a JSON schema for extracting event information.
    """
    # Define the URL to crawl
    #target_url = "https://tockify.com/beehive/agenda"
    #target_url = "https://www.ticketweb.com/venue/regattabar-cambridge-ma/748814?pl=regatta"
    #target_url = "https://lilypadinman.com/events"
    target_url = "https://www.themadmonkfish.com/jazz-schedule/"
    
    # Define a post-extraction hook to clean up the data
    def extraction_hook(extracted_content, context):
        """
        Post-extraction hook to clean up the data.
        """
        if not extracted_content:
            return extracted_content
        
        # If we have HTML content, try to find better image URLs and fix URLs
        html_content = context.get("html_content", "")
        if html_content and isinstance(extracted_content, list):
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Look for high-quality images
                all_images = soup.select('img[src^="https://"], img[src^="http://"]')
                good_image_urls = [img['src'] for img in all_images 
                                  if img.get('src') and not img['src'].startswith('data:')]
                
                # Also look for background images in style attributes
                elements_with_style = soup.select('[style*="background-image"]')
                for element in elements_with_style:
                    style = element.get('style', '')
                    match = re.search(r"url\(['\"]?(https?://[^'\")]+)['\"]?\)", style)
                    if match:
                        good_image_urls.append(match.group(1))
                
                # Process each event
                for event in extracted_content:
                    # Fix URLs - ensure they're absolute
                    if 'url' in event and event['url'] and not (event['url'].startswith('http://') or event['url'].startswith('https://')):
                        event['url'] = transform_url(event['url'], target_url)
                    
                    # Fix image URLs
                    if ('image_url' not in event or 
                        not event['image_url'] or 
                        event['image_url'].startswith('data:')):
                        
                        # Try to find an image that might be related to this event
                        event_title = event.get('title', '').lower()
                        if event_title:
                            # Look for images near text containing the event title
                            for img in all_images:
                                parent = img.parent
                                if parent and event_title in parent.get_text().lower():
                                    event['image_url'] = img['src']
                                    break
                        
                        # If still no image, just use the first good one
                        if ('image_url' not in event or 
                            not event['image_url'] or 
                            event['image_url'].startswith('data:')):
                            if good_image_urls:
                                event['image_url'] = good_image_urls[0]
                
                # Look for event detail links
                event_links = soup.select('a[href*="detail"], a[href*="event"]')
                event_urls = [a['href'] for a in event_links if a.get('href')]
                
                # If we found event detail links, try to match them with events
                if event_urls:
                    for event in extracted_content:
                        # If the event has no URL or has a relative URL
                        if 'url' not in event or not event['url'] or not (event['url'].startswith('http://') or event['url'].startswith('https://')):
                            event_title = event.get('title', '').lower()
                            if event_title:
                                # Try to find a link that might be related to this event
                                for link in event_links:
                                    if event_title in link.get_text().lower():
                                        event['url'] = transform_url(link['href'], target_url)
                                        break
                            
                            # If still no URL, just use the first one
                            if 'url' not in event or not event['url'] or not (event['url'].startswith('http://') or event['url'].startswith('https://')):
                                if event_urls:
                                    event['url'] = transform_url(event_urls[0], target_url)
            except Exception as e:
                print(f"Error in post-processing: {str(e)}")
        
        return extracted_content
    
    print(f"Fetching content from {target_url}...")
    
    # Initialize the crawler
    crawler = AsyncWebCrawler()
    
    # Fetch the HTML content from the target URL
    async with crawler:
        # Simple run to get the HTML content
        fetch_result = await crawler.arun(target_url)
        
        if not fetch_result.success:
            print(f"Failed to fetch content from {target_url}")
            return
            
        html_content = fetch_result.html
        
        if not html_content:
            print("No HTML content found in the response")
            return
            
        print(f"Successfully fetched HTML content ({len(html_content)} bytes)")
        
        # Save a sample of the HTML to a file for debugging
        with open("sample.html", "w") as f:
            f.write(html_content)
        print(f"Saved HTML sample to sample.html")
        
        try:
            # Generate CSS selectors schema for event extraction using Gemini
            print("\nGenerating CSS selectors schema for event extraction using Gemini...")
            
            # Define a specific query to guide the LLM
            query = """
            You are an expert web scraper. I need to extract event information from a given URL.
            
            The page structure has events listed as cards. Each event card likely contains:
            - Event title (probably in a heading element)
            - Date and time information
            - Location information
            - Possibly an image
            - Possibly a link to the event details
            
            Create a CSS selector schema to extract the following fields for EACH event on the page:
            1. Event title
            2. Date
            3. Location
            4. Description (if available)
            5. URL (the link to the event details)
            6. Image URL (if available)
            
            IMPORTANT NOTES:
            - Your selectors should target EACH individual event item, not just the first one.
            - If events are in a list or grid, make sure your selectors will work for ALL events.
            - For URLs, select the HREF attribute of the link, not just the element itself.
            - For image URLs, select the SRC attribute of the image, not just the element itself.
            - AVOID selecting base64-encoded images. Look for real image URLs that start with http:// or https://
            - If there are multiple image sources available, prefer the one with the highest resolution or quality.
            - IMPORTANT: Some websites use CSS background-image in style attributes instead of img tags. Look for elements with style attributes containing "background-image: url(...)" and extract those URLs.
            
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
              "image_url": {"selector": ".event-card img", "attribute": "src"}
            }
            
            For background images in style attributes, use:
            {
              "image_url": {"selector": ".event-card .image", "attribute": "style"}
            }
            """
            
            css_schema = JsonCssExtractionStrategy.generate_schema(
                html_content,
                schema_type="CSS",
                query=query,
                provider="gemini/gemini-2.0-flash-lite",
                api_token=os.getenv("GEMINI_API_KEY")
            )
            print("\nGenerated CSS Schema:")
            # Print the schema in a more readable format using json.dumps with indentation
            print(json.dumps(css_schema, indent=4))
            
            # Create an extraction strategy with the generated schema
            extraction_strategy = JsonCssExtractionStrategy(schema=css_schema)
            
            # Enable verbose mode for detailed logging
            config = CrawlerRunConfig(
                extraction_strategy=extraction_strategy, 
                verbose=True,
                cache_mode=CacheMode.BYPASS  # Ensure we're not using cached content
            )
            
            print("\nCrawling URL with generated schema...")
            async with crawler:
                # First, fetch the HTML content
                fetch_config = CrawlerRunConfig(verbose=True)
                fetch_result = await crawler.arun(url=target_url, config=fetch_config)
                
                if not fetch_result.success:
                    print(f"Failed to fetch content: {fetch_result.error}")
                    return
                
                # Save the HTML content to a file for debugging
                html_content = fetch_result.html
                with open("website_html_content.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                print(f"Saved HTML sample to website_html_content.html")
                
                # Create a hook to log extraction details
                async def extraction_hook(result, **kwargs):
                    print(f"\n🔍 Extraction Hook - Processing URL: {result.url}")
                    if result.extracted_content:
                        print(f"✅ Successfully extracted {len(result.extracted_content)} items")
                        # Print first item as sample
                        if len(result.extracted_content) > 0:
                            print("\nSample extracted item:")
                            print(json.dumps(result.extracted_content[0], indent=4, sort_keys=True))
                    else:
                        print("❌ No content extracted")
                        
                        # Debug the selectors against the HTML
                        print("\nDebugging selectors against HTML:")
                        # Handle different schema structures
                        if "fields" in css_schema:
                            # Handle array of field objects
                            for field_obj in css_schema["fields"]:
                                field_name = field_obj.get("name", "unknown")
                                selector = field_obj.get("selector", "")
                                try:
                                    from bs4 import BeautifulSoup
                                    soup = BeautifulSoup(html_content, 'html.parser')
                                    elements = soup.select(selector)
                                    print(f"Field: {field_name}, Selector: {selector}, Found: {len(elements)} elements")
                                    if len(elements) > 0 and len(elements) < 3:
                                        print(f"Sample content: {elements[0].text.strip()[:50]}...")
                                except Exception as e:
                                    print(f"Error testing selector '{selector}' for field '{field_name}': {str(e)}")
                        else:
                            # Handle direct key-value pairs
                            for field, selector in css_schema.items():
                                try:
                                    from bs4 import BeautifulSoup
                                    soup = BeautifulSoup(html_content, 'html.parser')
                                    elements = soup.select(selector)
                                    print(f"Field: {field}, Selector: {selector}, Found: {len(elements)} elements")
                                    if len(elements) > 0 and len(elements) < 3:
                                        print(f"Sample content: {elements[0].text.strip()[:50]}...")
                                except Exception as e:
                                    print(f"Error testing selector '{selector}' for field '{field}': {str(e)}")
                
                # Add the hook to the config
                config.hooks = {"post_extraction": extraction_hook}
                
                # Add URL transformation to the config
                config.field_transformers = {
                    "url": lambda url, context: transform_url(url, target_url),
                    "image_url": lambda url, context: transform_url(url, target_url)
                }
                
                # Run the crawler
                result = await crawler.arun(url=target_url, config=config)
                
                if result.success:
                    print("\n🔄 Crawler completed successfully")
                    if result.extracted_content:
                        print(f"📊 Extracted {len(result.extracted_content)} items")
                        print("\nExtracted content:")
                        
                        # Create a more human-readable formatted output
                        if result.extracted_content:
                            try:
                                # Check if the content is already a string (JSON)
                                content_to_format = result.extracted_content
                                if isinstance(content_to_format, str):
                                    # Parse the JSON string into Python objects
                                    try:
                                        content_to_format = json.loads(content_to_format)
                                    except json.JSONDecodeError:
                                        print("Warning: Could not parse the JSON string. Using raw output.")
                                
                                # Format each event in a more readable way
                                print("\n" + "="*80)  # Separator line
                                
                                # Handle both list of events and single event cases
                                events_list = content_to_format if isinstance(content_to_format, list) else [content_to_format]
                                
                                for i, event in enumerate(events_list, 1):
                                    print(f"\n📅 EVENT #{i}")
                                    print(f"  🎭 Title: {event.get('title', 'N/A')}")
                                    print(f"  🕒 Date: {event.get('date', 'N/A')}")
                                    
                                    # Handle URL - ensure it's absolute
                                    url = event.get('url', 'N/A')
                                    if url != 'N/A' and not (url.startswith('http://') or url.startswith('https://')):
                                        url = transform_url(url, target_url)
                                    print(f"  🔗 URL: {url}")
                                    
                                    # Handle image URL - ensure it's absolute
                                    image_url = event.get('image_url', 'N/A')
                                    if image_url != 'N/A':
                                        if image_url.startswith('data:image'):
                                            image_url = "Base64 image (not displayed)"
                                        elif 'background-image:' in image_url:
                                            # Extract URL from background-image: url('...')
                                            match = re.search(r"url\(['\"]?(https?://[^'\")]+)['\"]?\)", image_url)
                                            if match:
                                                image_url = match.group(1)
                                            else:
                                                image_url = "Invalid background-image format"
                                        elif not (image_url.startswith('http://') or image_url.startswith('https://')):
                                            image_url = transform_url(image_url, target_url)
                                            if not image_url:
                                                image_url = "Invalid image URL"
                                    print(f"  🖼️ Image: {image_url}")
                                    
                                    # Format description with proper line breaks if it exists
                                    if 'description' in event and event['description']:
                                        desc = event['description']
                                        # Limit description length and add ellipsis if too long
                                        if len(desc) > 100:
                                            desc = desc[:97] + "..."
                                        print(f"  📝 Description: {desc}")
                                    
                                    # Add any additional fields that might be present
                                    for key, value in event.items():
                                        if key not in ['title', 'date', 'description', 'url', 'image_url']:
                                            # Format value based on type
                                            if isinstance(value, str) and len(value) > 80:
                                                value = value[:77] + "..."
                                            print(f"  ➕ {key.capitalize()}: {value}")
                                    
                                    # Add separator between events
                                    if i < len(events_list):
                                        print("\n" + "-"*60)
                                
                                print("\n" + "="*80)  # End separator line
                                
                                # Also provide the option to see the raw JSON with highlighting
                                print("\n📋 Raw JSON data is also available. To view it, uncomment the next line in the code.")
                                
                                # Format the JSON for optional viewing
                                if isinstance(result.extracted_content, str):
                                    # If it's already a string, use it directly
                                    formatted_content = result.extracted_content
                                else:
                                    # Otherwise, convert to JSON
                                    formatted_content = json.dumps(
                                        result.extracted_content,
                                        indent=4,
                                        sort_keys=False,
                                        ensure_ascii=False
                                    )
                                
                                # Add color highlighting if in terminal environment
                                try:
                                    from pygments import highlight
                                    from pygments.lexers import JsonLexer
                                    from pygments.formatters import TerminalFormatter
                                    formatted_content = highlight(formatted_content, JsonLexer(), TerminalFormatter())
                                except ImportError:
                                    # If pygments is not available, just use the formatted JSON
                                    pass
                                
                                # Uncomment to print the raw JSON
                                # print(formatted_content)
                                
                            except Exception as e:
                                # Fallback to standard JSON formatting if custom formatting fails
                                print(f"Error formatting output: {str(e)}")
                                formatted_content = json.dumps(
                                    result.extracted_content,
                                    indent=4,
                                    sort_keys=False,
                                    ensure_ascii=False
                                )
                                print(formatted_content)
                        else:
                            print("⚠️ No content was extracted. The schema might need refinement.")
                            print("Examine the HTML structure in 'luma_boston_sample.html' and adjust the query.")
                            
                            # Try a more direct approach with BeautifulSoup for debugging
                            print("\n🔬 Attempting direct extraction with BeautifulSoup for debugging:")
                            try:
                                from bs4 import BeautifulSoup
                                soup = BeautifulSoup(html_content, 'html.parser')
                                
                                # Look for common event elements
                                event_cards = soup.select('.card-wrapper, .event-card, .content-card, [class*="event"]')
                                print(f"Found {len(event_cards)} potential event cards")
                                
                                if event_cards:
                                    sample_card = event_cards[0]
                                    print(f"\nSample card structure:")
                                    print(f"Classes: {sample_card.get('class')}")
                                    print(f"HTML snippet: {str(sample_card)[:200]}...")
                                    
                                    # Try to find titles
                                    titles = soup.select('h3, .title, [class*="title"]')
                                    print(f"\nFound {len(titles)} potential titles")
                                    if titles and len(titles) < 10:
                                        for i, title in enumerate(titles):
                                            print(f"Title {i+1}: {title.text.strip()[:50]}...")
                            except Exception as e:
                                print(f"Error during direct extraction: {str(e)}")
                else:
                    print(f"❌ Crawler failed: {result.error}")
        except Exception as e:
            print(f"Error during extraction: {str(e)}")
            # Print the full traceback for debugging
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(demo_json_schema_generation())