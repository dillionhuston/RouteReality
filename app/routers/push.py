# app/routers/push.py
import hashlib
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.models.Database import get_db
from app.models.PushSubscription import PushSubscription
from app.dependencies.get_current_user import get_current_user
from app.models.User import User
from app.Services.push_service.push_service import VAPID_PUBLIC_KEY, send_notifications_to_service

router = APIRouter(prefix="/push", tags=["Push Notifications"])

class SubscriptionSchema(BaseModel):
    service_id: str
    endpoint: str
    keys: dict

@router.get("/vapid-public-key")
def get_vapid_public_key():
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="VAPID key not configured")
    return {"public_key": VAPID_PUBLIC_KEY}

@router.post("/subscribe")
def subscribe(
    sub: SubscriptionSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):

    sub_id = hashlib.sha256(sub.endpoint.encode()).hexdigest()
    existing = db.get(PushSubscription, sub_id)

    if existing:
        existing.keys = sub.keys
        existing.service_id = sub.service_id
        existing.user_id = str(current_user.id) 

    else:
        new_sub = PushSubscription(
            id=sub_id,
            user_id=str(current_user.id),           
            service_id=sub.service_id,
            endpoint=sub.endpoint,
            keys=sub.keys,
        )
        db.add(new_sub)

    db.commit()
    return {"status": "subscribed"}

@router.post("/unsubscribe")
def unsubscribe(
    endpoint: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):

    sub_id = hashlib.sha256(endpoint.encode()).hexdigest()
    sub = db.get(PushSubscription, sub_id)
    if sub and sub.user_id == str(current_user.id):
        db.delete(sub)
        db.commit()
    return {"status": "unsubscribed"}

@router.post("/test/{service_id}")
def test_push(service_id: str, db: Session = Depends(get_db)):
    sent = send_notifications_to_service(
        db=db,
        service_id=service_id,
        title="Test Push",
        body="This is a test notification from your backend.",
        url="/"
    )
    return {"sent": sent}