from __future__ import annotations

import itertools
import json
import math
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
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
    orb_minutes: int = 30
    setup_window_minutes: int = 90
    confirmation: str = "directional"
    trend_filter: str = "none"
    extension_buffer_atr: float = 0.0
    touch_tolerance_atr: float = 0.03
    first_touch_only: bool = True
    stop_mode: str = "rejection"
    stop_buffer_atr: float = 0.01
    atr_stop_multiple: float = 0.25
    target_mode: str = "extreme"
    vwap_slope_bars: int = 3

    @property
    def slug(self) -> str:
        return (
            f"orb{self.orb_minutes}-{self.confirmation}-{self.trend_filter}"
            f"-eb{self.extension_buffer_atr:g}-tt{self.touch_tolerance_atr:g}"
            f"-ft{int(self.first_touch_only)}-{self.stop_mode}-{self.target_mode}"
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
            raise RuntimeError(f"No fresh USTEC M1 history: {mt5.last_error()}")
        metadata = {
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "terminal": terminal.path if terminal else None,
            "terminal_build": terminal.build if terminal else None,
            "account": account.login if account else None,
            "server": account.server if account else None,
            "symbol": "USTEC",
            "description": symbol.description if symbol else None,
            "source_rows": int(len(rates)),
            "source_start_utc": datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc).isoformat(),
            "source_end_utc": datetime.fromtimestamp(int(rates[-1]["time"]), timezone.utc).isoformat(),
            "screen_round_trip_cost_points": ROUND_TRIP_COST_POINTS,
            "volume_warning": "VWAP is weighted by Exness broker tick activity, not centralized futures exchange volume.",
        }
    finally:
        mt5.shutdown()
    frame = pd.DataFrame(rates)
    frame["timestamp"] = pd.to_datetime(frame.time, unit="s", utc=True).dt.tz_convert(NY)
    frame = frame.set_index("timestamp").sort_index()
    frame = frame.loc[~frame.index.duplicated(keep="last")]
    return frame[["open", "high", "low", "close", "tick_volume", "spread"]].astype(float), metadata


def aggregate_5m(frame: pd.DataFrame) -> pd.DataFrame:
    return (
        frame.resample("5min", label="left", closed="left", origin="start_day")
        .agg(
            open=("open", "first"),
            high=("high", "max"),
            low=("low", "min"),
            close=("close", "last"),
            tick_volume=("tick_volume", "sum"),
        )
        .dropna()
    )


def build_sessions(frame: pd.DataFrame) -> list[dict]:
    global_five = aggregate_5m(frame)
    global_five["ema20"] = global_five.close.ewm(span=20, adjust=False).mean()
    global_five["ema50"] = global_five.close.ewm(span=50, adjust=False).mean()
    daily_ranges: deque[float] = deque(maxlen=20)
    sessions = []
    for session_date in sorted(set(frame.index.date)):
        day = pd.Timestamp(session_date, tz=NY)
        if day.weekday() >= 5:
            continue
        cash_open = day + pd.Timedelta(hours=9, minutes=30)
        cash_close = day + pd.Timedelta(hours=16)
        minutes = frame.loc[cash_open : cash_close - pd.Timedelta(microseconds=1)]
        if len(minutes) < 330 or minutes.index[0] > cash_open + pd.Timedelta(minutes=2):
            continue
        bars = global_five.loc[cash_open : cash_close - pd.Timedelta(microseconds=1)].copy()
        if len(bars) < 70:
            continue
        volume = bars.tick_volume.cumsum()
        bars["vwap"] = (((bars.high + bars.low + bars.close) / 3.0) * bars.tick_volume).cumsum() / volume
        if len(daily_ranges) >= 14:
            sessions.append(
                {
                    "date": day,
                    "cash_open": cash_open,
                    "cash_close": cash_close,
                    "daily_atr": float(np.median(daily_ranges)),
                    "bars": bars,
                    "minute_times": minutes.index.view("int64"),
                    "minute_open": minutes.open.to_numpy(dtype=float),
                    "minute_high": minutes.high.to_numpy(dtype=float),
                    "minute_low": minutes.low.to_numpy(dtype=float),
                    "minute_close": minutes.close.to_numpy(dtype=float),
                }
            )
        daily_ranges.append(float(minutes.high.max() - minutes.low.min()))
    return sessions


