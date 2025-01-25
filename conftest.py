import pytest
import os
import django
from django.core.management import call_command
from django.test import Client
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialcal.settings.test')

@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command('migrate')

@pytest.fixture
def client():
    return Client()

@pytest.fixture
def user(db):
    User = get_user_model()
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )

@pytest.fixture
def authenticated_client(client, user):
    client.login(username='testuser', password='testpass123')
    return client
