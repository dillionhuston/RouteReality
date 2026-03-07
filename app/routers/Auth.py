from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.models.Database import get_db
from app.schemas.user import CreateUser, UserLogin
from app.Services.Auth.auth import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register")
def register(user: CreateUser, db: Session = Depends(get_db)):
    return AuthService.register_new_user(db, user)

@router.post("/login")
def login(user_login: UserLogin, db: Session = Depends(get_db)):
    return AuthService.login_current_user(db, user_login)

@router.post("/anonymous")
def anonymous_user(db:Session = Depends(get_db)):
    return AuthService.create_anonymous_user(db=db)