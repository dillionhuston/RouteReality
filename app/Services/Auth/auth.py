import uuid
import app.core.security as security

from fastapi import HTTPException, status

from app.schemas.user import CreateUser, UserLogin, AddUser
from app.models.User import User

from app.repositories.user_repository import UserRepository

class AuthService:

    def __init__(self, UserRepo: UserRepository):
        self.userrepo = UserRepo

    async def register_new_user(self, user: CreateUser):

        existing_user = await self.userrepo.GetUserByUsername(user.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered."
            )

        # Validate password length in bytes
        password_bytes = user.password.encode('utf-8')
        if len(password_bytes) > 72:
            raise HTTPException(
                status_code=400,
                detail="Password too long (max 72 bytes)."
            )

        hashed_password = security.create_password_hash(password=user.password)

        user_to_save = AddUser(
            id=str(uuid.uuid4()),   
            email=user.email,
            username=user.username,
            hashed_password=hashed_password
        )

        saved_user = await self.userrepo.AddUser(user_to_save)
        return {"user_id": saved_user}

   
    async def login(self, user_login: UserLogin):
        try:
            db_user = await self.userrepo.GetUserByEmail(user_login.email)
            if not db_user or not security.verify_password(user_login.password, db_user.hashed_password):
                raise Exception
        except Exception as e:
                raise Exception(
                    "Incorrect username/email or password",
                )
       
        token = security.generate_web_token({"sub": db_user.id})
        return{
            "id": db_user.id,
            "username": db_user.username,
            "email": db_user.email,
            "access_token": token,
            "token_type": "bearer"
        }