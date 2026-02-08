from sqlalchemy import Column, String, ForeignKey, Integer, Float, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID as PG_UUID   

from app.models.Database import Base
import uuid

class Route(Base):
    __tablename__ = "routes"

    id = Column(String(50), primary_key=True)  
    name = Column(String, nullable=False)
    direction = Column(String, nullable=True)
    official_timetable = Column(JSON, nullable=True)
    timetable_last_updated = Column(DateTime, nullable=True)

    route_stops = relationship('RouteStop', back_populates='route')


class Stop(Base):
    __tablename__ = "stops"

    id = Column(String(32), primary_key=True)  
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
   
    route_stops = relationship('RouteStop', back_populates='stop')


class RouteStop(Base):
    __tablename__ = "route_stops"

    route_id = Column(String(50), ForeignKey("routes.id"), primary_key=True)
    stop_id  = Column(String(32), ForeignKey("stops.id"), primary_key=True)
    sequence = Column(Integer, nullable=False)
    direction = Column(String, nullable=True)

    route = relationship('Route', back_populates='route_stops')
    stop  = relationship('Stop', back_populates='route_stops')