def next_minute_open(day: dict, after: pd.Timestamp) -> tuple[int, pd.Timestamp, float] | None:
    index = int(np.searchsorted(day["minute_times"], int(after.timestamp()), side="left"))
    if index >= len(day["minute_times"]):
        return None
    timestamp = pd.Timestamp(int(day["minute_times"][index]), unit="s", tz="UTC").tz_convert(NY)
    return index, timestamp, float(day["minute_open"][index])


def target_rr(target_mode: str) -> float | None:
    values = {"rr05": 0.5, "rr10": 1.0, "rr15": 1.5, "rr20": 2.0}
    return values.get(target_mode)


def trend_allows(bars: pd.DataFrame, index: int, direction: int, config: Config) -> bool:
    if config.trend_filter == "none":
        return True
    bar = bars.iloc[index]
    if config.trend_filter == "ema":
        return bool(bar.ema20 > bar.ema50) if direction > 0 else bool(bar.ema20 < bar.ema50)
    prior_index = index - config.vwap_slope_bars
    if prior_index < 0:
        return False
    slope = float(bar.vwap - bars.iloc[prior_index].vwap)
    return direction * slope > 0


def find_setup(day: dict, config: Config) -> dict | None:
    bars = day["bars"]
    atr = day["daily_atr"]
    orb_end = day["cash_open"] + pd.Timedelta(minutes=config.orb_minutes)
    setup_end = orb_end + pd.Timedelta(minutes=config.setup_window_minutes)
    orb = bars.loc[(bars.index >= day["cash_open"]) & (bars.index < orb_end)]
    candidates = bars.loc[(bars.index >= orb_end) & (bars.index < setup_end)]
    if orb.empty or candidates.empty:
        return None
    orb_high = float(orb.high.max())
    orb_low = float(orb.low.min())
    extension_buffer = config.extension_buffer_atr * atr
    direction = 0
    extension_extreme = math.nan
    extension_position = -1
    candidate_rows = list(candidates.iterrows())

    for position, (timestamp, bar) in enumerate(candidate_rows):
        if direction == 0:
            broke_high = float(bar.high) > orb_high + extension_buffer
            broke_low = float(bar.low) < orb_low - extension_buffer
            if broke_high and broke_low:
                direction = 1 if float(bar.close) >= (orb_high + orb_low) * 0.5 else -1
            elif broke_high:
                direction = 1
            elif broke_low:
                direction = -1
            else:
                continue
            extension_extreme = float(bar.high) if direction > 0 else float(bar.low)
            extension_position = position
            continue

        if direction > 0:
            extension_extreme = max(extension_extreme, float(bar.high))
        else:
            extension_extreme = min(extension_extreme, float(bar.low))
        if position <= extension_position:
            continue
        full_index = bars.index.get_loc(timestamp)
        if not trend_allows(bars, full_index, direction, config):
            continue
        vwap = float(bar.vwap)
        tolerance = config.touch_tolerance_atr * atr
        touched = float(bar.low) <= vwap + tolerance if direction > 0 else float(bar.high) >= vwap - tolerance
        if not touched:
            continue
        same_side = float(bar.open) > vwap and float(bar.close) > vwap if direction > 0 else float(bar.open) < vwap and float(bar.close) < vwap
        directional = float(bar.close) > float(bar.open) if direction > 0 else float(bar.close) < float(bar.open)
        accepted = same_side and (directional if config.confirmation == "directional" else True)
        if not accepted:
            if config.first_touch_only:
                return None
            continue

        entry_item = next_minute_open(day, timestamp + pd.Timedelta(minutes=5))
        if entry_item is None:
            return None
        entry_index, entry_time, entry = entry_item
        buffer = config.stop_buffer_atr * atr
        if config.stop_mode == "rejection":
            stop = float(bar.low) - buffer if direction > 0 else float(bar.high) + buffer
        elif config.stop_mode == "pullback_swing":
            swing = candidates.iloc[extension_position : position + 1]
            stop = float(swing.low.min()) - buffer if direction > 0 else float(swing.high.max()) + buffer
        else:
            stop = entry - config.atr_stop_multiple * atr if direction > 0 else entry + config.atr_stop_multiple * atr
        risk = direction * (entry - stop)
        if risk <= ROUND_TRIP_COST_POINTS * 1.5 or risk > 1.5 * atr:
            return None
        rr = target_rr(config.target_mode)
        target = extension_extreme if rr is None else entry + direction * rr * risk
        reward = direction * (target - entry)
        if reward <= ROUND_TRIP_COST_POINTS:
            return None
        return {
            "date": day["date"],
            "direction": direction,
            "orb_high": orb_high,
            "orb_low": orb_low,
            "vwap": vwap,
            "extension_extreme": extension_extreme,
            "signal_time": timestamp,
            "entry_time": entry_time,
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_points": risk,
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
    exit_time = pd.Timestamp(int(setup["minute_times"][start + int(exit_offset)]), unit="s", tz="UTC").tz_convert(NY)
    private = {"entry_index", "minute_times", "minute_high", "minute_low", "minute_close"}
    return {key: value for key, value in setup.items() if key not in private} | {
        "exit_time": exit_time,
        "exit_reason": exit_reason,
        "net_r": (raw_points - ROUND_TRIP_COST_POINTS) / risk,
    }


def statistics(trades: list[dict]) -> dict:
    balance = 10_000.0
    peak = balance
    maximum_drawdown = 0.0
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
        maximum_drawdown = max(maximum_drawdown, (peak - balance) / peak * 100.0)
        curve.append({"date": trade["exit_time"].isoformat(), "balance": balance})
    return {
        "initial_balance": 10_000.0,
        "final_balance": balance,
        "return_pct": (balance / 10_000.0 - 1.0) * 100.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0),
        "win_rate_pct": wins / len(trades) * 100.0 if trades else 0.0,
        "max_drawdown_pct": maximum_drawdown,
        "trades": len(trades),
        "wins": wins,
        "losses": len(trades) - wins,
        "curve": curve,
    }


