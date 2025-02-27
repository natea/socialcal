from django.dispatch import receiver
from allauth.socialaccount.signals import social_account_added
from allauth.socialaccount.models import SocialToken
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()

@receiver(social_account_added)
def handle_social_account_added(request, sociallogin, **kwargs):
    """Handle when a social account is added to a user."""
    user = sociallogin.user
    social_account = sociallogin.account
    
    # Get or create the user's profile
    profile, created = Profile.objects.get_or_create(user=user)
    
    # For Google accounts, check if we have calendar access
    if social_account.provider == 'google':
        # Get the scopes from the OAuth response
        oauth_scopes = request.GET.get('scope', '').split()
        has_calendar_access = any(
            scope in oauth_scopes 
            for scope in [
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/calendar.events'
            ]
        )
        
        if has_calendar_access:
            # Update both calendar access flags
            profile.has_google_calendar_access = True
            profile.google_calendar_connected = True
            profile.save()
