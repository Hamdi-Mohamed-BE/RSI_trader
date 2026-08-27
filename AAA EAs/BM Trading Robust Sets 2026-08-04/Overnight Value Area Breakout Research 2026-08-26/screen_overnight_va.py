from __future__ import annotations

import itertools
import json
import math
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "Screen Results"
OUTPUT.mkdir(parents=True, exist_ok=True)
NY = ZoneInfo("America/New_York")
START = datetime(2020, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 26, 23, 59, tzinfo=timezone.utc)
TRAIN_END = pd.Timestamp("2024-01-01", tz=NY)
VALID_END = pd.Timestamp("2025-07-01", tz=NY)
RISK_FRACTION = 0.01
ROUND_TRIP_COST_POINTS = 2.0


@dataclass(frozen=True)
class Config:
    value_area_pct: int = 70
    profile_bins: int = 48
    signal_window_bars: int = 1
    entry_mode: str = "direct"
    stop_mode: str = "signal"
    reward_risk: float = 1.5
    breakout_buffer_atr: float = 0.0
    minimum_relative_volume: float = 0.0
    require_directional_candle: bool = False
    retest_bars: int = 4
    retest_tolerance_atr: float = 0.08
    stop_buffer_atr: float = 0.0
    atr_stop_multiple: float = 1.0

    @property
    def slug(self) -> str:
        return (
            f"va{self.value_area_pct}-b{self.profile_bins}-w{self.signal_window_bars}"
            f"-{self.entry_mode}-{self.stop_mode}-rr{self.reward_risk:g}"
            f"-buf{self.breakout_buffer_atr:g}-rv{self.minimum_relative_volume:g}"
            f"-dir{int(self.require_directional_candle)}"
        ).replace(".", "")


