from asia_breakout.live import trailing_stop_candidate


def test_buy_trailing_waits_for_start_and_only_advances() -> None:
    assert trailing_stop_candidate("buy", 100, 90, 90, 119, 2, 1) is None
    assert trailing_stop_candidate("buy", 100, 90, 90, 120, 2, 1) == 110
    assert trailing_stop_candidate("buy", 100, 90, 112, 120, 2, 1) is None


def test_sell_trailing_waits_for_start_and_only_advances() -> None:
    assert trailing_stop_candidate("sell", 100, 110, 110, 81, 2, 1) is None
    assert trailing_stop_candidate("sell", 100, 110, 110, 80, 2, 1) == 90
    assert trailing_stop_candidate("sell", 100, 110, 88, 80, 2, 1) is None
