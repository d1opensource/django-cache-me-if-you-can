"""
Test decorators functionality for django-cache-me
"""
from django.test import TestCase
from django.db import models
from unittest.mock import patch

from django_cache_me.registry import cache_me_register, CacheMeOptions, cache_me_registry


# Simple test model for testing
class TestModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = 'django_cache_me'
        abstract = True


class TestCacheMeRegisterDecorator(TestCase):
    """Test the cache_me_register decorator."""
    
    def setUp(self):
        """Clean up registry before each test."""
        # Clear any existing registrations
        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
    
    def test_decorator_with_model_parameter(self):
        """Test decorator when used with model parameter."""
        @cache_me_register(TestModel)
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
                self.timeout = 600
        
        # Verify model is registered
        self.assertTrue(cache_me_registry.is_registered(TestModel))
        
        # Verify options are correct
        options = cache_me_registry.get_options(TestModel)
        self.assertTrue(options.cache_table)
        self.assertEqual(options.timeout, 600)
        
        # Verify the class is returned unchanged
        self.assertEqual(TestOptions.__name__, 'TestOptions')
        self.assertTrue(issubclass(TestOptions, CacheMeOptions))
    
    def test_decorator_without_model_parameter(self):
        """Test decorator when used without model parameter."""
        # This should return a decorator function
        decorator = cache_me_register
        self.assertTrue(callable(decorator))
    
    def test_decorator_with_custom_options_class(self):
        """Test decorator with custom options class."""
        class CustomCacheMeOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = False
                self.cache_queryset = False
                self.timeout = 120
        
        @cache_me_register(TestModel)
        class TestCustomOptions(CustomCacheMeOptions):
            pass
        
        # Verify model is registered
        self.assertTrue(cache_me_registry.is_registered(TestModel))
        
        # Verify custom options are preserved
        options = cache_me_registry.get_options(TestModel)
        self.assertFalse(options.cache_table)
        self.assertFalse(options.cache_queryset)
        self.assertEqual(options.timeout, 120)
    
    def test_decorator_class_inheritance(self):
        """Test that decorated class maintains inheritance."""
        class BaseCacheOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)

            def custom_method(self):
                return "base_method"
        
        @cache_me_register(TestModel)
        class InheritedOptions(BaseCacheOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
                
            def custom_method(self):
                return "inherited_method"
        
        # Verify inheritance is maintained
        options = cache_me_registry.get_options(TestModel)
        self.assertTrue(hasattr(options, 'custom_method'))
        self.assertEqual(options.custom_method(), "inherited_method")
        self.assertTrue(options.cache_table)
    
    @patch('django_cache_me.registry.cache_me_registry')
    def test_decorator_registry_interaction(self, mock_registry):
        """Test decorator interaction with registry."""
        @cache_me_register(TestModel)
        class RegistryTestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
        
        # Verify registry.register was called
        mock_registry.register.assert_called_once()
        args, kwargs = mock_registry.register.call_args
        self.assertEqual(args[0], TestModel)
        self.assertEqual(args[1], RegistryTestOptions)

    def test_decorator_preserves_class_attributes(self):
        """Test that decorator preserves class attributes and methods."""
        @cache_me_register(TestModel)
        class AttributeTestOptions(CacheMeOptions):
            custom_attribute = "test_value"
            
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
            
            def custom_method(self):
                return "test_method"
            
            @classmethod
            def class_method(cls):
                return "class_method"
            
            @staticmethod
            def static_method():
                return "static_method"
        
        # Verify all attributes and methods are preserved
        self.assertEqual(AttributeTestOptions.custom_attribute, "test_value")
        
        options = cache_me_registry.get_options(TestModel)
        self.assertEqual(options.custom_method(), "test_method")
        self.assertEqual(AttributeTestOptions.class_method(), "class_method")
        self.assertEqual(AttributeTestOptions.static_method(), "static_method")
    
    def test_decorator_with_multiple_inheritance(self):
        """Test decorator with multiple inheritance."""
        class MixinA:
            def method_a(self):
                return "method_a"
        
        class MixinB:
            def method_b(self):
                return "method_b"
        
        @cache_me_register(TestModel)
        class MultiInheritanceOptions(MixinA, MixinB, CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
        
        # Verify multiple inheritance is preserved
        options = cache_me_registry.get_options(TestModel)
        self.assertTrue(hasattr(options, 'method_a'))
        self.assertTrue(hasattr(options, 'method_b'))
        self.assertEqual(options.method_a(), "method_a")
        self.assertEqual(options.method_b(), "method_b")
        self.assertTrue(options.cache_table)
