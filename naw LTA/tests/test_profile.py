import pandas as pd

from naw_lta.engine.profile import build_bar_profile, order_book_metrics, trade_flow_metrics


def test_volume_profile_levels_are_ordered():
    frame = pd.DataFrame(
        {
            "high": [101, 102, 103, 102],
            "low": [99, 100, 101, 100],
            "close": [100, 101, 102, 101],
            "volume": [10, 50, 20, 40],
        }
    )
    profile = build_bar_profile(frame, bins=12)
    assert profile.val <= profile.poc <= profile.vah
    assert profile.total_volume == 120


def test_order_book_imbalance_uses_both_sides():
    frame = pd.DataFrame(
        [{"bid_px_00": 99, "ask_px_00": 101, "bid_sz_00": 30, "ask_sz_00": 10}]
    )
    metrics = order_book_metrics(frame)
    assert metrics["imbalance"] == 0.5
    assert metrics["spread"] == 2
    assert metrics["microprice"] == 100.5


def test_trade_delta_uses_databento_aggressor_convention():
    frame = pd.DataFrame(
        [
            {"price": 100, "size": 30, "side": "B"},
            {"price": 99, "size": 10, "side": "A"},
        ]
    )
    metrics = trade_flow_metrics(frame)
    assert metrics["buy_volume"] == 30
    assert metrics["sell_volume"] == 10
    assert metrics["delta_ratio"] == 0.5
