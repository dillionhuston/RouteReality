
from pydantic import BaseModel, Field
from typing import Optional


class StopPerRoute(BaseModel):
    id: str
    name: str
    order: int = Field(alias="sequence")

    class Config:
        from_attributes = True
        populate_by_name = True