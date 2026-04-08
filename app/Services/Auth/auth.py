import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.Services.Auth import data, security
from app.schemas.user import CreateUser, UserLogin, AddUser
from app.models.User import User

class AuthService:

    @staticmethod
    def register_new_user(db: Session, user: CreateUser):

        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == user.email) | (User.username == user.username)
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered."
            )

        # Validate password length in bytes (bcrypt limit)
        password_bytes = user.password.encode('utf-8')
        if len(password_bytes) > 72:
            raise HTTPException(
                status_code=400,
                detail="Password too long (max 72 bytes)."
            )

        # Hash the password
        hashed_password = security.create_password_hash(password=user.password)

        # Prepare user object for saving
        user_to_save = AddUser(
            id=str(uuid.uuid4()),   
            email=user.email,
            username=user.username,
            hashed_password=hashed_password
        )

        saved_user = data.save_user_details(db, user_to_save)
        return {"user_id": saved_user}

    @staticmethod
    def auth_user(db: Session, user_login: UserLogin):
        db_user = data.get_user_details(db, email=user_login.email)
        if not db_user:
            db_user = data.get_user_details(db, username=user_login.email)

        if not db_user:
            return None

        if not security.verify_password(user_login.password, db_user.hashed_password):
            return None

        return db_user

    @staticmethod
    def login_current_user(db: Session, user_login: UserLogin):
        db_user = AuthService.auth_user(db, user_login)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username/email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = security.generate_web_token({"sub": db_user.id})
        return {"access_token": token, "token_type": "bearer"}

    @staticmethod
    def create_anonymous_user(db: Session):
        random_user = str(uuid.uuid4())
        fake_password = str(uuid.uuid4())

        anonymous_user = User(
            id=str(uuid.uuid4()),
            email=None,
            username=random_user,
            hashed_password=security.create_password_hash(fake_password)
        )

        db_user = data.save_user_details(
            db=db,
            user_data=anonymous_user
        )
        db_user.is_anonymous = True
        db.commit()
        db.refresh(db_user)

        token = security.generate_web_token({"sub": db_user.id})

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": db_user.id,
                "username": db_user.username,
                "is_anonymous": True
            }
        }