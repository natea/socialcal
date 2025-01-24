import logging
from datetime import datetime, timedelta
import pytz

# Set up logging
logger = logging.getLogger(__name__)

def parse_datetime(date_str: str, time_str: str) -> tuple[str, str]:
    """Parse date and time strings into Django's expected format.
    Returns a tuple of (date, time) strings."""
    logger.info(f"Parsing date: '{date_str}' and time: '{time_str}'")
    
    if not date_str or not time_str:
        raise ValueError("Date and time strings cannot be empty")
    
    try:
        # Try to parse the date first
        current_date = datetime.now()
        current_year = current_date.year
        
        # Clean up the date string
        date_str = date_str.strip()
        
        # First try parsing with the date formats that include year
        date_formats_with_year = [
            ("%Y-%m-%d", date_str),                    # YYYY-MM-DD
            ("%m/%d/%Y", date_str),                    # MM/DD/YYYY
            ("%B %d, %Y", date_str),                   # Month DD, YYYY
        ]
        
        date_obj = None
        last_error = None
        
        # Try formats with year first
        for fmt, d_str in date_formats_with_year:
            try:
                date_obj = datetime.strptime(d_str, fmt)
                break
            except ValueError as e:
                last_error = e
                continue
        
        # If no year format worked, try formats without year
        if not date_obj:
            # No year in the date, need to determine appropriate year
            try:
                # Try parsing without year first
                if '/' in date_str:
                    month, day = map(int, date_str.split('/'))
                    test_date = datetime(current_year, month, day)
                else:
                    test_date = datetime.strptime(f"{date_str}, {current_year}", "%B %d, %Y")
                
                # Get current date for comparison
                current_date = datetime.now()
                
                # If the date is in the past and more than a few days ago, use next year
                days_ago = (current_date - test_date).days
                if days_ago > 7:  # If more than a week in the past
                    current_year += 1
                    logger.info(f"Date would be in the past, using next year: {current_year}")
                    # Reparse with new year
                    if '/' in date_str:
                        test_date = datetime(current_year, month, day)
                    else:
                        test_date = datetime.strptime(f"{date_str}, {current_year}", "%B %d, %Y")
                
                date_obj = test_date
            except ValueError as e:
                logger.warning(f"Failed to parse date: {str(e)}")
                raise ValueError(f"Invalid date format: {date_str}")
        
        if not date_obj:
            raise ValueError(f"Could not parse date: {date_str}")
        
        # Now parse the time
        try:
            # Convert 12-hour time to 24-hour time
            time_obj = datetime.strptime(time_str, "%I:%M %p")
            time_str_24h = time_obj.strftime("%H:%M:%S")
        except ValueError as e:
            raise ValueError(f"Invalid time format: {time_str}")
        
        return date_obj.strftime("%Y-%m-%d"), time_str_24h
        
    except Exception as e:
        logger.error(f"Error parsing date/time: {str(e)}")
        raise ValueError(f"Invalid date/time format: {str(e)}")

def format_event_datetime(date_str: str, time_str: str, end_time_str: str = None) -> tuple[str, str]:
    """Format event date and time into Django format with timezone.
    Returns a tuple of (start_datetime, end_datetime) strings."""
    try:
        # Parse date and times
        date, start_time = parse_datetime(date_str, time_str)
        
        # Parse end time if available
        _, end_time = parse_datetime(date_str, end_time_str) if end_time_str else ("", "")

        # Combine date and time for Django format with timezone
        tz = pytz.timezone('America/New_York')
        start_datetime = None
        end_datetime = None
        
        if date and start_time:
            try:
                # Create datetime object and make it timezone-aware
                dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M:%S")
                start_dt = tz.localize(dt)
                start_datetime = start_dt.strftime("%Y-%m-%d %H:%M:%S%z")
                
                # If no end time provided, set it to 2 hours after start time
                if not end_time:
                    end_dt = start_dt + timedelta(hours=2)
                    end_datetime = end_dt.strftime("%Y-%m-%d %H:%M:%S%z")
                else:
                    dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M:%S")
                    end_dt = tz.localize(dt)
                    end_datetime = end_dt.strftime("%Y-%m-%d %H:%M:%S%z")
            except Exception as e:
                logger.error(f"Error creating datetime: {str(e)}")
                # Don't raise, just return None values
                return None, None

        return start_datetime, end_datetime
        
    except Exception as e:
        logger.error(f"Error formatting event datetime: {str(e)}")
        return None, None
