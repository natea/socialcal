from seleniumbase import SB
from bs4 import BeautifulSoup
import logging
import re
from datetime import datetime
from .base_scraper import BaseScraper

def scrape_events():
    try:
        with SB(uc=True, headless=True, xvfb=True) as sb:
            # Navigate to the events page
            sb.get("https://www.regattabarjazz.com/calendar")
            
            # Wait for the content to load
            sb.wait_for_element_present("div.eventlist-column-info", timeout=10)
            
            # Get the page source
            html = sb.get_page_source()
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all event containers
            events = []
            event_containers = soup.find_all("div", class_="eventlist-event")
            
            for container in event_containers:
                try:
                    # Extract event details
                    title_elem = container.find("div", class_="eventlist-title")
                    title = title_elem.get_text(strip=True) if title_elem else "No Title"
                    
                    # Extract date and time
                    date_elem = container.find("time", class_="event-date")
                    if date_elem:
                        date_str = date_elem.get("datetime", "")
                        event_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                    else:
                        continue
                    
                    # Extract description
                    desc_elem = container.find("div", class_="eventlist-description")
                    description = desc_elem.get_text(strip=True) if desc_elem else ""
                    
                    # Extract ticket link
                    ticket_link = ""
                    link_elem = container.find("a", class_="eventlist-button")
                    if link_elem:
                        ticket_link = link_elem.get("href", "")
                    
                    # Create event dictionary
                    event = {
                        'title': title,
                        'date': event_date,
                        'description': description,
                        'ticket_link': ticket_link,
                        'venue': 'Regattabar',
                        'source': 'regattabar'
                    }
                    
                    events.append(event)
                    
                except Exception as e:
                    logging.error(f"Error processing event: {str(e)}")
                    continue
            
            return events
            
    except Exception as e:
        logging.error(f"Error during import: {str(e)}")
        return []

if __name__ == "__main__":
    events = scrape_events()
    for event in events:
        print(f"Event: {event['title']}")
        print(f"When: {event['date']}")
        print(f"Description: {event['description']}")
        print(f"Ticket Link: {event['ticket_link']}")
        print(f"Venue: {event['venue']}")
        print(f"Source: {event['source']}")
        print("-" * 50)
