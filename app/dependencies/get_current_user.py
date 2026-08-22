from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.Database import get_db
from app.models.User import User
from app.repositories.user_repository import UserRepository
from app.core.security import verify_web_token
from app.exceptions.exceptions import AuthenticationError, UserNotFoundError

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)):

    if not credentials:
        raise AuthenticationError(detail="Not authenticated")

    token = credentials.credentials
    payload = verify_web_token(token) 
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError(detail="Invalid token (missing subject)")

    user_repo = UserRepository(db)
    user = await user_repo.GetUserByID(user_id)
    if not user:
        raise UserNotFoundError()

    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)):
    
    if not credentials:
        return None

    try:
        token = credentials.credentials
        payload = verify_web_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None

        user_repo = UserRepository(db)
        user = await user_repo.GetUserByID(user_id)
        return user
    except Exception:
        return None