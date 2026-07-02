from telegram_mt5_copier.signal_parser import parse_signal


def test_profit_hacker_stoposs_signal_parses():
    signal = parse_signal(
        "CADJPY SELL NOW STOPOSS @ 114.260 TP @ 113.900 TP @ 113.760 TP @ 113.600"
    )
    assert signal is not None
    assert signal.symbol == "CADJPY"
    assert signal.side == "SELL"
    assert signal.market is True
    assert signal.stop_loss == 114.260
    assert signal.tp1 == 113.900
    assert signal.final_tp == 113.600


def test_limit_zone_and_alias_parse():
    signal = parse_signal(
        "GOLD BUY LIMIT 4310-4312 SL 4298 TP1 4325 TP2 4340",
        {"GOLD": "XAUUSD"},
    )
    assert signal is not None
    assert signal.symbol == "XAUUSD"
    assert signal.entry_low == 4310
    assert signal.entry_high == 4312
    assert signal.market is False
    assert signal.final_tp == 4340


def test_incomplete_signal_is_ignored():
    assert parse_signal("EURUSD BUY NOW TP 1.20") is None
