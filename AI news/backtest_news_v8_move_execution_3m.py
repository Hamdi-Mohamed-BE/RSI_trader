from __future__ import annotations

import csv
import json
import math
import os
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone

import joblib
import MetaTrader5 as mt5
import numpy as np

from news_core import ROOT, build_samples
from news_v8_move_range import (
    RangeConfig,
    fit_move_range_artifact,
    magnitude_rows,
    predict_magnitude_range,
    select_range_config,
    signed_range,
)


DIRECTION_RESULTS = ROOT / "news_v7_full_coverage_results.json"
OUTPUT_JSON = ROOT / "news_v8_move_execution_3m_results.json"
OUTPUT_CSV = ROOT / "news_v8_move_execution_3m_trades.csv"
OUTPUT_MD = ROOT / "NEWS_V8_MOVE_EXECUTION_3M_RESULTS.md"
MODEL_PATH = ROOT / "models" / "gold_news_v8_move_range.joblib"

RECENT_START = date(2026, 6, 10)
HOLDOUT_START = date(2026, 8, 7)
STARTING_BALANCE = 100.0
LOT = 0.08
MAX_TICK_WINDOW_SECONDS = 3600


@dataclass(frozen=True)
class ExecutionConfig:
    entry_offset_seconds: int
    stop_usd: float | None
    take_profit_usd: float | None
    trailing_trigger_usd: float | None
    trailing_distance_usd: float | None
    exit_after_seconds: int


def _utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(timezone.utc)


def _event_ticks(symbol: str, release: datetime) -> dict[str, np.ndarray]:
    start = release - timedelta(seconds=40)
    end = release + timedelta(seconds=MAX_TICK_WINDOW_SECONDS + 5)
    raw = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
    if raw is None or len(raw) < 20:
        raise RuntimeError(
            f"MT5 tick history is incomplete for {release.isoformat()}: {mt5.last_error()}"
        )
    return {
        "time_msc": raw["time_msc"].astype(np.int64),
        "bid": raw["bid"].astype(float),
        "ask": raw["ask"].astype(float),
    }


def _first_true(mask: np.ndarray) -> int | None:
    indexes = np.flatnonzero(mask)
    return int(indexes[0]) if len(indexes) else None


