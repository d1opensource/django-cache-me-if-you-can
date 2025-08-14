"""
Celery tasks for django-cache-me (optional, safe if Celery is not installed).

This module defines a task to invalidate a model's cache and optionally warm it.
If Celery is not available, a lightweight shim is used so .delay() still works
synchronously, keeping the library dependency-free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type-checking only
    from collections.abc import Callable

try:  # pragma: no cover - small import path that is hard to unit-test reliably
    from celery import shared_task
except Exception:  # pragma: no cover - we provide a shim when celery isn't available

    def shared_task(*_d_args: object, **_d_kwargs: object) -> Callable[[Callable[..., object]], Callable[..., object]]:
        """
        A minimal shim for celery.shared_task when Celery isn't installed.

        It attaches .delay/.apply_async attributes that call the function synchronously.
        """

        def decorator(func: Callable[..., object]) -> Callable[..., object]:
            def delay(*args: object, **kwargs: object) -> object:
                return func(*args, **kwargs)

            def apply_async(*args: object, **kwargs: object) -> object:
                return func(*args, **kwargs)

            func.delay = delay
            func.apply_async = apply_async
            return func

        return decorator


@shared_task(bind=True, ignore_result=True)
def invalidate_model_cache_task(
    self,
    app_label: str,
    model_name: str,
    invalidate_permanent: bool = False,
    warm: bool = False,
    **kwargs: object,
) -> None:
    """
    Celery task to invalidate cache for a given model and optionally warm it.

    Args:
        self: The Celery task instance (provided when bind=True).
        app_label: Django app label of the model.
        model_name: Model class name.
        invalidate_permanent: If True, also invalidates permanent cache.
        warm: If True, runs warmers after invalidation.
        **kwargs: Extra task options ignored by the shim/worker.

    """
    try:
        from django.apps import apps

        model_class = apps.get_model(app_label, model_name)
        # Import lazily to avoid cycles
        from .signals import _run_warmers_for_model, invalidate_model_cache

        invalidate_model_cache(model_class, invalidate_permanent=invalidate_permanent)
        if warm:
            _run_warmers_for_model(model_class)
    except Exception as e:  # pragma: no cover - defensive logging only
        from .settings import cache_generic_message

        cache_generic_message(f"invalidate_model_cache_task failed for {app_label}.{model_name}: {e}")
