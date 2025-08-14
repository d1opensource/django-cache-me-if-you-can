# Django Cache Me If You Can
![image_final.jpeg](image_final.jpeg)
A powerful Django library for intelligent queryset caching with automatic invalidation, permanent cache options, and comprehensive debug logging.

## Features

✨ **Smart Queryset Caching** - Automatically cache Django querysets based on SQL queries

🔄 **Automatic Cache Invalidation** - Clear cache when models are saved, updated, or deleted

🏛️ **Permanent Cache** - Cache that persists through model changes until timeout

🎯 **Granular Control** - Configure caching per model with flexible options

🐛 **Debug Mode** - Comprehensive logging for cache hits, misses, and invalidations

🚀 **Zero Configuration** - Works out of the box with sensible defaults

🔧 **Multiple Cache Backends** - Supports Redis, Memcached, and database cache

📈 **Performance Focused** - Minimal overhead with maximum speed gains

⚙️ **Optional Async Invalidation** - Offload cache invalidation to Celery with on-commit scheduling and optional pre-warming

## Quick Start

### Installation

```bash
# Install from GitHub
pip install git+https://github.com/d1opensource/django-cache-me-if-you-can.git

# Or install in development mode
pip install -e git+https://github.com/d1opensource/django-cache-me-if-you-can.git#egg=django-cache-me-if-you-can
```

### Basic Setup

1. Add to your `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ... your other apps
    'django_cache_me',
]
```

2. Configure your cache backend:

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}

# Optional: Configure django-cache-me settings
DJANGO_CACHE_ME_TIMEOUT = 600  # Default cache timeout (10 minutes)
DJANGO_CACHE_ME_DEBUG_MODE = True  # Enable debug logging
DJANGO_CACHE_ME_ON = True  # Enable/disable caching globally
```

3. Create a `cache_me.py` file in your app:

```python
# myapp/cache_me.py
from django_cache_me import cache_me_register, CacheMeOptions
from .models import Product


@cache_me_register(Product)
class ProductCacheMeOptions(CacheMeOptions):
    cache_table = True     # Cache .all() (entire table, it must be used with caution) -> Default False
    cache_queryset = True   # Cache filtered queries only -> Default True
    timeout = 1800         # Override default timeout to 30 minutes
```

That's it! Your models now have intelligent caching.

## Usage Examples

### Basic Caching

```python
# These queries are automatically cached
recent_products = Product.objects.filter(
    created_at__gte=timezone.now() - timedelta(days=7)
)  # Cached

# Cache is automatically invalidated when data changes
user = Product.objects.get(id=1)
user.name = "New Name"
user.save()  # Cache for User model is cleared
```

### Permanent Cache

Use permanent cache for data that shouldn't be invalidated on model changes. This is helpful for small querysets that require to be run over and over again like within chained processes.

```python
# Permanent cache - survives model saves/updates
hair_products = Product.objects.permanent_cache.filter(category__name='hair')

hair_product = Product.objects.get(name='Shampoo')
hair_product.name = "New Shampoo Name"
hair_product.save()  # Cache for Product model is cleared, but permanent cache remains

Product.objects.invalidate_cache(invalidate_all=True)  # Clears permanent cache too
```

### Manual Cache Control

```python
# Bypass cache entirely
active_products = Product.objects.no_cache.filter(is_active=True)

# Manual cache invalidation
Product.objects.invalidate_cache()                    # Clear regular cache only
Product.objects.invalidate_cache(invalidate_all=True) # Clear all cache (including permanent)

# From queryset
Product.objects.filter(name="test").invalidate_cache()
```

## Configuration Options

### Global Settings

```python
# settings.py

# Enable/disable caching globally (default: True)
DJANGO_CACHE_ME_ON = True

# Enable debug logging (default: False)
DJANGO_CACHE_ME_DEBUG_MODE = False

# Default cache timeout in seconds (default: 300)
DJANGO_CACHE_ME_TIMEOUT = 300

# Optional async invalidation via Celery (all default to disabled/safe)
# Enable background invalidation (default: False)
DJANGO_CACHE_ME_ASYNC_ENABLED = False

