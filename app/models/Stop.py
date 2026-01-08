from sqlalchemy import Column, String, Float
from sqlalchemy.orm import relationship
from app.models.base import Base


class Stop(Base):
    __tablename__ = "stops"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    longitude = Column(Float, nullable=False)
    latitude = Column(Float, nullable=False)

    route_stops = relationship('RouteStop', back_populates='stop')