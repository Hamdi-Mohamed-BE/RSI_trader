from __future__ import annotations

import itertools
import json
import math
from dataclasses import asdict, dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import research_common as common


ROOT_OUT = common.ROOT / "IVB FRVP"


@dataclass(frozen=True)
class Signal:
    session: str
    opening_minutes: int
    bins: int
    reload_zone: str
    minimum_breakout_relative_volume: float
    acceptance_closes: int
    retest_bars: int


@dataclass(frozen=True)
class Outcome:
    stop_mode: str
    reward_risk: float
    management: str
    no_progress_minutes: int


def ts(day, hour: int, minute: int, zone: str) -> pd.Timestamp:
    return pd.Timestamp(year=day.year, month=day.month, day=day.day, hour=hour, minute=minute, tz=zone).tz_convert("UTC")


def session_times(day, session: str, opening_minutes: int) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    if session == "new_york_0930":
        start = ts(day, 9, 30, "America/New_York")
        end = start + pd.Timedelta(minutes=opening_minutes)
        finish = ts(day, 16, 0, "America/New_York")
    elif session == "comex_0820":
        start = ts(day, 8, 20, "America/New_York")
        end = start + pd.Timedelta(minutes=opening_minutes)
        finish = ts(day, 13, 30, "America/New_York")
    elif session == "london_0800":
        start = ts(day, 8, 0, "Europe/London")
        end = start + pd.Timedelta(minutes=opening_minutes)
        finish = ts(day, 16, 0, "Europe/London")
    else:
        raise ValueError(session)
    return start, end, finish


def volume_profile(opening: pd.DataFrame, bins: int) -> tuple[float, float, float]:
    low = float(opening.low.min())
    high = float(opening.high.max())
    if not high > low:
        return low, high, low
    edges = np.linspace(low, high, bins + 1)
    profile = np.zeros(bins, dtype=float)
    width = edges[1] - edges[0]
    for row in opening.itertuples():
        first = max(0, min(bins - 1, int((float(row.low) - low) / width)))
        last = max(0, min(bins - 1, int((float(row.high) - low) / width)))
        touched = last - first + 1
        profile[first:last + 1] += max(float(row.tick_volume), 1.0) / touched
    poc_index = int(np.argmax(profile))
    selected = {poc_index}
    total = float(profile.sum())
    accumulated = float(profile[poc_index])
    left, right = poc_index - 1, poc_index + 1
    while accumulated < total * 0.70 and (left >= 0 or right < bins):
        left_value = profile[left] if left >= 0 else -1.0
        right_value = profile[right] if right < bins else -1.0
        if right_value > left_value:
            selected.add(right); accumulated += float(right_value); right += 1
        else:
            selected.add(left); accumulated += float(left_value); left -= 1
    val_index, vah_index = min(selected), max(selected)
    poc = (edges[poc_index] + edges[poc_index + 1]) * 0.5
    val = edges[val_index]
    vah = edges[vah_index + 1]
    return float(poc), float(vah), float(val)


def pack(window: pd.DataFrame) -> dict:
    return {
        "time": window.index.to_numpy(),
        "open": window.open.to_numpy(dtype=float),
        "high": window.high.to_numpy(dtype=float),
        "low": window.low.to_numpy(dtype=float),
        "close": window.close.to_numpy(dtype=float),
        "spread": window.spread_price.to_numpy(dtype=float),
        "volume": window.tick_volume.to_numpy(dtype=float),
        "relative_volume": window.relative_volume.to_numpy(dtype=float),
    }


def build_contexts(raw: pd.DataFrame, manifest: dict, sessions: tuple[str, ...]) -> dict[tuple, list[dict]]:
    frame = common.add_spread_price(raw, float(manifest["point"]))
    baseline = frame.tick_volume.rolling(20, min_periods=10).mean().shift(1)
    frame["relative_volume"] = frame.tick_volume / baseline.replace(0, np.nan)
    frame["relative_volume"] = frame.relative_volume.fillna(0.0).clip(0, 20)
    frame = frame.set_index("time").sort_index()
    first = frame.index[0].tz_convert("America/New_York").date()
    last = frame.index[-1].tz_convert("America/New_York").date()
    result: dict[tuple, list[dict]] = {(session, duration, bins): [] for session in sessions for duration in (30, 60) for bins in (24, 48)}
    for stamp in pd.date_range(first, last, freq="D"):
        day = stamp.date()
        if day.weekday() >= 5:
            continue
        for session in sessions:
            for duration in (30, 60):
                start, end, finish = session_times(day, session, duration)
                opening = common.interval(frame, start, end)
                trading = common.interval(frame, end, finish)
                if len(opening) < duration - 3 or len(trading) < 120:
                    continue
                or_high, or_low = float(opening.high.max()), float(opening.low.min())
                or_range = or_high - or_low
                if or_range <= 0:
                    continue
                for bins in (24, 48):
                    poc, vah, val = volume_profile(opening, bins)
                    result[(session, duration, bins)].append({
                        "date": day, "or_high": or_high, "or_low": or_low, "or_range": or_range,
                        "poc": poc, "vah": vah, "val": val, "path": pack(trading),
                    })
    return result


