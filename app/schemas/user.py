from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional
from uuid import uuid4
from datetime import date, time, datetime


class CreateUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))    
    username: str
    email: str
    password: str



class UserLogin(BaseModel):
    email: str
    password: str

    
    model_config = {"arbitrary_types_allowed": True}


class AddUser(BaseModel):
    id: str
    username: str
    email: str
    hashed_password: str

class AnonymousUserCreate(BaseModel):
    pass
    



class UserProfileResponse(BaseModel):
    id: str
    username: Optional[str]
    email: Optional[str]
    created_at: datetime
    is_guest: bool

class UserStatsResponse(BaseModel):
    points: int
    streak_current: int
    streak_best: int
    total_reports: int
    accurate_reports: int
    accuracy_percentage: float
    last_report_date: Optional[date]
    badges: list