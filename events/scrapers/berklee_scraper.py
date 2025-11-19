from firecrawl import FirecrawlApp
import json
from groq import Groq
from datetime import datetime
import os
from django.conf import settings
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
import pytz
from django.utils import timezone
import re

def is_image_caption(text):
    """
    Check if a text looks like an image caption or alt text.
    Returns True if it appears to be image metadata rather than a real description.
    """
    if not text or not isinstance(text, str):
        return False

    text_lower = text.lower().strip()

    # Check for common image caption patterns
    image_indicators = [
        r'^image\s+of\s+',
        r'^photo\s+of\s+',
        r'^picture\s+of\s+',
        r'\.jpg$',
        r'\.png$',
        r'\.gif$',
        r'\.jpeg$',
        r'^img[-_\d]',
        r'^\[image\]',
        r'^\[photo\]',
        r'alt\s*=',
        r'caption:',
    ]

    for pattern in image_indicators:
        if re.search(pattern, text_lower):
            return True

    # Check if text is suspiciously short (< 10 chars) - likely not a real description
    if len(text_lower) < 10:
        return True

    return False

def scrape_berklee_events():
    """Scrape events from Berklee's performance page."""
    # Initialize the clients with API keys from environment variables
    firecrawl = FirecrawlApp(api_key=settings.FIRECRAWL_API_KEY)
    groq = Groq(api_key=settings.GROQ_API_KEY)

    # Get the page content
    page_data = firecrawl.scrape_url('https://www.berklee.edu/events/performances', {
        'formats': ['markdown']
    })
    page_content = page_data['markdown']

    # Define the fields we want to extract
    fields_to_extract = [
        "event_title",
        "event_date",
        "event_time",
        "event_venue",
        "event_address",
        "event_city",
        "event_state",
        "event_zip",
        "event_country",
        "event_description",
        "event_url",
        "event_cost",
        "event_image_url"
    ]

    # Extract events using Groq LLama3
    completion = groq.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {
                "role": "system",
                "content": "You are an expert at extracting event information from web pages. Extract exactly 5 events and format them as a JSON array. Format dates as YYYY-MM-DD and times as HH:MM in 24-hour format. If a time is shown as 8:00 PM, convert it to 20:00. IMPORTANT: For event_description, extract the actual event description text, NOT image captions, image alt text, or image filenames. If no real description is available, use an empty string."
            },
            {
                "role": "user",
                "content": f"Extract the first 10 events from this Berklee performances page. For each event, extract these fields: {fields_to_extract}. Remember: Do NOT use image captions or alt text as the event description. Only use actual descriptive text about the event.\n\nPage content:\n\n{page_content}"
            }
        ],
        temperature=0,
        max_tokens=2048,
        top_p=1,
        stream=False,
        stop=None,
        response_format={"type": "json_object"}
    )

    # Get and format the extracted data
    events_data = json.loads(completion.choices[0].message.content)
    
    # Format events for the Event model
    formatted_events = []
    eastern = pytz.timezone('America/New_York')
    
    for event in events_data['events']:
        # Parse date and time
        try:
            # Combine date and time strings
            datetime_str = f"{event['event_date']} {event['event_time']}"
            
            # First create a naive datetime
            naive_dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            
            # Localize it to Eastern Time
            start_time = eastern.localize(naive_dt)
            
            # Convert to UTC for storage
            start_time_utc = start_time.astimezone(pytz.UTC)

            # Set end time to 2 hours after start time
            end_time_utc = start_time_utc + timedelta(hours=2)

            # Validate and clean description
            description = event.get('event_description', '')
            if is_image_caption(description):
                print(f"Warning: Filtered out image caption as description: '{description}'")
                description = ''

            formatted_event = {
                'title': event['event_title'],
                'description': description,
                'venue_name': event['event_venue'],
                'venue_address': event['event_address'],
                'venue_city': event['event_city'],
                'venue_state': event['event_state'],
                'venue_postal_code': event['event_zip'],
                'venue_country': event.get('event_country', 'United States'),
                'start_time': start_time_utc,
                'end_time': end_time_utc,
                'url': event['event_url'],
                'image_url': event.get('event_image_url', ''),
                'is_public': True
            }
            formatted_events.append(formatted_event)
            
            # Debug output
            print(f"Event: {event['event_title']}")
            print(f"Original time: {datetime_str}")
            print(f"Start time (ET): {start_time}")
            print(f"Start time (UTC): {start_time_utc}")
            print(f"End time (UTC): {end_time_utc}")
            print("-" * 50)
            
        except (ValueError, KeyError) as e:
            print(f"Error processing event {event['event_title']}: {str(e)}")
            continue
    
    return formatted_events 