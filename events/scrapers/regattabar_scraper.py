from seleniumbase import SB
from datetime import datetime
from zoneinfo import ZoneInfo
import re
from django.utils import timezone

def scrape_events():
    events_data = []
    with SB(uc=True, test=True, locale_code="en") as sb:
        url = "https://www.ticketweb.com/venue/regattabar-cambridge-ma/748814?pl=regatta"
        sb.activate_cdp_mode(url)
        sb.sleep(2.5)
        venue_name = sb.cdp.get_text("h1.venue-name")
        venue_address = sb.cdp.get_text(".venue-address")
        
        events = sb.cdp.select_all("li.media.theme-mod")
        for event in events:
            title_elem = event.query_selector("a.ng-scope")
            when_elem = event.query_selector("p.event-date.theme-subTitle")
            
            if title_elem and when_elem:
                title = title_elem.text.strip()
                when_text = when_elem.text.strip()
                
                # Get the full URL from the link
                event_url = sb.cdp.get_attribute("href", "a.ng-scope", by="css selector", element=event)
                
                # Extract the main time part before "(Doors...)"
                main_time = when_text.split(" (Doors")[0].strip()
                
                # Add the current year if not present
                if ", " not in main_time:
                    current_year = datetime.now().year
                    main_time = f"{main_time} {current_year}"
                
                try:
                    # Parse the date and time
                    naive_dt = datetime.strptime(main_time, "%a %b %d %I:%M %p %Y")
                    # Create timezone-aware datetime in Eastern Time
                    eastern = ZoneInfo("America/New_York")
                    dt = timezone.make_aware(naive_dt, eastern)
                    
                    # Get doors time if available
                    doors_time = None
                    doors_match = re.search(r"\(Doors (\d+):(\d+) ([AP]M)\)", when_text)
                    if doors_match:
                        doors_hour = int(doors_match.group(1))
                        doors_min = int(doors_match.group(2))
                        doors_ampm = doors_match.group(3)
                        if doors_ampm == "PM" and doors_hour != 12:
                            doors_hour += 12
                        naive_doors = naive_dt.replace(hour=doors_hour, minute=doors_min)
                        doors_time = timezone.make_aware(naive_doors, eastern)
                    
                    event_data = {
                        'title': title,
                        'location': venue_address,
                        'start_time': dt,
                        'end_time': dt.replace(hour=dt.hour + 2),  # Assume 2-hour duration
                        'url': event_url,
                        'is_public': True,
                        'description': f"Live music at {venue_name}" + 
                                     (f". Doors open at {doors_time.strftime('%I:%M %p')}" if doors_time else "")
                    }
                    events_data.append(event_data)
                except ValueError as e:
                    print(f"Error parsing date for event '{title}': {e}")
                    print(f"Date string attempted: '{main_time}'")
                    continue
                
    return events_data

if __name__ == "__main__":
    events = scrape_events()
    for event in events:
        print(f"Event: {event['title']}")
        print(f"When: {event['start_time']}")
        print(f"Where: {event['location']}")
        print(f"URL: {event['url']}")
        print(f"Description: {event['description']}")
        print("-" * 50)
