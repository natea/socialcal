import dj_database_url
from .base import *
import os

# SECURITY WARNING: keep the secret key used in production secret!
try:
    SECRET_KEY = get_env_variable('DJANGO_SECRET_KEY')
except ImproperlyConfigured:
    if os.environ.get('COLLECTING_STATIC') == 'true':
        SECRET_KEY = 'django-insecure-build-key-for-collectstatic-only'
    else:
        raise

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['socialcal.onrender.com', '.onrender.com']

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
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

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
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', '')
OLOSTEP_API_KEY = os.environ.get('OLOSTEP_API_KEY', '')

# Redis Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': os.environ.get('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PARSER_CLASS': 'redis.connection.HiredisParser',
            'SOCKET_CONNECT_TIMEOUT': 5,
            'SOCKET_TIMEOUT': 5,
            'RETRY_ON_TIMEOUT': True,
        }
    }
}