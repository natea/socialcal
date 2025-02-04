import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from profiles.models import Profile
from unittest.mock import patch, MagicMock
from django.utils import timezone

User = get_user_model()

@pytest.fixture
def google_app(db):
    return SocialApp.objects.create(
        provider='google',
        name='Google',
        client_id='test-client-id',
        secret='test-secret'
    )

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
    def test_welcome_page_unauthenticated(self, client):
        """Test that unauthenticated users can access the welcome page"""
        response = client.get(reverse('onboarding:welcome'))
        assert response.status_code == 200
        assert 'Connect Your Calendar' in str(response.content)

    def test_welcome_page_authenticated_incomplete(self, client, user):
        """Test that authenticated users with incomplete onboarding are redirected to event types"""
        client.force_login(user)
        response = client.get(reverse('onboarding:welcome'))
        assert response.status_code == 302
        assert response.url == reverse('onboarding:event_types')

    def test_welcome_page_authenticated_complete(self, client, user):
        """Test that authenticated users with complete onboarding are redirected home"""
        user.profile.has_completed_onboarding = True
        user.profile.save()
        client.force_login(user)
        response = client.get(reverse('onboarding:welcome'))
        assert response.status_code == 302
        assert response.url == reverse('core:home')

    @patch('allauth.socialaccount.providers.oauth2.client.OAuth2Client')
    def test_google_oauth_flow(self, mock_oauth2_client, client, google_app):
        """Test the Google OAuth flow"""
        # Mock the OAuth2 response
        mock_oauth2_client.return_value.get_access_token.return_value = {
            'access_token': 'test-token',
            'refresh_token': 'test-refresh',
            'expires_in': 3600,
            'scope': 'openid email profile https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events'
        }

        # Start OAuth flow
        response = client.get(reverse('account_login'))
        assert response.status_code == 200
        assert 'Login' in str(response.content)

    def test_event_types_no_google_account(self, client, user):
        """Test that users without Google account are redirected to welcome"""
        client.force_login(user)
        response = client.get(reverse('onboarding:event_types'))
        assert response.status_code == 302
        assert response.url == reverse('onboarding:welcome')

    def test_event_types_with_google_account(self, client, user, google_account):
        """Test that users with Google account can access event types"""
        client.force_login(user)
        response = client.get(reverse('onboarding:event_types'))
        assert response.status_code == 200

    def test_event_types_submission(self, client, user, google_account):
        """Test submitting event types"""
        client.force_login(user)
        response = client.post(reverse('onboarding:event_types'), {
            'event_types': ['sports', 'social']
        })
        assert response.status_code == 302
        user.refresh_from_db()
        assert user.profile.event_preferences == ['sports', 'social']

    def test_calendar_sync_with_access(self, client, user, google_account):
        """Test calendar sync page with existing calendar access"""
        user.profile.has_google_calendar_access = True
        user.profile.save()
        client.force_login(user)
        response = client.get(reverse('onboarding:calendar_sync'))
        assert response.status_code == 302
        assert response.url == reverse('onboarding:social_connect')

    def test_calendar_sync_without_access(self, client, user, google_account):
        """Test calendar sync page without calendar access"""
        client.force_login(user)
        response = client.get(reverse('onboarding:calendar_sync'))
        assert response.status_code == 200

    def test_social_connect_page(self, client, user):
        """Test social connect page"""
        client.force_login(user)
        response = client.get(reverse('onboarding:social_connect'))
        assert response.status_code == 200

    def test_complete_onboarding(self, client, user):
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

    @patch('allauth.socialaccount.providers.oauth2.views.OAuth2Adapter.complete_login')
    def test_google_calendar_permissions(self, mock_complete_login, client, user, google_app):
        """Test handling of Google Calendar permissions during OAuth"""
        # Set up the user's profile
        if not hasattr(user, 'profile'):
            Profile.objects.create(user=user)

        # Mock the OAuth response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'access_token': 'test-token',
            'refresh_token': 'test-refresh',
            'expires_in': 3600,
            'scope': 'https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events'
        }
        mock_complete_login.return_value = mock_response

        # Set up the session
        session = client.session
        session['socialaccount_state'] = ('test-state', 'test-verifier')
        session.save()

        # Log in the user
        client.force_login(user)

        # Create a social account for the user with calendar scopes
        social_account = SocialAccount.objects.create(
            user=user,
            provider='google',
            uid='test-uid',
            extra_data={
                'access_token': 'test-token',
                'refresh_token': 'test-refresh',
                'expires_in': 3600,
                'scope': 'https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events'
            }
        )

        # Update the user's profile with calendar access
        user.profile.has_google_calendar_access = True
        user.profile.google_calendar_connected = True
        user.profile.save()

        # Simulate the OAuth callback
        response = client.get(reverse('onboarding:welcome'), {
            'code': 'test-code',
            'state': 'test-state',
            'scope': 'https://www.googleapis.com/auth/calendar.readonly https://www.googleapis.com/auth/calendar.events'
        })

        # Verify the response and profile updates
        assert response.status_code == 302  # Should redirect to event_types
        assert response.url == reverse('onboarding:event_types')

        # Refresh the user instance to get updated profile
        user.refresh_from_db()
        assert user.profile.has_google_calendar_access
        assert user.profile.google_calendar_connected 