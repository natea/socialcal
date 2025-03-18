import asyncio
import logging
import sys
from typing import Dict, Any, List, Optional
import os
import django

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialcal.settings')
django.setup()

from events.models import Event, SiteScraper
from eventbrite_extractor import scrape_eventbrite

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def scrape_and_save_eventbrite_events(scraper_url: str, scraper_name: str = None) -> List[Event]:
    """
    Scrape events from Eventbrite using our dedicated extractor and save them to the database.
    
    Args:
        scraper_url: The Eventbrite URL to scrape
        scraper_name: Optional name for the scraper
        
    Returns:
        A list of created or updated Event instances
    """
    # Check if the URL is from Eventbrite
    if "eventbrite.com" not in scraper_url.lower():
        logger.warning(f"URL {scraper_url} is not an Eventbrite URL. Skipping.")
        return []
    
    logger.info(f"Scraping events from Eventbrite URL: {scraper_url}")
    
    # Use our dedicated Eventbrite extractor
    events_data = await scrape_eventbrite(scraper_url)
    
    if not events_data:
        logger.warning(f"No events found for URL: {scraper_url}")
        return []
    
    logger.info(f"Found {len(events_data)} events to process")
    
    # Find or create a scraper
    if not scraper_name:
        scraper_name = f"Eventbrite Scraper - {scraper_url.split('/')[-2]}"
    
    # Create a SiteScraper without a user (since we're running this manually)
    try:
        scraper, created = SiteScraper.objects.get_or_create(
            url=scraper_url,
            defaults={
                'name': scraper_name,
                'user': None  # No user association for now
            }
        )
    except Exception as e:
        # If there's an issue with user field (like in the error), create a minimal scraper
        logger.warning(f"Error creating scraper with user: {str(e)}")
        # Check if a scraper already exists
        existing_scrapers = SiteScraper.objects.filter(url=scraper_url)
        if existing_scrapers.exists():
            scraper = existing_scrapers.first()
            logger.info(f"Using existing scraper: {scraper.name}")
        else:
            # Create a new scraper manually
            scraper = SiteScraper(
                name=scraper_name,
                url=scraper_url,
                # Skip the user field
                css_schema='{}'  # Empty schema since we're using our custom extractor
            )
            scraper.save()
            logger.info(f"Created new scraper: {scraper.name}")
    
    # Save events to database
    saved_events = []
    for event_data in events_data:
        try:
            # Check if URL exists
            if not event_data['url']:
                logger.warning("Skipping event with no URL")
                continue
                
            # Create or update event
            event, created = Event.objects.update_or_create(
                url=event_data['url'],
                defaults={
                    'scraper': scraper,
                    'title': event_data['title'] or "Untitled Event",
                    'description': event_data.get('description', ''),
                    'date': event_data.get('date', ''),
                    'start_time': event_data.get('start_time', ''),
                    'end_time': event_data.get('end_time', ''),
                    'location': event_data.get('location', ''),
                    'image_url': event_data.get('image_url', ''),
                }
            )
            
            status = "Created" if created else "Updated"
            logger.info(f"{status} event: {event.title}")
            saved_events.append(event)
            
        except Exception as e:
            logger.error(f"Error saving event: {str(e)}")
    
    logger.info(f"Successfully saved {len(saved_events)} events")
    return saved_events

async def process_all_eventbrite_scrapers():
    """Process all Eventbrite site scrapers in the database."""
    # Get all Eventbrite scrapers
    scrapers = SiteScraper.objects.filter(url__icontains='eventbrite.com')
    
    if not scrapers:
        logger.warning("No Eventbrite scrapers found in the database.")
        return
    
    logger.info(f"Found {scrapers.count()} Eventbrite scrapers to process")
    
    # Process each scraper
    total_events = 0
    for scraper in scrapers:
        events = await scrape_and_save_eventbrite_events(scraper.url, scraper.name)
        total_events += len(events)
        
    logger.info(f"Completed processing {scrapers.count()} scrapers. Total events saved: {total_events}")

async def main():
    """Main function to run the Eventbrite integration."""
    logger.info("Starting Eventbrite integration")
    
    # If a URL is provided as a command-line argument, process just that URL
    if len(sys.argv) > 1:
        url = sys.argv[1]
        logger.info(f"Processing single URL: {url}")
        await scrape_and_save_eventbrite_events(url)
    else:
        # Process all Eventbrite scrapers
        await process_all_eventbrite_scrapers()
    
    logger.info("Eventbrite integration completed")

if __name__ == "__main__":
    asyncio.run(main()) 