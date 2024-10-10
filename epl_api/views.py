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
from epl_api.v1.utils import cache_result, get_browser, onetrust_accept_cookie


def get_root():
    return {"message": "Welcome to the EPL API"}


async def current_club_list(page):
    await page.goto("https://www.premierleague.com/clubs")
    await onetrust_accept_cookie(page)

    async def _extract():  # TODO
        list_items = page.locator("ul.club-list.dataContainer li.club-card-wrapper")
        count = await list_items.count()  # Get the number of list items

        for i in range(count):
            # Extract link and name for each club
            club_link = await list_items.nth(i).locator("a").get_attribute("href")
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

    # coroutine tasks for parallel processing
    tasks = []

    for fixture in fixtures:
        tmp = {}
        wrapper = fixture.locator("div.match-fixture__wrapper")
        href = await wrapper.get_attribute("data-href")
        home_team_name = await fixture.locator(
            "span.match-fixture__team:nth-child(1) span.match-fixture__short-name"
        ).inner_text()
        away_team_name = await fixture.locator(
            "span.match-fixture__team:nth-child(3) span.match-fixture__short-name"
        ).inner_text()
        score_element = await fixture.locator("span.match-fixture__score").inner_text()
        score = score_element.strip() if score_element else None

        tmp["home_team_name"] = home_team_name
        tmp["away_team_name"] = away_team_name
        tmp["score"] = score.replace("\n", "").strip()
        tmp["href"] = f"https:{href}"

        # Add the task for processing;
        tasks.append(process_fixture(tmp, home_team_name, away_team_name))

    # Run concurrently
    results = await asyncio.gather(*tasks)

    for result in results:
        yield result


async def process_fixture(fixture, home, away):
    _clean = lambda text: text.strip().replace("\n", " ").strip()
    async for browser in get_browser():
        page = await browser.new_page()

        try:
            response = await page.goto(fixture["href"])
            assert response.status == 200
        except Exception as e:
            print("Error href >> ", e)
        await onetrust_accept_cookie(page)

        try:
            # Click on the "Line-ups" tab if available
            lineup_locator = page.locator('li[role="tab"]:has-text("Line-ups")')
            # matchstat_locator = page.locator('li[role="tab"]:has-text("Stats")')
            if await lineup_locator.count() > 0:
                await lineup_locator.click()
            else:
                print("Line-ups tab not found")
                return None
        except Exception as e:
            print(e, ">>> Error Line-ups")
            return None
        await page.wait_for_selector(".matchLineups")

        # Extract home and away team lineup data
        match_details = {"lineups": {}}
        home_team_locator = page.locator(
            ".teamList.mcLineUpContainter.homeLineup.active"
        )
        away_team_locator = page.locator(".teamList.mcLineUpContainter.awayLineup")

        home_team = await home_team_locator.all_text_contents()
        away_team = await away_team_locator.all_text_contents()

        home_assists = (
            await page.locator(".mc-summary__player-names-container")
            .nth(0)
            .locator(".mc-summary__assister")
            .all_text_contents()
        )
        home_assists = [
            re.split(r"’| \(|\)", item) for item in map(_clean, home_assists) if item
        ]
        away_assists = (
            await page.locator(".mc-summary__player-names-container")
            .nth(1)
            .locator(".mc-summary__assister")
            .all_text_contents()
        )
        away_assists = [
            re.split(r"’| \(|\)", item) for item in map(_clean, away_assists) if item
        ]

        assists = {home: [], away: []}

        def _extract_assists(given, which: str):
            for item in given:
                minute, name = (
                    (item[0], item[1])
                    if item[0].isdigit() or "+" in item[0]
                    else (item[2], item[0])
                )

                # Sum minutes if there are additional time (e.g. "45+2")
                assists[which].append(
                    {
                        "name": name.strip(),
                        "minute": sum(map(int, minute.strip().split("+"))),
                    }
                )

        _extract_assists(home_assists, home)
        _extract_assists(away_assists, away)

        match_details["assists"] = assists
        match_details["lineups"] = process_lineups(home_team, away_team, fixture)
        return match_details


