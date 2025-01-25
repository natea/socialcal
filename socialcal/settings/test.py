from .base import *

# Use an in-memory SQLite database for testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Turn off password hashing to speed up tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Turn off debug mode
DEBUG = False

# Make tests faster by using simple password hasher
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

# Use a fast template loader
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    ]),
]

# Explicitly set the timezone for testing
USE_TZ = True
TIME_ZONE = 'America/New_York'

# Test API Keys
SIMPLESCRAPER_API_KEY = 'test_key'
OPENAI_API_KEY = 'test_key'

# Test venue mapping
EVENT_VENUE_MAPPING = {
    'event_venue': 'venue_name',
    'event_venue_address': 'venue_address',
    'event_venue_city': 'venue_city',
    'event_venue_state': 'venue_state',
    'event_venue_zip': 'venue_postal_code',
    'event_venue_country': 'venue_country',
}
