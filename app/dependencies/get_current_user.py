# app/dependencies/auth.py
# (or you can put it in app/Services/Auth/security.py or a new dependencies file)

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.models.Database import get_db
from app.models.User import User
from app.Services.Auth import security

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login",          
    scheme_name="Bearer",
    description="JWT access token"
)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Session = Depends(get_db)) -> User:
    """
    Dependency that:
    - Validates the JWT token
    - Extracts user ID from 'sub'
    - Fetches the user from the database
    - Returns the User model instance (or raises 401)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = security.verify_web_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
   

    if user is None:
        raise credentials_exception

    return user


# Optional: stricter version for routes that anonymous users should NOT access
def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Used  when a endpoint requires a registered user.
    """
    if current_user.is_anonymous:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a registered account (anonymous users not allowed)"
        )
    #TODO also check if user.is_active, email_verified, etc. in the future
    return current_user


def get_any_authenticated_user(
    current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """
    Use when anonymous users are allowed to perform the action.
    """
    return current_user