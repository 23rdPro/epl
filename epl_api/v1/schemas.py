from typing import Optional
from pydantic import BaseModel


class AttackSchema(BaseModel):
    goals: Optional[int] = 0
    goals_per_match: Optional[float] = 0
    headed_goals: Optional[int] = 0
    goals_with_left: Optional[int] = 0
    goals_with_right: Optional[int] = 0
    scored_pks: Optional[int] = 0
    scored_free_kicks: Optional[int] = 0
    shots: Optional[int] = 0
    shots_on_target: Optional[int] = 0
    shooting_accuracy: Optional[float] = 0
    hit_woodwork: Optional[int] = 0
    big_chances_missed: Optional[int] = 0


class TeamPlaySchema(BaseModel):
    assists: Optional[int] = 0
    passes: Optional[int] = 0
    passes_per_match: Optional[float] = 0
    big_chances_created: Optional[int] = 0 
    crosses: Optional[int] = 0


class DisciplineSchema(BaseModel):
    yellow_cards: Optional[int] = 0
    red_cards: Optional[int] = 0
    fouls: Optional[int] = 0
    offside: Optional[int] = 0


class DefenceSchema(BaseModel):
    tackles: Optional[int] = 0
    blocked_shots: Optional[int] = 0
    interceptions: Optional[int] = 0
    clearances: Optional[int] = 0
    headed_clearance: Optional[int] = 0


class PlayerStatsSchema(BaseModel):
    player_name: str
    appearances: Optional[int] = 0
    goals: Optional[int] = 0
    wins: Optional[int] = 0
    losses: Optional[int] = 0
    attack: Optional[AttackSchema]
    team_play: Optional[TeamPlaySchema]
    discipline: Optional[DisciplineSchema]
    defence: Optional[DefenceSchema]

class FixtureSchema(BaseModel):
    home: str
    away: str
    time: str


class TableSchema(BaseModel):
    position: Optional[str] = ""
    club: str
    played: Optional[str] = ""
    won: Optional[str] = ""
    drawn: Optional[str] = ""
    lost: Optional[str] = ""
    gf: Optional[str] = ""
    ga: Optional[str] = ""
    gd: Optional[str] = ""
    points: Optional[str] = ""
    form: Optional[str] = ""


class ResultSchema(BaseModel):
    home: str
    away: str
    score: str
