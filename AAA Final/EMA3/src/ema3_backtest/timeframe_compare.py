from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
import re

import MetaTrader5 as mt5
import pandas as pd
from dotenv import load_dotenv

from .optimize import (
    ExitConfig,
    filtered_pivot_signals,
    metrics,
    selection_score,
    simulate,
)


UTC = timezone.utc

TIMEFRAMES: dict[str, tuple[int, timedelta]] = {
    "H1": (mt5.TIMEFRAME_H1, timedelta(hours=1)),
    "H4": (mt5.TIMEFRAME_H4, timedelta(hours=4)),
}

ALIASES: dict[str, tuple[str, ...]] = {
    "XAUUSD": ("XAUUSD", "GOLD"),
    "XAGUSD": ("XAGUSD", "SILVER"),
    "BTCUSD": ("BTCUSD",),
    "ETHUSD": ("ETHUSD",),
    "EURUSD": ("EURUSD",),
    "GBPJPY": ("GBPJPY",),
    "AUDCHF": ("AUDCHF",),
    "US30": ("US30", "DJ30", "WS30"),
    "US100": ("US100", "NAS100", "USTEC", "NDX", "NASDAQ100"),
}


def canonical(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def env_list(name: str, default: str) -> list[str]:
    return [part.strip() for part in os.getenv(name, default).split(",") if part.strip()]


def symbol_score(item: object, requested: str) -> tuple[int, int, int, int, str]:
    aliases = tuple(canonical(alias) for alias in ALIASES.get(requested, (requested,)))
    name = str(getattr(item, "name", ""))
    normalized = canonical(name)
    description = canonical(str(getattr(item, "description", "")))
    exact = any(normalized == alias for alias in aliases)
    prefix_lengths = [len(alias) for alias in aliases if normalized.startswith(alias)]
    prefix = max(prefix_lengths, default=0)
    described = any(alias in description for alias in aliases if len(alias) >= 5)
    if not exact and not prefix and not described:
        return (-10_000, 0, 0, 0, name)
    tradable = int(getattr(item, "trade_mode", 0)) != int(
        mt5.SYMBOL_TRADE_MODE_DISABLED
    )
    visible = bool(getattr(item, "visible", False))
    return (
        1_000 if exact else 800 + prefix if prefix else 500,
        1 if tradable else 0,
        1 if visible else 0,
        -len(name),
        name,
    )


def discover_symbol(requested: str) -> str:
    items = mt5.symbols_get()
    if not items:
        raise RuntimeError(f"MT5 symbol catalogue unavailable: {mt5.last_error()}")
    ranked = sorted(
        ((symbol_score(item, requested), item) for item in items),
        key=lambda row: row[0],
        reverse=True,
    )
    if not ranked or ranked[0][0][0] < 0:
        raise RuntimeError(f"No broker symbol found for {requested}")
    symbol = str(getattr(ranked[0][1], "name"))
    if not mt5.symbol_select(symbol, True):
        raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")
    return symbol


def completed_rates(
    symbol: str,
    timeframe: str,
    requested_start: datetime,
    end: datetime,
    warmup_bars: int = 260,
) -> pd.DataFrame:
    mt5_timeframe, duration = TIMEFRAMES[timeframe]
    padded_start = requested_start - duration * warmup_bars
    rates = mt5.copy_rates_range(symbol, mt5_timeframe, padded_start, end)
    if rates is None or len(rates) == 0:
        raise RuntimeError(
            f"No {timeframe} history for {symbol}: {mt5.last_error()}"
        )
    frame = pd.DataFrame(rates).sort_values("time").reset_index(drop=True)
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    seconds = int(duration.total_seconds())
    current_open_epoch = int(end.timestamp()) // seconds * seconds
    current_open = datetime.fromtimestamp(current_open_epoch, UTC)
    return frame.loc[frame["time"] < current_open].reset_index(drop=True)


def exit_grid() -> list[ExitConfig]:
    fixed = [ExitConfig("fixed", target_r=value) for value in (2.0, 3.0, 4.0)]
    trailing = [
        ExitConfig("trail", trail_start_r=start, trail_distance_r=distance)
        for start, distance in ((1.0, 0.5), (1.0, 1.0), (1.5, 1.0))
    ]
    return fixed + trailing


def signal_variants(timeframe: str) -> list[tuple[str, int]]:
    slope = 24 if timeframe == "H1" else 6
    return [("none", 1), ("ema200_slope", slope)]


def pivot_distances(timeframe: str) -> tuple[int, ...]:
    return (6, 8, 10) if timeframe == "H1" else (4, 5, 6)


def confidence_requirements(timeframe: str, coverage_days: float) -> tuple[int, int]:
    if coverage_days < 120:
        return ((8, 3) if timeframe == "H1" else (4, 2))
    return ((25, 8) if timeframe == "H1" else (10, 4))


def finite_pf(value: object) -> float:
    number = float(value)
    return 10.0 if math.isinf(number) else number


def optimize_one(
    requested: str,
    broker_symbol: str,
    timeframe: str,
    frame: pd.DataFrame,
    requested_start: datetime,
    end: datetime,
    point: float,
    risk_pct: float,
    starting_balance: float,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    _, duration = TIMEFRAMES[timeframe]
    actual_start = max(requested_start, frame.at[0, "time"].to_pydatetime())
    actual_end = min(end, (frame.at[len(frame) - 1, "time"] + duration).to_pydatetime())
    coverage_days = (actual_end - actual_start).total_seconds() / 86_400.0
    if coverage_days < 30:
        raise RuntimeError(f"only {coverage_days:.1f} days of usable history")
    split = actual_start + (actual_end - actual_start) * 0.75
    minimum_train, minimum_validation = confidence_requirements(
        timeframe, coverage_days
    )
    prepared: dict[tuple[int, str, int], list[dict[str, object]]] = {}
    rows: list[dict[str, object]] = []
    candidates: list[tuple[dict[str, object], ExitConfig, list[dict[str, object]]]] = []
    for distance in pivot_distances(timeframe):
        for signal_filter, slope_bars in signal_variants(timeframe):
            key = (distance, signal_filter, slope_bars)
            prepared[key] = filtered_pivot_signals(
                frame, distance, signal_filter, slope_bars
            )
            for exit_config in exit_grid():
                trades = simulate(
                    frame,
                    requested,
                    point,
                    distance,
                    actual_start,
                    split,
                    exit_config,
                    max_same_direction_legs=1,
                    signal_filter=signal_filter,
                    ema_slope_bars=slope_bars,
                    prepared_signals=prepared[key],
                )
                stats = metrics(
                    trades, risk_pct=risk_pct, starting_balance=starting_balance
                )
                row: dict[str, object] = {
                    "instrument": requested,
                    "broker_symbol": broker_symbol,
                    "timeframe": timeframe,
                    "distance": distance,
                    "signal_filter": signal_filter,
                    "ema_slope_bars": slope_bars,
                    "exit": exit_config.name,
                    "sample": "training",
                    **stats,
                }
                row["selection_score"] = selection_score(row)
                rows.append(row)
                if (
                    int(stats["trades"]) >= minimum_train
                    and float(stats["net_r"]) > 0
                    and finite_pf(stats["profit_factor"]) >= 1.10
                    and float(stats["max_drawdown_pct"]) <= 15.0
                ):
                    candidates.append((row, exit_config, prepared[key]))
    if not candidates:
        raise RuntimeError(
            f"no training candidate passed minimum {minimum_train} trades"
        )
    selected_row, selected_exit, selected_signals = max(
        candidates, key=lambda item: float(item[0]["selection_score"])
    )
    distance = int(selected_row["distance"])
    signal_filter = str(selected_row["signal_filter"])
    slope_bars = int(selected_row["ema_slope_bars"])

    def record(sample: str, trades: list[object]) -> dict[str, object]:
        result = metrics(
            trades, risk_pct=risk_pct, starting_balance=starting_balance
        )
        rows.append(
            {
                "instrument": requested,
                "broker_symbol": broker_symbol,
                "timeframe": timeframe,
                "distance": distance,
                "signal_filter": signal_filter,
                "ema_slope_bars": slope_bars,
                "exit": selected_exit.name,
                "sample": sample,
                **result,
                "selection_score": None,
            }
        )
        return result

    # Run one continuous path so the validation period inherits the strategy's
    # true position state. Restarting flat at the split can create extra pivot
    # entries that a continuously running reversal bot would not take.
    full_trades = simulate(
        frame,
        requested,
        point,
        distance,
        actual_start,
        actual_end,
        selected_exit,
        max_same_direction_legs=1,
        signal_filter=signal_filter,
        ema_slope_bars=slope_bars,
        prepared_signals=selected_signals,
    )
    validation_trades = [
        trade
        for trade in full_trades
        if pd.Timestamp(trade.entry_time) >= pd.Timestamp(split)
    ]
    validation = record("validation", validation_trades)
    full = record("full", full_trades)
    robust = (
        int(validation["trades"]) >= minimum_validation
        and float(validation["net_r"]) > 0
        and finite_pf(validation["profit_factor"]) >= 1.15
    )
    confidence = (
        "limited"
        if coverage_days < 120 or int(validation["trades"]) < minimum_validation * 2
        else "standard"
    )
    best = {
        "instrument": requested,
        "broker_symbol": broker_symbol,
        "timeframe": timeframe,
        "history_start_utc": actual_start.isoformat(),
        "history_end_utc": actual_end.isoformat(),
        "coverage_days": coverage_days,
        "training_end_utc": split.isoformat(),
        "distance": distance,
        "signal_filter": signal_filter,
        "ema_slope_bars": slope_bars,
        "exit": selected_exit.name,
        "minimum_validation_trades": minimum_validation,
        "robust": robust,
        "confidence": confidence,
        **{f"train_{key}": value for key, value in selected_row.items() if key in {
            "trades", "wins", "losses", "win_rate_pct", "net_r", "profit_factor",
            "expectancy_r", "max_drawdown_pct", "ending_balance"
        }},
        **{f"validation_{key}": value for key, value in validation.items()},
        **{f"full_{key}": value for key, value in full.items()},
    }
    return best, rows


def pf_text(value: object) -> str:
    number = float(value)
    return "inf" if math.isinf(number) else f"{number:.2f}"


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Compare EMA3 across H1/H4 markets")
    parser.add_argument(
        "--symbols",
        default=os.getenv(
            "COMPARE_SYMBOLS",
            "XAUUSD,US100,US30,BTCUSD,EURUSD,GBPJPY",
        ),
    )
    parser.add_argument(
        "--days", type=int, default=int(os.getenv("COMPARE_HISTORY_DAYS", "365"))
    )
    parser.add_argument(
        "--risk-pct", type=float, default=float(os.getenv("BACKTEST_RISK_PCT", "1"))
    )
    parser.add_argument(
        "--balance", type=float, default=float(os.getenv("STARTING_BALANCE", "1000"))
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports") / "timeframe_comparison",
    )
    args = parser.parse_args()
    requested_symbols = [part.strip().upper() for part in args.symbols.split(",") if part.strip()]
    end = datetime.now(UTC)
    requested_start = end - timedelta(days=args.days)
    best_rows: list[dict[str, object]] = []
    all_rows: list[dict[str, object]] = []
    errors: list[dict[str, str]] = []
    if not mt5.initialize():
        raise SystemExit(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        for requested in requested_symbols:
            try:
                broker_symbol = discover_symbol(requested)
                info = mt5.symbol_info(broker_symbol)
                if info is None:
                    raise RuntimeError("symbol_info unavailable")
                for timeframe in TIMEFRAMES:
                    try:
                        frame = completed_rates(
                            broker_symbol,
                            timeframe,
                            requested_start,
                            end,
                        )
                        best, rows = optimize_one(
                            requested,
                            broker_symbol,
                            timeframe,
                            frame,
                            requested_start,
                            end,
                            float(info.point),
                            args.risk_pct,
                            args.balance,
                        )
                        best_rows.append(best)
                        all_rows.extend(rows)
                        print(
                            f"{requested:7} {timeframe} | {best['validation_trades']:3} validation "
                            f"| WR {best['validation_win_rate_pct']:5.1f}% | "
                            f"PF {pf_text(best['validation_profit_factor']):>5} | "
                            f"{best['validation_net_r']:+6.2f}R | "
                            f"DD {best['validation_max_drawdown_pct']:5.2f}%",
                            flush=True,
                        )
                    except Exception as exc:
                        errors.append(
                            {"instrument": requested, "timeframe": timeframe, "error": str(exc)}
                        )
            except Exception as exc:
                errors.append({"instrument": requested, "timeframe": "all", "error": str(exc)})
    finally:
        mt5.shutdown()

    args.output.mkdir(parents=True, exist_ok=True)
    best_frame = pd.DataFrame(best_rows)
    all_frame = pd.DataFrame(all_rows)
    errors_frame = pd.DataFrame(errors)
    best_frame.to_csv(args.output / "best_by_symbol_timeframe.csv", index=False)
    all_frame.to_csv(args.output / "all_training_results.csv", index=False)
    errors_frame.to_csv(args.output / "errors.csv", index=False)
    if best_frame.empty:
        raise SystemExit("No comparisons completed; see errors.csv")

    ranked = best_frame.loc[
        (best_frame["robust"] == True)  # noqa: E712
        & (best_frame["confidence"] == "standard")
    ].copy()
    if not ranked.empty:
        ranked["rank_score"] = (
            ranked["validation_expectancy_r"]
            * ranked["validation_trades"].clip(lower=1).pow(0.5)
            + ranked["validation_profit_factor"].clip(upper=5) * 0.15
            - ranked["validation_max_drawdown_pct"] * 0.04
        )
        ranked = ranked.sort_values(
            ["rank_score", "validation_trades"], ascending=[False, False]
        )
    lines = [
        "# EMA3 H1 versus H4 Walk-Forward Comparison",
        "",
        f"Requested period: {requested_start.isoformat()} to {end.isoformat()}",
        "The first 75% of each broker-history sample selects the setup; the final 25% is untouched validation.",
        "Every result uses one leg, structural pivot stops, historical spread and percentage risk.",
        "",
        "| Symbol | Broker symbol | TF | Coverage | Selected setup | Validation trades | WR | PF | Net R | DD | Confidence | Robust |",
        "|---|---|---|---:|---|---:|---:|---:|---:|---:|---|---|",
    ]
    for _, row in best_frame.sort_values(["instrument", "timeframe"]).iterrows():
        setup = (
            f"d{int(row['distance'])}, {row['signal_filter']}"
            + (f"/{int(row['ema_slope_bars'])}, " if row["signal_filter"] != "none" else ", ")
            + str(row["exit"])
        )
        lines.append(
            f"| {row['instrument']} | {row['broker_symbol']} | {row['timeframe']} | "
            f"{row['coverage_days']:.0f}d | {setup} | {int(row['validation_trades'])} | "
            f"{row['validation_win_rate_pct']:.1f}% | {pf_text(row['validation_profit_factor'])} | "
            f"{row['validation_net_r']:+.2f} | {row['validation_max_drawdown_pct']:.2f}% | "
            f"{row['confidence']} | {'yes' if row['robust'] else 'no'} |"
        )
    lines.extend(["", "## Standard-confidence robust ranking", ""])
    if ranked.empty:
        lines.append("No result passed the minimum untouched-validation rules.")
    else:
        lines.extend(
            [
                "| Rank | Symbol | TF | Validation trades | WR | PF | Net R | DD |",
                "|---:|---|---|---:|---:|---:|---:|---:|",
            ]
        )
        for rank, (_, row) in enumerate(ranked.iterrows(), start=1):
            lines.append(
                f"| {rank} | {row['instrument']} | {row['timeframe']} | "
                f"{int(row['validation_trades'])} | {row['validation_win_rate_pct']:.1f}% | "
                f"{pf_text(row['validation_profit_factor'])} | {row['validation_net_r']:+.2f} | "
                f"{row['validation_max_drawdown_pct']:.2f}% |"
            )
    provisional = best_frame.loc[
        (best_frame["robust"] == True)  # noqa: E712
        & (best_frame["confidence"] != "standard")
    ].copy()
    if not provisional.empty:
        lines.extend(["", "## Positive but limited-confidence results", ""])
        for _, row in provisional.sort_values(
            "validation_profit_factor", ascending=False
        ).iterrows():
            lines.append(
                f"- {row['instrument']} {row['timeframe']}: "
                f"{int(row['validation_trades'])} validation trades, "
                f"PF {pf_text(row['validation_profit_factor'])}, "
                f"{row['validation_net_r']:+.2f}R, "
                f"DD {row['validation_max_drawdown_pct']:.2f}%."
            )
    if errors:
        lines.extend(["", "## Data limitations", ""])
        for error in errors:
            lines.append(
                f"- {error['instrument']} {error['timeframe']}: {error['error']}"
            )
    lines.extend(
        [
            "",
            "US100 may resolve to the broker's current Nasdaq futures contract. Its result must not be compared",
            "as equal-confidence with instruments that have the full requested year.",
            "",
            "Historical optimization is research, not a guarantee. Forward demo validation is required before",
            "changing the live worker's symbol or timeframe.",
            "",
        ]
    )
    report = "\n".join(lines)
    (args.output / "REPORT.md").write_text(report, encoding="utf-8")
    (args.output / "summary.json").write_text(
        json.dumps(
            {
                "requested_start_utc": requested_start.isoformat(),
                "end_utc": end.isoformat(),
                "risk_pct": args.risk_pct,
                "starting_balance": args.balance,
                "completed_comparisons": len(best_rows),
                "errors": errors,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(report)


if __name__ == "__main__":
    main()
