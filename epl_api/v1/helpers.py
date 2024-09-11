import re
from typing import List, Optional, TypeVar as T, Dict
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
    await onetrust_accept_cookie(page)

    # Search for the player
    await page.wait_for_selector('input[placeholder="Search for a Player"]')
    await page.fill('input[placeholder="Search for a Player"]', player)
    await page.keyboard.press("Enter")
    await page.wait_for_selector("tbody.dataContainer.indexSection")

    # Parse the page content
    content = await page.content()
    soup = BeautifulSoup(content, "lxml")

    # Extract the player list from the table
    tbody = soup.select_one("tbody.dataContainer.indexSection")
    if not tbody:
        raise Exception("Player table data not found")

    players = tbody.find_all("tr", class_="player")

    results = [
        {
            "name": player.find("a", class_="player__name").text.strip(),
            "link": f"https:{player.find('a', class_='player__name')['href']}".replace(
                "overview", "stats"
            ),
            "position": player.find("td", class_="player__position").text.strip(),
            "nationality": player.find("span", class_="player__country").text.strip(),
        }
        for player in players
    ]

    async def extract_p_stats(player_data: dict) -> dict:
        await page.goto(player_data["link"])
        await onetrust_accept_cookie(page)

        # Extract the stats content
        content = await page.content()
        soup = BeautifulSoup(content, "lxml")

        # Extract player stats
        stats_section = soup.select_one("div.player-stats__top-stats")
        if not stats_section:
            return {}

        # Helper function to extract top stats
        def extract_stat(stat_class: str) -> int:
            stat_element = stats_section.find("span", class_=f"stat{stat_class}")
            return int(stat_element.text.strip()) if stat_element else 0

        # Extract appearances, goals, wins, and losses
        appearances = extract_stat("appearances")
        goals = extract_stat("goals")
        wins = extract_stat("wins")
        losses = extract_stat("losses")

        # Filter sections by their names and map them to schemas
        def filter_sections(name: str) -> Optional[BeautifulSoup]:
            return next(
                (
                    section
                    for section in soup.find_all("li", class_="player-stats__stat")
                    if section.find("div", text=re.compile(name))
                ),
                None,
            )

        # Extract stats with schemas
        def with_schema(section, schema):
            if not section:
                return schema()

            stats_dict = {}
            for stat_value in section.select("div.player-stats__stat-value"):
                stat_name = stat_value.contents[0].strip()
                stat_val = (
                    stat_value.find("span.allStatContainer").get_text().strip()
                    if stat_value.find("span.allStatContainer")
                    else None
                )
                if stat_name and stat_val:
                    stats_dict[stat_name] = stat_val

            return schema(**stats_dict)

        # Mapping stats sections 
        attack_section = filter_sections("Attack")
        team_play_section = filter_sections("Team Play")
        discipline_section = filter_sections("Discipline")
        defence_section = filter_sections("Defence")

        attack: AttackSchema = with_schema(attack_section, AttackSchema)
        team_play: TeamPlaySchema = with_schema(team_play_section, TeamPlaySchema)
        discipline: DisciplineSchema = with_schema(discipline_section, DisciplineSchema)
        defence: DefenceSchema = with_schema(defence_section, DefenceSchema)

        # Combine the extracted stats
        return {
            "player_name": player_data["name"],
            "appearances": appearances,
            "goals": goals,
            "wins": wins,
            "losses": losses,
            "attack": attack.model_dump(),
            "team_play": team_play.model_dump(),
            "discipline": discipline.model_dump(),
            "defence": defence.model_dump(),
        }

    return (await extract_p_stats(player) for player in results if player)
