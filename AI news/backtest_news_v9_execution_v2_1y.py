from __future__ import annotations

import csv
import json
import math
import os
from collections import Counter
from dataclasses import asdict
from datetime import date

import MetaTrader5 as mt5
import numpy as np

from backtest_news_v8_move_execution_3m import (
    ExecutionConfig,
    _event_ticks,
    _simulate_event,
    _utc,
)
from backtest_news_v8_one_year import _archived_hybrid_ticks
from news_core import ROOT


START = date(2025, 9, 10)
END = date(2026, 9, 10)
HOLDOUT_START = date(2026, 6, 1)
STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01
SUPPORTED_EVENTS = ("NFP", "CPI", "FOMC")
DIRECTION_REPORT = ROOT / "news_v9_direction_1y_results.json"
OUTPUT_JSON = ROOT / "news_v9_execution_v2_1y_results.json"
OUTPUT_CSV = ROOT / "news_v9_execution_v2_1y_trades.csv"
OUTPUT_MD = ROOT / "NEWS_V9_EXECUTION_V2_1Y_RESULTS.md"

BASELINE = ExecutionConfig(-5, 4.0, None, None, None, 900)


def candidate_configs() -> list[ExecutionConfig]:
    return [
        ExecutionConfig(entry, stop, target, None, None, exit_after)
        for entry in (-10, -5, 0, 1, 2, 5, 10)
        for stop in (4.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0)
        for target in (None, 4.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0)
        for exit_after in (60, 120, 300, 900)
    ]


def load_events() -> list[dict]:
    payload = json.loads(DIRECTION_REPORT.read_text(encoding="utf-8"))
    events = [
        {**row, "prediction": row["v9_direction"]}
        for row in payload["events"]
        if START <= date.fromisoformat(row["release_utc"][:10]) < END
        and row["event"] in SUPPORTED_EVENTS
    ]
    events.sort(key=lambda row: row["release_utc"])
    expected = Counter({"NFP": 10, "CPI": 11, "FOMC": 8})
    observed = Counter(row["event"] for row in events)
    if observed != expected:
        raise RuntimeError(f"Expected {dict(expected)}, found {dict(observed)}.")
    return events


def normalize_lot(raw_lot: float, info: object) -> float:
    step = float(info.volume_step)
    if step <= 0:
        raise RuntimeError("Broker returned an invalid volume step.")
    lot = math.floor((raw_lot + 1e-12) / step) * step
    lot = min(lot, float(info.volume_max))
    return round(lot, 8) if lot >= float(info.volume_min) else 0.0


def risk_lot(
    balance: float, stop_usd: float, info: object
) -> tuple[float, float, float]:
    budget = balance * RISK_FRACTION
    tick_size = float(info.trade_tick_size)
    tick_value = float(getattr(info, "trade_tick_value_loss", 0.0))
    tick_value = tick_value if tick_value > 0 else float(info.trade_tick_value)
    if tick_size <= 0 or tick_value <= 0:
        raise RuntimeError("Broker returned invalid XAUUSD tick metadata.")
    loss_per_lot = stop_usd * tick_value / tick_size
    lot = normalize_lot(budget / loss_per_lot, info)
    return lot, budget, lot * loss_per_lot


def drawdown(values: list[float]) -> tuple[float, float]:
    series = np.asarray(values, dtype=float)
    peaks = np.maximum.accumulate(series)
    amount = peaks - series
    percent = np.divide(
        amount, peaks, out=np.zeros_like(amount), where=peaks > 0
    )
    return float(np.max(amount)), 100 * float(np.max(percent))


