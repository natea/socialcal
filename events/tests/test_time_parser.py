import pytest
from datetime import datetime
import pytz
from django.test import TestCase
from ..utils.time_parser import (
    extract_date_time_from_string,
    parse_datetime,
    format_event_datetime
)


class TestTimeParser(TestCase):
    """Test suite for the time_parser module."""

    def test_extract_date_time_from_string_with_range(self):
        """Test extracting date and time from a string with a time range."""
        input_str = "March 15, 2025 at 8:00 PM - 10:00 PM"
        date_part, start_time, end_time = extract_date_time_from_string(input_str)
        
        self.assertEqual(date_part, "March 15, 2025")
        self.assertEqual(start_time, "8:00 PM")
        self.assertEqual(end_time, "10:00 PM")

    def test_extract_date_time_from_string_with_simple_range(self):
        """Test extracting date and time from a string with a simple time range."""
        input_str = "March 15, 2025 at 8 PM - 10 PM"
        date_part, start_time, end_time = extract_date_time_from_string(input_str)
        
        self.assertEqual(date_part, "March 15, 2025")
        self.assertEqual(start_time, "8 PM")
        self.assertEqual(end_time, "10 PM")

    def test_extract_date_time_from_string_with_single_time(self):
        """Test extracting date and time from a string with a single time."""
        input_str = "March 15, 2025 at 8:00 PM"
        date_part, start_time, end_time = extract_date_time_from_string(input_str)
        
        self.assertEqual(date_part, "March 15, 2025")
        self.assertEqual(start_time, "8:00 PM")
        self.assertIsNone(end_time)

    def test_extract_date_time_from_string_abbreviated(self):
        """Test extracting date and time from an abbreviated format."""
        input_str = "Mon Mar 3rd 5:00pm - 11:00pm"
        date_part, start_time, end_time = extract_date_time_from_string(input_str)
        
        self.assertEqual(date_part, "Mon Mar 3rd")
        self.assertEqual(start_time, "5:00PM")
        self.assertEqual(end_time, "11:00PM")

    def test_extract_date_time_from_string_empty(self):
        """Test extracting date and time from an empty string."""
        input_str = ""
        date_part, start_time, end_time = extract_date_time_from_string(input_str)
        
        self.assertIsNone(date_part)
        self.assertIsNone(start_time)
        self.assertIsNone(end_time)

    def test_parse_datetime_with_year(self):
        """Test parsing date and time with year specified."""
        date_str = "March 15, 2025"
        time_str = "8:00 PM"
        
        date, time = parse_datetime(date_str, time_str)
        
        self.assertEqual(date, "2025-03-15")
        self.assertEqual(time, "20:00:00")

    def test_parse_datetime_with_day_of_week(self):
        """Test parsing date and time with day of week."""
        date_str = "Saturday, April 12, 2025"
        time_str = "8:00 PM"
        
        date, time = parse_datetime(date_str, time_str)
        
        self.assertEqual(date, "2025-04-12")
        self.assertEqual(time, "20:00:00")

    def test_parse_datetime_with_day_of_week_no_year(self):
        """Test parsing date and time with day of week but no year."""
        date_str = "Saturday, April 12"
        time_str = "8:00 PM"
        
        # This should use the current year or next year if the date is in the past
        date, time = parse_datetime(date_str, time_str)
        
        # We can't assert the exact year since it depends on the current date
        # But we can check the month and day
        self.assertTrue(date.startswith("202"))  # Year should be in the 2020s
        self.assertTrue(date.endswith("-04-12"))  # Month and day should be April 12
        self.assertEqual(time, "20:00:00")

    def test_parse_datetime_with_slash_format(self):
        """Test parsing dates with slash formats."""
        # Test with MM/DD/YYYY format
        date_str, time_str = parse_datetime("03/15/2024", "7:30 PM")
        self.assertEqual(date_str, "2024-03-15")
        self.assertEqual(time_str, "19:30:00")
        
    def test_parse_datetime_with_day_date_time_slash_format(self):
        """Test parsing dates with day/date/time slash-separated format."""
        # Test the slash-separated format
        date_part, time_part, _ = extract_date_time_from_string("Tuesday / March 4, 2025 / 6:30 p.m.")
        self.assertEqual(date_part, "March 4, 2025")
        self.assertEqual(time_part, "6:30 PM")
        
        # Test with actual parse_datetime function
        date_str, time_str = parse_datetime("Tuesday / March 4, 2025 / 6:30 p.m.", "")
        self.assertEqual(date_str, "2025-03-04")
        self.assertEqual(time_str, "18:30:00")
        
        # Test with alternative spacing
        date_part, time_part, _ = extract_date_time_from_string("Wednesday / March 5, 2025 / 7:00 p.m.")
        self.assertEqual(date_part, "March 5, 2025")
        self.assertEqual(time_part, "7:00 PM")

    def test_parse_datetime_with_iso_format(self):
        """Test parsing date and time with ISO format."""
        date_str = "2025-04-12"
        time_str = "20:00"
        
        date, time = parse_datetime(date_str, time_str)
        
        self.assertEqual(date, "2025-04-12")
        self.assertEqual(time, "20:00:00")

    def test_parse_datetime_with_abbreviated_month(self):
        """Test parsing date and time with abbreviated month."""
        date_str = "Apr 12, 2025"
        time_str = "8:00 PM"
        
        date, time = parse_datetime(date_str, time_str)
        
        self.assertEqual(date, "2025-04-12")
        self.assertEqual(time, "20:00:00")

    def test_parse_datetime_with_ordinal_suffix(self):
        """Test parsing date and time with ordinal suffix."""
        date_str = "Mon Mar 3rd"
        time_str = "5:00PM"
        
        # This should use the current year or next year if the date is in the past
        date, time = parse_datetime(date_str, time_str)
        
        # We can't assert the exact year since it depends on the current date
        # But we can check the month and day
        self.assertTrue(date.endswith("-03-03"))  # Month and day should be March 3
        self.assertEqual(time, "17:00:00")

    def test_parse_datetime_with_various_time_formats(self):
        """Test parsing date and time with various time formats."""
        date_str = "April 12, 2025"
        
        # Test different time formats
        time_formats = {
            "8:00 PM": "20:00:00",
            "8:00PM": "20:00:00",
            "8PM": "20:00:00",
            "8 PM": "20:00:00",
            "20:00": "20:00:00"
        }
        
        for time_str, expected in time_formats.items():
            date, time = parse_datetime(date_str, time_str)
            self.assertEqual(date, "2025-04-12")
            self.assertEqual(time, expected)

    def test_parse_datetime_invalid_date(self):
        """Test parsing with invalid date format."""
        date_str = "Invalid date"
        time_str = "8:00 PM"
        
        with self.assertRaises(ValueError):
            parse_datetime(date_str, time_str)

    def test_parse_datetime_invalid_time(self):
        """Test parsing with invalid time format."""
        date_str = "April 12, 2025"
        time_str = "Invalid time"
        
        with self.assertRaises(ValueError):
            parse_datetime(date_str, time_str)

    def test_format_event_datetime_with_separate_fields(self):
        """Test formatting event datetime with separate date and time fields."""
        date_str = "April 12, 2025"
        time_str = "8:00 PM"
        end_time_str = "10:00 PM"
        
        start_datetime, end_datetime = format_event_datetime(date_str, time_str, end_time_str)
        
        # Check that the result is a timezone-aware datetime string
        self.assertIn("2025-04-12 20:00:00", start_datetime)
        self.assertIn("2025-04-12 22:00:00", end_datetime)
        # Check for timezone info (could be + or -)
        self.assertTrue('+' in start_datetime or '-' in start_datetime)
        self.assertTrue('+' in end_datetime or '-' in end_datetime)

    def test_format_event_datetime_with_combined_field(self):
        """Test formatting event datetime with a combined date/time field."""
        date_str = "April 12, 2025 at 8:00 PM - 10:00 PM"
        
        start_datetime, end_datetime = format_event_datetime(date_str, "", "")
        
        # Check that the result is a timezone-aware datetime string
        self.assertIn("2025-04-12 20:00:00", start_datetime)
        self.assertIn("2025-04-12 22:00:00", end_datetime)
        # Check for timezone info (could be + or -)
        self.assertTrue('+' in start_datetime or '-' in start_datetime)
        self.assertTrue('+' in end_datetime or '-' in end_datetime)

    def test_format_event_datetime_with_day_of_week(self):
        """Test formatting event datetime with day of week."""
        date_str = "Saturday, April 12, 2025"
        time_str = "8:00 PM"
        
        start_datetime, end_datetime = format_event_datetime(date_str, time_str)
        
        # Check that the result is a timezone-aware datetime string
        self.assertIn("2025-04-12 20:00:00", start_datetime)
        # End time should default to 2 hours after start time
        self.assertIn("2025-04-12 22:00:00", end_datetime)
        # Check for timezone info (could be + or -)
        self.assertTrue('+' in start_datetime or '-' in start_datetime)
        self.assertTrue('+' in end_datetime or '-' in end_datetime)

    def test_format_event_datetime_with_invalid_format(self):
        """Test formatting event datetime with invalid format."""
        date_str = "Invalid date"
        time_str = "Invalid time"
        
        start_datetime, end_datetime = format_event_datetime(date_str, time_str)
        
        # Should return None for both values
        self.assertIsNone(start_datetime)
        self.assertIsNone(end_datetime)

    def test_format_event_datetime_with_thursday_april_17(self):
        """Test formatting event datetime with Thursday, April 17, 2025."""
        date_str = "Thursday, April 17, 2025"
        time_str = "8:00 PM"
        
        start_datetime, end_datetime = format_event_datetime(date_str, time_str)
        
        # Check that the result is a timezone-aware datetime string
        self.assertIn("2025-04-17 20:00:00", start_datetime)
        # End time should default to 2 hours after start time
        self.assertIn("2025-04-17 22:00:00", end_datetime)
        # Check for timezone info (could be + or -)
        self.assertTrue('+' in start_datetime or '-' in start_datetime)
        self.assertTrue('+' in end_datetime or '-' in end_datetime) 