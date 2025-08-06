import hashlib

from django.conf import settings
from django.core.cache import cache
from django.db import models
from django.db.models.query import QuerySet

from .settings import (
    cache_disabled,
    cache_hit_log,
    cache_miss_log,
    cache_retrieval_log,
    empty_queryset_log,
    is_cache_enabled,
)
from .signals import invalidate_model_cache


class CachedQuerySet(QuerySet):
    """Custom QuerySet that handles caching based on model options."""

    def __init__(self, *args, **kwargs):
        self._use_cache = True
        self._is_permanent_cache = False
        super().__init__(*args, **kwargs)

    def _get_cache_options(self):
        """Get caching options for this model."""
        return cache_me_registry.get_options(self.model)

    @property
    def is_permanent_cache(self):
        """Check if this queryset uses permanent caching."""
        return self._is_permanent_cache

    def _generate_cache_key(self, query_type="queryset"):
        """Generate cache key based on query."""
        model_name = f"{self.model._meta.app_label}.{self.model._meta.model_name}"

        if query_type == "table":
            # For .all() when cache_table=True
            cache_type = "permanent" if self.is_permanent_cache else "table"
            return f"cache_me:{cache_type}:{model_name}"

        # For complex querysets - hash the SQL query
        try:
            query_str = str(self.query)
        except Exception:
            # Handle cases where query compilation fails (e.g., EmptyResultSet)
            # Use a fallback cache key based on the query object's attributes
            query_str = f"query_id_{id(self.query)}"

        query_hash = hashlib.md5(query_str.encode("utf-8")).hexdigest()
        cache_type = "permanent" if self.is_permanent_cache else "queryset"
        return f"cache_me:{cache_type}:{model_name}:{query_hash}"

    def _get_timeout(self):
        """Get cache timeout for this model."""
        options = self._get_cache_options()
        if options and options.timeout:
            return options.timeout
        return getattr(settings, "DJANGO_CACHE_ME_TIMEOUT", 300)

    def _should_cache_all(self):
        """Check if .all() should be cached."""
        options = self._get_cache_options()
        return options and options.cache_table

    def _should_cache_queryset(self):
        """Check if queryset should be cached."""
        options = self._get_cache_options()
        return options and options.cache_queryset

    def _is_all_query(self):
        """Check if this is a simple .all() query."""
        # Simple check: if no filters, excludes, or complex operations
        # Use getattr with default False to handle different Django versions
        return (
            not self.query.where
            and not getattr(self.query, "extra", None)
            and not getattr(self.query, "having", None)
            and not getattr(self.query, "order_by", None)
            and not getattr(self.query, "group_by", None)
        )

    def _cache_queryset(self):
        """Cache the queryset results."""
        if not self._use_cache or not is_cache_enabled():
            cache_disabled()
            return list(super().iterator())

        options = self._get_cache_options()
        if not options:
            return list(super().iterator())

        is_all_query = self._is_all_query()

        # Determine if we should cache this query
        should_cache = False
        cache_key = None

        if is_all_query and self._should_cache_all():
            # Cache .all() when cache_table=True
            should_cache = True
            cache_key = self._generate_cache_key("table")
        elif not is_all_query and self._should_cache_queryset():
            # Cache filtered queries when cache_queryset=True
            should_cache = True
            cache_key = self._generate_cache_key("queryset")
        elif is_all_query and self._should_cache_queryset() and not self._should_cache_all():
            # Cache .all() when cache_queryset=True but cache_table=False
            should_cache = True
            cache_key = self._generate_cache_key("queryset")

        if not should_cache:
            return list(super().iterator())

        # Try to get from cache
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            cache_retrieval_log(cache_key)
            return cached_result

        # Cache miss - execute query and cache results
        cache_miss_log(cache_key)
        result = list(super().iterator())

        # Skip caching if the result is empty
        if not result:
            empty_queryset_log(cache_key)
            return result

        timeout = self._get_timeout()
        cache.set(cache_key, result, timeout)
        cache_hit_log(cache_key, timeout)
        return result

    def iterator(self, chunk_size=2000):
        """Override iterator to use caching."""
        yield from self._cache_queryset()

    def __iter__(self):
        """Override iteration to use caching."""
        return iter(self._cache_queryset())

    def __len__(self):
        """Override len to use cached results if available."""
        # Ensure _result_cache is set for Django's internal QuerySet methods
        if not hasattr(self, "_result_cache") or self._result_cache is None:
            self._result_cache = self._cache_queryset()
        return len(self._result_cache)

    def __getitem__(self, k):
        """Override getitem to work with cached results."""
        # Ensure _result_cache is set for Django's internal QuerySet methods
        if not hasattr(self, "_result_cache") or self._result_cache is None:
            self._result_cache = self._cache_queryset()
        return self._result_cache[k]

    def _result_cache_or_evaluate(self):
        """
        Helper method to properly handle result cache for Django's QuerySet methods.
        This ensures compatibility with Django's internal QuerySet behavior.
        """
        # If we already have a _result_cache, use it
        if hasattr(self, "_result_cache") and self._result_cache is not None:
            return self._result_cache

        # Otherwise, evaluate the queryset and set the _result_cache
        cached_results = self._cache_queryset()
        self._result_cache = cached_results
        return cached_results

    def _fetch_all(self):
        """Override _fetch_all to use our caching mechanism."""
        if self._result_cache is None:
            self._result_cache = self._cache_queryset()

    def count(self):
        """Override count to use cached results when possible."""
        # For simple queries, we can use the cached results to get count
        try:
            cached_results = self._cache_queryset()
            return len(cached_results)
        except Exception:
            # Fallback to normal count if caching fails
            return super().count()

    def exists(self):
        """Override exists to use cached results when possible."""
        try:
            cached_results = self._cache_queryset()
            return len(cached_results) > 0
        except Exception:
            # Fallback to normal exists if caching fails
            return super().exists()

    def _clone(self):
        """Override _clone to preserve the _use_cache and _is_permanent_cache settings."""
        clone = super()._clone()
        clone._use_cache = getattr(self, "_use_cache", True)
        clone._is_permanent_cache = getattr(self, "_is_permanent_cache", False)
        return clone

    def no_cache(self):
        """Return a copy of this queryset that won't use cache."""
        qs = self._clone()
        qs._use_cache = False
        return qs

    def permanent_cache(self):
        """Return a copy of this queryset that uses permanent caching."""
        qs = self._clone()
        qs._is_permanent_cache = True
        return qs

    def update(self, **kwargs):
        """Override update to invalidate cache after bulk updates."""
        result = super().update(**kwargs)
        # Invalidate cache after update
        self._invalidate_cache()
        return result

    def delete(self):
        """Override delete to invalidate cache after bulk deletes."""
        # For delete operations, we need to bypass caching to avoid EmptyResultSet issues
        # Create a non-cached version of this queryset for the actual delete operation
        non_cached_qs = super(CachedQuerySet, self)._clone()  # noqa: UP008
        non_cached_qs.__class__ = QuerySet  # Use Django's base QuerySet class

        try:
            result = non_cached_qs.delete()
            # Invalidate cache after successful delete
            self._invalidate_cache()
        except Exception:
            pass
            # If delete fails, don't invalidate cache
        else:
            return result

    def _invalidate_cache(self):
        """Helper method to invalidate cache for this model."""
        invalidate_model_cache(self.model)

    def invalidate_cache(self, invalidate_all=False):
        """
        Invalidate cache for this model.

        Args:
            invalidate_all (bool): If True, also invalidates permanent cache.
                                 If False, only invalidates regular cache.

        """
        invalidate_model_cache(self.model, invalidate_permanent=invalidate_all)


