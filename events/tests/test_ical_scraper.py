import unittest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from events.models import Event
from events.scrapers.ical_scraper import ICalScraper
from datetime import datetime
import pytz
import requests

SAMPLE_ICAL_DATA = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Wayland Post - ECPv6.9.1//NONSGML v1.0//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Wayland Post
X-ORIGINAL-URL:https://www.waylandpost.org
X-WR-CALDESC:Events for Wayland Post

BEGIN:VEVENT
DTSTART;TZID=America/New_York:20250124T083000
DTEND;TZID=America/New_York:20250124T083000
DTSTAMP:20250124T130923
CREATED:20250123T225547Z
LAST-MODIFIED:20250123T225621Z
UID:10001316-1737707400-1737707400@www.waylandpost.org
SUMMARY:Economic Development Committee
DESCRIPTION:Test Description 1
LOCATION:Town Building\\, 41 Cochituate Road
CATEGORIES:Town Government
END:VEVENT

BEGIN:VEVENT
DTSTART;TZID=America/New_York:20250126T150000
DTEND;TZID=America/New_York:20250126T160000
DTSTAMP:20250124T130923
CREATED:20241218T201819Z
LAST-MODIFIED:20241218T201819Z
UID:10000730-1737903600-1737907200@www.waylandpost.org
SUMMARY:The Zahili Zamora Quartet
DESCRIPTION:Enjoy the talent of Cuban pianist\\, composer\\, and bandleader Zahili Zamora.
LOCATION:First Parish in Wayland\\, 225 Boston Post Road
CATEGORIES:Arts,Arts Wayland
END:VEVENT

BEGIN:VEVENT
DTSTART;TZID=America/New_York:20250127T174500
DTEND;TZID=America/New_York:20250127T191500
DTSTAMP:20250124T130923
CREATED:20241212T000621Z
LAST-MODIFIED:20241212T001622Z
UID:10000699-1737999900-1738005300@www.waylandpost.org
SUMMARY:Watercolor and Oil Pastel Workshop
DESCRIPTION:With Dr. Rahul Ray.
LOCATION:First Parish in Wayland\\, 225 Boston Post Road
CATEGORIES:Arts,Arts Wayland
END:VEVENT
END:VCALENDAR"""

SAMPLE_WEBPAGE_WITH_ICAL = """
<html>
<head>
    <link rel="alternate" type="text/calendar" href="https://example.com/events.ics">
    <link rel="alternate" type="application/x-webcal" href="webcal://example.com/feed.ics">
</head>
<body>
    <a href="webcal://example.com/feed.ics">Subscribe to Calendar</a>
    <a href="https://example.com/events/?ical=1">Export Calendar</a>
    <a href="https://example.com/calendar.ics">Download iCal</a>
</body>
</html>
"""

class TestICalScraper(TestCase):
    def setUp(self):
        self.scraper = ICalScraper()
        self.user = get_user_model().objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @patch('requests.get')
    def test_discover_ical_urls(self, mock_get):
        # Mock the webpage response
        mock_response = MagicMock()
        mock_response.text = SAMPLE_WEBPAGE_WITH_ICAL
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test URL discovery
        urls = self.scraper.discover_ical_urls('https://example.com')
        self.assertEqual(len(urls), 4)
        self.assertIn('https://example.com/events.ics', urls)
        self.assertIn('https://example.com/feed.ics', urls)
        self.assertIn('https://example.com/events/?ical=1', urls)
        self.assertIn('https://example.com/calendar.ics', urls)

    @patch('requests.get')
    def test_validate_ical_url(self, mock_get):
        # Mock valid iCal response
        mock_response = MagicMock()
        mock_response.content = SAMPLE_ICAL_DATA.encode('utf-8')
        mock_response.headers = {'content-type': 'text/calendar'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test validation
        result = self.scraper.validate_ical_url('https://example.com/events.ics')
        self.assertTrue(result)

        # Test invalid iCal data
        mock_response.content = 'Not an iCal file'.encode('utf-8')
        mock_response.headers = {'content-type': 'text/calendar'}
        mock_get.return_value = mock_response
        result = self.scraper.validate_ical_url('https://example.com/not-ical.txt')
        self.assertFalse(result)

    @patch('requests.get')
    def test_process_events(self, mock_get):
        # Mock iCal response
        mock_response = MagicMock()
        mock_response.content = SAMPLE_ICAL_DATA.encode('utf-8')
        mock_response.headers = {'content-type': 'text/calendar'}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test event processing
        events = self.scraper.process_events('https://example.com/events.ics')
        self.assertEqual(len(events), 3)
        
        # Check first event
        first_event = events[0]
        self.assertEqual(first_event['title'], 'Economic Development Committee')
        self.assertEqual(first_event['description'], 'Test Description 1')
        self.assertEqual(first_event['venue_name'], 'Town Building')
        self.assertEqual(first_event['venue_address'], '41 Cochituate Road')

        # Verify second event details
        event2 = events[1]
        self.assertEqual(event2['title'], 'The Zahili Zamora Quartet')
        self.assertEqual(event2['venue_name'], 'First Parish in Wayland')
        self.assertEqual(event2['venue_address'], '225 Boston Post Road')

        # Verify timezone handling
        eastern = pytz.timezone('America/New_York')
        self.assertTrue(timezone.is_aware(first_event['start_time']))
        self.assertEqual(first_event['start_time'].tzinfo.zone, 'America/New_York')

    @patch('requests.get')
    def test_webpage_to_events(self, mock_get):
        def mock_response(url, allow_redirects=True, **kwargs):
            response = MagicMock()
            if url == 'https://example.com':
                # Return HTML page for the initial URL
                response.content = SAMPLE_WEBPAGE_WITH_ICAL.encode('utf-8')
                response.text = SAMPLE_WEBPAGE_WITH_ICAL
                response.headers = {'content-type': 'text/html; charset=utf-8'}
            else:
                # Return iCal data for all other URLs (the discovered calendar URLs)
                response.content = SAMPLE_ICAL_DATA.encode('utf-8')
                response.text = SAMPLE_ICAL_DATA
                response.headers = {'content-type': 'text/calendar; charset=utf-8'}
            response.raise_for_status.return_value = None
            return response

        # Configure mock to use our custom response function
        mock_get.side_effect = mock_response

        # Test event processing from webpage
        events = self.scraper.process_events('https://example.com')
        self.assertEqual(len(events), 3)
        
        # Verify the discovered URL was used
        self.assertIsNotNone(self.scraper.selected_url)
        self.assertTrue(any(self.scraper.selected_url.endswith(ext) for ext in ['.ics', '?ical=1']))

    @patch('requests.get')
    def test_error_handling(self, mock_get):
        # Test network error
        mock_get.side_effect = requests.exceptions.RequestException('Network error')
        with self.assertRaises(Exception) as context:
            self.scraper.process_events('https://example.com/events.ics')
        self.assertIn('Failed to fetch URL', str(context.exception))

        # Test invalid iCal data
        mock_response = MagicMock()
        mock_response.content = 'Not an iCal file'.encode('utf-8')
        mock_response.headers = {'content-type': 'text/calendar'}
        mock_response.raise_for_status.return_value = None
        mock_get.side_effect = None
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as context:
            self.scraper.process_events('https://example.com/events.ics')
        self.assertIn('Invalid iCal data', str(context.exception))

if __name__ == '__main__':
    unittest.main()