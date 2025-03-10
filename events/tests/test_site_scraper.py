import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from django.test import TestCase
import pytest
from crawl4ai import JsonCssExtractionStrategy
from events.scrapers.site_scraper import (
    transform_url,
    generate_css_schema,
    run_css_schema,
    AsyncWebCrawler
)
from events.utils.time_parser import extract_date_time_from_string, parse_datetime, format_event_datetime


class TestSiteScraper(TestCase):
    """Test suite for the site_scraper module."""

    def test_transform_url_absolute(self):
        """Test transforming an absolute URL."""
        url = "https://example.com/path/to/page"
        base_url = "https://example.com"
        
        result = transform_url(url, base_url)
        
        self.assertEqual(result, url)

    def test_transform_url_relative(self):
        """Test transforming a relative URL."""
        url = "/path/to/page"
        base_url = "https://example.com"
        
        result = transform_url(url, base_url)
        
        self.assertEqual(result, "https://example.com/path/to/page")

    def test_transform_url_none(self):
        """Test transforming a None URL."""
        url = None
        base_url = "https://example.com"
        
        result = transform_url(url, base_url)
        
        self.assertIsNone(result)

    @pytest.mark.asyncio
    @patch('crawl4ai.JsonCssExtractionStrategy.generate_schema')
    async def test_generate_css_schema(self, mock_generate_schema):
        """Test generating a CSS schema."""
        # Mock the generate_schema function
        mock_generate_schema.return_value = {
            "title": ".event-title",
            "date": ".event-date",
            "url": {"selector": ".event-link", "attribute": "href"}
        }
        
        # Call the function
        result = await generate_css_schema("https://example.com", "fake_api_key")
        
        # Check the result
        self.assertEqual(result["title"], ".event-title")
        self.assertEqual(result["date"], ".event-date")
        self.assertEqual(result["url"]["selector"], ".event-link")
        self.assertEqual(result["url"]["attribute"], "href")

    @pytest.mark.asyncio
    @patch('events.scrapers.site_scraper.AsyncWebCrawler')
    async def test_run_css_schema_for_dynamic_site(self, mock_crawler_class):
        """Test extracting events from a dynamic site with lazy loading."""
        # Create a mock crawler instance
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler
        
        # Mock the context manager
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.__aexit__.return_value = None
        
        # Mock the arun method
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.extracted_content = json.dumps([
            {
                "title": "Event 1",
                "date": "April 12, 2025 at 8:00 PM",
                "location": "Location 1",
                "url": "/event1",
                "image_url": "/image1.jpg"
            },
            {
                "title": "Event 2",
                "date": "April 13, 2025 at 9:00 PM",
                "location": "Location 2",
                "url": "/event2",
                "image_url": "/image2.jpg"
            }
        ])
        mock_crawler.arun.return_value = mock_result
        
        # Create a test schema
        test_schema = {
            "baseSelector": ".event-container",
            "title": ".event-title",
            "date": ".event-date",
            "location": ".event-location",
            "url": {"selector": "a.event-link", "attribute": "href"},
            "image_url": {"selector": "img.event-image", "attribute": "src"}
        }
        
        # Call the function
        result = await run_css_schema("https://example.com/events", test_schema)
        
        # Check the result
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["title"], "Event 1")
        self.assertEqual(result[0]["date"], "April 12, 2025")
        self.assertEqual(result[0]["start_time"], "8:00 PM")
        self.assertEqual(result[0]["location"], "Location 1")
        self.assertEqual(result[1]["title"], "Event 2")
        self.assertEqual(result[1]["date"], "April 13, 2025")
        self.assertEqual(result[1]["start_time"], "9:00 PM")
        self.assertEqual(result[1]["location"], "Location 2")

    @pytest.mark.asyncio
    @patch('events.scrapers.site_scraper.AsyncWebCrawler')
    async def test_css_schema_function(self, mock_crawler_class):
        """Test the run_css_schema function."""
        # Create a mock crawler instance
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler
        
        # Mock the context manager
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.__aexit__.return_value = None
        
        # Mock the arun method
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.extracted_content = json.dumps([
            {
                "title": "Event 1",
                "date": "April 12, 2025 at 8:00 PM",
                "location": "Location 1",
                "url": "/event1",
                "image_url": "/image1.jpg"
            }
        ])
        mock_crawler.arun.return_value = mock_result
        
        # Create a test schema
        test_schema = {
            "baseSelector": ".event-container",
            "title": ".event-title",
            "date": ".event-date",
            "location": ".event-location",
            "url": {"selector": "a.event-link", "attribute": "href"},
            "image_url": {"selector": "img.event-image", "attribute": "src"}
        }
        
        # Call the function
        result = await run_css_schema("https://example.com", test_schema)
        
        # Check the result
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Event 1")
        self.assertEqual(result[0]["date"], "April 12, 2025")
        self.assertEqual(result[0]["start_time"], "8:00 PM")
        self.assertEqual(result[0]["location"], "Location 1")
        self.assertEqual(result[0]["url"], "https://example.com/event1")
        self.assertEqual(result[0]["image_url"], "https://example.com/image1.jpg")

    @pytest.mark.asyncio
    @patch('events.scrapers.site_scraper.AsyncWebCrawler')
    async def test_data_src_image_extraction(self, mock_crawler_class):
        """Test the extraction of data-src images when src is empty."""
        # Create a mock crawler instance
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value = mock_crawler
        
        # Mock the context manager
        mock_crawler.__aenter__.return_value = mock_crawler
        mock_crawler.__aexit__.return_value = None
        
        # Mock the arun method
        mock_result = MagicMock()
        mock_result.success = True
        # Return data with empty image_url but a data_image_url
        mock_result.extracted_content = json.dumps([
            {
                "title": "Event 1",
                "date": "April 12, 2025 at 8:00 PM",
                "location": "Location 1",
                "url": "/event1",
                "image_url": "",  # Empty src
                "data_image_url": "/real-image1.jpg"  # data-src value
            }
        ])
        mock_crawler.arun.return_value = mock_result
        
        # Create a test schema with image_url selector but no data_image_url
        # Our code should automatically add the data_image_url selector
        test_schema = {
            "baseSelector": ".event-container",
            "title": ".event-title",
            "date": ".event-date",
            "location": ".event-location",
            "url": {"selector": "a.event-link", "attribute": "href"},
            "image_url": {"selector": "img.event-image", "attribute": "src"}
        }
        
        # Call the function
        result = await run_css_schema("https://example.com", test_schema)
        
        # Check the result - image_url should use the data_image_url value
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Event 1")
        self.assertEqual(result[0]["image_url"], "https://example.com/real-image1.jpg")
        
        # Also verify that data_image_url was added to the schema
        self.assertIn("data_image_url", test_schema)
        self.assertEqual(test_schema["data_image_url"]["selector"], "img.event-image")
        self.assertEqual(test_schema["data_image_url"]["attribute"], "data-src")

    def test_all_day_basic_format(self):
        """Test basic 'All Day' format with a simple date."""
        date_str = "March 15, 2025"
        time_str = "All Day"
        
        # Test the basic parsing
        start_dt, end_dt = format_event_datetime(date_str, time_str)
        
        # Verify the start time is set to 12:00 AM
        self.assertIn("2025-03-15 00:00:00", start_dt)
        
        # Verify the end time is set to 11:59 PM
        self.assertIn("2025-03-15 23:59:00", end_dt)
    
    def test_all_day_with_date_range(self):
        """Test 'All Day' format with a date range."""
        date_str = "March 15, 2025 - March 18, 2025"
        time_str = "All Day"
        
        # First verify extraction works correctly
        extracted_date, extracted_time, extracted_end = extract_date_time_from_string(date_str)
        self.assertEqual(extracted_date, "March 15, 2025")
        
        # Test the full formatting
        start_dt, end_dt = format_event_datetime(date_str, time_str)
        
        # Verify the start time is set to 12:00 AM
        self.assertIn("2025-03-15 00:00:00", start_dt)
        
        # Verify the end time is set to 11:59 PM
        self.assertIn("2025-03-15 23:59:00", end_dt)
    
    def test_all_day_case_insensitive(self):
        """Test that 'all day' is handled case-insensitively."""
        date_str = "March 15, 2025"
        time_variations = [
            "All Day", 
            "all day", 
            "ALL DAY", 
            "All day"
        ]
        
        for time_str in time_variations:
            with self.subTest(time_str=time_str):
                start_dt, end_dt = format_event_datetime(date_str, time_str)
                
                # Verify the start time is set to 12:00 AM
                self.assertIn("2025-03-15 00:00:00", start_dt)
                
                # Verify the end time is set to 11:59 PM
                self.assertIn("2025-03-15 23:59:00", end_dt)
    
    @pytest.mark.asyncio
    @patch('events.scrapers.site_scraper.AsyncWebCrawler')
    async def test_all_day_event_scraping(self, mock_crawler_class):
        """Test that 'All Day' events are scraped with correct start/end times."""
        # Mock the crawler response
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler
        
        # Create a test scraper schema
        css_schema = {
            "baseSelector": ".event",
            "fields": {
                "title": {"selector": "h2", "type": "text"},
                "date": {"selector": ".date", "type": "text"},
                "start_time": {"selector": ".time", "type": "text"}
            }
        }
        
        # Set up mock HTML content with an all-day event
        html_content = """
        <div class="event">
            <h2>Conference Day 1</h2>
            <div class="date">March 15, 2025</div>
            <div class="time">All Day</div>
        </div>
        """
        
        # Mock the fetch method
        mock_crawler.fetch.return_value = (True, html_content)
        
        # Run the scraper
        events = await run_css_schema('https://example.com', css_schema)
        
        # Verify that we have one event
        self.assertEqual(len(events), 1)
        
        # Get the event data
        event = events[0]
        self.assertEqual(event['title'], 'Conference Day 1')
        self.assertEqual(event['date'], 'March 15, 2025')
        self.assertEqual(event['start_time'], 'All Day')
        
        # Now test the format_event_datetime function
        from events.utils.time_parser import format_event_datetime
        start_dt, end_dt = format_event_datetime(event['date'], event['start_time'])
        
        # Verify the start time is 12:00 AM
        self.assertIn("2025-03-15 00:00:00", start_dt)
        
        # Verify the end time is 11:59 PM
        self.assertIn("2025-03-15 23:59:00", end_dt)
    
    @pytest.mark.asyncio
    @patch('events.scrapers.site_scraper.AsyncWebCrawler')
    async def test_date_range_all_day_event_scraping(self, mock_crawler_class):
        """Test that 'All Day' events with date ranges are scraped correctly."""
        # Mock the crawler response
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler
        
        # Create a test scraper schema
        css_schema = {
            "baseSelector": ".event",
            "fields": {
                "title": {"selector": "h2", "type": "text"},
                "date": {"selector": ".date", "type": "text"},
                "start_time": {"selector": ".time", "type": "text"}
            }
        }
        
        # Set up mock HTML content with an all-day event with a date range
        html_content = """
        <div class="event">
            <h2>Conference</h2>
            <div class="date">March 15, 2025 - March 18, 2025</div>
            <div class="time">All Day</div>
        </div>
        """
        
        # Mock the fetch method
        mock_crawler.fetch.return_value = (True, html_content)
        
        # Run the scraper
        events = await run_css_schema('https://example.com', css_schema)
        
        # Verify that we have one event
        self.assertEqual(len(events), 1)
        
        # Get the event data
        event = events[0]
        self.assertEqual(event['title'], 'Conference')
        self.assertEqual(event['date'], 'March 15, 2025 - March 18, 2025')
        self.assertEqual(event['start_time'], 'All Day')
        
        # Now test the format_event_datetime function
        from events.utils.time_parser import format_event_datetime
        start_dt, end_dt = format_event_datetime(event['date'], event['start_time'])
        
        # Verify the start time is 12:00 AM on the first day
        self.assertIn("2025-03-15 00:00:00", start_dt)
        
        # Verify the end time is 11:59 PM on the first day
        self.assertIn("2025-03-15 23:59:00", end_dt) 