from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo


LOCAL_TZ = ZoneInfo("Africa/Casablanca")


def session_name(dt: datetime) -> str:
    hour = dt.astimezone(LOCAL_TZ).hour
    if 0 <= hour < 7:
        return "Asia/quiet"
    if 7 <= hour < 12:
        return "London"
    if 12 <= hour < 17:
        return "NY open"
    if 17 <= hour < 22:
        return "NY late"
    return "rollover"


def in_allowed_session(dt: datetime, sessions: list[str]) -> bool:
    if not sessions:
        return True
    return session_name(dt) in sessions
