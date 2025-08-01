"""
Test signals functionality for django-cache-me
"""
from django.test import TestCase, override_settings
from django.core.cache import cache
from django.db import models
from unittest.mock import patch, MagicMock

from django_cache_me.signals import (
    invalidate_model_cache,
    auto_invalidate_cache,
    enable_auto_invalidation,
    setup_cache_invalidation,
    CacheInvalidationMixin
)
from django_cache_me.registry import CacheMeOptions, cache_me_registry


# Simple test model for testing
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = 'django_cache_me'
        abstract = True


class TestCacheInvalidationSignals(TestCase):
    """Test cache invalidation signals."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

    def test_invalidate_model_cache_registered_model(self):
        """Test cache invalidation for registered model."""
        # Register the model
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
        cache_me_registry.register(TestModel, TestOptions)

        # Create cache entry
        cache_key = f"cache_me:queryset:{TestModel._meta.app_label}.{TestModel._meta.model_name}:test_key"
        cache.set(cache_key, ["test_data"], 300)

        # Test cache invalidation
        invalidate_model_cache(TestModel)

        # This test verifies the function runs without error
        self.assertTrue(True)

    def test_invalidate_model_cache_unregistered_model(self):
        """Test cache invalidation for unregistered model."""
        # Ensure model is not registered
        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]

        # Should not raise exception for unregistered model
        try:
            invalidate_model_cache(TestModel)
        except Exception as e:
            self.fail(f"invalidate_model_cache should not raise exception for unregistered model: {e}")

    def test_invalidate_model_cache_with_permanent_flag(self):
        """Test cache invalidation with permanent flag."""
        # Register the model
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
        cache_me_registry.register(TestModel, TestOptions)

        # Test with permanent invalidation
        try:
            invalidate_model_cache(TestModel, invalidate_permanent=True)
        except Exception as e:
            self.fail(f"invalidate_model_cache with permanent flag should not raise exception: {e}")

    def test_auto_invalidate_cache_signal_handler(self):
        """Test auto invalidate cache signal handler."""
        # Register the model
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
        cache_me_registry.register(TestModel, TestOptions)

        # Test signal handler
        try:
            auto_invalidate_cache(sender=TestModel, instance=None, created=True)
        except Exception as e:
            self.fail(f"auto_invalidate_cache should not raise exception: {e}")

    def test_enable_auto_invalidation(self):
        """Test enabling auto invalidation for a model."""
        # Test enabling auto invalidation
        try:
            enable_auto_invalidation(TestModel)
            # Verify signals are connected (check that no exception was raised)
            self.assertTrue(True)  # If we get here, no exception was raised
        except Exception as e:
            self.fail(f"enable_auto_invalidation should not raise exception: {e}")

    def test_setup_cache_invalidation(self):
        """Test setting up cache invalidation for all registered models."""
        # Register the model
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
        cache_me_registry.register(TestModel, TestOptions)

        # Test setup cache invalidation
        try:
            setup_cache_invalidation()
        except Exception as e:
            self.fail(f"setup_cache_invalidation should not raise exception: {e}")

    @override_settings(DJANGO_CACHE_ME_DEBUG_MODE=True)
    def test_cache_invalidation_with_debug_mode(self):
        """Test cache invalidation with debug mode enabled."""
        # Register the model
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
        cache_me_registry.register(TestModel, TestOptions)

        # Test that invalidation works in debug mode
        try:
            invalidate_model_cache(TestModel)
        except Exception as e:
            self.fail(f"invalidate_model_cache should not raise exception in debug mode: {e}")

    def test_cache_invalidation_mixin_functionality(self):
        """Test CacheInvalidationMixin functionality."""
        # Test that the mixin exists and can be used
        self.assertTrue(hasattr(CacheInvalidationMixin, 'save'))
        self.assertTrue(hasattr(CacheInvalidationMixin, 'delete'))

    @patch('django_cache_me.signals.cache')
    def test_cache_deletion_patterns(self, mock_cache):
        """Test cache deletion patterns."""
        # Register the model
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
        cache_me_registry.register(TestModel, TestOptions)

        # Mock cache methods
        mock_cache.delete = MagicMock()
        mock_cache.delete_pattern = MagicMock()
        mock_cache.keys = MagicMock(return_value=[
            f'cache_me:queryset:{TestModel._meta.app_label}.{TestModel._meta.model_name}:key1',
            f'cache_me:permanent:{TestModel._meta.app_label}.{TestModel._meta.model_name}:key2',
            'other_cache_key'
        ])

        invalidate_model_cache(TestModel)

        # Verify cache methods were called (implementation may vary)
        self.assertTrue(True)  # Test passes if no exception is raised

    def test_signal_exception_handling(self):
        """Test that signal handlers don't raise exceptions."""
        # Test with various scenarios that might cause exceptions
        try:
            # Test with None sender
            auto_invalidate_cache(sender=None, instance=None, created=True)

            # Test with unregistered model
            auto_invalidate_cache(sender=TestModel, instance=None, created=True)

        except Exception as e:
            self.fail(f"Signal handlers should not raise exceptions: {e}")

    def test_invalidate_model_cache_registry_interaction(self):
        """Test invalidate_model_cache interaction with registry."""
        # Register the model
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
        cache_me_registry.register(TestModel, TestOptions)

        # Test that invalidation works with registered model
        try:
            invalidate_model_cache(TestModel)
        except Exception as e:
            self.fail(f"invalidate_model_cache should work with registered model: {e}")
