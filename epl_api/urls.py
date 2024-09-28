from fastapi import APIRouter, status
from epl_api.views import (
    aggregate_club_stats,
    get_fixtures,
    get_results,
    get_root,
    get_p_stats,
    get_table,
)

router = APIRouter()

router.get("/", status_code=status.HTTP_200_OK)(get_root)
router.get(
    "/stats/{p_name}",
    status_code=status.HTTP_200_OK,
    summary="get player stats",
    tags=["pl-stats"],
)(get_p_stats)
router.get(
    "/table",
    status_code=status.HTTP_200_OK,
    summary="get epl table",
    tags=["epl-table"],
)(get_table)
router.get(
    "/fixtures", status_code=status.HTTP_200_OK, summary="", tags=["epl-fixtures"]
)(get_fixtures)
router.get(
    "/results", status_code=status.HTTP_200_OK, summary="", tags=["epl-results"]
)(get_results)
router.get(
    "/clubstats/{c_name}",
    status_code=200,
    summary="get club stats",
    tags=["club-stats"],
)(aggregate_club_stats)
router.get("")

urlpatterns = []
