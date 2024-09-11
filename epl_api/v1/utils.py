from asyncio import iscoroutine
from functools import wraps
import re
from typing import Any, Callable, Generator, Union, TypeVar as T, List
from django.core.cache import cache
from django.conf import settings


# def cache_result(key_func: Union[str, Callable[..., str]]):

#     def decorator(func: Callable[..., Any]):
#         @wraps(func)
#         async def wrapper(*args, **kwargs):
#             func_args = {k: v for k, v in kwargs.items() if k != "page"}
#             key = key_func(*args, **func_args) if callable(key_func) else key_func
#             cached_data = cache.get(key)
#             if iscoroutine(cached_data):
#                 cached_data = await cached_data
#             if cached_data:
#                 return cached_data
#             result = await func(*args, **kwargs)
#             cache.set(key, result, timeout=settings.CACHE_TIMEOUT)
#             return result

#         return wrapper

#     return decorator


async def onetrust_accept_cookie(page):
    try:
        # Wait for the consent modal button if it's there
        await page.wait_for_selector('button:has-text("Accept All Cookies")')
        await page.click('button:has-text("Accept All Cookies")')
        print("Cookie consent accepted.")
    except Exception as e:
        print(f"No consent modal or button found: {e}")


def cache_result(key_func: Union[str, Callable[..., str]], use_generator: bool = True):
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_args = {k: v for k, v in kwargs.items() if k != "page"}
            key = key_func(*args, **func_args) if callable(key_func) else key_func

            # Check if result is cached
            cached_data = cache.get(key)
            if iscoroutine(cached_data):
                cached_data = await cached_data
            if cached_data:
                return cached_data

            # Get the result from the function
            result = await func(*args, **kwargs)

            # If the result is a generator and caching is enabled, convert to a list
            if use_generator:
                if isinstance(result, Generator):
                    result = list(result)

            # Cache the result (will always be a list, as generators can't be pickled)
            cache.set(key, result, timeout=settings.CACHE_TIMEOUT)

            # Return a generator or list based on `use_generator` flag
            return (item for item in result) if use_generator else result

        return wrapper

    return decorator
