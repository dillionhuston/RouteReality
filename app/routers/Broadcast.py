import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["Broadcast"])

class ConnectionManager:
    """Manages WebSocket connections grouped by channel."""

    def __init__(self) -> None:
        self._channels: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._channels.setdefault(channel, set()).add(websocket)
        logger.info("Client connected to channel=%s total=%d", channel, self.channel_size(channel))

    async def disconnect(self, websocket: WebSocket, channel: str) -> None:
        async with self._lock:
            subscribers = self._channels.get(channel)
            if subscribers:
                subscribers.discard(websocket)
                if not subscribers:
                    del self._channels[channel]
        logger.info("Client disconnected from channel=%s remaining=%d", channel, self.channel_size(channel))

    async def broadcast(self, channel: str, payload: dict) -> int:
        """
        Send payload to all users on the channel.
        Returns the number of successfully reached clients.
        Drops dead connections in the background.
        """
        async with self._lock:
            subscribers = set(self._channels.get(channel, set())) 

        if not subscribers:
            return 0

        results = await asyncio.gather(
            *[self._safe_send(ws, payload) for ws in subscribers],
            return_exceptions=True,
        )

        dead: Set[WebSocket] = {
            ws for ws, ok in zip(subscribers, results) if ok is not True
        }

        if dead:
            async with self._lock:
                if channel in self._channels:
                    self._channels[channel] -= dead
                    if not self._channels[channel]:
                        del self._channels[channel]
            logger.warning("Removed %d dead connection(s) from channel=%s", len(dead), channel)

        return len(subscribers) - len(dead)

    @staticmethod
    async def _safe_send(websocket: WebSocket, payload: dict) -> bool:
        try:
            await websocket.send_json(payload)
            return True
        except Exception as exc: 
            logger.debug("Send failed for %s: %s", websocket.client, exc)
            return False

    def channel_size(self, channel: str) -> int:
        return len(self._channels.get(channel, set()))

    @property
    def stats(self) -> dict:
        return {ch: len(subs) for ch, subs in self._channels.items()}


manager = ConnectionManager()


@asynccontextmanager
async def _managed_connection(websocket: WebSocket, channel: str):
    """Manager that handles connect / disconnect processes"""
    await manager.connect(websocket, channel)
    try:
        yield
    finally:
        await manager.disconnect(websocket, channel)


@router.websocket("/service/{service_id}")
async def websocket_service_broadcast(websocket: WebSocket, service_id: str) -> None:
    channel = f"service:{service_id}"

    async with _managed_connection(websocket, channel):
        try:
            while True:
                data = await websocket.receive_text()
                logger.debug("Received from channel=%s: %s", channel, data)
        except WebSocketDisconnect:
            pass 



async def broadcast_service_update(service_id: str, payload: dict) -> int:
    """Broadcast *payload* to all memebers on a service channel.
    Returns the number of clients that received the message.
    """
    channel = f"service:{service_id}"
    sent = await manager.broadcast(channel, payload)
    logger.debug("Broadcast to channel=%s reached %d client(s)", channel, sent)
    return sent


@router.get("/stats", summary="Active WebSocket connections per channel")
async def connection_stats() -> dict:
    return manager.stats