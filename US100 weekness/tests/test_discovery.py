from types import SimpleNamespace

from us100_bot.symbol_discovery import rank_symbols


def _symbol(name, description, path):
    return SimpleNamespace(
        name=name, description=description, path=path, trade_mode=4, visible=True,
        trade_tick_size=.01, volume_step=.01,
    )


def test_cash_index_beats_equity_and_future():
    ranked = rank_symbols(
        [
            _symbol("NDAQ.OQ", "Nasdaq Inc", "CFD Shares/US Shares"),
            _symbol("NAS100U6", "E-mini Nasdaq Future", "CFD Futures/Indices"),
            _symbol("UT100", "US Tech 100 Index", "Cash Indices/UT100"),
        ],
        ("US100", "NAS100", "USTEC", "UT100", "NDX", "NASDAQ"),
    )
    assert ranked[0].symbol == "UT100"

