from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.Database import get_db
from app.schemas.user import CreateUser, UserLogin
from app.Services.Auth.auth import AuthService
from app.repositories.user_repository import UserRepository
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
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    return AuthService.login_current_user(db, user_login)

@router.post("/anonymous")
def anonymous_user(db:Session = Depends(get_db)):
    return AuthService.create_anonymous_user(db=db)