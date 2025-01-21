import os
from dotenv import load_dotenv
from firecrawl import FirecrawlApp
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, HttpUrl, Field
import google.generativeai as genai
import json
import re

# Load environment variables from .env file
load_dotenv()

class Event(BaseModel):
    title: str = Field(..., description="Title of the event")
    date: datetime = Field(..., description="Date of the event")
    time: str = Field(..., description="Time of the event")
    description: str = Field(..., description="Description of the event")
    url: HttpUrl = Field(..., description="URL of the event page")
    image_url: Optional[HttpUrl] = Field(None, description="URL of the event image")

class EventList(BaseModel):
    events: List[Event]

def log_debug(message, data=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
    if data:
        print(json.dumps(data, indent=2))
    print("-" * 80)

def extract_events_from_content(model, content):
    """Extract events from the content using Gemini."""
    response = model.generate_content(
        f"""Extract exactly 10 events from this content. Each event must have a complete URL.

Content:
{content[:10000]}

Return a valid JSON object with exactly 10 events in this format:
{{
    "events": [
        {{
            "title": "Event title",
            "date": "2024-03-21",
            "time": "7:00 PM",
            "url": "https://example.com/event",
            "image_url": "https://example.com/image.jpg"
        }}
    ]
}}

CRITICAL:
1. Return ONLY the JSON object, no markdown formatting or code blocks
2. All strings must be properly escaped
3. The JSON must be complete and valid
4. All URLs must be complete (including https://)
5. IMPORTANT: Do not truncate or shorten any URLs - they must be exact and complete
6. Some URLs are very long (over 200 characters) - make sure to include the entire URL
7. You MUST return exactly 10 events - no more, no less""",
        generation_config=genai.types.GenerationConfig(
            temperature=0,
            candidate_count=1,
            stop_sequences=[],
            max_output_tokens=8192
        )
    )
    
    try:
        # Clean up the response text
        text = response.text.strip()
        
        # Remove markdown code block if present
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
        if text.startswith('json'):
            text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text.rsplit('\n', 1)[0]
            
        # Parse the JSON
        data = json.loads(text)
        
        # Verify we got exactly 10 events
        if len(data.get('events', [])) != 10:
            log_debug(f"Warning: Got {len(data.get('events', []))} events instead of 10")
        
        # Verify URLs are not truncated
        for event in data.get('events', []):
            if event.get('url') and len(event['url']) < 50:
                log_debug(f"Warning: Potentially truncated URL detected: {event['url']}")
        
        return data
    except json.JSONDecodeError as e:
        log_debug(f"Error parsing JSON: {str(e)}")
        log_debug("Raw response:", response.text)
        return None

def extract_description_from_page(model, page_data):
    """Extract description from a page's data."""
    content = page_data.get('markdown', '')
    html = page_data.get('html', '')
    
    response = model.generate_content(
        f"""Extract the complete event description from this page. Include ALL details about the event, including performers, times, prices, and any additional information.

Content:
Markdown:
{content}

HTML:
{html}

Return ONLY the complete description text, no JSON formatting or other fields. Make sure to include ALL relevant information about the event.""",
        generation_config=genai.types.GenerationConfig(
            temperature=0,
            candidate_count=1,
            max_output_tokens=8192
        )
    )
    
    return response.text.strip()

# Get API keys from environment variables
firecrawl_api_key = os.getenv('FIRECRAWL_API_KEY')
gemini_api_key = os.getenv('GOOGLE_API_KEY')

if not firecrawl_api_key:
    raise ValueError("FIRECRAWL_API_KEY not found in environment variables")
if not gemini_api_key:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

# Initialize clients
app = FirecrawlApp(api_key=firecrawl_api_key)
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

# First, crawl the site to get all event pages
log_debug("Crawling website for event pages...")
crawl_result = app.crawl_url('https://www.lilypadinman.com', {
    'formats': ['markdown', 'html'],
    'include_patterns': ['/*', '/home/*', '/events/*'],  # Include root and event pages
    'max_pages': 50,  # Limit to 50 pages to ensure we get all events but don't crawl too much
    'crawl_options': {
        'max_depth': 2  # Only crawl 2 levels deep
    }
})

# Extract events from the main page first
main_page = crawl_result.get('pages', {}).get('https://www.lilypadinman.com', {})
if not main_page:
    log_debug("Main page not found in crawl results, trying /home")
    main_page = crawl_result.get('pages', {}).get('https://www.lilypadinman.com/home', {})

if not main_page:
    raise ValueError("Could not find main page in crawl results")

# Extract events from main page content
events_data = extract_events_from_content(model, main_page.get('markdown', ''))
if not events_data or 'events' not in events_data:
    raise ValueError("Failed to extract events from main page")

# Get descriptions from crawled pages
log_debug("Extracting descriptions from crawled pages...")
for event in events_data['events']:
    try:
        # Get the page data for this event's URL
        page_data = crawl_result.get('pages', {}).get(event['url'])
        if page_data:
            event['description'] = extract_description_from_page(model, page_data)
        else:
            log_debug(f"Page data not found for URL: {event['url']}")
            event['description'] = "Description could not be fetched - page not found in crawl results"
    except Exception as e:
        log_debug(f"Error extracting description for {event['url']}: {str(e)}")
        event['description'] = "Description could not be fetched"

# Print the extracted events with descriptions
log_debug("Processing events...")
for i, event in enumerate(events_data['events'], 1):
    log_debug(f"Event {i}", event)

log_debug(f"Total events extracted: {len(events_data['events'])}")
log_debug("Scraping completed!")