def evaluate(sessions: list[dict], config: Config) -> dict:
    trades = [resolve_setup(setup) for day in sessions if (setup := find_setup(day, config)) is not None]
    return {
        "config": asdict(config),
        "slug": config.slug,
        "training": statistics([trade for trade in trades if trade["date"] < TRAIN_END]),
        "validation": statistics([trade for trade in trades if TRAIN_END <= trade["date"] < VALID_END]),
        "locked": statistics([trade for trade in trades if trade["date"] >= VALID_END]),
        "trades": trades,
    }


def is_eligible(result: dict) -> bool:
    training = result["training"]
    validation = result["validation"]
    return (
        training["trades"] >= 50
        and validation["trades"] >= 20
        and training["return_pct"] > 0
        and validation["return_pct"] > 0
        and training["profit_factor"] >= 1.03
        and validation["profit_factor"] >= 1.03
        and max(training["max_drawdown_pct"], validation["max_drawdown_pct"]) <= 20.0
    )


def score(result: dict) -> float:
    training = result["training"]
    validation = result["validation"]
    minimum_pf = min(training["profit_factor"], validation["profit_factor"])
    minimum_return = min(training["return_pct"] / 4.0, validation["return_pct"] / 1.5)
    maximum_dd = max(training["max_drawdown_pct"], validation["max_drawdown_pct"])
    return 8.0 * minimum_pf + 0.15 * minimum_return - 0.30 * maximum_dd


def public(result: dict) -> dict:
    value = {key: item for key, item in result.items() if key != "trades"}
    for split in ("training", "validation", "locked"):
        value[split] = {key: item for key, item in value[split].items() if key != "curve"}
    return value


def save_equity(selected: dict) -> None:
    plt.style.use("dark_background")
    figure, axes = plt.subplots(3, 1, figsize=(13, 9), sharex=False)
    figure.patch.set_facecolor("#071311")
    colors = {"training": "#61dafb", "validation": "#ffd166", "locked": "#5fffd1"}
    for axis, split in zip(axes, ("training", "validation", "locked")):
        axis.set_facecolor("#0b1c19")
        curve = selected[split]["curve"]
        dates = [pd.Timestamp(point["date"]) for point in curve[1:]]
        balances = [point["balance"] for point in curve[1:]]
        if dates:
            axis.plot(dates, balances, color=colors[split], linewidth=1.7)
        axis.axhline(10_000, color="#9ab5ad", linestyle="--", linewidth=0.8)
        axis.grid(alpha=0.25)
        axis.set_ylabel("Balance USD")
        axis.set_title(
            f"{split.title()}: {selected[split]['return_pct']:+.2f}% | PF {selected[split]['profit_factor']:.2f} | "
            f"DD {selected[split]['max_drawdown_pct']:.2f}% | {selected[split]['trades']} trades",
            loc="left",
        )
    figure.suptitle("US100 New York VWAP Bounce — independent 1% risk curves", fontsize=15, weight="bold")
    figure.tight_layout()
    figure.savefig(OUTPUT / "selected-screen-equity.png", dpi=180, bbox_inches="tight", facecolor=figure.get_facecolor())
    plt.close(figure)


