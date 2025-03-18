import asyncio
import logging
import os
import sys
from typing import List, Dict, Any
import re
import json
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class EventExtractor:
    """A generic extractor for event listings from various websites."""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def fetch_page(self, url: str) -> str:
        """Fetch the HTML content from a URL."""
        logger.info(f"Fetching page: {url}")
        try:
            async with self.session.get(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }) as response:
                if response.status != 200:
                    logger.error(f"Failed to fetch page: HTTP {response.status}")
                    return ""
                
                html = await response.text()
                logger.info(f"Successfully fetched page ({len(html)} bytes)")
                return html
        except Exception as e:
            logger.error(f"Error fetching page: {str(e)}")
            return ""
    
    def extract_events(self, html: str, url: str) -> List[Dict[str, Any]]:
        """Extract events from an HTML listing page."""
        events = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all event cards using multiple potential selectors
        event_cards = []
        card_selectors = [
            # Event-specific selectors (without naming sites)
            "article.event-card", "div.event-card", ".SearchResultPanelContentEventCard-module__card", 
            "article[data-event-id]", "div[data-event-id]",
            
            # More specific selectors based on common patterns
            "div[class*='event-card']", "div[class*='event-listing']", 
            "article[class*='event']", "div.event-listing-card",
            
            # Elements containing event attributes
            "div:has(h3):has(.event-date)", "div:has(h3):has(time)", "div:has(h3):has(.location)",
            
            # Generic card selectors as a fallback
            "article", ".card", ".event-item", "div[class*='card']",
        ]
        
        # Try each selector until we find some event cards
        for selector in card_selectors:
            try:
                cards = soup.select(selector)
                if cards and len(cards) > 0:
                    # Verify these are likely actual event cards by checking for titles or dates
                    for card in cards[:5]:  # Check first 5 cards
                        if card.find('h3') or card.find('h2') or card.select('[class*="date"]') or card.select('[class*="time"]'):
                            logger.info(f"Found {len(cards)} potential event cards using selector: {selector}")
                            event_cards = cards
                            break
                    
                    if event_cards:
                        break
            except Exception as e:
                logger.warning(f"Error using selector '{selector}': {str(e)}")
        
        if not event_cards:
            logger.warning("No event cards found. The page structure may have changed.")
            return []
        
        # Try to validate that these are actually event cards
        valid_cards = []
        for card in event_cards:
            # An event card should have at least a title, date, or link
            has_title = card.find('h3') is not None or card.find('h2') is not None
            has_date = card.select('[class*="date"]') or card.select('[class*="time"]') or \
                      any('date' in attr for attr in card.attrs.get('class', []))
            has_link = card.find('a') is not None
            
            if has_title or (has_date and has_link):
                valid_cards.append(card)
        
        if valid_cards:
            logger.info(f"Found {len(valid_cards)} valid event cards")
            event_cards = valid_cards
        
        # Debug: Output one full card HTML
        if len(event_cards) > 0:
            logger.debug(f"Sample event card HTML: {event_cards[0]}")
        
        # Track URLs to avoid duplicates
        seen_urls = set()
        
        for card in event_cards:
            try:
                event = self._extract_event_from_card(card, url)
                if event and event["title"]:  # Only include events with at least a title
                    # Check for duplicate URLs
                    if event["url"] and event["url"] in seen_urls:
                        continue
                    
                    # Add URL to seen set
                    if event["url"]:
                        seen_urls.add(event["url"])
                    
                    events.append(event)
            except Exception as e:
                logger.error(f"Error extracting event: {str(e)}")
        
        logger.info(f"Successfully extracted {len(events)} events")
        return events
    
    def _extract_event_from_card(self, card, base_url: str) -> Dict[str, Any]:
        """Extract event details from a single event card."""
        event = {
            "title": "",
            "date": "",
            "start_time": "",
            "end_time": "",
            "location": "",
            "description": "",
            "url": "",
            "image_url": ""
        }
        
        # Extract title - try multiple heading elements
        title_selectors = ["h3", "h2", "h4", "h5", ".title", "[class*='title']", "[class*='event-name']", ".event-name"]
        for selector in title_selectors:
            title_el = card.select_one(selector)
            if title_el and title_el.text.strip():
                event["title"] = title_el.text.strip()
                break
        
        # If no title found, try direct h3
        if not event["title"]:
            title_el = card.find("h3")
            if title_el:
                event["title"] = title_el.text.strip()
        
        # ----- EXTRACT DATE/TIME -----
        
        # First, look for the format "Day, Month DD" or similar patterns
        date_elements = []
        
        # Promotional texts to filter out
        promo_texts = ["almost full", "going fast", "sales end soon", "save", "share", "popular", "selling fast"]
        
        # Try multiple approaches for finding date elements
        
        # 1. Look for spans containing months or day names
        month_pattern = r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)'
        day_pattern = r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Mon|Tue|Wed|Thu|Fri|Sat|Sun)'
        date_with_time_pattern = r'(\w+,\s+\w+\s+\d{1,2},?\s+\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))'
        
        # Find specific elements that are likely to contain clean date information
        date_time_elements = []
        
        # Look for clean date format first (e.g., "Fri, Mar 21, 9:00 AM")
        for element in card.find_all(['span', 'p', 'div']):
            text = element.text.strip()
            # Look for a date with time pattern
            date_match = re.search(date_with_time_pattern, text)
            if date_match:
                clean_date = date_match.group(1)
                date_time_elements.append((clean_date, 5))  # Highest priority
                break
        
        # Find all elements that might contain date information
        for element in card.find_all(['span', 'p', 'div', 'time']):
            text = element.text.strip()
            
            # Skip promotional messages and other non-date text
            if any(promo in text.lower() for promo in promo_texts):
                continue
            
            # Skip if it contains the event title (likely not a date)
            if event["title"] and event["title"] in text:
                continue
                
            # Check for month names
            if re.search(month_pattern, text):
                # More specific date format: "Month Day" or "Day, Month Day"
                if re.search(r'\b\w+\s+\d{1,2}\b', text) or re.search(r'\b\w+,\s+\w+\s+\d{1,2}\b', text):
                    date_elements.append((text, 4))  # Higher priority for specific date formats
                else:
                    date_elements.append((text, 2))  # Medium priority
            
            # Check for day names
            elif re.search(day_pattern, text) and not re.search(r'save|share', text.lower()):
                # Check if it contains a time as well
                if re.search(r'at\s+\d{1,2}:\d{2}', text):
                    date_elements.append((text, 3))  # Higher priority if it has "at TIME"
                else:
                    date_elements.append((text, 1))  # Lower priority
        
        # 2. Look for time format (e.g., "7:00 PM")
        time_pattern = r'\d{1,2}:\d{2}\s*(?:AM|PM|am|pm)'
        for element in card.find_all(['span', 'p', 'div', 'time']):
            text = element.text.strip()
            if re.search(time_pattern, text) and len(text) < 50:  # Avoid long texts that happen to contain times
                # Skip if it contains promotional text
                if not any(promo in text.lower() for promo in promo_texts):
                    date_elements.append((text, 3))  # High priority
        
        # Combine all date elements
        all_elements = date_time_elements + date_elements
        
        # Sort by priority (highest first)
        all_elements.sort(key=lambda x: x[1], reverse=True)
        
        # Process found date elements
        if all_elements:
            # Use the highest priority element
            raw_date = all_elements[0][0]
            
            # Clean the date text by removing event title, promotional text, and other noise
            clean_date = raw_date
            
            # Remove common phrases that aren't dates
            for phrase in ["Save this event", "Share this event"]:
                clean_date = re.sub(f"{phrase}.*", "", clean_date, flags=re.IGNORECASE)
            
            # Remove promotional messages
            for promo in promo_texts:
                clean_date = re.sub(rf"\b{promo}\b", "", clean_date, flags=re.IGNORECASE)
            
            # Remove title if it appears in the date
            if event["title"]:
                clean_date = clean_date.replace(event["title"], "")
            
            # Extract real date and time using regex
            # Look for patterns like: "Fri, Mar 21, 9:00 AM" or "Friday at 6:30 PM"
            date_formats = [
                (r'(\w+,\s+\w+\s+\d{1,2},?\s+\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', 1),  # Friday, March 15, 7:00 PM
                (r'(\w+\s+at\s+\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', 1),  # Friday at 7:00 PM
                (r'(\w+\s+\d{1,2},?\s+\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))', 1),  # March 15, 7:00 PM
                (r'(\w+\s+\d{1,2})', 1)  # March 15
            ]
            
            for pattern, group in date_formats:
                match = re.search(pattern, clean_date)
                if match:
                    clean_date = match.group(group).strip()
                    break
            
            # Additional cleaning: Remove non-date artifacts (like year only or IDs)
            # Remove standalone numbers that aren't part of a proper date
            clean_date = re.sub(r'^\d{2,4}', '', clean_date)  # Remove year at the beginning
            clean_date = re.sub(r'^\s*\d{1,2}\s*$', '', clean_date)  # Remove standalone 1-2 digit number
            
            # Handle specific formats like "Registration" that might appear
            for term in ["Registration", "Attendee", "Tickets"]:
                clean_date = clean_date.replace(term, "")
            
            # Set date field to the cleaned date
            event["date"] = clean_date.strip()
            
            # Try to extract start time from the cleaned date
            time_matches = re.findall(time_pattern, clean_date)
            if time_matches:
                event["start_time"] = time_matches[0].strip()
                
                # If there are two times, assume the second is end time
                if len(time_matches) > 1:
                    event["end_time"] = time_matches[1].strip()
            
            # If we somehow lost the date in cleaning but have a start time, try to reconstruct a basic date
            if not event["date"] and event["start_time"]:
                # Check if we can find a date element with lower priority
                for date_element, _ in all_elements[1:]:  # Skip the first one we already processed
                    if re.search(day_pattern, date_element) or re.search(month_pattern, date_element):
                        day_match = re.search(day_pattern, date_element)
                        month_match = re.search(month_pattern, date_element)
                        
                        if day_match:
                            event["date"] = f"{day_match.group(0)} at {event['start_time']}"
                            break
                        elif month_match:
                            # Try to extract a day number
                            day_num_match = re.search(r'\b(\d{1,2})\b', date_element)
                            if day_num_match:
                                event["date"] = f"{month_match.group(0)} {day_num_match.group(0)}, {event['start_time']}"
                            else:
                                event["date"] = f"{month_match.group(0)}, {event['start_time']}"
                            break
        
        # 3. As a fallback, try looking for specific date-related classes
        if not event["date"]:
            date_classes = [
                "[class*='date']", 
                "[class*='time']",
                "[class*='calendar']",
                ".event-date",
                "time"
            ]
            
            for class_selector in date_classes:
                date_elements = card.select(class_selector)
                if date_elements:
                    for el in date_elements:
                        text = el.text.strip()
                        if text and not any(promo in text.lower() for promo in promo_texts):
                            event["date"] = text
                            break
                    
                    if event["date"]:
                        break
        
        # Extract location using multiple strategies
        location_selectors = [
            ".location", "[class*='location']", "[class*='venue']", "[class*='address']",
            ".venue", ".address", "[class*='place']"
        ]
        
        for selector in location_selectors:
            location_el = card.select_one(selector)
            if location_el and location_el.text.strip():
                text = location_el.text.strip()
                # Skip promotional messages
                if not any(promo in text.lower() for promo in promo_texts):
                    event["location"] = text
                    break
                
        # If no location found, try alternative approaches
        if not event["location"]:
            location_candidates = []
            
            # Look for paragraphs that might contain a location
            for p in card.find_all("p"):
                text = p.text.strip()
                # Skip if it looks like a date, time, or promotion
                if not re.search(time_pattern, text) and not re.search(month_pattern, text) and \
                   not any(promo in text.lower() for promo in promo_texts):
                    location_candidates.append(text)
            
            if location_candidates:
                event["location"] = location_candidates[0]
        
        # Extract URL
        url_selectors = ["a[href]", ".event-card a", ".event-title a", "h3 a", "h2 a"]
        for selector in url_selectors:
            url_el = card.select_one(selector)
            if url_el and "href" in url_el.attrs:
                url = url_el["href"]
                # Ensure it's an absolute URL
                if not url.startswith("http"):
                    # Try to construct absolute URL
                    from urllib.parse import urljoin
                    url = urljoin(base_url, url)
                event["url"] = url
                break
        
        # Extract image URL using multiple strategies
        img_selectors = ["img", ".event-image img", ".card-image img", "[class*='image'] img"]
        for selector in img_selectors:
            img_el = card.select_one(selector)
            if img_el:
                # Try both src and data-src attributes
                for attr in ["src", "data-src"]:
                    if attr in img_el.attrs and img_el[attr]:
                        # Make image URL absolute
                        img_url = img_el[attr]
                        if not img_url.startswith("http"):
                            from urllib.parse import urljoin
                            img_url = urljoin(base_url, img_url)
                        event["image_url"] = img_url
                        break
                
                if event["image_url"]:
                    break
        
        # If no image found, try looking for background images in style attributes
        if not event["image_url"]:
            bg_elements = card.select("[style*='background-image']")
            for bg_el in bg_elements:
                style = bg_el.get("style", "")
                url_match = re.search(r"url\(['\"]?(https?://[^'\")]+)['\"]?\)", style)
                if url_match:
                    event["image_url"] = url_match.group(1)
                    break
        
        # Try to extract description from meta tags or hidden elements
        description_selectors = [
            "[class*='description']", "[class*='desc']", 
            "meta[property='og:description']", "p"
        ]
        
        for selector in description_selectors:
            description_el = card.select_one(selector)
            if description_el:
                if description_el.name == "meta":
                    event["description"] = description_el.get("content", "")
                else:
                    # Avoid using titles, dates, or locations as descriptions
                    text = description_el.text.strip()
                    if (text and text != event["title"] and text != event["date"] and 
                        text != event["location"] and len(text) > 10):
                        event["description"] = text
                        break
        
        return event

