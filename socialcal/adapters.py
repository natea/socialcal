from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.conf import settings

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
        user = super().populate_user(request, sociallogin, data)
        user.email = data.get('email', '')
        return user