def find_event(context: dict, signal: Signal):
    path = context["path"]
    direction = 0
    consecutive = 0
    accepted_at = -1
    prior_direction = 0
    for i in range(len(path["close"])):
        close = path["close"][i]
        candidate = 1 if close > context["or_high"] else -1 if close < context["or_low"] else 0
        if direction == 0:
            if candidate == 0 or path["relative_volume"][i] < signal.minimum_breakout_relative_volume:
                consecutive = 0; prior_direction = 0; continue
            if candidate == prior_direction:
                consecutive += 1
            else:
                prior_direction = candidate; consecutive = 1
            if consecutive >= signal.acceptance_closes:
                direction = candidate; accepted_at = i
            continue
        if i <= accepted_at:
            continue
        if i - accepted_at > signal.retest_bars:
            return None
        if direction > 0 and close < context["or_low"]:
            return None
        if direction < 0 and close > context["or_high"]:
            return None
        level = context[signal.reload_zone]
        tolerance = context["or_range"] * 0.02
        if direction > 0:
            valid = path["low"][i] <= level + tolerance and close > level and close > path["open"][i]
            if valid:
                return context, i, direction, close + path["spread"][i]
        else:
            valid = path["high"][i] + path["spread"][i] >= level - tolerance and close + path["spread"][i] < level and close < path["open"][i]
            if valid:
                return context, i, direction, close
    return None


def events_for_signal(context_map: dict, signal: Signal) -> list[tuple]:
    events = []
    for context in context_map[(signal.session, signal.opening_minutes, signal.bins)]:
        event = find_event(context, signal)
        if event is not None:
            events.append(event)
    return events


def stop_distance(context: dict, path: dict, index: int, direction: int, entry: float, mode: str) -> float:
    buffer = context["or_range"] * 0.05
    if mode == "opposite_value_area":
        stop = context["val"] - buffer if direction > 0 else context["vah"] + buffer
    elif mode == "signal_candle":
        stop = path["low"][index] - buffer if direction > 0 else path["high"][index] + path["spread"][index] + buffer
    else:
        stop = context["or_low"] - buffer if direction > 0 else context["or_high"] + buffer
    return direction * (entry - stop)


def simulate(path: dict, index: int, direction: int, entry: float, distance: float, outcome: Outcome):
    stop = entry - direction * distance
    target = entry + direction * outcome.reward_risk * distance
    pending = stop
    best_r = 0.0
    last, last_i = entry, index
    for i in range(index, len(path["open"])):
        if direction > 0:
            high, low, close = path["high"][i], path["low"][i], path["close"][i]
            if low <= stop and high >= target: return (stop-entry)/distance, "stop_same_bar", stop, i
            if low <= stop: return (stop-entry)/distance, "stop", stop, i
            if high >= target: return outcome.reward_risk, "target", target, i
            best_r = max(best_r, (high-entry)/distance)
            if outcome.management == "be_1r" and best_r >= 1.0: pending = max(pending, entry)
            elif outcome.management == "trail_1_5r" and best_r >= 1.5: pending = max(pending, close-0.75*distance, entry)
            last = close
        else:
            spread = path["spread"][i]
            high, low, close = path["high"][i]+spread, path["low"][i]+spread, path["close"][i]+spread
            if high >= stop and low <= target: return (entry-stop)/distance, "stop_same_bar", stop, i
            if high >= stop: return (entry-stop)/distance, "stop", stop, i
            if low <= target: return outcome.reward_risk, "target", target, i
            best_r = max(best_r, (entry-low)/distance)
            if outcome.management == "be_1r" and best_r >= 1.0: pending = min(pending, entry)
            elif outcome.management == "trail_1_5r" and best_r >= 1.5: pending = min(pending, close+0.75*distance, entry)
            last = close
        stop = pending; last_i = i
        if outcome.no_progress_minutes > 0 and i-index+1 >= outcome.no_progress_minutes and best_r < 0.5:
            return direction*(last-entry)/distance, "no_progress", last, i
    return direction*(last-entry)/distance, "time", last, last_i


def make_trades(events: list[tuple], outcome: Outcome) -> pd.DataFrame:
    rows = []
    for context, index, direction, entry in events:
        path = context["path"]
        distance = stop_distance(context, path, index, direction, entry, outcome.stop_mode)
        if distance <= max(path["spread"][index] * 1.5, context["or_range"] * 0.05) or distance > context["or_range"] * 2.5:
            continue
        r, reason, exit_price, exit_i = simulate(path, index, direction, entry, distance, outcome)
        if not math.isfinite(r):
            continue
        rows.append({
            "date": context["date"], "direction": "LONG" if direction > 0 else "SHORT",
            "entry_time": pd.Timestamp(path["time"][index]), "entry": entry,
            "exit_time": pd.Timestamp(path["time"][exit_i]), "exit": exit_price,
            "exit_reason": reason, "result_r": r, "opening_range": context["or_range"],
            "poc": context["poc"], "vah": context["vah"], "val": context["val"],
        })
    return pd.DataFrame(rows)


