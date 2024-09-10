import re
from typing import List, TypeVar as T, Dict
from bs4 import BeautifulSoup
from playwright.async_api import Page
from epl_api.v1.schemas import (
    AttackSchema,
    DefenceSchema,
    DisciplineSchema,
    TeamPlaySchema,
)
from epl_api.v1.utils import onetrust_accept_cookie


async def extract_player_stats(player: str, page: Page) -> List[Dict]:
    await page.goto("https://www.premierleague.com/players")
    # TODO: handle non-responsive page -> time out error waiting for element to be visible
    await onetrust_accept_cookie(page)

    await page.wait_for_selector('input[placeholder="Search for a Player"]')
    await page.fill('input[placeholder="Search for a Player"]', player)
    await page.keyboard.press("Enter")

    # Wait for player data to load
    await page.wait_for_selector("tbody.dataContainer.indexSection")

    # Extract the HTML content of the search results
    content = await page.content()

    # Parse the HTML
    soup = BeautifulSoup(content, "lxml")
    table = soup.find("div", class_="table playerIndex player-listing")
    tbody = table.find("tbody", class_="dataContainer indexSection")

    if not table or not tbody:
        raise Exception("Player table data not found")

    players = tbody.find_all("tr", class_="player")
    results = []

    for player in players:
        info = player.find("a", class_="player__name")
        link = f"https:{info['href']}".replace("overview", "stats")
        results.append(
            {
                "name": info.text.strip(),
                "link": link,
                "position": player.find("td", class_="player__position").text.strip(),
                "nationality": player.find(
                    "span", class_="player__country"
                ).text.strip(),
            }
        )

    async def extract_p_stats(player_data: dict, name: str) -> dict:
        await page.goto(player_data["link"])
        await onetrust_accept_cookie(page)

        # Navigate to the "Stats" section
        # await page.click('a.generic-tabs-nav__link[data-text="Stats"]')

        # Wait for the stats to load
        # await page.wait_for_selector("div.player-stats")

        # Extract the stats content
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")

        # Find the main stats section
        stats_section = soup.find("div", class_="player-stats__top-stats")

        # Extract top stats (appearances, goals, wins, losses)
        appearances = stats_section.find("span", class_="statappearances").text.strip()
        goals = stats_section.find("span", class_="statgoals").text.strip()
        wins = stats_section.find("span", class_="statwins").text.strip()
        losses = stats_section.find("span", class_="statlosses").text.strip()

        # Helper function to extract stat value
        def extract_stat(stat_section, stat_name):
            stat = stat_section.find("span", class_=f"stat{stat_name}")
            if stat:
                return int(stat.text) if stat.text.isdigit() else stat.text
            return 0

        stat_sections = soup.find_all("li", class_="player-stats__stat")

        def with_schema(section, schema):
            stats_dict = {}
            stat_values = section.find_all("div", class_="player-stats__stat-value")

            for stat_value in stat_values:
                # Extract stat name and value
                stat_name = stat_value.contents[0].strip()
                stat_span = stat_value.find("span", class_="allStatContainer")
                stat_val = stat_span.get_text().strip() if stat_span else None

                if stat_name and stat_val:
                    stats_dict[stat_name] = stat_val

            return schema(**stats_dict)

        def filter_sections(name: str) -> BeautifulSoup:
            return next(
                (
                section
                for section in stat_sections
                if section.find("div", text=re.compile(name))
            ),
            None,
            )

        attack_section = filter_sections("Attack")
        attack: AttackSchema = with_schema(attack_section, AttackSchema)

        team_play_section = filter_sections("Team Play")
        team_play: TeamPlaySchema = with_schema(team_play_section, TeamPlaySchema)

        discipline_section = filter_sections("Discipline")
        discipline: DisciplineSchema = with_schema(discipline_section, DisciplineSchema)

        defence_section = filter_sections("Defence")
        defence: DefenceSchema = with_schema(defence_section, DefenceSchema)

        # Combine all the extracted stats
        return {
            "player_name": name,
            "appearances": int(appearances),
            "goals": int(goals),
            "wins": int(wins),
            "losses": int(losses),
            "attack": attack.model_dump(),
            "team_play": team_play.model_dump(),
            "discipline": discipline.model_dump(),
            "defence": defence.model_dump(),
        }

    return [await extract_p_stats(player, player["name"]) for player in results]
