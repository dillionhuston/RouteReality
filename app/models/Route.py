from sqlalchemy import Column, String
from app.models.base import Base

class Route(Base):

    __tablename__ = "routes"

    id = Column(String, nullable=False, primary_key=True) # eg 12a 10J
    name = Column(String, nullable=False)
    direction= Column(String, nullable=False)