"""Test registry functionality for django-cache-me."""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.db import models
from django.db.models.query import QuerySet
from django.test import TestCase, override_settings

from django_cache_me.registry import (
    CachedManager,
    CachedQuerySet,
    CacheMeOptions,
    CacheMeRegistry,
    cache_me_register,
    cache_me_registry,
)


# Simple test model for testing
class TestModel(models.Model):
    name = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        app_label = "django_cache_me"
        abstract = True


class TestCacheMeOptions(TestCase):
    """Test CacheMeOptions class."""

    def test_init_default_values(self):
        """Test that default values are set correctly."""
        options = CacheMeOptions(TestModel)
        self.assertFalse(options.cache_table)
        self.assertTrue(options.cache_queryset)
        self.assertIsNone(options.timeout)

    def test_init_custom_values(self):
        """Test that custom values override defaults."""
        options = CacheMeOptions(TestModel)
        options.cache_table = True
        options.timeout = 600
        self.assertTrue(options.cache_table)
        self.assertEqual(options.timeout, 600)


class TestCachedQuerySet(TestCase):
    """Test CachedQuerySet functionality."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

    def test_generate_cache_key(self):
        """Test cache key generation."""
        queryset = CachedQuerySet(TestModel)
        key = queryset._generate_cache_key()
        self.assertIn("cache_me:queryset", key)
        self.assertIsInstance(key, str)

    def test_generate_cache_key_permanent(self):
        """Test permanent cache key generation."""
        queryset = CachedQuerySet(TestModel)
        queryset._is_permanent_cache = True
        key = queryset._generate_cache_key()
        self.assertIn("cache_me:permanent", key)

    def test_clone_preserves_settings(self):
        """Test that _clone preserves cache settings."""
        queryset = CachedQuerySet(TestModel)
        queryset._use_cache = False
        queryset._is_permanent_cache = True

        clone = queryset._clone()
        self.assertFalse(clone._use_cache)
        self.assertTrue(clone._is_permanent_cache)

    def test_no_cache(self):
        """Test no_cache method."""
        queryset = CachedQuerySet(TestModel)
        no_cache_qs = queryset.no_cache()
        self.assertFalse(no_cache_qs._use_cache)

    def test_permanent_cache(self):
        """Test permanent_cache method."""
        queryset = CachedQuerySet(TestModel)
        perm_cache_qs = queryset.permanent_cache()
        self.assertTrue(perm_cache_qs._is_permanent_cache)

    def test_iterator_method(self):
        """Test iterator method uses caching."""
        queryset = CachedQuerySet(TestModel)

        # Mock the _cache_queryset method to verify it's called
        test_data = ["item1", "item2", "item3"]
        with patch.object(queryset, "_cache_queryset", return_value=test_data) as mock_cache:
            # Test iterator method
            result = list(queryset.iterator())

            # Verify _cache_queryset was called
            mock_cache.assert_called_once()
            # Verify we get the expected data
            self.assertEqual(result, test_data)

    def test_iterator_with_chunk_size(self):
        """Test iterator method with chunk_size parameter."""
        queryset = CachedQuerySet(TestModel)

        test_data = ["item1", "item2", "item3", "item4"]
        with patch.object(queryset, "_cache_queryset", return_value=test_data) as mock_cache:
            # Test iterator with chunk_size (should still use caching)
            result = list(queryset.iterator(chunk_size=2))

            mock_cache.assert_called_once()
            self.assertEqual(result, test_data)

    @patch("django_cache_me.registry.invalidate_model_cache")
    def test_update_method(self, mock_invalidate):
        """Test update method invalidates cache."""
        queryset = CachedQuerySet(TestModel)

        # Mock the parent update method
        with patch.object(models.query.QuerySet, "update", return_value=3) as mock_update:
            # Call update
            result = queryset.update(name="updated_name", value=42)

            # Verify parent update was called with correct args
            mock_update.assert_called_once_with(name="updated_name", value=42)
            # Verify result is returned
            self.assertEqual(result, 3)
            # Verify cache invalidation was called
            mock_invalidate.assert_called_once_with(TestModel)

    @patch("django_cache_me.registry.invalidate_model_cache")
    def test_delete_method(self, mock_invalidate):
        """Test delete method invalidates cache."""
        queryset = CachedQuerySet(TestModel)

        # Mock the parent delete method
        with patch.object(models.query.QuerySet, "delete", return_value=(5, {"TestModel": 5})) as mock_delete:
            # Call delete
            result = queryset.delete()

            # Verify parent delete was called
            mock_delete.assert_called_once()
            # Verify result is returned
            self.assertEqual(result, (5, {"TestModel": 5}))
            # Verify cache invalidation was called
            mock_invalidate.assert_called_once_with(TestModel)

    def test_update_preserves_cache_settings(self):
        """Test update method preserves cache settings after operation."""
        queryset = CachedQuerySet(TestModel)
        queryset._use_cache = False
        queryset._is_permanent_cache = True

        with (
            patch.object(models.query.QuerySet, "update", return_value=1),
            patch("django_cache_me.registry.invalidate_model_cache"),
        ):
            queryset.update(name="test")

            # Verify cache settings are preserved
            self.assertFalse(queryset._use_cache)
            self.assertTrue(queryset._is_permanent_cache)

    def test_delete_preserves_cache_settings(self):
        """Test delete method preserves cache settings after operation."""
        queryset = CachedQuerySet(TestModel)
        queryset._use_cache = False
        queryset._is_permanent_cache = True

        with (
            patch.object(models.query.QuerySet, "delete", return_value=(1, {"TestModel": 1})),
            patch("django_cache_me.registry.invalidate_model_cache"),
        ):
            queryset.delete()

            # Verify cache settings are preserved
            self.assertFalse(queryset._use_cache)
            self.assertTrue(queryset._is_permanent_cache)

    def test_iterator_no_cache_mode(self):
        """Test iterator when caching is disabled."""
        queryset = CachedQuerySet(TestModel)
        queryset._use_cache = False

        test_data = ["item1", "item2"]
        with patch.object(queryset, "_cache_queryset", return_value=test_data) as mock_cache:
            # Iterator should still call _cache_queryset (which handles the no-cache logic)
            result = list(queryset.iterator())

            mock_cache.assert_called_once()
            self.assertEqual(result, test_data)

    def test_invalidate_cache_helper_method(self):
        """Test the _invalidate_cache helper method."""
        queryset = CachedQuerySet(TestModel)

        with patch("django_cache_me.registry.invalidate_model_cache") as mock_invalidate:
            queryset._invalidate_cache()

            mock_invalidate.assert_called_once_with(TestModel)

    def test_cache_queryset_with_disabled_caching(self):
        """Test _cache_queryset when caching is globally disabled."""
        queryset = CachedQuerySet(TestModel)

        with (
            patch("django_cache_me.registry.is_cache_enabled", return_value=False),
            patch.object(QuerySet, "iterator", return_value=iter(["item1", "item2"])) as mock_iterator,
        ):
            result = queryset._cache_queryset()
            mock_iterator.assert_called_once()
            # Should return list from iterator when caching is disabled
            self.assertEqual(result, ["item1", "item2"])

    def test_cache_queryset_no_options(self):
        """Test _cache_queryset when no cache options are available."""
        queryset = CachedQuerySet(TestModel)

        with (
            patch.object(queryset, "_get_cache_options", return_value=None),
            patch.object(QuerySet, "iterator", return_value=iter(["item1"])) as mock_iterator,
        ):
            result = queryset._cache_queryset()
            mock_iterator.assert_called_once()
            self.assertEqual(result, ["item1"])

    def test_cache_queryset_cache_hit(self):
        """Test _cache_queryset when cache hit occurs."""
        queryset = CachedQuerySet(TestModel)

        # Mock cache options
        options = MagicMock()
        options.cache_table = True
        options.cache_queryset = True

        cached_data = ["cached_item1", "cached_item2"]

        with (
            patch.object(queryset, "_get_cache_options", return_value=options),
            patch.object(queryset, "_is_all_query", return_value=True),
            patch.object(queryset, "_generate_cache_key", return_value="test_key"),
            patch("django_cache_me.registry.cache.get", return_value=cached_data),
            patch("django_cache_me.registry.cache_retrieval_log") as mock_log,
        ):
            result = queryset._cache_queryset()

            self.assertEqual(result, cached_data)
            mock_log.assert_called_once_with("test_key")

    def test_cache_queryset_cache_miss_and_set(self):
        """Test _cache_queryset when cache miss occurs and data is cached."""
        queryset = CachedQuerySet(TestModel)

        # Mock cache options
        options = MagicMock()
        options.cache_table = True
        options.timeout = 300

        fresh_data = ["fresh_item1", "fresh_item2"]

        with (
            patch.object(queryset, "_get_cache_options", return_value=options),
            patch.object(queryset, "_is_all_query", return_value=True),
            patch.object(queryset, "_generate_cache_key", return_value="test_key"),
            patch("django_cache_me.registry.cache.get", return_value=None),  # Cache miss
            patch.object(models.query.QuerySet, "iterator", return_value=iter(fresh_data)),
            patch("django_cache_me.registry.cache.set") as mock_set,
            patch("django_cache_me.registry.cache_miss_log") as mock_miss_log,
            patch("django_cache_me.registry.cache_hit_log") as mock_hit_log,
        ):
            result = queryset._cache_queryset()

            self.assertEqual(result, fresh_data)
            mock_miss_log.assert_called_once_with("test_key")
            mock_set.assert_called_once_with("test_key", fresh_data, 300)
            mock_hit_log.assert_called_once_with("test_key", 300)

    def test_get_timeout_with_options(self):
        """Test _get_timeout method with custom timeout in options."""
        queryset = CachedQuerySet(TestModel)

        options = MagicMock()
        options.timeout = 600

        with patch.object(queryset, "_get_cache_options", return_value=options):
            timeout = queryset._get_timeout()
            self.assertEqual(timeout, 600)

    def test_get_timeout_without_options(self):
        """Test _get_timeout method without options."""
        queryset = CachedQuerySet(TestModel)

        with (
            patch.object(queryset, "_get_cache_options", return_value=None),
            patch("django_cache_me.registry.settings") as mock_settings,
        ):
            mock_settings.DJANGO_CACHE_ME_TIMEOUT = 300
            timeout = queryset._get_timeout()
            # Should fall back to default
            self.assertIsNotNone(timeout)

    def test_should_cache_all_true(self):
        """Test _should_cache_all when cache_table is True."""
        queryset = CachedQuerySet(TestModel)

        options = MagicMock()
        options.cache_table = True

        with patch.object(queryset, "_get_cache_options", return_value=options):
            result = queryset._should_cache_all()
            self.assertTrue(result)

    def test_should_cache_all_false(self):
        """Test _should_cache_all when cache_table is False."""
        queryset = CachedQuerySet(TestModel)

        options = MagicMock()
        options.cache_table = False

        with patch.object(queryset, "_get_cache_options", return_value=options):
            result = queryset._should_cache_all()
            self.assertFalse(result)

    def test_should_cache_queryset_true(self):
        """Test _should_cache_queryset when cache_queryset is True."""
        queryset = CachedQuerySet(TestModel)

        options = MagicMock()
        options.cache_queryset = True

        with patch.object(queryset, "_get_cache_options", return_value=options):
            result = queryset._should_cache_queryset()
            self.assertTrue(result)

    def test_should_cache_queryset_false(self):
        """Test _should_cache_queryset when cache_queryset is False."""
        queryset = CachedQuerySet(TestModel)

        options = MagicMock()
        options.cache_queryset = False

        with patch.object(queryset, "_get_cache_options", return_value=options):
            result = queryset._should_cache_queryset()
            self.assertFalse(result)

    def test_is_all_query_true(self):
        """Test _is_all_query when query has no filters."""
        queryset = CachedQuerySet(TestModel)

        # Mock query object with no filters
        queryset.query = MagicMock()
        queryset.query.where = None
        queryset.query.extra = None
        queryset.query.having = None
        queryset.query.order_by = None
        queryset.query.group_by = None

        result = queryset._is_all_query()
        self.assertTrue(result)

    def test_is_all_query_false_with_where(self):
        """Test _is_all_query when query has where clause."""
        queryset = CachedQuerySet(TestModel)

        # Mock query object with where clause
        queryset.query = MagicMock()
        queryset.query.where = "some_filter"

        result = queryset._is_all_query()
        self.assertFalse(result)

    def test_generate_cache_key_table_type(self):
        """Test _generate_cache_key for table type."""
        queryset = CachedQuerySet(TestModel)

        key = queryset._generate_cache_key(query_type="table")
        self.assertIn("cache_me:table:", key)
        self.assertIn("django_cache_me.testmodel", key)

    def test_generate_cache_key_table_type_permanent(self):
        """Test _generate_cache_key for table type with permanent flag."""
        queryset = CachedQuerySet(TestModel)

        key = queryset._generate_cache_key(query_type="table", permanent=True)
        self.assertIn("cache_me:permanent:", key)
        self.assertIn("django_cache_me.testmodel", key)

    def test_invalidate_cache_method(self):
        """Test invalidate_cache method."""
        queryset = CachedQuerySet(TestModel)

        with patch("django_cache_me.registry.invalidate_model_cache") as mock_invalidate:
            queryset.invalidate_cache(invalidate_all=True)

            mock_invalidate.assert_called_once_with(TestModel, invalidate_permanent=True)

    def test_dunder_methods_use_caching(self):
        """Test that __iter__, __len__, and __getitem__ use caching."""
        queryset = CachedQuerySet(TestModel)
        test_data = ["item1", "item2", "item3"]

        with patch.object(queryset, "_cache_queryset", return_value=test_data) as mock_cache:
            # Test __iter__
            result_iter = list(iter(queryset))
            self.assertEqual(result_iter, test_data)

            # Test __len__
            result_len = len(queryset)
            self.assertEqual(result_len, 3)

            # Test __getitem__
            result_getitem = queryset[1]
            self.assertEqual(result_getitem, "item2")

            # Verify _cache_queryset was called exactly 3 times (once for each operation)
            self.assertEqual(mock_cache.call_count, 2)


class TestCachedManager(TestCase):
    """Test CachedManager functionality."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

    def test_manager_creates_cached_queryset(self):
        """Test that manager returns CachedQuerySet."""
        manager = CachedManager()
        manager.model = TestModel
        queryset = manager.get_queryset()
        self.assertIsInstance(queryset, CachedQuerySet)

    def test_no_cache_property(self):
        """Test no_cache property."""
        manager = CachedManager()
        manager.model = TestModel
        no_cache_qs = manager.no_cache
        self.assertIsInstance(no_cache_qs, CachedQuerySet)
        self.assertFalse(no_cache_qs._use_cache)

    def test_permanent_cache_property(self):
        """Test permanent_cache property."""
        manager = CachedManager()
        manager.model = TestModel
        perm_cache_qs = manager.permanent_cache
        self.assertIsInstance(perm_cache_qs, CachedQuerySet)
        self.assertTrue(perm_cache_qs._is_permanent_cache)

    @patch("django_cache_me.registry.invalidate_model_cache")
    def test_bulk_create_invalidates_cache(self, mock_invalidate):
        """Test bulk_create method invalidates cache."""
        manager = CachedManager()
        manager.model = TestModel

        test_objects = [MagicMock(), MagicMock()]

        with patch.object(models.Manager, "bulk_create", return_value=test_objects) as mock_bulk_create:
            result = manager.bulk_create(
                test_objects,
                batch_size=100,
                ignore_conflicts=True,
                update_conflicts=False,
                update_fields=["name"],
                unique_fields=["id"],
            )

            # Verify parent bulk_create was called with all arguments
            mock_bulk_create.assert_called_once_with(
                test_objects,
                batch_size=100,
                ignore_conflicts=True,
                update_conflicts=False,
                update_fields=["name"],
                unique_fields=["id"],
            )
            # Verify result is returned
            self.assertEqual(result, test_objects)
            # Verify cache invalidation was called
            mock_invalidate.assert_called_once_with(TestModel)

    @patch("django_cache_me.registry.invalidate_model_cache")
    def test_bulk_update_invalidates_cache(self, mock_invalidate):
        """Test bulk_update method invalidates cache."""
        manager = CachedManager()
        manager.model = TestModel

        test_objects = [MagicMock(), MagicMock()]
        test_fields = ["name", "value"]

        with patch.object(models.Manager, "bulk_update", return_value=2) as mock_bulk_update:
            result = manager.bulk_update(test_objects, test_fields, batch_size=50)

            # Verify parent bulk_update was called with correct arguments
            mock_bulk_update.assert_called_once_with(test_objects, test_fields, batch_size=50)
            # Verify result is returned
            self.assertEqual(result, 2)
            # Verify cache invalidation was called
            mock_invalidate.assert_called_once_with(TestModel)

    @patch("django_cache_me.registry.invalidate_model_cache")
    def test_invalidate_cache_method(self, mock_invalidate):
        """Test manager's invalidate_cache method."""
        manager = CachedManager()
        manager.model = TestModel

        # Test with invalidate_all=False
        manager.invalidate_cache(invalidate_all=False)
        mock_invalidate.assert_called_with(TestModel, invalidate_permanent=False)

        # Test with invalidate_all=True
        manager.invalidate_cache(invalidate_all=True)
        mock_invalidate.assert_called_with(TestModel, invalidate_permanent=True)

    def test_manager_invalidate_cache_helper(self):
        """Test the _invalidate_cache helper method."""
        manager = CachedManager()
        manager.model = TestModel

        with patch("django_cache_me.registry.invalidate_model_cache") as mock_invalidate:
            manager._invalidate_cache()
            mock_invalidate.assert_called_once_with(TestModel)


