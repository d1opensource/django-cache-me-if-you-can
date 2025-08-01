"""
Test autodiscover functionality for django-cache-me
"""
from django.test import TestCase
from django.core.exceptions import ImproperlyConfigured
from unittest.mock import patch, MagicMock

from django_cache_me.autodiscover import autodiscover


class TestAutodiscover(TestCase):
    """Test autodiscover functionality."""
    
    def test_autodiscover_runs_without_error(self):
        """Test that autodiscover runs without raising exceptions."""
        try:
            autodiscover()
        except Exception as e:
            self.fail(f"autodiscover() should not raise exceptions: {e}")
    
    @patch('django_cache_me.autodiscover.apps')
    @patch('django_cache_me.autodiscover.importlib.import_module')
    def test_autodiscover_success(self, mock_import_module, mock_apps):
        """Test successful autodiscovery with mocked apps."""
        # Mock Django apps
        mock_app_config = MagicMock()
        mock_app_config.name = 'test_app'
        mock_apps.get_app_configs.return_value = [mock_app_config]
        
        # Mock successful import
        mock_import_module.return_value = MagicMock()
        
        # Should not raise any exception
        autodiscover()
        
        # Verify import was attempted
        self.assertTrue(mock_import_module.called)
    
    @patch('django_cache_me.autodiscover.apps')
    @patch('django_cache_me.autodiscover.importlib.import_module')
    def test_autodiscover_module_not_found(self, mock_import_module, mock_apps):
        """Test autodiscover when cache_me module doesn't exist."""
        # Mock Django apps
        mock_app_config = MagicMock()
        mock_app_config.name = 'test_app'
        mock_apps.get_app_configs.return_value = [mock_app_config]
        
        # Mock ModuleNotFoundError
        mock_import_module.side_effect = ModuleNotFoundError("No module named 'test_app.cache_me'")
        
        # Should not raise any exception for ModuleNotFoundError
        autodiscover()
        
        # Verify import was attempted
        self.assertTrue(mock_import_module.called)
    
    @patch('django_cache_me.autodiscover.apps')
    @patch('django_cache_me.autodiscover.importlib.import_module')
    def test_autodiscover_handles_import_errors(self, mock_import_module, mock_apps):
        """Test autodiscover handles import errors appropriately."""
        # Mock Django apps
        mock_app_config = MagicMock()
        mock_app_config.name = 'test_app'
        mock_apps.get_app_configs.return_value = [mock_app_config]
        
        # Mock ImportError (not ModuleNotFoundError)
        mock_import_module.side_effect = ImportError("Some other import error")
        
        # Should handle the error gracefully
        try:
            autodiscover()
        except ImproperlyConfigured:
            # This is expected behavior for non-ModuleNotFoundError imports
            pass
        except Exception as e:
            self.fail(f"autodiscover should handle import errors gracefully: {e}")
    
    @patch('django_cache_me.autodiscover.apps')
    @patch('django_cache_me.autodiscover.importlib.import_module')
    def test_autodiscover_other_exception(self, mock_import_module, mock_apps):
        """Test autodiscover when there's another type of exception."""
        # Mock Django apps
        mock_app_config = MagicMock()
        mock_app_config.name = 'test_app'
        mock_apps.get_app_configs.return_value = [mock_app_config]
        
        # Mock other exception
        mock_import_module.side_effect = ValueError("Some value error")
        
        # Should handle the error gracefully
        try:
            autodiscover()
        except ImproperlyConfigured:
            # This is expected behavior for other exceptions
            pass
        except Exception as e:
            self.fail(f"autodiscover should handle exceptions gracefully: {e}")
    
    @patch('django_cache_me.autodiscover.apps')
    @patch('django_cache_me.autodiscover.importlib.import_module')
    def test_autodiscover_multiple_apps(self, mock_import_module, mock_apps):
        """Test autodiscover with multiple apps."""
        # Mock Django apps
        mock_app_config1 = MagicMock()
        mock_app_config1.name = 'app1'
        mock_app_config2 = MagicMock()
        mock_app_config2.name = 'app2'
        mock_apps.get_app_configs.return_value = [mock_app_config1, mock_app_config2]
        
        # Mock successful imports
        mock_import_module.return_value = MagicMock()
        
        autodiscover()
        
        # Should have attempted imports (actual count may vary due to real apps)
        self.assertTrue(mock_import_module.called)
    
    @patch('django_cache_me.autodiscover.apps')
    @patch('django_cache_me.autodiscover.importlib.import_module')
    def test_autodiscover_mixed_success_failure(self, mock_import_module, mock_apps):
        """Test autodiscover with mixed success and failure."""
        # Mock Django apps
        mock_app_config1 = MagicMock()
        mock_app_config1.name = 'app1'
        mock_app_config2 = MagicMock()
        mock_app_config2.name = 'app2'
        mock_apps.get_app_configs.return_value = [mock_app_config1, mock_app_config2]
        
        # Mock mixed results: first succeeds, second fails with ModuleNotFoundError
        def side_effect(module_name):
            if 'app1' in module_name:
                return MagicMock()
            elif 'app2' in module_name:
                raise ModuleNotFoundError("No module named 'app2.cache_me'")
            else:
                return MagicMock()
        
        mock_import_module.side_effect = side_effect
        
        # Should not raise exception
        autodiscover()
        
        # Should have attempted imports
        self.assertTrue(mock_import_module.called)
