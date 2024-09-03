from epl_api.v1.helper import extract_player_stats, get_player_stats
from epl_api.v1.schema import PlayerStatsSchema, PlayerStatsSchemas
from fastapi import Request, status
from fastapi.responses import JSONResponse
from django.core.cache import cache

CACHE_TIMEOUT = 72 * 60 * 60  # 72 hours


async def get_root():
    return {"message": "Welcome to the EPL API"}


async def get_p_stats(p_name: str, request: Request):
    key = f"player_stats_{p_name.lower()}_{request.query_params}"
    cached_stats = cache.get(key)
    if cached_stats:
        print("cache hit>>>>>>>>>>>>>>>>>>>>>>>>")
        # to maintain return type, use PlayerStatsSchemas
        return PlayerStatsSchemas(players=PlayerStatsSchema(**cached_stats))

    stats = await get_player_stats(p_name)
    if not stats:
        return JSONResponse(
            {"error": "Failed to retrieve stats"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if len(stats) > 1:
        # Extract filters from the query parameters
        position_filter: str = request.get("position")
        nationality_filter: str = request.get("nationality")
        full_name_filter: str = request.get("player")

        filters = {
            "position": position_filter,
            "nationality": nationality_filter,
            "full_name": full_name_filter,
        }
        # Filter the results based on the additional criteria
        for key, item in enumerate(filters.items()):
            if item:
                stats = [
                    player for player in stats if player[key].lower() == item.lower()
                ]

    if len(stats) == 1:
        # retrieve one player stats directly
        player = stats[0]
        player_stats = await extract_player_stats(player["link"])
        stats = [PlayerStatsSchema(**player_stats)]
    # combined stats if filter still > 1 to perform more specific filters
    res = PlayerStatsSchemas(players=[PlayerStatsSchema(**player) for player in stats])
    cache.set(key, res, timeout=CACHE_TIMEOUT)
    return JSONResponse(content=res)
