from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
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
