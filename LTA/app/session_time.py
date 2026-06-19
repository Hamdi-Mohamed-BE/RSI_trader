from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


DEFAULT_SESSION_TIMEZONE = "America/New_York"
DEFAULT_DATA_TIMEZONE = "UTC"


class NewYorkFallbackZone(tzinfo):
    @staticmethod
    def _nth_weekday(year: int, month: int, weekday: int, n: int) -> int:
        first = datetime(year, month, 1)
        return 1 + ((weekday - first.weekday()) % 7) + (n - 1) * 7

    @classmethod
    def _transition_utc(cls, year: int) -> tuple[datetime, datetime]:
        dst_start_day = cls._nth_weekday(year, 3, 6, 2)
        dst_end_day = cls._nth_weekday(year, 11, 6, 1)
        return datetime(year, 3, dst_start_day, 7), datetime(year, 11, dst_end_day, 6)

    @classmethod
    def _transition_local(cls, year: int) -> tuple[datetime, datetime]:
        dst_start_day = cls._nth_weekday(year, 3, 6, 2)
        dst_end_day = cls._nth_weekday(year, 11, 6, 1)
        return datetime(year, 3, dst_start_day, 2), datetime(year, 11, dst_end_day, 2)

    def _is_dst_local(self, value: datetime | None) -> bool:
        if value is None:
            return False
        local = value.replace(tzinfo=None)
        start, end = self._transition_local(local.year)
        return start <= local < end

    def utcoffset(self, value: datetime | None) -> timedelta:
        return timedelta(hours=-4 if self._is_dst_local(value) else -5)

    def dst(self, value: datetime | None) -> timedelta:
        return timedelta(hours=1 if self._is_dst_local(value) else 0)

    def tzname(self, value: datetime | None) -> str:
        return "EDT" if self._is_dst_local(value) else "EST"

    def fromutc(self, value: datetime) -> datetime:
        if value.tzinfo is not self:
            raise ValueError("fromutc: dt.tzinfo is not self")
        utc_value = value.replace(tzinfo=None)
        start, end = self._transition_utc(utc_value.year)
        offset = timedelta(hours=-4 if start <= utc_value < end else -5)
        return (utc_value + offset).replace(tzinfo=self)


def zone(name: str | None, default: str = DEFAULT_DATA_TIMEZONE) -> tzinfo:
    selected = (name or default).strip() or default
    try:
        return ZoneInfo(selected)
    except ZoneInfoNotFoundError:
        pass
    try:
        return ZoneInfo(default)
    except ZoneInfoNotFoundError:
        if selected in {"America/New_York", "US/Eastern"} or default in {"America/New_York", "US/Eastern"}:
            return NewYorkFallbackZone()
        if selected.upper() == "UTC" or default.upper() == "UTC":
            return timezone.utc
        return timezone.utc


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
