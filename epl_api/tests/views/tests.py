import pytest
from unittest.mock import AsyncMock, Mock, patch

from epl_api.v1.schemas import ResultSchema
from epl_api.views import get_results
from django.core.cache import cache


@pytest.mark.asyncio
@patch("epl_api.views.get_page")  # get_page dependency
@patch("epl_api.views.async_playwright")
@patch("epl_api.views.BeautifulSoup")
async def test_get_results(mock_bs4, mock_playwright, mock_get_page):
    cache.clear()

    # Mock the page interactions
    mock_page = AsyncMock()
    mock_get_page.return_value = mock_page

    # Mock the async playwright browser interaction
    mock_browser_type = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()

    mock_playwright.return_value.__aenter__.return_value.chromium = mock_browser_type
    mock_browser_type.launch.return_value.__aenter__.return_value = mock_browser
    mock_browser.new_context.return_value.__aenter__.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    # Mock the page.goto and other async methods
    mock_page.goto.return_value = None
    mock_page.wait_for_selector.return_value = None
    mock_page.click.return_value = None

    # Mock the page content and BeautifulSoup parsing
    mock_page.content.return_value = "<html><body><li class='match-fixture' data-home='Team A' data-away='Team B'><span class='match-fixture__score'>2 - 1</span></li></body></html>"

    # Mock BeautifulSoup to be synchronous
    mock_soup = Mock()
    mock_bs4.return_value = mock_soup

    # Return a list of mock elements from select (synchronous)
    mock_element = Mock()
    mock_element.get.side_effect = lambda key, default=None: (
        "Team A" if key == "data-home" else "Team B"
    )
    mock_element.select_one.return_value.text.strip.return_value = "2 - 1"

    mock_soup.select.return_value = [mock_element]

    # Call the view function with the mock_page manually passed in
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

    # Ensure BeautifulSoup was used for parsing
    mock_bs4.assert_called_once()
    mock_soup.select.assert_called_once_with("li.match-fixture")
