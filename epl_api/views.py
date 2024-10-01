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
    try:
        await page.goto(link)
        await onetrust_accept_cookie(page)

        fixtures = await page.locator(
            "div.fixtures__matches-list ul.matchList li.match-fixture"
        ).all()

        for fixture in fixtures:
            wrapper = fixture.locator("div.match-fixture__wrapper")
            href = await wrapper.get_attribute("data-href")
            if href:
                link_ = f"https:{href}"
                yield link_

                await page.goto(link_)
                await onetrust_accept_cookie(page)

                try:
                    # Get all the tab elements
                    tabs = await page.locator('li[role="tab"]').all()

                    # Check and click the "Line-ups"
                    for tab in tabs:
                        if (
                            tab_text := await tab.inner_text()
                        ) and "Line-ups" in tab_text:
                            await tab.click()
                            break
                    else:
                        print("Line-ups tab not found")
                except Exception as e:
                    print(e, ">>> Error")
                await page.wait_for_selector(".matchLineups")

                match_details = {"lineups": {}}
                home_team_locator = page.locator(
                    ".teamList.mcLineUpContainter.homeLineup.active"
                )
                home_team = await home_team_locator.all_text_contents()

                away_team_locator = page.locator(
                    ".teamList.mcLineUpContainter.awayLineup"
                )
                away_team = await away_team_locator.all_text_contents()

                def _clean(text: str) -> str:
                    return (
                        text[0]
                        .strip()
                        .replace("\n", " ")
                        .replace("  ", " ")
                        .split(" Shirt number ")
                    )

                cleaned_home = _clean(home_team)
                cleaned_away = _clean(away_team)

                for team_info, team_name in zip(
                    [cleaned_home, cleaned_away], ["Home", "Away"]
                ):
                    if not team_info:
                        continue

                    subi = next(
                        i for i, entry in enumerate(team_info) if "Substitutes" in entry
                    )
                    starters = team_info[:subi]
                    substitutes = team_info[subi + 1 :]

                    # Extract formation and team name from the first entry
                    first_entry_parts = starters[0].split()
                    formation = first_entry_parts[-2]
                    match_details["lineups"][team_name] = {
                        "formation": formation,
                        "starters": {},
                        "substitutes": {},
                    }

                    def _extract_player_info(player_string):
                        player_info = {}
                        parts = player_string.split()

                        # Extracting shirt number and name
                        player_info["name"] = " ".join(
                            parts[1:3]
                        )  # First and last name

                        # Default card and goal values
                        player_info["yellow_cards"] = 1 if "Yellow" in parts else 0
                        player_info["red_cards"] = 1 if "Red" in parts else 0

                        # Count occurrences of "Goal" to determine total goals
                        player_info["goals"] = player_string.count("Goal")
                        player_info["goals"] += player_string.count(
                            "label.penaltyscore"
                        )

                        # Minutes played (if any)
                        minutes_played = [part for part in parts if "'" in part]
                        player_info["minutes"] = (
                            minutes_played[0].strip("'") if minutes_played else "90"
                        )

                        return player_info

                    # Process starters
                    for entry in starters[1:]:  # Skip the first entry (team info)
                        player_info = _extract_player_info(entry)
                        name = player_info["name"]

                        if name not in match_details["lineups"][team_name]["starters"]:
                            match_details["lineups"][team_name]["starters"][name] = {
                                "goals": player_info["goals"],
                                "yellow_cards": player_info["yellow_cards"],
                                "red_cards": player_info["red_cards"],
                                "minutes": player_info["minutes"],
                            }
                        else:
                            # Accumulate stats for players appearing multiple times
                            existing_player = match_details["lineups"][team_name][
                                "starters"
                            ][name]
                            existing_player["goals"] += player_info["goals"]
                            existing_player["yellow_cards"] += player_info[
                                "yellow_cards"
                            ]
                            existing_player["red_cards"] += player_info["red_cards"]

                    # Process substitutes
                    for entry in substitutes:
                        player_info = _extract_player_info(entry)
                        name = player_info["name"]
                        match_details["lineups"][team_name]["substitutes"][name] = {
                            "goals": player_info["goals"],
                            "yellow_cards": player_info["yellow_cards"],
                            "red_cards": player_info["red_cards"],
                            "minutes": player_info["minutes"],
                        }

                yield match_details
    except Exception as e:
        print(e, ">>> Error")


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
