"""Alert feed (Mode B): REST list, WebSocket live stream, and a manual monitoring trigger."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from ..auth import current_user, require_role
from ..persistence import get_alerts

router = APIRouter(tags=["alerts"])


class AlertHub:
    """In-process pub/sub that streams live alerts to connected dashboards over WebSocket."""

    def __init__(self):
        self._clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self._clients.discard(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self._clients:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._clients.discard(ws)


hub = AlertHub()


@router.get("/alerts")
async def list_alerts(limit: int = 100, user: dict = Depends(current_user)):
    return {"alerts": get_alerts(limit)}


@router.post("/monitor/run")
async def run_monitor(trigger: str = "daily_delta", user: dict = Depends(require_role("credit_officer"))):
    """Trigger Mode-B monitoring on demand (batch re-score + alerts)."""
    from ..persistence import monitor_disbursed_borrowers
    result = await asyncio.to_thread(monitor_disbursed_borrowers, trigger)
    # push newly created alerts to any connected dashboards
    for a in get_alerts(result["alerts_created"]):
        await hub.broadcast({"event": "alert", "data": a})
    return result


@router.websocket("/ws/alerts")
async def ws_alerts(ws: WebSocket):
    await hub.connect(ws)
    try:
        # send a snapshot then keep the connection alive
        await ws.send_json({"event": "snapshot", "data": get_alerts(20)})
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(ws)
    except Exception:
        hub.disconnect(ws)
