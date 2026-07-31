from types import SimpleNamespace

from nasdaq_weakness import mt5_adapter
from nasdaq_weakness.mt5_adapter import discover_symbol, symbol_score


def test_nasdaq_aliases_rank_above_unrelated_symbols():
    assert symbol_score("NAS100U6")[0] > symbol_score("EURUSD")[0]
    assert symbol_score("USTECm")[0] > symbol_score("XAUUSD")[0]


def test_requested_alias_gets_a_preference():
    assert symbol_score("US100.cash", "US100") > symbol_score(
        "NAS100.cash", "US100"
    )


def test_exact_mixed_case_broker_symbol_works_without_catalogue(monkeypatch):
    info = SimpleNamespace(
        name="USTEC_x100m",
        trade_mode=mt5_adapter.mt5.SYMBOL_TRADE_MODE_FULL,
    )
    monkeypatch.setattr(
        mt5_adapter.mt5,
        "symbol_info",
        lambda name: info if name == "USTEC_x100m" else None,
    )
    monkeypatch.setattr(mt5_adapter.mt5, "symbol_select", lambda *_: True)
    monkeypatch.setattr(mt5_adapter.mt5, "symbols_get", lambda: ())

    assert discover_symbol("USTEC_x100m") == "USTEC_x100m"


def test_catalogue_recovers_case_normalized_config(monkeypatch):
    item = SimpleNamespace(name="USTEC_x100m")
    info = SimpleNamespace(
        name="USTEC_x100m",
        trade_mode=mt5_adapter.mt5.SYMBOL_TRADE_MODE_FULL,
    )
    monkeypatch.setattr(mt5_adapter.mt5, "symbols_get", lambda: (item,))
    monkeypatch.setattr(mt5_adapter.mt5, "symbol_info", lambda *_: info)
    monkeypatch.setattr(mt5_adapter.mt5, "symbol_select", lambda *_: True)

    assert discover_symbol("USTEC_X100M") == "USTEC_x100m"
