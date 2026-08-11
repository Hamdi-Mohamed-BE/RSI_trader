import asyncio
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..dependencies import request_session, require_user
from ..models import Account, CopyJob
from ..services.accounts import ensure_system_state
from ..services.events import event_hub

router = APIRouter()


@router.get("/api/health", name="health")
def health(request: Request) -> dict[str, Any]:
    return {
        "status": "ok",
        "service": request.app.state.settings.app_name,
        "safe_mode": request.app.state.settings.safe_mode,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/api/status", name="api-status")
def system_status(
    request: Request,
    session: Annotated[Session, Depends(request_session)],
) -> dict[str, Any]:
    user = require_user(request, session)
    state = ensure_system_state(session)
    return {
        "user": user.email,
        "global_pause": state.global_pause,
        "execution_mode": state.execution_mode,
        "reason": state.reason,
        "accounts": session.scalar(select(func.count(Account.id))) or 0,
        "jobs": session.scalar(select(func.count(CopyJob.id))) or 0,
    }


@router.websocket("/ws/status", name="status-websocket")
async def status_websocket(websocket: WebSocket) -> None:
    if not websocket.session.get("user_id"):
        await websocket.close(code=4401)
        return
    await websocket.accept()
    queue = event_hub.subscribe()
    try:
        await websocket.send_json({"type": "connected"})
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15)
                await websocket.send_json(event)
            except TimeoutError:
                await websocket.send_json(
                    {"type": "heartbeat", "timestamp": datetime.now(UTC).isoformat()}
                )
    except WebSocketDisconnect:
        pass
    finally:
        event_hub.unsubscribe(queue)
