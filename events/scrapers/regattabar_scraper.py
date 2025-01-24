from seleniumbase import SB
import logging
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from django.utils import timezone

def scrape_events():
    try:
        with SB(uc=True, headless=True) as sb:
            # Configure longer timeouts and wait times
            sb.timeout_multiplier = 2
            
            # Navigate to the events page using CDP mode
            url = "https://www.ticketweb.com/venue/regattabar-cambridge-ma/748814?pl=regatta"
            sb.activate_cdp_mode(url)
            
            # Wait for dynamic content to load and scroll
            sb.wait_for_element("li.media.theme-mod", timeout=15)
            sb.sleep(3)  # Additional wait for Angular to settle
            
            # Scroll through the page to trigger lazy loading
            sb.execute_script("""
                window.scrollTo(0, 0);
                let lastHeight = document.body.scrollHeight;
                let newHeight = 0;
                let tries = 0;
                
                function scrollDown() {
                    window.scrollBy(0, 500);
                    newHeight = document.body.scrollHeight;
                    if (newHeight > lastHeight || tries < 5) {
                        lastHeight = newHeight;
                        tries++;
                        setTimeout(scrollDown, 500);
                    }
                }
                
                scrollDown();
            """)
            sb.sleep(2)  # Wait for any final loading
            
            # Get venue details
            try:
                venue_name = sb.get_text("h1.venue-name", timeout=10)
                venue_address = sb.get_text(".venue-address", timeout=10)
                logging.info(f"Venue: {venue_name}, Address: {venue_address}")
            except Exception as e:
                logging.error(f"Error getting venue details: {str(e)}")
                venue_name = "Regattabar"
                venue_address = "Cambridge, MA"
            
            events = []
            
            # Use JavaScript with explicit waits to extract event data
            event_data = sb.execute_script("""
                function waitForElements() {
                    return new Promise((resolve) => {
                        let checkCount = 0;
                        const check = () => {
                            const events = [];
                            const eventElements = document.querySelectorAll('li.media.theme-mod');
                            
                            if (eventElements.length > 0) {
                                eventElements.forEach(event => {
                                    try {
                                        const titleElem = event.querySelector('a.ng-scope');
                                        const dateElem = event.querySelector('p.event-date');
                                        
                                        if (titleElem && dateElem) {
                                            // Get computed styles to check visibility
                                            const titleStyle = window.getComputedStyle(titleElem);
                                            const dateStyle = window.getComputedStyle(dateElem);
                                            
                                            if (titleStyle.display !== 'none' && dateStyle.display !== 'none') {
                                                events.push({
                                                    title: titleElem.textContent.trim(),
                                                    link: titleElem.href,
                                                    date: dateElem.textContent.trim()
                                                });
                                            }
                                        }
                                    } catch (e) {
                                        console.error('Error processing event:', e);
                                    }
                                });
                                resolve(events);
                            } else if (checkCount < 10) {
                                checkCount++;
                                setTimeout(check, 500);
                            } else {
                                resolve([]);
                            }
                        };
                        check();
                    });
                }
                return await waitForElements();
            """)
            
            logging.info(f"Found {len(event_data)} event elements")
            
            # Debug: Log the raw event data
            logging.info("Raw event data:")
            for event in event_data:
                logging.info(str(event))
            
            for event in event_data:
                try:
                    title = event['title']
                    ticket_link = event['link']
                    date_text = event['date']
                    
                    logging.info(f"Raw date text for '{title}': {date_text}")
                    
                    if not date_text:
                        logging.error(f"No date text found for event: {title}")
                        continue
                    
                    # Parse the date
                    # Format: "Fri Jan 24 7:30 PM (Doors 7:00 PM)"
                    main_time = date_text.split(" (Doors")[0].strip()
                    logging.info(f"Main time part: {main_time}")
                    
                    try:
                        # Split the date parts
                        parts = main_time.split()
                        if len(parts) == 5:  # Should be ['Fri', 'Jan', '24', '7:30', 'PM']
                            weekday, month, day, time, meridiem = parts
                            
                            # Add the current year
                            year = datetime.now().year
                            
                            # Construct the datetime string
                            dt_string = f"{month} {day} {year} {time} {meridiem}"
                            logging.info(f"Constructed datetime string: {dt_string}")
                            
                            # Parse the datetime
                            naive_dt = datetime.strptime(dt_string, "%b %d %Y %I:%M %p")
                            eastern = ZoneInfo("America/New_York")
                            event_date = timezone.make_aware(naive_dt, eastern)
                            logging.info(f"Parsed event date: {event_date}")
                            
                            # Get doors time if available
                            doors_time = None
                            doors_match = re.search(r"\(Doors (\d+):(\d+) ([AP]M)\)", date_text)
                            if doors_match:
                                doors_hour = int(doors_match.group(1))
                                doors_min = int(doors_match.group(2))
                                doors_ampm = doors_match.group(3)
                                if doors_ampm == "PM" and doors_hour != 12:
                                    doors_hour += 12
                                naive_doors = naive_dt.replace(hour=doors_hour, minute=doors_min)
                                doors_time = timezone.make_aware(naive_doors, eastern)
                                logging.info(f"Doors time: {doors_time}")
                        else:
                            logging.error(f"Unexpected date format: {main_time}")
                            continue
                            
                    except Exception as e:
                        logging.error(f"Error parsing date '{main_time}': {str(e)}")
                        continue
                    
                    # Create event dictionary
                    event_dict = {
                        'title': title,
                        'date': event_date,
                        'description': f"Live music at {venue_name}. " + 
                                     (f"Doors open at {doors_time.strftime('%I:%M %p')}" if doors_time else ""),
                        'ticket_link': ticket_link,
                        'venue': venue_name,
                        'location': venue_address,
                        'source': 'regattabar'
                    }
                    
                    events.append(event_dict)
                    logging.info(f"Successfully processed event: {title}")
                    
                except Exception as e:
                    logging.error(f"Error processing event: {str(e)}")
                    continue
            
            logging.info(f"Successfully scraped {len(events)} events")
            return events
            
    except Exception as e:
        logging.error(f"Error during scraping: {str(e)}")
        return []

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    events = scrape_events()
    for event in events:
        print(f"Event: {event['title']}")
        print(f"When: {event['date']}")
        print(f"Description: {event['description']}")
        print(f"Ticket Link: {event['ticket_link']}")
        print(f"Venue: {event['venue']}")
        print(f"Location: {event['location']}")
        print(f"Source: {event['source']}")
        print("-" * 50)
