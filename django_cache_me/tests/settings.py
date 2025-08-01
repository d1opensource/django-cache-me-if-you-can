"""
Test settings for django-cache-me
"""

SECRET_KEY = 'test-secret-key-for-django-cache-me'

DEBUG = True

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django_cache_me',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

USE_TZ = True

# Django Cache Me settings
DJANGO_CACHE_ME_DEBUG_MODE = True
DJANGO_CACHE_ME_ON = True

# Required for Django 3.2+
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