def metrics(
    trades: list[dict],
    starting_balance: float,
    equity_values: list[float] | None = None,
) -> dict:
    wins = [row for row in trades if row["pnl_usd"] > 0]
    losses = [row for row in trades if row["pnl_usd"] < 0]
    gross_profit = sum(row["pnl_usd"] for row in wins)
    gross_loss = -sum(row["pnl_usd"] for row in losses)
    ending = trades[-1]["balance_after_usd"] if trades else starting_balance
    realized_dd, realized_dd_pct = drawdown(
        [starting_balance] + [row["balance_after_usd"] for row in trades]
    )
    result = {
        "starting_balance_usd": round(starting_balance, 2),
        "ending_balance_usd": round(ending, 2),
        "net_profit_usd": round(ending - starting_balance, 2),
        "return_pct": round(100 * (ending - starting_balance) / starting_balance, 2),
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(trades), 2),
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "profit_factor": (
            round(gross_profit / gross_loss, 3) if gross_loss else None
        ),
        "maximum_realized_drawdown_usd": round(realized_dd, 2),
        "maximum_realized_drawdown_pct": round(realized_dd_pct, 2),
        "account_survived": ending > 0,
    }
    if equity_values:
        tick_dd, tick_dd_pct = drawdown(equity_values)
        result.update(
            {
                "maximum_tick_equity_drawdown_usd": round(tick_dd, 2),
                "maximum_tick_equity_drawdown_pct": round(tick_dd_pct, 2),
                "minimum_tick_equity_usd": round(min(equity_values), 2),
            }
        )
    return result


def replay(
    config: ExecutionConfig,
    events: list[dict],
    ticks_by_release: dict[str, dict[str, np.ndarray]],
    info: object,
    leverage: int,
    *,
    starting_balance: float = STARTING_BALANCE,
    include_path: bool = False,
) -> tuple[list[dict], dict]:
    if config.stop_usd is None:
        raise ValueError("A protective stop is required for risk sizing.")
    balance = starting_balance
    equity_values = [starting_balance]
    trades = []
    for event in events:
        lot, budget, nominal_risk = risk_lot(balance, config.stop_usd, info)
        result = _simulate_event(
            ticks_by_release[event["release_utc"]],
            release=_utc(event["release_utc"]),
            direction=event["v9_direction"],
            config=config,
            balance=balance,
            info=info,
            leverage=leverage,
            lot=lot,
            include_path=include_path,
        )
        if result["status"] != "EXECUTED":
            raise RuntimeError(
                f"{event['release_utc']} failed: {result['status']}"
            )
        if include_path:
            equity_values.extend(result.pop("equity_path").tolist())
        before = balance
        balance += float(result["pnl_usd"])
        trades.append(
            {
                "release_utc": event["release_utc"],
                "event": event["event"],
                "direction": event["v9_direction"],
                "confidence_pct": event["confidence_pct"],
                "action_tier": event["action_tier"],
                "actual_direction": event["actual"],
                "direction_correct": event["v9_direction"] == event["actual"],
                "balance_before_usd": round(before, 2),
                "risk_budget_usd": round(budget, 2),
                "nominal_risk_usd": round(nominal_risk, 2),
                **result,
                "realized_r": round(float(result["pnl_usd"]) / nominal_risk, 4),
                "balance_after_usd": round(balance, 2),
            }
        )
    return trades, metrics(
        trades, starting_balance, equity_values if include_path else None
    )


def wilson_lower_bound(wins: int, total: int, z: float = 1.96) -> float:
    rate = wins / total
    denominator = 1 + z * z / total
    center = rate + z * z / (2 * total)
    margin = z * math.sqrt(
        (rate * (1 - rate) + z * z / (4 * total)) / total
    )
    return (center - margin) / denominator


def rank_training(rows: list[dict]) -> list[dict]:
    eligible = [
        row
        for row in rows
        if row["metrics"]["account_survived"]
        and row["metrics"]["profit_factor"] is not None
        and row["metrics"]["profit_factor"] >= 1.25
        and row["metrics"]["maximum_realized_drawdown_pct"] <= 12.0
    ]
    if not eligible:
        raise RuntimeError("No candidate met the predeclared constraints.")
    return sorted(
        eligible,
        key=lambda row: (
            wilson_lower_bound(
                row["metrics"]["wins"], row["metrics"]["trades"]
            ),
            min(row["metrics"]["profit_factor"], 5.0),
            row["metrics"]["return_pct"],
            -row["metrics"]["maximum_realized_drawdown_pct"],
        ),
        reverse=True,
    )


