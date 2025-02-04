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
        
        # Create events for different days of the week with consistent ordering
        self.events = []
        base_time = self.week_start.replace(hour=10, minute=0)
        
        for i in range(3):
            event = Event.objects.create(
                user=self.user,
                title=f'Test Event {i+1}',
                description=f'Description for event {i+1}',
                start_time=base_time + timedelta(minutes=i*30),  # Space events 30 minutes apart
                end_time=base_time + timedelta(minutes=(i+1)*30),
                venue_name=f'Venue {i+1}'
            )
            self.events.append(event)

    def test_week_view_get(self):
        """Test that the week view loads correctly"""
        response = self.client.get(reverse('events:week'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calendar_app/week.html')

    def test_week_view_with_date(self):
        """Test week view with specific date parameters"""
        date = self.week_start + timedelta(days=14)  # Two weeks from now
        response = self.client.get(reverse('events:week_date', kwargs={
            'year': date.year,
            'month': date.month,
            'day': date.day
        }))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'calendar_app/week.html')

    def test_week_view_context(self):
        """Test that the week view provides correct context"""
        response = self.client.get(reverse('events:week'))
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
        
        # We should get all events for this day, ordered by start_time
        events_for_day = sorted(
            [e for e in self.events if e.start_time.date().isoformat() == date],
            key=lambda x: (x.start_time, x.id)
        )
        self.assertEqual(len(data['events']), len(events_for_day))
        
        # Verify all events match and are in the correct order
        for i, event in enumerate(events_for_day):
            self.assertEqual(data['events'][i]['title'], event.title)
            self.assertEqual(
                data['events'][i]['start_time'],
                event.start_time.isoformat()
            )

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
        
        # Should redirect to login page with next parameter
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/accounts/login/'))

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
                response = self.client.get(reverse('events:week'))
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
        response = self.client.get(reverse('events:week'))
        current_week = response.context['week_dates']
        
        # Test next week
        next_week_start = self.week_start + timedelta(days=7)
        response = self.client.get(reverse('events:week_date', kwargs={
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