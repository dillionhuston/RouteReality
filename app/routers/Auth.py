from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.Database import get_db
from app.schemas.user import CreateUser, UserLogin
from app.Services.auth import AuthService
from app.dependencies.dependency import get_auth_service, get_user_repository


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
async def register(
    user: CreateUser,
    authservice: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db)):

    user = await authservice.register_new_user(user)
    return user

@router.post("/login")
async def login(
    user_login: UserLogin,
    authservice: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db)):
    return await authservice.login(user_login)