class PermanentCachedQuerySet(CachedQuerySet):
    """
    QuerySet that uses permanent caching - cache is not invalidated on model saves/updates.
    Only expires by timeout or explicit invalidation.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_permanent_cache = True

    def _cache_queryset(self):
        """Cache the queryset results with permanent cache keys."""
        # Check if caching is globally disabled
        if not is_cache_enabled():
            cache_disabled()
            return list(super(CachedQuerySet, self).iterator())

        if not self._use_cache:
            return list(super(CachedQuerySet, self).iterator())

        options = self._get_cache_options()
        if not options:
            return list(super(CachedQuerySet, self).iterator())

        is_all_query = self._is_all_query()

        # Determine if we should cache this query (same logic but with permanent=True)
        should_cache = False
        cache_key = None

        if is_all_query and self._should_cache_all():
            # Cache .all() when cache_table=True
            should_cache = True
            cache_key = self._generate_cache_key("table")
        elif not is_all_query and self._should_cache_queryset():
            # Cache filtered queries when cache_queryset=True
            should_cache = True
            cache_key = self._generate_cache_key("queryset")
        elif is_all_query and self._should_cache_queryset() and not self._should_cache_all():
            # Cache .all() when cache_queryset=True but cache_table=False
            should_cache = True
            cache_key = self._generate_cache_key("queryset")

        if not should_cache:
            return list(super(CachedQuerySet, self).iterator())

        # Try to get from cache
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            cache_retrieval_log(cache_key)
            return cached_result

        # Cache miss - execute query and cache results
        cache_miss_log(cache_key)
        result = list(super(CachedQuerySet, self).iterator())
        timeout = self._get_timeout()
        cache.set(cache_key, result, timeout)
        cache_hit_log(cache_key, timeout)
        return result

    def update(self, **kwargs):
        """Override update - permanent cache doesn't get invalidated automatically."""
        return super(CachedQuerySet, self).update(**kwargs)

    def delete(self):
        """Override delete - permanent cache doesn't get invalidated automatically."""
        return super(CachedQuerySet, self).delete()


