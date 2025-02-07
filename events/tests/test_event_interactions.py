from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from events.models import Event, StarredEvent, EventResponse
import json
from datetime import timedelta

User = get_user_model()

class EventInteractionsTest(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        # Create test events with different times
        self.now = timezone.now()
        self.event1 = Event.objects.create(
            user=self.user,
            title='Event 1',
            description='Test Event 1',
            start_time=self.now - timedelta(hours=1)
        )
        self.event2 = Event.objects.create(
            user=self.user,
            title='Event 2',
            description='Test Event 2',
            start_time=self.now
        )
        self.event3 = Event.objects.create(
            user=self.user,
            title='Event 3',
            description='Test Event 3',
            start_time=self.now + timedelta(hours=1)
        )
        
        # Set up client and login
        self.client = Client()
        self.client.login(username='testuser', password='testpass123')

    def test_star_event(self):
        """Test starring and unstarring an event"""
        # Test starring an event
        response = self.client.post(
            reverse('events:toggle_star', args=[self.event1.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['is_starred'])
        self.assertTrue(StarredEvent.objects.filter(user=self.user, event=self.event1).exists())

        # Test unstarring the same event
        response = self.client.post(
            reverse('events:toggle_star', args=[self.event1.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['is_starred'])
        self.assertFalse(StarredEvent.objects.filter(user=self.user, event=self.event1).exists())

    def test_starred_events_list(self):
        """Test the starred events list view"""
        # Star two events
        StarredEvent.objects.create(user=self.user, event=self.event1)
        StarredEvent.objects.create(user=self.user, event=self.event2)

        # Test the starred events list view
        response = self.client.get(reverse('events:starred'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'events/starred.html')
        self.assertContains(response, 'Event 1')
        self.assertContains(response, 'Event 2')
        self.assertNotContains(response, 'Event 3')

    def test_event_response(self):
        """Test responding to events (thumbs up/down)"""
        # Test marking as going
        response = self.client.post(
            reverse('events:update_response', args=[self.event1.pk]),
            {'status': 'going'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['response']['status'], 'going')
        self.assertTrue(
            EventResponse.objects.filter(
                user=self.user,
                event=self.event1,
                status='going'
            ).exists()
        )

        # Test marking as not going
        response = self.client.post(
            reverse('events:update_response', args=[self.event1.pk]),
            {'status': 'not_going'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['response']['status'], 'not_going')
        self.assertTrue(
            EventResponse.objects.filter(
                user=self.user,
                event=self.event1,
                status='not_going'
            ).exists()
        )

        # Test invalid status
        response = self.client.post(
            reverse('events:update_response', args=[self.event1.pk]),
            {'status': 'invalid'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)

    def test_event_navigation(self):
        """Test previous/next event navigation"""
        # Test middle event (should have both prev and next)
        response = self.client.get(reverse('events:detail', args=[self.event2.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-event-id="{self.event1.pk}"')  # prev event
        self.assertContains(response, f'data-event-id="{self.event3.pk}"')  # next event

        # Test first event (should only have next)
        response = self.client.get(reverse('events:detail', args=[self.event1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-event-id=""')  # no prev event
        self.assertContains(response, f'data-event-id="{self.event2.pk}"')  # next event

        # Test last event (should only have prev)
        response = self.client.get(reverse('events:detail', args=[self.event3.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'data-event-id="{self.event2.pk}"')  # prev event
        self.assertNotContains(response, 'data-event-id=""')  # no next event

    def test_authentication_required(self):
        """Test that authentication is required for all interactions"""
        # Logout the user
        self.client.logout()

        # Test starring requires auth
        response = self.client.post(
            reverse('events:toggle_star', args=[self.event1.pk]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 302)  # redirects to login

        # Test event response requires auth
        response = self.client.post(
            reverse('events:update_response', args=[self.event1.pk]),
            {'status': 'going'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 302)  # redirects to login

        # Test starred events list requires auth
        response = self.client.get(reverse('events:starred'))
        self.assertEqual(response.status_code, 302)  # redirects to login

    def test_empty_starred_events(self):
        """Test the starred events page when no events are starred"""
        response = self.client.get(reverse('events:starred'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No Starred Events')
        self.assertContains(response, 'Events you star will appear here')

    def test_event_response_persistence(self):
        """Test that event responses persist correctly"""
        # Create a response
        response = self.client.post(
            reverse('events:update_response', args=[self.event1.pk]),
            {'status': 'going'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)

        # Verify response shows up in event detail
        response = self.client.get(reverse('events:detail', args=[self.event1.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'active')
        self.assertContains(response, 'bi-hand-thumbs-up-fill') 