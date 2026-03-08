# market_prices/market_prices/settings.py
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# SECURITY SETTINGS - PRODUCTION
# ============================================================================
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY')

# IMPORTANT: Set DEBUG to False in production
DEBUG = False

# Add your PythonAnywhere domain to ALLOWED_HOSTS
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'marketlens.pythonanywhere.com',
    'marketlens-qmum.onrender.com',
]

# Site URL
SITE_URL = os.getenv('SITE_URL', 'https://marketlens-qmum.onrender.com')
SITE_ID = 1

# ============================================================================
# APPLICATION DEFINITION
# ============================================================================
INSTALLED_APPS = [
    # Django core
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Custom apps
    'accounts.apps.AccountsConfig',
    'market',
    'vendor',
    'core',
    'notifications',
    
    # Third-party apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'market_prices.urls'

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
                'notifications.context_processors.notifications_processor',
            ],
        },
    },
]

WSGI_APPLICATION = 'market_prices.wsgi.application'

# ============================================================================
# DATABASE - SQLite for PythonAnywhere
# ============================================================================
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ============================================================================
# AUTHENTICATION
# ============================================================================
AUTHENTICATION_BACKENDS = [
    'accounts.backends.EmailAuthBackend',  # Custom email authentication
    'allauth.account.auth_backends.AuthenticationBackend',
    'django.contrib.auth.backends.ModelBackend',  # Fallback
]

# ============================================================================
# DJANGO-ALLAUTH SETTINGS - UPDATED FOR VERSION 64.2.1
# ============================================================================

# Authentication - use email only (ACCOUNT_LOGIN_METHODS is deprecated)
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_UNIQUE_EMAIL = True

# Signup fields configuration - updated format for 64.2.1
ACCOUNT_SIGNUP_FIELDS = [
    'email*',      # Required
    'password1*',  # Required
    'password2*',  # Required
    'first_name',  # Optional
    'last_name',   # Optional
]

# Email settings
ACCOUNT_EMAIL_VERIFICATION = 'mandatory'
ACCOUNT_EMAIL_SUBJECT_PREFIX = '[MarketLens] '
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_EMAIL_CONFIRMATION_HMAC = True

# Template settings - Use our custom templates
ACCOUNT_TEMPLATE_EXTENSION = 'html'
ACCOUNT_CONFIRM_EMAIL_ON_GET = True

# Email confirmation redirects
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = 'pending_verification'
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = 'pending_verification'

# Login/Logout settings
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_SESSION_REMEMBER = True

# User settings
ACCOUNT_USER_MODEL_USERNAME_FIELD = None

# Password settings
ACCOUNT_PASSWORD_MIN_LENGTH = 8

# Signup redirect
ACCOUNT_SIGNUP_REDIRECT_URL = 'pending_verification'
ACCOUNT_USERNAME_BLACKLIST = []

# Email template mapping
ACCOUNT_EMAIL_CONFIRMATION_HTML = True
ACCOUNT_EMAIL_CONFIRMATION_SUBJECT = 'Confirm Your Email - MarketLens'

# ============================================================================
# SOCIAL ACCOUNT SETTINGS
# ============================================================================
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.CustomSocialAccountAdapter'
ACCOUNT_INACTIVE_URL = 'account_inactive'

# ============================================================================
# PROVIDER SPECIFIC SETTINGS
# ============================================================================
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'EMAIL_AUTHENTICATION': True,
        'VERIFIED_EMAIL': True,
    }
}

# ============================================================================
# REDIRECT URLS
# ============================================================================
LOGIN_REDIRECT_URL = '/dashboard/'
LOGIN_URL = '/accounts/login/'
LOGOUT_REDIRECT_URL = '/'

# ============================================================================
# RATE LIMITING SETTINGS (Allauth)
# ============================================================================
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/5m',
    'signup': '3/1h',
    'confirm_email': '10/5m',
    'reset_password': '5/1h',
}

# ============================================================================
# PASSWORD VALIDATION
# ============================================================================
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

# ============================================================================
# INTERNATIONALIZATION
# ============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = True

# ============================================================================
# STATIC & MEDIA FILES - PRODUCTION
# ============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ============================================================================
# WHITENOISE CONFIGURATION
# ============================================================================
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ============================================================================
# SECURITY HEADERS (Production)
# ============================================================================
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================
EMAIL_BACKEND = os.getenv('DJANGO_EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('DJANGO_EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('DJANGO_EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('DJANGO_EMAIL_USE_TLS', 'True').lower() in ('true', '1', 't')
EMAIL_HOST_USER = os.getenv('DJANGO_EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('DJANGO_EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'MarketLens <noreply@marketlens.com>')

# ============================================================================
# SESSION SETTINGS
# ============================================================================
SESSION_ENGINE = os.getenv('SESSION_ENGINE', 'django.contrib.sessions.backends.db')
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', 86400))
SESSION_SAVE_EVERY_REQUEST = os.getenv('SESSION_SAVE_EVERY_REQUEST', 'True').lower() in ('true', '1', 't')
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.getenv('SESSION_EXPIRE_AT_BROWSER_CLOSE', 'False').lower() in ('true', '1', 't')
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# ============================================================================
# TOKEN EXPIRY SETTINGS
# ============================================================================
OTP_EXPIRY_MINUTES = int(os.getenv('OTP_EXPIRY_MINUTES', 10))
PASSWORD_RESET_TOKEN_EXPIRY_HOURS = int(os.getenv('PASSWORD_RESET_TOKEN_EXPIRY_HOURS', 1))
EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS = int(os.getenv('EMAIL_VERIFICATION_TOKEN_EXPIRY_HOURS', 24))

# ============================================================================
# RATE LIMITING SETTINGS (Custom)
# ============================================================================
RATE_LIMIT_MAX_ATTEMPTS = int(os.getenv('RATE_LIMIT_MAX_ATTEMPTS', 3))
RATE_LIMIT_BLOCK_HOURS = int(os.getenv('RATE_LIMIT_BLOCK_HOURS', 1))
RATE_LIMIT_WINDOW_HOURS = int(os.getenv('RATE_LIMIT_WINDOW_HOURS', 1))

# ============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ============================================================================
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ============================================================================
# LOGGING CONFIGURATION (Production)
# ============================================================================
import os

# Ensure logs directory exists
LOG_DIR = BASE_DIR / 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'WARNING',
            'class': 'logging.handlers.RotatingFileHandler',  # Changed to RotatingFileHandler
            'filename': LOG_DIR / 'django.log',
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'accounts': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}