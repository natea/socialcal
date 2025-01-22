from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-replace-with-your-secret-key'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email Configuration for Development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# API Keys
SIMPLESCRAPER_API_KEY = get_env_variable('SIMPLESCRAPER_API_KEY')
FIRECRAWL_API_KEY = get_env_variable('FIRECRAWL_API_KEY')
GROQ_API_KEY = get_env_variable('GROQ_API_KEY') 