"""
Django settings for restaurant_system project.
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-your-secret-key-here'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*', 'testserver', '127.0.0.1', 'localhost']

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
    'django.middleware.csrf.CsrfViewMiddleware',  # Re-enabled for security
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

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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
# This matches your system timezone for proper Happy Hour functionality
TIME_ZONE = 'Africa/Nairobi'  # East Africa Standard Time (UTC+3)

USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
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

# Channels Configuration for WebSockets
ASGI_APPLICATION = 'restaurant_system.asgi.application'

# Security Headers Configuration
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'SAMEORIGIN'  # Allow iframes from same origin

# Cross-Origin Policies
CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
CROSS_ORIGIN_EMBEDDER_POLICY = 'require-corp'

# CSRF Configuration for development
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access for AJAX
CSRF_COOKIE_SECURE = False    # Set to True in production with HTTPS
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://0.0.0.0:8000',
]

# Session Configuration
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Try Redis first, fall back to in-memory channels for development
try:
    import redis
    # Test Redis connection
    r = redis.Redis(host='127.0.0.1', port=6379, db=0)
    r.ping()
    # Redis is available
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [('127.0.0.1', 6379)],
            },
        },
    }
    print("✓ Using Redis for WebSocket channels")
except (ImportError, redis.ConnectionError, redis.ResponseError):
    # Redis not available, use in-memory channels (development only)
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
    print("⚠ Using in-memory channels (development only) - Install and start Redis for production")
LOGOUT_REDIRECT_URL = '/'

# Custom Security Headers Middleware Class
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Add security headers
        response['Cross-Origin-Opener-Policy'] = 'same-origin'
        response['Cross-Origin-Embedder-Policy'] = 'require-corp'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response

# Add custom middleware to the middleware stack
MIDDLEWARE.insert(1, 'restaurant_system.settings.SecurityHeadersMiddleware')
