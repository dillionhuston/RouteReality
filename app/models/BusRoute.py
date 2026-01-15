from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from app.models.base import Base

class Route(Base):
    __tablename__ = "routes"

    id = Column(String, nullable=False, primary_key=True)  # e.g., 12a, 10J
    name = Column(String, nullable=False)
    direction = Column(String, nullable=True)

    route_stops = relationship('RouteStop', back_populates='route')