def _simulate_event(
    ticks: dict[str, np.ndarray],
    *,
    release: datetime,
    direction: str,
    config: ExecutionConfig,
    balance: float,
    info: object,
    leverage: int,
    lot: float = LOT,
    include_path: bool = False,
) -> dict:
    release_ms = int(release.timestamp() * 1000)
    entry_request_ms = release_ms + config.entry_offset_seconds * 1000
    entry_index = int(np.searchsorted(ticks["time_msc"], entry_request_ms, side="left"))
    if entry_index >= len(ticks["time_msc"]):
        return {"status": "NO_ENTRY_TICK", "pnl_usd": 0.0}

    exit_request_ms = release_ms + config.exit_after_seconds * 1000
    end_index = int(np.searchsorted(ticks["time_msc"], exit_request_ms, side="left"))
    end_index = min(max(entry_index, end_index), len(ticks["time_msc"]) - 1)
    bid = ticks["bid"][entry_index : end_index + 1]
    ask = ticks["ask"][entry_index : end_index + 1]
    times = ticks["time_msc"][entry_index : end_index + 1]
    if len(times) == 0:
        return {"status": "NO_EXIT_TICK", "pnl_usd": 0.0}

    is_buy = direction == "POSITIVE"
    entry_bid = float(bid[0])
    entry_ask = float(ask[0])
    entry = entry_ask if is_buy else entry_bid
    required_margin = float(info.trade_contract_size) * lot * entry / leverage
    if balance < required_margin:
        return {
            "status": "MARGIN_REJECTED",
            "pnl_usd": 0.0,
            "required_margin_usd": round(required_margin, 2),
        }

    executable = bid if is_buy else ask
    favorable = executable - entry if is_buy else entry - executable
    value_per_price_usd = (
        float(info.trade_tick_value) * lot / float(info.trade_tick_size)
    )
    floating = favorable * value_per_price_usd

    candidates: list[tuple[int, int, str]] = []
    if config.take_profit_usd is not None:
        index = _first_true(favorable >= config.take_profit_usd)
        if index is not None:
            candidates.append((index, 0, "TAKE_PROFIT"))

    prior_max = np.empty_like(favorable)
    prior_max[0] = -np.inf
    if len(favorable) > 1:
        prior_max[1:] = np.maximum.accumulate(favorable[:-1])
    trail_active = np.zeros(len(favorable), dtype=bool)
    if config.trailing_trigger_usd is not None:
        trail_active = prior_max >= config.trailing_trigger_usd

    stop_threshold = np.full(len(favorable), -np.inf)
    if config.stop_usd is not None:
        stop_threshold[:] = -config.stop_usd
    if config.trailing_trigger_usd is not None:
        trailing_threshold = prior_max - float(config.trailing_distance_usd)
        stop_threshold = np.where(
            trail_active,
            np.maximum(stop_threshold, trailing_threshold),
            stop_threshold,
        )
    stop_index = _first_true(favorable <= stop_threshold)
    if stop_index is not None:
        reason = "TRAILING_STOP" if trail_active[stop_index] else "STOP_LOSS"
        candidates.append((stop_index, 1, reason))

    # The connected account uses zero-percent stop-out. Preserve that broker rule
    # while still recording when a no-stop experiment exhausts the cash balance.
    stopout_index = _first_true(balance + floating <= 0)
    if stopout_index is not None:
        candidates.append((stopout_index, 2, "BROKER_STOP_OUT"))

    if candidates:
        exit_index, _, exit_reason = min(candidates)
    else:
        exit_index = len(favorable) - 1
        exit_reason = f"TIME_EXIT_T_PLUS_{config.exit_after_seconds}s"

    captured = float(favorable[exit_index])
    pnl = captured * value_per_price_usd
    path_equity = balance + floating[: exit_index + 1]
    result = {
        "status": "EXECUTED",
        "lot": round(lot, 8),
        "entry_time_utc": datetime.fromtimestamp(
            int(times[0]) / 1000, timezone.utc
        ).isoformat(),
        "exit_time_utc": datetime.fromtimestamp(
            int(times[exit_index]) / 1000, timezone.utc
        ).isoformat(),
        "entry_price": round(entry, 3),
        "exit_price": round(float(executable[exit_index]), 3),
        "entry_spread_usd": round(entry_ask - entry_bid, 4),
        "entry_gap_from_request_ms": int(times[0] - entry_request_ms),
        "required_margin_usd": round(required_margin, 2),
        "captured_move_usd": round(captured, 3),
        "maximum_favorable_move_usd": round(
            max(0.0, float(np.max(favorable[: exit_index + 1]))), 3
        ),
        "maximum_adverse_move_usd": round(
            max(0.0, -float(np.min(favorable[: exit_index + 1]))), 3
        ),
        "exit_reason": exit_reason,
        "pnl_usd": round(pnl, 2),
        "minimum_equity_usd": round(float(np.min(path_equity)), 2),
        "maximum_equity_usd": round(float(np.max(path_equity)), 2),
    }
    if include_path:
        result["equity_path"] = path_equity
    return result


def _metrics(trades: list[dict], starting_balance: float = STARTING_BALANCE) -> dict:
    executed = [row for row in trades if row["status"] == "EXECUTED"]
    wins = [row for row in executed if row["pnl_usd"] > 0]
    losses = [row for row in executed if row["pnl_usd"] < 0]
    gross_profit = sum(float(row["pnl_usd"]) for row in wins)
    gross_loss = -sum(float(row["pnl_usd"]) for row in losses)
    balance = starting_balance
    peak = balance
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    for row in trades:
        balance += float(row["pnl_usd"])
        peak = max(peak, balance)
        drawdown = peak - balance
        max_drawdown = max(max_drawdown, drawdown)
        if peak > 0:
            max_drawdown_pct = max(max_drawdown_pct, 100 * drawdown / peak)
    return {
        "starting_balance_usd": round(starting_balance, 2),
        "ending_balance_usd": round(balance, 2),
        "net_profit_usd": round(balance - starting_balance, 2),
        "executed_trades": len(executed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(executed), 2) if executed else 0.0,
        "gross_profit_usd": round(gross_profit, 2),
        "gross_loss_usd": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss else None,
        "maximum_realized_drawdown_usd": round(max_drawdown, 2),
        "maximum_realized_drawdown_pct": round(max_drawdown_pct, 2),
        "account_survived": balance > 0 and len(executed) == len(trades),
    }


