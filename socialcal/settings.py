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

SECRET_KEY = 'django-insecure-replace-with-your-secret-key'

DEBUG = True

ALLOWED_HOSTS = []

# Modify installed apps based on whether we're testing
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
]

if 'test' not in sys.argv:
    INSTALLED_APPS.append('debug_toolbar')

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
        'DIRS': [
            BASE_DIR / 'templates',
            BASE_DIR / 'allauth/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
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

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication Backends
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Sites Framework
SITE_ID = 1

# Login/Logout URLs
LOGIN_URL = 'onboarding:welcome'
LOGIN_REDIRECT_URL = 'onboarding:event_types'
LOGOUT_REDIRECT_URL = 'onboarding:welcome'

# Email Configuration for Development
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.resend.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = 'resend'
    EMAIL_HOST_PASSWORD = get_env_variable('RESEND_API_KEY')
    DEFAULT_FROM_EMAIL = get_env_variable('RESEND_FROM_EMAIL')

# django-allauth settings
ACCOUNT_EMAIL_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_CONFIRM_EMAIL_ON_GET = False
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = False
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGOUT_ON_GET = False
ACCOUNT_LOGOUT_REDIRECT_URL = 'onboarding:welcome'
ACCOUNT_LOGIN_ATTEMPTS_LIMIT = None
ACCOUNT_MAX_EMAIL_ADDRESSES = 1

# Provider specific settings
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_STORE_TOKENS = True
SOCIALACCOUNT_EMAIL_VERIFICATION = False
SOCIALACCOUNT_EMAIL_REQUIRED = False
SOCIALACCOUNT_ADAPTER = 'socialcal.adapters.CustomSocialAccountAdapter'

# Disable email verification completely
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http'
ACCOUNT_EMAIL_CONFIRMATION_HMAC = False
ACCOUNT_EMAIL_CONFIRMATION_COOLDOWN = 0
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 0
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True

# API Keys
SIMPLESCRAPER_API_KEY = get_env_variable('SIMPLESCRAPER_API_KEY')
FIRECRAWL_API_KEY = get_env_variable('FIRECRAWL_API_KEY')
GROQ_API_KEY = get_env_variable('GROQ_API_KEY')
SPOTIFY_CLIENT_ID = get_env_variable('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = get_env_variable('SPOTIFY_CLIENT_SECRET')

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
    'IS_RUNNING_TESTS': True,
    'SHOW_TOOLBAR_CALLBACK': lambda request: (
        not request.headers.get('x-requested-with') == 'XMLHttpRequest' and
        request.META.get('REMOTE_ADDR', None) in ['127.0.0.1', '::1'] and
        DEBUG
    ),
}

DEBUG_TOOLBAR_PANELS = [
    'debug_toolbar.panels.versions.VersionsPanel',
    'debug_toolbar.panels.timer.TimerPanel',
    'debug_toolbar.panels.settings.SettingsPanel',
    'debug_toolbar.panels.headers.HeadersPanel',
    'debug_toolbar.panels.request.RequestPanel',
    'debug_toolbar.panels.sql.SQLPanel',
    'debug_toolbar.panels.staticfiles.StaticFilesPanel',
    'debug_toolbar.panels.templates.TemplatesPanel',
    'debug_toolbar.panels.cache.CachePanel',
    'debug_toolbar.panels.signals.SignalsPanel',
    'debug_toolbar.panels.logging.LoggingPanel',
    'debug_toolbar.panels.redirects.RedirectsPanel',
]  # Note: ProfilingPanel is intentionally omitted to avoid conflicts

# Social Account Settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'openid',
            'profile',
            'email',
            'https://www.googleapis.com/auth/calendar.readonly',
            'https://www.googleapis.com/auth/calendar.events'
        ],
        'AUTH_PARAMS': {
            'access_type': 'offline',
            'prompt': 'consent',
        },
        'OAUTH_PKCE_ENABLED': True,
        'VERIFIED_EMAIL': True
    }
}
