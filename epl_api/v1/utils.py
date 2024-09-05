from functools import wraps
from typing import Any, Callable, Union
from django.core.cache import cache

CACHE_TIMEOUT = 72 * 60 * 60  # 72 hours


def cache_result(key_func: Union[str, Callable[..., str]]):
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs) if callable(key_func) else key_func

            cached_data = await cache.get(key)
            if cached_data:
                return cached_data
            result = await func(*args, **kwargs)
            await cache.set(key, result, timeout=CACHE_TIMEOUT)
            return result

        return wrapper

    return decorator

