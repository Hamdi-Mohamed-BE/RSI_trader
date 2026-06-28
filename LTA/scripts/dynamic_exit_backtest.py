from __future__ import annotations

import argparse
import heapq
import json
import math
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import REPORTS_DIR, load_config
from app.adaptive_risk import (
    apply_dynamic_stop,
    dynamic_stop_settings,
    evaluate_setup_validity,
    smart_exit_settings,
)
from app.mt5_client import MT5Client, TIMEFRAME_MINUTES
from app.orb_strategy import ORBSettings, atr as orb_atr, session_bounds as orb_session_bounds
from app.session_time import DEFAULT_DATA_TIMEZONE, DEFAULT_SESSION_TIMEZONE, as_aware, date_in_timezone
from app.strategy_engine import generate_signal


DEFAULT_LTA_SYMBOLS = ("AUDUSD", "GBPJPY", "USDCAD")
DEFAULT_ORB_SYMBOLS = ("AUDUSD", "NZDUSD", "USDCAD", "GBPUSD", "USDCHF")
DEFAULT_LTA_TIMEFRAMES = ("M15", "M30")


@dataclass(frozen=True)
class Candidate:
    bot: str
    symbol: str
    timeframe: str
    series_key: str
    start_index: int
    opened_at: datetime
    direction: str
    entry: float
    base_stop: float
    configured_rr: float
    setup_score: int
    atr: float
    atr_percentile: float
    session_metric: float | None
    entry_model: str


@dataclass
class PolicyTrade:
    policy: str
    bot: str
    symbol: str
    timeframe: str
    month: str
    opened_at: str
    closed_at: str
    direction: str
    entry: float
    stop_loss: float
    final_rr: float
    exit_price: float
    result: str
    r_multiple: float
    setup_score: int
    atr: float
    spread_r: float
    spread_points: float
    atr_percentile: float
    session_metric: float | None
    stop_mode: str
    rr_mode: str
    entry_model: str


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def parse_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def parse_rr_map(value: str | None) -> dict[str, float]:
    out: dict[str, float] = {}
    if not value:
        return out
    for chunk in value.split(","):
        if ":" not in chunk:
            continue
        symbol, raw_value = chunk.split(":", 1)
        symbol = symbol.strip().upper()
        try:
            out[symbol] = float(raw_value.strip())
        except ValueError:
            continue
    return out


def parse_sessions(value: str | None) -> list[tuple[int, int, str]]:
    sessions: list[tuple[int, int, str]] = []
    if not value:
        return sessions
    for chunk in value.split(","):
        label = chunk.strip()
        if not label or "-" not in label:
            continue
        start_raw, end_raw = label.split("-", 1)
        try:
            start_h, start_m = [int(part) for part in start_raw.strip().split(":", 1)]
            end_h, end_m = [int(part) for part in end_raw.strip().split(":", 1)]
        except ValueError:
            continue
        sessions.append((start_h * 60 + start_m, end_h * 60 + end_m, label))
    return sessions


def in_allowed_sessions(
    value: datetime,
    sessions: list[tuple[int, int, str]],
    data_timezone: str,
    session_timezone: str,
) -> bool:
    if not sessions:
        return True
    local = as_aware(value, data_timezone).astimezone(as_aware(datetime.now(), session_timezone).tzinfo)
    minutes = local.hour * 60 + local.minute
    for start, end, _label in sessions:
        if start <= end and start <= minutes <= end:
            return True
        if start > end and (minutes >= start or minutes <= end):
            return True
    return False