def _run_config(
    config: ExecutionConfig,
    events: list[dict],
    ticks_by_release: dict[str, dict[str, np.ndarray]],
    info: object,
    leverage: int,
    *,
    starting_balance: float = STARTING_BALANCE,
    include_path: bool = False,
) -> tuple[list[dict], dict]:
    balance = starting_balance
    trades = []
    equity_values = [starting_balance]
    for event in events:
        result = _simulate_event(
            ticks_by_release[event["release_utc"]],
            release=_utc(event["release_utc"]),
            direction=event["prediction"],
            config=config,
            balance=balance,
            info=info,
            leverage=leverage,
            include_path=include_path,
        )
        before = balance
        balance += float(result["pnl_usd"])
        if include_path and "equity_path" in result:
            equity_values.extend(result.pop("equity_path").tolist())
        trades.append(
            {
                "release_utc": event["release_utc"],
                "event": event["event"],
                "direction": event["prediction"],
                "actual_direction": event["actual"],
                "actual_move_usd": event["release_move_usd"],
                "balance_before_usd": round(before, 2),
                **result,
                "balance_after_usd": round(balance, 2),
            }
        )
    metrics = _metrics(trades, starting_balance)
    if include_path:
        equity = np.asarray(equity_values, dtype=float)
        peaks = np.maximum.accumulate(equity)
        drawdowns = peaks - equity
        pct = np.divide(
            drawdowns,
            peaks,
            out=np.zeros_like(drawdowns),
            where=peaks > 0,
        )
        metrics["maximum_tick_equity_drawdown_usd"] = round(
            float(np.max(drawdowns)), 2
        )
        metrics["maximum_tick_equity_drawdown_pct"] = round(
            100 * float(np.max(pct)), 2
        )
        metrics["minimum_tick_equity_usd"] = round(float(np.min(equity)), 2)
    return trades, metrics


def _candidate_configs() -> list[ExecutionConfig]:
    entries = (-30, -20, -10, -5, 0, 1, 2, 3, 5, 10, 15, 20, 30, 45, 60)
    stops = (None, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0)
    exits = (60, 120, 300, 900, 3600)
    configs = set()

    for entry in entries:
        for stop in stops:
            for target in (None, 20.0, 30.0, 40.0, 46.0, 50.0, 60.0):
                for exit_after in exits:
                    configs.add(
                        ExecutionConfig(entry, stop, target, None, None, exit_after)
                    )

    for entry in entries:
        for stop in (None, 4.0, 6.0, 8.0, 12.0, 20.0):
            for trigger in (10.0, 20.0, 30.0, 40.0):
                for distance in (5.0, 10.0, 15.0, 20.0):
                    if distance > trigger:
                        continue
                    for target in (None, 46.0):
                        for exit_after in (60, 120, 300, 900):
                            configs.add(
                                ExecutionConfig(
                                    entry,
                                    stop,
                                    target,
                                    trigger,
                                    distance,
                                    exit_after,
                                )
                            )
    return sorted(
        configs,
        key=lambda item: (
            item.entry_offset_seconds,
            item.stop_usd is None,
            item.stop_usd or 0,
            item.take_profit_usd is None,
            item.take_profit_usd or 0,
            item.trailing_trigger_usd is None,
            item.trailing_trigger_usd or 0,
            item.trailing_distance_usd or 0,
            item.exit_after_seconds,
        ),
    )


def _ranking_score(metrics: dict) -> float:
    if not metrics["account_survived"]:
        return -1_000_000 + metrics["net_profit_usd"]
    return (
        metrics["net_profit_usd"]
        - 0.75 * metrics["maximum_realized_drawdown_usd"]
        + 0.15 * metrics["win_rate_pct"]
    )


