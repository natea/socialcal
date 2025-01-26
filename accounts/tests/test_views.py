from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.contrib.sites.models import Site
from allauth.account.models import EmailAddress

User = get_user_model()

class TestAccountViews(TestCase):
    def setUp(self):
        # Create a site
        self.site = Site.objects.get_current()
        self.site.domain = 'example.com'
        self.site.save()

    def test_signup_view(self):
        url = reverse('account_signup')
        response = self.client.get(url)
        assert response.status_code == 200

        # Test POST with valid data
        data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        response = self.client.post(url, data)
        assert response.status_code == 302  # Redirect after successful signup
        assert User.objects.filter(email='test@example.com').exists()

    def test_login_view(self):
        # Create a user and verify their email
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='testpass123'
        )
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=True
        )

        url = reverse('account_login')
        response = self.client.get(url)
        assert response.status_code == 200

        # Test POST with valid credentials
        data = {
            'login': 'test@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data)
        assert response.status_code == 302  # Redirect after successful login
        assert '_auth_user_id' in self.client.session

    def test_logout_view(self):
        # Create and login a user
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='test', password='testpass123')
        
        # Test logout
        url = reverse('account_logout')
        response = self.client.post(url)
        assert response.status_code == 302  # Redirect after logout
        
        # Verify user is logged out
        response = self.client.get(reverse('profiles:edit', kwargs={'email': user.email}))
        assert response.status_code == 302  # Redirect to login
        
    def test_password_change(self):
        # Create and login a user
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='testpass123'
        )
        self.client.login(username='test', password='testpass123')
        
        url = reverse('account_change_password')
        response = self.client.get(url)
        assert response.status_code == 200
        
        # Test POST with valid data
        data = {
            'oldpassword': 'testpass123',
            'password1': 'newtestpass123',
            'password2': 'newtestpass123'
        }
        response = self.client.post(url, data)
        assert response.status_code == 302  # Redirect after successful change
        
        # Verify password was changed
        assert self.client.login(username='test', password='newtestpass123')
        
    def test_password_reset(self):
        # Create a user
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='testpass123'
        )
        
        url = reverse('account_reset_password')
        response = self.client.get(url)
        assert response.status_code == 200
        
        # Test POST with valid email
        data = {'email': 'test@example.com'}
        response = self.client.post(url, data)
        assert response.status_code == 302  # Redirect after successful submission
        
        # Verify email was sent
        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == ['test@example.com']

    def test_login_with_invalid_credentials(self):
        # Create a user and verify their email
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='testpass123'
        )
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=True
        )
        
        url = reverse('account_login')
        
        # Test with wrong password
        data = {
            'login': 'test@example.com',
            'password': 'wrongpass123'
        }
        response = self.client.post(url, data)
        assert response.status_code == 200
        form = response.context['form']
        assert form.errors['__all__'] == ['The email address and/or password you specified are not correct.']
        
        # Test with non-existent email
        data = {
            'login': 'nonexistent@example.com',
            'password': 'testpass123'
        }
        response = self.client.post(url, data)
        assert response.status_code == 200
        form = response.context['form']
        assert form.errors['__all__'] == ['The email address and/or password you specified are not correct.']
        
    def test_signup_with_invalid_data(self):
        url = reverse('account_signup')
        
        # Test with invalid email
        data = {
            'email': 'invalid-email',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        response = self.client.post(url, data)
        assert response.status_code == 200  # Stay on form with errors
        form = response.context['form']
        assert 'email' in form.errors
        assert form.errors['email'] == ['Enter a valid email address.']
        
        # Test with mismatched passwords
        data = {
            'email': 'test@example.com',
            'password1': 'testpass123',
            'password2': 'differentpass123'
        }
        response = self.client.post(url, data)
        assert response.status_code == 200
        form = response.context['form']
        assert 'password2' in form.errors
        assert form.errors['password2'] == ['You must type the same password each time.']
        
    def test_password_change_with_invalid_data(self):
        # Create a user and verify their email
        user = User.objects.create_user(
            username='test',
            email='test@example.com',
            password='testpass123'
        )
        EmailAddress.objects.create(
            user=user,
            email=user.email,
            primary=True,
            verified=True
        )
        self.client.force_login(user)
        
        url = reverse('account_change_password')
        
        # Test with wrong old password
        data = {
            'oldpassword': 'wrongpass123',
            'password1': 'newtestpass123',
            'password2': 'newtestpass123'
        }
        response = self.client.post(url, data)
        assert response.status_code == 200
        form = response.context['form']
        assert form.errors['oldpassword'] == ['Please type your current password.']
        
        # Test with mismatched new passwords
        data = {
            'oldpassword': 'testpass123',
            'password1': 'newtestpass123',
            'password2': 'differentpass123'
        }
        response = self.client.post(url, data)
        assert response.status_code == 200
        form = response.context['form']
        assert form.errors['password2'] == ['You must type the same password each time.']
        
    def test_password_reset_with_invalid_email(self):
        url = reverse('account_reset_password')
        
        # Test with non-existent email
        data = {'email': 'nonexistent@example.com'}
        response = self.client.post(url, data)
        # django-allauth always redirects and sends an email for security
        assert response.status_code == 302
        assert len(mail.outbox) == 1  # Email is sent even for non-existent addresses 