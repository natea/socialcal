import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
import pytz
import pytest
from ..utils.time_parser import parse_datetime
from ..scrapers.generic_crawl4ai import GenericCrawl4AIScraper

class TestGenericCrawl4AIScraper(unittest.TestCase):
    def setUp(self):
        self.current_time = datetime(2025, 1, 24, 16, 31, 1, tzinfo=pytz.timezone('America/New_York'))
        self.patcher = patch('datetime.datetime')
        self.mock_datetime = self.patcher.start()
        self.mock_datetime.now.return_value = self.current_time
        self.mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

    def tearDown(self):
        self.patcher.stop()

    def test_parse_datetime_with_explicit_year(self):
        """Test parsing dates that include the year explicitly"""
        test_cases = [
            # Format: (date_str, time_str, expected_date, expected_time)
            ("2025-01-24", "8:00 PM", "2025-01-24", "20:00:00"),
            ("01/24/2025", "8:00 PM", "2025-01-24", "20:00:00"),
            ("January 24, 2025", "8:00 PM", "2025-01-24", "20:00:00"),
        ]
        
        for date_str, time_str, expected_date, expected_time in test_cases:
            with self.subTest(date_str=date_str):
                date, time = parse_datetime(date_str, time_str)
                self.assertEqual(date, expected_date)
                self.assertEqual(time, expected_time)

    def test_parse_datetime_without_year(self):
        """Test parsing dates without explicit year"""
        test_cases = [
            # Current month
            ("01/24", "8:00 PM", "2025-01-24", "20:00:00"),
            ("January 24", "8:00 PM", "2025-01-24", "20:00:00"),
            
            # Future month this year
            ("03/15", "8:00 PM", "2025-03-15", "20:00:00"),
            ("March 15", "8:00 PM", "2025-03-15", "20:00:00"),
            
            # Next year (when date would be in the past)
            ("01/15", "8:00 PM", "2026-01-15", "20:00:00"),  # More than 1 month ago
            ("December 15", "8:00 PM", "2025-12-15", "20:00:00"),
        ]
        
        for date_str, time_str, expected_date, expected_time in test_cases:
            with self.subTest(date_str=date_str):
                date, time = parse_datetime(date_str, time_str)
                self.assertEqual(date, expected_date)
                self.assertEqual(time, expected_time)

    def test_parse_datetime_invalid_formats(self):
        """Test handling of invalid date formats"""
        invalid_dates = [
            "",  # Empty string
            "invalid",  # Invalid format
            "13/45/2025",  # Invalid date
            "January 32, 2025",  # Invalid day
        ]
        
        for date_str in invalid_dates:
            with self.subTest(date_str=date_str):
                with self.assertRaises(ValueError):
                    parse_datetime(date_str, "8:00 PM")

    def test_parse_datetime_invalid_times(self):
        """Test handling of invalid time formats"""
        invalid_times = [
            "",  # Empty string
            "invalid",  # Invalid format
            "25:00 PM",  # Invalid hour
            "8:60 PM",  # Invalid minute
        ]
        
        for time_str in invalid_times:
            with self.subTest(time_str=time_str):
                with self.assertRaises(ValueError):
                    parse_datetime("2025-01-24", time_str)

@pytest.mark.asyncio
class TestGenericCrawl4AIScraper_Async:
    async def test_extract_events(self):
        """Test the event extraction functionality"""
        # Mock the crawler response
        mock_response = MagicMock()
        mock_response.extracted_content = [
            {
                "event_title": "Test Event 1",
                "event_description": "Description 1",
                "event_date": "01/24/2025",
                "event_start_time": "8:00 PM",
                "event_end_time": "10:00 PM",
                "event_venue": "Test Venue",
                "event_venue_address": "123 Test St",
                "event_venue_city": "Test City",
                "event_venue_state": "TS",
                "event_venue_zip": "12345",
                "event_venue_country": "USA",
                "event_url": "http://test.com/event1",
                "event_image_url": "http://test.com/image1.jpg"
            }
        ]
        
        with patch('events.scrapers.generic_crawl4ai.AsyncWebCrawler') as mock_crawler:
            mock_crawler_instance = MagicMock()
            mock_crawler_instance.arun.return_value = mock_response
            mock_crawler.return_value.__aenter__.return_value = mock_crawler_instance

            # Create scraper instance and test
            scraper = GenericCrawl4AIScraper(api_token="test_token")
            events = await scraper.extract_events("http://test.com")

            # Verify the extracted event
            assert len(events) == 1
            event = events[0]
            assert event["title"] == "Test Event 1"
            assert "2025-01-24" in event["start_time"]
            assert "20:00:00" in event["start_time"]
            assert event["venue_name"] == "Test Venue"

    async def test_extract_events_error_handling(self):
        """Test error handling during event extraction"""
        with patch('events.scrapers.generic_crawl4ai.AsyncWebCrawler') as mock_crawler:
            # Mock crawler to raise an exception
            mock_crawler_instance = MagicMock()
            mock_crawler_instance.arun.side_effect = Exception("Test error")
            mock_crawler.return_value.__aenter__.return_value = mock_crawler_instance

            # Create scraper instance and test
            scraper = GenericCrawl4AIScraper(api_token="test_token")
            with pytest.raises(Exception):
                await scraper.extract_events("http://test.com")

if __name__ == '__main__':
    unittest.main()