def fetch_rates() -> tuple[pd.DataFrame, dict]:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        if not mt5.symbol_select("USTEC", True):
            raise RuntimeError(f"USTEC selection failed: {mt5.last_error()}")
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        symbol = mt5.symbol_info("USTEC")
        rates = mt5.copy_rates_range("USTEC", mt5.TIMEFRAME_M1, START, END)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No live-terminal USTEC M1 history: {mt5.last_error()}")
        metadata = {
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "terminal": terminal.path if terminal else None,
            "terminal_build": terminal.build if terminal else None,
            "account": account.login if account else None,
            "server": account.server if account else None,
            "symbol": "USTEC",
            "description": symbol.description if symbol else None,
            "point": symbol.point if symbol else None,
            "tick_size": symbol.trade_tick_size if symbol else None,
            "source_rows": int(len(rates)),
            "source_start_utc": datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc).isoformat(),
            "source_end_utc": datetime.fromtimestamp(int(rates[-1]["time"]), timezone.utc).isoformat(),
            "screen_round_trip_cost_points": ROUND_TRIP_COST_POINTS,
            "volume_warning": "Exness USTEC supplies quote tick activity, not centralized Nasdaq futures exchange volume.",
        }
    finally:
        mt5.shutdown()
    frame = pd.DataFrame(rates)
    frame["timestamp"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_convert(NY)
    frame = frame.set_index("timestamp").sort_index()
    frame = frame.loc[~frame.index.duplicated(keep="last")]
    return frame[["open", "high", "low", "close", "tick_volume", "spread"]].astype(float), metadata


def profile_levels(profile: pd.DataFrame, bins: int, value_area_pct: int) -> tuple[float, float, float] | None:
    low = float(profile.low.min())
    high = float(profile.high.max())
    if not math.isfinite(low) or not math.isfinite(high) or high <= low:
        return None
    width = (high - low) / bins
    activity = np.zeros(bins, dtype=float)
    typical = (profile.high.to_numpy() + profile.low.to_numpy() + profile.close.to_numpy()) / 3.0
    indexes = np.floor((typical - low) / width).astype(int)
    indexes = np.clip(indexes, 0, bins - 1)
    np.add.at(activity, indexes, profile.tick_volume.to_numpy(dtype=float))
    total = float(activity.sum())
    if total <= 0:
        return None
    poc = int(np.argmax(activity))
    value_low = value_high = poc
    included = float(activity[poc])
    target = total * value_area_pct / 100.0
    while included < target and (value_low > 0 or value_high < bins - 1):
        below = activity[value_low - 1] if value_low > 0 else -1.0
        above = activity[value_high + 1] if value_high < bins - 1 else -1.0
        if above >= below and value_high < bins - 1:
            value_high += 1
            included += float(activity[value_high])
        elif value_low > 0:
            value_low -= 1
            included += float(activity[value_low])
        else:
            break
    return (
        low + (poc + 0.5) * width,
        low + (value_high + 1) * width,
        low + value_low * width,
    )


def aggregate_15m(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.resample("15min", label="left", closed="left", origin="start_day").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
    )
    return result.dropna()


def build_sessions(frame: pd.DataFrame) -> list[dict]:
    dates = sorted(set(frame.index.date))
    true_ranges: deque[float] = deque(maxlen=20)
    slot_volumes: dict[int, deque[float]] = defaultdict(lambda: deque(maxlen=20))
    previous_close: float | None = None
    sessions: list[dict] = []
    profile_keys = list(itertools.product((65, 70, 75), (36, 48, 64)))

    for session_date in dates:
        session_day = pd.Timestamp(session_date, tz=NY)
        if session_day.weekday() >= 5:
            continue
        cash_open = session_day + pd.Timedelta(hours=9, minutes=30)
        cash_close = session_day + pd.Timedelta(hours=16)
        profile_start = session_day - pd.Timedelta(days=1) + pd.Timedelta(hours=16, minutes=30)
        # DatetimeIndex label slicing uses binary search; boolean scans here make
        # the multi-year fresh MT5 pull unnecessarily quadratic by session.
        overnight = frame.loc[profile_start : cash_open - pd.Timedelta(microseconds=1)]
        rth = frame.loc[cash_open : cash_close - pd.Timedelta(microseconds=1)]
        if len(overnight) < 600 or len(rth) < 330:
            continue
        if rth.index[0] > cash_open + pd.Timedelta(minutes=2):
            continue

        day_high = float(rth.high.max())
        day_low = float(rth.low.min())
        day_close = float(rth.iloc[-1].close)
        true_range = day_high - day_low
        if previous_close is not None:
            true_range = max(true_range, abs(day_high - previous_close), abs(day_low - previous_close))

        bars = aggregate_15m(rth)
        if len(true_ranges) >= 14 and previous_close is not None and len(bars) >= 24:
            atr = float(np.median(true_ranges))
            profiles = {
                f"{value}-{bins}": profile_levels(overnight, bins, value)
                for value, bins in profile_keys
            }
            if all(levels is not None for levels in profiles.values()):
                relative_volume: list[float] = []
                for timestamp, bar in bars.iterrows():
                    slot = timestamp.hour * 60 + timestamp.minute
                    history = slot_volumes[slot]
                    baseline = float(np.median(history)) if len(history) >= 10 else math.nan
                    relative_volume.append(float(bar.tick_volume) / baseline if baseline > 0 else math.nan)
                bars = bars.copy()
                bars["relative_volume"] = relative_volume
                sessions.append(
                    {
                        "date": session_day,
                        "cash_open": cash_open,
                        "cash_close": cash_close,
                        "atr": atr,
                        "profiles": profiles,
                        "bars": bars,
                        "minute_times": rth.index.view("int64"),
                        "minute_open": rth.open.to_numpy(dtype=float),
                        "minute_high": rth.high.to_numpy(dtype=float),
                        "minute_low": rth.low.to_numpy(dtype=float),
                        "minute_close": rth.close.to_numpy(dtype=float),
                    }
                )

        for timestamp, bar in bars.iterrows():
            slot_volumes[timestamp.hour * 60 + timestamp.minute].append(float(bar.tick_volume))
        true_ranges.append(true_range)
        previous_close = day_close
    return sessions


def next_minute_open(day: dict, after: pd.Timestamp) -> tuple[int, pd.Timestamp, float] | None:
    index = int(np.searchsorted(day["minute_times"], int(after.timestamp()), side="left"))
    if index >= len(day["minute_times"]):
        return None
    timestamp = pd.Timestamp(int(day["minute_times"][index]), unit="s", tz="UTC").tz_convert(NY)
    return index, timestamp, float(day["minute_open"][index])


def find_setup(day: dict, config: Config) -> dict | None:
    levels = day["profiles"].get(f"{config.value_area_pct}-{config.profile_bins}")
    if levels is None:
        return None
    poc, vah, val = levels
    atr = day["atr"]
    bars = day["bars"].loc[
        (day["bars"].index >= day["cash_open"])
        & (day["bars"].index < day["cash_open"] + pd.Timedelta(minutes=15 * config.signal_window_bars))
    ]
    if bars.empty:
        return None

    for signal_time, signal in bars.iterrows():
        if config.minimum_relative_volume > 0:
            if not math.isfinite(float(signal.relative_volume)) or float(signal.relative_volume) < config.minimum_relative_volume:
                continue
        buffer = config.breakout_buffer_atr * atr
        direction = 0
        if float(signal.close) > vah + buffer:
            direction = 1
        elif float(signal.close) < val - buffer:
            direction = -1
        if direction == 0:
            if config.signal_window_bars == 1:
                return None
            continue
        if config.require_directional_candle:
            if direction > 0 and float(signal.close) <= float(signal.open):
                continue
            if direction < 0 and float(signal.close) >= float(signal.open):
                continue

        reference = signal
        entry_after = signal_time + pd.Timedelta(minutes=15)
        if config.entry_mode == "retest":
            later = day["bars"].loc[
                (day["bars"].index >= entry_after)
                & (day["bars"].index < entry_after + pd.Timedelta(minutes=15 * config.retest_bars))
            ]
            accepted = None
            tolerance = config.retest_tolerance_atr * atr
            for retest_time, retest in later.iterrows():
                if direction > 0:
                    valid = float(retest.low) <= vah + tolerance and float(retest.close) > vah and float(retest.close) > float(retest.open)
                else:
                    valid = float(retest.high) >= val - tolerance and float(retest.close) < val and float(retest.close) < float(retest.open)
                if valid:
                    accepted = (retest_time, retest)
                    break
            if accepted is None:
                return None
            reference = accepted[1]
            entry_after = accepted[0] + pd.Timedelta(minutes=15)

        entry_item = next_minute_open(day, entry_after)
        if entry_item is None:
            return None
        entry_index, entry_time, entry = entry_item
        stop_buffer = config.stop_buffer_atr * atr
        if config.stop_mode == "signal":
            stop = float(reference.low) - stop_buffer if direction > 0 else float(reference.high) + stop_buffer
        elif config.stop_mode == "poc":
            stop = poc - stop_buffer if direction > 0 else poc + stop_buffer
        elif config.stop_mode == "opposite_va":
            stop = val - stop_buffer if direction > 0 else vah + stop_buffer
        else:
            stop = entry - config.atr_stop_multiple * atr if direction > 0 else entry + config.atr_stop_multiple * atr
        risk = direction * (entry - stop)
        if risk <= ROUND_TRIP_COST_POINTS * 1.5 or risk > atr * 2.5:
            return None
        target = entry + direction * config.reward_risk * risk
        return {
            "date": day["date"],
            "direction": direction,
            "signal_time": signal_time,
            "entry_time": entry_time,
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_points": risk,
            "poc": poc,
            "vah": vah,
            "val": val,
            "relative_volume": float(signal.relative_volume) if math.isfinite(float(signal.relative_volume)) else None,
            "entry_index": entry_index,
            "minute_times": day["minute_times"],
            "minute_high": day["minute_high"],
            "minute_low": day["minute_low"],
            "minute_close": day["minute_close"],
        }
    return None


def resolve_setup(setup: dict) -> dict:
    direction = setup["direction"]
    entry = setup["entry"]
    stop = setup["stop"]
    target = setup["target"]
    risk = setup["risk_points"]
    start = setup["entry_index"]
    highs = setup["minute_high"][start:]
    lows = setup["minute_low"][start:]
    raw_points = direction * (float(setup["minute_close"][-1]) - entry)
    exit_offset = len(highs) - 1
    exit_reason = "session_close"
    stop_hits = np.flatnonzero(lows <= stop) if direction > 0 else np.flatnonzero(highs >= stop)
    target_hits = np.flatnonzero(highs >= target) if direction > 0 else np.flatnonzero(lows <= target)
    first_stop = int(stop_hits[0]) if len(stop_hits) else math.inf
    first_target = int(target_hits[0]) if len(target_hits) else math.inf
    if first_stop < math.inf and first_stop <= first_target:
        exit_offset = first_stop
        raw_points = direction * (stop - entry)
        exit_reason = "stop"
    elif first_target < math.inf:
        exit_offset = first_target
        raw_points = direction * (target - entry)
        exit_reason = "target"
    exit_ns = int(setup["minute_times"][start + int(exit_offset)])
    exit_time = pd.Timestamp(exit_ns, unit="s", tz="UTC").tz_convert(NY)
    net_r = (raw_points - ROUND_TRIP_COST_POINTS) / risk
    private_keys = {"entry_index", "minute_times", "minute_high", "minute_low", "minute_close"}
    return {key: value for key, value in setup.items() if key not in private_keys} | {
        "exit_time": exit_time,
        "exit_reason": exit_reason,
        "net_r": net_r,
    }


def stats(trades: list[dict]) -> dict:
    balance = 10_000.0
    peak = balance
    max_dd = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    curve = [{"date": None, "balance": balance}]
    for trade in sorted(trades, key=lambda item: item["exit_time"]):
        pnl = balance * RISK_FRACTION * trade["net_r"]
        balance += pnl
        gross_profit += max(pnl, 0.0)
        gross_loss += max(-pnl, 0.0)
        wins += int(pnl > 0)
        peak = max(peak, balance)
        max_dd = max(max_dd, (peak - balance) / peak * 100.0)
        curve.append({"date": trade["exit_time"].isoformat(), "balance": balance})
    return {
        "initial_balance": 10_000.0,
        "final_balance": balance,
        "return_pct": (balance / 10_000.0 - 1.0) * 100.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0),
        "win_rate_pct": wins / len(trades) * 100.0 if trades else 0.0,
        "max_drawdown_pct": max_dd,
        "trades": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "curve": curve,
    }