def passes_strict_session_gate(
    signal: dict[str, Any],
    value: datetime,
    data_timezone: str,
    session_timezone: str,
) -> bool:
    start_raw = os.getenv("AUTO_STRICT_SESSION_START", "10:00")
    end_raw = os.getenv("AUTO_STRICT_SESSION_END", "13:00")
    ranges = parse_sessions(f"{start_raw}-{end_raw}")
    if not ranges or ranges[0][0] == ranges[0][1]:
        return True
    local = as_aware(value, data_timezone).astimezone(as_aware(datetime.now(), session_timezone).tzinfo)
    minutes = local.hour * 60 + local.minute
    start, end, _label = ranges[0]
    in_window = start <= minutes < end if start < end else minutes >= start or minutes < end
    if not in_window:
        return True
    min_score = int(os.getenv("AUTO_STRICT_SESSION_MIN_SCORE", "96") or 96)
    if int(signal.get("setup_score") or 0) < min_score:
        return False
    require_internal = str(os.getenv("AUTO_STRICT_SESSION_REQUIRE_INTERNAL_BREAK", "true")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return not require_internal or "Internal Structure" in str(signal.get("entry_model") or "")


def normalize_candles(candles: pd.DataFrame) -> pd.DataFrame:
    df = candles.copy()
    df["time"] = pd.to_datetime(df["time"])
    for column in ("open", "high", "low", "close"):
        df[column] = pd.to_numeric(df[column], errors="coerce")
    if "volume" not in df.columns and "tick_volume" in df.columns:
        df["volume"] = df["tick_volume"]
    return df.dropna(subset=["time", "open", "high", "low", "close"]).sort_values("time").reset_index(drop=True)


def add_atr_columns(df: pd.DataFrame, period: int = 14, percentile_window: int = 96) -> pd.DataFrame:
    out = df.copy()
    high = out["high"].astype(float)
    low = out["low"].astype(float)
    close = out["close"].astype(float)
    previous_close = close.shift(1)
    true_range = pd.concat([(high - low), (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
    atr = true_range.rolling(period).mean()
    out["atr"] = atr

    percentiles: list[float] = []
    values = atr.tolist()
    for index, value in enumerate(values):
        if value is None or not math.isfinite(float(value)) or float(value) <= 0:
            percentiles.append(0.5)
            continue
        start = max(0, index - percentile_window)
        window = [float(item) for item in values[start:index] if item is not None and math.isfinite(float(item)) and float(item) > 0]
        if not window:
            percentiles.append(0.5)
            continue
        less_equal = sum(1 for item in window if item <= float(value))
        percentiles.append(less_equal / len(window))
    out["atr_percentile"] = percentiles
    return out


def current_rr(symbol: str, default_rr: float, rr_map: dict[str, float]) -> float:
    return max(1.0, float(rr_map.get(symbol.upper(), default_rr)))


def infer_point(symbol: str) -> float:
    upper = symbol.upper()
    if upper.endswith("JPY") and len(upper) == 6:
        return 0.001
    if len(upper) == 6 and upper[:3].isalpha() and upper[3:].isalpha():
        return 0.00001
    if upper == "XAUUSD":
        return 0.01
    if upper == "XAGUSD":
        return 0.001
    if upper == "BTCUSD":
        return 0.01
    if upper in {"US30", "US300"}:
        return 0.1
    return 0.01


def historical_spread_price(row: pd.Series, symbol: str) -> tuple[float, float]:
    try:
        points = max(0.0, float(row.get("spread") or 0.0))
    except (TypeError, ValueError):
        points = 0.0
    try:
        multiplier = max(0.0, float(os.getenv("BACKTEST_SPREAD_MULTIPLIER", "1") or 1.0))
    except ValueError:
        multiplier = 1.0
    return points * infer_point(symbol) * multiplier, points


def dynamic_rr(candidate: Candidate, mode: str) -> float:
    score = int(candidate.setup_score)
    vol = float(candidate.atr_percentile)
    session_metric = candidate.session_metric
    wide_session = session_metric is not None and session_metric > 1.35
    narrow_session = session_metric is not None and session_metric < 0.70

    if mode == "static":
        return max(1.0, candidate.configured_rr)
    if mode == "challenge20":
        risk_percent = max(0.01, float(os.getenv("CHALLENGE20_RISK_PERCENT", "23") or 23.0))
        target_percent = max(0.01, float(os.getenv("CHALLENGE20_TARGET_PERCENT", "30") or 30.0))
        return target_percent / risk_percent
    if mode == "conservative":
        return 2.0 if vol >= 0.75 or wide_session else 3.0
    if mode == "balanced":
        if vol >= 0.80 or wide_session:
            return 3.0
        if score >= 96 and (vol <= 0.45 or narrow_session):
            return 5.0
        return 4.0
    if mode == "score":
        rr = 6.0 if score >= 98 else 5.0 if score >= 95 else 3.0
        if vol >= 0.80 or wide_session:
            rr -= 1.0
        return max(2.0, rr)
    if mode == "aggressive":
        if vol >= 0.85 or wide_session:
            return 4.0
        return 6.0 if score >= 95 else 5.0
    return max(1.0, candidate.configured_rr)


def dynamic_stop_distance(candidate: Candidate, mode: str) -> tuple[float, str]:
    base_risk = abs(candidate.entry - candidate.base_stop)
    atr_value = max(float(candidate.atr or 0.0), base_risk * 0.25, abs(candidate.entry) * 0.00001)
    vol = float(candidate.atr_percentile)
    session_metric = candidate.session_metric

    if mode == "static":
        return base_risk, "structure"
    if mode == "atr_floor_0_8":
        return max(base_risk, atr_value * 0.8), "max(structure,0.8ATR)"
    if mode == "atr_floor_1_0":
        return max(base_risk, atr_value * 1.0), "max(structure,1.0ATR)"
    if mode == "adaptive":
        floor = 0.80
        if vol >= 0.80 or (session_metric is not None and session_metric > 1.35):
            floor = 1.25
        elif vol >= 0.60:
            floor = 1.00
        elif session_metric is not None and session_metric < 0.70:
            floor = 0.70
        return max(base_risk, atr_value * floor), f"max(structure,{floor:.2f}ATR)"
    if mode == "adaptive_cap":
        floor = 0.85 if vol < 0.70 else 1.10
        capped = min(max(base_risk, atr_value * floor), atr_value * 2.20)
        return max(capped, atr_value * 0.35), f"min(max(structure,{floor:.2f}ATR),2.2ATR)"
    return base_risk, "structure"


POLICIES: tuple[dict[str, str], ...] = (
    {"name": "production_current", "stop": "live_adaptive", "rr": "static"},
    {"name": "challenge20_current", "stop": "live_adaptive", "rr": "challenge20"},
    {"name": "fixed_current", "stop": "static", "rr": "static"},
    {"name": "dynamic_balanced", "stop": "adaptive", "rr": "balanced"},
    {"name": "dynamic_conservative", "stop": "atr_floor_1_0", "rr": "conservative"},
    {"name": "dynamic_score", "stop": "adaptive", "rr": "score"},
    {"name": "dynamic_aggressive", "stop": "atr_floor_0_8", "rr": "aggressive"},
    {"name": "dynamic_capped", "stop": "adaptive_cap", "rr": "balanced"},
)


def price_at_r(entry: float, risk: float, direction: str, r_value: float) -> float:
    if direction == "BUY":
        return entry + risk * r_value
    return entry - risk * r_value


def stop_from_r(entry: float, risk: float, direction: str, r_value: float) -> float:
    if direction == "BUY":
        return entry + risk * r_value
    return entry - risk * r_value


def simulate_managed_trade(
    df: pd.DataFrame,
    candidate: Candidate,
    policy: dict[str, str],
    max_holding_bars: int,
    partial_fraction: float = 0.0,
) -> PolicyTrade | None:
    direction = candidate.direction.upper()
    if direction not in {"BUY", "SELL"}:
        return None

    if policy["stop"] == "live_adaptive":
        prefix = (
            "CHALLENGE20"
            if policy["name"] == "challenge20_current"
            else "AUTO" if candidate.bot.upper() == "LTA" else candidate.bot.upper()
        )
        signal = {
            "direction": direction,
            "entry": candidate.entry,
            "stop_loss": candidate.base_stop,
            "risk_reward": candidate.configured_rr,
        }
        context = df.iloc[max(0, candidate.start_index - 160) : candidate.start_index + 1]
        adjusted = apply_dynamic_stop(
            signal,
            context,
            dynamic_stop_settings(prefix),
            last_bar_is_closed=True,
        )
        risk_distance = abs(float(adjusted.get("stop_loss") or candidate.base_stop) - candidate.entry)
        dynamic_meta = adjusted.get("dynamic_stop") or {}
        stop_mode = (
            f"live_adaptive(vol={float(dynamic_meta.get('volatility_ratio') or 1):.2f},"
            f"volume={float(dynamic_meta.get('volume_ratio') or 1):.2f})"
        )
    else:
        risk_distance, stop_mode = dynamic_stop_distance(candidate, policy["stop"])
    if risk_distance <= 0:
        return None
    entry = candidate.entry
    stop = entry - risk_distance if direction == "BUY" else entry + risk_distance
    final_rr = dynamic_rr(candidate, policy["rr"])
    end_index = min(len(df) - 1, candidate.start_index + max(1, max_holding_bars))
    trade_path = df.iloc[candidate.start_index : end_index + 1]
    if trade_path.empty:
        return None

    current_sl_r = -1.0
    stage = 0
    remaining = 1.0
    first_row = trade_path.iloc[0]
    spread_price, spread_points = historical_spread_price(first_row, candidate.symbol)
    spread_r = spread_price / risk_distance if risk_distance > 0 else 0.0
    spread_enabled = str(os.getenv("BACKTEST_SPREAD_ADJUST", "true")).strip().lower() in {"1", "true", "yes", "on"}
    max_spread_r = float(os.getenv("BACKTEST_MAX_SPREAD_R", "0") or 0.0)
    if spread_enabled and max_spread_r > 0 and spread_r > max_spread_r:
        return None
    realized_r = -spread_r if spread_enabled else 0.0
    exit_price = float(trade_path.iloc[-1]["close"])
    closed_at = pd.Timestamp(trade_path.iloc[-1]["time"]).to_pydatetime()
    result = "timeout"

    use_smart_exit = policy["name"] in {"production_current", "challenge20_current"}
    exit_prefix = (
        "CHALLENGE20"
        if policy["name"] == "challenge20_current"
        else "AUTO" if candidate.bot.upper() == "LTA" else candidate.bot.upper()
    )
    exit_settings = smart_exit_settings(exit_prefix)
    for row_index, row in trade_path.iterrows():
        high = float(row["high"])
        low = float(row["low"])
        happened_at = pd.Timestamp(row["time"]).to_pydatetime()
        current_sl = stop_from_r(entry, risk_distance, direction, current_sl_r)
        final_tp = price_at_r(entry, risk_distance, direction, final_rr)
        if direction == "BUY":
            if low <= current_sl:
                exit_price = current_sl
                closed_at = happened_at
                result = "loss" if current_sl_r < -0.05 else "trail_stop"
                realized_r += remaining * current_sl_r
                break
            if high >= final_tp:
                exit_price = final_tp
                closed_at = happened_at
                result = "win"
                realized_r += remaining * final_rr
                break
            while stage < int(math.floor(final_rr)) and high >= price_at_r(entry, risk_distance, direction, stage + 1):
                stage += 1
                if stage == 1:
                    if partial_fraction > 0 and remaining > 0:
                        close_fraction = min(partial_fraction, remaining)
                        realized_r += close_fraction * 1.0
                        remaining -= close_fraction
                    current_sl_r = max(current_sl_r, 0.0)
                elif stage >= 2:
                    current_sl_r = max(current_sl_r, float(stage - 1))
        else:
            if high >= current_sl:
                exit_price = current_sl
                closed_at = happened_at
                result = "loss" if current_sl_r < -0.05 else "trail_stop"
                realized_r += remaining * current_sl_r
                break
            if low <= final_tp:
                exit_price = final_tp
                closed_at = happened_at
                result = "win"
                realized_r += remaining * final_rr
                break
            while stage < int(math.floor(final_rr)) and low <= price_at_r(entry, risk_distance, direction, stage + 1):
                stage += 1
                if stage == 1:
                    if partial_fraction > 0 and remaining > 0:
                        close_fraction = min(partial_fraction, remaining)
                        realized_r += close_fraction * 1.0
                        remaining -= close_fraction
                    current_sl_r = max(current_sl_r, 0.0)
                elif stage >= 2:
                    current_sl_r = max(current_sl_r, float(stage - 1))

        smart_exit_delay = TIMEFRAME_MINUTES.get(exit_settings.timeframe, 15) * exit_settings.min_bars_open * 60
        elapsed_seconds = (happened_at - candidate.opened_at).total_seconds()
        if use_smart_exit and exit_settings.enabled and elapsed_seconds >= smart_exit_delay:
            close_price = float(row["close"])
            unrealized_r = (
                (close_price - entry) / risk_distance
                if direction == "BUY"
                else (entry - close_price) / risk_distance
            )
            validity = evaluate_setup_validity(
                df.iloc[max(0, int(row_index) - exit_settings.lookback_bars) : int(row_index) + 1],
                direction=direction,
                entry=entry,
                profit=unrealized_r,
                settings=exit_settings,
                last_bar_is_closed=True,
            )
            if validity.get("invalid"):
                exit_price = close_price
                closed_at = happened_at
                result = "smart_exit"
                realized_r += remaining * unrealized_r
                break
    else:
        if direction == "BUY":
            realized_r += remaining * ((exit_price - entry) / risk_distance)
        else:
            realized_r += remaining * ((entry - exit_price) / risk_distance)

    opened_at = candidate.opened_at
    return PolicyTrade(
        policy=policy["name"],
        bot=candidate.bot,
        symbol=candidate.symbol,
        timeframe=candidate.timeframe,
        month=opened_at.strftime("%Y-%m"),
        opened_at=opened_at.isoformat(sep=" ", timespec="seconds"),
        closed_at=closed_at.isoformat(sep=" ", timespec="seconds"),
        direction=direction,
        entry=round(entry, 6),
        stop_loss=round(stop, 6),
        final_rr=round(final_rr, 3),
        exit_price=round(exit_price, 6),
        result=result,
        r_multiple=round(float(realized_r), 4),
        setup_score=candidate.setup_score,
        atr=round(float(candidate.atr), 6),
        spread_r=round(float(spread_r if spread_enabled else 0.0), 4),
        spread_points=round(float(spread_points), 2),
        atr_percentile=round(float(candidate.atr_percentile), 4),
        session_metric=round(float(candidate.session_metric), 4) if candidate.session_metric is not None else None,
        stop_mode=stop_mode,
        rr_mode=policy["rr"],
        entry_model=candidate.entry_model,
    )


def summarize_trades(rows: list[dict[str, Any]], groups: list[str]) -> pd.DataFrame:
    columns = [
        *groups,
        "trades",
        "wins",
        "losses",
        "trail_stops",
        "timeouts",
        "win_rate",
        "net_r",
        "avg_r",
        "profit_factor",
        "avg_final_rr",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows)
    out: list[dict[str, Any]] = []
    for keys, group in frame.groupby(groups, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        r_values = group["r_multiple"].astype(float)
        gross_r = float(r_values[r_values > 0].sum())
        loss_r = abs(float(r_values[r_values < 0].sum()))
        total = int(len(group))
        wins = int((group["result"] == "win").sum())
        row = dict(zip(groups, keys))
        row.update(
            {
                "trades": total,
                "wins": wins,
                "losses": int((group["result"] == "loss").sum()),
                "trail_stops": int((group["result"] == "trail_stop").sum()),
                "timeouts": int((group["result"] == "timeout").sum()),
                "win_rate": round(wins / total * 100, 2) if total else 0.0,
                "net_r": round(float(r_values.sum()), 2),
                "avg_r": round(float(r_values.mean()), 3) if total else 0.0,
                "profit_factor": round(gross_r / loss_r, 2) if loss_r else round(gross_r, 2),
                "avg_final_rr": round(float(group["final_rr"].astype(float).mean()), 2) if total else 0.0,
            }
        )
        out.append(row)
    return pd.DataFrame(out, columns=columns).sort_values(groups).reset_index(drop=True)


def apply_account(
    rows: list[dict[str, Any]],
    starting_balance: float,
    risk_pct: float,
    max_trades_per_day: int,
    max_daily_loss_pct: float,
    max_drawdown_pct: float,
) -> tuple[dict[str, Any], pd.DataFrame]:
    if not rows:
        return {
            "starting_balance": round(starting_balance, 2),
            "ending_balance": round(starting_balance, 2),
            "net_profit": 0.0,
            "return_pct": 0.0,
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "net_r": 0.0,
            "max_drawdown_pct": 0.0,
        }, pd.DataFrame()

    balance = float(starting_balance)
    peak = balance
    max_drawdown = 0.0
    daily_trades: dict[str, int] = {}
    daily_pnl: dict[str, float] = {}
    open_until: dict[str, datetime] = {}
    applied: list[dict[str, Any]] = []
    pending: list[tuple[datetime, int, dict[str, Any]]] = []
    skipped_guardrail = 0
    skipped_overlap = 0
    sequence = 0

    def settle(until: datetime | None = None) -> None:
        nonlocal balance, peak, max_drawdown
        while pending and (until is None or pending[0][0] <= until):
            closed_at, _sequence, item = heapq.heappop(pending)
            before = balance
            pnl = float(item["pnl"])
            balance = max(0.0, balance + pnl)
            peak = max(peak, balance)
            max_drawdown = max(max_drawdown, (peak - balance) / peak if peak else 0.0)
            daily_key = closed_at.date().isoformat()
            daily_pnl[daily_key] = daily_pnl.get(daily_key, 0.0) + pnl
            item["balance_before_settlement"] = round(before, 2)
            item["balance_after"] = round(balance, 2)
            applied.append(item)

    for row in sorted(rows, key=lambda item: (str(item["opened_at"]), str(item["bot"]), str(item["symbol"]))):
        opened_at = datetime.fromisoformat(str(row["opened_at"]))
        closed_at = datetime.fromisoformat(str(row["closed_at"]))
        settle(opened_at)
        day_key = opened_at.date().isoformat()
        current_dd_pct = (peak - balance) / peak * 100 if peak > 0 else 0.0
        if open_until.get(str(row["symbol"]), datetime.min) > opened_at:
            skipped_overlap += 1
            continue
        if max_drawdown_pct > 0 and current_dd_pct >= max_drawdown_pct:
            skipped_guardrail += 1
            continue
        if max_trades_per_day > 0 and daily_trades.get(day_key, 0) >= max_trades_per_day:
            skipped_guardrail += 1
            continue
        if max_daily_loss_pct > 0 and daily_pnl.get(day_key, 0.0) <= -(balance * max_daily_loss_pct / 100):
            skipped_guardrail += 1
            continue

        risk_amount = balance * risk_pct / 100
        item = dict(row)
        item.update(
            {
                "balance_at_entry": round(balance, 2),
                "risk_amount": round(risk_amount, 2),
                "pnl": round(risk_amount * float(row["r_multiple"]), 2),
            }
        )
        daily_trades[day_key] = daily_trades.get(day_key, 0) + 1
        open_until[str(row["symbol"])] = closed_at
        sequence += 1
        heapq.heappush(pending, (closed_at, sequence, item))

    settle()

    wins = sum(1 for item in applied if float(item["r_multiple"]) > 0)
    losses = sum(1 for item in applied if float(item["r_multiple"]) < 0)
    summary = {
        "starting_balance": round(starting_balance, 2),
        "ending_balance": round(balance, 2),
        "net_profit": round(balance - starting_balance, 2),
        "return_pct": round((balance / starting_balance - 1) * 100, 2) if starting_balance else 0.0,
        "trades": len(applied),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(applied) * 100, 2) if applied else 0.0,
        "net_r": round(sum(float(item["r_multiple"]) for item in applied), 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "skipped_guardrail": skipped_guardrail,
        "skipped_same_symbol_overlap": skipped_overlap,
    }
    return summary, pd.DataFrame(applied)


def collect_lta_candidates(
    client: MT5Client,
    symbols: tuple[str, ...],
    timeframes: tuple[str, ...],
    start: datetime,
    end: datetime,
    min_score: int,
    min_rr: float,
    stride: int,
    lookback_bars: int,
    rr_map: dict[str, float],
    allowed_sessions: list[tuple[int, int, str]],
    session_timezone: str,
    data_timezone: str,
    market_data: dict[str, pd.DataFrame],
) -> tuple[list[Candidate], list[dict[str, Any]]]:
    candidates: list[Candidate] = []
    availability: list[dict[str, Any]] = []
    fetch_start = start - timedelta(days=45)
    for symbol in symbols:
        resolved = client.resolve_symbol(symbol)
        if not resolved:
            availability.append({"bot": "LTA", "symbol": symbol, "timeframe": None, "status": "unavailable", "candles": 0})
            continue
        for timeframe in timeframes:
            candles = client.fetch_candles(symbol, timeframe, fetch_start, end, max_bars=200000)
            count = 0 if candles is None else len(candles)
            if candles is None or count < 160:
                availability.append({"bot": "LTA", "symbol": symbol, "timeframe": timeframe, "status": "not_enough_data", "candles": count})
                continue
            df = add_atr_columns(normalize_candles(candles))
            key = f"LTA:{symbol}:{timeframe}"
            market_data[key] = df
            availability.append({"bot": "LTA", "symbol": symbol, "timeframe": timeframe, "status": "ok", "candles": len(df), "broker_symbol": resolved})
            log(f"LTA {symbol} {timeframe}: scanning {len(df)} candles")
            start_index = max(120, min(240, len(df) // 5))
            i = start_index
            while i < len(df) - 2:
                candle_time = pd.Timestamp(df.iloc[i]["time"]).to_pydatetime()
                if candle_time < start:
                    i += stride
                    continue
                if candle_time > end:
                    break
                if date_in_timezone(candle_time, data_timezone, session_timezone).weekday() >= 5:
                    i += stride
                    continue
                if not in_allowed_sessions(candle_time, allowed_sessions, data_timezone, session_timezone):
                    i += stride
                    continue
                context_start = max(0, i + 1 - lookback_bars)
                signal = generate_signal(
                    df.iloc[context_start : i + 1],
                    symbol=symbol,
                    timeframe=timeframe,
                    min_score=min_score,
                    min_rr=min_rr,
                )
                if signal and signal.get("status") == "allowed":
                    if not passes_strict_session_gate(signal, candle_time, data_timezone, session_timezone):
                        i += stride
                        continue
                    entry = float(signal.get("entry") or 0.0)
                    stop = float(signal.get("stop_loss") or 0.0)
                    direction = str(signal.get("direction") or "").upper()
                    atr_value = float(df.iloc[i].get("atr") or abs(entry - stop))
                    if entry > 0 and stop > 0 and direction in {"BUY", "SELL"} and atr_value > 0:
                        candidates.append(
                            Candidate(
                                bot="LTA",
                                symbol=symbol,
                                timeframe=timeframe,
                                series_key=key,
                                start_index=i + 1,
                                opened_at=candle_time,
                                direction=direction,
                                entry=entry,
                                base_stop=stop,
                                configured_rr=current_rr(symbol, min_rr, rr_map),
                                setup_score=int(signal.get("setup_score") or 0),
                                atr=atr_value,
                                atr_percentile=float(df.iloc[i].get("atr_percentile") or 0.5),
                                session_metric=None,
                                entry_model=str(signal.get("entry_model") or ""),
                            )
                        )
                i += stride
            log(f"LTA {symbol} {timeframe}: candidates={sum(1 for item in candidates if item.series_key == key)}")
    return candidates, availability


def collect_orb_candidates(
    client: MT5Client,
    symbols: tuple[str, ...],
    start: datetime,
    end: datetime,
    settings: ORBSettings,
    rr_map: dict[str, float],
    market_data: dict[str, pd.DataFrame],
) -> tuple[list[Candidate], list[dict[str, Any]], list[dict[str, Any]]]:
    candidates: list[Candidate] = []
    availability: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    fetch_start = start - timedelta(days=10)
    for symbol in symbols:
        resolved = client.resolve_symbol(symbol)
        if not resolved:
            availability.append({"bot": "ORB", "symbol": symbol, "timeframe": "M15", "status": "unavailable", "candles": 0})
            continue
        candles = client.fetch_candles(symbol, "M15", fetch_start, end, max_bars=200000)
        count = 0 if candles is None else len(candles)
        if candles is None or count < 120:
            availability.append({"bot": "ORB", "symbol": symbol, "timeframe": "M15", "status": "not_enough_data", "candles": count})
            continue
        df = add_atr_columns(normalize_candles(candles))
        key = f"ORB:{symbol}:M15"
        market_data[key] = df
        availability.append({"bot": "ORB", "symbol": symbol, "timeframe": "M15", "status": "ok", "candles": len(df), "broker_symbol": resolved})
        days = sorted(
            {
                date_in_timezone(pd.Timestamp(value).to_pydatetime(), settings.data_timezone, settings.session_timezone)
                for value in df["time"]
            }
        )
        log(f"ORB {symbol}: scanning {len(days)} session days")
        for session_day in days:
            if session_day.weekday() >= 5:
                continue
            session_start, range_end, session_end = orb_session_bounds(session_day, settings)
            if session_end < start or session_start > end:
                continue
            needed_bars = max(1, int(settings.range_minutes // TIMEFRAME_MINUTES["M15"]))
            range_bars = df[(df["time"] >= session_start) & (df["time"] < range_end)]
            if len(range_bars) < needed_bars:
                continue
            prior = df[df["time"] < session_start].tail(64)
            atr_value = orb_atr(prior, 14)
            range_high = float(range_bars["high"].max())
            range_low = float(range_bars["low"].min())
            range_width = range_high - range_low
            if range_width <= 0:
                continue
            range_atr = range_width / atr_value if atr_value > 0 else None
            if range_atr is not None and range_atr < settings.min_range_atr:
                continue
            if range_atr is not None and range_atr > settings.max_range_atr:
                continue
            buffer = max(0.0, settings.buffer_atr) * max(0.0, atr_value)
            buy_trigger = range_high + buffer
            sell_trigger = range_low - buffer
            post = df[(df["time"] >= range_end) & (df["time"] <= session_end)]
            for index, row in post.iterrows():
                high = float(row["high"])
                low = float(row["low"])
                hit_buy = high >= buy_trigger
                hit_sell = low <= sell_trigger
                if hit_buy and hit_sell:
                    skipped.append({"bot": "ORB", "symbol": symbol, "date": session_day.isoformat(), "reason": "ambiguous_breakout"})
                    break
                if hit_buy or hit_sell:
                    direction = "BUY" if hit_buy else "SELL"
                    entry = buy_trigger if hit_buy else sell_trigger
                    stop = range_low if hit_buy else range_high
                    opened_at = pd.Timestamp(row["time"]).to_pydatetime()
                    if opened_at < start or opened_at > end:
                        break
                    score = 100 if range_atr is not None and 0.5 <= range_atr <= 2.0 else 95
                    atr_pct = float(df.iloc[int(index)].get("atr_percentile") or 0.5)
                    candidates.append(
                        Candidate(
                            bot="ORB",
                            symbol=symbol,
                            timeframe="M15",
                            series_key=key,
                            start_index=int(index),
                            opened_at=opened_at,
                            direction=direction,
                            entry=float(entry),
                            base_stop=float(stop),
                            configured_rr=current_rr(symbol, settings.reward_risk, rr_map),
                            setup_score=score,
                            atr=max(float(atr_value), abs(float(entry) - float(stop))),
                            atr_percentile=atr_pct,
                            session_metric=range_atr,
                            entry_model=f"ORB {settings.range_minutes}m breakout",
                        )
                    )
                    break
        log(f"ORB {symbol}: candidates={sum(1 for item in candidates if item.series_key == key)}")
    return candidates, availability, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare fixed RR exits against ATR/regime dynamic exits.")
    parser.add_argument("--start", default=None, help="YYYY-MM-DD. Defaults to end minus --days.")
    parser.add_argument("--end", default=None, help="YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--days", type=int, default=31)
    parser.add_argument("--balance", type=float, default=300.0)
    parser.add_argument("--risk-pct", type=float, default=5.0)
    parser.add_argument("--max-holding-bars", type=int, default=96)
    parser.add_argument("--lookback-bars", type=int, default=500)
    parser.add_argument("--skip-orb", action="store_true", help="Validate only LTA candidates.")
    args = parser.parse_args()

    config = load_config()
    end_day = date.fromisoformat(args.end) if args.end else date.today()
    start_day = date.fromisoformat(args.start) if args.start else end_day - timedelta(days=max(1, int(args.days)))
    start = datetime.combine(start_day, time.min)
    end = datetime.combine(end_day, time.max)

    lta_symbols = parse_csv(os.getenv("AUTO_SYMBOLS"), DEFAULT_LTA_SYMBOLS)
    lta_timeframes = parse_csv(os.getenv("AUTO_SCAN_TIMEFRAMES"), DEFAULT_LTA_TIMEFRAMES)
    orb_symbols = () if args.skip_orb else parse_csv(os.getenv("ORB_SYMBOLS"), DEFAULT_ORB_SYMBOLS)
    auto_rr = parse_rr_map(os.getenv("AUTO_SYMBOL_RR"))
    orb_rr = parse_rr_map(os.getenv("ORB_SYMBOL_RR"))
    allowed_sessions = parse_sessions(os.getenv("AUTO_ALLOWED_SESSIONS"))
    session_timezone = os.getenv("MARKET_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE)
    data_timezone = os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE)

    orb_settings = ORBSettings(
        session_start=os.getenv("ORB_SESSION_START", "09:30"),
        session_end=os.getenv("ORB_SESSION_END", "16:00"),
        range_minutes=int(os.getenv("ORB_RANGE_MINUTES", "15") or 15),
        reward_risk=float(os.getenv("ORB_RR", "3") or 3.0),
        buffer_atr=float(os.getenv("ORB_BREAK_BUFFER_ATR", "0") or 0.0),
        min_range_atr=float(os.getenv("ORB_MIN_RANGE_ATR", "0") or 0.0),
        max_range_atr=float(os.getenv("ORB_MAX_RANGE_ATR", "999") or 999.0),
        session_timezone=os.getenv("ORB_SESSION_TIMEZONE", session_timezone),
        data_timezone=data_timezone,
    )

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = REPORTS_DIR / "dynamic_exit_backtest" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    client = MT5Client()
    status = client.terminal_status()
    log(f"MT5 status: {status.get('message')}")
    log(f"Window: {start.date()} to {end.date()} | balance=${args.balance:g} | risk={args.risk_pct:g}%")
    log(f"LTA: {', '.join(lta_symbols)} on {', '.join(lta_timeframes)}")
    if orb_symbols:
        log(f"ORB: {', '.join(orb_symbols)} | {orb_settings.session_start}-{orb_settings.session_end} {orb_settings.session_timezone}")
    else:
        log("ORB: skipped")

    market_data: dict[str, pd.DataFrame] = {}
    lta_candidates, lta_availability = collect_lta_candidates(
        client,
        lta_symbols,
        lta_timeframes,
        start,
        end,
        min_score=int(os.getenv("MIN_SETUP_SCORE", str(config.min_setup_score)) or config.min_setup_score),
        min_rr=float(os.getenv("MIN_RISK_REWARD", str(config.min_risk_reward)) or config.min_risk_reward),
        stride=max(1, int(os.getenv("BACKTEST_SIGNAL_STRIDE", str(config.backtest_signal_stride)) or config.backtest_signal_stride)),
        lookback_bars=max(120, int(args.lookback_bars)),
        rr_map=auto_rr,
        allowed_sessions=allowed_sessions,
        session_timezone=session_timezone,
        data_timezone=data_timezone,
        market_data=market_data,
    )
    orb_candidates, orb_availability, orb_skipped = collect_orb_candidates(
        client,
        orb_symbols,
        start,
        end,
        orb_settings,
        orb_rr,
        market_data,
    )
    client.shutdown()

    all_candidates = [*lta_candidates, *orb_candidates]
    log(f"Total candidates: {len(all_candidates)}")

    policy_rows: list[dict[str, Any]] = []
    for policy in POLICIES:
        for candidate in all_candidates:
            df = market_data[candidate.series_key]
            trade = simulate_managed_trade(df, candidate, policy, int(args.max_holding_bars), partial_fraction=0.0)
            if trade:
                policy_rows.append(asdict(trade))

    trades_frame = pd.DataFrame(policy_rows)
    trades_path = out_dir / "dynamic_exit_trades.csv"
    trades_frame.to_csv(trades_path, index=False)

    candidate_path = out_dir / "candidates.csv"
    pd.DataFrame([asdict(item) for item in all_candidates]).to_csv(candidate_path, index=False)

    availability_path = out_dir / "availability.csv"
    pd.DataFrame([*lta_availability, *orb_availability]).to_csv(availability_path, index=False)

    skipped_path = out_dir / "skipped.csv"
    pd.DataFrame(orb_skipped).to_csv(skipped_path, index=False)

    policy_summary = summarize_trades(policy_rows, ["policy"])
    bot_policy_summary = summarize_trades(policy_rows, ["policy", "bot"])
    symbol_policy_summary = summarize_trades(policy_rows, ["policy", "bot", "symbol"])
    monthly_summary = summarize_trades(policy_rows, ["policy", "bot", "symbol", "month"])

    policy_summary_path = out_dir / "policy_summary.csv"
    bot_summary_path = out_dir / "bot_policy_summary.csv"
    symbol_summary_path = out_dir / "symbol_policy_summary.csv"
    monthly_summary_path = out_dir / "monthly_policy_symbol_summary.csv"
    policy_summary.to_csv(policy_summary_path, index=False)
    bot_policy_summary.to_csv(bot_summary_path, index=False)
    symbol_policy_summary.to_csv(symbol_summary_path, index=False)
    monthly_summary.to_csv(monthly_summary_path, index=False)

    account_summaries: list[dict[str, Any]] = []
    account_paths: dict[str, str] = {}
    max_daily_trades = int(os.getenv("MAX_TRADES_PER_DAY", "2") or 2)
    max_daily_loss = float(os.getenv("MAX_DAILY_LOSS_PERCENT", "5") or 5.0)
    max_drawdown = float(os.getenv("MAX_TOTAL_DRAWDOWN_PERCENT", "10") or 10.0)
    for policy in [item["name"] for item in POLICIES]:
        rows = [row for row in policy_rows if row["policy"] == policy]
        summary, account_frame = apply_account(
            rows,
            starting_balance=float(args.balance),
            risk_pct=float(args.risk_pct),
            max_trades_per_day=max_daily_trades,
            max_daily_loss_pct=max_daily_loss,
            max_drawdown_pct=max_drawdown,
        )
        summary["policy"] = policy
        account_summaries.append(summary)
        account_path = out_dir / f"account_{policy}.csv"
        account_frame.to_csv(account_path, index=False)
        account_paths[policy] = str(account_path)
    account_summaries.sort(key=lambda item: (float(item["ending_balance"]), float(item["net_r"])), reverse=True)
    account_summary_path = out_dir / "account_policy_summary.csv"
    pd.DataFrame(account_summaries).to_csv(account_summary_path, index=False)

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "window_start": start.isoformat(sep=" ", timespec="seconds"),
        "window_end": end.isoformat(sep=" ", timespec="seconds"),
        "starting_balance": float(args.balance),
        "risk_pct": float(args.risk_pct),
        "model_notes": [
            "A+ entry candidates use the current LTA/ORB watchlists and sessions from .env.",
            "No position is partially closed at TP1. SL moves to break-even at TP1, then to TP(n-1) after TPn.",
            "production_current mirrors the live ATR/volume adaptive stop and confirmation-based smart invalidation exit.",
            "Dynamic stops use ATR/volume regimes; lot/risk is represented in R-multiples and compounded at the requested account risk.",
            "This is a research backtest. Live spread, slippage, broker minimum lot, and order filling can change actual results.",
        ],
        "policies": list(POLICIES),
        "candidate_count": len(all_candidates),
        "lta_candidate_count": len(lta_candidates),
        "orb_candidate_count": len(orb_candidates),
        "best_account_policy": account_summaries[0] if account_summaries else None,
        "account_summaries": account_summaries,
        "policy_summary": policy_summary.to_dict(orient="records"),
        "bot_policy_summary": bot_policy_summary.to_dict(orient="records"),
        "paths": {
            "trades": str(trades_path),
            "candidates": str(candidate_path),
            "availability": str(availability_path),
            "skipped": str(skipped_path),
            "policy_summary": str(policy_summary_path),
            "bot_policy_summary": str(bot_summary_path),
            "symbol_policy_summary": str(symbol_summary_path),
            "monthly_policy_symbol_summary": str(monthly_summary_path),
            "account_policy_summary": str(account_summary_path),
            "account_equity_by_policy": account_paths,
        },
    }
    report_path = out_dir / "dynamic_exit_backtest_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    log(f"Done. Report: {report_path}")
    print(json.dumps({"report": str(report_path), "best": report["best_account_policy"], "account_summaries": account_summaries}, indent=2), flush=True)


if __name__ == "__main__":
    main()
