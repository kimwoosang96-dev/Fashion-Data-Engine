from __future__ import annotations

from collections import deque
from typing import Any

from fastapi import APIRouter, Header, HTTPException, WebSocket, WebSocketDisconnect

from fashion_engine.config import settings

router = APIRouter(tags=["realtime"])


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []
        self.recent: deque[dict[str, Any]] = deque(maxlen=100)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)
        for item in self.recent:
            await websocket.send_json(item)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        self.recent.appendleft(message)
        for ws in self.active[:]:
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/feed")
async def websocket_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@router.post("/internal/broadcast")
async def internal_broadcast(
    payload: dict[str, Any],
    x_internal_key: str | None = Header(None),
):
    expected = (settings.internal_api_key or "").strip()
    if not expected:
        raise HTTPException(status_code=503, detail="INTERNAL_API_KEY not configured")
    if x_internal_key != expected:
        raise HTTPException(status_code=401, detail="invalid internal key")
    await manager.broadcast(payload)
    return {"ok": True}