def evaluate(sessions: list[dict], config: Config) -> dict:
    trades = [resolve_setup(setup) for day in sessions if (setup := find_setup(day, config)) is not None]
    training = [trade for trade in trades if trade["date"] < TRAIN_END]
    validation = [trade for trade in trades if TRAIN_END <= trade["date"] < VALID_END]
    locked = [trade for trade in trades if trade["date"] >= VALID_END]
    return {
        "config": asdict(config),
        "slug": config.slug,
        "training": stats(training),
        "validation": stats(validation),
        "locked": stats(locked),
        "trades": trades,
    }


def is_eligible(result: dict) -> bool:
    train = result["training"]
    valid = result["validation"]
    if train["trades"] < 80 or valid["trades"] < 30:
        return False
    if train["return_pct"] <= 0 or valid["return_pct"] <= 0:
        return False
    if train["profit_factor"] <= 1.02 or valid["profit_factor"] <= 1.02:
        return False
    if max(train["max_drawdown_pct"], valid["max_drawdown_pct"]) > 20.0:
        return False
    return True


def score(result: dict) -> float:
    train = result["training"]
    valid = result["validation"]
    minimum_pf = min(train["profit_factor"], valid["profit_factor"])
    minimum_return = min(train["return_pct"] / 4.0, valid["return_pct"] / 1.5)
    return 8.0 * minimum_pf + 0.15 * minimum_return - 0.30 * max(train["max_drawdown_pct"], valid["max_drawdown_pct"])


