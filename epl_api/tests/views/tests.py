import datetime
import json
from fastapi import Request
from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from dateutil import parser

from epl_api.v1.schemas import (
    AttackSchema,
    DefenceSchema,
    DisciplineSchema,
    FixtureSchema,
    PlayerStatsSchema,
    ResultSchema,
    TeamPlaySchema,
)
from epl_api.views import get_fixtures, get_p_stats, get_results, get_table
from epl_api.asgi import app


client = TestClient(app)


def test_get_root():
    response = client.get("/api/v1")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the EPL API"}


@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
@patch("epl_api.views.async_playwright")
async def test_get_results(mock_playwright, mock_cache):
    # simulate a cache miss
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()

    # Mock Playwright browser
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value.__aenter__.return_value = (
        mock_browser
    )
    mock_browser.new_page.return_value = mock_page

    # Mock HTML
    _html = """
    <ul class="matchFixtureContainer">
        <li class="match-fixture" data-home="Team A" data-away="Team B">
            <div class="match-fixture__score">2 - 1</div>
        </li>
        <li class="match-fixture" data-home="Team C" data-away="Team D">
            <div class="match-fixture__score">0 - 0</div>
        </li>
    </ul>
    """
    mock_page.content.return_value = _html

    # Mocking BeautifulSoup and schema classes
    with patch("epl_api.views.BeautifulSoup") as mock_soup, patch(
        "epl_api.v1.schema.ResultSchema"
    ) as mock_result_schema:

        mock_soup.return_value.select.return_value = [
            {
                "data-home": "Team A",
                "data-away": "Team B",
                "select_one": lambda _: Mock(text="2 - 1"),
            },
            {
                "data-home": "Team C",
                "data-away": "Team D",
                "select_one": lambda _: Mock(text="0 - 0"),
            },
        ]

        # Mock the schemas
        mock_result_schema.side_effect = lambda home, away, score: ResultSchema(
            home=home, away=away, score=score
        )

        # Call the view
        response = await get_results()

        # Assertions
        expected_results = [
            {"home": "Team A", "away": "Team B", "score": "2 - 1"},
            {"home": "Team C", "away": "Team D", "score": "0 - 0"},
        ]
        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        assert response_data == expected_results

        # Verify Playwright interaction TODO cannot yet verify this
        # mock_page.goto.assert_called_once_with("https://www.premierleague.com")
        # mock_page.click.assert_any_call('a[href="/results"][data-link-index="2"]')
        # mock_page.wait_for_selector.assert_called_with("li.match-fixture")

        # Verify cache set call with correct data
        mock_cache.set.assert_called_once()


@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
async def test_get_results_cache_hit(mock_cache):
    # Simulate a cache hit
    cached_data = {"results": [{"home": "Team A", "away": "Team B", "score": "2 - 1"}]}
    mock_cache.get = AsyncMock(return_value=cached_data)

    # Call the view method
    response = await get_results()

    # Assertions
    assert response == cached_data

    # Verify that no Playwright interaction occurs on cache hit
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_not_called()


