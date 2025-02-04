import unittest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
import os
import pytz
import pytest
from ..utils.time_parser import parse_datetime
from ..scrapers.generic_crawl4ai import GenericCrawl4AIScraper, EventModel

class TestGenericCrawl4AIScraper(unittest.TestCase):
    def setUp(self):
        self.current_time = datetime(2025, 1, 24, 16, 31, 1, tzinfo=pytz.timezone('America/New_York'))
        self.patcher = patch('events.utils.time_parser.datetime')
        self.mock_datetime = self.patcher.start()
        self.mock_datetime.now.return_value = self.current_time
        self.mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs) if args else self.current_time
        self.mock_datetime.strptime = datetime.strptime

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
            ("01/24", "8:00 PM", "2025-01-24", "20:00:00"),  # Same as current date
            ("January 24", "8:00 PM", "2025-01-24", "20:00:00"),  # Same as current date
            
            # Future month this year
            ("03/15", "8:00 PM", "2025-03-15", "20:00:00"),  # Future date this year
            ("March 15", "8:00 PM", "2025-03-15", "20:00:00"),  # Future date this year
            
            # Past dates (should use next year)
            ("01/15", "8:00 PM", "2026-01-15", "20:00:00"),  # More than 7 days ago
            ("December 15", "8:00 PM", "2025-12-15", "20:00:00"),  # Future date this year
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

    def test_scraper_initialization(self):
        """Test scraper initialization with different API token scenarios"""
        # Test with explicit token
        scraper = GenericCrawl4AIScraper(api_token="test_token")
        self.assertEqual(scraper.api_token, "test_token")

        # Test with environment variable
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'env_token'}):
            with patch('events.scrapers.generic_crawl4ai.settings') as mock_settings:
                mock_settings.OPENAI_API_KEY = None
                scraper = GenericCrawl4AIScraper()
                self.assertEqual(scraper.api_token, "env_token")

        # Test with no token
        with patch.dict(os.environ, {}, clear=True):
            with patch('events.scrapers.generic_crawl4ai.settings') as mock_settings:
                mock_settings.OPENAI_API_KEY = None
                scraper = GenericCrawl4AIScraper()
                self.assertIsNone(scraper.api_token)

    def test_event_model_validation(self):
        """Test EventModel validation"""
        # Test valid event data
        valid_event = {
            "event_title": "Test Event",
            "event_description": "Description",
            "event_date": "2025-01-24",
            "event_start_time": "8:00 PM",
            "event_end_time": "10:00 PM",
            "event_venue": "Venue",
            "event_venue_address": "Address",
            "event_venue_city": "City",
            "event_venue_state": "State",
            "event_venue_zip": "12345",
            "event_venue_country": "Country",
            "event_url": "http://test.com",
            "event_image_url": "http://test.com/image.jpg"
        }
        event_model = EventModel(**valid_event)
        self.assertEqual(event_model.event_title, "Test Event")

        # Test missing required fields
        invalid_event = valid_event.copy()
        del invalid_event["event_title"]
        with self.assertRaises(ValueError):
            EventModel(**invalid_event)

@pytest.mark.asyncio
class TestGenericCrawl4AIScraper_Async:
    @pytest.fixture
    def mock_crawler(self):
        with patch('events.scrapers.generic_crawl4ai.AsyncWebCrawler') as mock:
            yield mock

    @pytest.mark.asyncio
    async def test_extract_events_success(self, mock_crawler):
        """Test successful event extraction with various data formats"""
        test_cases = [
            # Single event with all fields
            [{
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
            }],
            # Multiple events
            [{
                "event_title": "Event 1",
                "event_description": "Desc 1",
                "event_date": "2025-01-24",
                "event_start_time": "8:00 PM",
                "event_end_time": "10:00 PM",
                "event_venue": "Venue 1",
                "event_venue_address": "",
                "event_venue_city": "",
                "event_venue_state": "",
                "event_venue_zip": "",
                "event_venue_country": "",
                "event_url": "",
                "event_image_url": ""
            },
            {
                "event_title": "Event 2",
                "event_description": "Desc 2",
                "event_date": "2025-01-25",
                "event_start_time": "9:00 PM",
                "event_end_time": "11:00 PM",
                "event_venue": "Venue 2",
                "event_venue_address": "",
                "event_venue_city": "",
                "event_venue_state": "",
                "event_venue_zip": "",
                "event_venue_country": "",
                "event_url": "",
                "event_image_url": ""
            }]
        ]

        for events_data in test_cases:
            mock_response = MagicMock()
            mock_response.extracted_content = events_data
            
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun.return_value = mock_response
            mock_crawler.return_value.__aenter__.return_value = mock_crawler_instance

            scraper = GenericCrawl4AIScraper(api_token="test_token")
            events = await scraper.extract_events("http://test.com")

            assert len(events) == len(events_data)
            for i, event in enumerate(events):
                assert event["title"] == events_data[i]["event_title"]
                assert event["venue_name"] == events_data[i]["event_venue"]

    @pytest.mark.asyncio
    async def test_extract_events_empty_response(self, mock_crawler):
        """Test handling of empty response from crawler"""
        mock_response = MagicMock()
        mock_response.extracted_content = []
        
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.arun.return_value = mock_response
        mock_crawler.return_value.__aenter__.return_value = mock_crawler_instance

        scraper = GenericCrawl4AIScraper(api_token="test_token")
        events = await scraper.extract_events("http://test.com")
        assert events == []

    @pytest.mark.asyncio
    async def test_extract_events_invalid_data(self, mock_crawler):
        """Test handling of invalid event data"""
        invalid_data = [
            None,  # None value
            "not a dict",  # String instead of dict
            {},  # Empty dict
            {"invalid_key": "value"},  # Dict with wrong keys
        ]

        for data in invalid_data:
            mock_response = MagicMock()
            mock_response.extracted_content = data
            
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun.return_value = mock_response
            mock_crawler.return_value.__aenter__.return_value = mock_crawler_instance

            scraper = GenericCrawl4AIScraper(api_token="test_token")
            events = await scraper.extract_events("http://test.com")
            assert events == []

    @pytest.mark.asyncio
    async def test_extract_events_error_handling(self, mock_crawler):
        """Test error handling during event extraction"""
        error_cases = [
            Exception("Generic error"),
            ValueError("Invalid value"),
            RuntimeError("Runtime error"),
            ConnectionError("Network error")
        ]

        for error in error_cases:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.arun.side_effect = error
            mock_crawler.return_value.__aenter__.return_value = mock_crawler_instance

            scraper = GenericCrawl4AIScraper(api_token="test_token")
            with pytest.raises(Exception) as exc_info:
                await scraper.extract_events("http://test.com")
            assert str(error) in str(exc_info.value)

if __name__ == '__main__':
    unittest.main()