def public(result: dict) -> dict:
    value = {key: item for key, item in result.items() if key != "trades"}
    for split in ("training", "validation", "locked"):
        value[split] = {key: item for key, item in value[split].items() if key != "curve"}
    return value


def save_chart(selected: dict) -> None:
    plt.style.use("dark_background")
    figure, axes = plt.subplots(3, 1, figsize=(13, 10), sharex=False)
    figure.patch.set_facecolor("#071311")
    colors = {"training": "#61dafb", "validation": "#ffd166", "locked": "#5fffd1"}
    for axis, split in zip(axes, ("training", "validation", "locked")):
        axis.set_facecolor("#0b1c19")
        curve = selected[split]["curve"]
        dates = [pd.Timestamp(point["date"]) for point in curve[1:]]
        balances = [point["balance"] for point in curve[1:]]
        if dates:
            axis.plot(dates, balances, color=colors[split], linewidth=1.8)
        axis.axhline(10_000, color="#9ab5ad", linestyle="--", linewidth=0.8)
        axis.grid(alpha=0.25)
        axis.set_ylabel("Balance USD")
        axis.set_title(
            f"{split.title()}: {selected[split]['return_pct']:+.2f}% | "
            f"PF {selected[split]['profit_factor']:.2f} | DD {selected[split]['max_drawdown_pct']:.2f}% | "
            f"{selected[split]['trades']} trades",
            loc="left",
        )
    figure.suptitle("US100 Overnight Value Area Breakout — independent 1% risk curves", fontsize=15, weight="bold")
    figure.tight_layout()
    figure.savefig(OUTPUT / "selected-screen-equity.png", dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> None:
    frame, metadata = fetch_rates()
    (OUTPUT / "data-source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    sessions = build_sessions(frame)
    if len(sessions) < 500:
        raise RuntimeError(f"Only {len(sessions)} complete US100 sessions were constructed.")
    print(f"constructed {len(sessions)} complete sessions")

    stage_one_configs = [
        Config(
            signal_window_bars=window,
            entry_mode=entry,
            stop_mode=stop,
            reward_risk=rr,
            breakout_buffer_atr=buffer,
        )
        for window, entry, stop, rr, buffer in itertools.product(
            (1, 4),
            ("direct", "retest"),
            ("signal", "poc", "opposite_va", "atr"),
            (0.5, 1.0, 1.5, 2.0, 3.0),
            (0.0,),
        )
    ]
    stage_one = []
    for index, config in enumerate(stage_one_configs, start=1):
        result = evaluate(sessions, config)
        result["score"] = score(result)
        result["eligible"] = is_eligible(result)
        stage_one.append(result)
        if index % 40 == 0:
            print(f"stage one {index}/{len(stage_one_configs)}")
    ranked_one = sorted(stage_one, key=lambda item: item["score"], reverse=True)
    eligible_one = [item for item in ranked_one if item["eligible"]]
    seed = eligible_one[0] if eligible_one else ranked_one[0]
    seed_config = seed["config"]

    ordered_rewards = (0.5, 1.0, 1.5, 2.0, 3.0)
    seed_reward_index = ordered_rewards.index(float(seed_config["reward_risk"]))
    reward_neighbors = ordered_rewards[max(0, seed_reward_index - 1) : min(len(ordered_rewards), seed_reward_index + 2)]
    stage_two_configs = [
        Config(
            value_area_pct=value,
            profile_bins=bins,
            signal_window_bars=int(seed_config["signal_window_bars"]),
            entry_mode=str(seed_config["entry_mode"]),
            stop_mode=str(seed_config["stop_mode"]),
            reward_risk=rr,
            breakout_buffer_atr=buffer,
            minimum_relative_volume=relative_volume,
            require_directional_candle=directional,
        )
        for value, bins, rr, buffer, relative_volume, directional in itertools.product(
            (65, 70, 75),
            (36, 48, 64),
            reward_neighbors,
            (float(seed_config["breakout_buffer_atr"]),),
            (0.0, 1.0),
            (False, True),
        )
    ]
    stage_two = []
    for index, config in enumerate(stage_two_configs, start=1):
        result = evaluate(sessions, config)
        result["score"] = score(result)
        result["eligible"] = is_eligible(result)
        stage_two.append(result)
        if index % 200 == 0:
            print(f"stage two {index}/{len(stage_two_configs)}")
    ranked = sorted(stage_one + stage_two, key=lambda item: item["score"], reverse=True)
    eligible = [item for item in ranked if item["eligible"]]
    selected = eligible[0] if eligible else ranked[0]

    rows = []
    for result in ranked:
        rows.append(
            {
                "slug": result["slug"],
                "score": result["score"],
                "eligible": result["eligible"],
                **result["config"],
                **{f"train_{key}": value for key, value in public(result)["training"].items()},
                **{f"validation_{key}": value for key, value in public(result)["validation"].items()},
                **{f"locked_{key}": value for key, value in public(result)["locked"].items()},
            }
        )
    pd.DataFrame(rows).to_csv(OUTPUT / "all-screen-results.csv", index=False)
    (OUTPUT / "top-100-screen-results.json").write_text(
        json.dumps([public(item) | {"score": item["score"], "eligible": item["eligible"]} for item in ranked[:100]], indent=2),
        encoding="utf-8",
    )
    selected_public = public(selected) | {
        "score": selected["score"],
        "eligible_candidates": len(eligible),
        "selection_rule": "Training and validation only; locked segment was never used for selection.",
    }
    (OUTPUT / "selected-screen-result.json").write_text(json.dumps(selected_public, indent=2), encoding="utf-8")
    pd.DataFrame(
        [
            {
                key: value.isoformat() if isinstance(value, pd.Timestamp) else value
                for key, value in trade.items()
            }
            for trade in selected["trades"]
        ]
    ).to_csv(OUTPUT / "selected-screen-trades.csv", index=False)
    save_chart(selected)
    print(json.dumps(selected_public, indent=2))


if __name__ == "__main__":
    main()
