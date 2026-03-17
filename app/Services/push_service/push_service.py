import os
import json
import logging
from dotenv import load_dotenv
from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session
from app.models.PushSubscription import PushSubscription

load_dotenv()

logger = logging.getLogger(__name__)

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_EMAIL = os.getenv("VAPID_EMAIL")

if not VAPID_PRIVATE_KEY or not VAPID_EMAIL:
    raise ValueError("VAPID_PRIVATE_KEY and VAPID_EMAIL must be set in .env")

VAPID_CLAIMS = {"sub": f"mailto:{VAPID_EMAIL}"}

def send_push_notification(subscription: PushSubscription, title: str, body: str, url: str = "/") -> bool:
    """Send notfiction to user"""
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": subscription.keys,
            },
            data=json.dumps({
                "title": title,
                "body": body,
                "url": url,
                "route_id": subscription.service_id,
            }),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
        )
        return True
    except WebPushException as ex:
        if ex.response and ex.response.status_code in [410, 404]:
            logger.info(f"Removing expired subscription {subscription.id}")
            return False  # signal to delete
        logger.warning(f"Push failed for {subscription.id}: {ex}")
        return False
    except Exception as e:
        logger.exception(f"Unexpected push error: {e}")
        return False

def send_notifications_to_service(db: Session, service_id: str, title: str, body: str, url: str = "/") -> int:
    subs = db.query(PushSubscription).filter(PushSubscription.service_id == service_id).all()
    dead = []
    sent = 0
    for sub in subs:
        ok = send_push_notification(sub, title, body, url)
        if ok:
            sent += 1
        else:
            dead.append(sub)
    for sub in dead:
        db.delete(sub)
    if dead:
        db.commit()
    return sent