@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
@patch("epl_api.views.async_playwright")
async def test_get_fixtures(mock_playwright, mock_cache):
    # Simulate a cache miss
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()

    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value.__aenter__.return_value = (
        mock_browser
    )
    mock_browser.new_page.return_value = mock_page

    # Mock HTML
    _html = """
    <ul class="matchFixtureContainer">
        <li class="match-fixture" data-home="Team A" data-away="Team B">
            <time datetime="2024-09-10T15:00:00Z"></time>
        </li>
        <li class="match-fixture" data-home="Team C" data-away="Team D">
            <time datetime="2024-09-11T17:00:00Z"></time>
        </li>
    </ul>
    """
    mock_page.content.return_value = _html

    # Mock BeautifulSoup and schema classes
    with patch("epl_api.views.BeautifulSoup") as mock_soup, patch(
        "epl_api.v1.schema.FixtureSchema"
    ) as mock_fixture_schema:

        d1 = datetime.datetime.strptime("2024-09-10T15:00:00", "%Y-%m-%dT%H:%M:%S")
        d2 = datetime.datetime.strptime("2024-09-11T17:00:00", "%Y-%m-%dT%H:%M:%S")

        formatted_d1 = d1.strftime("%Y-%m %H:%M")
        formatted_d2 = d2.strftime("%Y-%m %H:%M")

        mock_soup.return_value.select.return_value = [
            {
                "data-home": "Team A",
                "data-away": "Team B",
                "time":  formatted_d1
            },
            {
                "data-home": "Team C",
                "data-away": "Team D",
                "time": formatted_d2
            },
        ]
        mock_fixture_schema.side_effect = lambda home, away, time: FixtureSchema(
            home=home, away=away, time=time
        )

        # Call the view method
        response = await get_fixtures()

        # Assertions
        expected_fixtures = {'fixtures': [
            {"home": "Team A", "away": "Team B", "time": formatted_d1},
            {"home": "Team C", "away": "Team D", "time": formatted_d2},
        ]}
        assert response.status_code == 200
        response_data = json.loads(response.body.decode("utf-8"))
        
        print()
        print(response_data)
        print()
        print(expected_fixtures)
        assert response_data == expected_fixtures

        # Verify Playwright interactions todo
        # mock_page.goto.assert_called_once_with("https://www.premierleague.com")
        # mock_page.click.assert_any_call('a[href="/fixtures"][data-link-index="1"]')
        # mock_page.wait_for_selector.assert_called_with("li.match-fixture")

        # Verify cache set call with correct data
        mock_cache.set.assert_called_once()


@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
async def test_get_fixtures_cache_hit(mock_cache):
    # Simulate a cache hit
    cached_data = {
        "fixtures": [
            {"home": "Team A", "away": "Team B", "time": "2024-09-10T15:00:00Z"}
        ]
    }
    mock_cache.get = AsyncMock(return_value=cached_data)

    # Call the view method
    response = await get_fixtures()

    # Assertions
    assert response == cached_data

    # Verify that no Playwright interaction occurs on cache hit
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_not_called()


@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
@patch("epl_api.views.async_playwright")
async def test_get_table(mock_playwright, mock_cache):
    pytest.skip("Todo")
    
    # Simulate a cache miss
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()

    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value.__aenter__.return_value = (
        mock_browser
    )
    mock_browser.new_page.return_value = mock_page

    # Mock HTML
    _html = """
    <div id="mainContent">
        <div class="league-table__all-tables-container allTablesContainer">
            <table>
                <tbody>
                    <tr>
                        <td>1</td>
                        <td>Team A</td>
                        <td>5</td>
                        <td>3</td>
                        <td>1</td>
                        <td>1</td>
                        <td>10</td>
                        <td>5</td>
                        <td>+5</td>
                        <td>10</td>
                        <td>WWDWL</td>
                    </tr>
                    <tr>
                        <td>2</td>
                        <td>Team B</td>
                        <td>5</td>
                        <td>3</td>
                        <td>1</td>
                        <td>1</td>
                        <td>8</td>
                        <td>4</td>
                        <td>+4</td>
                        <td>10</td>
                        <td>LWWDW</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    """
    mock_page.content.return_value = _html

    # Mock BeautifulSoup
    with patch("epl_api.views.BeautifulSoup") as mock_soup:
        # Setup BeautifulSoup mock
        mock_soup.return_value.select_one.return_value.find_all.return_value = [
            MagicMock(
                find_all=lambda _: [
                    MagicMock(text="1"),
                    MagicMock(text="Team A"),
                    MagicMock(text="5"),
                    MagicMock(text="3"),
                    MagicMock(text="1"),
                    MagicMock(text="1"),
                    MagicMock(text="10"),
                    MagicMock(text="5"),
                    MagicMock(text="+5"),
                    MagicMock(text="10"),
                    MagicMock(text="WWDWL"),
                ]
            ),
            MagicMock(
                find_all=lambda _: [
                    MagicMock(text="2"),
                    MagicMock(text="Team B"),
                    MagicMock(text="5"),
                    MagicMock(text="3"),
                    MagicMock(text="1"),
                    MagicMock(text="1"),
                    MagicMock(text="8"),
                    MagicMock(text="4"),
                    MagicMock(text="+4"),
                    MagicMock(text="10"),
                    MagicMock(text="LWWDW"),
                ]
            ),
        ]

        # Call the view method
        response = await get_table()

        # Assertions
        expected_table = [
            {
                "position": "1",
                "club": "Team A",
                "played": "5",
                "won": "3",
                "drawn": "1",
                "lost": "1",
                "gf": "10",
                "ga": "5",
                "gd": "+5",
                "points": "10",
                "form": "WWDWL",
            },
            {
                "position": "2",
                "club": "Team B",
                "played": "5",
                "won": "3",
                "drawn": "1",
                "lost": "1",
                "gf": "8",
                "ga": "4",
                "gd": "+4",
                "points": "10",
                "form": "LWWDW",
            },
        ]
        assert response == expected_table

        # Verify Playwright
        # mock_page.goto.assert_called_once_with("https://www.premierleague.com")
        # mock_page.click.assert_any_call('a[data-link-index="3"][role="menuitem"]')
        # mock_page.wait_for_selector.assert_any_call(
        #     'li[data-tab-index="0"][data-text="First Team"]'
        # )
        # mock_page.wait_for_selector.assert_called_with(
        #     "#mainContent div.league-table__all-tables-container.allTablesContainer table tbody"
        # )

        # Verify cache set call with correct data
        mock_cache.set.assert_called_once_with(
            "epl_table", expected_table, timeout=mock_cache.set.call_args[1]["timeout"]
        )


