import json
import os
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from pywebpush import webpush, WebPushException

from app.models.PushSubscription import PushSubscription
from app.repositories.push_subscription_repository import PushSubscriptionRepository

logger = logging.getLogger(__name__)

#TODO move to config
VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY")
VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY")
VAPID_EMAIL = os.getenv("VAPID_EMAIL")

if not VAPID_PRIVATE_KEY or not VAPID_EMAIL:
    logger.error("VAPID_PRIVATE_KEY and VAPID_EMAIL must be set in .env")

VAPID_CLAIMS = {"sub": f"mailto:{VAPID_EMAIL}"}


def send_push_notification(
    subscription: PushSubscription,
    title: str,
    body: str,
    url: str = "/") -> bool:
    """Send push to a single subscription. Returns True on success."""
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
            }),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS,
            ttl=86400,  # 24 hours
        )
        logger.debug(f"Push sent successfully to subscription {subscription.id[:8]}...")
        return True

    except WebPushException as ex:
        if ex.response and ex.response.status_code in (404, 410):
            logger.info(f"Subscription {subscription.id[:8]}... expired (HTTP {ex.response.status_code})")
            return False
        else:
            logger.warning(f"WebPushException for {subscription.id[:8]}...: {ex}")
            return False

    except Exception as e:
        logger.exception(f"Unexpected error sending push to {subscription.id[:8]}...")
        return False


async def send_notifications_to_service(
    db: AsyncSession,
    service_id: str,
    title: str,
    body: str,
    url: str = "/") -> int:
    """
    Send push notification to all subscribers of a service_id.
    Automatically removes dead subscriptions.
    Returns number of successful deliveries.
    """
    if not VAPID_PRIVATE_KEY:
        logger.warning("VAPID keys not configured — skipping push notifications")
        return 0

    repo = PushSubscriptionRepository(db)
    subs = await repo.GetSubscriptionsByService(service_id)

    if not subs:
        logger.debug(f"No subscribers for service {service_id}")
        return 0

    dead = []
    sent = 0

    for sub in subs:
        success = send_push_notification(sub, title, body, url)
        if success:
            sent += 1
        else:
            dead.append(sub)

    if dead:
        await repo.DeleteSubscriptions(dead)
        logger.info(f"Cleaned up {len(dead)} expired subscriptions for service {service_id}")

    logger.info(f"Push notifications for service {service_id}: {sent}/{len(subs)} sent")
    return sent