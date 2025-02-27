from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from events.models import Event
from datetime import datetime, timedelta
import json
import pytz

User = get_user_model()

class WeekViewTests(TestCase):
    def setUp(self):
        # Create a test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

        # Create some test events
        self.today = timezone.now()
        self.week_start = self.today - timedelta(days=self.today.weekday())  # Monday of current week
        
        # Create events for different days of the week
        self.events = []
        for i in range(3):
            event = Event.objects.create(
                user=self.user,
                title=f'Test Event {i+1}',
                description=f'Description for event {i+1}',
                start_time=self.week_start + timedelta(days=i, hours=10),
                end_time=self.week_start + timedelta(days=i, hours=11),
                venue_name=f'Venue {i+1}'
            )
            self.events.append(event)

    def test_week_view_get(self):
        """Test that the week view loads correctly"""
        today = timezone.now()
        response = self.client.get(reverse('calendar:week', kwargs={
            'year': today.year,
            'month': today.month,
            'day': today.day
        }))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calendar_app/week.html')

    def test_week_view_with_date(self):
        """Test week view with specific date parameters"""
        date = self.week_start + timedelta(days=14)  # Two weeks from now
        response = self.client.get(reverse('calendar:week', kwargs={
            'year': date.year,
            'month': date.month,
            'day': date.day
        }))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calendar_app/week.html')

    def test_week_view_context(self):
        """Test that the week view provides correct context"""
        today = timezone.now()
        response = self.client.get(reverse('calendar:week', kwargs={
            'year': today.year,
            'month': today.month,
            'day': today.day
        }))
        self.assertTrue('week_dates' in response.context)
        self.assertTrue('selected_date' in response.context)
        self.assertTrue('events' in response.context)
        
        # Check that we get 7 days in the week
        self.assertEqual(len(response.context['week_dates']), 7)
        
        # Check that the dates are consecutive
        dates = [date['date'] for date in response.context['week_dates']]
        for i in range(len(dates)-1):
            self.assertEqual(dates[i+1], dates[i] + timedelta(days=1))

    def test_get_day_events_api(self):
        """Test the API endpoint for getting events for a specific day"""
        # Test with a day that has events
        date = self.events[0].start_time.date().isoformat()
        response = self.client.get(reverse('events:day_events', kwargs={'date': date}))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('events' in data)
        self.assertEqual(len(data['events']), 1)
        # The API returns events ordered by start_time, and for this date
        # 'Test Event 2' is the event that falls on this day
        self.assertEqual(data['events'][0]['title'], 'Test Event 2')

    def test_get_day_events_api_no_events(self):
        """Test the API endpoint for a day with no events"""
        future_date = (self.today + timedelta(days=30)).date().isoformat()
        response = self.client.get(reverse('events:day_events', kwargs={'date': future_date}))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue('events' in data)
        self.assertEqual(len(data['events']), 0)

    def test_get_day_events_api_invalid_date(self):
        """Test the API endpoint with invalid date format"""
        response = self.client.get(reverse('events:day_events', kwargs={'date': 'invalid-date'}))
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertTrue('error' in data)

    def test_get_day_events_api_unauthorized(self):
        """Test that unauthorized users cannot access the API"""
        self.client.logout()
        date = self.events[0].start_time.date().isoformat()
        response = self.client.get(reverse('events:day_events', kwargs={'date': date}))
        self.assertEqual(response.status_code, 302)  # Should redirect to login

    def test_week_view_timezone_handling(self):
        """Test that the week view handles timezones correctly"""
        # Create an event near midnight in UTC
        utc_midnight = timezone.now().replace(hour=23, minute=30)
        event = Event.objects.create(
            user=self.user,
            title='Late Night Event',
            start_time=utc_midnight,
            end_time=utc_midnight + timedelta(hours=1)
        )

        # Test viewing the event in different timezones
        timezones_to_test = ['UTC', 'America/New_York', 'Asia/Tokyo']
        for tz_name in timezones_to_test:
            with self.settings(TIME_ZONE=tz_name):
                today = timezone.now()
                response = self.client.get(reverse('calendar:week', kwargs={
                    'year': today.year,
                    'month': today.month,
                    'day': today.day
                }))
                self.assertEqual(response.status_code, 200)
                
                # Get events for the day in the current timezone
                local_date = utc_midnight.astimezone(pytz.timezone(tz_name)).date().isoformat()
                response = self.client.get(reverse('events:day_events', kwargs={'date': local_date}))
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.content)
                self.assertTrue(any(e['title'] == 'Late Night Event' for e in data['events']))

    def test_week_navigation(self):
        """Test that week navigation returns correct dates"""
        # Test current week
        today = timezone.now()
        response = self.client.get(reverse('calendar:week', kwargs={
            'year': today.year,
            'month': today.month,
            'day': today.day
        }))
        current_week = response.context['week_dates']
        
        # Test next week
        next_week_start = self.week_start + timedelta(days=7)
        response = self.client.get(reverse('calendar:week', kwargs={
            'year': next_week_start.year,
            'month': next_week_start.month,
            'day': next_week_start.day
        }))
        next_week = response.context['week_dates']
        
        # Verify dates are 7 days apart
        self.assertEqual(
            next_week[0]['date'].date() - current_week[0]['date'].date(),
            timedelta(days=7)
        ) 