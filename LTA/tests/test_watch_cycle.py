from app.watch_cycle import _candidate, _float_list


def test_reference_levels_ignore_invalid_values() -> None:
    assert _float_list("4165, bad, 4138") == [4165.0, 4138.0]


def test_candidate_prefers_prepared_order_prices() -> None:
    item = {
        "signal": {
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "direction": "BUY",
            "setup_score": 94,
            "setup_grade": "PRE-A+",
            "trigger_price": 4150.0,
            "stop_loss": 4140.0,
        },
        "order": {
            "pending_order_type": "BUY_LIMIT",
            "trigger_price": 4151.0,
            "stop_loss": 4141.0,
            "take_profit": 4211.0,
        },
    }

    candidate = _candidate(item)

    assert candidate["score"] == 94
    assert candidate["order_type"] == "BUY_LIMIT"
    assert candidate["entry"] == 4151.0
    assert candidate["stop_loss"] == 4141.0
