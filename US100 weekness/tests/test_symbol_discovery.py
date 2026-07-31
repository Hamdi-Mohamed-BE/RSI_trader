from nasdaq_weakness.mt5_adapter import symbol_score


def test_nasdaq_aliases_rank_above_unrelated_symbols():
    assert symbol_score("NAS100U6")[0] > symbol_score("EURUSD")[0]
    assert symbol_score("USTECm")[0] > symbol_score("XAUUSD")[0]


def test_requested_alias_gets_a_preference():
    assert symbol_score("US100.cash", "US100") > symbol_score(
        "NAS100.cash", "US100"
    )
