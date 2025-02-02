from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_added
from allauth.socialaccount.models import SocialAccount

@receiver(social_account_added)
def handle_social_account_added(request, sociallogin, **kwargs):
    """
    Signal handler for when a social account is connected.
    Updates the user's profile based on the connected account.
    """
    if sociallogin.account.provider == 'google':
        # Check if calendar scope is in the token scopes
        token = sociallogin.token
        if 'https://www.googleapis.com/auth/calendar' in token.scope:
            profile = sociallogin.user.profile
            profile.google_calendar_connected = True
            profile.save()
