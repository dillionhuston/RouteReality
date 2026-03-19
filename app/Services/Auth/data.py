import uuid
from sqlalchemy.orm import Session
from app.models.User import User
from app.schemas.user import AddUser   
def save_user_details(db: Session, user_data: AddUser):
    db_user = User(
        id=str(uuid.uuid4()),
        email=user_data.email,
        username=user_data.username if hasattr(user_data, 'username') else None,
        hashed_password=user_data.hashed_password  
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user_details(db: Session, email: str = None, username: str = None):
    query = db.query(User)
    if  email:
        query = query.filter(User.email == email)
    if username:
        query = query.filter(User.username == username)
    return query.first() 