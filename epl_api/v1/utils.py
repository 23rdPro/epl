from functools import wraps
from django.core.cache import cache
from django.conf import settings
from epl_api.v1.schema import PlayerStatsSchema, PlayerStatsSchemas


def cache_result(key_func, timeout=settings.CACHE_TIMEOUT):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs)

            cached_data = cache.get(key)
            if cached_data:
                print("cache hit>>>>>>>>>>>>>>>>>>>>>>>>")
                return cached_data
                # return PlayerStatsSchemas(players=[PlayerStatsSchema(**cached_data)])
            result = await func(*args, **kwargs)
            cache.set(key, result, timeout=settings.CACHE_TIMEOUT)
            return result

        return wrapper
    return decorator
