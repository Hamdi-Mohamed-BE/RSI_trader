from __future__ import annotations

import csv
import json
import math
import os
from datetime import date

import MetaTrader5 as mt5

from backtest_news_v8_dynamic_compounding_3m import _dynamic_lot, _metrics
from backtest_news_v8_move_execution_3m import (
    DIRECTION_RESULTS,
    RECENT_START,
    ExecutionConfig,
    _event_ticks,
    _simulate_event,
    _utc,
)
from news_core import ROOT
from train_news_v9_direction import run as train_live_model


END = date(2026, 9, 10)
STARTING_BALANCE = 100.0
V6_REPORT = ROOT / "news_v6_fxmacro_3m_results.json"
OUTPUT_JSON = ROOT / "news_v9_direction_3m_results.json"
OUTPUT_CSV = ROOT / "news_v9_direction_3m_trades.csv"
OUTPUT_MD = ROOT / "NEWS_V9_DIRECTION_3M_RESULTS.md"

CONFIG = ExecutionConfig(
    entry_offset_seconds=-5,
    stop_usd=4.0,
    take_profit_usd=None,
    trailing_trigger_usd=None,
    trailing_distance_usd=None,
    exit_after_seconds=900,
)


def _wilson(wins: int, calls: int) -> list[float]:
    if calls == 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = wins / calls
    denominator = 1 + z * z / calls
    center = (p + z * z / (2 * calls)) / denominator
    margin = z * math.sqrt(
        (p * (1 - p) + z * z / (4 * calls)) / calls
    ) / denominator
    return [round(100 * (center - margin), 2), round(100 * (center + margin), 2)]


def _score(rows: list[dict], *, tier: str | None = None) -> dict:
    selected = rows if tier is None else [row for row in rows if row["action_tier"] == tier]
    wins = sum(row["v9_direction"] == row["actual_direction"] for row in selected)
    return {
        "events": len(rows),
        "calls": len(selected),
        "wins": wins,
        "losses": len(selected) - wins,
        "accuracy_pct": round(100 * wins / len(selected), 2) if selected else 0.0,
        "coverage_pct": round(100 * len(selected) / len(rows), 2) if rows else 0.0,
        "wilson_95_pct": _wilson(wins, len(selected)),
    }


def _simulate(
    events: list[dict],
    ticks: dict,
    info: object,
    leverage: int,
    *,
    dynamic: bool,
) -> tuple[list[dict], dict]:
    balance = STARTING_BALANCE
    equity_values = [STARTING_BALANCE]
    trades = []
    for event in events:
        units, lot = _dynamic_lot(balance, info) if dynamic else (1, 0.08)
        before = balance
        result = _simulate_event(
            ticks[event["release_utc"]],
            release=_utc(event["release_utc"]),
            direction=event["v9_direction"],
            config=CONFIG,
            balance=balance,
            info=info,
            leverage=leverage,
            lot=lot,
            include_path=True,
        )
        balance += float(result["pnl_usd"])
        equity_values.extend(result.pop("equity_path").tolist())
        trades.append(
            {
                **event,
                "balance_units": units,
                "balance_before_usd": round(before, 2),
                **result,
                "balance_after_usd": round(balance, 2),
            }
        )
    return trades, _metrics(trades, equity_values)


