from __future__ import annotations

import itertools
import json
import math
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "Screen Results"
RESULTS.mkdir(exist_ok=True)
NY = ZoneInfo("America/New_York")
START = datetime(2020, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 8, 21, tzinfo=timezone.utc)
TRAIN_END = pd.Timestamp("2024-01-01", tz=NY)
VALID_END = pd.Timestamp("2025-07-01", tz=NY)
ROUND_TRIP_COST_POINTS = 2.0
RISK_FRACTION = 0.01


@dataclass(frozen=True)
class Config:
    opening_minutes: int
    direction: str
    gap_mode: str
    minimum_opening_efficiency: float
    minimum_breakout_relative_volume: float
    stop_mode: str
    reward_risk: float
    maximum_retest_bars: int = 3
    minimum_opening_relative_volume: float = 0.8
    minimum_range_daily_atr: float = 0.05
    maximum_range_daily_atr: float = 0.35
    breakout_body_minimum: float = 0.55
    breakout_buffer_daily_atr: float = 0.015
    maximum_pre_retest_excursion_range: float = 0.60
    retest_tolerance_range: float = 0.12
    break_even_at_r: float = 1.0

    @property
    def slug(self) -> str:
        return (
            f"or{self.opening_minutes}-{self.direction}-{self.gap_mode}"
            f"-eff{self.minimum_opening_efficiency:g}-bv{self.minimum_breakout_relative_volume:g}"
            f"-{self.stop_mode}-rr{self.reward_risk:g}"
        ).replace(".", "")