def ivb_score(train: dict, validation: dict) -> float:
    if train["trades"] < 30 or validation["trades"] < 10:
        return -999.0
    if train["profit_factor"] <= 1.0 or validation["profit_factor"] <= 1.0:
        return -500.0 + min(train["mean_r"], validation["mean_r"])
    return min(train["mean_r"], validation["mean_r"]) - 0.0015 * max(train["max_closed_balance_dd_pct"], validation["max_closed_balance_dd_pct"])


def research_market(label: str, sessions: tuple[str, ...]) -> dict:
    print(f"Loading IVB {label}...", flush=True)
    raw, manifest = common.load_history(label, 2022)
    context_map = build_contexts(raw, manifest, sessions)
    signals = [
        Signal(session, duration, bins, zone, volume, acceptance, retest)
        for session, duration, bins, zone, volume, acceptance, retest in itertools.product(
            sessions, (30, 60), (24, 48), ("vah", "poc", "val"), (0.0, 1.10), (1, 2), (3, 6)
        )
    ]
    baseline = Outcome("opposite_value_area", 2.0, "none", 60)
    cached: dict[Signal, list[tuple]] = {}
    stage = []
    for signal in signals:
        events = events_for_signal(context_map, signal)
        cached[signal] = events
        trades = make_trades(events, baseline)
        if len(trades) == 0:
            continue
        periods = common.period_metrics(trades)
        stage.append((ivb_score(periods["train_2022_2023"], periods["validation_2024"]), signal))
    selected_signals = [signal for _, signal in sorted(stage, key=lambda item: item[0], reverse=True)[:10]]
    outcomes = [
        Outcome(stop, rr, management, timeout)
        for stop, rr, management, timeout in itertools.product(
            ("opposite_value_area", "signal_candle", "opposite_opening_range"),
            (1.5, 2.0, 3.0), ("none", "be_1r", "trail_1_5r"), (0, 60, 90)
        )
    ]
    ranking = []
    best = None
    best_score = -math.inf
    print(f"  {label}: sessions={sessions}, stage-one={len(signals)}, stage-two={len(selected_signals)*len(outcomes)}", flush=True)
    for number, signal in enumerate(selected_signals, 1):
        for outcome in outcomes:
            trades = make_trades(cached[signal], outcome)
            if len(trades) == 0:
                continue
            periods = common.period_metrics(trades)
            score = ivb_score(periods["train_2022_2023"], periods["validation_2024"])
            ranking.append({**asdict(signal), **asdict(outcome), "score": score,
                            "train_pf": periods["train_2022_2023"]["profit_factor"], "train_return": periods["train_2022_2023"]["return_pct"], "train_trades": periods["train_2022_2023"]["trades"],
                            "validation_pf": periods["validation_2024"]["profit_factor"], "validation_return": periods["validation_2024"]["return_pct"], "validation_trades": periods["validation_2024"]["trades"]})
            if score > best_score:
                best_score = score; best = (signal, outcome, trades, periods)
        print(f"    management search {number}/{len(selected_signals)}", flush=True)
    if best is None:
        raise RuntimeError(f"No viable IVB configuration for {label}")
    signal, outcome, trades, periods = best
    out = ROOT_OUT / label
    out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(ranking).sort_values("score", ascending=False).to_csv(out / "configuration-ranking.csv", index=False)
    trades.to_csv(out / "selected-trades.csv", index=False)
    yearly = {str(year): common.metrics(group.result_r) for year, group in trades.groupby(pd.to_datetime(trades.date).dt.year)}
    result = {"market": label, "data": manifest, "selected_signal": asdict(signal), "selected_outcome": asdict(outcome), "period_metrics": periods, "yearly": yearly,
              "volume_note": "FRVP uses MEXAtlantic M1 quote-tick activity, not CME real volume.",
              "selection_note": "Selected on 2022-2023 training and 2024 validation; 2025-2026 untouched."}
    (out / "results.json").write_text(json.dumps(common.json_safe(result), indent=2), encoding="utf-8")
    equity = common.INITIAL_BALANCE * (1.0 + common.RISK_FRACTION * trades.result_r).cumprod()
    fig, ax = plt.subplots(figsize=(12, 6)); ax.step(pd.to_datetime(trades.date), equity, where="post")
    ax.axhline(common.INITIAL_BALANCE, color="#777", linewidth=0.8); ax.grid(alpha=0.25)
    ax.set(title=f"IVB FRVP {label} — selected configuration", ylabel="Closed balance (USD)", xlabel="Trade date")
    fig.tight_layout(); fig.savefig(out / "equity.png", dpi=170); plt.close(fig)
    print(json.dumps(common.json_safe(result), indent=2), flush=True)
    return result


def main() -> int:
    ROOT_OUT.mkdir(parents=True, exist_ok=True)
    results = {
        "US100": research_market("US100", ("new_york_0930",)),
        "US30": research_market("US30", ("new_york_0930",)),
        "XAU": research_market("XAU", ("new_york_0930", "comex_0820", "london_0800")),
    }
    (ROOT_OUT / "all-results.json").write_text(json.dumps(common.json_safe(results), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