def main() -> None:
    frame, metadata = fetch_rates()
    (OUTPUT / "data-source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    sessions = build_sessions(frame)
    print(f"constructed {len(sessions)} complete sessions", flush=True)
    if len(sessions) < 500:
        raise RuntimeError("Insufficient complete sessions")

    stage_one_configs = [
        Config(orb_minutes=orb, confirmation=confirmation, stop_mode=stop, target_mode=target)
        for orb, confirmation, stop, target in itertools.product(
            (15, 30),
            ("directional", "side_only"),
            ("rejection", "pullback_swing", "atr"),
            ("extreme", "rr05", "rr10", "rr15", "rr20"),
        )
    ]
    stage_one = []
    for index, config in enumerate(stage_one_configs, start=1):
        result = evaluate(sessions, config)
        result["score"] = score(result)
        result["eligible"] = is_eligible(result)
        stage_one.append(result)
        if index % 20 == 0:
            print(f"stage one {index}/{len(stage_one_configs)}", flush=True)
    ranked_one = sorted(stage_one, key=lambda item: item["score"], reverse=True)
    seed = next((item for item in ranked_one if item["eligible"]), ranked_one[0])
    seed_config = seed["config"]

    stage_two_configs = [
        Config(
            orb_minutes=orb,
            confirmation=confirmation,
            trend_filter=trend,
            extension_buffer_atr=extension_buffer,
            touch_tolerance_atr=tolerance,
            first_touch_only=first_touch,
            stop_mode=str(seed_config["stop_mode"]),
            target_mode=str(seed_config["target_mode"]),
        )
        for orb, confirmation, trend, extension_buffer, tolerance, first_touch in itertools.product(
            (15, 30),
            ("directional", "side_only"),
            ("none", "vwap_slope", "ema"),
            (0.0, 0.02),
            (0.01, 0.03, 0.05),
            (True, False),
        )
    ]
    stage_two = []
    for index, config in enumerate(stage_two_configs, start=1):
        result = evaluate(sessions, config)
        result["score"] = score(result)
        result["eligible"] = is_eligible(result)
        stage_two.append(result)
        if index % 50 == 0:
            print(f"stage two {index}/{len(stage_two_configs)}", flush=True)
    ranked = sorted(stage_one + stage_two, key=lambda item: item["score"], reverse=True)
    eligible = [item for item in ranked if item["eligible"]]
    selected = eligible[0] if eligible else ranked[0]

    rows = []
    for result in ranked:
        row = {"slug": result["slug"], "score": result["score"], "eligible": result["eligible"], **result["config"]}
        for split in ("training", "validation", "locked"):
            for key, value in public(result)[split].items():
                row[f"{split}_{key}"] = value
        rows.append(row)
    pd.DataFrame(rows).to_csv(OUTPUT / "all-screen-results.csv", index=False)
    (OUTPUT / "top-100-screen-results.json").write_text(
        json.dumps([public(item) | {"score": item["score"], "eligible": item["eligible"]} for item in ranked[:100]], indent=2),
        encoding="utf-8",
    )
    selected_public = public(selected) | {
        "score": selected["score"],
        "eligible": selected["eligible"],
        "eligible_candidates": len(eligible),
        "selection_rule": "Training and validation only; locked data was not used for selection.",
    }
    (OUTPUT / "selected-screen-result.json").write_text(json.dumps(selected_public, indent=2), encoding="utf-8")
    pd.DataFrame(
        [
            {key: value.isoformat() if isinstance(value, pd.Timestamp) else value for key, value in trade.items()}
            for trade in selected["trades"]
        ]
    ).to_csv(OUTPUT / "selected-screen-trades.csv", index=False)
    save_equity(selected)
    print(json.dumps(selected_public, indent=2))


if __name__ == "__main__":
    main()
