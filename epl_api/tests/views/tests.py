from fastapi.testclient import TestClient
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from epl_api.v1.schemas import ResultSchema
from epl_api.views import get_p_stats, get_results, get_table
from django.core.cache import cache
from epl_api.asgi import app


@pytest.mark.asyncio
@patch("epl_api.views.get_page")  
@patch("epl_api.views.async_playwright")
@patch("epl_api.views.BeautifulSoup")
async def test_get_results(mock_bs4, mock_playwright, mock_get_page):
    cache.clear()

    mock_page = AsyncMock()
    mock_get_page.return_value = mock_page

    mock_browser_type = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()

    mock_playwright.return_value.__aenter__.return_value.chromium = mock_browser_type
    mock_browser_type.launch.return_value.__aenter__.return_value = mock_browser
    mock_browser.new_context.return_value.__aenter__.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    # page.goto and other async methods
    mock_page.goto.return_value = None
    mock_page.wait_for_selector.return_value = None
    mock_page.click.return_value = None

    # page content and BeautifulSoup parsing
    mock_page.content.return_value = "<html><body><li class='match-fixture' data-home='Team A' data-away='Team B'><span class='match-fixture__score'>2 - 1</span></li></body></html>"

    # Mock BeautifulSoup 
    mock_soup = Mock()
    mock_bs4.return_value = mock_soup

    mock_element = Mock()
    mock_element.get.side_effect = lambda key, default=None: (
        "Team A" if key == "data-home" else "Team B"
    )
    mock_element.select_one.return_value.text.strip.return_value = "2 - 1"

    mock_soup.select.return_value = [mock_element]

    results = await get_results(page=mock_page)

    # Check the results
    assert len(results) == 1
    assert isinstance(results[0], ResultSchema)
    assert results[0].home == "Team A"
    assert results[0].away == "Team B"
    assert results[0].score == "2 - 1"

    # Ensure that the page interactions occurred
    mock_page.goto.assert_called_once_with("https://www.premierleague.com/results")
    mock_page.wait_for_selector.assert_called()
    mock_page.click.assert_called()

    # Ensure BeautifulSoup was used 
    mock_bs4.assert_called_once()
    mock_soup.select.assert_called_once_with("li.match-fixture")
    

@pytest.mark.asyncio
@patch("epl_api.v1.helpers.onetrust_accept_cookie")
@patch("epl_api.views.BeautifulSoup")
@patch("epl_api.views.get_page")  # get_page dependency
@patch("epl_api.views.async_playwright")  
async def test_get_table(mock_playwright, mock_get_page, mock_bs4, mock_cookie):
    pytest.skip()
    cache.clear()

    mock_page = AsyncMock()
    mock_get_page.return_value = mock_page

    mock_browser_type = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()

    mock_playwright.return_value.__aenter__.return_value.chromium = mock_browser_type
    mock_browser_type.launch.return_value.__aenter__.return_value = mock_browser
    mock_browser.new_context.return_value.__aenter__.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_page.goto.return_value = None
    mock_page.wait_for_selector.return_value = None
    mock_page.click.return_value = None

    mock_page.content.return_value = """
    <html>
        <body>
            <div class="league-table__all-tables-container allTablesContainer">
                <table>
                    <tbody>
                        <tr>
                            <td>1</td>
                            <td><span class="league-table__team-name--long">Team A</span></td>
                            <td>30</td>
                            <td>20</td>
                            <td>5</td>
                            <td>5</td>
                            <td>50</td>
                            <td>20</td>
                            <td>+30</td>
                            <td>65</td>
                            <td>WDLWDL</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </body>
    </html>
    """

    mock_soup = mock_bs4.return_value

    mock_table = MagicMock()
    mock_row = MagicMock()
    
    mock_soup.select_one.return_value = mock_table
    mock_table.find_all.return_value = [mock_row]
    
    mock_row.find_all.return_value = [
        MagicMock(text="1"),
        MagicMock(text="Team A"),
        MagicMock(text="30"),
        MagicMock(text="20"),
        MagicMock(text="5"),
        MagicMock(text="5"),
        MagicMock(text="50"),
        MagicMock(text="20"),
        MagicMock(text="+30"),
        MagicMock(text="65"),
        MagicMock(text="WDLWDL"),
    ]

    table = await get_table(page=mock_page)

    # Assert that the table data matches the expected schema
    assert len(table) == 1
    team_data = table[0]

    # Check the values of the team data
    assert team_data.position == "1"
    assert team_data.club == "Team A"
    assert team_data.played == "30"
    assert team_data.won == "20"
    assert team_data.drawn == "5"
    assert team_data.lost == "5"
    assert team_data.gf == "50"
    assert team_data.ga == "20"
    assert team_data.gd == "+30"
    assert team_data.points == "65"
    assert team_data.form == "WDLWDL"

    # Ensure the cookie function was called
    assert mock_cookie.call_count == 1
    # Ensure that the page interactions occurred
    mock_page.goto.assert_called_once_with("https://www.premierleague.com/tables")
    mock_page.click.assert_called_once()
    mock_page.wait_for_selector.assert_called()

    # Ensure BeautifulSoup was used for parsing
    mock_bs4.assert_called_once()
    mock_soup.select_one.assert_called_once_with(
        "#mainContent div.league-table__all-tables-container.allTablesContainer table tbody"
    )
    

client = TestClient(app)

@pytest.fixture
def mock_extract_player_stats():
    with patch('epl_api.views.extract_player_stats') as mock:
        yield mock
        

@pytest.fixture
def mock_get_page():
    with patch('epl_api.views.get_page') as mock:
        yield mock
        

@pytest.mark.asyncio
async def test_get_p_stats_cache_miss(mock_extract_player_stats, mock_get_page):
    cache.clear()
    mock_extract_player_stats.return_value = [
        {"player_name": "Player One", "goals": "10", "assists": "5", "attack": {}, "team_play": {}, "discipline": {}, "defence": {}},
        {"player_name": "Player Two", "goals": "7", "assists": "3", "attack": {}, "team_play": {}, "discipline": {}, "defence": {}},
    ]
    mock_get_page.return_value = MagicMock()

    p_name = "Player One"
    (stat for stat in await get_p_stats(p_name))

    result = client.get(f"/api/v1/stats/{p_name}")

    # Assert
    assert result.status_code == 200
    assert len(result.json()) == 2
    assert result.json()[0]["player_name"] == "Player One"
    assert result.json()[1]["goals"] == "7"
    

@pytest.mark.asyncio
async def test_get_p_stats_cache_hit(mock_extract_player_stats, mock_get_page):
    cache.clear()
    mock_extract_player_stats.return_value = [
        {"player_name": "Player One", "goals": "10", "assists": "5", "attack": {}, "team_play": {}, "discipline": {}, "defence": {}},
        {"player_name": "Player Two", "goals": "7", "assists": "3", "attack": {}, "team_play": {}, "discipline": {}, "defence": {}},
    ]
    mock_get_page.return_value = MagicMock()

    p_name = "Player One"
    
    # First call to populate cache
    await get_p_stats(p_name)
    
    # Second call to test cache hit
    result = list(await get_p_stats(p_name))
    
    # Assert
    assert result[0].player_name == "Player One"
    assert result[1].goals == "7"
