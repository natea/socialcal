import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase
from ..scrapers.site_scraper import (
    transform_url,
    generate_css_schema,
    run_css_schema
)


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