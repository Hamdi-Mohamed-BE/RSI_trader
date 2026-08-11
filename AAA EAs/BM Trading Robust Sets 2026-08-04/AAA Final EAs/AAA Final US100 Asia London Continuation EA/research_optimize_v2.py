from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import research_optimize as base


REPORTS = base.RESEARCH / "reports-v2-aligned-breakout"


@dataclass(frozen=True)
class Session:
    session_date: date
    asia_open: float
    asia_close: float
    asia_high: float
    asia_low: float
    london_open: float
    london_close: float
    ny_open: float
    or_high: float
    or_low: float
    or_range: float
    total_move: float
    asia_move: float
    london_move: float
    minutes: np.ndarray
    bid_open: np.ndarray
    bid_high: np.ndarray
    bid_low: np.ndarray
    bid_close: np.ndarray
    spread_points: np.ndarray
    timestamps: np.ndarray


@dataclass(frozen=True)
class Signal:
    proximity_threshold: float
    minimum_trend: float
    trend_definition: str
    proximity_relation: str
    direction_mode: str
    maximum_opening_range: float


@dataclass(frozen=True)
class Outcome:
    entry_mode: str
    entry_cutoff_minute: int
    stop_range_multiple: float
    minimum_stop_points: float
    reward_risk: float
    trailing_mode: str
    exit_minute: int


def build_sessions(raw: pd.DataFrame, fallback_spread: float) -> tuple[list[Session], dict]:
    frame = raw.copy().set_index("time").sort_index()
    first = frame.index[0].tz_convert(base.NY).date()
    last = frame.index[-1].tz_convert(base.NY).date()
    sessions: list[Session] = []
    skipped: dict[str, int] = {}

    def reject(reason: str) -> None:
        skipped[reason] = skipped.get(reason, 0) + 1

    for stamp in pd.date_range(first + timedelta(days=1), last, freq="D"):
        day = stamp.date()
        if day.weekday() >= 5:
            continue
        asia = base.index_slice(frame, base.ny_timestamp(day - timedelta(days=1), 18), base.ny_timestamp(day, 3))
        london = base.index_slice(frame, base.ny_timestamp(day, 3), base.ny_timestamp(day, 9, 30))
        opening_range = base.index_slice(frame, base.ny_timestamp(day, 9, 30), base.ny_timestamp(day, 9, 45))
        path = base.index_slice(frame, base.ny_timestamp(day, 9, 45), base.ny_timestamp(day, 16))
        if len(asia) < 180:
            reject("insufficient_asia_bars")
            continue
        if len(london) < 180:
            reject("insufficient_london_bars")
            continue
        if len(opening_range) < 12:
            reject("incomplete_new_york_opening_range")
            continue
        if len(path) < 60:
            reject("insufficient_trade_path")
            continue
        local = path.index.tz_convert(base.NY)
        spreads = path["spread"].to_numpy(dtype=float)
        spreads = np.where(spreads > 0, spreads, fallback_spread)
        asia_open = float(asia.iloc[0]["open"])
        asia_close = float(asia.iloc[-1]["close"])
        london_open = float(london.iloc[0]["open"])
        london_close = float(london.iloc[-1]["close"])
        ny_open = float(opening_range.iloc[0]["open"])
        or_high = float(opening_range["high"].max())
        or_low = float(opening_range["low"].min())
        sessions.append(
            Session(
                session_date=day,
                asia_open=asia_open,
                asia_close=asia_close,
                asia_high=float(asia["high"].max()),
                asia_low=float(asia["low"].min()),
                london_open=london_open,
                london_close=london_close,
                ny_open=ny_open,
                or_high=or_high,
                or_low=or_low,
                or_range=max(or_high - or_low, base.POINT),
                total_move=ny_open - asia_open,
                asia_move=asia_close - asia_open,
                london_move=london_close - london_open,
                minutes=(local.hour * 60 + local.minute).to_numpy(dtype=np.int16),
                bid_open=path["open"].to_numpy(dtype=float),
                bid_high=path["high"].to_numpy(dtype=float),
                bid_low=path["low"].to_numpy(dtype=float),
                bid_close=path["close"].to_numpy(dtype=float),
                spread_points=spreads,
                timestamps=path.index.to_numpy(),
            )
        )
    return sessions, {"valid_sessions": len(sessions), "skipped": skipped}


