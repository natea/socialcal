import dj_database_url
from .base import *
import os
import logging

# SECURITY WARNING: keep the secret key used in production secret!
try:
    SECRET_KEY = get_env_variable('DJANGO_SECRET_KEY')
except ImproperlyConfigured:
    if os.environ.get('COLLECTING_STATIC') == 'true':
        SECRET_KEY = 'django-insecure-build-key-for-collectstatic-only'
    else:
        raise

# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG to False when running on Render as recommended
DEBUG = False  # Always False in production

# Configure allowed hosts according to Render's recommendations
ALLOWED_HOSTS = []
# Add the Render external hostname to allowed hosts
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Add custom domains to allowed hosts
ALLOWED_HOSTS.extend(['socialcal.io', 'www.socialcal.io', 'socialcal.onrender.com'])

# Database configuration
DATABASES = {
    'default': dj_database_url.config(
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Security Settings
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Static files configuration
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
# Change to use the simpler storage that doesn't hash filenames
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = True

# Make sure the directory exists and is accessible
STATICFILES_DIRS = []
if (BASE_DIR / 'static').exists():
    STATICFILES_DIRS.append(BASE_DIR / 'static')

STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# WhiteNoise Configuration
WHITENOISE_ROOT = STATIC_ROOT

# Sites framework
SITE_ID = 1

# Email Configuration - Make it optional
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Default to console backend

# Only configure email if RESEND_API_KEY is available
if 'RESEND_API_KEY' in os.environ and 'RESEND_FROM_EMAIL' in os.environ:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.resend.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'resend'
    EMAIL_HOST_PASSWORD = os.environ['RESEND_API_KEY']
    DEFAULT_FROM_EMAIL = os.environ['RESEND_FROM_EMAIL']

# API Keys - Make them optional
SIMPLESCRAPER_API_KEY = os.environ.get('SIMPLESCRAPER_API_KEY', '')
FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
OLOSTEP_API_KEY = os.environ.get('OLOSTEP_API_KEY', '')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# make a small change to trigger a build

# Spotify API Configuration
SPOTIFY_CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET')

# OpenAI Configuration
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger = logging.getLogger(__name__)
    logger.warning('OPENAI_API_KEY environment variable is not set. Event extraction will use basic mode.')

# Redis Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
        }
    }
}

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Application definition
INSTALLED_APPS = [
    # Django built-in apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Third party apps
    'rest_framework',
    'widget_tweaks',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    
    # Local apps
    'core.apps.CoreConfig',
    'events.apps.EventsConfig',
    'profiles.apps.ProfilesConfig',
]

# Middleware configuration - ensure WhiteNoise is properly positioned
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Make sure this is right after SecurityMiddleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]