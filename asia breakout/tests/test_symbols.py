from asia_breakout.symbols import canonical_for_symbol, symbol_match_score


def test_broker_prefix_and_suffix_match_canonical_symbol() -> None:
    assert symbol_match_score("XAUUSD", "XAUUSDb") is not None
    assert symbol_match_score("BTCUSD", "#BTCUSDr") is not None
    assert canonical_for_symbol("#BTCUSDr", ("XAUUSD", "BTCUSD")) == "BTCUSD"


def test_unrelated_symbol_does_not_match() -> None:
    assert symbol_match_score("XAUUSD", "EURUSD") is None
