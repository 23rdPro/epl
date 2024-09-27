from inspect import isasyncgen, iscoroutine
from functools import wraps
from typing import Any, Callable, Union
from django.core.cache import cache
from django.conf import settings


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
            # Prepare cache key
            func_args = {k: v for k, v in kwargs.items() if k != "page"}
            key = key_func(*args, **func_args) if callable(key_func) else key_func

            # Check if result is cached
            cached_data = cache.get(key)

            # If cached data is a coroutine, await it
            if iscoroutine(cached_data):
                cached_data = await cached_data

            # If cached data exists, return it
            if cached_data:
                return (item for item in cached_data) if use_generator else cached_data

            # Call the original function
            result = await func(*args, **kwargs)

            # Handle async generators if `use_generator` is True
            if use_generator and isasyncgen(result):
                result_list = [
                    item async for item in result
                ]  # Convert async generator to list
                cache.set(key, result_list, timeout=settings.CACHE_TIMEOUT)
                return (
                    item for item in result_list
                )  # Return generator from the cached list

            # Otherwise, handle normal async functions that return lists
            cache.set(key, result, timeout=settings.CACHE_TIMEOUT)
            return result

        return wrapper

    return decorator