class TestCacheMeRegistry(TestCase):
    """Test CacheMeRegistry functionality."""

    def setUp(self):
        """Set up test registry."""
        self.registry = CacheMeRegistry()
        cache.clear()

    def test_register_model(self):
        """Test registering a model."""

        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        self.registry.register(TestModel, TestOptions)

        self.assertIn(TestModel, self.registry._registry)
        self.assertIsInstance(self.registry._registry[TestModel], CacheMeOptions)

    def test_get_options_for_unregistered_model(self):
        """Test getting options for unregistered model returns None."""
        options = self.registry.get_options(TestModel)
        self.assertIsNone(options)

    def test_get_options_for_registered_model(self):
        """Test getting options for registered model."""

        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        self.registry.register(TestModel, TestOptions)

        retrieved_options = self.registry.get_options(TestModel)
        self.assertTrue(retrieved_options.cache_table)

    def test_is_registered(self):
        """Test is_registered method."""
        self.assertFalse(self.registry.is_registered(TestModel))

        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)

        self.registry.register(TestModel, TestOptions)

        self.assertTrue(self.registry.is_registered(TestModel))

    def test_get_registered_models(self):
        """Test get_registered_models method."""
        initial_count = len(self.registry.get_registered_models())

        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)

        self.registry.register(TestModel, TestOptions)

        models = self.registry.get_registered_models()
        self.assertEqual(len(models), initial_count + 1)
        self.assertIn(TestModel, models)


