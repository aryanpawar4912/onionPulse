# onion_forecast/settings.py - PRODUCTION READY VERSION
import os
from pathlib import Path
import dj_database_url  # Import this to handle Render PostgreSQL

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- ENVIRONMENT CONFIGURATION ---
SECRET_KEY = os.environ.get('KEY', 'your-fallback-dev-key-if-needed')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Parse comma-separated hosts from environment, or default to Render wildcard
ALLOWED_HOSTS = os.environ.get('HOSTS', '.render.com').split(',')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',  # WhiteNoise goes right above staticfiles
    'django.contrib.staticfiles',
    'forecast_app',
    'custom_admin',  
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # WhiteNoise goes right here
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'onion_forecast.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'forecast_app/templates'),
            os.path.join(BASE_DIR, 'custom_admin/templates'),  
        ],
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

WSGI_APPLICATION = 'onion_forecast.wsgi.application'

# --- DATABASE SETUP (Render PostgreSQL) ---
# It automatically reads the DATABASE_URL provided by Render's PostgreSQL instance.
# If it can't find it (like on your local PC), it safely falls back to local SQLite.
DATABASES = {
    'default': dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600
    )
}

# Password validation (disabled for development/quick launch)
AUTH_PASSWORD_VALIDATORS = []

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# --- STATIC & MEDIA FILES HANDLING ---
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'forecast_app/static'),
    os.path.join(BASE_DIR, 'custom_admin/static'),  
]

# Production static file storage optimizing compression
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Authentication URLs
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# --- EMAIL CONFIGURATION ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'onionpulse88@gmail.com'
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD')  
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER

# Security settings (Keep lenient for now, can harden later)
SECURE_BROWSER_XSS_FILTER = False
SECURE_CONTENT_TYPE_NOSNIFF = False
X_FRAME_OPTIONS = 'SAMEORIGIN'

# --- LOGGING (Fixed for Render's Read-Only Container Filesystem) ---
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'forecast_app': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'custom_admin': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Onion Pulse AI App Custom Settings
ONION_FORECAST_SETTINGS = {
    'DEFAULT_MARKET': 'Nashik',
    'PRICE_RANGE_DAYS': 30,
    'PREDICTION_DAYS': 7,
    'CURRENCY': 'INR',
    'DEFAULT_VARIETY': 'Regular',
}