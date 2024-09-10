from bs4 import BeautifulSoup
from epl_api.v1.dependencies import get_page
from epl_api.v1.helpers import extract_player_stats
from epl_api.v1.schemas import (
    FixtureSchema,
    PlayerStatsSchema,
    ResultSchema,
    TableSchema,
)
from fastapi import Depends, status
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright, TimeoutError
from epl_api.v1.utils import cache_result, format_league_table, onetrust_accept_cookie


def get_root():
    return {"message": "Welcome to the EPL API"}


@cache_result("epl_results")
async def get_results():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.premierleague.com")

        # Click on the "Results" link
        await page.click('a[href="/results"][data-link-index="2"]')

        # "First Team" tab to load and click on it
        await page.wait_for_selector('li[data-tab-index="0"][data-text="First Team"]')
        await page.click('li[data-tab-index="0"][data-text="First Team"]')

        # Wait for the results to load
        await page.wait_for_selector("li.match-fixture")

        # Parse page content
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        await browser.close()

        # Extract result data
        results = []
        result_elements = soup.select("li.match-fixture")
        for result in result_elements:
            home_team = result["data-home"]
            away_team = result["data-away"]
            score = result["select_one"](".match-fixture__score").text.strip()

            # Structure the data using the schemas
            result_data = ResultSchema(
                home=home_team,
                away=away_team,
                score=score,
            )
            results.append(result_data)

        # Return the structured data
        return JSONResponse(content=[result.model_dump() for result in results])


# @cache_result("epl_fixture")
async def get_fixtures():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.premierleague.com")

        # Click on the "Fixtures" link
        await page.click('a[href="/fixtures"][data-link-index="1"]')

        await page.wait_for_selector('li[data-tab-index="0"][data-text="First Team"]')
        await page.click('li[data-tab-index="0"][data-text="First Team"]')

        # Wait for the fixtures to load
        await page.wait_for_selector("li.match-fixture")

        # Parse page content
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        await browser.close()

        # Extract fixture data
        fixtures = []
        fixture_elements = soup.select("li.match-fixture")
        for fixture in fixture_elements:
            home_team = fixture["data-home"]
            away_team = fixture["data-away"]
            kickoff_time = fixture["time"]

            # Structure the data using the schemas
            fixture_data = FixtureSchema(
                home=home_team,
                away=away_team,
                time=kickoff_time,
            )
            fixtures.append(fixture_data)

        # Return the structured data
        return JSONResponse(
            content={"fixtures": [fixture.model_dump() for fixture in fixtures]}
        )


@cache_result("epl_table")
async def get_table(page=Depends(get_page)):
    await page.goto("https://www.premierleague.com/tables")
    # accept cookie
    await onetrust_accept_cookie(page)
    # click on "First Team" tab
    await page.wait_for_selector('li[data-tab-index="0"][data-text="First Team"]')
    await page.click('li[data-tab-index="0"][data-text="First Team"]')

    # Wait for the table to load
    await page.wait_for_selector(
        "#mainContent div.league-table__all-tables-container.allTablesContainer table tbody"
    )

    # parse page with BeautifulSoup
    content = await page.content()
    soup = BeautifulSoup(content, "lxml")
    # await browser.close()

    # Extract the table rows
    table = soup.select_one(
        "#mainContent div.league-table__all-tables-container.allTablesContainer table tbody"
    )
    rows = table.find_all("tr")
    format_data = format_league_table(rows)
    return [TableSchema(**d) for d in format_data]


@cache_result(lambda p_name: f"player_stats_{''.join(p_name.split(' ')).lower()}")
async def get_p_stats(p_name: str, page=Depends(get_page)):
    stats = await extract_player_stats(p_name, page)
    if not stats:
        return JSONResponse(
            {"error get_player_stats": "Failed to retrieve stats"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return [PlayerStatsSchema(**p_stat) for p_stat in stats]