def signal_direction_and_strength(session: Session, definition: str) -> tuple[int, float]:
    if definition == "total_move":
        if math.isclose(session.total_move, 0.0, abs_tol=1e-12):
            return 0, 0.0
        return (1 if session.total_move > 0 else -1), abs(session.total_move)
    asia_direction = 1 if session.asia_move > 0 else -1 if session.asia_move < 0 else 0
    london_direction = 1 if session.london_move > 0 else -1 if session.london_move < 0 else 0
    if asia_direction == 0 or asia_direction != london_direction:
        return 0, 0.0
    return asia_direction, min(abs(session.asia_move), abs(session.london_move))


def signal_arrays(sessions: list[Session], param: Signal) -> tuple[np.ndarray, np.ndarray]:
    directions = np.zeros(len(sessions), dtype=np.int8)
    include = np.zeros(len(sessions), dtype=bool)
    for i, session in enumerate(sessions):
        direction, strength = signal_direction_and_strength(session, param.trend_definition)
        if direction == 0 or strength < param.minimum_trend or session.or_range > param.maximum_opening_range:
            continue
        if param.direction_mode == "long" and direction < 0:
            continue
        if param.direction_mode == "short" and direction > 0:
            continue
        if direction > 0:
            delta = session.or_high - session.asia_high
        else:
            delta = session.asia_low - session.or_low
        if param.proximity_relation == "absolute":
            proximity_ok = abs(delta) <= param.proximity_threshold
        else:
            # The first New York range must actually break the matching Asia extreme,
            # but must not exceed it by more than the configured distance.
            proximity_ok = 0.0 <= delta <= param.proximity_threshold
        if proximity_ok:
            directions[i] = direction
            include[i] = True
    return include, directions


def outcomes() -> list[Outcome]:
    entries = (("market_0945", 9 * 60 + 45), ("opening_range_breakout", 10 * 60 + 30), ("opening_range_breakout", 11 * 60 + 30))
    return [
        Outcome(entry, cutoff, stop_mult, minimum_stop, rr, trailing, exit_minute)
        for entry, cutoff in entries
        for stop_mult in (1.0, 1.25)
        for minimum_stop in (20.0, 40.0)
        for rr in (1.5, 2.0, 3.0, 4.0)
        for trailing in ("none", "be_1r", "m15_1_5r")
        for exit_minute in (14 * 60, 16 * 60)
    ]


def signals() -> list[Signal]:
    return [
        Signal(threshold, trend, definition, relation, direction, maximum_range)
        for threshold in (20.0, 40.0, 100.0, 200.0)
        for trend in (0.0, 50.0, 100.0)
        for definition in ("total_move", "asia_and_london_aligned")
        for relation in ("absolute", "breakout_band")
        for direction in ("both", "long", "short")
        for maximum_range in (100.0, 200.0, 400.0)
    ]


def trail_start(mode: str) -> float:
    return {"none": math.inf, "be_1r": 1.0, "m15_1_5r": 1.5}[mode]