class CachedManager(models.Manager):
    """Custom Manager that returns CachedQuerySet instances."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cached_queryset_class = None

    def _get_cached_queryset_class(self):
        """Create a dynamic queryset class that combines CachedQuerySet with the original queryset."""
        if self._cached_queryset_class is not None:
            return self._cached_queryset_class

        # Get the original queryset class from the parent manager classes
        original_queryset_class = None

        # Look through the MRO to find the original get_queryset method
        # Skip CachedManager and any previously created cached classes
        for base_class in self.__class__.__mro__:
            if (
                base_class != CachedManager
                and hasattr(base_class, "get_queryset")
                and not base_class.__name__.startswith("Cached")
            ):
                try:
                    # Create a temporary instance to get the original queryset class
                    temp_manager = base_class()
                    temp_manager.model = self.model
                    temp_manager._db = self._db
                    original_qs = temp_manager.get_queryset()
                    original_queryset_class = original_qs.__class__
                    # Make sure we don't get a Cached class
                    if not original_queryset_class.__name__.startswith("Cached"):
                        break
                except Exception:
                    continue

        # Fallback to Django's default QuerySet
        if original_queryset_class is None:
            from django.db.models.query import QuerySet

            original_queryset_class = QuerySet

        # Only create a new class if the original is not already CachedQuerySet or a Cached variant
        if original_queryset_class == CachedQuerySet or original_queryset_class.__name__.startswith("Cached"):
            self._cached_queryset_class = CachedQuerySet
        else:
            # Create a dynamic class that inherits from both CachedQuerySet and the original queryset
            cached_queryset_name = f"Cached{original_queryset_class.__name__}"

            try:
                # Try the normal approach first
                self._cached_queryset_class = type(
                    cached_queryset_name,
                    (CachedQuerySet, original_queryset_class),
                    {
                        "__module__": original_queryset_class.__module__,
                    },
                )
            except TypeError as e:
                if "consistent method resolution order" in str(e):
                    # MRO conflict - use composition approach instead of inheritance
                    # Create a class that inherits from CachedQuerySet and delegates missing methods
                    class CachedQuerySetWithDelegation(CachedQuerySet):
                        def __init__(self, *args, **kwargs):
                            super().__init__(*args, **kwargs)
                            # Store the original queryset class for delegation
                            self._original_queryset_class = original_queryset_class

                        def __getattr__(self, name):
                            # If the method doesn't exist on CachedQuerySet, try to get it from the original
                            if hasattr(self._original_queryset_class, name):
                                original_method = getattr(self._original_queryset_class, name)
                                if callable(original_method):
                                    # Create a wrapper that applies the method to a clone of this queryset
                                    def method_wrapper(*args, **kwargs):
                                        # Create an instance of the original queryset class with our data
                                        original_qs = self._original_queryset_class(self.model, using=self._db)
                                        # Copy our query state
                                        original_qs.query = self.query.clone()
                                        # Call the original method
                                        result = original_method(original_qs, *args, **kwargs)
                                        # If the result is a QuerySet, wrap it back in our cached version
                                        if isinstance(result, QuerySet):
                                            cached_result = self.__class__(self.model, using=self._db)
                                            cached_result.query = result.query.clone()
                                            cached_result._use_cache = getattr(self, "_use_cache", True)
                                            cached_result._is_permanent_cache = getattr(
                                                self, "_is_permanent_cache", False
                                            )
                                            return cached_result
                                        return result

                                    return method_wrapper
                                return original_method
                            msg = f"'{self._original_queryset_class.__name__}' object has no attribute '{name}'"
                            raise AttributeError(msg)

                    # Give it a proper name
                    CachedQuerySetWithDelegation.__name__ = cached_queryset_name
                    CachedQuerySetWithDelegation.__qualname__ = cached_queryset_name
                    self._cached_queryset_class = CachedQuerySetWithDelegation
                else:
                    # Different error, re-raise
                    raise

        return self._cached_queryset_class

    def get_queryset(self):
        cached_queryset_class = self._get_cached_queryset_class()
        return cached_queryset_class(self.model, using=self._db)

    @property
    def no_cache(self):
        """Return a manager that doesn't use cache."""
        return self.get_queryset().no_cache()

    @property
    def permanent_cache(self):
        """Return a manager that uses permanent caching."""
        return PermanentCachedQuerySet(self.model, using=self._db)

    def invalidate_cache(self, invalidate_all=False):
        """
        Invalidate cache for this model.

        Args:
            invalidate_all (bool): If True, also invalidates permanent cache.
                                 If False, only invalidates regular cache.

        """
        invalidate_model_cache(self.model, invalidate_permanent=invalidate_all)

    def bulk_create(
        self,
        objs,
        batch_size=None,
        ignore_conflicts=False,
        update_conflicts=False,
        update_fields=None,
        unique_fields=None,
    ):
        """Override bulk_create to invalidate cache after bulk operations."""
        result = super().bulk_create(
            objs,
            batch_size=batch_size,
            ignore_conflicts=ignore_conflicts,
            update_conflicts=update_conflicts,
            update_fields=update_fields,
            unique_fields=unique_fields,
        )
        # Invalidate cache after bulk create
        self._invalidate_cache()
        return result

    def bulk_delete(self, objs, fields, batch_size=None):
        result = super().bulk_update(objs, fields, batch_size=batch_size)
        # Invalidate cache after bulk delete
        self._invalidate_cache()
        return result

    def bulk_update(self, objs, fields, batch_size=None):
        """Override bulk_update to invalidate cache after bulk operations."""
        result = super().bulk_update(objs, fields, batch_size=batch_size)
        # Invalidate cache after bulk update
        self._invalidate_cache()
        return result

    def _invalidate_cache(self):
        """Helper method to invalidate cache for this model."""
        invalidate_model_cache(self.model)


