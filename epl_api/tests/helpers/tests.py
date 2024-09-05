import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from epl_api.v1.helper import (
    extract_attack_stats,
    extract_defence_stats,
    extract_discipline_stats,
    extract_player_stats,
    extract_team_play_stats,
    get_player_stats,
)
from epl_api.v1.schema import (
    AttackSchema,
    DefenceSchema,
    DisciplineSchema,
    TeamPlaySchema,
)
from epl_api.v1.utils import cache_result


@pytest.mark.asyncio
@patch("epl_api.v1.helper.async_playwright")
async def test_get_player_stats(playwright_mocked):
    brs = AsyncMock()
    pge = AsyncMock()
    playwright_mocked.return_value.__aenter__.return_value.chromium.launch.return_value = (
        brs
    )
    brs.new_page.return_value = pge
    _html = """
    <div class="table playerIndex player-listing">
        <tbody class="dataContainer indexSection">
            <tr class="player">
                <a class="player__name" href="/players/1234/Ilkay-Gundogan/overview">Ilkay Gundogan</a>
                <td class="player__position">Midfielder</td>
                <span class="player__country">Germany</span>
            </tr>
        </tbody>
    </div>
    """
    pge.content.return_value = _html
    p_name = "Ilkay Gundogan"
    result = await get_player_stats(player_name=p_name)

    expected_result = [
        {
            "name": "Ilkay Gundogan",
            "link": "https://www.premierleague.com/players/1234/Ilkay-Gundogan/overview",
            "position": "Midfielder",
            "nationality": "Germany",
        },
    ]
    assert result == expected_result
    await pge.close()
    pge.goto.assert_called_once_with("https://www.premierleague.com/players")
    pge.fill.assert_called_once_with('input[placeholder="Search for a Player"]', p_name)
    pge.keyboard.press.assert_called_once_with("Enter")
    pge.wait_for_selector.assert_called_once_with("tbody.dataContainer.indexSection")
    pge.content.assert_called_once()
    pge.close.assert_called_once()


@pytest.mark.asyncio
async def test_extract_attack_stats():
    # Mock BeautifulSoup
    bs = MagicMock()

    # Mock the `find` method and its return value's `text.strip()`
    bs.find.side_effect = lambda class_name, class_: MagicMock(
        text=MagicMock(
            strip=MagicMock(
                return_value={
                    "goals": "10",
                    "goals_per_match": "0.5",
                    "headed_goals": "2",
                    "goals_with_left": "3",
                    "goals_with_right": "5",
                    "scored_pks": "1",
                    "scored_free_kicks": "0",
                    "shots": "30",
                    "shots_on_target": "15",
                    "shooting_accuracy": "50%",
                    "hit_woodwork": "2",
                    "big_chances_missed": "4",
                }[class_]
            )
        )
    )
    result = await extract_attack_stats(bs)

    expected_result = AttackSchema(
        goals=10,
        goals_per_match=0.5,
        headed_goals=2,
        goals_with_left=3,
        goals_with_right=5,
        scored_pks=1,
        scored_free_kicks=0,
        shots=30,
        shots_on_target=15,
        shooting_accuracy=50.0,
        hit_woodwork=2,
        big_chances_missed=4,
    )

    assert result == expected_result

    expected_calls = [
        ("span", "goals"),
        ("span", "goals_per_match"),
        ("span", "headed_goals"),
        ("span", "goals_with_left"),
        ("span", "goals_with_right"),
        ("span", "scored_pks"),
        ("span", "scored_free_kicks"),
        ("span", "shots"),
        ("span", "shots_on_target"),
        ("span", "shooting_accuracy"),
        ("span", "hit_woodwork"),
        ("span", "big_chances_missed"),
    ]
    # assert bs.find.call_args_list == [((key, value),) for key, value in expected_calls]


@pytest.mark.asyncio
async def test_extract_team_play_stats():
    bs = MagicMock()
    bs.find.side_effect = lambda class_name, class_: MagicMock(
        text=MagicMock(
            strip=MagicMock(
                return_value={
                    "assists": "7",
                    "passes": "1200",
                    "passes_per_match": "85.7",
                    "big_chances_created": "10",
                    "crosses": "50",
                }[class_]
            )
        )
    )

    result = await extract_team_play_stats(bs)

    expected_result = TeamPlaySchema(
        assists=7,
        passes=1200,
        passes_per_match=85.7,
        big_chances_created=10,
        crosses=50,
    )

    assert result == expected_result

    expected_calls = [
        ("span", "assists"),
        ("span", "passes"),
        ("span", "passes_per_match"),
        ("span", "big_chances_created"),
        ("span", "crosses"),
    ]
    # assert bs.find.call_args_list == [((key, value),) for key, value in expected_calls]


@pytest.mark.asyncio
async def test_extract_discipline_stats():
    bs = MagicMock()
    bs.find.side_effect = lambda class_name, class_: MagicMock(
        text=MagicMock(
            strip=MagicMock(
                return_value={
                    "yellow_cards": "5",
                    "red_cards": "1",
                    "fouls": "30",
                    "offside": "10",
                }[class_]
            )
        )
    )
    result = await extract_discipline_stats(bs)

    expected_result = DisciplineSchema(
        yellow_cards=5,
        red_cards=1,
        fouls=30,
        offside=10,
    )

    assert result == expected_result

    expected_calls = [
        ("span", "yellow_cards"),
        ("span", "red_cards"),
        ("span", "fouls"),
        ("span", "offside"),
    ]
    # assert bs.find.call_args_list == [((key, value),) for key, value in expected_calls]


