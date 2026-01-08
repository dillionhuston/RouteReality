import dotenv
import os
from app.models.Database import engine
from app.models.base import Base
from app.models.Journey import Journey
from app.models.Route import Route
from app.models.Stop import Stop


# please NEVER  use drop all in a live system. This is only used to updated tables in dev. Always use Alembic
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)