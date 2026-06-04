from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    age: Optional[int] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    gender: Optional[str] = None
    level: Optional[str] = "beginner"
    weekly_volume: Optional[float] = 20.0
    best_5k: Optional[int] = None
    best_10k: Optional[int] = None
    goal_distance: Optional[str] = None
    goal_time: Optional[int] = None
    training_days: Optional[int] = 4

class UserResponse(BaseModel):
    id: int
    email: str
    level: str
    subscription_status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse