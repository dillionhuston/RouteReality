from pydantic import BaseModel, EmailStr, Field, model_validator
from typing import Optional
from uuid import uuid4



class CreateUser(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))    
    username: str
    email: EmailStr
    password: str



class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @model_validator(mode="after")
    def set_email_or_username(self) -> "UserLogin":
        self.email_or_username = self.email
        return self

    model_config = {"arbitrary_types_allowed": True}


class AddUser(BaseModel):
    username: str
    email: EmailStr
    hashed_password: str

class AnonymousUserCreate(BaseModel):
    pass
    