def _optimize(
    configs: list[ExecutionConfig],
    events: list[dict],
    ticks_by_release: dict[str, dict[str, np.ndarray]],
    info: object,
    leverage: int,
) -> list[dict]:
    results = []
    for config in configs:
        _, metrics = _run_config(
            config,
            events,
            ticks_by_release,
            info,
            leverage,
        )
        results.append(
            {
                "config": config,
                "metrics": metrics,
                "score": _ranking_score(metrics),
            }
        )
    return sorted(
        results,
        key=lambda row: (
            row["score"],
            row["metrics"]["net_profit_usd"],
            -row["metrics"]["maximum_realized_drawdown_usd"],
        ),
        reverse=True,
    )


def _format_optional(value: float | None) -> str:
    return "none" if value is None else f"${value:.0f}"


def _config_label(config: ExecutionConfig) -> str:
    entry = f"T{config.entry_offset_seconds:+d}s"
    trail = (
        "none"
        if config.trailing_trigger_usd is None
        else f"activate ${config.trailing_trigger_usd:.0f}, distance ${config.trailing_distance_usd:.0f}"
    )
    return (
        f"entry {entry}; SL {_format_optional(config.stop_usd)}; "
        f"TP {_format_optional(config.take_profit_usd)}; trail {trail}; "
        f"time exit T+{config.exit_after_seconds}s"
    )


def _serialize_ranked(rows: list[dict], limit: int = 20) -> list[dict]:
    return [
        {
            "configuration": asdict(row["config"]),
            "score": round(row["score"], 4),
            "metrics": row["metrics"],
        }
        for row in rows[:limit]
    ]


