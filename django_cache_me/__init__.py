"""Django Cache Me If You Can - A Django library for caching model querysets."""

# Import main components for easy access
from .model_mixin import CacheMeInvalidationMixin
from .registry import CacheMeOptions, cache_me_register, cache_me_registry

__version__ = "0.1.0"
__author__ = "Marcelo Moraes"

default_app_config = "django_cache_me.apps.DjangoCacheMeConfig"


__all__ = [
    "CacheMeInvalidationMixin",
    "CacheMeOptions",
    "cache_me_register",
    "cache_me_registry",
]
