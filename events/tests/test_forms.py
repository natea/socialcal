import pytest
from django.test import TestCase
from django.utils import timezone
import pytz
from events.forms import EventForm

class TestEventForm(TestCase):
    def setUp(self):
        self.base_data = {
            'title': 'Test Event',
            'description': 'Test Description',
            'timezone': 'America/New_York',
            'venue_name': 'Test Venue',
            'venue_address': '123 Test St',
            'venue_city': 'Test City',
            'venue_state': 'TS',
            'venue_postal_code': '12345',
            'venue_country': 'Test Country',
            'is_public': True
        }

    def test_valid_event_times(self):
        """Test that the form is valid when end_time is after start_time"""
        now = timezone.now()
        data = self.base_data.copy()
        data.update({
            'start_time': now.strftime('%Y-%m-%dT%H:%M'),
            'end_time': (now + timezone.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
        })
        
        form = EventForm(data=data)
        self.assertTrue(form.is_valid())

    def test_end_time_before_start_time(self):
        """Test that the form is invalid when end_time is before start_time"""
        now = timezone.now()
        data = self.base_data.copy()
        data.update({
            'start_time': now.strftime('%Y-%m-%dT%H:%M'),
            'end_time': (now - timezone.timedelta(hours=2)).strftime('%Y-%m-%dT%H:%M')
        })
        
        form = EventForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)
        self.assertIn('start_time', form.errors)
        self.assertEqual(form.errors['end_time'], ['End time must be after start time'])
        self.assertEqual(form.errors['start_time'], ['Start time must be before end time'])

    def test_equal_start_and_end_time(self):
        """Test that the form is invalid when start_time equals end_time"""
        now = timezone.now()
        data = self.base_data.copy()
        data.update({
            'start_time': now.strftime('%Y-%m-%dT%H:%M'),
            'end_time': now.strftime('%Y-%m-%dT%H:%M')
        })
        
        form = EventForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('end_time', form.errors)
        self.assertIn('start_time', form.errors)
        self.assertEqual(form.errors['end_time'], ['End time must be after start time'])
        self.assertEqual(form.errors['start_time'], ['Start time must be before end time'])

    def test_timezone_conversion(self):
        """Test that the form handles timezone conversion correctly"""
        # Create a specific time in Eastern timezone
        eastern = pytz.timezone('America/New_York')
        start = eastern.localize(timezone.datetime(2025, 1, 1, 10, 0))  # 10 AM ET
        end = eastern.localize(timezone.datetime(2025, 1, 1, 12, 0))    # 12 PM ET
        
        data = self.base_data.copy()
        data.update({
            'start_time': start.strftime('%Y-%m-%dT%H:%M'),
            'end_time': end.strftime('%Y-%m-%dT%H:%M'),
            'timezone': 'America/New_York'
        })
        
        form = EventForm(data=data)
        self.assertTrue(form.is_valid())
        
        # Verify the times are converted to UTC
        cleaned_start = form.cleaned_data['start_time']
        cleaned_end = form.cleaned_data['end_time']
        
        self.assertEqual(cleaned_start.tzinfo, pytz.UTC)
        self.assertEqual(cleaned_end.tzinfo, pytz.UTC)
        self.assertEqual(cleaned_start.hour, 15)  # 10 AM ET = 15:00 UTC
        self.assertEqual(cleaned_end.hour, 17)    # 12 PM ET = 17:00 UTC 