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
        await page.wait_for_selector('a[data-link-index="3"][role="menuitem"]')
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


@cache_result(lambda p_name: f"player_stats_{''.join(p_name.split(' ')).lower()}")
async def get_p_stats(p_name: str):
    stats = await get_player_stats(p_name)
    if not stats:
        return JSONResponse(
            {"error get_player_stats": "Failed to retrieve stats"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    combined = [
        {
            "player_name": (player_stats := await extract_player_stats(player["link"]))[
                "player_name"
            ],
            "appearances": player_stats["appearances"],
            "goals": player_stats["goals"],
            "wins": player_stats["wins"],
            "losses": player_stats["losses"],
            "attack": player_stats["attack"],
            "team_play": player_stats["team_play"],
            "discipline": player_stats["discipline"],
            "defence": player_stats["defence"],
        }
        for player in stats
    ]
    return [PlayerStatsSchema(**p_stat) for p_stat in combined]
