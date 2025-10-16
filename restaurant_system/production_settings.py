"""
Production settings for Restaurant Ordering System
This file will be used when deploying to production server
"""

from pathlib import Path
import os
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

# Application definition
INSTALLED_APPS = [
    'daphne',  # Add this for Channels ASGI support
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',  # Add Channels
    'accounts',
    'restaurant',
    'orders',
    'admin_panel',
    'system_admin',
    'cashier',
    'waste_management',
    'reports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',  # Enabled for production
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'subscription_middleware.SubscriptionAccessMiddleware',  # SaaS subscription control
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'restaurant_system.urls'

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

WSGI_APPLICATION = 'restaurant_system.wsgi.application'

# Database - Use environment variables for production
DATABASES = {
    'default': {
        'ENGINE': config('DATABASE_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME', default='restaurant_db'),
        'USER': config('DB_USER', default='restaurant_user'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# Password validation
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

# Internationalization
LANGUAGE_CODE = 'en-us'

# Set to East Africa Standard Time (UTC+3) for consistent local/production behavior
TIME_ZONE = 'Africa/Nairobi'  # East Africa Standard Time (UTC+3)

USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom user model
AUTH_USER_MODEL = 'accounts.User'

# Login URLs
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Channels Configuration for WebSockets
ASGI_APPLICATION = 'restaurant_system.asgi.application'

# Redis configuration for production
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(
                config('REDIS_HOST', default='127.0.0.1'),
                config('REDIS_PORT', default=6379, cast=int)
            )],
        },
    },
}

# Security Settings for Production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Allow iframes from same origin

# Cross-Origin Policies - Relaxed to allow CDN resources
CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'
CROSS_ORIGIN_EMBEDDER_POLICY = 'unsafe-none'  # Allow external CDN resources

# CSRF Settings
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript to read CSRF token
CSRF_COOKIE_SECURE = True    # Required for HTTPS
CSRF_COOKIE_SAMESITE = 'Lax'  # Allow cookies in same-site context
CSRF_COOKIE_NAME = 'csrftoken'  # Default name
CSRF_USE_SESSIONS = False  # Store CSRF token in cookie, not session
CSRF_TRUSTED_ORIGINS = [
    'https://easyfixsoft.com',
    'https://www.easyfixsoft.com',
    'http://easyfixsoft.com',
    'http://www.easyfixsoft.com',
    'http://24.199.116.165',
    'https://24.199.116.165',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

# Session Configuration
SESSION_COOKIE_SECURE = True  # Required for HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# HTTPS Settings - SSL is configured with nginx reverse proxy
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# SECURE_SSL_REDIRECT = True  # Let nginx handle SSL redirect

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'django.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'restaurant': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Custom Security Headers Middleware Class
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers - Allow CDN resources
        response['Cross-Origin-Opener-Policy'] = 'same-origin-allow-popups'
        response['Cross-Origin-Embedder-Policy'] = 'unsafe-none'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response

# Add custom middleware to the middleware stack
MIDDLEWARE.insert(1, 'restaurant_system.production_settings.SecurityHeadersMiddleware')
