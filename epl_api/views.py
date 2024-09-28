import asyncio
import re
from typing import List
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


async def current_club_list(page):
    await page.goto("https://www.premierleague.com/clubs")
    await onetrust_accept_cookie(page)

    async def _extract():  # TODO: handle background, celery
        list_items = page.locator("ul.club-list.dataContainer li.club-card-wrapper")
        count = await list_items.count()  # Get the number of list items

        for i in range(count):
            # Extract link and name for each club
            club_link = (
                await list_items.nth(i)
                .locator("a")
                .get_attribute("href")
            ).replace("overview", "results")
            club_name = (
                await list_items.nth(i).locator("h2.club-card__name").inner_text()
            )

            yield club_name, f"https://www.premierleague.com{club_link}"

    return _extract()


async def team_level_features(link, page):
    await page.goto(link)
    await onetrust_accept_cookie(page)

    fixtures = await page.locator(
        "div.fixtures__matches-list ul.matchList li.match-fixture"
    ).all()

    # Aggregate results
    _agg = [
        {
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
        }
        for fixture in fixtures
        for (
            home_team,
            away_team,
            score_text,
        ) in [
            await asyncio.gather(
                fixture.locator("span.match-fixture__team")
                .first.locator("span.match-fixture__short-name")
                .inner_text(),
                fixture.locator("span.match-fixture__team")
                .nth(1)
                .locator("span.match-fixture__short-name")
                .inner_text(),
                fixture.locator("span.match-fixture__score").inner_text(),
            )
        ]
        if (home_score := int(score_text.split("-")[0])) is not None
        and (away_score := int(score_text.split("-")[1])) is not None
    ]

    return _agg


async def player_level_features(link, page):
    await page.goto(link)
    await onetrust_accept_cookie(page)

    squad_list = await page.locator("ul.squadListContainer.squad-list").all()

    players_data = {}

    for squad in squad_list:
        # Get the position header
        position_header = await squad.locator("h1").inner_text()
        players_data[position_header] = []

        player_cards = await squad.locator("ul li.stats-card").all()

        # Extract player details concurrently
        players = await asyncio.gather(
            *[_extract_player_stats(player_card) for player_card in player_cards]
        )

        players_data[position_header].extend(players)
    print(">>>>>>>>>>>>>>>>>>>>> start from here")
    print(players_data)

    return players_data


async def _extract_player_stats(player_card):
    player_name = await player_card.locator("div.stats-card__name").inner_text()

    # Extract player statistics
    stats = {
        await stat.locator("div.stats-card__pos")
        .inner_text(): await stat.locator("div.stats-card__stat")
        .inner_text()
        for stat in await player_card.locator(
            "ul.stats-card__stats-list.js-featured-player-stats li.stats-card__row"
        ).all()
    }

    # Return player data as a dictionary
    return {"name": player_name, **stats}


# @cache_result(lambda club: '-'.join(club.split()))
async def aggregate_club_stats(club: str, page=Depends(get_page)):
    _links = await current_club_list(page)
    _link = None

    async for name, link in _links:
        if club.lower() in name.lower():
            _link = link
            break

    # Fetch team-level and player-level statistics
    team_level = await team_level_features(_link, page)
    player_level = await player_level_features(_link, page)
    
    # print(team_level)
    print(player_level)

    # Initialize an aggregated result dictionary
    aggregate = {
        "team_stats": [],
        "player_stats": {}
    }

    # Aggregate team-level stats
    for match in team_level:
        match_info = {
            "home_team": match["home_team"],
            "away_team": match["away_team"],
            "home_score": match["home_score"],
            "away_score": match["away_score"],
            "players": []  # Placeholder for players in this match
        }

        # Extract players from the player_level structure
        for position, players in player_level.items():
            for player in players:
                # Check if player belongs to the home or away team
                if player["name"] in match["home_team"] or player["name"] in match["away_team"]:
                    match_info["players"].append(player)

        # Append the match info to the team stats
        aggregate["team_stats"].append(match_info)

    # Aggregate player stats by position
    for position, players in player_level.items():
        aggregate["player_stats"][position] = players

    return aggregate



@cache_result("epl_fixture")
async def get_fixtures(page=Depends(get_page)):
    async with async_playwright() as p:
        await page.goto("https://www.premierleague.com/fixtures")
        await onetrust_accept_cookie(page)
        await page.click('li[data-tab-index="0"][data-text="First Team"]')
        await page.wait_for_selector("li.match-fixture")
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")
        fixture_elements = soup.select("li.match-fixture")

        def _extract(element):
            home_team = element.get("data-home", "")
            away_team = element.get("data-away", "")
            time = element.select_one("time")
            return {
                "home": home_team,
                "away": away_team,
                "time": time and time.get("datetime", time.text.strip()),
            }

        fixtures = [_extract(e) for e in fixture_elements]
        return [FixtureSchema(**fsch) for fsch in fixtures]


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
    return [PlayerStatsSchema(**p_stat) async for p_stat in stats]
