from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import AppConfig
from .engine import backtest
from .mt5_data import (
    discover_symbols,
    ensure_account,
    load_or_fetch_m1,
    mt5_connection,
    symbol_metadata,
)
from .portfolio import simulate_portfolio


def run_risk_progression_study(
    config: AppConfig,
    warmup: datetime,
    start: datetime,
    end: datetime,
    cache: Path,
    output_dir: Path,
    refresh: bool = False,
) -> pd.DataFrame:
    """Run the four requested 1.7R portfolio scenarios.

    Entry/stop/range filters remain frozen per symbol. Only exit mode and
    account risk policy change, which keeps the comparison causal.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    fixed: dict[str, pd.DataFrame] = {}
    trailing: dict[str, pd.DataFrame] = {}
    with mt5_connection(config):
        symbol_map = discover_symbols(config.symbols)
        ensure_account(config)
        for instrument, symbol in symbol_map.items():
            frame = load_or_fetch_m1(symbol, warmup, end, cache, refresh)
            point = float(symbol_metadata(symbol)["point"])
            base = config.strategy_for(instrument)
            fixed_config = base.evolved(rr=1.7, exit_mode="fixed")
            trailing_config = base.evolved(
                rr=1.7,
                exit_mode="trailing",
                trail_start_r=1.0,
                trail_distance_r=1.0,
            )
            fixed[instrument] = pd.DataFrame(
                trade.to_dict()
                for trade in backtest(
                    frame, symbol, point, fixed_config, start, end
                )
            )
            trailing[instrument] = pd.DataFrame(
                trade.to_dict()
                for trade in backtest(
                    frame, symbol, point, trailing_config, start, end
                )
            )

    scenarios = (
        ("flat_fixed_1_7r", fixed, None),
        ("flat_trailing_capped_1_7r", trailing, None),
        ("progression_fixed_1_7r", fixed, 1.6),
        ("progression_trailing_capped_1_7r", trailing, 1.6),
    )
    rows: list[dict[str, object]] = []
    for name, trades, multiplier in scenarios:
        result, audit = simulate_portfolio(
            trades,
            starting_balance=config.strategy.starting_balance,
            risk_pct=0.5,
            exposure_cap_pct=config.max_basket_risk_pct,
            priority=config.symbols,
            progression_multiplier=multiplier,
            # Deliberately uncapped in research. The independent basket cap
            # still rejects entries that would exceed aggregate exposure.
            max_risk_pct=None,
        )
        record = result.to_dict()
        accepted = audit[audit["portfolio_status"] == "accepted"]
        cash_pnl = accepted["portfolio_pnl_cash"].astype(float)
        gross_cash_profit = float(cash_pnl.clip(lower=0).sum())
        gross_cash_loss = float(abs(cash_pnl.clip(upper=0).sum()))
        record.update(
            {
                "scenario": name,
                "progression_multiplier": multiplier or 1.0,
                "target_cap_r": 1.7,
                "trailing_enabled": "trailing" in name,
                "test_start": start.date().isoformat(),
                "test_end": end.date().isoformat(),
                "cash_profit_factor": (
                    gross_cash_profit / gross_cash_loss
                    if gross_cash_loss
                    else float("inf") if gross_cash_profit else 0.0
                ),
            }
        )
        rows.append(record)
        audit.to_csv(output_dir / f"{name}_audit.csv", index=False)

    summary = pd.DataFrame(rows)
    summary.to_csv(output_dir / "summary.csv", index=False)
    return summary
