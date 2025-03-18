import asyncio
import logging
import sys
import os
import json
import re
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Import site_scraper functions directly
from site_scraper import generate_css_schema, run_css_schema

def is_date_like(text):
    """Check if the text looks like a date/time rather than promotional text."""
    if not text:
        return False
        
    # Check for common promotional phrases
    promo_phrases = ["almost full", "going fast", "sale", "end soon"]
    if any(phrase in text.lower() for phrase in promo_phrases):
        return False
        
    # Check for date/time patterns
    date_patterns = [
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)',
        r'(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',
        r'(Mon|Tue|Wed|Thu|Fri|Sat|Sun)',
        r'\d{1,2}:\d{2}',
        r'\d{1,2}(AM|PM|am|pm)',
        r'\d{1,2}/\d{1,2}',
    ]
    
    # Return True if any date pattern is found
    return any(re.search(pattern, text) for pattern in date_patterns)

async def test_improved_schema_generation(url):
    """Test the improved schema generation on the given URL."""
    logger.info(f"Testing improved schema generation for: {url}")
    
    try:
        # Get GEMINI_API_KEY from environment
        api_key = os.environ.get('GEMINI_API_KEY')
        if not api_key:
            logger.error("GEMINI_API_KEY not found in environment variables")
            return
        
        # Generate enhanced CSS schema
        logger.info("Generating enhanced CSS schema...")
        schema = await generate_css_schema(url, api_key)
        
        if not schema:
            logger.error("Failed to generate schema")
            return
        
        logger.info(f"Generated schema: {json.dumps(schema, indent=2)}")
        
        # Test the schema
        logger.info("\nTesting generated schema...")
        events = await run_css_schema(url, schema)
        
        logger.info(f"\nExtracted {len(events)} events")
        
        # Check if titles were extracted
        title_count = sum(1 for event in events if event.get('title'))
        logger.info(f"Events with title: {title_count}/{len(events)} ({title_count/len(events)*100:.1f}%)")
        
        # Check if dates are properly detected (not promotional text)
        date_counts = {
            "valid_dates": 0,
            "promotional_text": 0,
            "empty": 0
        }
        
        for event in events:
            date_text = event.get('date', '')
            if not date_text:
                date_counts["empty"] += 1
            elif is_date_like(date_text):
                date_counts["valid_dates"] += 1
            else:
                date_counts["promotional_text"] += 1
        
        # Report date quality
        logger.info(f"Date field quality:")
        logger.info(f"  - Valid dates: {date_counts['valid_dates']}/{len(events)} ({date_counts['valid_dates']/len(events)*100:.1f}%)")
        logger.info(f"  - Promotional text: {date_counts['promotional_text']}/{len(events)} ({date_counts['promotional_text']/len(events)*100:.1f}%)")
        logger.info(f"  - Empty: {date_counts['empty']}/{len(events)} ({date_counts['empty']/len(events)*100:.1f}%)")
        
        # Print the first 5 events as samples
        for i, event in enumerate(events[:5]):
            logger.info(f"\nEvent {i+1}:")
            logger.info(f"Title: {event.get('title', '')}")
            logger.info(f"Date: {event.get('date', '')}")
            logger.info(f"Start time: {event.get('start_time', '')}")
            logger.info(f"Location: {event.get('location', '')}")
            logger.info(f"URL: {event.get('url', '')}")
            logger.info(f"Image URL: {event.get('image_url', '')[0:100]}...")  # Truncate long image URLs
            
        # Return success indicator (good title and date extraction)
        success = {
            "title_success": title_count / len(events) > 0.7,  # At least 70% of events have titles
            "date_success": date_counts["valid_dates"] / len(events) > 0.7  # At least 70% have valid dates
        }
        return success
        
    except Exception as e:
        logger.error(f"Error testing improved schema: {str(e)}", exc_info=True)
        return {"title_success": False, "date_success": False}

async def main():
    """Main function to test multiple sites."""
    # Test URLs
    urls = [
        'https://www.eventbrite.com/d/oh--cincinnati/all-events/',
        # Add more sites to test if needed
    ]
    
    results = {}
    
    for url in urls:
        logger.info(f"\n\n{'='*50}\nTesting URL: {url}\n{'='*50}\n")
        success = await test_improved_schema_generation(url)
        
        # Format success message
        title_result = "✅ TITLE SUCCESS" if success.get("title_success", False) else "❌ TITLE FAILED"
        date_result = "✅ DATE SUCCESS" if success.get("date_success", False) else "❌ DATE FAILED"
        results[url] = f"{title_result} | {date_result}"
    
    # Print summary
    logger.info("\n\n" + "="*50)
    logger.info("SUMMARY OF RESULTS:")
    for url, result in results.items():
        logger.info(f"{result}: {url}")

if __name__ == "__main__":
    asyncio.run(main()) 