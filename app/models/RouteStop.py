from sqlalchemy import Column, String, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.models.base import Base


class RouteStop(Base):
    __tablename__ = "route_stops"  

    route_id = Column(String, ForeignKey("routes.id"), primary_key=True)  
    stop_id = Column(String, ForeignKey("stops.id"), primary_key=True)    
    sequence = Column(Integer, nullable=False)
    direction = Column(String)  # outbound/inbound

    route = relationship('Route', back_populates='route_stops')
    stop = relationship('Stop', back_populates='route_stops')