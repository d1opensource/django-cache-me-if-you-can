from django.core.cache import cache
from django.db.models.signals import post_delete, post_save

from .settings import cache_invalidation_log


def invalidate_model_cache(model_class, invalidate_permanent=False):
    """
    Invalidate all cached data for a specific model.

    Args:
        model_class: The model class to invalidate cache for
        invalidate_permanent (bool): If True, also invalidates permanent cache

    """
    from .registry import cache_me_registry

    if not cache_me_registry.is_registered(model_class):
        return

    model_name = f"{model_class._meta.app_label}.{model_class._meta.model_name}"

    # Log cache invalidation
    cache_invalidation_log(model_name, invalidate_permanent)

    # Always invalidate regular cache
    # Invalidate table cache (for cache_table=True)
    table_cache_key = f"cache_me:table:{model_name}"
    cache.delete(table_cache_key)

    # Invalidate simple query cache
    simple_cache_key = f"cache_me:queryset:{model_name}:simple"
    cache.delete(simple_cache_key)

    # Invalidate permanent cache if requested
    if invalidate_permanent:
        permanent_table_cache_key = f"cache_me:permanent:{model_name}"
        cache.delete(permanent_table_cache_key)

        permanent_simple_cache_key = f"cache_me:permanent:{model_name}:simple"
        cache.delete(permanent_simple_cache_key)

    # Get tracked cache keys and invalidate them
    tracking_key = f"cache_me:keys:{model_name}"
    tracked_keys = cache.get(tracking_key, set())

    if isinstance(tracked_keys, set) and tracked_keys:
        # Delete all tracked cache keys
        for cache_key in tracked_keys:
            # Only delete regular cache keys unless invalidate_permanent is True
            if invalidate_permanent or not cache_key.startswith("cache_me:permanent"):
                cache.delete(cache_key)

        # Clean up tracking key if invalidating all
        if invalidate_permanent:
            cache.delete(tracking_key)
        else:
            # Remove only non-permanent keys from tracking
            remaining_keys = {key for key in tracked_keys if key.startswith("cache_me:permanent")}
            if remaining_keys:
                cache.set(tracking_key, remaining_keys, 86400)
            else:
                cache.delete(tracking_key)

    # For queryset caches, we need a way to track and invalidate them
    try:
        # Try to delete pattern-based keys if using Redis with django-redis
        if hasattr(cache, "delete_pattern"):
            # Delete regular queryset cache
            cache.delete_pattern(f"cache_me:queryset:{model_name}:*")

            # Delete permanent queryset cache if requested
            if invalidate_permanent:
                cache.delete_pattern(f"cache_me:permanent:{model_name}:*")
        else:
            # Fallback: we could maintain a set of cache keys, but for now we'll clear all
            # In a real implementation, you might want to use cache versioning or key tracking
            pass
    except Exception:
        # If pattern deletion fails, we could implement key tracking
        pass


def auto_invalidate_cache(sender, **kwargs):
    """Signal handler to automatically invalidate cache when models are saved/deleted."""
    invalidate_model_cache(sender)


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
