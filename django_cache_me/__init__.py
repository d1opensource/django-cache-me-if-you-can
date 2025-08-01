"""Django Cache Me If You Can - A Django library for caching model querysets."""

# Import main components for easy access
from .registry import CacheMeOptions, cache_me_register, cache_me_registry

__version__ = "0.1.0"
__author__ = "Marcelo Moraes"

default_app_config = "django_cache_me.apps.DjangoCacheMeConfig"


__all__ = [
    "CacheMeOptions",
    "cache_me_register",
    "cache_me_registry",
]