def process_lineups(home_team, away_team, fixture):
    def _clean(team_text):
        return (
            team_text[0]
            .strip()
            .replace("\n", " ")
            .replace("  ", " ")
            .split(" Shirt number ")
        )

    cleaned_home = _clean(home_team)
    cleaned_away = _clean(away_team)
    lineups = {}

    for team_info, team_name in zip(
        [cleaned_home, cleaned_away],
        [fixture["home_team_name"], fixture["away_team_name"]],
    ):
        if not team_info:
            continue

        subi = next(
            (i for i, entry in enumerate(team_info) if "Substitutes" in entry), None
        )
        starters = team_info[: subi + 1] if subi else team_info
        substitutes = team_info[subi + 1 :] if subi else []

        formation = starters[0].split()[-2] if starters else None
        lineups[team_name] = {
            "formation": formation,
            "score": fixture["score"],
            "starters": process_players(
                starters[1:], "90"
            ),  # Skip first entry (team info)
            "substitutes": process_players(substitutes, "0"),
        }

    return lineups


def process_players(players, custom):
    def _extract_player_info(player_string):
        player_info = {}
        parts = player_string.split()
        player_info["name"] = " ".join(parts[1:3])  # First and last name

        player_info["yellow_cards"] = 1 if "Yellow" in parts else 0
        player_info["red_cards"] = 1 if "Red" in parts else 0
        player_info["goals"] = player_string.count("Goal") + player_string.count(
            "label.penaltyscore"
        )

        minutes_played = [
            part for part in parts if "'" in part and part.replace("'", "").isdigit()
        ]
        player_info["minutes"] = (
            minutes_played[0].strip("'") if minutes_played else custom
        )

        return player_info

    return {
        player_info["name"]: player_info
        for player_info in map(_extract_player_info, players)
    }


async def player_level_features(link, page):
    await page.goto(link)
    await onetrust_accept_cookie(page)

    squads = await page.locator("ul.squadListContainer.squad-list").all_text_contents()

    # Clean the squad list content by replacing newline characters and extra spaces
    cleaned_squads = [re.sub(r"\s+", " ", s.replace("\n", " ")).strip() for s in squads]

    def extract_player_data(from_text):
        # Split the text into sections by positions
        player_data = {}
        players_by_position = re.split(
            r"(Goalkeepers|Defenders|Midfielders|Forwards)", from_text[0]
        )

        # Iterate over positions and associated player details
        for i in range(1, len(players_by_position), 2):
            position = players_by_position[i].strip()
            players_section = players_by_position[i + 1].strip()

            # Split players based on "View Profile" which marks the end of player data
            player_entries = players_section.split("View Profile")

            # List to hold player data for the current position
            player_data[position] = []

            for entry in player_entries:
                entry = entry.strip()
                if not entry:
                    continue  # Skip empty entries

                player_info = {}

                # Extract player name before "Appearances"
                name_pos = entry.find("Appearances")
                if name_pos != -1:
                    player_info["name"] = entry[:name_pos].rsplit(" ", 1)[0].strip()
                else:
                    player_info["name"] = "Unknown"

                def extract_stat(pattern, text, default=0):
                    match = re.search(pattern, text)
                    return int(match.group(1)) if match else default

                # Extract numeric stats (default to 0 if not found)
                player_info["appearances"] = extract_stat(r"Appearances (\d+)", entry)
                player_info["goals"] = extract_stat(r"Goals (\d+)", entry)
                player_info["assists"] = extract_stat(r"Assists (\d+)", entry)
                player_info["clean_sheets"] = extract_stat(r"Clean sheets (\d+)", entry)
                player_info["saves"] = extract_stat(r"Saves (\d+)", entry)
                player_info["shots"] = extract_stat(r"Shots (\d+)", entry)

                # Append player info to the list for this position
                player_data[position].append(player_info)

        return player_data

    return extract_player_data(cleaned_squads)


# @cache_result(lambda club: '-'.join(club.split()))
async def aggregate_club_stats(club: str, page=Depends(get_page)):
    _links = await current_club_list(page)
    p_link = t_link = None

    async for name, link in _links:
        if club.lower() in name.lower():
            p_link = link.replace("overview", "squad?se=719")
            t_link = link.replace("overview", "results")
            break

    # Fetch team-level and player-level statistics
    teamattr = [tfeat async for tfeat in team_level_features(t_link, page)]
    player_level = await player_level_features(p_link, page)
    return {"team_stats": teamattr, "player_stats": player_level}


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
