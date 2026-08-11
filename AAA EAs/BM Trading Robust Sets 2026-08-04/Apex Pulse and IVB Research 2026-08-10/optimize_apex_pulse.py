from __future__ import annotations

import itertools
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import research_common as common


OUT = common.ROOT / "Apex Pulse EURUSD"
PIP = 0.0001


@dataclass(frozen=True)
class Signal:
    session: str
    buffer_pips: float
    minimum_asia_range_pips: float
    maximum_asia_range_pips: float


@dataclass(frozen=True)
class Outcome:
    stop_mode: str
    stop_value: float
    reward_risk: float
    management: str


def local_timestamp(day, hour: int, minute: int, zone: str) -> pd.Timestamp:
    return pd.Timestamp(year=day.year, month=day.month, day=day.day, hour=hour, minute=minute, tz=zone).tz_convert("UTC")


def packed(window: pd.DataFrame) -> dict:
    return {
        "time": window.index.to_numpy(),
        "open": window.open.to_numpy(dtype=float),
        "high": window.high.to_numpy(dtype=float),
        "low": window.low.to_numpy(dtype=float),
        "close": window.close.to_numpy(dtype=float),
        "spread": window.spread_price.to_numpy(dtype=float),
    }


def contexts(frame: pd.DataFrame, point: float) -> list[dict]:
    frame = common.add_spread_price(frame, point).set_index("time").sort_index()
    first = frame.index[0].tz_convert("Europe/London").date()
    last = frame.index[-1].tz_convert("Europe/London").date()
    result: list[dict] = []
    for stamp in pd.date_range(first, last, freq="D"):
        day = stamp.date()
        if day.weekday() >= 5:
            continue
        asia = common.interval(frame, local_timestamp(day, 0, 0, "Europe/London"), local_timestamp(day, 7, 0, "Europe/London"))
        if len(asia) < 300:
            continue
        raw_windows = {
            "london_0700": common.interval(frame, local_timestamp(day, 7, 0, "Europe/London"), local_timestamp(day, 12, 0, "Europe/London")),
            "london_0800": common.interval(frame, local_timestamp(day, 8, 0, "Europe/London"), local_timestamp(day, 12, 0, "Europe/London")),
            "new_york_0800": common.interval(frame, local_timestamp(day, 8, 0, "America/New_York"), local_timestamp(day, 12, 0, "America/New_York")),
        }
        if any(len(window) < 120 for window in raw_windows.values()):
            continue
        windows = {name: packed(window) for name, window in raw_windows.items()}
        result.append({
            "date": day,
            "asia_high": float(asia.high.max()),
            "asia_low": float(asia.low.min()),
            "asia_range_pips": float((asia.high.max() - asia.low.min()) / PIP),
            "windows": windows,
        })
    return result


def find_entry(day: dict, signal: Signal):
    if not signal.minimum_asia_range_pips <= day["asia_range_pips"] <= signal.maximum_asia_range_pips:
        return None
    path = day["windows"][signal.session]
    long_level = day["asia_high"] + signal.buffer_pips * PIP
    short_level = day["asia_low"] - signal.buffer_pips * PIP
    long_hits = np.flatnonzero(path["high"] + path["spread"] >= long_level)
    short_hits = np.flatnonzero(path["low"] <= short_level)
    long_i = int(long_hits[0]) if len(long_hits) else 10**9
    short_i = int(short_hits[0]) if len(short_hits) else 10**9
    if long_i == short_i:
        return None
    if long_i < short_i:
        return path, long_i, 1, max(long_level, path["open"][long_i] + path["spread"][long_i])
    if short_i < 10**9:
        return path, short_i, -1, min(short_level, path["open"][short_i])
    return None


def simulate_np(path: dict, entry_index: int, direction: int, entry: float, distance: float, rr: float, management: str):
    stop = entry - distance if direction > 0 else entry + distance
    target = entry + direction * rr * distance
    best_r = 0.0
    pending = stop
    last = entry
    last_i = entry_index
    for i in range(entry_index, len(path["open"])):
        if direction > 0:
            high, low, close = path["high"][i], path["low"][i], path["close"][i]
            if low <= stop and high >= target:
                return (stop-entry)/distance, "stop_same_bar", stop, i
            if low <= stop:
                return (stop-entry)/distance, "stop", stop, i
            if high >= target:
                return rr, "target", target, i
            best_r = max(best_r, (high-entry)/distance)
            if management == "be_1r" and best_r >= 1.0:
                pending = max(pending, entry)
            elif management == "trail_1_5r" and best_r >= 1.5:
                pending = max(pending, close-0.75*distance, entry)
            last = close
        else:
            spread = path["spread"][i]
            high, low, close = path["high"][i]+spread, path["low"][i]+spread, path["close"][i]+spread
            if high >= stop and low <= target:
                return (entry-stop)/distance, "stop_same_bar", stop, i
            if high >= stop:
                return (entry-stop)/distance, "stop", stop, i
            if low <= target:
                return rr, "target", target, i
            best_r = max(best_r, (entry-low)/distance)
            if management == "be_1r" and best_r >= 1.0:
                pending = min(pending, entry)
            elif management == "trail_1_5r" and best_r >= 1.5:
                pending = min(pending, close+0.75*distance, entry)
            last = close
        stop = pending
        last_i = i
    return direction*(last-entry)/distance, "time", last, last_i


def entry_events(days: list[dict], signal: Signal) -> list[tuple]:
    events = []
    for day in days:
        found = find_entry(day, signal)
        if found is not None:
            events.append((day, *found))
    return events


