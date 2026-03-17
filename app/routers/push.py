import hashlib
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.models.Database import get_db
from app.models.PushSubscription import PushSubscription
from pydantic import BaseModel

router = APIRouter(prefix="/push", tags=["Push Notifications"])

class SubscriptionSchema(BaseModel):
    service_id: str
    endpoint: str
    keys: dict  

@router.post("/subscribe")
def subscribe(sub: SubscriptionSchema, db: Session = Depends(get_db)):
    sub_id = hashlib.sha256(sub.endpoint.encode()).hexdigest()
    existing = db.get(PushSubscription, sub_id)
    if existing:
        existing.keys = sub.keys
        existing.service_id = sub.service_id
    else:
        new_sub = PushSubscription(
            id=sub_id,
            service_id=sub.service_id,
            endpoint=sub.endpoint,
            keys=sub.keys,
        )
        db.add(new_sub)
    db.commit()
    return {"status": "subscribed"}

@router.post("/unsubscribe")
def unsubscribe(endpoint: str, db: Session = Depends(get_db)):
    sub_id = hashlib.sha256(endpoint.encode()).hexdigest()
    sub = db.get(PushSubscription, sub_id)
    if sub:
        db.delete(sub)
        db.commit()
    return {"status": "unsubscribed"}