# Enqueue after successful DB commit (default: True)
DJANGO_CACHE_ME_ASYNC_ON_COMMIT = True

# Optional Celery queue routing (default: None)
DJANGO_CACHE_ME_CELERY_QUEUE = None

# Pre-warm cache after invalidation (default: False)
DJANGO_CACHE_ME_WARM_ON_INVALIDATE = False

# Optional per-model warmers mapping (default: {})
# Format: {"app_label.ModelName": ["dotted.path.to.callable", ...]}
DJANGO_CACHE_ME_WARMERS = {}
```

### Per-Model Configuration

```python
# app/cache_me.py
@cache_me_register(MyModel)
class MyModelCacheMeOptions(CacheMeOptions):
    # Cache entire table when .all() is called (default: False)
    cache_table = True

    # Cache querysets with filters/annotations (default: True)
    cache_queryset = True

    # Custom timeout for this model (default: uses DJANGO_CACHE_ME_TIMEOUT)
    timeout = 1800  # 30 minutes
```

## Caching Behavior Matrix

| Configuration | `.all()` | `.filter()` | `.exclude()` | Other QuerySets |
|---------------|----------|-------------|--------------|-----------------|
| `cache_table=False, cache_queryset=False` | ❌ | ❌ | ❌ | ❌ |
| `cache_table=True, cache_queryset=False` | ✅ | ❌ | ❌ | ❌ |
| `cache_table=False, cache_queryset=True` | ✅ | ✅ | ✅ | ✅ |
| `cache_table=True, cache_queryset=True` | ✅ (table) | ✅ (queryset) | ✅ (queryset) | ✅ (queryset) |

## Cache Invalidation

### Automatic Invalidation

Cache is automatically cleared when:

```python
# Individual operations
Product.save()                    # Clears Product cache
Product.delete()                  # Clears Product cache

# Bulk operations
Product.objects.bulk_create([...])           # Clears Product cache
Product.objects.bulk_update([...], ['name']) # Clears Product cache
Product.objects.filter(...).update(...)      # Clears Product cache
Product.objects.filter(...).delete()         # Clears Product cache
```

### Manual Invalidation

```python
# Clear all cache for a model
Product.objects.invalidate_cache()

# Clear all cache including permanent cache
Product.objects.invalidate_cache(invalidate_all=True)

# From a queryset
Product.objects.filter(is_active=True).invalidate_cache()
```

## Async Invalidation (optional)

You can offload cache invalidation to a Celery worker to keep write paths snappy.

- Toggle on with settings (safe defaults keep current sync behavior):

```python
DJANGO_CACHE_ME_ASYNC_ENABLED = True
DJANGO_CACHE_ME_ASYNC_ON_COMMIT = True          # recommend enqueuing after commit
DJANGO_CACHE_ME_CELERY_QUEUE = "cache_me"       # optional, route to a specific queue
DJANGO_CACHE_ME_WARM_ON_INVALIDATE = True       # optional, pre-warm cache
```

- Warmers: configure per-model callables to evaluate and populate cache after invalidation.

```python
# settings.py
DJANGO_CACHE_ME_WARMERS = {
    "myapp.Product": [
        "myapp.cache_warmers.product_all",           # returns a QuerySet
        "myapp.cache_warmers.product_popular_filters",
    ]
}
```

Example warmer:

```python
# myapp/cache_warmers.py
from .models import Product

def product_all():
    return Product.objects.all()  # evaluating this warms the table cache if enabled

def product_popular_filters():
    return Product.objects.filter(is_active=True)