class CacheMeOptions:  # noqa: B903
    """Base configuration class for model caching options."""

    cache_table = False  # Cache entire table when .all() is executed
    cache_queryset = True  # Cache querysets with complex filtering
    timeout = None  # Custom timeout for this model (uses default if None)

    def __init__(self, model_class: type[models.Model]):
        self.model = model_class


class CacheMeRegistry:
    """Registry to store model caching configurations."""

    def __init__(self):
        self._registry: dict[type[models.Model], CacheMeOptions] = {}
        self._cache = cache

    def register(self, model_class: type[models.Model], options_class: type[CacheMeOptions] | None = None):
        """Register a model with caching options."""
        if not is_cache_enabled():
            cache_disabled()
            return
        if options_class is None:
            options_class = CacheMeOptions

        options = options_class(model_class)
        self._registry[model_class] = options

        # Patch the model's manager to enable caching
        self._patch_model_manager(model_class, options)

    def _patch_model_manager(self, model_class: type[models.Model], options: CacheMeOptions):
        """Patch the model's default manager to add caching capabilities and inject invalidation behavior."""
        # Handle cases where the default manager might not be properly set up (e.g., abstract models)
        if not hasattr(model_class, "_default_manager") or model_class._default_manager is None:
            # For abstract models or models without proper managers, just store the options
            # The actual manager patching will happen when the model is properly instantiated
            return

        # Inject cache invalidation methods into the model
        self._inject_cache_invalidation(model_class)

        original_manager_class = model_class._default_manager.__class__

        # Additional safety check for None manager class
        if original_manager_class is None:
            # Fallback to django's default Manager
            from django.db import models as django_models

            original_manager_class = django_models.Manager

        # Check if we've already patched this manager class
        cache_manager_name = f"Cached{original_manager_class.__name__}"

        # Create a new manager class that inherits from both CachedManager and original manager
        cached_manager_class = type(
            cache_manager_name,
            (CachedManager, original_manager_class),
            {
                "__module__": original_manager_class.__module__,
            },
        )

        # Create an instance of the new mixed manager
        cached_manager = cached_manager_class()

        # Copy attributes from the original manager more carefully
        original_manager = model_class._default_manager
        for attr_name in dir(original_manager):
            if (
                not attr_name.startswith("_")
                and hasattr(original_manager, attr_name)
                and attr_name not in {"model", "db"}
            ):  # Skip attributes we'll set manually
                try:
                    attr_value = getattr(original_manager, attr_name)
                    # Only copy non-callable attributes that aren't properties
                    if not callable(attr_value) and not isinstance(
                        getattr(original_manager_class, attr_name, None), property
                    ):
                        setattr(cached_manager, attr_name, attr_value)
                except (AttributeError, TypeError):
                    # Skip attributes that can't be copied (properties, descriptors, etc.)
                    continue

        # Set the essential manager attributes manually
        cached_manager.model = model_class
        cached_manager._db = original_manager._db

        # Store reference to original manager for potential restoration
        if not hasattr(model_class, "_original_manager_instance"):
            model_class._original_manager_instance = original_manager

        # Use Django's proper way to replace the manager
        # We need to modify the _meta.managers list and replace the objects attribute
        model_class.objects = cached_manager

        # Replace in the _meta.managers list - handle different Django versions and manager structures
        try:
            if hasattr(model_class._meta, "managers"):
                managers = model_class._meta.managers
                # Check if managers is iterable and contains tuples
                if hasattr(managers, "__iter__"):
                    # Try to iterate through managers
                    for i, manager_item in enumerate(managers):
                        try:
                            # Handle different manager structures
                            if isinstance(manager_item, tuple) and len(manager_item) == 2:
                                name, manager = manager_item
                                if name == "objects" or manager is original_manager:
                                    model_class._meta.managers[i] = (name, cached_manager)
                                    break
                            elif hasattr(manager_item, "name"):
                                # Some manager structures have a name attribute
                                if manager_item.name == "objects" or manager_item is original_manager:
                                    # Replace the manager instance
                                    model_class._meta.managers[i] = cached_manager
                                    break
                        except (TypeError, AttributeError):
                            # Skip problematic manager entries
                            continue
        except (AttributeError, TypeError):
            # If we can't modify _meta.managers, that's okay - the objects attribute replacement is the main thing
            pass

    def _inject_cache_invalidation(self, model_class: type[models.Model]):
        """
        Inject cache invalidation methods into the model class.

        This method safely wraps the model's save() and delete() methods with cache invalidation
        logic, eliminating the need to manually inherit from Model mixin.
        """
        # Check if we've already injected to avoid duplicate wrapping
        if hasattr(model_class, "_cache_me_invalidation_injected"):
            return

        # Store original methods
        original_save = model_class.save
        original_delete = model_class.delete

        def save_with_invalidation(self, *args, **kwargs):
            """Save method wrapped with cache invalidation."""
            result = original_save(self, *args, **kwargs)
            # Invalidate cache after successful save
            invalidate_model_cache(self.__class__)
            return result

        def delete_with_invalidation(self, *args, **kwargs):
            """Delete method wrapped with cache invalidation."""
            result = original_delete(self, *args, **kwargs)
            # Invalidate cache after successful delete
            invalidate_model_cache(self.__class__)
            return result

        def invalidate_cache_classmethod(cls, invalidate_all=False):
            """
            Class method to manually invalidate cache for this model.

            Args:
                cls: The model class to invalidate cache for.
                invalidate_all (bool): If True, also invalidates permanent cache.
                                     If False, only invalidates regular cache.

            """
            invalidate_model_cache(cls, invalidate_permanent=invalidate_all)

        # Replace the methods with wrapped versions
        model_class.save = save_with_invalidation
        model_class.delete = delete_with_invalidation

        # Add class method for manual cache invalidation
        model_class.invalidate_cache = classmethod(invalidate_cache_classmethod)

        # Mark that we've injected the functionality
        model_class._cache_me_invalidation_injected = True

    def get_options(self, model_class: type[models.Model]) -> CacheMeOptions:
        """Get caching options for a model."""
        return self._registry.get(model_class)

    def is_registered(self, model_class: type[models.Model]) -> bool:
        """Check if a model is registered for caching."""
        return model_class in self._registry

    def get_registered_models(self):
        """Get all registered models."""
        return list(self._registry.keys())


# Global registry instance
cache_me_registry = CacheMeRegistry()


def cache_me_register(model_class: type[models.Model]):
    """
    Decorator to register a model with caching options.

    Usage:
        @cache_me_register(Account)
        class AccountCacheMeOption(CacheMeOptions):
            cache_table = True
            cache_queryset = True
    """

    def decorator(options_class: type[CacheMeOptions]):
        cache_me_registry.register(model_class, options_class)
        return options_class

    return decorator