class TestCacheMeRegisterDecorator(TestCase):
    """Test the cache_me_register decorator."""

    def test_decorator_registers_model(self):
        """Test that decorator registers model correctly."""
        # Clear registry
        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]

        @cache_me_register(TestModel)
        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True
                self.timeout = 600

        self.assertTrue(cache_me_registry.is_registered(TestModel))
        options = cache_me_registry.get_options(TestModel)
        self.assertTrue(options.cache_table)
        self.assertEqual(options.timeout, 600)

    def test_decorator_returns_class(self):
        """Test decorator returns the class unchanged."""

        @cache_me_register(TestModel)
        class SimpleOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        # Should work and return a class instance
        self.assertTrue(issubclass(SimpleOptions, CacheMeOptions))


@override_settings(DJANGO_CACHE_ME_DEBUG_MODE=True)
class TestDebugMode(TestCase):
    """Test debug mode functionality."""

    def setUp(self):
        """Set up test data."""
        cache.clear()

    def test_debug_logging(self):
        """Test that debug mode logs cache operations."""
        # Clear and register model
        if TestModel in cache_me_registry._registry:
            del cache_me_registry._registry[TestModel]

        class TestOptions(CacheMeOptions):
            def __init__(self, model_class):
                super().__init__(model_class)
                self.cache_table = True

        cache_me_registry.register(TestModel, TestOptions)

        # Test that we can create a queryset without errors
        queryset = CachedQuerySet(TestModel)
        cache_key = queryset._generate_cache_key()
        self.assertIsInstance(cache_key, str)


class TestCacheKeyGeneration(TestCase):
    """Test cache key generation with various scenarios."""

    def test_complex_query_cache_key(self):
        """Test cache key generation for complex queries."""
        queryset = CachedQuerySet(TestModel)

        # Test basic cache key generation
        key = queryset._generate_cache_key()
        self.assertIsInstance(key, str)
        self.assertIn("cache_me:queryset", key)

    def test_cache_key_consistency(self):
        """Test that cache keys are consistent."""
        queryset1 = CachedQuerySet(TestModel)
        queryset2 = CachedQuerySet(TestModel)

        # Keys should be similar for same model
        key1 = queryset1._generate_cache_key()
        key2 = queryset2._generate_cache_key()

        self.assertIsInstance(key1, str)
        self.assertIsInstance(key2, str)
