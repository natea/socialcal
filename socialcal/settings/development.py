from .base import *
import os

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-replace-with-your-secret-key'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Django Debug Toolbar Configuration
INTERNAL_IPS = [
    '127.0.0.1',
]

INSTALLED_APPS += [
    'debug_toolbar',
]

MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE

# Configure Debug Toolbar
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: True,
}

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email Configuration for Development
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.resend.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'resend'
EMAIL_HOST_PASSWORD = os.environ.get('RESEND_API_KEY')
DEFAULT_FROM_EMAIL = os.environ.get('RESEND_FROM_EMAIL')

# API Keys - Make them optional in development
SIMPLESCRAPER_API_KEY = os.environ.get('SIMPLESCRAPER_API_KEY', '')
FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY', '')
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '') 