from typing import List, Optional
from pydantic import BaseModel

class AttackSchema(BaseModel):
    goals: int 
    goals_per_match: float
    headed_goals: int 
    goals_with_left: int 
    goals_with_right: int
    scored_pks: int 
    scored_free_kicks: int 
    shots: int 
    shots_on_target: int 
    shooting_accuracy: float 
    hit_woodwork: int
    big_chances_missed: int 
    
    
class TeamPlaySchema(BaseModel):
    assists: int
    passes: int 
    passes_per_match: float
    big_chances_created: int
    crosses: int 
    
    
class DisciplineSchema(BaseModel):
    yellow_cards: int 
    red_cards: int 
    fouls: int 
    offside: int 
    
    
class DefenceSchema(BaseModel):
    tackles: int 
    blocked_shots: int 
    interceptions: int 
    clearances: int 
    headed_clearance: int 
    
    
class ClubSchema(BaseModel):
    name: str 
    
class PlayerStatsSchema(ClubSchema):
    player_name: str 
    appearances: int 
    goals: int
    wins: int
    losses: int
    attack: Optional[AttackSchema]
    team_play: Optional[TeamPlaySchema]
    discipline: Optional[DisciplineSchema]
    defence: Optional[DefenceSchema]
    
    
class PlayerStatsSchemas(BaseModel):
    players: List[PlayerStatsSchema]
    
class FixtureSchema(BaseModel):
    home: ClubSchema 
    away: ClubSchema 
    time: str 
    
    
class TableSchema(BaseModel):
    position: int 
    club: ClubSchema
    played: int
    won: int 
    drawn: int 
    lost: int 
    gf: int 
    ga: int 
    gd: int 
    points: int 
    form: str  
    
    
class ResultSchema(BaseModel):
    home: ClubSchema 
    away: ClubSchema
    score: str 