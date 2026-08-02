from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime
import json
import math
from pathlib import Path
from typing import Iterable

import pandas as pd

from .config import Config
from .strategy import Trade, risk_pct_for_streak, run_backtest


SCENARIOS = (
    ("flat_fixed", False, False),
    ("flat_trailing", False, True),
    ("progression_fixed", True, False),
    ("progression_trailing", True, True),
)


def _portfolio_metrics(
    trades: Iterable[tuple[str, Trade]],
    *,
    starting_balance: float,
    base_risk_pct: float,
    progression: bool,
    multiplier: float,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    ordered = sorted(trades, key=lambda item: item[1].exit_time)
    balance = starting_balance
    peak = balance
    maximum_drawdown = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    streak = 0
    maximum_streak = 0
    maximum_risk = base_risk_pct
    journal: list[dict[str, object]] = []
    for symbol, trade in ordered:
        risk_pct = (
            risk_pct_for_streak(base_risk_pct, streak, multiplier)
            if progression
            else base_risk_pct
        )
        risk_cash = balance * risk_pct / 100.0
        pnl = risk_cash * trade.r_multiple
        before = balance
        balance += pnl
        if pnl > 0:
            gross_profit += pnl
            streak = 0
        elif pnl < 0:
            gross_loss += -pnl
            streak += 1
            maximum_streak = max(maximum_streak, streak)
        maximum_risk = max(maximum_risk, risk_pct)
        peak = max(peak, balance)
        maximum_drawdown = max(
            maximum_drawdown,
            (peak - balance) / peak * 100.0 if peak else 0.0,
        )
        journal.append(
            {
                "symbol": symbol,
                **trade.row(),
                "portfolio_balance_before": before,
                "portfolio_risk_pct": risk_pct,
                "portfolio_risk_cash": risk_cash,
                "portfolio_cash_pnl": pnl,
                "portfolio_balance_after": balance,
                "loss_streak_after_close": streak,
            }
        )
    wins = sum(float(item[1].r_multiple) > 0 for item in ordered)
    losses = len(ordered) - wins
    profit_factor = (
        gross_profit / gross_loss
        if gross_loss
        else (math.inf if gross_profit else 0.0)
    )
    return (
        {
            "trades": len(ordered),
            "wins": wins,
            "losses": losses,
            "win_rate_pct": wins / len(ordered) * 100.0 if ordered else 0.0,
            "profit_factor_cash_weighted": profit_factor,
            "starting_balance": starting_balance,
            "ending_balance": balance,
            "net_profit": balance - starting_balance,
            "return_pct": (balance / starting_balance - 1.0) * 100.0,
            "max_realized_dd_pct": maximum_drawdown,
            "max_loss_streak": maximum_streak,
            "max_risk_pct_used": maximum_risk,
            "final_loss_streak": streak,
        },
        journal,
    )


def run_risk_study(
    datasets: dict[str, tuple[pd.DataFrame, float, Config]],
    *,
    start: datetime,
    end: datetime,
    starting_balance: float,
    output_dir: Path,
    base_risk_pct: float = 0.5,
    multiplier: float = 1.6,
    target_rr: float = 1.7,
    trail_start_r: float = 1.0,
    trail_distance_r: float = 0.5,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    payload: dict[str, object] = {
        "study": "DmC 0.5% loss progression and 1.7R TP ceiling",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "starting_balance": starting_balance,
        "base_risk_pct": base_risk_pct,
        "progression_multiplier": multiplier,
        "research_progression_cap": None,
        "target_rr_ceiling": target_rr,
        "trailing_profile": {
            "start_r": trail_start_r,
            "distance_r": trail_distance_r,
        },
        "methodology_note": (
            "Portfolio metrics replay closed trades chronologically on one shared "
            "balance. They do not model concurrent margin or mark-to-market overlap."
        ),
        "scenarios": {},
    }
    summary_rows: list[dict[str, object]] = []
    for name, progression, trailing in SCENARIOS:
        all_trades: list[tuple[str, Trade]] = []
        symbols: dict[str, object] = {}
        for symbol, (frame, point, source_config) in datasets.items():
            scenario_config = replace(
                source_config,
                risk_pct=base_risk_pct,
                risk_progression_enabled=progression,
                risk_progression_multiplier=multiplier,
                trailing_enabled=trailing,
                trail_start_r=trail_start_r,
                trail_distance_r=trail_distance_r,
                target_rr=target_rr,
                maximum_target_r=min(source_config.maximum_target_r, target_rr),
            )
            trades, metrics = run_backtest(
                frame,
                scenario_config,
                point=point,
                start=start,
                end=end,
                starting_balance=starting_balance,
            )
            all_trades.extend((symbol, trade) for trade in trades)
            symbols[symbol] = asdict(metrics)
        portfolio, journal = _portfolio_metrics(
            all_trades,
            starting_balance=starting_balance,
            base_risk_pct=base_risk_pct,
            progression=progression,
            multiplier=multiplier,
        )
        scenario = {
            "risk_mode": "progression_uncapped" if progression else "flat",
            "trailing_enabled": trailing,
            "target_rr": target_rr,
            "portfolio": portfolio,
            "symbols": symbols,
        }
        payload["scenarios"][name] = scenario
        summary_rows.append(
            {
                "scenario": name,
                "progression_enabled": progression,
                "trailing_enabled": trailing,
                "base_risk_pct": base_risk_pct,
                "progression_multiplier": multiplier,
                "target_rr": target_rr,
                "trail_start_r": trail_start_r if trailing else None,
                "trail_distance_r": trail_distance_r if trailing else None,
                **portfolio,
            }
        )
        pd.DataFrame(journal).to_csv(
            output_dir / f"{name}_trades.csv", index=False
        )
    pd.DataFrame(summary_rows).to_csv(output_dir / "summary.csv", index=False)
    (output_dir / "results.json").write_text(
        json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8"
    )
    return payload