def _markdown(report: dict) -> str:
    direction = report["direction_metrics"]
    dynamic = report["dynamic_simulation"]["metrics"]
    fixed = report["fixed_008_simulation"]["metrics"]
    lines = [
        "# Gold News V9 - Three-Month Direction and Execution Replay",
        "",
        "> V9 promotes the frozen V5/V6 event-specific bias to a full direction and retains the original gate as TRADE versus LOW_CONFIDENCE. The execution replay uses exact MT5 bid/ask ticks.",
        "",
        "## Direction Results",
        "",
        "| Policy | Calls | Wins | Accuracy | Coverage |",
        "|---|---:|---:|---:|---:|",
        f"| V7 baseline | {direction['v7_baseline']['calls']} | {direction['v7_baseline']['wins']} | {direction['v7_baseline']['accuracy_pct']:.2f}% | 100.00% |",
        f"| V9 all directions | {direction['v9_full']['calls']} | {direction['v9_full']['wins']} | {direction['v9_full']['accuracy_pct']:.2f}% | 100.00% |",
        f"| V9 TRADE tier | {direction['trade_tier']['calls']} | {direction['trade_tier']['wins']} | {direction['trade_tier']['accuracy_pct']:.2f}% | {direction['trade_tier']['coverage_pct']:.2f}% |",
        f"| V9 LOW_CONFIDENCE tier | {direction['low_confidence_tier']['calls']} | {direction['low_confidence_tier']['wins']} | {direction['low_confidence_tier']['accuracy_pct']:.2f}% | {direction['low_confidence_tier']['coverage_pct']:.2f}% |",
        "",
        "## Execution Results",
        "",
        "| Sizing | Start | End | Net P/L | Wins | Win rate | Profit factor | Max realized DD | Max tick DD |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| Fixed 0.08 lot | ${fixed['starting_balance_usd']:.2f} | ${fixed['ending_balance_usd']:.2f} | ${fixed['net_profit_usd']:+.2f} | {fixed['wins']}/{fixed['executed_trades']} | {fixed['win_rate_pct']:.2f}% | {fixed['profit_factor']:.2f} | {fixed['maximum_realized_drawdown_pct']:.2f}% | {fixed['maximum_tick_equity_drawdown_pct']:.2f}% |",
        f"| 0.06 per complete $100 | ${dynamic['starting_balance_usd']:.2f} | ${dynamic['ending_balance_usd']:.2f} | ${dynamic['net_profit_usd']:+.2f} | {dynamic['wins']}/{dynamic['executed_trades']} | {dynamic['win_rate_pct']:.2f}% | {dynamic['profit_factor']:.2f} | {dynamic['maximum_realized_drawdown_pct']:.2f}% | {dynamic['maximum_tick_equity_drawdown_pct']:.2f}% |",
        "",
        "## Prediction and Dynamic Simulation Table",
        "",
        "| Date | Event | V7 | V9 | Tier | Confidence | Actual | Result | Lot | Captured | P/L | Balance |",
        "|---|---|---|---|---|---:|---|---|---:|---:|---:|---:|",
    ]
    for row in report["dynamic_simulation"]["trades"]:
        result = "WIN" if row["v9_direction"] == row["actual_direction"] else "LOSS"
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['v7_direction']} | "
            f"{row['v9_direction']} | {row['action_tier']} | {row['confidence_pct']:.2f}% | "
            f"{row['actual_direction']} | {result} | {row['lot']:.2f} | "
            f"{row['captured_move_usd']:+.3f} USD | ${row['pnl_usd']:+.2f} | "
            f"${row['balance_after_usd']:.2f} |"
        )
    lines.extend(
        [
            "",
            "## Honesty Notes",
            "",
            "- V9 improves this retrospective eight-event table from 5/8 to 6/8 by correcting July 29 FOMC and August 7 NFP, while changing July 2 NFP from correct to wrong.",
            "- V5/V6 was designed after part of this period was visible. Therefore 75% is not an untouched forward result and cannot establish a stable improvement.",
            "- Point-in-time consensus history is incomplete. Consensus, official nowcasts, and macro-regime candidates remain context-only when their chronological validation does not beat the frozen direction rule.",
            "- Dynamic compounding magnifies one changed prediction dramatically. Commission, latency, rejection, and large-order market-depth slippage are unavailable historically.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    v6 = json.loads(V6_REPORT.read_text(encoding="utf-8"))
    v7 = json.loads(DIRECTION_RESULTS.read_text(encoding="utf-8"))
    v7_by_release = {
        row["release_utc"]: row
        for row in v7["events"]
        if RECENT_START <= date.fromisoformat(row["release_utc"][:10]) < END
    }
    events = []
    for row in v6["events"]:
        if not (RECENT_START <= date.fromisoformat(row["release_utc"][:10]) < END):
            continue
        baseline = v7_by_release[row["release_utc"]]
        events.append(
            {
                "release_utc": row["release_utc"],
                "event": row["event"],
                "v7_direction": baseline["prediction"],
                "v9_direction": row["shadow_bias"],
                "action_tier": "TRADE" if row["prediction"] != "NO CALL" else "LOW_CONFIDENCE",
                "confidence_pct": float(row["confidence_pct"]),
                "actual_direction": baseline["actual"],
                "actual_release_move_usd": float(baseline["release_move_usd"]),
            }
        )
    events.sort(key=lambda row: row["release_utc"])

    terminal = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        info = mt5.symbol_info("XAUUSD")
        if account is None or info is None or not mt5.symbol_select("XAUUSD", True):
            raise RuntimeError("The connected MT5 account does not expose XAUUSD.")
        ticks = {
            row["release_utc"]: _event_ticks("XAUUSD", _utc(row["release_utc"]))
            for row in events
        }
        dynamic_trades, dynamic_metrics = _simulate(
            events, ticks, info, int(account.leverage), dynamic=True
        )
        fixed_trades, fixed_metrics = _simulate(
            events, ticks, info, int(account.leverage), dynamic=False
        )
    finally:
        mt5.shutdown()

    baseline_rows = [
        {**row, "v9_direction": row["v7_direction"]} for row in events
    ]
    report = {
        "status": "v9_retrospective_candidate",
        "window": {"start": RECENT_START.isoformat(), "end_exclusive": END.isoformat()},
        "methodology": {
            "prediction_cutoff": "T-15 canonical feature snapshot",
            "direction": "V5/V6 event-specific shadow bias promoted to full coverage",
            "action_tier": "Original V5 gate: TRADE or LOW_CONFIDENCE",
            "execution": "T-5 seconds, $4 stop, no TP, no trailing, T+15 exit",
            "dynamic_sizing": "floor(balance / $100) x 0.06 lot",
        },
        "broker": {
            "server": account.server,
            "symbol": "XAUUSD",
            "leverage": int(account.leverage),
        },
        "direction_metrics": {
            "v7_baseline": _score(baseline_rows),
            "v9_full": _score(events),
            "trade_tier": _score(events, tier="TRADE"),
            "low_confidence_tier": _score(events, tier="LOW_CONFIDENCE"),
        },
        "fixed_008_simulation": {"metrics": fixed_metrics, "trades": fixed_trades},
        "dynamic_simulation": {"metrics": dynamic_metrics, "trades": dynamic_trades},
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(dynamic_trades[0]))
        writer.writeheader()
        writer.writerows(dynamic_trades)
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")
    report["live_artifact"] = train_live_model()
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
