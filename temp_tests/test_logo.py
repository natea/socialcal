import pytest
from django.urls import reverse
from django.conf import settings

@pytest.mark.django_db
class TestLogo:
    def test_logo_in_header(self, client):
        """Test that the logo is included in the header"""
        response = client.get(reverse('core:privacy'))
        content = response.content.decode('utf-8')
        
        # Check if the logo image tag is in the response
        assert '<img src="/static/images/logo.png"' in content
        assert 'alt="SocialCal Logo"' in content 