def _markdown(report: dict) -> str:
    magnitude = report["magnitude_backtest"]
    selected = report["selected_execution"]
    config = ExecutionConfig(**selected["configuration"])
    full = selected["full_three_months"]
    training = selected["selection_window"]
    holdout = selected["untouched_holdout"]
    lines = [
        "# Gold News V8 - Move Range and Execution Study",
        "",
        "> NFP, CPI, and FOMC only. Direction is the frozen V7 walk-forward call. Move intervals use only earlier releases. Execution uses MT5 bid/ask ticks, first available fill after the requested time, and gap slippage.",
        "",
        "## Predicted Move Range - Last Three Months",
        "",
        "| Date | Event | Call | Predicted gold move | Actual release move | Direction | Magnitude range |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for row in magnitude["events"]:
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['prediction']} | "
            f"{row['predicted_display']} | {row['actual_move_usd']:+.2f} USD | "
            f"{'WIN' if row['direction_correct'] else 'LOSS'} | "
            f"{'HIT' if row['magnitude_range_hit'] else 'MISS'} |"
        )
    lines.extend(
        [
            "",
            "### Range Scores",
            "",
            "| Measure | Result |",
            "|---|---:|",
            f"| Direction accuracy | {magnitude['direction_accuracy_pct']:.2f}% |",
            f"| Magnitude interval coverage | {magnitude['magnitude_coverage_pct']:.2f}% |",
            f"| Signed interval coverage | {magnitude['signed_coverage_pct']:.2f}% |",
            f"| Median-estimate MAE | ${magnitude['median_absolute_error_usd']:.2f} |",
            f"| Nominal interval mass | {magnitude['nominal_coverage_pct']:.1f}% |",
            "",
            "## Selected Execution",
            "",
            f"**{_config_label(config)}**",
            "",
            "The configuration was selected on June 10 through July 29. August 7 through September 4 was not used to choose it.",
            "",
            "| Window | Trades | Wins | Win rate | Net P/L | End balance | Profit factor | Max realized DD |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
            f"| Selection window | {training['executed_trades']} | {training['wins']} | {training['win_rate_pct']:.2f}% | ${training['net_profit_usd']:+.2f} | ${training['ending_balance_usd']:.2f} | {training['profit_factor']} | ${training['maximum_realized_drawdown_usd']:.2f} |",
            f"| Untouched holdout | {holdout['executed_trades']} | {holdout['wins']} | {holdout['win_rate_pct']:.2f}% | ${holdout['net_profit_usd']:+.2f} | ${holdout['ending_balance_usd']:.2f} | {holdout['profit_factor']} | ${holdout['maximum_realized_drawdown_usd']:.2f} |",
            f"| Full three months | {full['executed_trades']} | {full['wins']} | {full['win_rate_pct']:.2f}% | ${full['net_profit_usd']:+.2f} | ${full['ending_balance_usd']:.2f} | {full['profit_factor']} | ${full['maximum_realized_drawdown_usd']:.2f} |",
            "",
            "## Full $100 Replay",
            "",
            "| Date | Event | Call | Entry time | Entry | Exit | Exit reason | Gold captured | P/L | Balance |",
            "|---|---|---|---|---:|---:|---|---:|---:|---:|",
        ]
    )
    for row in selected["trades"]:
        entry_time = row.get("entry_time_utc", "-")
        if entry_time != "-":
            parsed_entry = datetime.fromisoformat(entry_time)
            entry_time = parsed_entry.strftime("%H:%M:%S.%f")[:12]
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['direction']} | "
            f"{entry_time} UTC | {row.get('entry_price', 0):.3f} | "
            f"{row.get('exit_price', 0):.3f} | {row.get('exit_reason', row['status'])} | "
            f"{row.get('captured_move_usd', 0):+.3f} USD | ${row['pnl_usd']:+.2f} | "
            f"${row['balance_after_usd']:.2f} |"
        )
    observed = report["best_observed_all_eight"]
    lines.extend(
        [
            "",
            "## Optimization Honesty",
            "",
            f"- Tested {report['search']['candidate_configurations']} predefined configurations.",
            f"- The best-observed all-eight configuration ended at ${observed['metrics']['ending_balance_usd']:.2f}. Its full-period profit remains an in-sample upper bound even when it matches the selection-window winner.",
            "- Commission, latency, rejected orders, and server-side execution asymmetry are unavailable historically. Spread and tick-gap slippage are included.",
            "- Eight releases are far too few to establish stability. The holdout result is the most important number in this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def run() -> dict:
    samples, sample_audit = build_samples(15)
    rows = magnitude_rows(samples)
    range_config, range_ranking = select_range_config(rows, cutoff=RECENT_START)

    direction_payload = json.loads(DIRECTION_RESULTS.read_text(encoding="utf-8"))
    recent_events = [
        dict(row)
        for row in direction_payload["events"]
        if date.fromisoformat(row["release_utc"][:10]) >= RECENT_START
    ]
    history = []
    recent_by_key = {
        (row["release_utc"][:10], row["event"]): row for row in recent_events
    }
    magnitude_events = []
    for row in rows:
        released = date.fromisoformat(row["release_utc"][:10])
        key = (row["release_utc"][:10], row["event"])
        if released >= RECENT_START and key in recent_by_key:
            direction = recent_by_key[key]
            forecast = predict_magnitude_range(
                history,
                event=row["event"],
                current_atr=float(row["atr_30m"]),
                current_spread=float(row["spread_usd"]),
                config=range_config,
            )
            signed = signed_range(direction["prediction"], forecast)
            actual = float(direction["release_move_usd"])
            magnitude_hit = (
                forecast["minimum_usd"] <= abs(actual) <= forecast["maximum_usd"]
            )
            direction_correct = bool(direction["correct"])
            magnitude_events.append(
                {
                    "release_utc": direction["release_utc"],
                    "event": direction["event"],
                    "prediction": direction["prediction"],
                    "actual_direction": direction["actual"],
                    "actual_move_usd": round(actual, 3),
                    "predicted_minimum_abs_usd": forecast["minimum_usd"],
                    "predicted_median_abs_usd": forecast["median_usd"],
                    "predicted_maximum_abs_usd": forecast["maximum_usd"],
                    "predicted_range_low_usd": signed["range_low_usd"],
                    "predicted_point_usd": signed["point_estimate_usd"],
                    "predicted_range_high_usd": signed["range_high_usd"],
                    "predicted_display": signed["display"],
                    "direction_correct": direction_correct,
                    "magnitude_range_hit": magnitude_hit,
                    "signed_range_hit": direction_correct and magnitude_hit,
                }
            )
        history.append(row)

    direction_hits = sum(row["direction_correct"] for row in magnitude_events)
    magnitude_hits = sum(row["magnitude_range_hit"] for row in magnitude_events)
    signed_hits = sum(row["signed_range_hit"] for row in magnitude_events)
    magnitude_backtest = {
        "configuration": asdict(range_config),
        "nominal_coverage_pct": round(
            100 * (range_config.high_quantile - range_config.low_quantile), 1
        ),
        "events": magnitude_events,
        "direction_accuracy_pct": round(100 * direction_hits / len(magnitude_events), 2),
        "magnitude_coverage_pct": round(100 * magnitude_hits / len(magnitude_events), 2),
        "signed_coverage_pct": round(100 * signed_hits / len(magnitude_events), 2),
        "median_absolute_error_usd": round(
            float(
                np.mean(
                    [
                        abs(abs(row["actual_move_usd"]) - row["predicted_median_abs_usd"])
                        for row in magnitude_events
                    ]
                )
            ),
            2,
        ),
        "pre_recent_selection_top_five": [
            {
                "configuration": asdict(item["config"]),
                "events": item["events"],
                "coverage_pct": round(item["coverage_pct"], 2),
                "mean_normalized_interval_score": round(
                    item["mean_normalized_interval_score"], 4
                ),
                "median_width_usd": round(item["median_width_usd"], 2),
            }
            for item in range_ranking[:5]
        ],
    }

    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(fit_move_range_artifact(rows, range_config), MODEL_PATH)

    terminal = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"Could not initialize MT5: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        info = mt5.symbol_info("XAUUSD")
        if account is None or info is None or not mt5.symbol_select("XAUUSD", True):
            raise RuntimeError("The connected MT5 account does not expose XAUUSD.")
        leverage = int(account.leverage)
        ticks_by_release = {
            event["release_utc"]: _event_ticks("XAUUSD", _utc(event["release_utc"]))
            for event in recent_events
        }
        configs = _candidate_configs()
        selection_events = [
            row
            for row in recent_events
            if date.fromisoformat(row["release_utc"][:10]) < HOLDOUT_START
        ]
        holdout_events = [
            row
            for row in recent_events
            if date.fromisoformat(row["release_utc"][:10]) >= HOLDOUT_START
        ]
        ranked_selection = _optimize(
            configs, selection_events, ticks_by_release, info, leverage
        )
        selected_config = ranked_selection[0]["config"]
        selected_trades, full_metrics = _run_config(
            selected_config,
            recent_events,
            ticks_by_release,
            info,
            leverage,
            include_path=True,
        )
        _, selection_metrics = _run_config(
            selected_config,
            selection_events,
            ticks_by_release,
            info,
            leverage,
            include_path=True,
        )
        _, holdout_metrics = _run_config(
            selected_config,
            holdout_events,
            ticks_by_release,
            info,
            leverage,
            starting_balance=STARTING_BALANCE,
            include_path=True,
        )
        ranked_all = _optimize(
            configs, recent_events, ticks_by_release, info, leverage
        )
    finally:
        mt5.shutdown()

    report = {
        "methodology": {
            "magnitude": (
                "A 25th-to-90th percentile likely-move interval selected before the displayed period. "
                "The selection must achieve at least 60% prior walk-forward coverage; each forecast uses only earlier releases."
            ),
            "execution": (
                "Fixed 0.08 lot and $100 start. Selection uses the first five releases; "
                "the final three are untouched. Real MT5 bid/ask ticks and crossing gaps determine fills."
            ),
        },
        "sample_audit": sample_audit,
        "broker": {
            "server": account.server,
            "symbol": "XAUUSD",
            "leverage": leverage,
            "contract_size": float(info.trade_contract_size),
            "tick_size": float(info.trade_tick_size),
            "tick_value_per_lot_usd": float(info.trade_tick_value),
        },
        "magnitude_backtest": magnitude_backtest,
        "search": {
            "candidate_configurations": len(configs),
            "selection_start": RECENT_START.isoformat(),
            "holdout_start": HOLDOUT_START.isoformat(),
            "selection_top_20": _serialize_ranked(ranked_selection),
        },
        "selected_execution": {
            "configuration": asdict(selected_config),
            "configuration_label": _config_label(selected_config),
            "selection_window": selection_metrics,
            "untouched_holdout": holdout_metrics,
            "full_three_months": full_metrics,
            "trades": selected_trades,
        },
        "best_observed_all_eight": {
            "configuration": asdict(ranked_all[0]["config"]),
            "configuration_label": _config_label(ranked_all[0]["config"]),
            "metrics": ranked_all[0]["metrics"],
        },
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected_trades[0]))
        writer.writeheader()
        writer.writerows(selected_trades)
    OUTPUT_MD.write_text(_markdown(report), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
