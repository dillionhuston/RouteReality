import dotenv
import os
from app.models.Database import engine
from app.models.base import Base
from app.models.Journey import Journey
from app.models.Route import Route
from app.models.Stop import Stop


Base.metadata.create_all(engine)