import logging
from django.conf import settings

# Configure logger for cache debug messages
logger = logging.getLogger('django_cache_me')


def get_setting(name, default):
    """Get a django-cache-me setting with a default value."""
    return getattr(settings, name, default)


def is_cache_enabled():
    """Check if caching is enabled globally."""
    return get_setting('DJANGO_CACHE_ME_ON', True)


def is_debug_mode():
    """Check if debug mode is enabled."""
    return get_setting('DJANGO_CACHE_ME_DEBUG_MODE', False)


def get_default_timeout():
    """Get the default cache timeout."""
    return get_setting('DJANGO_CACHE_ME_TIMEOUT', 300)


def debug_log(message, *args):
    """Log debug message if debug mode is enabled."""
    if is_debug_mode():
        if args:
            message = message % args
        logger.info(message)
        # Also print to stdout for immediate visibility
        print(f"[django-cache-me] {message}")


def cache_hit_log(cache_key, timeout):
    """Log when a queryset is cached."""
    debug_log("Cached queryset with key '%s' for %d seconds", cache_key, timeout)


def cache_miss_log(cache_key):
    """Log when cache is missed and query hits database."""
    debug_log("Cache miss for key '%s' - hitting database", cache_key)


def cache_retrieval_log(cache_key):
    """Log when data is retrieved from cache."""
    debug_log("Retrieving data from key '%s' from cache", cache_key)


def cache_invalidation_log(model_name, permanent=False):
    """Log when cache is invalidated."""
    cache_type = "permanent and regular" if permanent else "regular"
    debug_log("Cache invalidated for model '%s' (%s cache)", model_name, cache_type)
