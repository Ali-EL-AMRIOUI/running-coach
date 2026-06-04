from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WorkoutCreate(BaseModel):
    plan_id: Optional[int] = None
    workout_type: str  # easy, tempo, intervals, long, recovery
    distance: float  # km
    duration: int  # minutes
    avg_hr: Optional[int] = None
    perceived_effort: Optional[int] = None  # 1-10
    notes: Optional[str] = None
    completed: bool = True

class WorkoutResponse(BaseModel):
    id: int
    user_id: int
    plan_id: Optional[int]
    date: datetime
    workout_type: str
    distance: float
    duration: int
    avg_hr: Optional[int]
    perceived_effort: Optional[int]
    notes: Optional[str]
    completed: bool
    
    class Config:
        from_attributes = True