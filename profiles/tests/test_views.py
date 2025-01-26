import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from profiles.models import Profile
from events.models import Event
from accounts.adapters import EmailAccountAdapter

User = get_user_model()

@pytest.mark.django_db
class TestProfileViews:
    def create_test_user(self, email, password):
        user = User.objects.create_user(username=email.split('@')[0], email=email, password=password)
        adapter = EmailAccountAdapter()
        adapter.populate_username(None, user)
        user.save()
        return user
        
    def test_profile_list_view(self, client):
        user = self.create_test_user('test@example.com', 'testpass123')
        response = client.get(reverse('profiles:list'))
        assert response.status_code == 200
        assert user.profile in response.context['profiles']
        
    def test_profile_detail_view(self, client):
        user = self.create_test_user('test@example.com', 'testpass123')
        response = client.get(reverse('profiles:detail', kwargs={'email': user.email}))
        assert response.status_code == 200
        assert response.context['profile'] == user.profile
        
    def test_profile_detail_view_with_private_calendar(self, client):
        owner = self.create_test_user('owner@example.com', 'testpass123')
        viewer = self.create_test_user('viewer@example.com', 'testpass123')
        
        # Create an event
        event = Event.objects.create(
            user=owner,
            title='Test Event',
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )
        
        # Make calendar private
        owner.profile.calendar_public = False
        owner.profile.save()
        
        # Test as viewer
        client.force_login(viewer)
        response = client.get(reverse('profiles:detail', kwargs={'email': owner.email}))
        assert response.status_code == 200
        assert len(response.context['events']) == 0
        assert not response.context['can_view_events']
        
    def test_profile_detail_view_with_public_calendar(self, client):
        owner = self.create_test_user('owner@example.com', 'testpass123')
        viewer = self.create_test_user('viewer@example.com', 'testpass123')
        
        # Create an event with a fixed future time
        future_time = timezone.now() + timezone.timedelta(days=1)
        event = Event.objects.create(
            user=owner,
            title='Test Event',
            start_time=future_time,
            end_time=future_time + timezone.timedelta(hours=1),
            is_public=True
        )
        
        # Verify event was created correctly
        assert event.is_public is True
        assert event.user == owner
        assert event.start_time > timezone.now()
        
        # Make calendar public
        owner.profile.calendar_public = True
        owner.profile.save()
        
        # Verify profile settings
        owner.profile.refresh_from_db()
        assert owner.profile.calendar_public is True
        
        # Test as viewer
        client.force_login(viewer)
        response = client.get(reverse('profiles:detail', kwargs={'email': owner.email}))
        assert response.status_code == 200
        
        # Debug output
        print("Events in response:", response.context['events'])
        print("Event public:", event.is_public)
        print("Calendar public:", owner.profile.calendar_public)
        print("Event start time:", event.start_time)
        print("Current time:", timezone.now())
        
        assert len(response.context['events']) == 1
        assert response.context['can_view_events']
        assert event in response.context['events']
        
    def test_profile_edit_view_owner(self, client):
        user = self.create_test_user('test@example.com', 'testpass123')
        client.force_login(user)
        
        response = client.get(reverse('profiles:edit', kwargs={'email': user.email}))
        assert response.status_code == 200
        
        # Test POST
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'bio': 'Test bio',
            'location': 'Test City',
            'calendar_public': True
        }
        response = client.post(reverse('profiles:edit', kwargs={'email': user.email}), data)
        assert response.status_code == 302  # Redirect after success
        
        # Verify changes
        user.profile.refresh_from_db()
        assert user.profile.first_name == 'John'
        assert user.profile.last_name == 'Doe'
        
    def test_profile_edit_view_non_owner(self, client):
        owner = self.create_test_user('owner@example.com', 'testpass123')
        non_owner = self.create_test_user('other@example.com', 'testpass123')
        
        client.force_login(non_owner)
        response = client.get(reverse('profiles:edit', kwargs={'email': owner.email}))
        assert response.status_code == 302  # Redirect to profile detail
        
    def test_profile_detail_view_with_private_events(self, client):
        owner = self.create_test_user('owner@example.com', 'testpass123')
        
        # Create a public event
        public_event = Event.objects.create(
            user=owner,
            title='Public Event',
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=1),
            is_public=True
        )
        
        # Create a private event
        private_event = Event.objects.create(
            user=owner,
            title='Private Event',
            start_time=timezone.now() + timezone.timedelta(days=2),
            end_time=timezone.now() + timezone.timedelta(days=2, hours=1),
            is_public=False
        )
        
        # Test as owner
        client.force_login(owner)
        response = client.get(reverse('profiles:detail', kwargs={'email': owner.email}))
        assert response.status_code == 200
        assert len(response.context['events']) == 2
        assert public_event in response.context['events']
        assert private_event in response.context['events']
        
    def test_profile_calendar_view(self, client):
        owner = self.create_test_user('owner@example.com', 'testpass123')
        viewer = self.create_test_user('viewer@example.com', 'testpass123')
        
        # Create some events
        event1 = Event.objects.create(
            user=owner,
            title='Event 1',
            start_time=timezone.now(),
            end_time=timezone.now() + timezone.timedelta(hours=1)
        )
        event2 = Event.objects.create(
            user=owner,
            title='Event 2',
            start_time=timezone.now() + timezone.timedelta(days=1),
            end_time=timezone.now() + timezone.timedelta(days=1, hours=1)
        )
        
        # Test as owner
        client.force_login(owner)
        response = client.get(reverse('profiles:calendar', kwargs={'email': owner.email}))
        assert response.status_code == 200
        assert len(response.context['events']) == 2
        assert event1 in response.context['events']
        assert event2 in response.context['events']
        
        # Test as viewer with private calendar
        owner.profile.calendar_public = False
        owner.profile.save()
        client.force_login(viewer)
        response = client.get(reverse('profiles:calendar', kwargs={'email': owner.email}))
        assert response.status_code == 302  # Should redirect to profile detail
        
        # Test as viewer with public calendar
        owner.profile.calendar_public = True
        owner.profile.save()
        response = client.get(reverse('profiles:calendar', kwargs={'email': owner.email}))
        assert response.status_code == 200
        assert len(response.context['events']) == 2 