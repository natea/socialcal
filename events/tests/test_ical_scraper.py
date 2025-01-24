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
</head>
<body>
    <a href="webcal://example.com/feed.ics">Subscribe to Calendar</a>
    <a href="https://example.com/events/?ical=1">Export Calendar</a>
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
        self.assertEqual(len(urls), 3)
        self.assertIn('https://example.com/events.ics', urls)
        self.assertIn('https://example.com/feed.ics', urls)
        self.assertIn('https://example.com/events/?ical=1', urls)

    @patch('requests.get')
    def test_validate_ical_url(self, mock_get):
        # Mock valid iCal response
        mock_response = MagicMock()
        mock_response.text = SAMPLE_ICAL_DATA
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test validation
        is_valid = self.scraper.validate_ical_url('https://example.com/events.ics')
        self.assertTrue(is_valid)

        # Test invalid iCal data
        mock_response.text = "Not an iCal file"
        mock_get.return_value = mock_response
        is_valid = self.scraper.validate_ical_url('https://example.com/not-ical.txt')
        self.assertFalse(is_valid)

    @patch('requests.get')
    def test_process_events(self, mock_get):
        # Mock iCal response
        mock_response = MagicMock()
        mock_response.text = SAMPLE_ICAL_DATA
        mock_response.raise_for_status.return_value = None
        mock_response.url = 'https://example.com/events.ics'
        mock_get.return_value = mock_response

        # Process events
        events = self.scraper.process_events('https://example.com/events.ics')

        # Verify number of events
        self.assertEqual(len(events), 3)

        # Verify first event details
        event1 = events[0]
        self.assertEqual(event1['title'], 'Economic Development Committee')
        self.assertEqual(event1['venue_name'], 'Town Building')
        self.assertEqual(event1['venue_address'], '41 Cochituate Road')

        # Verify second event details
        event2 = events[1]
        self.assertEqual(event2['title'], 'The Zahili Zamora Quartet')
        self.assertEqual(event2['venue_name'], 'First Parish in Wayland')
        self.assertEqual(event2['venue_address'], '225 Boston Post Road')

        # Verify timezone handling
        eastern = pytz.timezone('America/New_York')
        self.assertTrue(timezone.is_aware(event1['start_time']))
        self.assertEqual(event1['start_time'].tzinfo.zone, 'America/New_York')

    @patch('requests.get')
    def test_webpage_to_events(self, mock_get):
        # Mock responses
        webpage_response = MagicMock()
        webpage_response.text = SAMPLE_WEBPAGE_WITH_ICAL
        webpage_response.raise_for_status.return_value = None

        ical_response = MagicMock()
        ical_response.text = SAMPLE_ICAL_DATA
        ical_response.raise_for_status.return_value = None
        ical_response.url = 'https://example.com/events.ics'

        # Configure mock to return different responses
        mock_get.side_effect = [webpage_response, ical_response, ical_response, ical_response]

        # Process events from webpage URL
        events = self.scraper.process_events('https://example.com/events')
        
        # Verify events were processed
        self.assertEqual(len(events), 3)
        self.assertTrue(any(e['title'] == 'Economic Development Committee' for e in events))
        self.assertTrue(any(e['title'] == 'The Zahili Zamora Quartet' for e in events))
        self.assertTrue(any(e['title'] == 'Watercolor and Oil Pastel Workshop' for e in events))

    def test_error_handling(self):
        # Test with invalid URL
        with self.assertRaises(Exception):
            self.scraper.process_events('not-a-url')

        # Test with non-existent URL
        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.exceptions.RequestException
            with self.assertRaises(Exception):
                self.scraper.process_events('https://nonexistent.example.com')

if __name__ == '__main__':
    unittest.main() 