def fetch_rates() -> pd.DataFrame:
    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        terminal = mt5.terminal_info()
        account = mt5.account_info()
        rates = mt5.copy_rates_range("USTEC", mt5.TIMEFRAME_M1, START, END)
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No USTEC M1 history: {mt5.last_error()}")
        metadata = {
            "terminal": terminal.path if terminal else None,
            "terminal_build": terminal.build if terminal else None,
            "account": account.login if account else None,
            "server": account.server if account else None,
            "symbol": "USTEC",
            "source_rows": int(len(rates)),
            "source_start_utc": datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc).isoformat(),
            "source_end_utc": datetime.fromtimestamp(int(rates[-1]["time"]), timezone.utc).isoformat(),
            "round_trip_cost_points": ROUND_TRIP_COST_POINTS,
        }
        (RESULTS / "data-source.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    finally:
        mt5.shutdown()

    frame = pd.DataFrame(rates)
    frame["timestamp"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_convert(NY)
    frame = frame.set_index("timestamp").sort_index()
    frame = frame.loc[~frame.index.duplicated(keep="last")]
    frame = frame.between_time("04:00", "16:00", inclusive="both")
    return frame[["open", "high", "low", "close", "tick_volume", "spread"]].astype(float)


def aggregate_five_minutes(rth: pd.DataFrame) -> pd.DataFrame:
    bars = rth.resample("5min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
    )
    return bars.dropna()


def build_sessions(frame: pd.DataFrame, opening_minutes: int) -> list[dict]:
    raw: list[dict] = []
    for session_date, day in frame.groupby(frame.index.date, sort=True):
        rth = day.between_time("09:30", "15:59", inclusive="both")
        if len(rth) < 300 or rth.index[0].time() != time(9, 30):
            continue
        five = aggregate_five_minutes(rth)
        if len(five) < 70:
            continue
        range_start = pd.Timestamp.combine(session_date, time(9, 30)).tz_localize(NY)
        range_end = range_start + pd.Timedelta(minutes=opening_minutes)
        opening = rth.loc[(rth.index >= range_start) & (rth.index < range_end)]
        if len(opening) < opening_minutes:
            continue
        prior = day.between_time("04:00", "09:29", inclusive="both")
        raw.append(
            {
                "date": pd.Timestamp(session_date, tz=NY),
                "open": float(opening.iloc[0].open),
                "close": float(rth.iloc[-1].close),
                "high": float(rth.high.max()),
                "low": float(rth.low.min()),
                "opening_high": float(opening.high.max()),
                "opening_low": float(opening.low.min()),
                "opening_close": float(opening.iloc[-1].close),
                "opening_volume": float(opening.tick_volume.sum()),
                "premarket_open": float(prior.iloc[0].open) if len(prior) else float(opening.iloc[0].open),
                "five": five,
                "range_end": range_end,
            }
        )

    sessions: list[dict] = []
    opening_volumes: deque[float] = deque(maxlen=20)
    true_ranges: deque[float] = deque(maxlen=20)
    minute_volumes: dict[int, deque[float]] = defaultdict(lambda: deque(maxlen=20))
    previous_close: float | None = None
    for day in raw:
        width = day["opening_high"] - day["opening_low"]
        current_true_range = day["high"] - day["low"]
        if previous_close is not None:
            current_true_range = max(
                current_true_range,
                abs(day["high"] - previous_close),
                abs(day["low"] - previous_close),
            )
        if len(opening_volumes) >= 15 and len(true_ranges) >= 15 and previous_close is not None and width > 0:
            day["opening_relative_volume"] = day["opening_volume"] / float(np.median(opening_volumes))
            day["daily_atr"] = float(np.median(true_ranges))
            day["range_daily_atr"] = width / day["daily_atr"]
            day["gap_daily_atr"] = (day["open"] - previous_close) / day["daily_atr"]
            day["opening_efficiency"] = (day["opening_close"] - day["open"]) / width
            five = day["five"].copy()
            relative_volume: list[float] = []
            cumulative_weighted = 0.0
            cumulative_volume = 0.0
            vwaps: list[float] = []
            for timestamp, bar in five.iterrows():
                slot = timestamp.hour * 60 + timestamp.minute
                history = minute_volumes[slot]
                baseline = float(np.median(history)) if len(history) >= 10 else math.nan
                relative_volume.append(float(bar.tick_volume) / baseline if baseline > 0 else math.nan)
                typical = (float(bar.high) + float(bar.low) + float(bar.close)) / 3.0
                cumulative_weighted += typical * float(bar.tick_volume)
                cumulative_volume += float(bar.tick_volume)
                vwaps.append(cumulative_weighted / cumulative_volume if cumulative_volume > 0 else math.nan)
            five["relative_volume"] = relative_volume
            five["vwap"] = vwaps
            day["five"] = five
            sessions.append(day)
        opening_volumes.append(day["opening_volume"])
        true_ranges.append(current_true_range)
        for timestamp, bar in day["five"].iterrows():
            minute_volumes[timestamp.hour * 60 + timestamp.minute].append(float(bar.tick_volume))
        previous_close = day["close"]
    return sessions


def candle_body_ratio(bar: pd.Series) -> float:
    width = float(bar.high - bar.low)
    return abs(float(bar.close - bar.open)) / width if width > 0 else 0.0


def find_trade(day: dict, config: Config) -> dict | None:
    if not (config.minimum_range_daily_atr <= day["range_daily_atr"] <= config.maximum_range_daily_atr):
        return None
    if day["opening_relative_volume"] < config.minimum_opening_relative_volume:
        return None
    bars = day["five"]
    candidates = bars.loc[(bars.index >= day["range_end"]) & (bars.index < day["date"] + pd.Timedelta(hours=11, minutes=30))]
    high = day["opening_high"]
    low = day["opening_low"]
    width = high - low
    buffer = config.breakout_buffer_daily_atr * day["daily_atr"]
    breakout_items = list(candidates.iterrows())
    for breakout_index, (timestamp, bar) in enumerate(breakout_items):
        if not np.isfinite(bar.relative_volume) or bar.relative_volume < config.minimum_breakout_relative_volume:
            continue
        if candle_body_ratio(bar) < config.breakout_body_minimum:
            continue
        direction = 0
        if bar.close > high + buffer and bar.close > bar.open:
            direction = 1
        elif bar.close < low - buffer and bar.close < bar.open:
            direction = -1
        if direction == 0 or (config.direction == "long" and direction < 0):
            continue
        if direction * day["opening_efficiency"] < config.minimum_opening_efficiency:
            continue
        if config.gap_mode == "not_against" and direction * day["gap_daily_atr"] < -0.05:
            continue
        if config.gap_mode == "align" and direction * day["gap_daily_atr"] < 0.02:
            continue
        if (direction > 0 and bar.close <= bar.vwap) or (direction < 0 and bar.close >= bar.vwap):
            continue

        boundary = high if direction > 0 else low
        tolerance = config.retest_tolerance_range * width
        retest_candidates = breakout_items[breakout_index + 1 : breakout_index + 1 + config.maximum_retest_bars]
        for retest_offset, (retest_time, retest) in enumerate(retest_candidates, start=1):
            excursion = (retest.high - boundary) if direction > 0 else (boundary - retest.low)
            if excursion > config.maximum_pre_retest_excursion_range * width:
                break
            accepted = (
                retest.low <= boundary + tolerance
                and retest.close >= boundary
                and retest.close > retest.open
                if direction > 0
                else retest.high >= boundary - tolerance
                and retest.close <= boundary
                and retest.close < retest.open
            )
            if not accepted:
                continue
            all_bars = list(bars.iterrows())
            full_index = next((i for i, (ts, _) in enumerate(all_bars) if ts == retest_time), -1)
            if full_index < 0 or full_index + 1 >= len(all_bars):
                return None
            entry_time, entry_bar = all_bars[full_index + 1]
            entry = float(entry_bar.open)
            if config.stop_mode == "retest":
                stop = float(retest.low - 0.05 * width) if direction > 0 else float(retest.high + 0.05 * width)
            elif config.stop_mode == "midpoint":
                midpoint = (high + low) * 0.5
                stop = midpoint - 0.05 * width if direction > 0 else midpoint + 0.05 * width
            else:
                stop = low - 0.05 * width if direction > 0 else high + 0.05 * width
            risk = direction * (entry - stop)
            if risk <= ROUND_TRIP_COST_POINTS or risk > 0.80 * day["daily_atr"]:
                return None
            target = entry + direction * config.reward_risk * risk
            return {
                "date": day["date"],
                "direction": direction,
                "entry_time": entry_time,
                "entry": entry,
                "stop": stop,
                "target": target,
                "risk": risk,
                "bars": bars.loc[bars.index >= entry_time],
                "breakout_relative_volume": float(bar.relative_volume),
                "opening_relative_volume": day["opening_relative_volume"],
                "gap_daily_atr": day["gap_daily_atr"],
                "range_daily_atr": day["range_daily_atr"],
                "retest_bars": retest_offset,
            }
        return None
    return None


def resolve_trade(trade: dict, config: Config) -> dict:
    direction = trade["direction"]
    entry = trade["entry"]
    stop = trade["stop"]
    target = trade["target"]
    risk = trade["risk"]
    break_even = False
    exit_time = trade["bars"].index[-1]
    raw_points = direction * (float(trade["bars"].iloc[-1].close) - entry)
    exit_reason = "session_close"
    for timestamp, bar in trade["bars"].iterrows():
        active_stop = entry if break_even else stop
        stop_hit = bar.low <= active_stop if direction > 0 else bar.high >= active_stop
        target_hit = bar.high >= target if direction > 0 else bar.low <= target
        if stop_hit and target_hit:
            target_hit = False
        if stop_hit:
            raw_points = direction * (active_stop - entry)
            exit_time = timestamp
            exit_reason = "break_even" if break_even else "stop"
            break
        if target_hit:
            raw_points = direction * (target - entry)
            exit_time = timestamp
            exit_reason = "target"
            break
        favorable = direction * ((float(bar.high) if direction > 0 else float(bar.low)) - entry)
        if not break_even and config.break_even_at_r > 0 and favorable >= config.break_even_at_r * risk:
            break_even = True
    net_r = (raw_points - ROUND_TRIP_COST_POINTS) / risk
    return trade | {"r": net_r, "exit_time": exit_time, "exit_reason": exit_reason}


def statistics(trades: list[dict]) -> dict:
    equity = 10_000.0
    peak = equity
    maximum_drawdown = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    curve = [{"date": None, "equity": equity}]
    for trade in trades:
        pnl = equity * RISK_FRACTION * trade["r"]
        equity += pnl
        gross_profit += max(0.0, pnl)
        gross_loss += max(0.0, -pnl)
        wins += int(pnl > 0)
        peak = max(peak, equity)
        maximum_drawdown = max(maximum_drawdown, (peak - equity) / peak * 100.0)
        curve.append({"date": trade["date"].isoformat(), "equity": equity})
    return {
        "trades": len(trades),
        "wins": wins,
        "win_rate_pct": wins / len(trades) * 100.0 if trades else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0),
        "return_pct": (equity / 10_000.0 - 1.0) * 100.0,
        "maximum_drawdown_pct": maximum_drawdown,
        "final_balance": equity,
        "gross_profit": gross_profit,
        "gross_loss": -gross_loss,
        "curve": curve,
    }


def evaluate(sessions: list[dict], config: Config) -> dict:
    trades = [resolve_trade(trade, config) for day in sessions if (trade := find_trade(day, config)) is not None]
    train = [trade for trade in trades if trade["date"] < TRAIN_END]
    validation = [trade for trade in trades if TRAIN_END <= trade["date"] < VALID_END]
    locked = [trade for trade in trades if trade["date"] >= VALID_END]
    return {
        "config": asdict(config),
        "slug": config.slug,
        "training": statistics(train),
        "validation": statistics(validation),
        "locked": statistics(locked),
        "all_trades": trades,
    }


def public_result(result: dict) -> dict:
    cleaned = {key: value for key, value in result.items() if key != "all_trades"}
    for split in ("training", "validation", "locked"):
        cleaned[split] = {key: value for key, value in cleaned[split].items() if key != "curve"}
    return cleaned


def candidate_score(result: dict) -> float:
    train = result["training"]
    validation = result["validation"]
    if train["trades"] < 35 or validation["trades"] < 18:
        return -1e9
    if train["profit_factor"] <= 1.0 or validation["profit_factor"] <= 1.0:
        return -1e9
    if train["return_pct"] <= 0 or validation["return_pct"] <= 0:
        return -1e9
    if max(train["maximum_drawdown_pct"], validation["maximum_drawdown_pct"]) > 15.0:
        return -1e9
    minimum_pf = min(train["profit_factor"], validation["profit_factor"])
    return minimum_pf * math.sqrt(train["trades"] + validation["trades"]) - 0.25 * max(
        train["maximum_drawdown_pct"], validation["maximum_drawdown_pct"]
    )


def save_equity(result: dict) -> None:
    plt.figure(figsize=(12, 6))
    colors = {"training": "#1f77b4", "validation": "#ff9f1c", "locked": "#2a9d8f"}
    for split in ("training", "validation", "locked"):
        trades = [
            trade
            for trade in result["all_trades"]
            if (trade["date"] < TRAIN_END if split == "training" else TRAIN_END <= trade["date"] < VALID_END if split == "validation" else trade["date"] >= VALID_END)
        ]
        stats = statistics(trades)
        dates = [pd.Timestamp(point["date"]) for point in stats["curve"][1:]]
        values = [point["equity"] for point in stats["curve"][1:]]
        if dates:
            plt.plot(dates, values, label=split.title(), color=colors[split], linewidth=1.5)
    plt.axhline(10_000, color="#777", linestyle="--", linewidth=0.8)
    plt.title("US100 Selective ORB — independent $10,000 split equity curves")
    plt.ylabel("Balance (USD, 1% risk per trade)")
    plt.grid(alpha=0.2)
    plt.legend()
    plt.tight_layout()
    plt.savefig(RESULTS / "selected-screen-equity.png", dpi=180)
    plt.close()


def main() -> None:
    frame = fetch_rates()
    sessions_by_length = {length: build_sessions(frame, length) for length in (5, 15, 30)}
    configurations = [
        Config(length, direction, gap, efficiency, breakout_volume, stop_mode, reward_risk)
        for length, direction, gap, efficiency, breakout_volume, stop_mode, reward_risk in itertools.product(
            (5, 15, 30),
            ("both", "long"),
            ("any", "not_against"),
            (0.0, 0.25),
            (0.8, 1.1),
            ("retest", "midpoint", "opposite"),
            (1.5, 2.0),
        )
    ]
    results: list[dict] = []
    for index, config in enumerate(configurations, start=1):
        result = evaluate(sessions_by_length[config.opening_minutes], config)
        result["selection_score"] = candidate_score(result)
        results.append(result)
        if index % 48 == 0:
            print(f"screened {index}/{len(configurations)}")
    ranked = sorted(results, key=lambda item: item["selection_score"], reverse=True)
    eligible = [item for item in ranked if item["selection_score"] > -1e8]
    selected = eligible[0] if eligible else ranked[0]
    (RESULTS / "all-screen-results.json").write_text(
        json.dumps([public_result(item) | {"selection_score": item["selection_score"]} for item in ranked], indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(
        [
            {
                "slug": item["slug"],
                "selection_score": item["selection_score"],
                **item["config"],
                **{f"train_{key}": value for key, value in item["training"].items() if key != "curve"},
                **{f"validation_{key}": value for key, value in item["validation"].items() if key != "curve"},
                **{f"locked_{key}": value for key, value in item["locked"].items() if key != "curve"},
            }
            for item in ranked
        ]
    ).to_csv(RESULTS / "all-screen-results.csv", index=False)
    selected_public = public_result(selected) | {
        "selection_score": selected["selection_score"],
        "eligible_candidates": len(eligible),
        "selection_rule": "Locked period was not used for selection.",
    }
    (RESULTS / "selected-screen-result.json").write_text(json.dumps(selected_public, indent=2), encoding="utf-8")
    pd.DataFrame(
        [
            {
                key: value.isoformat() if isinstance(value, pd.Timestamp) else value
                for key, value in trade.items()
                if key != "bars"
            }
            for trade in selected["all_trades"]
        ]
    ).to_csv(RESULTS / "selected-screen-trades.csv", index=False)
    save_equity(selected)
    print(json.dumps(selected_public, indent=2))


if __name__ == "__main__":
    main()