async def scrape_events(url: str) -> List[Dict[str, Any]]:
    """Scrape events from a URL."""
    async with EventExtractor() as extractor:
        html = await extractor.fetch_page(url)
        if not html:
            return []
        
        events = extractor.extract_events(html, url)
        return events

async def main():
    """Main function to test event scraping."""
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default to a popular event listing site
        url = 'https://www.example.com/events'
        logger.info("No URL provided. Please provide a URL as a command line argument.")
        logger.info("Example: python event_extractor.py https://www.example.com/events")
        return
    
    logger.info(f"Scraping events from: {url}")
    events = await scrape_events(url)
    
    logger.info(f"Extracted {len(events)} events")
    
    # Print a sample of events
    for i, event in enumerate(events[:5]):
        logger.info(f"\nEvent {i+1}:")
        logger.info(f"Title: {event['title']}")
        logger.info(f"Date: {event['date']}")
        logger.info(f"Start time: {event['start_time']}")
        logger.info(f"Location: {event['location']}")
        logger.info(f"URL: {event['url']}")
    
    # Save to JSON file for inspection
    output_file = "extracted_events.json"
    with open(output_file, "w") as f:
        json.dump(events, f, indent=2)
    logger.info(f"Saved {len(events)} events to {output_file}")

if __name__ == "__main__":
    asyncio.run(main()) 