"""
Django Cache Me If You Can - A Django library for caching model querysets.
"""

__version__ = '0.1.0'
__author__ = 'Your Name'

default_app_config = 'django_cache_me.apps.DjangoCacheMeConfig'

# Import main components for easy access
from .registry import cache_me_register, CacheMeOptions, cache_me_registry
