from .base import *

# Use a faster password hasher for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Use an in-memory database for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Disable debug mode
DEBUG = False

# Disable CSRF for testing
MIDDLEWARE = [m for m in MIDDLEWARE if 'csrf' not in m.lower()]

# Configure email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Configure cache for testing
import logging
logger = logging.getLogger(__name__)

try:
    import django_redis
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': 'redis://127.0.0.1:6379/1',
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'SOCKET_CONNECT_TIMEOUT': 5,
                'SOCKET_TIMEOUT': 5,
                'RETRY_ON_TIMEOUT': True,
                'IGNORE_EXCEPTIONS': True,  # Don't crash if Redis is unavailable
            }
        }
    }
    logger.info("Using Redis cache backend for tests")
except ImportError:
    # Fallback to LocMemCache if django_redis is not available
    logger.warning("django_redis not available, using LocMemCache for tests")
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# Fallback to LocMemCache if Redis is explicitly disabled
if os.environ.get('DISABLE_REDIS_CACHE', 'false').lower() == 'true':
    logger.warning("Redis cache disabled by environment variable, using LocMemCache for tests")
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'unique-snowflake',
        }
    }

# Configure media storage for testing
DEFAULT_FILE_STORAGE = 'django.core.files.storage.InMemoryStorage'

# Disable SSL redirect for testing
SECURE_SSL_REDIRECT = False

# Configure allauth for testing
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': 'test-client-id',
            'secret': 'test-secret',
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events'
        ],
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

# Spotify API credentials for testing
SPOTIFY_CLIENT_ID = 'test_client_id'
SPOTIFY_CLIENT_SECRET = 'test_client_secret'

# Test venue mapping
EVENT_VENUE_MAPPING = {
    'event_venue': 'venue_name',
    'event_venue_address': 'venue_address',
    'event_venue_city': 'venue_city',
    'event_venue_state': 'venue_state',
    'event_venue_zip': 'venue_postal_code',
    'event_venue_country': 'venue_country',
}
