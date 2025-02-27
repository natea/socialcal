import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from django.contrib.sites.models import Site
from profiles.models import Profile
from unittest.mock import patch, MagicMock
from django.utils import timezone
from freezegun import freeze_time

User = get_user_model()

@pytest.fixture
def google_app(db):
    app = SocialApp.objects.create(
        provider='google',
        name='Google',
        client_id='test-client-id',
        secret='test-secret'
    )
    site = Site.objects.get_current()
    app.sites.add(site)
    return app

@pytest.fixture
def user(db):
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def google_account(db, user, google_app):
    account = SocialAccount.objects.create(
        user=user,
        provider='google',
        uid='test-uid',
        extra_data={
            'email': 'test@example.com',
            'given_name': 'Test',
            'family_name': 'User',
            'picture': 'http://example.com/picture.jpg'
        }
    )
    SocialToken.objects.create(
        app=google_app,
        account=account,
        token='test-token',
        token_secret='test-token-secret'
    )
    return account

@pytest.mark.django_db
class TestOnboardingFlow:
    @pytest.fixture(autouse=True)
    def setup_time(self):
        """Set up a fixed time for all tests in this class."""
        with freeze_time("2025-02-08 12:00:00"):
            yield

    def test_welcome_page_unauthenticated(self, client, google_app):
        """Test that unauthenticated users can access the welcome page"""
        response = client.get(reverse('onboarding:welcome'))
        assert response.status_code == 200
        assert 'Welcome to SocialCal' in response.content.decode()

    def test_welcome_page_authenticated_incomplete(self, client, user, google_app):
        """Test that authenticated users with incomplete onboarding see the welcome page"""
        client.force_login(user)
        response = client.get(reverse('onboarding:welcome'))
        assert response.status_code == 200
        assert 'Welcome to SocialCal' in response.content.decode()

    def test_welcome_page_authenticated_complete(self, client, user, google_app):
        """Test that authenticated users with complete onboarding are redirected"""
        user.profile.has_completed_onboarding = True
        user.profile.save()
        client.force_login(user)
        response = client.get(reverse('onboarding:welcome'))
        assert response.status_code == 302
        assert response.url == reverse('calendar:index')

    def test_google_oauth_flow(self, client, user, google_app):
        """Test the Google OAuth flow"""
        client.force_login(user)
        response = client.get(reverse('onboarding:google_oauth'))
        assert response.status_code == 302
        assert 'accounts/google/login' in response.url

    def test_event_types_no_google_account(self, client, user, google_app):
        """Test event types page without Google account"""
        client.force_login(user)
        response = client.get(reverse('onboarding:event_types'))
        assert response.status_code == 200
        assert 'Connect Google Calendar' in response.content.decode()

    def test_event_types_with_google_account(self, client, user, google_app):
        """Test event types page with Google account"""
        client.force_login(user)
        # Create Google account for the user
        account = SocialAccount.objects.create(
            user=user,
            provider='google',
            uid='test-uid',
            extra_data={
                'email': 'test@example.com',
                'given_name': 'Test',
                'family_name': 'User',
                'picture': 'http://example.com/picture.jpg'
            }
        )
        SocialToken.objects.create(
            app=google_app,
            account=account,
            token='test-token',
            token_secret='test-token-secret'
        )
        response = client.get(reverse('onboarding:event_types'))
        assert response.status_code == 200
        assert 'Select Event Types' in response.content.decode()

    def test_event_types_submission(self, client, user, google_app):
        """Test submitting event types"""
        client.force_login(user)
        # Create Google account for the user
        account = SocialAccount.objects.create(
            user=user,
            provider='google',
            uid='test-uid',
            extra_data={
                'email': 'test@example.com',
                'given_name': 'Test',
                'family_name': 'User',
                'picture': 'http://example.com/picture.jpg'
            }
        )
        SocialToken.objects.create(
            app=google_app,
            account=account,
            token='test-token',
            token_secret='test-token-secret'
        )
        response = client.post(reverse('onboarding:event_types'), {
            'event_types': ['music', 'sports', 'tech'],
        })
        assert response.status_code == 302
        assert response.url == reverse('onboarding:calendar_sync')

    def test_calendar_sync_with_access(self, client, user, google_app):
        """Test calendar sync page with Google Calendar access"""
        client.force_login(user)
        # Create Google account for the user with calendar access
        account = SocialAccount.objects.create(
            user=user,
            provider='google',
            uid='test-uid',
            extra_data={
                'email': 'test@example.com',
                'given_name': 'Test',
                'family_name': 'User',
                'picture': 'http://example.com/picture.jpg',
                'scope': 'https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events'
            }
        )
        SocialToken.objects.create(
            app=google_app,
            account=account,
            token='test-token',
            token_secret='test-token-secret'
        )
        # Set calendar access flag
        user.profile.has_google_calendar_access = True
        user.profile.save()
        
        response = client.get(reverse('onboarding:calendar_sync'))
        assert response.status_code == 200
        assert 'Sync Your Calendar' in response.content.decode()

    def test_calendar_sync_without_access(self, client, user, google_app):
        """Test calendar sync page without Google Calendar access"""
        client.force_login(user)
        response = client.get(reverse('onboarding:calendar_sync'))
        assert response.status_code == 200
        assert 'Grant Calendar Access' in response.content.decode()

    def test_social_connect_page(self, client, user, google_app):
        """Test social connect page"""
        client.force_login(user)
        response = client.get(reverse('onboarding:social_connect'))
        assert response.status_code == 200
        assert 'Connect Your Social Accounts' in response.content.decode()

    def test_complete_onboarding(self, client, user, google_app):
        """Test completing the onboarding process"""
        client.force_login(user)
        response = client.get(reverse('onboarding:complete'))
        assert response.status_code == 302  # Expect redirect instead of 200

        # Verify the user's profile is updated
        user.refresh_from_db()
        assert user.profile.has_completed_onboarding

        # Verify redirect to calendar week view
        today = timezone.now()
        expected_url = reverse('calendar:week', kwargs={
            'year': today.year,
            'month': today.month,
            'day': today.day
        })
        assert response.url == expected_url

    def test_google_calendar_permissions(self, client, user, google_app):
        """Test Google Calendar permissions page"""
        client.force_login(user)
        response = client.get(reverse('onboarding:google_calendar_permissions'))
        assert response.status_code == 200
        assert 'Grant Calendar Access' in response.content.decode() 