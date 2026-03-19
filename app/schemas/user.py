from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional
from uuid import uuid4



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
    username: str
    email: str
    hashed_password: str

class AnonymousUserCreate(BaseModel):
    pass
    




