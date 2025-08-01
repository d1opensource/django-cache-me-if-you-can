"""
Test settings functionality for django-cache-me
"""
import pytest
from django.test import TestCase, override_settings
from unittest.mock import patch

from django_cache_me.settings import get_setting


class TestSettings(TestCase):
    """Test settings functionality."""
    
    def test_get_setting_default_debug_mode(self):
        """Test default value for DJANGO_CACHE_ME_DEBUG_MODE."""
        with override_settings():
            # Remove the setting if it exists
            from django.conf import settings
            if hasattr(settings, 'DJANGO_CACHE_ME_DEBUG_MODE'):
                delattr(settings, 'DJANGO_CACHE_ME_DEBUG_MODE')
            
            result = get_setting('DJANGO_CACHE_ME_DEBUG_MODE', False)
            self.assertFalse(result)
    
    def test_get_setting_default_cache_on(self):
        """Test default value for DJANGO_CACHE_ME_ON."""
        with override_settings():
            # Remove the setting if it exists
            from django.conf import settings
            if hasattr(settings, 'DJANGO_CACHE_ME_ON'):
                delattr(settings, 'DJANGO_CACHE_ME_ON')
            
            result = get_setting('DJANGO_CACHE_ME_ON', True)
            self.assertTrue(result)
    
    @override_settings(DJANGO_CACHE_ME_DEBUG_MODE=True)
    def test_get_setting_custom_debug_mode(self):
        """Test custom value for DJANGO_CACHE_ME_DEBUG_MODE."""
        result = get_setting('DJANGO_CACHE_ME_DEBUG_MODE', False)
        self.assertTrue(result)
    
    @override_settings(DJANGO_CACHE_ME_ON=False)
    def test_get_setting_custom_cache_on(self):
        """Test custom value for DJANGO_CACHE_ME_ON."""
        result = get_setting('DJANGO_CACHE_ME_ON', True)
        self.assertFalse(result)
    
    def test_get_setting_custom_timeout(self):
        """Test getting custom timeout setting."""
        with override_settings(DJANGO_CACHE_ME_DEFAULT_TIMEOUT=600):
            result = get_setting('DJANGO_CACHE_ME_DEFAULT_TIMEOUT', 300)
            self.assertEqual(result, 600)
    
    def test_get_setting_nonexistent_setting(self):
        """Test getting non-existent setting returns default."""
        result = get_setting('DJANGO_CACHE_ME_NONEXISTENT', 'default_value')
        self.assertEqual(result, 'default_value')
    
    def test_get_setting_none_default(self):
        """Test getting setting with None as default."""
        result = get_setting('DJANGO_CACHE_ME_NONEXISTENT', None)
        self.assertIsNone(result)
    
    @override_settings(DJANGO_CACHE_ME_PREFIX='custom_prefix')
    def test_get_setting_string_value(self):
        """Test getting string setting value."""
        result = get_setting('DJANGO_CACHE_ME_PREFIX', 'cache_me')
        self.assertEqual(result, 'custom_prefix')
    
    @override_settings(DJANGO_CACHE_ME_MAX_ENTRIES=1000)
    def test_get_setting_integer_value(self):
        """Test getting integer setting value."""
        result = get_setting('DJANGO_CACHE_ME_MAX_ENTRIES', 500)
        self.assertEqual(result, 1000)
    
    def test_get_setting_with_empty_string_default(self):
        """Test getting setting with empty string as default."""
        result = get_setting('DJANGO_CACHE_ME_NONEXISTENT', '')
        self.assertEqual(result, '')
    
    def test_get_setting_with_list_default(self):
        """Test getting setting with list as default."""
        default_list = ['item1', 'item2']
        result = get_setting('DJANGO_CACHE_ME_NONEXISTENT', default_list)
        self.assertEqual(result, default_list)
    
    def test_get_setting_with_dict_default(self):
        """Test getting setting with dict as default."""
        default_dict = {'key': 'value'}
        result = get_setting('DJANGO_CACHE_ME_NONEXISTENT', default_dict)
        self.assertEqual(result, default_dict)
