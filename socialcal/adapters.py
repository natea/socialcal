from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from allauth.account.utils import user_email, user_field, user_username
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_connect_redirect_url(self, request, socialaccount):
        """
        Returns the URL to redirect to after a successful connection.
        """
        next_url = request.GET.get('next') or settings.LOGIN_REDIRECT_URL
        return next_url

    def is_auto_signup_allowed(self, request, sociallogin):
        """
        Enables auto-signup for social accounts.
        """
        return True

    def populate_user(self, request, sociallogin, data):
        """
        Populates user information from social account data.
        """
        user = sociallogin.user
        if not user.email:
            user.email = data.get('email', '')
        if not user.username:
            email_base = user.email.split('@')[0]
            user.username = f"{email_base}_{uuid.uuid4().hex[:8]}"
        return user

    def is_email_verified(self, request, email):
        """
        Skip email verification for social accounts.
        """
        return True

    def save_user(self, request, sociallogin, form=None):
        """
        Save the user and mark their email as verified.
        """
        user = super().save_user(request, sociallogin, form)
        user.emailaddress_set.update(verified=True)
        return user

    def pre_social_login(self, request, sociallogin):
        """
        Invoked just after a user successfully authenticates via a social provider,
        but before the login is actually processed.
        """
        # Get the user's email from the social account
        email = sociallogin.account.extra_data.get('email')
        if not email:
            return

        try:
            # Try to find an existing user with this email
            user = User.objects.get(email=email)
            
            # If we found a user but the social account is not connected
            if not sociallogin.is_existing:
                # Connect the social account to the existing user
                sociallogin.connect(request, user)
                
            # Set the user on the sociallogin
            sociallogin.user = user
            
            # Check for calendar scopes in the OAuth response
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
                user.profile.has_google_calendar_access = True
                user.profile.google_calendar_connected = True
                user.profile.save()
                
            return
            
        except User.DoesNotExist:
            # If no user exists with this email, let the standard signup flow continue
            pass

    def new_user(self, request, sociallogin):
        """
        Called when a new user is created through social login.
        """
        # Create a new user instance
        user = User()
        
        # Get email from the social account
        email = sociallogin.account.extra_data.get('email', '')
        user.email = email
        
        # Generate a username based on email
        if email:
            email_base = email.split('@')[0]
            user.username = f"{email_base}_{uuid.uuid4().hex[:8]}"
        else:
            user.username = f"user_{uuid.uuid4().hex[:8]}"
        
        # Set the user on the sociallogin object
        sociallogin.user = user
            
        return user
