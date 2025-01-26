import pytest
from django.contrib.auth import get_user_model
from accounts.adapters import EmailAccountAdapter
from django.test import TestCase
from django.forms import ValidationError
from allauth.account.models import EmailAddress
from django.test.client import RequestFactory

User = get_user_model()

@pytest.mark.django_db
class TestEmailAccountAdapter:
    def test_username_generation_format(self):
        """Test that username is generated with correct format"""
        adapter = EmailAccountAdapter()
        user = User(email='test@example.com')
        adapter.populate_username(None, user)
        # Should generate a username with email base and random suffix
        assert user.username.startswith('test_')
        assert len(user.username) > 5  # Base + underscore + some random chars
        
    def test_unique_username_generation(self):
        """Test that generated usernames are unique"""
        adapter = EmailAccountAdapter()
        
        # Create multiple users with same email base
        user1 = User(email='test@example.com')
        user2 = User(email='test@example.com')
        
        adapter.populate_username(None, user1)
        adapter.populate_username(None, user2)
        
        # Usernames should be different
        assert user1.username != user2.username
        # Both should follow the pattern
        assert user1.username.startswith('test_')
        assert user2.username.startswith('test_')
        assert len(user1.username) > 5
        assert len(user2.username) > 5

class MockForm:
    def __init__(self, email):
        self.cleaned_data = {
            'email': email,
            'password1': 'testpass123',
        }

class EmailAccountAdapterTests(TestCase):
    def setUp(self):
        self.adapter = EmailAccountAdapter()
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        
        # Create an existing user
        self.existing_email = "existing@example.com"
        self.existing_user = User.objects.create_user(
            username="existing",
            email=self.existing_email,
            password="testpass123"
        )
        EmailAddress.objects.create(
            user=self.existing_user,
            email=self.existing_email,
            primary=True,
            verified=True
        )

    def test_prevent_duplicate_email_registration(self):
        """Test that registering with an existing email raises ValidationError"""
        new_user = User(email=self.existing_email)
        form = MockForm(self.existing_email)
        
        with self.assertRaises(ValidationError) as context:
            self.adapter.save_user(self.request, new_user, form)
        
        self.assertEqual(
            str(context.exception), 
            "['A user is already registered with this e-mail address.']"
        )

    def test_allow_new_email_registration(self):
        """Test that registering with a new email proceeds normally"""
        new_email = "new@example.com"
        new_user = User(email=new_email)
        form = MockForm(new_email)
        
        try:
            self.adapter.save_user(self.request, new_user, form)
        except ValidationError:
            self.fail("save_user raised ValidationError unexpectedly!")

    def test_username_generation(self):
        """Test that usernames are generated correctly"""
        # Test username generation
        user = User(email="test@example.com")
        self.adapter.populate_username(self.request, user)
        # Should have email base followed by random suffix
        self.assertRegex(user.username, r"test_[a-f0-9]{8}")
        
        # Test that a second user gets a different username
        user2 = User(email="test@example.com")
        self.adapter.populate_username(self.request, user2)
        self.assertRegex(user2.username, r"test_[a-f0-9]{8}")
        self.assertNotEqual(user.username, user2.username) 