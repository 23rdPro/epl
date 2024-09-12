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

    return (await extract_p_stats(player, page) for player in results if player)


async def extract_p_stats(player_data: dict, page) -> dict:
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
        return stat_element.text.strip() if stat_element else 0

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
                if section.find("div", string=re.compile(name))
            ),
            None,
        )
        
    def _to_decimal(arg: str) -> str:
        if "%" in arg:
            return str(round(int(arg.replace("%", "").strip()) / 100, 2))
        return arg 
    
    # Function to map the schema with extracted stats
    def with_schema(section, schema: DefenceSchema):
        if not section:
            return schema()  # validation error if field missing

        stats_dict = {}
        # Extract stats from the section
        for stat_value in section.select("div.player-stats__stat-value"):
            # Split the stat name and value correctly
            stat_name = '_'.join(k.lower() for k in stat_value.contents[0].strip().split(' '))
            statval = stat_value.find("span", class_="allStatContainer").get_text().strip()
            stat_val = _to_decimal(statval)
            if stat_name and stat_val:
                # Ensure stats are mapped correctly
                stats_dict[stat_name] = stat_val
                                                
        key_mapping = {
            "shooting_accuracy": "shooting_accuracy_%",
            "successful_50_50s": "successful_50/50s"
        }
                
        filtered_stats = {}
        
        for field in schema.model_fields:
            if field in stats_dict:
                filtered_stats[field] = stats_dict[field]
            else:
                # Check if the field has a mapped key in key_mapping
                mapped_key = key_mapping.get(field)
                if mapped_key and mapped_key in stats_dict:
                    filtered_stats[field] = stats_dict[mapped_key]
                else:
                    # Default to "N/A" if not found
                    filtered_stats[field] = "N/A"

        return schema(**filtered_stats)


    # Mapping stats sections
    attack_section = filter_sections("Attack")
    team_play_section = filter_sections("Team Play")
    discipline_section = filter_sections("Discipline")
    defence_section = filter_sections("Defence")

    attack: AttackSchema = with_schema(attack_section, AttackSchema)
    team_play: TeamPlaySchema = with_schema(team_play_section, TeamPlaySchema)
    discipline: DisciplineSchema = with_schema(discipline_section, DisciplineSchema)
    defence: DefenceSchema = with_schema(defence_section, DefenceSchema)

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
