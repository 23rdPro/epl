from epl_api.v1.helper import extract_player_stats, get_player_stats
from epl_api.v1.schema import PlayerStatsSchema, PlayerStatsSchemas
from fastapi import Request, status
from fastapi.responses import JSONResponse


async def get_root():
    return {"message": "Welcome to the EPL API"}


async def get_p_stats(p_name: str, request: Request):
    stats = await get_player_stats(p_name)
    if not stats:
        return JSONResponse(
            {"error": "Failed to retrieve stats"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if len(stats) > 1:
        # Extract filters from the query parameters
        position_filter: str = request.GET.get("position")
        nationality_filter: str = request.GET.get("nationality")
        full_name_filter: str = request.GET.get("player")

        # Filter the results based on the additional criteria
        if position_filter:
            stats = [
                player
                for player in stats
                if player["position"].lower() == position_filter.lower()
            ]
        if nationality_filter:
            stats = [
                player
                for player in stats
                if player["nationality"].lower() == nationality_filter.lower()
            ]
        if full_name_filter:
            stats = [p for p in stats if p["player"].lower() == full_name_filter.lower()]

    if len(stats) == 1:
        # retrieve one player stats directly
        player = stats[0]
        player_stats = await extract_player_stats(player["link"])
        stats = [PlayerStatsSchema(**player_stats)]
    # combined if filter still > 1 to perform more specific filters
    return PlayerStatsSchemas(players=[PlayerStatsSchema(**player) for player in stats])

