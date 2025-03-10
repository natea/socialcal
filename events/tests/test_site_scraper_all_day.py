import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.utils import timezone
import pytest
from events.models import SiteScraper, Event
from events.scrapers.site_scraper import run_css_schema, scrape_with_site_scraper

class SiteScraperAllDayTests(TestCase):
    """Tests for the site scraper's handling of 'All Day' events."""
    
    def setUp(self):
        """Set up test data."""
        # Create a test user
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpassword'
        )
        
        # Create a test scraper
        self.scraper = SiteScraper.objects.create(
            user=self.user,
            name='Test Scraper',
            url='https://example.com',
            css_schema={
                "baseSelector": ".event",
                "fields": {
                    "title": {"selector": "h2", "type": "text"},
                    "date": {"selector": ".date", "type": "text"},
                    "start_time": {"selector": ".time", "type": "text"}
                }
            }
        )
    
    @pytest.mark.asyncio
    @patch('events.scrapers.site_scraper.AsyncWebCrawler')
    async def test_all_day_event_scraping(self, mock_crawler_class):
        """Test that 'All Day' events are scraped with correct start/end times."""
        # Mock the crawler response
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler
        
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
        events = await run_css_schema('https://example.com', self.scraper.css_schema)
        
        # Verify that we have one event
        self.assertEqual(len(events), 1)
        
        # Get the event data
        event = events[0]
        self.assertEqual(event['title'], 'Conference Day 1')
        self.assertEqual(event['date'], 'March 15, 2025')
        self.assertEqual(event['start_time'], 'All Day')
        
        # Now test the format_event_datetime function indirectly through the import function
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
        events = await run_css_schema('https://example.com', self.scraper.css_schema)
        
        # Verify that we have one event
        self.assertEqual(len(events), 1)
        
        # Get the event data
        event = events[0]
        self.assertEqual(event['title'], 'Conference')
        self.assertEqual(event['date'], 'March 15, 2025 - March 18, 2025')
        self.assertEqual(event['start_time'], 'All Day')
        
        # Now test the format_event_datetime function indirectly through the import function
        from events.utils.time_parser import format_event_datetime
        start_dt, end_dt = format_event_datetime(event['date'], event['start_time'])
        
        # Verify the start time is 12:00 AM on the first day
        self.assertIn("2025-03-15 00:00:00", start_dt)
        
        # Verify the end time is 11:59 PM on the first day
        # Note: Currently, our parser only takes the first date from a range
        self.assertIn("2025-03-15 23:59:00", end_dt)
    
    @pytest.mark.asyncio
    @patch('events.scrapers.site_scraper.AsyncWebCrawler')
    async def test_event_name_with_date_range_all_day(self, mock_crawler_class):
        """Test 'All Day' events with event name in the date range."""
        # Mock the crawler response
        mock_crawler = MagicMock()
        mock_crawler_class.return_value = mock_crawler
        
        # Set up mock HTML content with an all-day event with event name and date range
        html_content = """
        <div class="event">
            <h2>SCALE 22x</h2>
            <div class="date">SCALE 22x - March 6, 2025 - March 9, 2025</div>
            <div class="time">All Day</div>
        </div>
        """
        
        # Mock the fetch method
        mock_crawler.fetch.return_value = (True, html_content)
        
        # Run the scraper
        events = await run_css_schema('https://example.com', self.scraper.css_schema)
        
        # Verify that we have one event
        self.assertEqual(len(events), 1)
        
        # Get the event data
        event = events[0]
        self.assertEqual(event['title'], 'SCALE 22x')
        self.assertEqual(event['date'], 'SCALE 22x - March 6, 2025 - March 9, 2025')
        self.assertEqual(event['start_time'], 'All Day')
        
        # Now test the format_event_datetime function indirectly through the import function
        from events.utils.time_parser import format_event_datetime
        start_dt, end_dt = format_event_datetime(event['date'], event['start_time'])
        
        # Verify the start time is 12:00 AM
        self.assertIn("2025-03-06 00:00:00", start_dt)
        
        # Verify the end time is 11:59 PM
        self.assertIn("2025-03-06 23:59:00", end_dt) 