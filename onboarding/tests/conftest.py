import pytest
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

@pytest.fixture
def google_social_app(db):
    """Create a test Google social app."""
    site = Site.objects.get_current()
    app = SocialApp.objects.create(
        provider='google',
        name='Google',
        client_id='test-client-id',
        secret='test-secret',
    )
    app.sites.add(site)
    return app 