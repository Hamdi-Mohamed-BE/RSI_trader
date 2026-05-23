from rsi_divergence_bot.live_session import LIVE_SCAN_BARS, first_poll_after, poll_times, timeframe_seconds


def test_live_scan_constants_match_bot():
    assert LIVE_SCAN_BARS == 600
    assert timeframe_seconds("M1") == 60
    assert timeframe_seconds("M5") == 300


def test_poll_times_align_to_interval():
    times = poll_times(100, 200, 15)
    assert times
    assert all(time % 15 == 0 for time in times)
    assert times[0] >= 100
    assert times[-1] <= 200


def test_first_poll_after_never_before_as_of():
    assert first_poll_after(100, 15) >= 100
    assert first_poll_after(100, 15) % 15 == 0
