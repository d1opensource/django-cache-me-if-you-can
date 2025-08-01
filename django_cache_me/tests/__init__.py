"""
Test suite for django-cache-me

This package contains comprehensive tests for all modules in django-cache-me
to achieve 100% code coverage.

Test modules:
- test_registry: Tests for CacheMeRegistry, CachedQuerySet, CachedManager
- test_apps: Tests for Django app configuration
- test_autodiscover: Tests for autodiscovery functionality
- test_signals: Tests for cache invalidation signals
- test_settings: Tests for settings handling
- test_decorators: Tests for cache_me_register decorator
- test_integration: Integration tests for complete workflows
- models: Test models using django_fake_model

Usage:
    # Run all tests
    python -m pytest django_cache_me/tests/
    
    # Run with coverage
    python -m pytest --cov=django_cache_me django_cache_me/tests/
    
    # Run specific test module
    python -m pytest django_cache_me/tests/test_registry.py
"""
