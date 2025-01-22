import dj_database_url
from .base import *

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_env_variable('DJANGO_SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['socialcal.onrender.com', '.onrender.com']  # Update with your domain

# Database
# Use Render PostgreSQL database
DATABASES = {
    'default': dj_database_url.config(
        default=get_env_variable('DATABASE_URL'),
        conn_max_age=600
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

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.resend.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'resend'
EMAIL_HOST_PASSWORD = get_env_variable('RESEND_API_KEY')
DEFAULT_FROM_EMAIL = get_env_variable('RESEND_FROM_EMAIL')

# API Keys
SIMPLESCRAPER_API_KEY = get_env_variable('SIMPLESCRAPER_API_KEY')
FIRECRAWL_API_KEY = get_env_variable('FIRECRAWL_API_KEY')
GROQ_API_KEY = get_env_variable('GROQ_API_KEY') 