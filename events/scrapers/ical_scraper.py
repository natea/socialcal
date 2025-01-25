import requests
from datetime import datetime, date
from icalendar import Calendar
from typing import Dict, Any, List, Tuple
from .base_scraper import BaseScraper
from django.conf import settings
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, urlunparse
from django.utils import timezone
import pytz
import logging

logger = logging.getLogger('events.scrapers.generic_scraper')

class ICalScraper(BaseScraper):
    """Scraper for iCal/webcal feeds"""
    
    def __init__(self):
        super().__init__()
        self.selected_url = None  # Track which URL was successfully used
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL to handle common variations"""
        # Parse the URL
        parsed = urlparse(url)
        
        # Convert webcal to https
        if parsed.scheme == 'webcal':
            parsed = parsed._replace(scheme='https')
        
        return urlunparse(parsed)
    
    def discover_ical_urls(self, url: str) -> List[str]:
        """Find iCal/webcal URLs from a webpage"""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            ical_urls = []
            
            # Look for common patterns in links and attributes
            patterns = [
                # Common URL patterns
                r'\.ics$',
                r'ical=1',
                r'format=ical',
                r'/feed/',
                r'webcal://',
                r'calendar\.',
                r'events.*\?ical'
            ]
            
            # Find all links and link-like elements
            for link in soup.find_all(['a', 'link']):
                href = link.get('href', '')
                if not href:
                    continue
                
                # Check for type attribute in link elements
                if link.name == 'link' and link.get('type', '').lower() in ['text/calendar', 'application/x-webcal']:
                    if not href:
                        continue
                    # Make URL absolute
                    if not href.startswith(('http://', 'https://', 'webcal://')):
                        href = urljoin(url, href)
                    ical_urls.append(self.normalize_url(href))
                    continue
                
                # Make URL absolute
                if not href.startswith(('http://', 'https://', 'webcal://')):
                    href = urljoin(url, href)
                
                # Normalize the URL
                href = self.normalize_url(href)
                
                # Check if URL matches any of our patterns
                if any(re.search(pattern, href, re.I) for pattern in patterns):
                    ical_urls.append(href)
                    continue
                
                # Check link text for calendar-related keywords
                text = link.get_text().lower()
                if any(keyword in text for keyword in ['ical', 'calendar feed', 'subscribe', 'export calendar']):
                    ical_urls.append(href)
            
            # Log discovered URLs
            logger.info(f"Discovered {len(ical_urls)} potential calendar URLs: {ical_urls}")
            
            return list(set(ical_urls))  # Remove duplicates
            
        except Exception as e:
            raise Exception(f"Failed to discover iCal URLs: {str(e)}")
    
    def validate_ical_url(self, url: str) -> bool:
        """Validate if a URL returns valid iCal data"""
        try:
            response = requests.get(url, allow_redirects=True)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'text/calendar' in content_type or 'text/x-vcalendar' in content_type:
                # It's definitely an iCal feed
                try:
                    Calendar.from_ical(response.content)
                    return True
                except Exception as e:
                    logger.warning(f"Invalid iCal data from {url}: {str(e)}")
                    return False
            
            # If it's HTML, it might contain calendar links
            if 'text/html' in content_type:
                return False
            
            # Try to parse as iCal anyway (some servers don't set correct content type)
            try:
                Calendar.from_ical(response.content)
                return True
            except Exception:
                return False
            
        except Exception as e:
            logger.warning(f"Failed to validate iCal URL {url}: {str(e)}")
            return False
            
    def fetch_data(self, url: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """Fetch and parse iCal data from URL"""
        # Normalize the input URL
        url = self.normalize_url(url)
        
        all_events = []
        tried_urls = set()  # Keep track of URLs we've tried to avoid duplicates
        
        # First check if this is a webpage that might contain calendar links
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'text/html' in content_type:
                # This is an HTML page, try to find calendar links
                discovered_urls = self.discover_ical_urls(url)
                logger.info(f"Discovered {len(discovered_urls)} potential calendar URLs: {discovered_urls}")
                
                if not discovered_urls:
                    raise Exception("No calendar URLs found on the page. The page might not have any iCal export links.")
                
                # Try each discovered URL
                for calendar_url in discovered_urls:
                    if calendar_url in tried_urls:
                        continue
                        
                    tried_urls.add(calendar_url)
                    try:
                        if self.validate_ical_url(calendar_url):
                            # Found a valid iCal feed
                            self.selected_url = calendar_url
                            response = requests.get(calendar_url, allow_redirects=True)
                            response.raise_for_status()
                            cal = Calendar.from_ical(response.content)
                            events = [c for c in cal.walk() if c.name == "VEVENT"]
                            all_events.extend(events)
                            logger.info(f"Found {len(events)} events in calendar at {calendar_url}")
                    except Exception as e:
                        logger.warning(f"Failed to fetch events from {calendar_url}: {str(e)}")
                        continue
                
                if not all_events:
                    raise Exception("Found potential calendar URLs, but none contained valid iCal data")
                    
            else:
                # Try to parse as direct iCal feed
                try:
                    cal = Calendar.from_ical(response.content)
                    events = [c for c in cal.walk() if c.name == "VEVENT"]
                    if not events:
                        raise Exception("No events found in the calendar feed")
                    all_events.extend(events)
                    self.selected_url = url
                    logger.info(f"Found {len(events)} events in calendar at {url}")
                except Exception as e:
                    raise Exception(f"Invalid iCal data: {str(e)}")
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch URL: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to process calendar data: {str(e)}")
        
        # Remove duplicate events based on UID if present
        unique_events = {}
        for event in all_events:
            uid = str(event.get('uid', ''))
            if uid:
                if uid not in unique_events:
                    unique_events[uid] = event
            else:
                # If no UID, use summary and start time as key
                key = (str(event.get('summary', '')), str(event.get('dtstart', '')))
                if key not in unique_events:
                    unique_events[key] = event
        
        logger.info(f"Found {len(unique_events)} unique events in total")
        return list(unique_events.values())

    def parse_event(self, component: Dict[str, Any]) -> Dict[str, Any]:
        """Parse iCal event component into our event format"""
        # Extract location details (if available)
        location = str(component.get('location', ''))
        venue_parts = location.split(',')
        
        venue_name = venue_parts[0].strip() if venue_parts else ''
        venue_address = venue_parts[1].strip() if len(venue_parts) > 1 else ''
        venue_city = venue_parts[2].strip() if len(venue_parts) > 2 else ''
        venue_state = venue_parts[3].strip() if len(venue_parts) > 3 else ''
        
        # Get image URL if available
        image_url = ''
        if component.get('ATTACH'):
            attach = component['ATTACH']
            if isinstance(attach, list):
                for item in attach:
                    if str(item).startswith(('http://', 'https://')):
                        image_url = str(item)
                        break
            else:
                if str(attach).startswith(('http://', 'https://')):
                    image_url = str(attach)
        
        # Handle timezone-aware datetimes
        def make_timezone_aware(dt):
            if dt is None:
                return None
            
            # Get the value if it's a vDate or vDatetime
            if hasattr(dt, 'dt'):
                dt = dt.dt
            
            # Convert date to datetime if necessary
            if isinstance(dt, date) and not isinstance(dt, datetime):
                dt = datetime.combine(dt, datetime.min.time())
            
            # Make timezone aware if it isn't already
            if timezone.is_naive(dt):
                # If datetime is naive, assume it's in America/New_York
                eastern = pytz.timezone('America/New_York')
                dt = eastern.localize(dt)
            return dt
        
        # Get start and end times
        start = component.get('dtstart')
        end = component.get('dtend')
        
        # Make datetimes timezone-aware
        start_time = make_timezone_aware(start)
        end_time = make_timezone_aware(end)
        
        # Get URL from either URL or ATTACH property
        event_url = ''
        if component.get('url'):
            event_url = str(component.get('url'))
        elif component.get('ATTACH'):
            attach = component['ATTACH']
            if isinstance(attach, list):
                for item in attach:
                    if str(item).startswith(('http://', 'https://')) and not image_url:
                        event_url = str(item)
                        break
            elif not image_url:
                event_url = str(attach)
        
        # Get summary and description
        summary = component.get('summary')
        description = component.get('description')
        
        # Convert to string if they're not already
        if summary:
            summary = str(summary)
        if description:
            description = str(description)
        
        return {
            'title': summary or '',
            'description': description or '',
            'start_time': start_time,
            'end_time': end_time,
            'url': event_url,
            'venue_name': venue_name,
            'venue_address': venue_address,
            'venue_city': venue_city,
            'venue_state': venue_state,
            'venue_country': 'United States',  # Default
            'image_url': image_url,
            'is_public': True
        }

    def process_events(self, url: str, *args, **kwargs) -> List[Dict[str, Any]]:
        """Process iCal feed into events"""
        raw_data = self.fetch_data(url)
        events = [self.parse_event(item) for item in raw_data]
        
        # Print which URL was used for fetching
        print(f"\nUsing calendar URL: {self.selected_url}\n")
        
        return events 