def simulate(session: Session, direction: int, param: Outcome, detail: bool = False):
    stop_distance = max(session.or_range * param.stop_range_multiple, param.minimum_stop_points)
    entry_index = 0
    if param.entry_mode == "market_0945":
        opening_spread = session.spread_points[0] * base.POINT
        entry = float(session.bid_open[0] + opening_spread) if direction > 0 else float(session.bid_open[0])
    else:
        stop_entry = session.or_high if direction > 0 else session.or_low
        entry = math.nan
        for i, minute in enumerate(session.minutes):
            if int(minute) >= param.entry_cutoff_minute:
                break
            spread = session.spread_points[i] * base.POINT
            if direction > 0 and session.bid_high[i] + spread >= stop_entry:
                entry = max(stop_entry, float(session.bid_open[i] + spread))
                entry_index = i
                break
            if direction < 0 and session.bid_low[i] <= stop_entry:
                entry = min(stop_entry, float(session.bid_open[i]))
                entry_index = i
                break
        if not math.isfinite(entry):
            return None if detail else math.nan

    initial_stop = entry - stop_distance if direction > 0 else entry + stop_distance
    stop = initial_stop
    target = entry + param.reward_risk * stop_distance if direction > 0 else entry - param.reward_risk * stop_distance
    activated = False
    bucket_high = -math.inf
    bucket_low = math.inf
    exit_price = entry
    exit_reason = "time"
    exit_time = session.timestamps[entry_index]

    for i in range(entry_index, len(session.minutes)):
        if int(session.minutes[i]) >= param.exit_minute:
            break
        spread = session.spread_points[i] * base.POINT
        if direction > 0:
            bar_open = float(session.bid_open[i])
            bar_high = float(session.bid_high[i])
            bar_low = float(session.bid_low[i])
            bar_close = float(session.bid_close[i])
        else:
            bar_open = float(session.bid_open[i] + spread)
            bar_high = float(session.bid_high[i] + spread)
            bar_low = float(session.bid_low[i] + spread)
            bar_close = float(session.bid_close[i] + spread)
        bucket_high = max(bucket_high, bar_high)
        bucket_low = min(bucket_low, bar_low)
        stop_hit = bar_low <= stop if direction > 0 else bar_high >= stop
        target_hit = bar_high >= target if direction > 0 else bar_low <= target
        if stop_hit:
            exit_price = min(stop, bar_open) if direction > 0 and bar_open < stop else stop
            if direction < 0:
                exit_price = max(stop, bar_open) if bar_open > stop else stop
            exit_reason = "stop"
            exit_time = session.timestamps[i]
            break
        if target_hit:
            exit_price = target
            exit_reason = "target"
            exit_time = session.timestamps[i]
            break
        favorable = (bar_high - entry) / stop_distance if direction > 0 else (entry - bar_low) / stop_distance
        if favorable >= trail_start(param.trailing_mode):
            activated = True
        if activated and param.trailing_mode == "be_1r":
            stop = max(stop, entry) if direction > 0 else min(stop, entry)
        if int(session.minutes[i]) % 15 == 14:
            if activated and param.trailing_mode == "m15_1_5r":
                candidate = bucket_low if direction > 0 else bucket_high
                if direction > 0 and candidate < bar_close:
                    stop = max(stop, candidate)
                elif direction < 0 and candidate > bar_close:
                    stop = min(stop, candidate)
            bucket_high = -math.inf
            bucket_low = math.inf
        exit_price = bar_close
        exit_time = session.timestamps[i]

    result_r = (exit_price - entry) * direction / stop_distance
    if not detail:
        return float(result_r)
    return {
        "date": session.session_date.isoformat(),
        "side": "LONG" if direction > 0 else "SHORT",
        "entry": entry,
        "initial_stop": initial_stop,
        "target": target,
        "exit": exit_price,
        "exit_reason": exit_reason,
        "exit_time_utc": pd.Timestamp(exit_time).isoformat(),
        "result_r": float(result_r),
        "asia_open": session.asia_open,
        "asia_close": session.asia_close,
        "london_open": session.london_open,
        "london_close": session.london_close,
        "ny_open": session.ny_open,
        "or_high": session.or_high,
        "or_low": session.or_low,
        "or_range": session.or_range,
        "total_move": session.total_move,
        "asia_move": session.asia_move,
        "london_move": session.london_move,
    }


def nan_vector_metrics(values: np.ndarray) -> dict[str, np.ndarray]:
    finite = np.isfinite(values)
    count = finite.sum(axis=0)
    total = np.nansum(values, axis=0)
    mean = np.divide(total, count, out=np.zeros(values.shape[1]), where=count > 0)
    centered = np.where(finite, values - mean, 0.0)
    variance = np.divide((centered * centered).sum(axis=0), count - 1, out=np.zeros(values.shape[1]), where=count > 1)
    std = np.sqrt(variance)
    positive = np.nansum(np.where(values > 0, values, 0.0), axis=0)
    negative = -np.nansum(np.where(values < 0, values, 0.0), axis=0)
    pf = np.divide(positive, negative, out=np.full(values.shape[1], np.inf), where=negative > 0)
    lcb = mean - 1.2816 * np.divide(std, np.sqrt(count), out=np.zeros_like(std), where=count > 0)
    win_rate = np.divide((values > 0).sum(axis=0), count, out=np.zeros(values.shape[1]), where=count > 0) * 100.0
    return {"count": count, "mean": mean, "std": std, "pf": pf, "lcb": lcb, "win_rate": win_rate}


