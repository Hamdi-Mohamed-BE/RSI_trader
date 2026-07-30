from __future__ import annotations

from datetime import date, datetime, time, timedelta
from functools import lru_cache
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
UTC = ZoneInfo("UTC")


def ny_datetime(day: date, clock: time) -> datetime:
    return datetime.combine(day, clock, tzinfo=NY)


def to_utc(day: date, clock: time) -> datetime:
    return ny_datetime(day, clock).astimezone(UTC)


def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    d = date(year, month, 1)
    d += timedelta(days=(weekday - d.weekday()) % 7 + 7 * (n - 1))
    return d


def _last_weekday(year: int, month: int, weekday: int) -> date:
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    d -= timedelta(days=(d.weekday() - weekday) % 7)
    return d


def _observed(d: date) -> date:
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


@lru_cache(maxsize=16)
def market_holidays(year: int) -> frozenset[date]:
    # NYSE full closures needed by this strategy.
    new_year = _observed(date(year, 1, 1))
    mlk = _nth_weekday(year, 1, 0, 3)
    presidents = _nth_weekday(year, 2, 0, 3)
    # Gregorian Easter algorithm; Good Friday is two days earlier.
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f, g = (b + 8) // 25, (b - (b + 8) // 25 + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    easter = date(year, month, day)
    good_friday = easter - timedelta(days=2)
    memorial = _last_weekday(year, 5, 0)
    juneteenth = _observed(date(year, 6, 19))
    independence = _observed(date(year, 7, 4))
    labor = _nth_weekday(year, 9, 0, 1)
    thanksgiving = _nth_weekday(year, 11, 3, 4)
    christmas = _observed(date(year, 12, 25))
    return frozenset(
        {
            new_year,
            mlk,
            presidents,
            good_friday,
            memorial,
            juneteenth,
            independence,
            labor,
            thanksgiving,
            christmas,
        }
    )


def is_shortened_session(day: date) -> bool:
    thanksgiving = _nth_weekday(day.year, 11, 3, 4)
    candidates = {
        thanksgiving + timedelta(days=1),
        _observed(date(day.year, 7, 4)) - timedelta(days=1),
        date(day.year, 12, 24),
    }
    return day in candidates and day.weekday() < 5


def is_trading_day(day: date, exclude_shortened: bool = True) -> tuple[bool, str]:
    if day.weekday() >= 5:
        return False, "weekend"
    if day in market_holidays(day.year):
        return False, "NYSE holiday"
    if exclude_shortened and is_shortened_session(day):
        return False, "shortened US session"
    return True, ""

