from asyncio import iscoroutine
from functools import wraps
import re
from typing import Any, Callable, Union, TypeVar as T, List
from django.core.cache import cache
from django.conf import settings


def cache_result(key_func: Union[str, Callable[..., str]]):
    def decorator(func: Callable[..., Any]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            func_args = {k: v for k, v in kwargs.items() if k != "page"}
            key = key_func(*args, **func_args) if callable(key_func) else key_func
            cached_data = cache.get(key)
            if iscoroutine(cached_data):
                cached_data = await cached_data
            if cached_data:
                return cached_data
            result = await func(*args, **kwargs)
            cache.set(key, result, timeout=settings.CACHE_TIMEOUT)
            return result

        return wrapper

    return decorator


def extract_team_data(row):
    def clean_form(text):
        results = re.findall(r"(?:\b|\\n)([WLD])(?:\b|\\n)", text)
        # only the last 6 results
        return "".join(results[-6:])

    clean_pos = lambda text: (
        re.search(r"\d+", text).group(0) if text and re.search(r"\d+", text) else None
    )

    cells = row.find_all("td")
    if len(cells) < 10:
        return None
    team_data = {
        "position": clean_pos(cells[0].text.strip()) if len(cells) > 0 else None,
        "club": (
            cells[1].find("span", class_="league-table__team-name--long").text.strip()
            if len(cells) > 1
            else None
        ),
        "played": cells[2].text.strip() if len(cells) > 2 else None,
        "won": cells[3].text.strip() if len(cells) > 3 else None,
        "drawn": cells[4].text.strip() if len(cells) > 4 else None,
        "lost": cells[5].text.strip() if len(cells) > 5 else None,
        "gf": cells[6].text.strip() if len(cells) > 6 else None,  # Goals For
        "ga": cells[7].text.strip() if len(cells) > 7 else None,  # Goals Against
        "gd": cells[8].text.strip() if len(cells) > 8 else None,  # Goal Difference
        "points": cells[9].text.strip() if len(cells) > 9 else None,
        "form": clean_form(cells[10].text.strip()) if len(cells) > 10 else None,
    }
    return team_data


# Extract and format the league table
def format_league_table(rows: List[T]):
    league_table = []
    for row in rows:

        team_data = extract_team_data(row)
        if team_data:
            league_table.append(team_data)

    return league_table


async def onetrust_accept_cookie(page):
    try:
        # Wait for the consent modal button if it's there
        await page.wait_for_selector('button:has-text("Accept All Cookies")')
        await page.click('button:has-text("Accept All Cookies")')
        print("Cookie consent accepted.")
    except Exception as e:
        print(f"No consent modal or button found: {e}")