def choose(sessions: list[Session]) -> tuple[Signal, Outcome, pd.DataFrame, np.ndarray, np.ndarray]:
    outcome_list = outcomes()
    long_matrix = np.empty((len(sessions), len(outcome_list)), dtype=np.float32)
    short_matrix = np.empty_like(long_matrix)
    print(f"V2 precompute: {len(sessions):,} sessions x {len(outcome_list):,} outcomes x 2 directions", flush=True)
    for row, session in enumerate(sessions):
        for col, param in enumerate(outcome_list):
            long_matrix[row, col] = simulate(session, 1, param)
            short_matrix[row, col] = simulate(session, -1, param)
        if (row + 1) % 250 == 0:
            print(f"  V2 simulated {row + 1:,}/{len(sessions):,}", flush=True)

    np.savez_compressed(REPORTS / "outcome-cache.npz", long=long_matrix, short=short_matrix)
    dates = np.asarray([np.datetime64(s.session_date) for s in sessions])
    train_dates = dates < np.datetime64("2024-01-01")
    validation_dates = (dates >= np.datetime64("2024-01-01")) & (dates < np.datetime64("2025-01-01"))
    candidates: list[dict] = []
    for signal in signals():
        include, direction = signal_arrays(sessions, signal)
        mixed = np.where(direction[:, None] > 0, long_matrix, short_matrix)
        train = nan_vector_metrics(mixed[include & train_dates])
        validation = nan_vector_metrics(mixed[include & validation_dates])
        qualified = (
            (train["count"] >= 60)
            & (validation["count"] >= 15)
            & (train["pf"] >= 1.05)
            & (validation["pf"] >= 1.05)
            & (train["mean"] > 0)
            & (validation["mean"] > 0)
        )
        score = np.minimum(train["lcb"], validation["lcb"])
        for col in np.flatnonzero(qualified):
            candidates.append(
                {
                    **asdict(signal),
                    **asdict(outcome_list[col]),
                    "outcome_index": int(col),
                    "robust_lcb_score": float(score[col]),
                    "train_trades": int(train["count"][col]),
                    "train_pf": float(train["pf"][col]),
                    "train_mean_r": float(train["mean"][col]),
                    "validation_trades": int(validation["count"][col]),
                    "validation_pf": float(validation["pf"][col]),
                    "validation_mean_r": float(validation["mean"][col]),
                }
            )
    if not candidates:
        raise RuntimeError("No V2 configuration passed train/validation criteria")
    ranked = pd.DataFrame(candidates).sort_values(["robust_lcb_score", "validation_pf"], ascending=False)
    audited: list[dict] = []
    for _, row in ranked.head(750).iterrows():
        signal = Signal(
            float(row.proximity_threshold), float(row.minimum_trend), str(row.trend_definition),
            str(row.proximity_relation), str(row.direction_mode), float(row.maximum_opening_range)
        )
        include, direction = signal_arrays(sessions, signal)
        col = int(row.outcome_index)
        values = np.where(direction > 0, long_matrix[:, col], short_matrix[:, col])
        positive_years = 0
        tested_years = 0
        yearly = {}
        for year in range(2020, 2025):
            mask = include & (dates >= np.datetime64(f"{year}-01-01")) & (dates < np.datetime64(f"{year+1}-01-01")) & np.isfinite(values)
            metrics = base.scalar_metrics(values[mask])
            yearly[str(year)] = metrics["return_pct"]
            if metrics["trades"] >= 8:
                tested_years += 1
                positive_years += int(metrics["return_pct"] > 0)
        pre = include & (dates < np.datetime64("2025-01-01")) & np.isfinite(values)
        pre_metrics = base.scalar_metrics(values[pre])
        stability = float(row.robust_lcb_score) + 0.01 * positive_years - 0.002 * pre_metrics["max_closed_balance_dd_pct"]
        audited.append(
            {
                **row.to_dict(),
                "positive_preholdout_years": positive_years,
                "tested_preholdout_years": tested_years,
                "preholdout_return_pct": pre_metrics["return_pct"],
                "preholdout_pf": pre_metrics["profit_factor"],
                "preholdout_dd_pct": pre_metrics["max_closed_balance_dd_pct"],
                "stability_score": stability,
                "yearly_returns_json": json.dumps(yearly, sort_keys=True),
            }
        )
    table = pd.DataFrame(audited)
    stable = table[
        (table.tested_preholdout_years >= 5)
        & (table.positive_preholdout_years >= 4)
        & (table.preholdout_pf >= 1.10)
        & (table.preholdout_dd_pct <= 15.0)
    ]
    if stable.empty:
        stable = table
    stable = stable.sort_values(["stability_score", "robust_lcb_score"], ascending=False)
    win = stable.iloc[0]
    signal = Signal(
        float(win.proximity_threshold), float(win.minimum_trend), str(win.trend_definition),
        str(win.proximity_relation), str(win.direction_mode), float(win.maximum_opening_range)
    )
    outcome = Outcome(
        str(win.entry_mode), int(win.entry_cutoff_minute), float(win.stop_range_multiple),
        float(win.minimum_stop_points), float(win.reward_risk), str(win.trailing_mode), int(win.exit_minute)
    )
    return signal, outcome, stable, long_matrix, short_matrix


def make_trades(sessions: list[Session], signal: Signal, outcome: Outcome) -> pd.DataFrame:
    include, directions = signal_arrays(sessions, signal)
    rows = []
    for session, use, direction in zip(sessions, include, directions):
        if not use:
            continue
        detail = simulate(session, int(direction), outcome, detail=True)
        if detail is not None:
            rows.append(detail)
    return pd.DataFrame(rows)


