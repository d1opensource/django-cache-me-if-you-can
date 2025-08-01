import importlib

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured


def autodiscover():
    """
    Auto-discover cache_me.py files in all INSTALLED_APPS.
    This function is called when Django starts up.
    """
    for app_config in apps.get_app_configs():
        app_name = app_config.name

        # Try to import cache_me module from each app
        try:
            importlib.import_module(f"{app_name}.cache_me")
        except ImportError:
            # No cache_me.py file in this app, that's fine
            pass
        except Exception as e:
            # Other errors should be reported
            msg = f"Error importing cache_me module from {app_name}: {e}"
            raise ImproperlyConfigured(msg) from e


#
# def get_cache_backend():
#     """
#     Get the configured Django cache backend.
#     """
#     from django.core.cache import cache
#     return cache
