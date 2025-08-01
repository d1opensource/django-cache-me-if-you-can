"""
Pytest configuration for django-cache-me tests
"""
import os
import django
from django.conf import settings
from django.test.utils import get_runner


def pytest_configure():
    """Configure Django settings for pytest."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_cache_me.tests.settings')
    django.setup()


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    pass