def write_results(manifest: dict, quality: dict, signal: Signal, outcome: Outcome, stable: pd.DataFrame, trades: pd.DataFrame) -> dict:
    REPORTS.mkdir(parents=True, exist_ok=True)
    dates = pd.to_datetime(trades.date)
    masks = {
        "training_2019_2023": dates < pd.Timestamp("2024-01-01"),
        "validation_2024": (dates >= pd.Timestamp("2024-01-01")) & (dates < pd.Timestamp("2025-01-01")),
        "holdout_2025_2026": dates >= pd.Timestamp("2025-01-01"),
        "full": np.ones(len(trades), dtype=bool),
    }
    metrics = {name: base.scalar_metrics(trades.loc[mask, "result_r"]) for name, mask in masks.items()}
    stop_distance = (trades.entry - trades.initial_stop).abs().to_numpy()
    stress = {}
    for points in (0.5, 1.0, 2.0):
        stressed = trades.result_r.to_numpy() - 2 * points / stop_distance
        stress[f"{points:g}_points_each_side"] = base.scalar_metrics(stressed)
    results = {
        "selected_signal": asdict(signal),
        "selected_outcome": asdict(outcome),
        "quality": quality,
        "metrics": metrics,
        "slippage_stress_full": stress,
        "tick_size": manifest["specification"]["trade_tick_size"],
        "original_2000_ticks_index_points": 2000 * manifest["specification"]["trade_tick_size"],
    }
    (REPORTS / "results.json").write_text(json.dumps(base.json_safe(results), indent=2), encoding="utf-8")
    stable.head(250).to_csv(REPORTS / "top-configurations.csv", index=False)
    trades.to_csv(REPORTS / "selected-trades.csv", index=False)

    equity = base.INITIAL_BALANCE * np.cumprod(1 + base.RISK_FRACTION * trades.result_r.to_numpy())
    plt.figure(figsize=(12, 5.5))
    plt.plot(dates, equity, color="#1677ff", linewidth=1.8)
    plt.axvline(pd.Timestamp("2024-01-01"), color="#888888", linestyle="--", linewidth=1)
    plt.axvline(pd.Timestamp("2025-01-01"), color="#d65f5f", linestyle="--", linewidth=1)
    plt.title("US100 Asia–London continuation V2")
    plt.xlabel("Session date")
    plt.ylabel("Balance (USD), 1% risk")
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(REPORTS / "equity-curve.png", dpi=170)
    plt.close()

    full = metrics["full"]
    holdout = metrics["holdout_2025_2026"]
    report = [
        "# US100 Asia–London Continuation V2",
        "",
        "This version tests two wording-faithful alternatives: both Asia and London must align, and post-09:45 opening-range breakout entry.",
        "",
        "## Selected signal",
        "",
        *[f"- {k}: `{v}`" for k, v in asdict(signal).items()],
        "",
        "## Selected execution",
        "",
        *[f"- {k}: `{v}`" for k, v in asdict(outcome).items()],
        "",
        "## Full period",
        "",
        f"- Trades: {full['trades']}",
        f"- Return: {full['return_pct']:.2f}%",
        f"- PF: {full['profit_factor']:.2f}",
        f"- Win rate: {full['win_rate_pct']:.2f}%",
        f"- Closed-balance DD: {full['max_closed_balance_dd_pct']:.2f}%",
        "",
        "## Untouched 2025–2026 holdout",
        "",
        f"- Trades: {holdout['trades']}",
        f"- Return: {holdout['return_pct']:.2f}%",
        f"- PF: {holdout['profit_factor']:.2f}",
        f"- Win rate: {holdout['win_rate_pct']:.2f}%",
        f"- Closed-balance DD: {holdout['max_closed_balance_dd_pct']:.2f}%",
        "",
        "No EA should be deployed if the untouched holdout is not viable.",
        "",
    ]
    (REPORTS / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    return results


def main() -> int:
    REPORTS.mkdir(parents=True, exist_ok=True)
    raw, manifest = base.download_history()
    sessions, quality = build_sessions(raw, manifest["median_positive_spread_points"])
    print(f"V2 sessions={len(sessions):,}; skipped={quality['skipped']}", flush=True)
    signal, outcome, stable, _, _ = choose(sessions)
    print(f"V2 selected signal={signal}", flush=True)
    print(f"V2 selected outcome={outcome}", flush=True)
    trades = make_trades(sessions, signal, outcome)
    results = write_results(manifest, quality, signal, outcome, stable, trades)
    print(json.dumps(base.json_safe(results["metrics"]), indent=2), flush=True)
    print(f"V2 reports: {REPORTS}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
