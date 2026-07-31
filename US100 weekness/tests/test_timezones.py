from datetime import date

from nasdaq_weakness.strategy import LONDON, NY, _utc


def test_new_york_open_tracks_dst():
    winter = _utc(date(2026, 1, 15), (9, 30), NY)
    summer = _utc(date(2026, 7, 15), (9, 30), NY)
    assert winter.hour == 14
    assert summer.hour == 13


def test_london_range_start_tracks_dst():
    winter = _utc(date(2026, 1, 15), (8, 0), LONDON)
    summer = _utc(date(2026, 7, 15), (8, 0), LONDON)
    assert winter.hour == 8
    assert summer.hour == 7
