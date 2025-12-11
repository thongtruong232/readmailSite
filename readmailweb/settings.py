import os
from pathlib import Path
import redis

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-4@3+8)s&i%la6h85zrraihigs3p5yr3w($bc0+4h2*w*!rb4+%'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '207.148.69.229', '103.216.119.53']

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',
    'channels_redis',
    'mail',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Channels
ASGI_APPLICATION = 'readmailweb.asgi.application'

# Redis configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        # Avoid URL-encoding issues by passing address/password separately
        'LOCATION': 'redis://207.148.69.229:6380/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': 'J[y7324M8jo?YG[=',
        }
    }
}

# Try to use Redis, fallback to InMemoryChannelLayer if Redis is not available
try:
    # Test Redis connection
    r = redis.Redis(host='207.148.69.229', port=6380, password='J[y7324M8jo?YG[=', socket_connect_timeout=2)
    r.ping()
    # Redis is available, use it
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                # Use structured config to avoid invalid Redis URLs with special chars
                "hosts": [{
                    # aioredis expects a string URL; tuple causes AttributeError in parse_url
                    "address": "redis://207.148.69.229:6380/0",
                    "password": "J[y7324M8jo?YG[=",
                    "db": 0,
                }],
            },
        },
    }
    print("==> Using Redis Channel Layer")
except (redis.exceptions.ConnectionError, redis.exceptions.TimeoutError, Exception) as e:
    # Redis is not available, use InMemoryChannelLayer for development
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        },
    }
    print(f"==> Redis not available ({e}), using InMemoryChannelLayer (single process only)")

# URL Configuration
ROOT_URLCONF = 'readmailweb.urls'

# Template Configuration
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'mail/templates')],
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

# Cấu hình WebSocket
CHANNELS_WS_PROTOCOLS = ["websocket"]
CHANNELS_WS_ALLOWED_HOSTS = ["*"]  # Cho phép kết nối từ mọi host trong development
CHANNELS_WS_AUTHENTICATION = True 