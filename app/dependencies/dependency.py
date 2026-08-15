# app/dependencies/services.py
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.Database import get_db
from app.repositories.user_repository import UserRepository
from app.Services.Auth.auth import AuthService

def get_auth_service(db: Session = Depends(get_db)):
    repo = UserRepository(db)
    return AuthService(repo)

def get_user_repository(db: Session = Depends(get_db)):
    return UserRepository(db)