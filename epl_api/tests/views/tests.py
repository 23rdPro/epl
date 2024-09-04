import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from epl_api.views import get_results
# from your_module import get_results, ResultSchema, ClubSchema


@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
@patch("epl_api.views.async_playwright")
async def test_get_results(mock_playwright, mock_cache):
    # simulate a cache miss
    mock_cache.get.return_value = None
    mock_cache.set = AsyncMock()

    # Mock Playwright browser
    mock_browser = AsyncMock()
    mock_page = AsyncMock()
    mock_playwright.return_value.__aenter__.return_value.chromium.launch.return_value.__aenter__.return_value = mock_browser
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
    with patch("epl_api.views.BeautifulSoup") as mock_soup, \
         patch("epl_api.v1.schema.ResultSchema") as mock_result_schema, \
         patch("epl_api.v1.schema.ClubSchema") as mock_club_schema:
        
        # Setup BeautifulSoup mock
        mock_soup.return_value.select.return_value = [
            MagicMock(**{"data-home": "Team A", "data-away": "Team B", "select_one.return_value.text.strip.return_value": "2 - 1"}),
            MagicMock(**{"data-home": "Team C", "data-away": "Team D", "select_one.return_value.text.strip.return_value": "0 - 0"}),
        ]

        # Mock the schemas
        mock_result_schema.side_effect = lambda home, away, score: MagicMock(
            dict=lambda: {"home": home.name, "away": away.name, "score": score}
        )
        mock_club_schema.side_effect = lambda name: MagicMock(name=name)

        # Call the view method
        response = await get_results()

        # Assertions
        expected_results = [
            {"home": "Team A", "away": "Team B", "score": "2 - 1"},
            {"home": "Team C", "away": "Team D", "score": "0 - 0"},
        ]
        assert response.status_code == 200
        assert response.json() == {"results": expected_results}

        # Verify Playwright interaction
        mock_page.goto.assert_called_once_with("https://www.premierleague.com")
        mock_page.click.assert_any_call('a[href="/results"][data-link-index="2"]')
        mock_page.wait_for_selector.assert_called_with("li.match-fixture")

        # Verify cache set call with correct data
        mock_cache.set.assert_called_once()
        

@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
async def test_get_results_cache_hit(mock_cache):
    # Simulate a cache hit
    cached_data = {"results": [{"home": "Team A", "away": "Team B", "score": "2 - 1"}]}
    mock_cache.get.return_value = cached_data

    # Call the view method
    response = await get_results()

    # Assertions
    assert response.status_code == 200
    assert response.json() == cached_data

    # Verify that no Playwright interaction occurs on cache hit
    mock_cache.get.assert_called_once()
    mock_cache.set.assert_not_called()
