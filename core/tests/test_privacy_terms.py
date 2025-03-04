import pytest
from django.urls import reverse

@pytest.mark.django_db
class TestPrivacyTermsViews:
    def test_privacy_view(self, client):
        """Test that the privacy policy page loads correctly"""
        response = client.get(reverse('core:privacy'))
        assert response.status_code == 200
        assert 'Privacy Policy' in str(response.content)

    def test_terms_of_service_view(self, client):
        """Test that the terms of service page loads correctly"""
        response = client.get(reverse('core:terms_of_service'))
        assert response.status_code == 200
        assert 'Terms of Service' in str(response.content) 