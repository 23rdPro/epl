import re
from typing import List, TypeVar as T
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
from playwright.async_api import async_playwright
from epl_api.v1.utils import cache_result, onetrust_accept_cookie


def get_root():
    return {"message": "Welcome to the EPL API"}


@cache_result("epl_results", use_generator=True)
async def get_results(page=Depends(get_page)):
    async with async_playwright() as p:
        await page.goto("https://www.premierleague.com/results")
        await onetrust_accept_cookie(page)
        await page.wait_for_selector('li[data-tab-index="0"][data-text="First Team"]')
        await page.click('li[data-tab-index="0"][data-text="First Team"]')

        await page.wait_for_selector("li.match-fixture")

        # Parse page content
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        
        result_elements = soup.select("li.match-fixture")

        def extract_result_data(result):
            home_team = result.get("data-home", "")
            away_team = result.get("data-away", "")
            score = result.select_one(".match-fixture__score").text.strip()

            return {
                "home": home_team,
                "away": away_team,
                "score": score,
            }

        results = [extract_result_data(result) for result in result_elements]

        return [ResultSchema(**rsch) for rsch in results]


@cache_result("epl_table", use_generator=True)
async def get_table(page=Depends(get_page)) -> List[TableSchema]:
    await page.goto("https://www.premierleague.com/tables")
    await onetrust_accept_cookie(page)

    # Click on "First Team" tab and wait for the table to load
    await page.wait_for_selector('li[data-tab-index="0"][data-text="First Team"]')
    await page.click('li[data-tab-index="0"][data-text="First Team"]')
    await page.wait_for_selector(
        "#mainContent div.league-table__all-tables-container.allTablesContainer table tbody"
    )

    # Parse page content
    content = await page.content()
    soup = BeautifulSoup(content, "lxml")

    # Extract table rows
    table = soup.select_one(
        "#mainContent div.league-table__all-tables-container.allTablesContainer table tbody"
    )

    # Function to clean form text
    def clean_form(text):
        results = re.findall(r"(?:\b|\\n)([WLD])(?:\b|\\n)", text)
        return "".join(results[-6:])

    # Function to extract team data from a row
    def extract_team_data(row):
        cells = row.find_all("td")
        if len(cells) < 10:
            return None

        clean_pos = lambda text: (
            re.search(r"\d+", text).group(0)
            if text and re.search(r"\d+", text)
            else None
        )

        return {
            "position": clean_pos(cells[0].text.strip()),
            "club": (
                cells[1]
                .find("span", class_="league-table__team-name--long")
                .text.strip()
                if len(cells) > 1
                else None
            ),
            "played": cells[2].text.strip(),
            "won": cells[3].text.strip(),
            "drawn": cells[4].text.strip(),
            "lost": cells[5].text.strip(),
            "gf": cells[6].text.strip(),  # Goals For
            "ga": cells[7].text.strip(),  # Goals Against
            "gd": cells[8].text.strip(),  # Goal Difference
            "points": cells[9].text.strip(),
            "form": clean_form(cells[10].text.strip()) if len(cells) > 10 else None,
        }
        
    rows = table.find_all("tr")
    league_table = (data for row in rows if (data := extract_team_data(row)))
    return [TableSchema(**team_data) for team_data in league_table if team_data]


@cache_result(
    lambda p_name: f"player_stats_{''.join(p_name.split(' ')).lower()}",
    use_generator=True,
)
async def get_p_stats(p_name: str, page=Depends(get_page)):
    stats = await extract_player_stats(p_name, page)
    if not stats:
        return JSONResponse(
            {"error get_player_stats": "Failed to retrieve stats"},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    return [PlayerStatsSchema(**p_stat) for p_stat in stats]


# @cache_result("epl_fixture")  TODO
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