```

Behavior and fallbacks:
- If Celery is available, we enqueue invalidate_model_cache_task; if not, we gracefully run synchronously.
- When DJANGO_CACHE_ME_ASYNC_ON_COMMIT is True, we enqueue only after the DB transaction commits.
- Warmers run only when DJANGO_CACHE_ME_WARM_ON_INVALIDATE is True (and for table warm-up, when the model has cache_table=True).

## Debug Mode

Enable debug logging to see exactly what's happening:

```python
# settings.py
DJANGO_CACHE_ME_DEBUG_MODE = True
```

Output examples:
```
[django-cache-me] Cache miss for key 'cache_me:queryset:myapp.product:a1b2c3d4' - hitting database
[django-cache-me] Cached queryset with key 'cache_me:queryset:myapp.product:a1b2c3d4' for 300 seconds
[django-cache-me] Cache invalidated for model 'myapp.product' (regular cache)
[django-cache-me] Cache invalidated for model 'myapp.product' (permanent and regular cache)
```

## Advanced Usage

### Using with Custom Managers

The library works with custom managers through mixin inheritance:

```python
class CustomProductManager(models.Manager):
    def active_products(self):
        return self.filter(is_active=True)

class Product(models.Model):
    objects = CustomProductManager()
    # ... fields

# After registration, you get both:
Product.objects.active_users()              # Custom method
Product.objects.filter(...).cache()         # Caching capabilities
Product.objects.no_cache.active_users()     # Bypass cache
```

### Cache Keys

The library generates cache keys based on:
- Model app label and name
- SQL query hash for querysets
- Cache type (regular vs permanent)

Key patterns:
```
cache_me:table:myapp.user                           # Table cache
cache_me:queryset:myapp.table:md5hash                # Queryset cache
cache_me:permanent_table:myapp.table                 # Permanent table cache
cache_me:permanent_queryset:myapp.table:md5hash      # Permanent queryset cache
```

### Cache Invalidation Mixin

For models that need custom invalidation logic:

```python
from django_cache_me.signals import CacheMeInvalidationMixin


class Product(models.Model, CacheMeInvalidationMixin):
    name = models.CharField(max_length=100)
    # Cache automatically invalidated on save/delete
```

## Performance Tips

1. **Use permanent cache** for relatively static data
2. **Enable table cache** for small, frequently accessed tables
3. **Use Redis** for best performance with pattern-based key deletion
4. **Monitor cache hit rates** in debug mode during development
5. **Set appropriate timeouts** based on data change frequency
6. **Enable async invalidation** in write-heavy flows to keep responses fast

## Cache Backend Compatibility

| Backend | Regular Cache | Permanent Cache | Pattern Deletion | Recommended |
|---------|---------------|-----------------|------------------|-------------|
| Redis (django-redis) | ✅ | ✅ | ✅ | ⭐⭐⭐⭐⭐ |
| Memcached | ✅ | ✅ | ❌ | ⭐⭐⭐⭐ |
| Database Cache | ✅ | ✅ | ❌ | ⭐⭐⭐ |
| Dummy Cache | ✅ | ✅ | ❌ | ⭐ (dev only) |

## Troubleshooting

### Common Issues

**Cache not working:**
- Check `DJANGO_CACHE_ME_ON = True`
- Verify cache backend is configured
- Ensure model is registered in `cache_me.py`

**Cache not invalidating:**
- Verify signals are connected (automatic on app startup)
- Check if using custom save methods that bypass signals
- Use manual invalidation for custom update logic

**Async invalidation not enqueuing:**
- Ensure `DJANGO_CACHE_ME_ASYNC_ENABLED = True`
- Make sure Celery is running if you expect background execution
- With no Celery, invalidation falls back to sync (by design)

**Performance issues:**
- Enable debug mode to check cache hit rates
- Consider using permanent cache for static data
- Verify cache backend performance (Redis recommended)

### Debug Commands

```python
# Check registered models
from django_cache_me.registry import cache_me_registry
print(cache_me_registry.get_registered_models())

# Check model options
options = cache_me_registry.get_options(Product)
print(f"Table cache: {options.cache_table}")
print(f"Queryset cache: {options.cache_queryset}")
```

## Requirements

- Django 3.2+
- Python 3.8+
- A configured cache backend (Redis recommended)
- Optional: Celery if you want background invalidation (the library runs without it)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **GitHub**: https://github.com/d1opensource/django-cache-me-if-you-can
- **Issues**: https://github.com/d1opensource/django-cache-me-if-you-can/issues
- **Documentation**: This README

---

*Cache me if you can* 🚀
