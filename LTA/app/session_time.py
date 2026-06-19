from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_SESSION_TIMEZONE = "America/New_York"
DEFAULT_DATA_TIMEZONE = "UTC"


def zone(name: str | None, default: str = DEFAULT_DATA_TIMEZONE) -> ZoneInfo:
    selected = (name or default).strip() or default
    try:
        return ZoneInfo(selected)
    except ZoneInfoNotFoundError:
        return ZoneInfo(default)


def parse_hhmm(value: str | None, default: str) -> time:
    raw = (value or default).strip()
    try:
        hour, minute = raw.split(":", 1)
        return time(hour=int(hour), minute=int(minute))
    except (TypeError, ValueError):
        hour, minute = default.split(":", 1)
        return time(hour=int(hour), minute=int(minute))


def as_aware(value: datetime, timezone_name: str) -> datetime:
    selected = zone(timezone_name)
    if value.tzinfo is None:
        return value.replace(tzinfo=selected)
    return value.astimezone(selected)


def convert_naive(value: datetime, source_timezone: str, target_timezone: str) -> datetime:
    return as_aware(value, source_timezone).astimezone(zone(target_timezone)).replace(tzinfo=None)


def now_naive(timezone_name: str = DEFAULT_DATA_TIMEZONE) -> datetime:
    return datetime.now(zone(timezone_name)).replace(tzinfo=None)


def date_in_timezone(value: datetime, source_timezone: str, target_timezone: str) -> date:
    return as_aware(value, source_timezone).astimezone(zone(target_timezone)).date()


def minutes_in_timezone(value: datetime, source_timezone: str, target_timezone: str) -> int:
    converted = as_aware(value, source_timezone).astimezone(zone(target_timezone))
    return converted.hour * 60 + converted.minute


def session_bounds(
    session_day: date,
    session_start: str,
    session_end: str,
    session_timezone: str = DEFAULT_SESSION_TIMEZONE,
    data_timezone: str = DEFAULT_DATA_TIMEZONE,
) -> tuple[datetime, datetime]:
    start_time = parse_hhmm(session_start, "09:30")
    end_time = parse_hhmm(session_end, "16:00")
    session_zone = zone(session_timezone, DEFAULT_SESSION_TIMEZONE)
    start = datetime.combine(session_day, start_time, tzinfo=session_zone)
    end = datetime.combine(session_day, end_time, tzinfo=session_zone)
    if end <= start:
        end += timedelta(days=1)
    data_zone = zone(data_timezone, DEFAULT_DATA_TIMEZONE)
    return start.astimezone(data_zone).replace(tzinfo=None), end.astimezone(data_zone).replace(tzinfo=None)
