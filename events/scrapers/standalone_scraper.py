import asyncio
import logging
import sys
import json
import argparse
from event_extractor import scrape_events

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def extract_events(url: str, output_file: str = None):
    """
    Extract events from a URL and save them to a JSON file.
    
    Args:
        url: The URL to scrape
        output_file: Optional file path to save the events data
        
    Returns:
        The list of extracted events
    """
    logger.info(f"Scraping events from URL: {url}")
    
    # Use our generic event extractor
    events = await scrape_events(url)
    
    if not events:
        logger.warning(f"No events found for URL: {url}")
        return []
    
    logger.info(f"Found {len(events)} events")
    
    # Display a sample of events
    for i, event in enumerate(events[:5]):
        logger.info(f"\nEvent {i+1}:")
        logger.info(f"Title: {event['title']}")
        logger.info(f"Date: {event['date']}")
        logger.info(f"Start time: {event['start_time']}")
        logger.info(f"Location: {event['location']}")
        logger.info(f"URL: {event['url']}")
    
    # Save to JSON file if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(events, f, indent=2)
        logger.info(f"Saved {len(events)} events to {output_file}")
    
    return events

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Extract events from a URL.")
    parser.add_argument("url", nargs="?", help="URL to scrape")
    parser.add_argument("-o", "--output", help="Output JSON file path")
    return parser.parse_args()

async def main():
    """Main function to run the event extractor."""
    args = parse_arguments()
    logger.info("Starting event extraction")
    
    if not args.url:
        logger.error("No URL provided. Please provide a URL as a command line argument.")
        logger.info("Example: python standalone_scraper.py https://example.com/events")
        return
        
    url = args.url
    output_file = args.output or "extracted_events.json"
    
    await extract_events(url, output_file)
    
    logger.info("Event extraction completed")

if __name__ == "__main__":
    asyncio.run(main()) 