from bs4 import BeautifulSoup
from epl_api.v1.helper import extract_player_stats, get_player_stats
from epl_api.v1.schema import (
    FixtureSchema,
    PlayerStatsSchema,
    PlayerStatsSchemas,
    ResultSchema,
)
from fastapi import Request, status
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright
from epl_api.v1.utils import cache_result


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
            score = result['select_one'](".match-fixture__score").text.strip()

            # Structure the data using the schemas
            result_data = ResultSchema(
                home=home_team,
                away=away_team,
                score=score,
            )
            results.append(result_data)

        # Return the structured data
        return JSONResponse(content=[result.model_dump() for result in results])


@cache_result("epl_fixture")
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
async def get_table():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.premierleague.com")

        # Click on the "Tables" link
        await page.click('a[data-link-index="3"][role="menuitem"]')

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
        await browser.close()

        # Extract the table rows
        table = soup.select_one(
            "#mainContent div.league-table__all-tables-container.allTablesContainer table tbody"
        )
        rows = table.find_all("tr")

        # Parse the table rows into structured data
        league_table = []
        for row in rows:
            cells = row.find_all("td")
            league_table.append(
                {
                    "position": cells[0].text.strip(),
                    "club": cells[1].text.strip(),
                    "played": cells[2].text.strip(),
                    "won": cells[3].text.strip(),
                    "drawn": cells[4].text.strip(),
                    "lost": cells[5].text.strip(),
                    "gf": cells[6].text.strip(),
                    "ga": cells[7].text.strip(),
                    "gd": cells[8].text.strip(),
                    "points": cells[9].text.strip(),
                    "form": cells[10].text.strip() if len(cells) > 10 else None,
                }
            )

        return league_table


@cache_result(
    lambda p_name, request: f"player_stats_{p_name.lower()}_{request.query_params}"
)
async def get_p_stats(p_name: str, request: Request):
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
        for key, item in filters.items():
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
        return PlayerStatsSchema(**player_stats)
    return PlayerStatsSchemas(players=stats)
