from passlib.context import CryptContext
import jwt
from datetime import datetime, timedelta, timezone

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# For now hardcode (change to env in production!)
SECRET_KEY = "your-very-long-random-secret-key-change-this-please"  # min 32 chars
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_password_hash(password: str):
    return pwd_context.hash(password)

def verify_password(password_string: str, password_hash: str) -> bool:
    return pwd_context.verify(password_string, password_hash)

def generate_web_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_web_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None  # or raise exception
    except jwt.InvalidTokenError:
        return None