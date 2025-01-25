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

# Debug settings
DEBUG = False

# Add a test secret key
SECRET_KEY = 'django-insecure-test-key-for-testing-only-do-not-use-in-production'

# Remove debug toolbar from installed apps and middleware
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != 'debug_toolbar']
MIDDLEWARE = [mw for mw in MIDDLEWARE if not mw.startswith('debug_toolbar.')]

# Configure debug toolbar to be disabled in tests
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: False,
    'IS_RUNNING_TESTS': True,  # This tells the debug toolbar that we're running tests
}

# Disable debug toolbar internal IPs
INTERNAL_IPS = []

# Make tests faster by using simple password hasher
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)

# Template settings
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Explicitly set the timezone for testing
USE_TZ = True
TIME_ZONE = 'America/New_York'

# Test API Keys
SIMPLESCRAPER_API_KEY = 'test_key'
OPENAI_API_KEY = 'test_key'
FIRECRAWL_API_KEY = 'test_key'
GROQ_API_KEY = 'test_key'

# Redis Cache Configuration for Testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/2',  # Using DB 2 for testing
    }
}

# Test venue mapping
EVENT_VENUE_MAPPING = {
    'event_venue': 'venue_name',
    'event_venue_address': 'venue_address',
    'event_venue_city': 'venue_city',
    'event_venue_state': 'venue_state',
    'event_venue_zip': 'venue_postal_code',
    'event_venue_country': 'venue_country',
}