def trade_rows(events: list[tuple], outcome: Outcome) -> pd.DataFrame:
    rows = []
    for day, path, index, direction, entry in events:
        if outcome.stop_mode == "fixed_pips":
            distance = outcome.stop_value * PIP
        else:
            distance = day["asia_range_pips"] * PIP * outcome.stop_value
        r, reason, exit_price, exit_index = simulate_np(
            path, index, direction, entry, distance, outcome.reward_risk, outcome.management
        )
        if not math.isfinite(r):
            continue
        rows.append({
            "date": day["date"], "direction": "LONG" if direction > 0 else "SHORT",
            "entry_time": pd.Timestamp(path["time"][index]), "entry": entry,
            "exit_time": pd.Timestamp(path["time"][exit_index]),
            "exit": exit_price, "exit_reason": reason, "result_r": r,
            "asia_range_pips": day["asia_range_pips"],
        })
    return pd.DataFrame(rows)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    raw, manifest = common.load_history("EURUSD", 2022)
    days = contexts(raw, float(manifest["point"]))
    signals = [
        Signal(session, buffer, minimum, maximum)
        for session, buffer, minimum, maximum in itertools.product(
            ("london_0700", "london_0800", "new_york_0800"),
            (0.0, 2.0, 5.0),
            (0.0, 15.0),
            (40.0, 60.0, 100.0),
        )
        if minimum < maximum
    ]
    outcomes = [
        Outcome(mode, value, rr, management)
        for mode, value in (("fixed_pips", 30.0), ("fixed_pips", 40.0), ("fixed_pips", 50.0), ("asia_fraction", 0.5), ("asia_fraction", 1.0))
        for rr in (1.5, 2.0, 3.0)
        for management in ("none", "be_1r", "trail_1_5r")
    ]
    # Stage one selects the session/range definition with the public 50-pip, 3R,
    # no-trailing baseline. Management is optimized only for the twelve strongest
    # pre-holdout signals, which controls runtime and reduces combinatorial fitting.
    baseline = Outcome("fixed_pips", 50.0, 3.0, "none")
    signal_stage = []
    cached_events: dict[Signal, list[tuple]] = {}
    for signal in signals:
        events = entry_events(days, signal)
        cached_events[signal] = events
        trades = trade_rows(events, baseline)
        if len(trades) == 0:
            continue
        periods = common.period_metrics(trades)
        score = common.selection_score(periods["train_2022_2023"], periods["validation_2024"])
        signal_stage.append((score, signal))
    selected_signals = [signal for _, signal in sorted(signal_stage, key=lambda item: item[0], reverse=True)[:12]]

    ranking = []
    best = None
    best_score = -math.inf
    print(f"Apex contexts={len(days):,}; stage-one signals={len(signals):,}; stage-two configurations={len(selected_signals) * len(outcomes):,}", flush=True)
    for s_index, signal in enumerate(selected_signals):
        events = cached_events[signal]
        for outcome in outcomes:
            trades = trade_rows(events, outcome)
            if len(trades) == 0:
                continue
            periods = common.period_metrics(trades)
            score = common.selection_score(periods["train_2022_2023"], periods["validation_2024"])
            row = {**asdict(signal), **asdict(outcome), "score": score,
                   "train_pf": periods["train_2022_2023"]["profit_factor"],
                   "train_return": periods["train_2022_2023"]["return_pct"],
                   "train_trades": periods["train_2022_2023"]["trades"],
                   "validation_pf": periods["validation_2024"]["profit_factor"],
                   "validation_return": periods["validation_2024"]["return_pct"],
                   "validation_trades": periods["validation_2024"]["trades"]}
            ranking.append(row)
            if score > best_score:
                best_score = score
                best = (signal, outcome, trades, periods)
        print(f"  management search {s_index + 1}/{len(selected_signals)}", flush=True)
    if best is None:
        raise RuntimeError("No Apex configuration produced trades")
    signal, outcome, trades, periods = best
    ranking_frame = pd.DataFrame(ranking).sort_values("score", ascending=False)
    ranking_frame.to_csv(OUT / "configuration-ranking.csv", index=False)
    trades.to_csv(OUT / "selected-trades.csv", index=False)
    yearly = {str(year): common.metrics(group.result_r) for year, group in trades.groupby(pd.to_datetime(trades.date).dt.year)}
    result = {
        "data": manifest,
        "contexts": len(days),
        "selected_signal": asdict(signal),
        "selected_outcome": asdict(outcome),
        "period_metrics": periods,
        "yearly": yearly,
        "selection_note": "Selected on 2022-2023 training and 2024 validation; 2025-2026 was untouched.",
    }
    (OUT / "results.json").write_text(json.dumps(common.json_safe(result), indent=2), encoding="utf-8")
    equity = common.INITIAL_BALANCE * (1.0 + common.RISK_FRACTION * trades.result_r).cumprod()
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.step(pd.to_datetime(trades.date), equity, where="post")
    ax.axhline(common.INITIAL_BALANCE, color="#777", linewidth=0.8)
    ax.set(title="Transparent Apex Pulse EURUSD — selected configuration", ylabel="Closed balance (USD)", xlabel="Trade date")
    ax.grid(alpha=0.25)
    fig.tight_layout(); fig.savefig(OUT / "equity.png", dpi=170); plt.close(fig)
    print(json.dumps(common.json_safe(result), indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