@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
async def test_get_table_cache_hit(mock_cache):
    # Simulate a cache hit
    cached_data = [
        {
            "position": "1",
            "club": "Team A",
            "played": "5",
            "won": "3",
            "drawn": "1",
            "lost": "1",
            "gf": "10",
            "ga": "5",
            "gd": "+5",
            "points": "10",
            "form": "WWDWL",
        }
    ]
    mock_cache.get = AsyncMock(return_value=cached_data)

    # Call the view method
    response = await get_table()

    # Assertions
    assert response == cached_data

    # Verify that no Playwright interaction occurs on cache hit
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_not_called()


@pytest.mark.asyncio
@patch("epl_api.views.get_player_stats")
@patch("epl_api.views.extract_player_stats")
@patch("epl_api.v1.utils.cache")
async def test_get_p_stats(
    mock_cache, mock_extract_player_stats, mock_get_player_stats
):
    # Setup mock data for the get_player_stats function
    mock_get_player_stats.return_value = [
        {
            "name": "John Doe",
            "link": "player_link_1",
            "position": "Midfielder",
            "nationality": "England",
        },
        {
            "name": "Jane Doe",
            "link": "player_link_2",
            "position": "Defender",
            "nationality": "Scotland",
        },
    ]

    # Simulate a cache miss
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()

    # Setup a mock request with query parameters

    # Mock data for the extract_player_stats function
    mock_extract_player_stats.return_value = {
        "player_name": "John Doe",
        "appearances": 10,
        "goals": 5,
        "wins": 7,
        "losses": 3,
        "attack": {},
        "team_play": {},
        "discipline": {},
        "defence": {},
    }

    # Call the function under test
    response = await get_p_stats("John Doe")

    # Verify the correct schema was used and returned
    # assert isinstance(response, (PlayerStatsSchemas, PlayerStatsSchema))
    # assert len(response.players) == 1
    # assert response.players[0].player_name == "John Doe"

    # Verify the cache was set with the correct data
    mock_cache.set.assert_called_once()


# @pytest.mark.asyncio
# @patch("epl_api.views.get_player_stats")
# @patch("epl_api.v1.utils.cache")
# async def test_get_p_stats_cache_hit(mock_cache, mock_get_player_stats):
#     # Simulate a cache hit
#     cached_data = PlayerStatsSchemas(
#         players=[
#             PlayerStatsSchema(
#                 player_name="John Doe",
#                 appearances=10,
#                 goals=5,
#                 wins=7,
#                 losses=3,
#                 attack=AttackSchema(),
#                 team_play=TeamPlaySchema(),
#                 discipline=DisciplineSchema(),
#                 defence=DefenceSchema(),
#             )
#         ]
#     )
#     mock_cache.get = AsyncMock(return_value=cached_data)

#     # Setup a mock request
#     # request = MagicMock(spec=Request)
#     # request.query_params = {}

#     # Call the function under test
#     response = await get_p_stats("John Doe")

#     # Verify the response matches the cached data
#     assert response == cached_data

#     # Verify that no further processing occurs on cache hit
#     mock_get_player_stats.assert_not_called()
#     mock_cache.set.assert_not_called()
    
