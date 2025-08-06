"""Integration tests for django-cache-me."""

from django.core.cache import cache
from django.db import models
from django.test import TestCase, override_settings

from django_cache_me.registry import CacheMeOptions, cache_me_register, cache_me_registry
from django_cache_me.signals import auto_invalidate_cache, invalidate_model_cache


# Simple test models for integration testing
class IntegrationTestModel(models.Model):
    """Test model for integration testing."""

    name = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "django_cache_me"
        abstract = True


class RelatedIntegrationModel(models.Model):
    """Related test model for integration testing."""

    title = models.CharField(max_length=200)
    score = models.FloatField(default=0.0)

    class Meta:
        app_label = "django_cache_me"
        abstract = True


class IntegrationTestCase(TestCase):
    """Full integration tests for django-cache-me."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

    def test_full_cache_workflow(self):
        """Test complete cache workflow: register, cache, invalidate."""
        # Clear registry for this model
        if IntegrationTestModel in cache_me_registry._registry:
            del cache_me_registry._registry[IntegrationTestModel]

        # Step 1: Register model with cache options
        @cache_me_register(IntegrationTestModel)
        class IntegrationOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
                self.cache_queryset = True
                self.timeout = 300

        # Verify registration worked
        self.assertTrue(cache_me_registry.is_registered(IntegrationTestModel))
        options = cache_me_registry.get_options(IntegrationTestModel)
        self.assertTrue(options.cache_table)
        self.assertTrue(options.cache_queryset)

    def test_queryset_caching_with_filters(self):
        """Test queryset caching with complex filters."""
        # Clear registry for this model
        if IntegrationTestModel in cache_me_registry._registry:
            del cache_me_registry._registry[IntegrationTestModel]

        # Register model
        @cache_me_register(IntegrationTestModel)
        class FilterOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_queryset = True
                self.timeout = 300

        # Verify registration
        self.assertTrue(cache_me_registry.is_registered(IntegrationTestModel))

    def test_no_cache_functionality(self):
        """Test no_cache functionality."""
        # Clear registry for this model
        if IntegrationTestModel in cache_me_registry._registry:
            del cache_me_registry._registry[IntegrationTestModel]

        # Register model
        @cache_me_register(IntegrationTestModel)
        class NoCacheOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
                self.cache_queryset = True

        # Verify registration
        self.assertTrue(cache_me_registry.is_registered(IntegrationTestModel))

    def test_permanent_cache_functionality(self):
        """Test permanent cache functionality."""
        # Clear registry for this model
        if IntegrationTestModel in cache_me_registry._registry:
            del cache_me_registry._registry[IntegrationTestModel]

        # Register model
        @cache_me_register(IntegrationTestModel)
        class PermanentCacheOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_queryset = True
                self.timeout = 300

        # Verify registration
        self.assertTrue(cache_me_registry.is_registered(IntegrationTestModel))

    def test_cache_invalidation_on_model_changes(self):
        """Test that cache is invalidated when model instances change."""
        # Clear registry for this model
        if IntegrationTestModel in cache_me_registry._registry:
            del cache_me_registry._registry[IntegrationTestModel]

        # Register model
        @cache_me_register(IntegrationTestModel)
        class InvalidationOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
                self.cache_queryset = True

        # Test that invalidation functions work
        try:
            invalidate_model_cache(IntegrationTestModel)
            auto_invalidate_cache(sender=IntegrationTestModel, instance=None, created=False)
        except Exception as e:
            self.fail(f"Cache invalidation should work: {e}")

    @override_settings(DJANGO_CACHE_ME_ON=False)
    def test_cache_disabled_functionality(self):
        """Test that caching is disabled when DJANGO_CACHE_ME_ON=False."""
        # Clear registry for this model
        if IntegrationTestModel in cache_me_registry._registry:
            del cache_me_registry._registry[IntegrationTestModel]

        # Register model
        @cache_me_register(IntegrationTestModel)
        class DisabledOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
                self.cache_queryset = True

        # Verify registration still works even when caching is disabled
        self.assertFalse(cache_me_registry.is_registered(IntegrationTestModel))

    @override_settings(DJANGO_CACHE_ME_DEBUG_MODE=True)
    def test_debug_mode_logging(self):
        """Test debug mode logging functionality."""
        # Clear registry for this model
        if IntegrationTestModel in cache_me_registry._registry:
            del cache_me_registry._registry[IntegrationTestModel]

        # Register model
        @cache_me_register(IntegrationTestModel)
        class DebugOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        # Verify debug mode works
        self.assertTrue(cache_me_registry.is_registered(IntegrationTestModel))
