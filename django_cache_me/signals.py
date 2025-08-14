from contextlib import suppress

from django.core.cache.backends.dummy import DummyCache
from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.utils.module_loading import import_string

from .settings import cache_disabled, cache_generic_message, cache_invalidation_log, get_setting, is_cache_enabled


def invalidate_model_cache(model_class, invalidate_permanent=False):
    """
    Invalidate all cached data for a specific model.

    Args:
        model_class: The model class to invalidate cache for
        invalidate_permanent (bool): If True, also invalidates permanent cache

    """
    if not is_cache_enabled():
        cache_disabled()
        return

    from django.core.cache import caches

    from .registry import cache_me_registry

    # Get fresh cache instance to respect override_settings
    current_cache = caches["default"]

    # Check if cache is DummyCache - skip invalidation for dummy cache
    if isinstance(current_cache, DummyCache):
        cache_generic_message("DummyCache detected - cache invalidation not needed")
        return

    if not cache_me_registry.is_registered(model_class):
        return

    model_name = f"{model_class._meta.app_label}.{model_class._meta.model_name}"

    # Always invalidate regular cache
    # Invalidate table cache (for cache_table=True)
    table_cache_key = f"*cache_me:table:{model_name}"
    current_cache.delete(table_cache_key)
    cache_invalidation_log(table_cache_key)

    # Invalidate queryset caches - need to find and delete keys with pattern
    queryset_pattern = f"*cache_me:queryset:{model_name}:*"
    _delete_cache_keys_by_pattern(queryset_pattern, current_cache=current_cache)

    # Invalidate permanent cache if requested
    if invalidate_permanent:
        permanent_table_cache_key = f"*cache_me:permanent:{model_name}"
        current_cache.delete(permanent_table_cache_key)
        cache_invalidation_log(permanent_table_cache_key)

        # Invalidate permanent queryset caches
        permanent_queryset_pattern = f"*cache_me:permanent:{model_name}:*"
        _delete_cache_keys_by_pattern(permanent_queryset_pattern, current_cache=current_cache)


def _run_warmers_for_model(model_class):
    """
    Optionally pre-warm cache for a model after invalidation.

    Obeys settings:
    - DJANGO_CACHE_ME_WARMERS: mapping of "app_label.ModelName" -> list of dotted callables
      that return QuerySet(s) to be evaluated.
    - If the registered options have cache_table=True, evaluates objects.all().
    """
    try:
        from .registry import cache_me_registry

        options = cache_me_registry.get_options(model_class)
    except Exception:
        options = None

    # Warm the table cache if configured
    try:
        if options and getattr(options, "cache_table", False):
            list(model_class.objects.all())
    except Exception as e:  # pragma: no cover - defensive logging only
        cache_generic_message(f"Error warming table cache for {model_class}: {e}")

    # Run custom warmers
    warmers_map = get_setting("DJANGO_CACHE_ME_WARMERS", {}) or {}
    key = f"{model_class._meta.app_label}.{model_class.__name__}"
    warmer_paths = warmers_map.get(key, [])
    for path in warmer_paths:
        try:
            func = import_string(path)
            qs = func()
            # If it returns a queryset or iterable, evaluate to trigger caching
            with suppress(TypeError):
                list(qs)
        except Exception as e:  # pragma: no cover - defensive logging only
            cache_generic_message(f"Warmer '{path}' failed: {e}")


def schedule_invalidation(model_class, invalidate_permanent=False, warm=None):
    """
    Schedule (or execute) cache invalidation for a model.

    When DJANGO_CACHE_ME_ASYNC_ENABLED is True, will try to enqueue a Celery task.
    Falls back to synchronous invalidation if Celery is unavailable or enqueue fails.

    Args:
        model_class: The model class to invalidate.
        invalidate_permanent: If True, also invalidates permanent cache.
        warm: Optional boolean. If None, uses DJANGO_CACHE_ME_WARM_ON_INVALIDATE.

    """
    if not is_cache_enabled():
        cache_disabled()
        return

    if warm is None:
        warm = bool(get_setting("DJANGO_CACHE_ME_WARM_ON_INVALIDATE", False))

    async_enabled = bool(get_setting("DJANGO_CACHE_ME_ASYNC_ENABLED", False))
    on_commit = bool(get_setting("DJANGO_CACHE_ME_ASYNC_ON_COMMIT", True))

    def _sync_path():
        invalidate_model_cache(model_class, invalidate_permanent=invalidate_permanent)
        if warm:
            _run_warmers_for_model(model_class)

    if not async_enabled:
        _sync_path()
        return

    def enqueue():
        try:
            # Import lazily to avoid hard dependency and circular imports
            from .tasks import invalidate_model_cache_task

            app_label = model_class._meta.app_label
            model_name = model_class.__name__
            queue = get_setting("DJANGO_CACHE_ME_CELERY_QUEUE", None)
            apply_kwargs = {"queue": queue} if queue else {}
            # In tests without Celery, our task decorator shim provides .delay
            invalidate_model_cache_task.delay(app_label, model_name, invalidate_permanent, warm, **apply_kwargs)
        except Exception as e:
            cache_generic_message(f"Async enqueue failed, falling back to sync: {e}")
            _sync_path()

    if on_commit:
        try:
            transaction.on_commit(enqueue)
        except Exception:
            enqueue()
    else:
        enqueue()


