from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path

import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv

from .backtest import completed_h4_rates, discover_symbol
from .optimize import ExitConfig, compounded_journal, metrics, simulate


UTC = timezone.utc
BASE_RISK_PCT = 0.5
PROGRESSION_MULTIPLIER = 1.6
TARGET_CAP_R = 1.7


def main() -> None:
    load_dotenv()
    requested_symbol = os.getenv("GOLD_SYMBOL_HINT", "XAUUSD").strip()
    if requested_symbol.upper() == "AUTO":
        requested_symbol = "XAUUSD"
    history_days = int(os.getenv("HISTORY_DAYS", "365"))
    distance = int(os.getenv("PIVOT_DISTANCE", "5"))
    max_legs = int(os.getenv("MAX_SAME_DIRECTION_LEGS", "1"))
    signal_filter = os.getenv("SIGNAL_FILTER", "ema200_slope").strip().lower()
    ema_slope_bars = int(os.getenv("EMA_SLOPE_BARS", "6"))
    trail_start_r = float(os.getenv("TRAIL_START_R", "1.0"))
    trail_distance_r = float(os.getenv("TRAIL_DISTANCE_R", "1.0"))
    starting_balance = float(os.getenv("STARTING_BALANCE", "1000"))
    output = Path("reports") / "risk_progression_1_7r"
    output.mkdir(parents=True, exist_ok=True)

    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        broker_symbol = discover_symbol(requested_symbol)
        info = mt5.symbol_info(broker_symbol)
        if info is None:
            raise RuntimeError(f"No symbol info for {broker_symbol}")
        end = datetime.now(UTC)
        start = end - timedelta(days=history_days)
        warmup = 250 + ema_slope_bars if signal_filter != "none" else 0
        frame = completed_h4_rates(
            broker_symbol, start, end, distance, warmup_bars=warmup
        )
    finally:
        mt5.shutdown()

    fixed = ExitConfig(mode="fixed", target_r=TARGET_CAP_R)
    trailing = ExitConfig(
        mode="trail",
        trail_start_r=trail_start_r,
        trail_distance_r=trail_distance_r,
        target_cap_r=TARGET_CAP_R,
    )
    scenarios = [
        ("flat_fixed_1_7r", fixed, False),
        ("flat_trailing_cap_1_7r", trailing, False),
        ("progression_fixed_1_7r", fixed, True),
        ("progression_trailing_cap_1_7r", trailing, True),
    ]
    trade_cache: dict[str, list] = {}
    rows: list[dict[str, object]] = []
    for name, exit_config, progression in scenarios:
        if exit_config.name not in trade_cache:
            trade_cache[exit_config.name] = simulate(
                frame,
                requested_symbol,
                float(info.point),
                distance,
                start,
                end,
                exit_config,
                max_same_direction_legs=max_legs,
                signal_filter=signal_filter,
                ema_slope_bars=ema_slope_bars,
            )
        trades = trade_cache[exit_config.name]
        stats = metrics(
            trades,
            risk_pct=BASE_RISK_PCT,
            starting_balance=starting_balance,
            progression_enabled=progression,
            progression_multiplier=PROGRESSION_MULTIPLIER,
            max_risk_pct=None,
        )
        journal = compounded_journal(
            trades,
            risk_pct=BASE_RISK_PCT,
            starting_balance=starting_balance,
            progression_enabled=progression,
            progression_multiplier=PROGRESSION_MULTIPLIER,
            max_risk_pct=None,
        )
        journal.insert(0, "scenario", name)
        journal.to_csv(output / f"{name}_trades.csv", index=False)
        row = {
            "scenario": name,
            "exit_config": exit_config.name,
            "base_risk_pct": BASE_RISK_PCT,
            "progression_enabled": progression,
            "progression_multiplier": PROGRESSION_MULTIPLIER,
            "progression_cap_pct": None,
            "target_cap_r": TARGET_CAP_R,
            **stats,
        }
        rows.append(row)

    comparable = pd.DataFrame(rows)
    comparable.to_csv(output / "scenarios.csv", index=False)
    payload = {
        "study": "EMA3 0.5% loss-streak progression and 1.7R target cap",
        "requested_symbol": requested_symbol,
        "broker_symbol": broker_symbol,
        "timeframe": "H4",
        "period_start_utc": start.isoformat(),
        "period_end_utc": end.isoformat(),
        "history_days": history_days,
        "pivot_distance": distance,
        "max_same_direction_legs": max_legs,
        "signal_filter": signal_filter,
        "ema_slope_bars": ema_slope_bars,
        "starting_balance": starting_balance,
        "base_risk_pct": BASE_RISK_PCT,
        "progression_rule": "0.5% * 1.6^consecutive_closed_losses; reset after win",
        "research_progression_cap_pct": None,
        "target_cap_r": TARGET_CAP_R,
        "trail_start_r": trail_start_r,
        "trail_distance_r": trail_distance_r,
        "scenarios": rows,
    }
    (output / "summary.json").write_text(
        json.dumps(payload, indent=2, allow_nan=True), encoding="utf-8"
    )

    def pf(value: object) -> str:
        number = float(value)
        return "inf" if math.isinf(number) else f"{number:.2f}"

    report = [
        "# EMA3 risk progression / 1.7R study",
        "",
        f"- Symbol: **{broker_symbol}**; timeframe: **H4**",
        f"- Period: **{start.isoformat()} to {end.isoformat()}**",
        f"- Base risk: **{BASE_RISK_PCT:.2f}%**",
        f"- Progression: **base x {PROGRESSION_MULTIPLIER:g}^loss_streak**, uncapped for research",
        f"- Target ceiling: **{TARGET_CAP_R:g}R**",
        "",
        "| Scenario | Trades | Win rate | R-PF | Cash PF | Net R | Ending balance | Return | Max DD | Max risk |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        report.append(
            f"| {row['scenario']} | {int(row['trades'])} | "
            f"{float(row['win_rate_pct']):.2f}% | {pf(row['profit_factor'])} | "
            f"{pf(row['cash_profit_factor'])} | "
            f"{float(row['net_r']):+.2f}R | ${float(row['ending_balance']):,.2f} | "
            f"{(float(row['ending_balance']) / starting_balance - 1) * 100:.2f}% | "
            f"{float(row['max_drawdown_pct']):.2f}% | "
            f"{float(row['maximum_applied_risk_pct']):.4f}% |"
        )
    report.extend(
        [
            "",
            "The progression scenarios intentionally have no research cap so the exact",
            "0.5%, 0.8%, 1.28%, ... sequence is visible. Live defaults keep progression",
            "disabled and impose a separate safety cap if it is manually enabled.",
            "",
        ]
    )
    (output / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report))


if __name__ == "__main__":
    main()
