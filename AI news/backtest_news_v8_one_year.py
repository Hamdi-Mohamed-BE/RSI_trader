from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path

import joblib
import MetaTrader5 as mt5
import numpy as np

from backtest_news_v8_move_execution_3m import (
    DIRECTION_RESULTS,
    LOT,
    STARTING_BALANCE,
    ExecutionConfig,
    _event_ticks,
    _run_config,
    _utc,
)
from news_core import ROOT, build_samples, load_day
from news_v8_move_range import (
    RangeConfig,
    magnitude_rows,
    predict_magnitude_range,
    signed_range,
)


START = date(2025, 9, 10)
END = date(2026, 9, 10)
MOVE_MODEL_PATH = ROOT / "models" / "gold_news_v8_move_range.joblib"
OUTPUT_JSON = ROOT / "news_v8_one_year_results.json"
OUTPUT_CSV = ROOT / "news_v8_one_year_trades.csv"
OUTPUT_MD = ROOT / "NEWS_V8_ONE_YEAR_RESULTS.md"
TICK_ARCHIVE = ROOT / "data" / "xau-news-ticks-5y"

FROZEN_EXECUTION = ExecutionConfig(
    entry_offset_seconds=-5,
    stop_usd=4.0,
    take_profit_usd=None,
    trailing_trigger_usd=None,
    trailing_distance_usd=None,
    exit_after_seconds=900,
)


def _bar_path(row: dict[str, float]) -> list[tuple[int, float]]:
    open_ = float(row["open"])
    high = float(row["high"])
    low = float(row["low"])
    close = float(row["close"])
    anchors = [(20_000, low), (40_000, high)] if close >= open_ else [
        (20_000, high),
        (40_000, low),
    ]
    anchors = [(0, open_), *anchors, (59_000, close)]
    path = []
    for (start_ms, start_price), (end_ms, end_price) in zip(anchors, anchors[1:]):
        for stamp in range(start_ms, end_ms, 1_000):
            fraction = (stamp - start_ms) / (end_ms - start_ms)
            path.append((stamp, start_price + fraction * (end_price - start_price)))
    path.append(anchors[-1])
    return path


