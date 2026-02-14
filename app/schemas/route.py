from pydantic import BaseModel
from typing import Optional

class RouteOut(BaseModel):
    id: str
    name: str
    first_start_lat: float | None = None
    first_stop_lon: float | None = None
    first_stop_lat: float |None = None
    direction: Optional[str] = None 

    class Config:
        from_attributes = True 


class StopsPerRoute(BaseModel):
    id: str
    name: str
    sequence: Optional[int] = None  
    direction: Optional[str] = None  
    latitude: float | None = None
    longitude: float | None = None

    class Config:
        from_attributes = True  