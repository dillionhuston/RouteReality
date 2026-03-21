from fastapi import APIRouter
from datetime import datetime, timezone

router = APIRouter(prefix="/time", tags=["System"])

@router.get("")
def get_server_time():
    return {"server_time": datetime.now(timezone.utc).isoformat()}