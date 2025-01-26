import pytest
from django.contrib.auth import get_user_model
from accounts.adapters import EmailAccountAdapter

User = get_user_model()

@pytest.mark.django_db
class TestEmailAccountAdapter:
    def test_populate_username_with_available_email_base(self):
        adapter = EmailAccountAdapter()
        user = User(email='test@example.com')
        adapter.populate_username(None, user)
        assert user.username == 'test'
        
    def test_populate_username_with_taken_email_base(self):
        # Create a user with the base username
        User.objects.create_user(username='test', email='test1@example.com')
        
        # Try to create another user with same email base
        adapter = EmailAccountAdapter()
        user = User(email='test@example.com')
        adapter.populate_username(None, user)
        
        # Should generate a unique username with suffix
        assert user.username.startswith('test_')
        assert len(user.username) > 5  # Base + underscore + some random chars
        
    def test_populate_username_with_multiple_conflicts(self):
        # Create users with base username and one variant
        User.objects.create_user(username='test', email='test1@example.com')
        User.objects.create_user(username='test_abc123', email='test2@example.com')
        
        # Try to create another user with same email base
        adapter = EmailAccountAdapter()
        user = User(email='test@example.com')
        adapter.populate_username(None, user)
        
        # Should generate a different unique username
        assert user.username.startswith('test_')
        assert user.username != 'test'
        assert user.username != 'test_abc123' 