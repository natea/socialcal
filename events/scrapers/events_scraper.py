from datetime import datetime
from django.utils import timezone
from typing import List, Dict, Any, Tuple
from .base_scraper import BaseScraper
import json

class EventsScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.skipped_events = []

    def parse_event(self, data):
        """Parse scraped data into event format"""
        # Get event title and date
        title = data.get('event', '')
        date_str = data.get('Event Dates', '')  # Changed from 'date' to 'Event Dates'
        
        # Get location details
        location_parts = []
        if data.get('Venue Title'):
            location_parts.append(data['Venue Title'])
        if data.get('street'):
            location_parts.append(data['street'])
        if data.get('city') and data.get('state'):
            location_parts.append(f"{data['city']}, {data['state']} {data.get('zip', '')}")
        location = ', '.join(filter(None, location_parts))

        # Parse the datetime
        start_time = self._parse_datetime(date_str)
        if not start_time:
            self.skipped_events.append({
                'title': title,
                'reason': f"Invalid or missing date format: '{date_str}'"
            })
            return None

        # Build event data
        return {
            'title': title,
            'description': data.get('description', ''),
            'location': location,
            'start_time': start_time,
            'end_time': start_time,  # Since end time isn't provided, use same as start
            'is_public': True,
            'url': data.get('event_link', '')
        }
    
    def _parse_datetime(self, date_str):
        """Parse datetime from string like 'Sunday / January 26, 2025 / 6:00 p.m. (EST)'"""
        if not date_str:
            return None
            
        try:
            # Remove timezone indicator and clean up string
            date_str = date_str.split('(')[0].strip()
            
            # Split the string and get relevant parts
            parts = [p.strip() for p in date_str.split('/')]
            if len(parts) != 3:
                return None
                
            # Get date and time parts
            date_part = parts[1].strip()
            time_part = parts[2].strip().lower()  # Convert to lowercase for consistency
            
            # Handle 'p.m.' and 'a.m.' format
            time_part = time_part.replace('p.m.', 'PM').replace('a.m.', 'AM')
            
            # Combine date and time
            datetime_str = f"{date_part} {time_part}"
            
            # Parse the datetime with the correct format
            try:
                # First try with minutes
                return datetime.strptime(datetime_str, '%B %d, %Y %I:%M %p')
            except ValueError:
                # If that fails, try without minutes
                return datetime.strptime(datetime_str, '%B %d, %Y %I %p')
            
        except (ValueError, IndexError) as e:
            print(f"Failed to parse date: '{date_str}' - Error: {str(e)}")  # Debug output
            return None

    def process_events(self, recipe_id: str, source_url: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Process scraped data into events and return both valid and skipped events"""
        self.skipped_events = []  # Reset skipped events
        raw_data = self.fetch_data(recipe_id, source_url)
        
        # Debug the complete raw data
        print("\n=== START OF API RESPONSE ===")
        print(f"Number of events found: {len(raw_data)}")
        print("\nComplete API Response:")
        print(json.dumps(raw_data, indent=2))
        print("=== END OF API RESPONSE ===\n")
        
        # Also print the keys available in the first event
        if raw_data and len(raw_data) > 0:
            print("\nAvailable fields in first event:")
            for key, value in raw_data[0].items():
                print(f"{key}: {value}")
        
        # Filter out None values from parse_event
        valid_events = [event for event in (self.parse_event(item) for item in raw_data) if event is not None]
        
        if not valid_events:
            if self.skipped_events:
                skipped_details = "\n".join([
                    f"- {event['title']}: {event['reason']}"
                    for event in self.skipped_events
                ])
                raise Exception(
                    f"No valid events found to import. The following events were skipped:\n{skipped_details}"
                )
            raise Exception("No events found to import")
            
        return valid_events, self.skipped_events 