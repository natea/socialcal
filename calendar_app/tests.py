from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from events.models import Event
from datetime import datetime
import pytz

User = get_user_model()

@override_settings(USE_TZ=True)
class CalendarViewTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')
        
        # Set up timezone for testing
        self.user_timezone = pytz.timezone('America/New_York')
        session = self.client.session
        session['event_timezone'] = 'America/New_York'
        session.save()

    def test_calendar_view_no_events(self):
        """Test calendar view with no events"""
        response = self.client.get(reverse('calendar:month', kwargs={'year': 2024, 'month': 2}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calendar_app/month.html')
        self.assertContains(response, 'February 2024')

    def test_calendar_view_with_events(self):
        """Test calendar view displays events on correct days"""
        # Create an event at 8 PM EST on February 15, 2024
        local_dt = self.user_timezone.localize(datetime(2024, 2, 15, 20, 0))
        event = Event.objects.create(
            user=self.user,
            title='Test Event',
            start_time=local_dt.astimezone(pytz.UTC),  # Store in UTC
            end_time=local_dt.astimezone(pytz.UTC) + timezone.timedelta(hours=2)
        )

        response = self.client.get(reverse('calendar:month', kwargs={'year': 2024, 'month': 2}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Event')
        # Verify event appears on February 15
        content = response.content.decode()
        self.assertTrue(any('15' in cell and 'Test Event' in cell 
                          for cell in content.split('<td')))

    def test_event_timezone_crossing_day_boundary(self):
        """Test events near midnight appear on correct day in user's timezone"""
        # Create event at 11 PM EST on February 15, 2024
        # This will be 4 AM UTC on February 16
        local_dt = self.user_timezone.localize(datetime(2024, 2, 15, 23, 0))
        event = Event.objects.create(
            user=self.user,
            title='Late Night Event',
            start_time=local_dt.astimezone(pytz.UTC),
            end_time=local_dt.astimezone(pytz.UTC) + timezone.timedelta(hours=2)
        )

        response = self.client.get(reverse('calendar:month', kwargs={'year': 2024, 'month': 2}))
        self.assertEqual(response.status_code, 200)
        
        # Event should appear on February 15 in EST, even though it's February 16 in UTC
        content = response.content.decode()
        self.assertIn('Late Night Event', content)
        # Verify event appears in the cell for day 15
        self.assertTrue(any('15' in cell and 'Late Night Event' in cell 
                          for cell in content.split('<td')))

    def test_events_spanning_months(self):
        """Test events at month boundaries appear in correct month"""
        # Create event at 11 PM EST on January 31, 2024
        local_dt = self.user_timezone.localize(datetime(2024, 1, 31, 23, 0))
        event = Event.objects.create(
            user=self.user,
            title='Month Boundary Event',
            start_time=local_dt.astimezone(pytz.UTC),
            end_time=local_dt.astimezone(pytz.UTC) + timezone.timedelta(hours=2)
        )

        # Check January view
        response = self.client.get(reverse('calendar:month', kwargs={'year': 2024, 'month': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Month Boundary Event')

        # Check February view - should not contain the event
        response = self.client.get(reverse('calendar:month', kwargs={'year': 2024, 'month': 2}))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Month Boundary Event')

    def test_different_timezone_display(self):
        """Test events display correctly when user changes timezone"""
        # Create event at midnight UTC on February 1
        utc_dt = pytz.UTC.localize(datetime(2024, 2, 1, 0, 0))
        event = Event.objects.create(
            user=self.user,
            title='Timezone Test Event',
            start_time=utc_dt,
            end_time=utc_dt + timezone.timedelta(hours=2)
        )

        # Test with Eastern Time (event should appear on January 31)
        session = self.client.session
        session['event_timezone'] = 'America/New_York'
        session.save()
        
        response = self.client.get(reverse('calendar:month', kwargs={'year': 2024, 'month': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Timezone Test Event')

        # Test with Pacific Time (event should also appear on January 31)
        session = self.client.session
        session['event_timezone'] = 'America/Los_Angeles'
        session.save()
        
        response = self.client.get(reverse('calendar:month', kwargs={'year': 2024, 'month': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Timezone Test Event')

    def test_navigation_between_months(self):
        """Test navigation between months works correctly"""
        # Start with February 2024
        response = self.client.get(reverse('calendar:month', kwargs={'year': 2024, 'month': 2}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'February 2024')

        # Get next month link (March 2024)
        self.assertContains(response, reverse('calendar:month', kwargs={'year': 2024, 'month': 3}))

        # Get previous month link (January 2024)
        self.assertContains(response, reverse('calendar:month', kwargs={'year': 2024, 'month': 1}))

        # Test year boundary navigation
        response = self.client.get(reverse('calendar:month', kwargs={'year': 2024, 'month': 12}))
        self.assertEqual(response.status_code, 200)
        # Should have link to January 2025
        self.assertContains(response, reverse('calendar:month', kwargs={'year': 2025, 'month': 1})) 