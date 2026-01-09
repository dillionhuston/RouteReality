from app.schemas.journey import JourneyEventType
from sqlalchemy.orm import Session

class JourneyEventHandler():
    def __init__(self):
        pass

    def addEvent(event: JourneyEventType, db: Session):
        #TODO
        return