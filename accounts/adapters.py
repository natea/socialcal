from allauth.account.adapter import DefaultAccountAdapter
from django.contrib.auth import get_user_model
from allauth.account.models import EmailAddress
import uuid
from django.forms import ValidationError

User = get_user_model()

class EmailAccountAdapter(DefaultAccountAdapter):
    def save_user(self, request, user, form, commit=True):
        """
        Called when saving a new user.
        """
        # Check if email already exists
        email = user.email
        if EmailAddress.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user is already registered with this e-mail address.")
        return super().save_user(request, user, form, commit)

    def populate_username(self, request, user):
        """
        Generate a unique username using the first part of the email address
        and a random suffix if needed.
        """
        email = user.email
        email_base = email.split('@')[0]
        
        # Always add a random suffix to ensure uniqueness
        unique_username = f"{email_base}_{uuid.uuid4().hex[:8]}"
        user.username = unique_username 