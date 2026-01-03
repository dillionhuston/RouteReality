from sqlalchemy import Column, String, ForeignKey, Integer, Float
from app.models.base import Base


class Stop(Base):

    __tablename__ = "stops"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    route_id = Column(String, ForeignKey("routes.id"), nullable=False)
    sequence = Column(Integer, nullable=False)
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)