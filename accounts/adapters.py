from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class EmailAccountAdapter(DefaultAccountAdapter):
    def populate_username(self, request, user):
        """
        Generate a unique username using the first part of the email address
        and a random suffix if needed.
        """
        email = user.email
        email_base = email.split('@')[0]
        
        # Try using just the email base first
        if not User.objects.filter(username=email_base).exists():
            user.username = email_base
            return

        # If that username is taken, add a random suffix
        while True:
            unique_username = f"{email_base}_{uuid.uuid4().hex[:8]}"
            if not User.objects.filter(username=unique_username).exists():
                user.username = unique_username
                return 