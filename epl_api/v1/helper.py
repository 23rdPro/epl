from typing import List, TypeVar as T
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from epl_api.v1.schema import (
    AttackSchema,
    DefenceSchema,
    DisciplineSchema,
    TeamPlaySchema,
)


async def get_player_stats(player_name: str) -> List[T]:  # TODO: return generator
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto("https://www.premierleague.com/players", wait_until='load', timeout=15000)
        await page.wait_for_selector('input[placeholder="Search for a Player"]')
        await page.fill('input[placeholder="Search for a Player"]', player_name)

        # [Enter]: to submit the search
        await page.keyboard.press("Enter")

        # Wait for the player data
        await page.wait_for_selector("tbody.dataContainer.indexSection", timeout=15000)

        # Extract the HTML
        content = await page.content()
        await browser.close()

        # BeautifulSoup to parse the content
        soup = BeautifulSoup(content, "lxml")
        table = soup.find("div", class_="table playerIndex player-listing")
        tbody = table.find("tbody", class_="dataContainer indexSection")

        players = tbody.find_all("tr", class_="player")
        data = []

        for player in players:
            info = player.find("a", class_="player__name")
            if info:
                name = info.text.strip()
                link = f"https://www.premierleague.com{info['href']}"
                position = player.find("td", class_="player__position").text.strip()
                nationality = player.find("span", class_="player__country").text.strip()
                data.append(
                    {
                        "name": name,
                        "link": link,
                        "position": position,
                        "nationality": nationality,
                    }
                )
        return data


async def extract_attack_stats(section: BeautifulSoup) -> AttackSchema:
    return AttackSchema(
        goals=int(section.find("span", class_="goals").text.strip()),
        goals_per_match=float(
            section.find("span", class_="goals_per_match").text.strip()
        ),
        headed_goals=int(section.find("span", class_="headed_goals").text.strip()),
        goals_with_left=int(
            section.find("span", class_="goals_with_left").text.strip()
        ),
        goals_with_right=int(
            section.find("span", class_="goals_with_right").text.strip()
        ),
        scored_pks=int(section.find("span", class_="scored_pks").text.strip()),
        scored_free_kicks=int(
            section.find("span", class_="scored_free_kicks").text.strip()
        ),
        shots=int(section.find("span", class_="shots").text.strip()),
        shots_on_target=int(
            section.find("span", class_="shots_on_target").text.strip()
        ),
        shooting_accuracy=float(
            section.find("span", class_="shooting_accuracy")
            .text.strip()
            .replace("%", "")
        ),
        hit_woodwork=int(section.find("span", class_="hit_woodwork").text.strip()),
        big_chances_missed=int(
            section.find("span", class_="big_chances_missed").text.strip()
        ),
    )


async def extract_team_play_stats(section: BeautifulSoup) -> TeamPlaySchema:
    return TeamPlaySchema(
        assists=int(section.find("span", class_="assists").text.strip()),
        passes=int(section.find("span", class_="passes").text.strip()),
        passes_per_match=float(
            section.find("span", class_="passes_per_match").text.strip()
        ),
        big_chances_created=int(
            section.find("span", class_="big_chances_created").text.strip()
        ),
        crosses=int(section.find("span", class_="crosses").text.strip()),
    )


async def extract_discipline_stats(section: BeautifulSoup) -> DisciplineSchema:
    return DisciplineSchema(
        yellow_cards=int(section.find("span", class_="yellow_cards").text.strip()),
        red_cards=int(section.find("span", class_="red_cards").text.strip()),
        fouls=int(section.find("span", class_="fouls").text.strip()),
        offside=int(section.find("span", class_="offside").text.strip()),
    )


async def extract_defence_stats(section: BeautifulSoup) -> DefenceSchema:
    return DefenceSchema(
        tackles=int(section.find("span", class_="tackles").text.strip()),
        blocked_shots=int(section.find("span", class_="blocked_shots").text.strip()),
        interceptions=int(section.find("span", class_="interceptions").text.strip()),
        clearances=int(section.find("span", class_="clearances").text.strip()),
        headed_clearance=int(
            section.find("span", class_="headed_clearance").text.strip()
        ),
    )


async def extract_player_stats(page: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Go to the player's specific page
        await page.goto(page, wait_until="load", timeout=15000)

        # Navigate to the "Stats" section
        await page.click('a.generic-tabs-nav__link[data-text="Stats"]')

        # Wait for the stats to load
        await page.wait_for_selector("div.player-stats")

        # Extract the HTML content
        content = await page.content()
        await browser.close()

        # Parse the stats with BeautifulSoup
        soup = BeautifulSoup(content, "lxml")

        # stats section
        stats_section = soup.find("div", class_="player-stats")
        player_name = soup.find("div", class_="name").text.strip()

        # Extract specifics
        appearances = stats_section.find("span", class_="appearances").text.strip()
        goals = stats_section.find("span", class_="goals").text.strip()
        wins = stats_section.find("span", class_="wins").text.strip()
        losses = stats_section.find("span", class_="losses").text.strip()

        attack: AttackSchema = extract_attack_stats(stats_section)
        team_play: TeamPlaySchema = extract_team_play_stats(stats_section)
        discipline: DisciplineSchema = extract_discipline_stats(stats_section)
        defence: DefenceSchema = extract_defence_stats(stats_section)

        player_stats = {
            "player_name": player_name,
            "appearances": int(appearances),
            "goals": int(goals),
            "wins": int(wins),
            "losses": int(losses),
            "attack": attack,
            "team_play": team_play,
            "discipline": discipline,
            "defence": defence,
        }

        return player_stats
