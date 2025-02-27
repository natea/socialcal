from pathlib import Path
import os
import logging

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Import all settings from the main settings file
from .settings import *

# Disable Debug for tests
DEBUG = False

# Define base installed apps without debug_toolbar
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'widget_tweaks',
    'core',
    'profiles',
    'events',
    'onboarding',
    'calendar_app',
    'api',
    'accounts',
]

# Use in-memory SQLite database for faster tests
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Use console email backend for tests
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Configure cache for tests
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

# Password hashers - use fast password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Media files
MEDIA_ROOT = BASE_DIR / 'test_media'
MEDIA_URL = '/test_media/'

# Override SECRET_KEY for tests
SECRET_KEY = 'django-insecure-test-key-for-testing-only'

# Use a faster test runner
TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# Template settings
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,  # Let Django find templates in app directories
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

# Use database sessions for tests
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Root URL Configuration
ROOT_URLCONF = 'socialcal.urls'

# Static files
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# Use timezone-aware datetimes
USE_TZ = True

# Override environment variables for testing
SIMPLESCRAPER_API_KEY = 'test-key'
FIRECRAWL_API_KEY = 'test-key'
GROQ_API_KEY = 'test-key'
RESEND_API_KEY = 'test-key'
RESEND_FROM_EMAIL = 'test@example.com'

# Spotify settings for testing
SPOTIFY_CLIENT_ID = 'test_client_id'
SPOTIFY_CLIENT_SECRET = 'test_client_secret'

# Debug Toolbar settings for tests
DEBUG_TOOLBAR_CONFIG = {
    'IS_RUNNING_TESTS': True,
}

# Middleware without debug toolbar
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

# django-allauth settings
SITE_ID = 1
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
ACCOUNT_ADAPTER = 'accounts.adapters.EmailAccountAdapter'

# Login/Logout settings
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'
LOGIN_URL = 'account_login'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]
