import pytest
from unittest.mock import AsyncMock

import pytest_asyncio

from epl_api.v1.helpers import extract_player_stats


from unittest.mock import AsyncMock
import pytest
import pytest_asyncio


@pytest_asyncio.fixture
async def mock_page(mocker):
    # Mock the Playwright Page object
    page = mocker.Mock()

    # Mock the content for the search page (player search results)
    search_page_content = """
    <tbody class="dataContainer indexSection">
        <tr class="player">
            <a class="player__name" href="/players/12345/player-name/overview">Test Player</a>
            <td class="player__position">Midfielder</td>
            <span class="player__country">Country Name</span>
        </tr>
    </tbody>
    """

    # Mock the content for the stats page (player stats)
    stats_page_content = """
    <div class="player-stats__top-stats">
        <span class="statappearances">50</span>
        <span class="statgoals">15</span>
        <span class="statwins">30</span>
        <span class="statlosses">20</span>
    </div>
    <li class="player-stats__stat">
        <div>Attack</div>
        <div class="player-stats__stat-value">goals<span class="allStatContainer">10</span></div>
        <div class="player-stats__stat-value">goals_per_match<span class="allStatContainer">5.6</span></div>
        <div class="player-stats__stat-value">headed_goals<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">goals_with_left<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">goals_with_right<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">scored_pks<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">scored_free_kicks<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">shots<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">shots_on_target<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">shooting accuracy %<span class="allStatContainer">5%</span></div>
        
        <div class="player-stats__stat-value">shooting_accuracy<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">shots_on_target<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">hit_woodwork<span class="allStatContainer">5</span></div>
        <div class="player-stats__stat-value">big_chances_missed<span class="allStatContainer">5</span></div>
    </li>
    <li class="player-stats__stat">
        <div>Team Play</div>
        <div class="player-stats__stat-value">assists<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">passes<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">passes_per_match<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">big_chances_created<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">crosses<span class="allStatContainer">7</span></div>
    </li>
    <li class="player-stats__stat">
        <div>Discipline</div>
        <div class="player-stats__stat-value">yellow_cards<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">red_cards<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">fouls<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">offside<span class="allStatContainer">7</span></div>
    </li>
    <li class="player-stats__stat">
        <div>Defence</div>
        <div class="player-stats__stat-value">tackles<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">blocked_shots<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">interceptions<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">clearances<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">headed_clearance<span class="allStatContainer">7</span></div>
        <div class="player-stats__stat-value">successful 50/50s<span class="allStatContainer">44</span></div>
    </li>
    """
    # Mock the cookie consent function
    mocker.patch("epl_api.v1.helpers.onetrust_accept_cookie", new=AsyncMock())

    # Set the page content mocks for both search and stats pages
    page.content.side_effect = AsyncMock(
        side_effect=[search_page_content, stats_page_content]
    )
    page.goto = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.fill = AsyncMock()
    page.keyboard.press = AsyncMock()

    return page


@pytest.mark.asyncio
async def test_extract_player_stats(mock_page):
    # Call the extract_player_stats function with the mocked page
    player_stats_generator = await extract_player_stats("Test Player", mock_page)

    # Convert the async generator to a list for testing
    player_stats = [stat async for stat in player_stats_generator]

    # Assert that the extracted data matches the expected values
    assert len(player_stats) == 1
    player_data = player_stats[0]

    # Assert general stats
    assert player_data["player_name"] == "Test Player"
    assert player_data["appearances"] == "50"
    assert player_data["goals"] == "15"
    assert player_data["wins"] == "30"
    assert player_data["losses"] == "20"

    assert player_data["attack"]["goals"] == "10"
    assert player_data["attack"]["shots"] == "5"
    assert player_data["attack"]["shooting_accuracy"] == "5"

    assert player_data["team_play"]["assists"] == "7"

    assert player_data["discipline"]["yellow_cards"] == "7"
    assert player_data["discipline"]["red_cards"] == "7"
    assert player_data["defence"]["tackles"] == "7"
    assert player_data["defence"]["clearances"] == "7"
    assert player_data["defence"]["successful_50_50s"] == "44"
