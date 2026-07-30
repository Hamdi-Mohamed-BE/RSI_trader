from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from us100_bot.config import load_config
from us100_bot.models import SymbolSpec
from us100_bot.normalization import PriceNormalizer
from us100_bot.strategies import Backtest


def _bars():
    start = datetime(2026, 7, 6, 13, 0, tzinfo=timezone.utc)  # 09:00 NY
    rows = []
    price = 20000.0
    for i in range(420):
        t = start + timedelta(minutes=i)
        if t.hour == 13 and t.minute >= 30:
            price -= 1.0
        rows.append(
            {
                "time": t, "open": price, "high": price + .2, "low": price - .2,
                "close": price, "tick_volume": 10, "spread": 100, "real_volume": 0,
            }
        )
    return pd.DataFrame(rows)


def test_strategy_a_uses_closed_progression(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("STARTING_BALANCE=10000\nMAX_SPREAD_PIPS=5\nSLIPPAGE_PIPS=0\n", encoding="utf-8")
    cfg = load_config(env)
    spec = SymbolSpec(
        "UT100", "", "", 2, .01, .01, .01, 1, .01, 50, .01,
        0, 0, 100, 4, 3, True,
    )
    trades, _ = Backtest(cfg, PriceNormalizer(spec)).run(_bars(), ("A_FIXED",))
    assert len(trades) == 1
    assert trades[0].entry_time.hour == 13 and trades[0].entry_time.minute == 30
    assert trades[0].target == trades[0].entry - 100

