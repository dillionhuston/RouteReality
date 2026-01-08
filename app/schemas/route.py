from pydantic import BaseModel
from typing import Optional

class RouteOut(BaseModel):
    id: str
    name: str
    direction: Optional[str] = None 

    class Config:
        from_attributes = True 


