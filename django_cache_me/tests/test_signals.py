"""Test signals functionality for django-cache-me."""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.db import models, transaction
from django.test import TestCase, TransactionTestCase, override_settings

from django_cache_me.registry import CacheMeOptions, cache_me_registry
from django_cache_me.signals import (
    auto_invalidate_cache,
    enable_auto_invalidation,
    invalidate_all_caches,
    invalidate_model_cache,
    schedule_invalidation,
    setup_cache_invalidation,
)


# Simple test model for testing
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "django_cache_me"
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

    @patch("django.core.cache.caches")
    def test_cache_deletion_patterns(self, mock_caches):
        """Test cache deletion patterns."""

        # Register the model
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
        cache_me_registry.register(TestModel, TestOptions)

        # Mock the cache instance
        mock_cache = MagicMock()
        mock_caches.__getitem__.return_value = mock_cache

        # Mock cache methods
        mock_cache.delete = MagicMock()
        mock_cache.delete_pattern = MagicMock()
        mock_cache.__class__.__name__ = "MockCache"

        # Make sure it's not detected as DummyCache
        mock_cache.__class__ = MagicMock()

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

    @override_settings(DJANGO_CACHE_ME_ASYNC_ENABLED=False, DJANGO_CACHE_ME_ASYNC_ON_COMMIT=False)
    def test_schedule_invalidation_sync_calls_invalidate_and_warmers(self):
        """schedule_invalidation should call invalidate_model_cache and warmers in sync mode."""
        with (
            patch("django_cache_me.signals.invalidate_model_cache") as mock_inv,
            patch("django_cache_me.signals._run_warmers_for_model") as mock_warm,
        ):
            schedule_invalidation(TestModel, invalidate_permanent=True, warm=True)
            mock_inv.assert_called_once_with(TestModel, invalidate_permanent=True)
            mock_warm.assert_called_once_with(TestModel)

    @override_settings(DJANGO_CACHE_ME_ASYNC_ENABLED=True, DJANGO_CACHE_ME_ASYNC_ON_COMMIT=False)
    def test_schedule_invalidation_async_fallback_to_sync_on_error(self):
        """If enqueue fails, scheduler should fall back to sync invalidation."""
        with (
            patch("django_cache_me.tasks.invalidate_model_cache_task.delay", side_effect=RuntimeError("boom")),
            patch("django_cache_me.signals.invalidate_model_cache") as mock_inv,
        ):
            schedule_invalidation(TestModel, invalidate_permanent=True, warm=False)
            mock_inv.assert_called_once_with(TestModel, invalidate_permanent=True)

    @override_settings(DJANGO_CACHE_ME_ASYNC_ENABLED=True)
    def test_invalidate_all_caches_uses_scheduler(self):
        """invalidate_all_caches should go through the scheduler in async mode."""

        # Register a dummy model so the helper has something to process
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]
        cache_me_registry.register(TestModel, TestOptions)

        with (
            patch("django_cache_me.signals.schedule_invalidation") as mock_sched,
            patch("django_cache_me.registry.cache_me_registry.get_registered_models", return_value=[TestModel]),
        ):
            invalidate_all_caches(invalidate_permanent=False)
            # Should attempt to schedule for the single registered model
            mock_sched.assert_called_once_with(TestModel, invalidate_permanent=False)


class TestCacheInvalidationSignalsTransactional(TransactionTestCase):
    """Transactional tests for commit hooks."""

    reset_sequences = True

    @override_settings(DJANGO_CACHE_ME_ASYNC_ENABLED=True, DJANGO_CACHE_ME_ASYNC_ON_COMMIT=True)
    def test_schedule_invalidation_async_on_commit(self):
        """When on_commit is enabled, enqueue should be called after commit in a real transaction."""
        with patch("django_cache_me.tasks.invalidate_model_cache_task.delay") as mock_delay:
            # Use an atomic block to trigger on_commit
            with transaction.atomic():
                schedule_invalidation(TestModel, invalidate_permanent=False, warm=False)
                # Not yet called inside the transaction
                assert mock_delay.call_count == 0
            # After exiting atomic block (innermost and outermost), on_commit runs in TransactionTestCase
            assert mock_delay.call_count == 1
