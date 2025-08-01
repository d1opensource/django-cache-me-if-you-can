from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured


class DjangoCacheMeConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'django_cache_me'
    verbose_name = 'Django Cache Me'

    def ready(self):
        """
        This method is called when the app is ready.
        Auto-discover cache_me.py files in all installed apps and set up cache invalidation.
        """
        from .autodiscover import autodiscover
        from .signals import setup_cache_invalidation

        # First discover all cache_me.py files and register models
        try:
            autodiscover()
        except ImproperlyConfigured:
            # Handle autodiscover exceptions gracefully
            pass

        # Then set up automatic cache invalidation for all registered models
        setup_cache_invalidation()
