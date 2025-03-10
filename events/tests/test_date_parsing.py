import sys
from events.utils.time_parser import extract_date_time_from_string, parse_datetime, format_event_datetime

def test_date_range_parsing():
    """Test parsing of date ranges like "March 6, 2025 - March 9, 2025" with "All Day" time."""
    
    # Test cases for date ranges
    test_cases = [
        "March 6, 2025 - March 9, 2025",
        "March 6, 2025 - March 9, 2025 All Day",
        "SCALE 22x - March 6, 2025 - March 9, 2025 All Day",
        "March 10, 2025 - March 11, 2025",
        "FOSS Backstage - March 10, 2025 - March 11, 2025 All Day",
        "March 17, 2025 - March 18, 2025 All Day"
    ]
    
    print("\n--- Testing extract_date_time_from_string ---")
    for test_input in test_cases:
        print(f"\nInput: '{test_input}'")
        date_part, time_part, end_time = extract_date_time_from_string(test_input)
        print(f"Extracted: date='{date_part}', start_time='{time_part}', end_time='{end_time}'")
    
    print("\n--- Testing parse_datetime ---")
    for test_input in test_cases:
        print(f"\nInput: '{test_input}'")
        date_part, time_part, _ = extract_date_time_from_string(test_input)
        print(f"Extracted: date='{date_part}', start_time='{time_part}'")
        
        if date_part and time_part:
            try:
                parsed_date, parsed_time = parse_datetime(date_part, time_part)
                print(f"Parsed: date='{parsed_date}', time='{parsed_time}'")
            except Exception as e:
                print(f"Error parsing: {str(e)}")
        else:
            print(f"Cannot parse datetime: Missing date_part or time_part")
    
    print("\n--- Testing format_event_datetime ---")
    for test_input in test_cases:
        print(f"\nInput: '{test_input}'")
        date_part, time_part, end_time = extract_date_time_from_string(test_input)
        print(f"Extracted: date='{date_part}', start_time='{time_part}', end_time='{end_time}'")
        
        if date_part and time_part:
            try:
                start_dt, end_dt = format_event_datetime(date_part, time_part, end_time)
                print(f"Formatted: start='{start_dt}', end='{end_dt}'")
            except Exception as e:
                print(f"Error formatting: {str(e)}")
        else:
            print(f"Cannot format event datetime: Missing date_part or time_part")

# Run the test
print("Starting date range parsing tests...")
test_date_range_parsing()
print("Tests completed.") 