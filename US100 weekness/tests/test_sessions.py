from datetime import date, time

from us100_bot.sessions import is_trading_day, to_utc


def test_new_york_dst_conversion():
    assert to_utc(date(2026, 1, 15), time(9, 30)).hour == 14
    assert to_utc(date(2026, 7, 15), time(9, 30)).hour == 13


def test_holiday_and_weekend_filters():
    assert is_trading_day(date(2026, 7, 4))[0] is False
    assert is_trading_day(date(2026, 7, 5))[0] is False
    assert is_trading_day(date(2026, 7, 6))[0] is True

