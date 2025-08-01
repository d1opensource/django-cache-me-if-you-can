"""
Test apps module for django-cache-me
"""
from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
from unittest.mock import patch

from django_cache_me.apps import DjangoCacheMeConfig


class TestDjangoCacheMeConfig(TestCase):
    """Test the Django app configuration."""

    def test_app_config_name(self):
        """Test that app config has correct name."""
        config = DjangoCacheMeConfig.create('django_cache_me')
        self.assertEqual(config.name, 'django_cache_me')
        self.assertEqual(config.verbose_name, 'Django Cache Me')

    @patch('django_cache_me.autodiscover.autodiscover')
    def test_ready_calls_autodiscover(self, mock_autodiscover):
        """Test that ready() method calls autodiscover."""
        config = DjangoCacheMeConfig.create('django_cache_me')
        config.ready()
        mock_autodiscover.assert_called_once()

    @patch('django_cache_me.autodiscover.autodiscover')
    def test_ready_handles_autodiscover_exception(self, mock_autodiscover):
        """Test that ready() handles autodiscover exceptions gracefully."""
        mock_autodiscover.side_effect = ImproperlyConfigured("Test error")

        config = DjangoCacheMeConfig.create('django_cache_me')

        # Should not raise exception
        try:
            config.ready()
        except ImproperlyConfigured:
            self.fail("ready() should handle ImproperlyConfigured exceptions")

        mock_autodiscover.assert_called_once()
