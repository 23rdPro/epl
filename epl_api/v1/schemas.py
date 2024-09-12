from typing import Optional
from pydantic import BaseModel


class AttackSchema(BaseModel):
    goals: Optional[str] = "N/A"
    goals_per_match: Optional[str] = "N/A"
    headed_goals: Optional[str] = "N/A"
    goals_with_left_foot: Optional[str] = "N/A"
    goals_with_right_foot: Optional[str] = "N/A"
    penalties_scored: Optional[str] = "N/A"
    freekicks_scored: Optional[str] = "N/A"
    shots: Optional[str] = "N/A"
    shots_on_target: Optional[str] = "N/A"
    shooting_accuracy: Optional[str] = "N/A"  # percentage
    hit_woodwork: Optional[str] = "N/A"
    big_chances_missed: Optional[str] = "N/A"


class GoalkeepingSchema(BaseModel):
    saves: Optional[str] = "N/A"
    penalties_saved: Optional[str] = "N/A"
    punches: Optional[str] = "N/A"
    high_claims: Optional[str] = "N/A"
    catches: Optional[str] = "N/A"
    sweeper_clearances: Optional[str] = "N/A"
    throw_outs: Optional[str] = "N/A"
    goal_kicks: Optional[str] = "N/A"


class TeamPlaySchema(BaseModel):
    assists: Optional[str] = "N/A"
    passes: Optional[str] = "N/A"
    passes_per_match: Optional[str] = "N/A"
    big_chances_created: Optional[str] = "N/A"
    crosses: Optional[str] = "N/A"
    cross_accuracy: Optional[str] = "N/A"
    through_balls: Optional[str] = "N/A"
    accurate_long_balls: Optional[str] = "N/A"
    goals: Optional[str] = "N/A"


class DisciplineSchema(BaseModel):
    yellow_cards: Optional[str] = "N/A"
    red_cards: Optional[str] = "N/A"
    fouls: Optional[str] = "N/A"
    offside: Optional[str] = "N/A"


class DefenceSchema(BaseModel):
    tackles: Optional[str] = "N/A"
    blocked_shots: Optional[str] = "N/A"
    interceptions: Optional[str] = "N/A"
    clearances: Optional[str] = "N/A"
    headed_clearance: Optional[str] = "N/A"
    clean_sheets: Optional[str] = "N/A"
    goals_conceded: Optional[str] = "N/A"
    tackles_success: Optional[str] = "N/A"
    last_man_tackles: Optional[str] = "N/A"
    clearances_off_line: Optional[str] = "N/A"
    recoveries: Optional[str] = "N/A"
    duels_won: Optional[str] = "N/A"
    duels_lost: Optional[str] = "N/A"
    successful_50_50s: Optional[str] = "N/A"
    aerial_battles_won: Optional[str] = "N/A"
    aerial_battles_lost: Optional[str] = "N/A"
    own_goals: Optional[str] = "N/A"
    errors_leading_to_goals: Optional[str] = "N/A"  # TODO: maybe not needed
    errors_leading_to_goal: Optional[str] = "N/A"


class PlayerStatsSchema(BaseModel):
    player_name: Optional[str] = "N/A"
    appearances: Optional[str] = "N/A"
    goals: Optional[str] = "N/A"
    wins: Optional[str] = "N/A"
    losses: Optional[str] = "N/A"
    attack: AttackSchema
    team_play: TeamPlaySchema
    discipline: DisciplineSchema
    defence: DefenceSchema


class FixtureSchema(BaseModel):
    home: Optional[str] = "N/A"
    away: Optional[str] = "N/A"
    time: Optional[str] = "N/A"


class TableSchema(BaseModel):
    position: Optional[str] = "N/A"
    club: Optional[str] = "N/A"
    played: Optional[str] = "N/A"
    won: Optional[str] = "N/A"
    drawn: Optional[str] = "N/A"
    lost: Optional[str] = "N/A"
    gf: Optional[str] = "N/A"
    ga: Optional[str] = "N/A"
    gd: Optional[str] = "N/A"
    points: Optional[str] = "N/A"
    form: Optional[str] = "N/A"


class ResultSchema(BaseModel):
    home: Optional[str] = "N/A"
    away: Optional[str] = "N/A"
    score: Optional[str] = "N/A"
