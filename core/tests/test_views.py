import pytest
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def user():
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.mark.django_db
class TestHomeView:
    def test_home_unauthenticated(self, client):
        """Test that unauthenticated users are redirected to onboarding welcome"""
        response = client.get(reverse('core:home'))
        assert response.status_code == 302
        assert response.url == reverse('onboarding:welcome')

    def test_home_authenticated(self, client, user):
        """Test that authenticated users are redirected to calendar week view"""
        client.force_login(user)
        response = client.get(reverse('core:home'))
        assert response.status_code == 302
        
        # Get today's date for comparison
        today = timezone.now()
        expected_url = reverse('calendar:week', kwargs={
            'year': today.year,
            'month': today.month,
            'day': today.day
        })
        assert response.url == expected_url 