import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from profiles.forms import ProfileForm
from profiles.models import Profile
from accounts.adapters import EmailAccountAdapter

User = get_user_model()

@pytest.mark.django_db
class TestProfileForm:
    def create_test_user(self, email, password):
        user = User.objects.create_user(username=email.split('@')[0], email=email, password=password)
        adapter = EmailAccountAdapter()
        adapter.populate_username(None, user)
        user.save()
        return user
        
    def test_valid_form(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'bio': 'Test bio',
            'location': 'Test City',
            'calendar_public': True
        }
        form = ProfileForm(data=form_data, instance=user.profile)
        assert form.is_valid()
        
    def test_blank_data(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        form = ProfileForm(data={}, instance=user.profile)
        assert form.is_valid()  # All fields are optional
        
    def test_form_widgets(self):
        form = ProfileForm()
        assert form.fields['birth_date'].widget.input_type == 'date'
        assert form.fields['bio'].widget.attrs['rows'] == 4
        assert 'placeholder' in form.fields['first_name'].widget.attrs
        assert 'placeholder' in form.fields['last_name'].widget.attrs
        
    def test_form_save(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'bio': 'Test bio',
            'location': 'Test City',
            'calendar_public': True
        }
        form = ProfileForm(data=form_data, instance=user.profile)
        profile = form.save()
        
        assert profile.first_name == 'John'
        assert profile.last_name == 'Doe'
        assert profile.bio == 'Test bio'
        assert profile.location == 'Test City'
        assert profile.calendar_public is True 