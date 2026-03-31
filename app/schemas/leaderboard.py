from pydantic import BaseModel


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    points: int
    total_reports: int
    accuracy: float