def _mt5_bid_bars(release: datetime) -> dict[int, dict[str, float]]:
    rates = mt5.copy_rates_range(
        "XAUUSD",
        mt5.TIMEFRAME_M1,
        release - timedelta(minutes=2),
        release + timedelta(seconds=FROZEN_EXECUTION.exit_after_seconds + 60),
    )
    if rates is None or len(rates) == 0:
        return {}
    return {
        int(row["time"]) * 1000: {
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for row in rates
    }


def _archive_path(event: dict) -> Path | None:
    release = _utc(event["release_utc"])
    pattern = (
        f"xauusd-tick-{release:%Y-%m-%d}-{release:%H%M}-"
        f"{event['event'].lower()}.json"
    )
    path = TICK_ARCHIVE / pattern
    return path if path.exists() else None


def _archived_hybrid_ticks(event: dict) -> dict[str, np.ndarray]:
    path = _archive_path(event)
    if path is None:
        raise RuntimeError("No archived bid/ask tick file is available.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw = payload.get("ticks", [])
    if len(raw) < 20:
        raise RuntimeError(f"Archived tick file is incomplete: {path.name}")
    times = [int(row["timestamp"]) for row in raw]
    bids = [float(row["bidPrice"]) for row in raw]
    asks = [float(row["askPrice"]) for row in raw]
    first_exact_ms = min(times)
    last_exact_ms = max(times)
    positive_spreads = [ask - bid for bid, ask in zip(bids, asks) if ask > bid]
    archive_spread = float(np.median(positive_spreads)) if positive_spreads else 0.3

    release = _utc(event["release_utc"])
    release_ms = int(release.timestamp() * 1000)
    end_ms = release_ms + FROZEN_EXECUTION.exit_after_seconds * 1000
    last_ms = times[-1]
    day = release.date().isoformat()
    bid_bars = load_day(day, "bid")
    ask_bars = load_day(day, "ask")
    if not bid_bars:
        bid_bars = _mt5_bid_bars(release)
    if bid_bars and not ask_bars:
        ask_bars = {
            stamp: {
                key: float(value) + archive_spread
                for key, value in row.items()
            }
            for stamp, row in bid_bars.items()
        }
    if not bid_bars or not ask_bars:
        raise RuntimeError("Matching M1 bridge is unavailable.")

    first_minute = ((release_ms - 60_000) // 60_000) * 60_000
    is_buy = event["prediction"] == "POSITIVE"
    for stamp in range(first_minute, end_ms + 60_000, 60_000):
        bid_row = bid_bars.get(stamp)
        ask_row = ask_bars.get(stamp)
        if not bid_row or not ask_row:
            continue
        spread = max(0.001, float(ask_row["close"]) - float(bid_row["close"]))
        source = bid_row if is_buy else ask_row
        for offset, executable in _bar_path(source):
            tick_ms = stamp + offset
            if first_exact_ms <= tick_ms <= last_exact_ms or tick_ms > end_ms:
                continue
            if is_buy:
                bid, ask = executable, executable + spread
            else:
                bid, ask = executable - spread, executable
            times.append(tick_ms)
            bids.append(bid)
            asks.append(ask)
    if min(times) > release_ms + FROZEN_EXECUTION.entry_offset_seconds * 1000:
        raise RuntimeError("Archived data does not reach the T-5 entry.")
    if max(times) < end_ms:
        raise RuntimeError("Archived data does not reach the T+15 exit.")
    order = np.argsort(np.asarray(times, dtype=np.int64))
    return {
        "time_msc": np.asarray(times, dtype=np.int64)[order],
        "bid": np.asarray(bids, dtype=float)[order],
        "ask": np.asarray(asks, dtype=float)[order],
    }


def _magnitude_backtest(direction_events: list[dict]) -> dict:
    samples, audit = build_samples(15)
    rows = magnitude_rows(samples)
    artifact = joblib.load(MOVE_MODEL_PATH)
    config = RangeConfig(**artifact["configuration"])
    wanted = {
        (row["release_utc"][:10], row["event"]): row for row in direction_events
    }
    history = []
    events = []
    for row in rows:
        key = (row["release_utc"][:10], row["event"])
        if key in wanted:
            direction = wanted[key]
            forecast = predict_magnitude_range(
                history,
                event=row["event"],
                current_atr=float(row["atr_30m"]),
                current_spread=float(row["spread_usd"]),
                config=config,
            )
            signed = signed_range(direction["prediction"], forecast)
            actual = float(direction["release_move_usd"])
            magnitude_hit = (
                forecast["minimum_usd"] <= abs(actual) <= forecast["maximum_usd"]
            )
            direction_correct = bool(direction["correct"])
            events.append(
                {
                    "release_utc": direction["release_utc"],
                    "event": direction["event"],
                    "prediction": direction["prediction"],
                    "actual_direction": direction["actual"],
                    "predicted_range_low_usd": signed["range_low_usd"],
                    "predicted_point_usd": signed["point_estimate_usd"],
                    "predicted_range_high_usd": signed["range_high_usd"],
                    "predicted_display": signed["display"],
                    "actual_move_usd": round(actual, 3),
                    "direction_correct": direction_correct,
                    "magnitude_range_hit": magnitude_hit,
                    "signed_range_hit": direction_correct and magnitude_hit,
                }
            )
        history.append(row)

    count = len(events)
    direction_hits = sum(row["direction_correct"] for row in events)
    magnitude_hits = sum(row["magnitude_range_hit"] for row in events)
    signed_hits = sum(row["signed_range_hit"] for row in events)
    return {
        "configuration": artifact["configuration"],
        "sample_audit": audit,
        "events": events,
        "direction_accuracy_pct": round(100 * direction_hits / count, 2),
        "magnitude_coverage_pct": round(100 * magnitude_hits / count, 2),
        "signed_coverage_pct": round(100 * signed_hits / count, 2),
        "median_estimate_mae_usd": round(
            float(
                np.mean(
                    [
                        abs(abs(row["actual_move_usd"]) - abs(row["predicted_point_usd"]))
                        for row in events
                    ]
                )
            ),
            2,
        ),
    }


def _event_breakdown(prediction: dict, trades: list[dict]) -> list[dict]:
    by_release = {row["release_utc"]: row for row in trades}
    results = []
    for event_name in ("CPI", "NFP", "FOMC"):
        predictions = [
            row for row in prediction["events"] if row["event"] == event_name
        ]
        event_trades = [
            by_release[row["release_utc"]]
            for row in predictions
            if row["release_utc"] in by_release
        ]
        gross_profit = sum(max(0.0, float(row["pnl_usd"])) for row in event_trades)
        gross_loss = -sum(min(0.0, float(row["pnl_usd"])) for row in event_trades)
        results.append(
            {
                "event": event_name,
                "releases": len(predictions),
                "direction_wins": sum(row["direction_correct"] for row in predictions),
                "direction_accuracy_pct": round(
                    100
                    * sum(row["direction_correct"] for row in predictions)
                    / len(predictions),
                    2,
                ),
                "trade_wins": sum(row["pnl_usd"] > 0 for row in event_trades),
                "trade_win_rate_pct": round(
                    100 * sum(row["pnl_usd"] > 0 for row in event_trades)
                    / len(event_trades),
                    2,
                ),
                "net_profit_usd": round(
                    sum(float(row["pnl_usd"]) for row in event_trades), 2
                ),
                "profit_factor": round(gross_profit / gross_loss, 2),
            }
        )
    return results


def _markdown(report: dict) -> str:
    prediction = report["prediction_backtest"]
    execution = report["execution_backtest"]
    metrics = execution["metrics"]
    by_release = {row["release_utc"]: row for row in execution["trades"]}
    lines = [
        "# Gold News V8 - Frozen Parameters, One-Year Replay",
        "",
        "> The three-month winner is applied unchanged: 0.08 lot, market entry at T-5 seconds, $4 gold-price stop, no take profit, no trailing stop, and exit at T+15 minutes. MT5 bid/ask ticks include spread and crossing slippage.",
        "",
        "## Summary",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Prediction events | {len(prediction['events'])} |",
        f"| Direction accuracy | {prediction['direction_accuracy_pct']:.2f}% |",
        f"| Magnitude-range coverage | {prediction['magnitude_coverage_pct']:.2f}% |",
        f"| Signed-range coverage | {prediction['signed_coverage_pct']:.2f}% |",
        f"| Starting balance | ${metrics['starting_balance_usd']:.2f} |",
        f"| Ending balance | ${metrics['ending_balance_usd']:.2f} |",
        f"| Net P/L | ${metrics['net_profit_usd']:+.2f} |",
        f"| Executed trades | {metrics['executed_trades']} |",
        f"| Wins / losses | {metrics['wins']} / {metrics['losses']} |",
        f"| Win rate | {metrics['win_rate_pct']:.2f}% |",
        f"| Profit factor | {metrics['profit_factor']} |",
        f"| Maximum realized drawdown | ${metrics['maximum_realized_drawdown_usd']:.2f} ({metrics['maximum_realized_drawdown_pct']:.2f}%) |",
        f"| Maximum tick-equity drawdown | ${metrics.get('maximum_tick_equity_drawdown_usd', 0):.2f} ({metrics.get('maximum_tick_equity_drawdown_pct', 0):.2f}%) |",
        f"| Minimum tick equity | ${metrics.get('minimum_tick_equity_usd', 0):.2f} |",
        f"| Fully tick-exact executions | {execution['source_counts'].get('MT5 ticks', 0)} |",
        f"| Tick + M1 continuation executions | {execution['source_counts'].get('archive ticks + M1 continuation', 0)} |",
        "",
        "## Event Breakdown",
        "",
        "| Event | Releases | Direction accuracy | Trade win rate | Net P/L | Profit factor |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in execution["event_breakdown"]:
        lines.append(
            f"| {row['event']} | {row['releases']} | "
            f"{row['direction_wins']}/{row['releases']} ({row['direction_accuracy_pct']:.2f}%) | "
            f"{row['trade_wins']}/{row['releases']} ({row['trade_win_rate_pct']:.2f}%) | "
            f"${row['net_profit_usd']:+.2f} | {row['profit_factor']:.2f} |"
        )
    lines.extend(
        [
        "",
        "## Predictions and $100 Simulation",
        "",
        "| Date | Event | Call | Predicted release move | Actual release move | Direction | Range | Captured | Exit | P/L | Balance | Source |",
        "|---|---|---|---:|---:|---|---|---:|---|---:|---:|---|",
        ]
    )
    for row in prediction["events"]:
        trade = by_release.get(row["release_utc"])
        if trade:
            captured = f"{trade.get('captured_move_usd', 0):+.2f}"
            exit_reason = trade.get("exit_reason", trade["status"])
            pnl = f"${trade['pnl_usd']:+.2f}"
            balance = f"${trade['balance_after_usd']:.2f}"
        else:
            captured, exit_reason, pnl, balance = "-", "NO TICKS", "$0.00", "-"
        source = trade.get("data_source", "-") if trade else "-"
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['prediction']} | "
            f"{row['predicted_display']} | {row['actual_move_usd']:+.2f} | "
            f"{'WIN' if row['direction_correct'] else 'LOSS'} | "
            f"{'HIT' if row['magnitude_range_hit'] else 'MISS'} | {captured} | "
            f"{exit_reason} | {pnl} | {balance} | {source} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The execution parameters were discovered inside the final three months of this one-year table. The full-year replay is retrospective and is not a clean prospective validation.",
            "- The magnitude range is walk-forward: every row uses only earlier event outcomes.",
            "- Commission, execution rejection, and network latency are unavailable historically. They are excluded; spread and tick-gap slippage are included where ticks exist.",
            "- Hybrid rows use archived bid/ask ticks where available and M1 OHLC to bridge missing seconds through T+15. A fixed-stop crossing in an M1 segment is detected, but its exact sub-minute slippage cannot be reconstructed.",
            "- Fixed 0.08 lot is used throughout; lot size is not compounded as the balance changes.",
        ]
    )
    if execution["missing_tick_events"]:
        lines.append(
            f"- MT5 tick history was unavailable for {len(execution['missing_tick_events'])} releases; those events remain in the prediction table but are not executed."
        )
    return "\n".join(lines) + "\n"


def run() -> dict:
    payload = json.loads(DIRECTION_RESULTS.read_text(encoding="utf-8"))
    direction_events = [
        dict(row)
        for row in payload["events"]
        if START <= date.fromisoformat(row["release_utc"][:10]) < END
    ]
    prediction = _magnitude_backtest(direction_events)

    terminal = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        info = mt5.symbol_info("XAUUSD")
        if account is None or info is None or not mt5.symbol_select("XAUUSD", True):
            raise RuntimeError("The connected MT5 account does not expose XAUUSD.")
        ticks_by_release = {}
        tick_sources = {}
        executable_events = []
        missing = []
        for event in direction_events:
            try:
                ticks_by_release[event["release_utc"]] = _event_ticks(
                    "XAUUSD", _utc(event["release_utc"])
                )
                tick_sources[event["release_utc"]] = "MT5 ticks"
                executable_events.append(event)
            except RuntimeError as error:
                try:
                    ticks_by_release[event["release_utc"]] = _archived_hybrid_ticks(event)
                    tick_sources[event["release_utc"]] = (
                        "archive ticks + M1 continuation"
                    )
                    executable_events.append(event)
                except RuntimeError as fallback_error:
                    missing.append(
                        {
                            "release_utc": event["release_utc"],
                            "event": event["event"],
                            "reason": f"{error}; fallback: {fallback_error}",
                        }
                    )
        trades, metrics = _run_config(
            FROZEN_EXECUTION,
            executable_events,
            ticks_by_release,
            info,
            int(account.leverage),
            starting_balance=STARTING_BALANCE,
            include_path=True,
        )
        for trade in trades:
            trade["data_source"] = tick_sources[trade["release_utc"]]
    finally:
        mt5.shutdown()

    report = {
        "window": {"start": START.isoformat(), "end_exclusive": END.isoformat()},
        "broker": {
            "server": account.server,
            "symbol": "XAUUSD",
            "leverage": int(account.leverage),
            "contract_size": float(info.trade_contract_size),
            "lot": LOT,
        },
        "frozen_execution_configuration": {
            "entry_offset_seconds": FROZEN_EXECUTION.entry_offset_seconds,
            "stop_usd": FROZEN_EXECUTION.stop_usd,
            "take_profit_usd": FROZEN_EXECUTION.take_profit_usd,
            "trailing_trigger_usd": FROZEN_EXECUTION.trailing_trigger_usd,
            "trailing_distance_usd": FROZEN_EXECUTION.trailing_distance_usd,
            "exit_after_seconds": FROZEN_EXECUTION.exit_after_seconds,
        },
        "prediction_backtest": prediction,
        "execution_backtest": {
            "metrics": metrics,
            "trades": trades,
            "event_breakdown": _event_breakdown(prediction, trades),
            "missing_tick_events": missing,
            "source_counts": {
                source: sum(value == source for value in tick_sources.values())
                for source in sorted(set(tick_sources.values()))
            },
        },
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if trades:
        with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(trades[0]))
            writer.writeheader()
            writer.writerows(trades)
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
