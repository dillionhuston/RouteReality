import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    """Application configuration."""
    
    BASE_DIR = BASE_DIR
    
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")
    
    SECRET_KEY = os.getenv("SECRET_KEY")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
    VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
    VAPID_EMAIL = os.getenv("VAPID_EMAIL")
    
    EMAIL = os.getenv("EMAIL")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    
    CIF_FILE = os.getenv("CIF_FILE", str(BASE_DIR / "app" / "data" / "Metro.cif"))
    
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", str(BASE_DIR / "tmp" / "uploads"))


config = Config()