@pytest.mark.asyncio
async def test_extract_defence_stats():
    bs = MagicMock()
    bs.find.side_effect = lambda class_name, class_: MagicMock(
        text=MagicMock(
            strip=MagicMock(
                return_value={
                    "tackles": "45",
                    "blocked_shots": "10",
                    "interceptions": "20",
                    "clearances": "50",
                    "headed_clearance": "25",
                }[class_]
            )
        )
    )

    result = await extract_defence_stats(bs)

    expected_result = DefenceSchema(
        tackles=45,
        blocked_shots=10,
        interceptions=20,
        clearances=50,
        headed_clearance=25,
    )

    assert result == expected_result

    expected_calls = [
        ("span", "tackles"),
        ("span", "blocked_shots"),
        ("span", "interceptions"),
        ("span", "clearances"),
        ("span", "headed_clearance"),
    ]
    # assert bs.find.call_args_list == [((key, value),) for key, value in expected_calls]


@pytest.mark.asyncio
@patch("epl_api.v1.helper.async_playwright")
async def test_extract_player_stats(mock_playwright_extract):
    pytest.skip("Todo")
    brs = AsyncMock()
    pge = AsyncMock()
    mock_playwright_extract.return_value.__aenter__.return_value.chromium.launch.return_value.__aenter__.return_value = (
        brs
    )
    brs.new_page.return_value = pge

    _html = """
    <div class="player-stats">
        <span class="appearances">30</span>
        <span class="goals">10</span>
        <span class="wins">20</span>
        <span class="losses">5</span>
    </div>
    <div class="name">Test Player</div>
    """
    pge.content.return_value = _html

    with patch("epl_api.v1.helper.BeautifulSoup") as mock_soup, patch(
        "epl_api.v1.helper.extract_attack_stats", return_value="mocked_attack"
    ), patch("epl_api.v1.helper.extract_team_play_stats", return_value="mocked_team_play"), patch(
        "epl_api.v1.helper.extract_discipline_stats", return_value="mocked_discipline"
    ), patch(
        "epl_api.v1.helper.extract_defence_stats", return_value="mocked_defence"
    ):

        mock_soup.return_value.find.side_effect = lambda name, class_: MagicMock(
            text=MagicMock(
                strip=MagicMock(
                    return_value={
                        "appearances": "30",
                        "goals": "10",
                        "wins": "20",
                        "losses": "5",
                        "name": "Test Player",
                    }[class_]
                )
            )
        )

        result = await extract_player_stats(
            "https://www.premierleague.com/players/12345/Test-Player/overview"
        )

        expected_result = {
            "player_name": "Test Player",
            "appearances": 30,
            "goals": 10,
            "wins": 20,
            "losses": 5,
            "attack": "mocked_attack",
            "team_play": "mocked_team_play",
            "discipline": "mocked_discipline",
            "defence": "mocked_defence",
        }

        # assert result == expected_result

        # pge.goto.assert_called_once_with(
        #     "https://www.premierleague.com/players/12345/Test-Player/overview"
        # )
        # pge.click.assert_called_once_with('a.generic-tabs-nav__link[data-text="Stats"]')
        # pge.wait_for_selector.assert_called_once_with("div.player-stats")
        # pge.close.assert_called_once()


# Test other decorators


class MockSettings:
    CACHE_TIMEOUT = 60


@pytest.fixture
def mock_settings():
    return MockSettings()


@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
async def test_cache_result_cache_hit(mock_cache, mock_settings):
    mock_cache.get = AsyncMock(return_value={"mocked_key": "mocked_value"})
    mock_cache.set = AsyncMock()

    # function to decorate
    async def sample_view_func(arg1, arg2):
        return {"computed_key": f"{arg1}_{arg2}"}

    # key func for caching
    def gen_key(arg1, arg2):
        return f"cache_key_{arg1}_{arg2}"

    # Apply the decorator
    decorated_func = cache_result(gen_key)(sample_view_func)

    # Call the decorated function
    result = await decorated_func("foo", "bar")

    # Assertions
    assert result == {"mocked_key": "mocked_value"}
    mock_cache.get.assert_called_once_with("cache_key_foo_bar")
    mock_cache.set.assert_not_called()  # Should not be called if cache hit


@pytest.mark.asyncio
@patch("epl_api.v1.utils.cache")
async def test_cache_result_cache_miss(mock_cache, mock_settings):
    # Mock the cache get method to return None (cache miss)
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()

    async def sample_func(arg1, arg2):
        return {"computed_key": f"{arg1}_{arg2}"}

    def gen_key(arg1, arg2):
        return f"cache_key_{arg1}_{arg2}"

    decorated_func = cache_result(gen_key)(sample_func)

    result = await decorated_func("foo", "bar")

    # Assertions
    assert result == {"computed_key": "foo_bar"}
    mock_cache.get.assert_called_once_with("cache_key_foo_bar")
    # mock_cache.set.assert_called_once_with(
    #     "cache_key_foo_bar", result, timeout=mock_settings.CACHE_TIMEOUT
    # )
