import pytest
import os
import django
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'socialcal.settings.test')

def pytest_configure():
    django.setup()
    call_command('migrate')
