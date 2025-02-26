import os
import sys
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

def get_env_variable(var_name):
    """Get the environment variable or return exception."""
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = f"Set the {var_name} environment variable"
        raise ImproperlyConfigured(error_msg)

BASE_DIR = Path(__file__).resolve().parent.parent

# Determine if we're running tests
TESTING = 'test' in sys.argv

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('DJANGOSECRET_KEY', 'django-insecure-replace-with-your-secret-key')

# SECURITY WARNING: don't run with debug turned on in production!
# Set DEBUG to False when running on Render
DEBUG = 'RENDER' not in os.environ

# Configure allowed hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Add the Render external hostname to allowed hosts
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)

# Add custom domains to allowed hosts
ALLOWED_HOSTS.extend(['socialcal.io', 'www.socialcal.io'])

# Add any additional domains from environment variable if set
additional_hosts = os.environ.get('ADDITIONAL_ALLOWED_HOSTS', '')
if additional_hosts:
    ALLOWED_HOSTS.extend(additional_hosts.split(','))

# Modify installed apps based on whether we're testing
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
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

# Only add debug_toolbar if we're not testing and DEBUG is True
if not TESTING and DEBUG:
    INSTALLED_APPS += ['debug_toolbar']

# Local apps
INSTALLED_APPS += [
    'core.apps.CoreConfig',
    'calendar_app.apps.CalendarAppConfig',
    'events.apps.EventsConfig',
    'profiles.apps.ProfilesConfig',
    'api.apps.ApiConfig',
]

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

ROOT_URLCONF = 'socialcal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'socialcal.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/New_York'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Sites Framework
SITE_ID = 1

# Authentication Settings
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False

# Social Account Settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
            'https://www.googleapis.com/auth/calendar'
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.resend.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'resend'
EMAIL_HOST_PASSWORD = get_env_variable('RESEND_API_KEY')
DEFAULT_FROM_EMAIL = get_env_variable('RESEND_FROM_EMAIL')

# django-allauth settings
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_EMAIL_SUBJECT_PREFIX = 'SocialCal - '
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_LOGOUT_REDIRECT_URL = 'core:home'
ACCOUNT_PRESERVE_USERNAME_CASING = False
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

# Login/Logout settings
LOGIN_REDIRECT_URL = 'core:home'
LOGOUT_REDIRECT_URL = 'core:home'
LOGIN_URL = 'account_login'

# API Keys
SIMPLESCRAPER_API_KEY = get_env_variable('SIMPLESCRAPER_API_KEY')
FIRECRAWL_API_KEY = get_env_variable('FIRECRAWL_API_KEY')
GROQ_API_KEY = get_env_variable('GROQ_API_KEY')

# Redis Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Debug Toolbar Configuration
DEBUG_TOOLBAR_CONFIG = {
    'IS_RUNNING_TESTS': True,  # Allow debug toolbar to work with tests
}

# Spotify API Configuration
SPOTIFY_CLIENT_ID = get_env_variable('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = get_env_variable('SPOTIFY_CLIENT_SECRET')
