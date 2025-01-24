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
            
            return list(set(ical_urls))  # Remove duplicates
            
        except Exception as e:
            raise Exception(f"Failed to discover iCal URLs: {str(e)}")
    
    def validate_ical_url(self, url: str) -> bool:
        """Validate if a URL returns valid iCal data"""
        try:
            response = requests.get(url, allow_redirects=True)
            response.raise_for_status()
            
            # Try to parse as iCal
            cal = Calendar.from_ical(response.text)
            
            # Check if calendar has any events
            events = [c for c in cal.walk() if c.name == "VEVENT"]
            if not events:
                logger.warning(f"No events found in calendar at {url}")
                return False
                
            logger.info(f"Found {len(events)} events in calendar at {url}")
            return True
            
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
        if not url.endswith('.ics') and not 'ical=1' in url:
            discovered_urls = self.discover_ical_urls(url)
            logger.info(f"Discovered {len(discovered_urls)} potential calendar URLs: {discovered_urls}")
            
            # Filter out non-calendar URLs
            calendar_urls = []
            for discovered_url in discovered_urls:
                normalized_url = self.normalize_url(discovered_url)
                if normalized_url in tried_urls:
                    continue
                    
                # Skip URLs that are clearly not calendar feeds
                if any(pattern in normalized_url.lower() for pattern in [
                    '.css', '/feed/', 'comments'
                ]):
                    continue
                    
                # Prioritize URLs that look like calendar feeds
                if any(pattern in normalized_url.lower() for pattern in [
                    '.ics', 'ical=1', 'outlook-ical=1', 'tribe_events'
                ]):
                    calendar_urls.append(normalized_url)
                    tried_urls.add(normalized_url)
            
            # Try each discovered URL
            valid_urls_found = False
            for calendar_url in calendar_urls:
                try:
                    if self.validate_ical_url(calendar_url):
                        valid_urls_found = True
                        # Fetch events from this URL
                        response = requests.get(calendar_url, allow_redirects=True)
                        response.raise_for_status()
                        cal = Calendar.from_ical(response.text)
                        events = [c for c in cal.walk() if c.name == "VEVENT"]
                        all_events.extend(events)
                        logger.info(f"Found {len(events)} events in calendar at {calendar_url}")
                except Exception as e:
                    logger.warning(f"Failed to fetch events from {calendar_url}: {str(e)}")
                    continue
            
            if not valid_urls_found:
                if calendar_urls:
                    raise Exception(f"Found {len(calendar_urls)} potential calendar URLs, but none contained valid iCal data")
                else:
                    raise Exception("No calendar URLs found on the page")
        else:
            # Direct iCal URL provided
            try:
                response = requests.get(url, allow_redirects=True)
                response.raise_for_status()
                cal = Calendar.from_ical(response.text)
                events = [c for c in cal.walk() if c.name == "VEVENT"]
                all_events.extend(events)
                logger.info(f"Found {len(events)} events in calendar at {url}")
            except Exception as e:
                raise Exception(f"Failed to fetch iCal data: {str(e)}")
        
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
            
            # Convert date to datetime if necessary
            if isinstance(dt, date) and not isinstance(dt, datetime):
                dt = datetime.combine(dt, datetime.min.time())
            
            # Make timezone aware if it isn't already
            if timezone.is_naive(dt):
                # If datetime is naive, assume it's in America/New_York
                eastern = pytz.timezone('America/New_York')
                dt = eastern.localize(dt)
            return dt
        
        start_time = component.get('dtstart').dt if component.get('dtstart') else None
        end_time = component.get('dtend').dt if component.get('dtend') else None
        
        # Make datetimes timezone-aware
        start_time = make_timezone_aware(start_time)
        end_time = make_timezone_aware(end_time)
        
        return {
            'title': str(component.get('summary', '')),
            'description': str(component.get('description', '')),
            'start_time': start_time,
            'end_time': end_time,
            'url': str(component.get('url', '')),
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