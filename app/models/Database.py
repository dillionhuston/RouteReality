import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.base import Base
"""TODO move journey, stop models into 2 main files, rather than having 5 different files for 2 things"""
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    echo=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind= engine
    )

# get use access to the database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

