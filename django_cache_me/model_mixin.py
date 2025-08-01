"""
Model mixin for automatic cache invalidation in django-cache-me-if-you-can.

This module provides the CacheMeInvalidationMixin class that can be used to automatically
invalidate cache when model instances are saved or deleted.

Example usage:
    class MyModel(CacheMeInvalidationMixin, models.Model):
        name = models.CharField(max_length=100)

Recommended approach:
    # In your apps.py or wherever you configure caching
    from django_cache_me.registry import cache_me_registry
    from myapp.models import MyModel

    cache_me_registry.register(MyModel)

The mixin approach is kept for backward compatibility but may be removed in future versions.
"""

from .signals import invalidate_model_cache


class CacheMeInvalidationMixin:
    """
    Mixin to automatically invalidate cache when model instances are saved or deleted.

    This version uses safer method calls that don't interfere with Django's QuerySet
    _result_cache mechanism.
    """

    def save(self, *args, **kwargs):
        """
        Save the model instance and automatically invalidate related cache entries.

        This method wraps the standard Django model save() method to provide automatic
        cache invalidation. After successfully saving the model instance, it triggers
        cache invalidation for all cached querysets related to this model.

        Args:
            *args: Variable length argument list passed to the parent save() method.
            **kwargs: Arbitrary keyword arguments passed to the parent save() method.

        Returns:
            The result from the parent save() method.

        Note:
            Cache invalidation occurs after the save operation completes successfully.
            If the save operation fails, cache invalidation will not be triggered.

        """
        # Call the original save method first
        result = super().save(*args, **kwargs)
        # Then invalidate cache for this model
        invalidate_model_cache(self.__class__)
        return result

    def delete(self, *args, **kwargs):
        """
        Delete the model instance and automatically invalidate related cache entries.

        This method wraps the standard Django model delete() method to provide automatic
        cache invalidation. After successfully deleting the model instance, it triggers
        cache invalidation for all cached querysets related to this model.

        Args:
            *args: Variable length argument list passed to the parent delete() method.
            **kwargs: Arbitrary keyword arguments passed to the parent delete() method.

        Returns:
            The result from the parent delete() method.

        Note:
            Cache invalidation occurs after the delete operation completes successfully.
            If the delete operation fails, cache invalidation will not be triggered.

        """
        # Call the original delete method first
        result = super().delete(*args, **kwargs)
        # Then invalidate cache for this model
        invalidate_model_cache(self.__class__)
        return result