def window_result(trades: list[dict], performance: dict) -> dict:
    direction_wins = sum(row["direction_correct"] for row in trades)
    return {
        "direction": {
            "events": len(trades),
            "wins": direction_wins,
            "losses": len(trades) - direction_wins,
            "accuracy_pct": round(100 * direction_wins / len(trades), 2),
            "coverage_pct": 100.0,
        },
        "performance": performance,
    }


def config_label(config: ExecutionConfig) -> str:
    target = "none" if config.take_profit_usd is None else str(config.take_profit_usd)
    return (
        f"T{config.entry_offset_seconds:+d}s entry, "
        f"{config.stop_usd} USD stop, {target} USD target, "
        f"T+{config.exit_after_seconds}s exit"
    )


def render_markdown(report: dict) -> str:
    lines = [
        "# Gold News V9 Execution V2 - One-Year Replay",
        "",
        "> The V9 direction model is unchanged. Parameters were selected on the "
        "first 20 releases only. The final nine releases are untouched holdout data. "
        "All NFP, CPI, and FOMC calls are executed.",
        "",
        "## Selected Rule",
        "",
        f"**{report['selected_configuration_label']}**",
        "",
        "## Results",
        "",
        "| Window | Trades | Direction accuracy | Trade win rate | PF | Return | End balance | Realized DD | Tick DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label in (
        ("development", "Development"),
        ("holdout", "Untouched holdout"),
        ("full_year", "Full year"),
    ):
        row = report["results"][key]
        d = row["direction"]
        p = row["performance"]
        lines.append(
            f"| {label} | {p['trades']} | {d['accuracy_pct']:.2f}% | "
            f"{p['win_rate_pct']:.2f}% | {p['profit_factor']:.3f} | "
            f"{p['return_pct']:+.2f}% | {p['ending_balance_usd']:.2f} USD | "
            f"{p['maximum_realized_drawdown_pct']:.2f}% | "
            f"{p['maximum_tick_equity_drawdown_pct']:.2f}% |"
        )
    base = report["baseline_full_year"]
    full = report["results"]["full_year"]["performance"]
    lines.extend(
        [
            "",
            "## Baseline Comparison",
            "",
            "| Version | Win rate | PF | Return | End balance | Realized DD | Tick DD |",
            "|---|---:|---:|---:|---:|---:|---:|",
            f"| Original | {base['win_rate_pct']:.2f}% | "
            f"{base['profit_factor']:.3f} | {base['return_pct']:+.2f}% | "
            f"{base['ending_balance_usd']:.2f} USD | "
            f"{base['maximum_realized_drawdown_pct']:.2f}% | "
            f"{base['maximum_tick_equity_drawdown_pct']:.2f}% |",
            f"| Execution V2 | {full['win_rate_pct']:.2f}% | "
            f"{full['profit_factor']:.3f} | {full['return_pct']:+.2f}% | "
            f"{full['ending_balance_usd']:.2f} USD | "
            f"{full['maximum_realized_drawdown_pct']:.2f}% | "
            f"{full['maximum_tick_equity_drawdown_pct']:.2f}% |",
            "",
            "## Full-Year Trades",
            "",
            "| Date | Event | Call | Confidence | Actual | Exit | Captured | P/L | Balance |",
            "|---|---|---|---:|---|---|---:|---:|---:|",
        ]
    )
    for row in report["trades"]:
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | "
            f"{row['direction']} | {row['confidence_pct']:.1f}% | "
            f"{row['actual_direction']} | {row['exit_reason']} | "
            f"{row['captured_move_usd']:+.3f} USD | "
            f"{row['pnl_usd']:+.2f} USD | {row['balance_after_usd']:.2f} USD |"
        )
    lines.extend(
        [
            "",
            "## Limits",
            "",
            "- Prediction accuracy is measured at T+15; a correct direction can still "
            "lose if price reaches the stop first.",
            "- The holdout is the honest execution test. Full-year performance also "
            "contains the development period.",
            "- Spread and tick-gap slippage are included. Commission, network delay, "
            "rejections, and market-depth impact are not.",
            "- Twenty development and nine holdout releases are small samples. "
            "Results are evidence, not a guarantee.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    events = load_events()
    development = [
        row for row in events
        if date.fromisoformat(row["release_utc"][:10]) < HOLDOUT_START
    ]
    holdout = [
        row for row in events
        if date.fromisoformat(row["release_utc"][:10]) >= HOLDOUT_START
    ]
    if (len(development), len(holdout)) != (20, 9):
        raise RuntimeError(
            f"Expected a 20/9 split, found {len(development)}/{len(holdout)}."
        )

    terminal = os.getenv(
        "MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe"
    )
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        info = mt5.symbol_info("XAUUSD")
        if account is None or info is None or not mt5.symbol_select("XAUUSD", True):
            raise RuntimeError("The connected MT5 account does not expose XAUUSD.")
        ticks_by_release = {}
        sources = {}
        for event in events:
            try:
                ticks_by_release[event["release_utc"]] = _event_ticks(
                    "XAUUSD", _utc(event["release_utc"])
                )
                sources[event["release_utc"]] = "MT5 ticks"
            except RuntimeError:
                ticks_by_release[event["release_utc"]] = _archived_hybrid_ticks(event)
                sources[event["release_utc"]] = "archive ticks + M1 continuation"

        leverage = int(account.leverage)
        training_rows = []
        for config in candidate_configs():
            _, performance = replay(
                config, development, ticks_by_release, info, leverage
            )
            training_rows.append({"config": config, "metrics": performance})
        ranked = rank_training(training_rows)
        selected = ranked[0]["config"]

        development_trades, development_metrics = replay(
            selected, development, ticks_by_release, info, leverage, include_path=True
        )
        holdout_trades, holdout_metrics = replay(
            selected, holdout, ticks_by_release, info, leverage, include_path=True
        )
        full_trades, full_metrics = replay(
            selected, events, ticks_by_release, info, leverage, include_path=True
        )
        _, baseline_metrics = replay(
            BASELINE, events, ticks_by_release, info, leverage, include_path=True
        )
    finally:
        mt5.shutdown()

    for row in full_trades:
        row["data_source"] = sources[row["release_utc"]]
    report = {
        "status": "v9_execution_v2_development_holdout_replay",
        "window": {
            "start": START.isoformat(),
            "end_exclusive": END.isoformat(),
            "holdout_start": HOLDOUT_START.isoformat(),
        },
        "scope": {
            "events": list(SUPPORTED_EVENTS),
            "coverage_pct": 100.0,
            "low_confidence_executed": True,
        },
        "selection": {
            "candidate_configurations": len(training_rows),
            "eligible_after_constraints": len(ranked),
            "rule": (
                "Maximize the 95% Wilson lower bound for development win rate; "
                "require PF >= 1.25 and realized DD <= 12%."
            ),
            "top_ten": [
                {
                    "configuration": asdict(row["config"]),
                    "metrics": row["metrics"],
                }
                for row in ranked[:10]
            ],
        },
        "selected_configuration": asdict(selected),
        "selected_configuration_label": config_label(selected),
        "results": {
            "development": window_result(
                development_trades, development_metrics
            ),
            "holdout": window_result(holdout_trades, holdout_metrics),
            "full_year": window_result(full_trades, full_metrics),
        },
        "baseline_configuration": asdict(BASELINE),
        "baseline_full_year": baseline_metrics,
        "data_source_counts": dict(Counter(sources.values())),
        "broker": {
            "server": account.server,
            "symbol": info.name,
            "leverage": int(account.leverage),
            "volume_min": float(info.volume_min),
            "volume_max": float(info.volume_max),
            "volume_step": float(info.volume_step),
            "tick_size": float(info.trade_tick_size),
            "tick_value_loss": float(info.trade_tick_value_loss),
        },
        "trades": full_trades,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(full_trades[0]))
        writer.writeheader()
        writer.writerows(full_trades)
    OUTPUT_MD.write_text(render_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(
        json.dumps(
            {
                "selected": result["selected_configuration_label"],
                "development": result["results"]["development"],
                "holdout": result["results"]["holdout"],
                "full_year": result["results"]["full_year"],
                "baseline": result["baseline_full_year"],
            },
            indent=2,
        )
    )
    print(f"Saved {OUTPUT_MD}")
