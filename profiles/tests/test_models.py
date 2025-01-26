import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from profiles.models import Profile
from accounts.adapters import EmailAccountAdapter

User = get_user_model()

@pytest.mark.django_db
class TestProfileModel:
    def create_test_user(self, email, password):
        user = User.objects.create_user(username=email.split('@')[0], email=email, password=password)
        adapter = EmailAccountAdapter()
        adapter.populate_username(None, user)
        user.save()
        return user
        
    def test_profile_creation(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        assert Profile.objects.filter(user=user).exists()
        
    def test_profile_str_with_name(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        profile = user.profile
        profile.first_name = 'John'
        profile.last_name = 'Doe'
        profile.save()
        assert str(profile) == "John Doe's profile"
        
    def test_profile_str_without_name(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        profile = user.profile
        assert str(profile) == "test@example.com's profile"
        
    def test_get_full_name_with_both_names(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        profile = user.profile
        profile.first_name = 'John'
        profile.last_name = 'Doe'
        profile.save()
        assert profile.get_full_name() == 'John Doe'
        
    def test_get_full_name_with_first_name_only(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        profile = user.profile
        profile.first_name = 'John'
        profile.save()
        assert profile.get_full_name() == 'John'
        
    def test_get_full_name_without_names(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        profile = user.profile
        assert profile.get_full_name() == 'test@example.com'
        
    def test_profile_fields(self):
        user = self.create_test_user('test@example.com', 'testpass123')
        profile = user.profile
        profile.first_name = 'John'
        profile.last_name = 'Doe'
        profile.bio = 'Test bio'
        profile.location = 'Test City'
        profile.calendar_public = True
        profile.save()
        
        fetched_profile = Profile.objects.get(user=user)
        assert fetched_profile.first_name == 'John'
        assert fetched_profile.last_name == 'Doe'
        assert fetched_profile.bio == 'Test bio'
        assert fetched_profile.location == 'Test City'
        assert fetched_profile.calendar_public is True

    def test_profile_signal_no_profile_attr(self):
        # Test the case where user doesn't have a profile attribute
        user = self.create_test_user('test@example.com', 'testpass123')
        # Delete the profile but keep the user
        user.profile.delete()
        # Force refresh from db to clear cached properties
        user.refresh_from_db()
        # This should create a new profile
        user.save()
        assert hasattr(user, 'profile')
        assert Profile.objects.filter(user=user).exists()
    
    def test_profile_signal_profile_does_not_exist(self):
        # Test the case where Profile.DoesNotExist is raised
        user = self.create_test_user('test@example.com', 'testpass123')
        # Delete the profile but keep the reference
        Profile.objects.filter(user=user).delete()
        # Clear the profile cache
        if hasattr(user, '_profile_cache'):
            delattr(user, '_profile_cache')
        # This should trigger Profile.DoesNotExist and create a new profile
        user.save()
        assert Profile.objects.filter(user=user).exists() 