def auto_invalidate_cache(sender, **kwargs):
    """Signal handler to automatically invalidate cache when models are saved/deleted."""
    if sender is None:
        return
    schedule_invalidation(sender)


def enable_auto_invalidation(model_class):
    """
    Enable automatic cache invalidation for a model.

    Usage:
        enable_auto_invalidation(MyModel)
    """
    post_save.connect(auto_invalidate_cache, sender=model_class)
    post_delete.connect(auto_invalidate_cache, sender=model_class)


def setup_cache_invalidation():
    """
    Set up cache invalidation for all registered models.
    This is called automatically when the app is ready.
    """
    from .registry import cache_me_registry

    for model_class in cache_me_registry.get_registered_models():
        enable_auto_invalidation(model_class)


def invalidate_all_caches(invalidate_permanent=False):
    """
    Invalidate all caches across all registered models.

    This is a helper function to clear all cached data for all models
    that have been registered with django-cache-me.

    Args:
        invalidate_permanent (bool): If True, also invalidates permanent cache.
                                   If False, only invalidates regular cache.

    Usage:
        from django_cache_me.signals import invalidate_all_caches

        # Invalidate all regular caches
        invalidate_all_caches()

        # Invalidate all caches including permanent ones
        invalidate_all_caches(invalidate_permanent=True)

    """
    if not is_cache_enabled():
        cache_disabled()
        return
    from .registry import cache_me_registry

    registered_models = cache_me_registry.get_registered_models()

    if not registered_models:
        cache_generic_message("No registered models found for cache invalidation")
        return

    cache_generic_message(f"Invalidating caches for {len(registered_models)} registered models")

    for model_class in registered_models:
        try:
            # Go through the scheduler so async mode can be honored
            schedule_invalidation(model_class, invalidate_permanent=invalidate_permanent)
        except Exception as e:
            # Log the error but continue with other models
            cache_generic_message(f"Error invalidating cache for {model_class}: {e}")

    cache_generic_message("Finished invalidating all caches")


def _delete_cache_keys_by_pattern(pattern, current_cache):
    """
    Delete cache keys matching a pattern.

    This function handles different cache backends:
    - Redis: Uses SCAN command to find and delete keys
    - django-redis: Uses delete_pattern method
    - Other backends: Logs that pattern deletion isn't supported
    """
    # Get a fresh cache instance to ensure we're using the current settings

    try:
        # First, try django-redis specific approach
        if hasattr(current_cache, "delete_pattern"):
            # django-redis backend supports delete_pattern
            deleted_count = current_cache.delete_pattern(pattern)
            cache_generic_message(f"Deleted {deleted_count} keys matching pattern '{pattern}' using delete_pattern")
            return

        # Try Redis-specific approach through _cache.get_client
        if hasattr(current_cache, "_cache") and hasattr(current_cache._cache, "get_client"):
            # Redis backend
            try:
                client = current_cache._cache.get_client(write=True)
                if hasattr(client, "scan_iter"):
                    # Use Redis SCAN to find matching keys
                    keys_to_delete = []

                    # Handle key prefixes that Django might add
                    search_pattern = pattern
                    if hasattr(current_cache, "key_prefix") and current_cache.key_prefix:
                        # If there's a key prefix, we need to include it in our search
                        search_pattern = f"{current_cache.key_prefix}:*{pattern}"

                    for key in client.scan_iter(match=search_pattern):
                        # Redis returns bytes, decode to string
                        if isinstance(key, bytes):
                            key = key.decode("utf-8")
                        keys_to_delete.append(key)

                    if keys_to_delete:
                        client.delete(*keys_to_delete)
                        cache_generic_message(
                            f"Deleted {len(keys_to_delete)} keys matching pattern '{pattern}' using Redis SCAN"
                        )
                    else:
                        cache_generic_message(f"No keys found matching pattern '{pattern}' using Redis SCAN")
                    return
            except Exception as e:
                cache_generic_message(f"Error accessing Redis client: {e}")

        # Try accessing Redis client directly if available
        if hasattr(current_cache, "scan_iter"):
            try:
                keys_to_delete = []
                for key in current_cache.scan_iter(match=pattern):
                    keys_to_delete.append(key)

                if keys_to_delete:
                    for key in keys_to_delete:
                        current_cache.delete(key)
                    cache_generic_message(
                        f"Deleted {len(keys_to_delete)} keys matching pattern '{pattern}' using direct scan_iter"
                    )
                else:
                    cache_generic_message(f"No keys found matching pattern '{pattern}' using direct scan_iter")
            except Exception as e:
                cache_generic_message(f"Error using direct scan_iter: {e}")
            else:
                return

        # Fallback for other backends (like LocMemCache, DummyCache, MemcachedCache, etc.)
        # These don't support pattern deletion, so we just log the attempt
        cache_backend_name = current_cache.__class__.__name__
        cache_generic_message(
            f"Cache backend '{cache_backend_name}' doesn't support pattern deletion for pattern '{pattern}'"
        )

    except Exception as e:
        cache_generic_message(f"Error deleting cache keys with pattern '{pattern}': {e}")
