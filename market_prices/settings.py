# market_prices/market_prices/settings.py
from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# ============================================================================
# SECURITY SETTINGS
# ============================================================================
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-fallback-key-change-in-production')

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() in ('true', '1', 't')

ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Site URL
SITE_URL = os.getenv('SITE_URL', 'http://127.0.0.1:8000')
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
# DATABASE
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
# DJANGO-ALLAUTH SETTINGS
# ============================================================================

# Authentication methods - use email only
ACCOUNT_LOGIN_METHODS = {'email'}

# Signup fields configuration
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
ACCOUNT_TEMPLATE_EXTENSION = 'html'  # Use .html templates
ACCOUNT_CONFIRM_EMAIL_ON_GET = True  # Confirm email on GET request

# Email confirmation redirects
ACCOUNT_EMAIL_CONFIRMATION_AUTHENTICATED_REDIRECT_URL = 'pending_verification'
ACCOUNT_EMAIL_CONFIRMATION_ANONYMOUS_REDIRECT_URL = 'pending_verification'

# Login/Logout settings
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True  # Auto-login after email confirmation
ACCOUNT_LOGOUT_ON_PASSWORD_CHANGE = True
ACCOUNT_LOGIN_ON_PASSWORD_RESET = True
ACCOUNT_SESSION_REMEMBER = True

# User settings
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # We're using email for login

# Password settings
ACCOUNT_PASSWORD_MIN_LENGTH = 8  # Minimum password length

# Signup settings
ACCOUNT_SIGNUP_REDIRECT_URL = 'pending_verification'  # Redirect after signup
ACCOUNT_USERNAME_BLACKLIST = []  # List of forbidden usernames (not used since we don't use usernames)

# Email template mapping
ACCOUNT_EMAIL_CONFIRMATION_HTML = True
ACCOUNT_EMAIL_CONFIRMATION_SUBJECT = 'Confirm Your Email - MarketLens'
# ============================================================================
# SOCIAL ACCOUNT SETTINGS
# ============================================================================

# Social account settings
SOCIALACCOUNT_LOGIN_ON_GET = True  # Skip the intermediate page
SOCIALACCOUNT_EMAIL_REQUIRED = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'none'  # Google already verifies email
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
        # Additional Google-specific settings
        'EMAIL_AUTHENTICATION': True,  # Use email for authentication
        'VERIFIED_EMAIL': True,  # Google emails are verified
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

# Rate limiting for allauth (prevents abuse)
ACCOUNT_RATE_LIMITS = {
    'login_failed': '5/5m',        # 5 attempts per 5 minutes
    'signup': '3/1h',               # 3 signups per hour
    'confirm_email': '10/5m',       # 10 email confirmations per 5 minutes
    'reset_password': '5/1h',       # 5 password resets per hour
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
# STATIC & MEDIA FILES
# ============================================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

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
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', 86400))  # 24 hours default
SESSION_SAVE_EVERY_REQUEST = os.getenv('SESSION_SAVE_EVERY_REQUEST', 'True').lower() in ('true', '1', 't')
SESSION_EXPIRE_AT_BROWSER_CLOSE = os.getenv('SESSION_EXPIRE_AT_BROWSER_CLOSE', 'False').lower() in ('true', '1', 't')
SESSION_COOKIE_SECURE = not DEBUG  # Only send over HTTPS in production
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



# Add to settings.py for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'accounts': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}