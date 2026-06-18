from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Profile:
    poc: float
    vah: float
    val: float


def _to_frame(candles: pd.DataFrame) -> pd.DataFrame:
    df = candles.copy()
    df["time"] = pd.to_datetime(df["time"])
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" not in df.columns:
        df["volume"] = 1.0
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(1.0).clip(lower=1.0)
    return df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)


def _atr(df: pd.DataFrame, period: int = 14) -> float:
    if len(df) < 2:
        return float((df["high"].iloc[-1] - df["low"].iloc[-1]) or df["close"].iloc[-1] * 0.001)
    high = df["high"]
    low = df["low"]
    close = df["close"]
    prev_close = close.shift(1)
    tr = pd.concat([(high - low), (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    value = float(tr.tail(period).mean())
    if not np.isfinite(value) or value <= 0:
        value = float(close.iloc[-1] * 0.001)
    return value


def _volume_profile(df: pd.DataFrame, bins: int = 48, value_area: float = 0.70) -> Profile | None:
    if len(df) < 8:
        return None
    low = float(df["low"].min())
    high = float(df["high"].max())
    if high <= low:
        return None
    bins = min(max(16, bins), 96)
    weights = df["volume"].to_numpy(dtype=float)
    closes = df["close"].to_numpy(dtype=float)
    hist, edges = np.histogram(closes, bins=bins, range=(low, high), weights=weights)
    if hist.sum() <= 0:
        return None
    centers = (edges[:-1] + edges[1:]) / 2
    poc_idx = int(np.argmax(hist))
    ranked = np.argsort(hist)[::-1]
    selected: list[int] = []
    total = 0.0
    target = float(hist.sum() * value_area)
    for idx in ranked:
        selected.append(int(idx))
        total += float(hist[idx])
        if total >= target:
            break
    selected_centers = centers[selected]
    return Profile(
        poc=float(centers[poc_idx]),
        vah=float(np.max(selected_centers)),
        val=float(np.min(selected_centers)),
    )


def _session_name(timestamp: datetime) -> str:
    hour = timestamp.hour + timestamp.minute / 60
    if 8 <= hour < 17:
        return "New York"
    if 3 <= hour < 12:
        return "London"
    if hour >= 19 or hour < 2:
        return "Asia"
    return "Off-session"


def _candle_parts(row: pd.Series) -> dict[str, float]:
    high = float(row["high"])
    low = float(row["low"])
    open_ = float(row["open"])
    close = float(row["close"])
    rng = max(high - low, 1e-9)
    body_high = max(open_, close)
    body_low = min(open_, close)
    return {
        "range": rng,
        "upper_wick": (high - body_high) / rng,
        "lower_wick": (body_low - low) / rng,
        "body": abs(close - open_) / rng,
    }


def detect_bias(candles: pd.DataFrame, timeframe: str = "M15") -> str:
    df = _to_frame(candles)
    if len(df) < 40:
        return "unclear"
    close = df["close"]
    fast = close.rolling(20).mean().iloc[-1]
    slow = close.rolling(50).mean().iloc[-1] if len(df) >= 50 else close.rolling(30).mean().iloc[-1]
    slope = close.iloc[-1] - close.iloc[-20]
    atr = _atr(df)
    if fast > slow and slope > atr:
        return "bullish"
    if fast < slow and slope < -atr:
        return "bearish"
    return "ranging"


def detect_market_structure(candles: pd.DataFrame) -> dict[str, Any]:
    df = _to_frame(candles)
    if len(df) < 30:
        return {"structure": "unclear", "details": "Not enough candles."}
    recent = df.tail(40)
    first = recent.head(20)
    last = recent.tail(20)
    higher_high = float(last["high"].max()) > float(first["high"].max())
    higher_low = float(last["low"].min()) > float(first["low"].min())
    lower_high = float(last["high"].max()) < float(first["high"].max())
    lower_low = float(last["low"].min()) < float(first["low"].min())
    if higher_high and higher_low:
        return {"structure": "bullish", "details": "Recent range is making higher highs and higher lows."}
    if lower_high and lower_low:
        return {"structure": "bearish", "details": "Recent range is making lower highs and lower lows."}
    return {"structure": "ranging", "details": "Recent range is mixed or consolidating."}


def _week_id(series: pd.Series) -> pd.Series:
    iso = series.dt.isocalendar()
    return iso["year"].astype(str) + "-" + iso["week"].astype(str).str.zfill(2)


def _add_profile_levels(levels: list[dict[str, Any]], profile: Profile | None, profile_type: str, prefix: str, priority: int) -> None:
    if profile is None:
        return
    levels.extend(
        [
            {"profile_type": profile_type, "key_level": f"{prefix} PoC", "kind": "PoC", "price": profile.poc, "priority": priority},
            {"profile_type": profile_type, "key_level": f"{prefix} VaH", "kind": "VaH", "price": profile.vah, "priority": priority - 1},
            {"profile_type": profile_type, "key_level": f"{prefix} VaL", "kind": "VaL", "price": profile.val, "priority": priority - 1},
        ]
    )


def _candidate_levels(df: pd.DataFrame) -> list[dict[str, Any]]:
    levels: list[dict[str, Any]] = []
    if len(df) < 60:
        return levels

    dates = df["time"].dt.date
    current_date = dates.iloc[-1]
    previous_dates = sorted({d for d in dates.unique() if d < current_date})
    if previous_dates:
        prev_day = df[dates == previous_dates[-1]]
        _add_profile_levels(levels, _volume_profile(prev_day), "Previous Daily", "PD", 18)
    if len(previous_dates) >= 2:
        early_day = df[dates == previous_dates[-2]]
        _add_profile_levels(levels, _volume_profile(early_day), "Early Previous Daily", "EPD", 14)

    weeks = _week_id(df["time"])
    current_week = weeks.iloc[-1]
    previous_weeks = list(dict.fromkeys(weeks[weeks != current_week].tolist()))
    if previous_weeks:
        prev_week_id = previous_weeks[-1]
        prev_week = df[weeks == prev_week_id]
        _add_profile_levels(levels, _volume_profile(prev_week), "Previous Weekly", "PW", 20)
    current_week_df = df[weeks == current_week]
    if len(current_week_df) >= 80:
        _add_profile_levels(levels, _volume_profile(current_week_df), "Current Weekly", "CW", 17)

    fixed = df.tail(min(120, len(df)))
    recent_range = float(fixed["high"].max() - fixed["low"].min())
    atr = _atr(df)
    if recent_range <= atr * 18:
        _add_profile_levels(levels, _volume_profile(fixed), "Fixed Range", "Fixed", 16)

    swing = df.tail(min(180, len(df)))
    _add_profile_levels(levels, _volume_profile(swing), "Swing", "Swing", 15)
    return levels


def detect_aoi(candles: pd.DataFrame) -> dict[str, Any] | None:
    df = _to_frame(candles)
    if len(df) < 60:
        return None
    current = df.iloc[-1]
    atr = _atr(df)
    tolerance = max(atr * 0.45, abs(float(current["close"])) * 0.00035)
    levels = _candidate_levels(df)
    touched: list[dict[str, Any]] = []
    for level in levels:
        price = float(level["price"])
        in_candle = float(current["low"]) - tolerance <= price <= float(current["high"]) + tolerance
        near_close = abs(float(current["close"]) - price) <= tolerance
        if in_candle or near_close:
            confluence = 1 + sum(
                1
                for other in levels
                if other is not level and abs(float(other["price"]) - price) <= tolerance
            )
            item = dict(level)
            item["confluence"] = confluence
            item["tolerance"] = tolerance
            touched.append(item)
    if not touched:
        return None
    touched.sort(key=lambda x: (x["confluence"], x["priority"]), reverse=True)
    return touched[0]


def _liquidity_context(df: pd.DataFrame, direction: str) -> tuple[bool, str]:
    if len(df) < 25:
        return False, "Not enough candles to confirm liquidity buildup."
    recent = df.tail(16)
    atr = _atr(df)
    if direction == "BUY":
        lows = recent["low"].tail(8)
        equal_lows = lows.max() - lows.min() <= atr * 0.8
        swept = recent["low"].iloc[-2] <= recent["low"].head(12).min()
        if swept:
            return True, "Sell-side liquidity was swept before the bullish reaction."
        if equal_lows:
            return True, "Sell-side liquidity was built through clustered lows."
    else:
        highs = recent["high"].tail(8)
        equal_highs = highs.max() - highs.min() <= atr * 0.8
        swept = recent["high"].iloc[-2] >= recent["high"].head(12).max()
        if swept:
            return True, "Buy-side liquidity was swept before the bearish reaction."
        if equal_highs:
            return True, "Buy-side liquidity was built through clustered highs."
    return False, "Liquidity buildup or sweep is not clear."


def detect_entry_confirmation(candles: pd.DataFrame, level: dict[str, Any] | None = None, direction: str | None = None) -> dict[str, Any]:
    df = _to_frame(candles)
    if level is None or direction is None or len(df) < 8:
        return {"confirmed": False, "model": None, "reasons": ["Missing level, direction, or candle history."]}

    current = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    level_price = float(level["price"])
    tolerance = float(level.get("tolerance") or _atr(df) * 0.45)
    reasons: list[str] = []
    models: list[str] = []

    prev_parts = _candle_parts(prev)
    current_parts = _candle_parts(current)
    prev_touched = float(prev["low"]) - tolerance <= level_price <= float(prev["high"]) + tolerance
    current_touched = float(current["low"]) - tolerance <= level_price <= float(current["high"]) + tolerance

    if direction == "BUY":
        double_wick = (
            prev_touched
            and current_touched
            and (prev_parts["lower_wick"] >= 0.28 or current_parts["lower_wick"] >= 0.28)
            and float(current["close"]) > float(current["open"])
            and float(current["close"]) > max(float(prev["open"]), float(prev["close"]))
        )
        if double_wick:
            models.append("Entry Model 1 - Double Wick Confirmation")
            reasons.append("Bullish double wick and candle flip confirmed at the key level.")

        prior = df.iloc[-12:-3]
        swept_low = float(prev["low"]) <= float(prior["low"].min()) if len(prior) else False
        broke_internal = float(current["close"]) > max(float(prev["high"]), float(prev2["high"]))
        reclaimed = float(current["close"]) > level_price
        if swept_low and broke_internal and reclaimed:
            models.append("Entry Model 3 - Confirmation of Internal Structure")
            reasons.append("Sell-side manipulation reversed and broke internal highs.")

    else:
        double_wick = (
            prev_touched
            and current_touched
            and (prev_parts["upper_wick"] >= 0.28 or current_parts["upper_wick"] >= 0.28)
            and float(current["close"]) < float(current["open"])
            and float(current["close"]) < min(float(prev["open"]), float(prev["close"]))
        )
        if double_wick:
            models.append("Entry Model 1 - Double Wick Confirmation")
            reasons.append("Bearish double wick and candle flip confirmed at the key level.")

        prior = df.iloc[-12:-3]
        swept_high = float(prev["high"]) >= float(prior["high"].max()) if len(prior) else False
        broke_internal = float(current["close"]) < min(float(prev["low"]), float(prev2["low"]))
        rejected = float(current["close"]) < level_price
        if swept_high and broke_internal and rejected:
            models.append("Entry Model 3 - Confirmation of Internal Structure")
            reasons.append("Buy-side manipulation reversed and broke internal lows.")

    if not models and len(df) >= 40:
        reaction = df.tail(24)
        reaction_start = reaction.iloc[0]
        if direction == "BUY" and float(reaction["low"].min()) <= level_price + tolerance:
            swing_profile = _volume_profile(reaction)
            if swing_profile and abs(float(current["low"]) - swing_profile.poc) <= tolerance and float(current["close"]) > float(current["open"]):
                models.append("Entry Model 2 - Internal Swing Confirmation")
                reasons.append("LTF swing profile retest confirmed after the initial bullish reaction.")
        if direction == "SELL" and float(reaction["high"].max()) >= level_price - tolerance:
            swing_profile = _volume_profile(reaction)
            if swing_profile and abs(float(current["high"]) - swing_profile.poc) <= tolerance and float(current["close"]) < float(current["open"]):
                models.append("Entry Model 2 - Internal Swing Confirmation")
                reasons.append("LTF swing profile retest confirmed after the initial bearish reaction.")

    if models:
        model = " + ".join(dict.fromkeys(models))
        return {"confirmed": True, "model": model, "reasons": reasons}
    return {"confirmed": False, "model": None, "reasons": ["No official LTA entry model confirmed yet."]}


def _direction_from_reaction(df: pd.DataFrame, level: dict[str, Any]) -> str | None:
    current = df.iloc[-1]
    price = float(level["price"])
    close = float(current["close"])
    open_ = float(current["open"])
    if float(current["low"]) <= price <= close and close > open_:
        return "BUY"
    if close <= price <= float(current["high"]) and close < open_:
        return "SELL"
    if close > price and _candle_parts(current)["lower_wick"] > 0.35:
        return "BUY"
    if close < price and _candle_parts(current)["upper_wick"] > 0.35:
        return "SELL"
    return None


def _build_trade_levels(df: pd.DataFrame, direction: str, min_rr: float) -> tuple[float, float, float, float]:
    current = df.iloc[-1]
    entry = float(current["close"])
    atr = _atr(df)
    recent = df.tail(8)
    if direction == "BUY":
        stop = float(recent["low"].min()) - atr * 0.15
        risk = max(entry - stop, atr * 0.25)
        stop = entry - risk
        target = entry + risk * max(min_rr, 5.0)
    else:
        stop = float(recent["high"].max()) + atr * 0.15
        risk = max(stop - entry, atr * 0.25)
        stop = entry + risk
        target = entry - risk * max(min_rr, 5.0)
    rr = abs(target - entry) / max(abs(entry - stop), 1e-9)
    return entry, stop, target, rr


def _profit_targets(entry: float, stop: float, direction: str, final_rr: float = 5.0) -> dict[str, float]:
    risk = abs(entry - stop)
    stages = range(1, int(max(1, round(final_rr))) + 1)
    if direction == "BUY":
        return {f"tp{stage}": entry + risk * stage for stage in stages}
    return {f"tp{stage}": entry - risk * stage for stage in stages}


def _recent_aoi(candles: pd.DataFrame, lookback: int = 12) -> dict[str, Any] | None:
    df = _to_frame(candles)
    level = detect_aoi(df)
    if level:
        current = df.iloc[-1]
        item = dict(level)
        item["touched_recent"] = True
        item["distance_from_close"] = abs(float(current["close"]) - float(level["price"]))
        return item

    if len(df) < 60:
        return None
    current = df.iloc[-1]
    close = float(current["close"])
    atr = _atr(df)
    tolerance = max(atr * 0.55, abs(close) * 0.00045)
    max_distance = max(atr * 4.0, abs(close) * 0.0025)
    levels = _candidate_levels(df)
    recent = df.tail(lookback)
    touched: list[dict[str, Any]] = []

    for level in levels:
        price = float(level["price"])
        touched_recent = float(recent["low"].min()) - tolerance <= price <= float(recent["high"].max()) + tolerance
        distance = abs(close - price)
        if not touched_recent or distance > max_distance:
            continue
        confluence = 1 + sum(
            1
            for other in levels
            if other is not level and abs(float(other["price"]) - price) <= tolerance
        )
        item = dict(level)
        item["confluence"] = confluence
        item["tolerance"] = tolerance
        item["touched_recent"] = True
        item["distance_from_close"] = distance
        touched.append(item)

    if not touched:
        return None
    touched.sort(key=lambda item: (item["confluence"], item["priority"], -item["distance_from_close"]), reverse=True)
    return touched[0]


def _preentry_direction(df: pd.DataFrame, level: dict[str, Any]) -> str | None:
    direction = _direction_from_reaction(df, level)
    if direction:
        return direction

    current = df.iloc[-1]
    recent = df.tail(12)
    price = float(level["price"])
    tolerance = float(level.get("tolerance") or _atr(df) * 0.45)
    close = float(current["close"])
    bias = detect_bias(df)
    touched_support = float(recent["low"].min()) <= price + tolerance and close >= price
    touched_resistance = float(recent["high"].max()) >= price - tolerance and close <= price

    if touched_support and not touched_resistance:
        return "BUY"
    if touched_resistance and not touched_support:
        return "SELL"
    if close > price and bias in {"bullish", "ranging"}:
        return "BUY"
    if close < price and bias in {"bearish", "ranging"}:
        return "SELL"
    if close > price:
        return "BUY"
    if close < price:
        return "SELL"
    return None


def _score_preentry_candidate(
    df: pd.DataFrame,
    level: dict[str, Any],
    direction: str,
    trigger_price: float,
    stop_loss: float,
    risk_reward: float,
    min_rr: float,
    mode: str,
    timeframe: str,
) -> tuple[int, list[str], dict[str, Any]]:
    current = df.iloc[-1]
    atr = _atr(df)
    close = float(current["close"])
    bias = detect_bias(df, timeframe)
    structure = detect_market_structure(df)
    liquidity_ok, liquidity_reason = _liquidity_context(df, direction)
    session = _session_name(pd.Timestamp(current["time"]).to_pydatetime())
    trigger_distance = abs(trigger_price - close)
    stop_clear = trigger_price > stop_loss if direction == "BUY" else trigger_price < stop_loss

    score = 0
    reasons: list[str] = []
    score += min(20, int(level.get("priority", 10)))
    reasons.append(f"Price recently reacted around {level['key_level']} ({level['profile_type']}).")
    if int(level.get("confluence") or 1) >= 2:
        score += 5
        reasons.append("The pending level has volume-profile confluence.")

    if (bias == "bullish" and direction == "BUY") or (bias == "bearish" and direction == "SELL"):
        score += 15
        reasons.append("Pending direction aligns with the higher-timeframe bias.")
    elif bias == "ranging":
        score += 8
        reasons.append("Range conditions allow a level-to-level reaction setup.")
    else:
        reasons.append("Higher-timeframe bias is not fully aligned yet.")

    if (structure.get("structure") == "bullish" and direction == "BUY") or (
        structure.get("structure") == "bearish" and direction == "SELL"
    ):
        score += 10
        reasons.append(structure.get("details") or "Market structure supports the pending direction.")
    elif structure.get("structure") == "ranging":
        score += 5
        reasons.append("Structure is ranging, so confirmation trigger is required.")

    if liquidity_ok:
        score += 15
        reasons.append(liquidity_reason)
    else:
        reasons.append(liquidity_reason)

    if mode == "structure_break":
        score += 12
        reasons.append("Pending stop is placed only at the internal break/reclaim trigger.")
    else:
        score += 8
        reasons.append("Pending limit is placed at the LTF swing profile retest area after the first reaction.")

    if stop_clear:
        score += 10
        reasons.append("Stop loss is beyond the reacted structure, not inside the noise.")
    else:
        reasons.append("Stop loss is not structurally clear enough.")

    if risk_reward >= min_rr:
        score += 10
        reasons.append("The pending setup keeps the required reward-to-risk profile.")
    else:
        reasons.append("The pending setup does not keep the minimum reward-to-risk.")

    if trigger_distance <= atr * 1.5:
        score += 10
        reasons.append("Trigger is close enough to current price to remain tied to the active setup.")
    elif trigger_distance <= atr * 3.0:
        score += 5
        reasons.append("Trigger is valid but slightly stretched from the current candle.")
    else:
        reasons.append("Trigger is far from current price and may become stale.")

    if session in {"London", "New York"}:
        score += 8
        reasons.append(f"Pending setup is forming during active {session} conditions.")
    elif session == "Asia":
        score += 4
        reasons.append("Asia session requires stricter trigger confirmation.")
    else:
        reasons.append("Off-session timing lowers the pending setup quality.")

    if not liquidity_ok:
        score = min(score, 83)
    if not stop_clear:
        score = min(score, 74)
    if risk_reward < min_rr:
        score = min(score, 79)
    if trigger_distance > atr * 3.0:
        score = min(score, 80)
    score = min(89, max(0, score))
    metadata = {
        "bias": bias,
        "structure": structure.get("structure"),
        "trigger_distance": trigger_distance,
        "atr": atr,
        "session": session,
    }
    return score, list(dict.fromkeys(reasons)), metadata


def _structure_break_preentry(
    df: pd.DataFrame,
    level: dict[str, Any],
    direction: str,
    timeframe: str,
    min_rr: float,
) -> dict[str, Any] | None:
    if len(df) < 24:
        return None
    current = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    close = float(current["close"])
    atr = _atr(df)
    buffer = max(atr * 0.05, abs(close) * 0.00002)
    recent = df.tail(12)
    tolerance = float(level.get("tolerance") or atr * 0.45)
    level_price = float(level["price"])

    if direction == "BUY":
        trigger = max(float(current["high"]), float(prev["high"]), float(prev2["high"])) + buffer
        stop = min(float(recent["low"].min()), level_price - tolerance) - atr * 0.15
        pending_order_type = "BUY_STOP"
        valid_if = "Price trades through the internal highs, confirming the reclaim/structure break after the level reaction."
        invalidation = "Close below the reacted key level or the manipulation swing low."
    else:
        trigger = min(float(current["low"]), float(prev["low"]), float(prev2["low"])) - buffer
        stop = max(float(recent["high"].max()), level_price + tolerance) + atr * 0.15
        pending_order_type = "SELL_STOP"
        valid_if = "Price trades through the internal lows, confirming the rejection/structure break after the level reaction."
        invalidation = "Close above the reacted key level or the manipulation swing high."

    if not np.isfinite(trigger) or not np.isfinite(stop):
        return None
    risk = abs(trigger - stop)
    if risk <= 0:
        return None
    target = trigger + risk * max(min_rr, 5.0) if direction == "BUY" else trigger - risk * max(min_rr, 5.0)
    rr = abs(target - trigger) / max(risk, 1e-9)
    if abs(trigger - close) > atr * 3.5:
        return None

    score, reasons, metadata = _score_preentry_candidate(
        df=df,
        level=level,
        direction=direction,
        trigger_price=trigger,
        stop_loss=stop,
        risk_reward=rr,
        min_rr=min_rr,
        mode="structure_break",
        timeframe=timeframe,
    )
    targets = _profit_targets(trigger, stop, direction, max(min_rr, 5.0))
    return {
        "direction": direction,
        "setup_score": int(score),
        "setup_grade": "PRE-A+" if score >= 85 else "WATCH",
        "profile_type": level["profile_type"],
        "key_level": level["key_level"],
        "entry_model": "Pending Entry Model 3 - Internal Structure Break",
        "execution_type": "PENDING",
        "pending_order_type": pending_order_type,
        "trigger_price": round(trigger, 5),
        "entry": round(trigger, 5),
        "stop_loss": round(stop, 5),
        "take_profit": round(target, 5),
        "tp1": round(targets["tp1"], 5),
        "tp2": round(targets["tp2"], 5),
        "tp3": round(targets["tp3"], 5),
        "tp4": round(targets["tp4"], 5) if "tp4" in targets else None,
        "tp5": round(targets["tp5"], 5) if "tp5" in targets else None,
        "risk_reward": round(rr, 2),
        "invalidation": invalidation,
        "preplace_valid_if": valid_if,
        "reasons": reasons,
        "status": "preplace",
        **metadata,
    }


def _profile_retest_preentry(
    df: pd.DataFrame,
    level: dict[str, Any],
    direction: str,
    timeframe: str,
    min_rr: float,
) -> dict[str, Any] | None:
    if len(df) < 40:
        return None
    current = df.iloc[-1]
    close = float(current["close"])
    atr = _atr(df)
    reaction = df.tail(24)
    profile = _volume_profile(reaction)
    if profile is None:
        return None
    level_price = float(level["price"])
    moved_from_level = (close - level_price) if direction == "BUY" else (level_price - close)
    if moved_from_level < atr * 0.45 or moved_from_level > atr * 3.5:
        return None

    raw_levels = [profile.poc, profile.vah, profile.val]
    if direction == "BUY":
        possible = [price for price in raw_levels if price < close]
        if not possible:
            return None
        trigger = min(possible, key=lambda price: abs(price - profile.poc))
        stop = min(float(reaction["low"].min()), level_price) - atr * 0.15
        pending_order_type = "BUY_LIMIT"
        valid_if = "Price retraces into the LTF swing profile after the first key-level reaction, giving the planned pullback entry."
        invalidation = "Close below the LTF swing low and reacted key level."
    else:
        possible = [price for price in raw_levels if price > close]
        if not possible:
            return None
        trigger = min(possible, key=lambda price: abs(price - profile.poc))
        stop = max(float(reaction["high"].max()), level_price) + atr * 0.15
        pending_order_type = "SELL_LIMIT"
        valid_if = "Price retraces into the LTF swing profile after the first key-level rejection, giving the planned pullback entry."
        invalidation = "Close above the LTF swing high and reacted key level."

    if abs(trigger - close) < atr * 0.12 or abs(trigger - close) > atr * 3.5:
        return None
    risk = abs(trigger - stop)
    if risk <= 0:
        return None
    target = trigger + risk * max(min_rr, 5.0) if direction == "BUY" else trigger - risk * max(min_rr, 5.0)
    rr = abs(target - trigger) / max(risk, 1e-9)
    score, reasons, metadata = _score_preentry_candidate(
        df=df,
        level=level,
        direction=direction,
        trigger_price=trigger,
        stop_loss=stop,
        risk_reward=rr,
        min_rr=min_rr,
        mode="profile_retest",
        timeframe=timeframe,
    )
    targets = _profit_targets(trigger, stop, direction, max(min_rr, 5.0))
    return {
        "direction": direction,
        "setup_score": int(score),
        "setup_grade": "PRE-A+" if score >= 85 else "WATCH",
        "profile_type": level["profile_type"],
        "key_level": level["key_level"],
        "entry_model": "Pending Entry Model 2 - LTF Swing Retest",
        "execution_type": "PENDING",
        "pending_order_type": pending_order_type,
        "trigger_price": round(trigger, 5),
        "entry": round(trigger, 5),
        "stop_loss": round(stop, 5),
        "take_profit": round(target, 5),
        "tp1": round(targets["tp1"], 5),
        "tp2": round(targets["tp2"], 5),
        "tp3": round(targets["tp3"], 5),
        "tp4": round(targets["tp4"], 5) if "tp4" in targets else None,
        "tp5": round(targets["tp5"], 5) if "tp5" in targets else None,
        "risk_reward": round(rr, 2),
        "invalidation": invalidation,
        "preplace_valid_if": valid_if,
        "reasons": reasons,
        "status": "preplace",
        **metadata,
    }


def score_setup(context: dict[str, Any]) -> tuple[int, list[str]]:
    reasons: list[str] = []
    score = 0

    level = context["level"]
    if level:
        score += min(20, int(level.get("priority", 10)))
        if level.get("confluence", 1) >= 2:
            score += 5
            reasons.append("Key level has volume-profile confluence.")
        reasons.append(f"Price is reacting from {level['key_level']} ({level['profile_type']}).")
    else:
        reasons.append("No mapped LTA key level.")

    bias = context["bias"]
    direction = context["direction"]
    confirmation = context["confirmation"]
    if (bias == "bullish" and direction == "BUY") or (bias == "bearish" and direction == "SELL"):
        score += 15
        reasons.append("Direction aligns with higher-timeframe bias.")
    elif bias == "ranging" and confirmation.get("confirmed"):
        score += 9
        reasons.append("Range conditions allow a confirmed reaction trade.")
    elif confirmation.get("model") and "Internal Structure" in confirmation["model"]:
        score += 10
        reasons.append("Counter-bias idea is supported by manipulation and internal structure break.")
    else:
        reasons.append("Higher-timeframe bias is not fully aligned.")

    if context["liquidity_ok"]:
        score += 15
        reasons.append(context["liquidity_reason"])
    else:
        reasons.append(context["liquidity_reason"])

    if confirmation.get("confirmed"):
        score += 20
        reasons.extend(confirmation.get("reasons", []))
    else:
        reasons.extend(confirmation.get("reasons", []))

    if context["stop_clear"]:
        score += 10
        reasons.append("Stop loss and invalidation are structure based.")
    else:
        reasons.append("Stop loss or invalidation is unclear.")

    if context["risk_reward"] >= context["min_rr"]:
        score += 10
        reasons.append("Risk-to-reward meets the minimum.")
    else:
        reasons.append("Risk-to-reward is too low.")

    if context["session"] in {"London", "New York"}:
        score += 10
        reasons.append(f"Setup appears during active {context['session']} session conditions.")
    elif context["session"] == "Asia":
        score += 5
        reasons.append("Asia session is acceptable only with extra confirmation.")
    else:
        reasons.append("Off-session timing lowers quality.")

    if not level:
        score = min(score, 60)
    if not confirmation.get("confirmed"):
        score = min(score, 70)
    if not context["stop_clear"]:
        score = min(score, 75)
    if context["risk_reward"] < context["min_rr"]:
        score = min(score, 79)

    grade = min(100, max(0, score))
    return grade, reasons


def generate_signal(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    min_score: int = 90,
    min_rr: float = 5.0,
) -> dict[str, Any] | None:
    df = _to_frame(candles)
    if len(df) < 80:
        return None
    level = detect_aoi(df)
    if not level:
        return None

    direction = _direction_from_reaction(df, level)
    if direction is None:
        direction = "BUY" if float(df.iloc[-1]["close"]) >= float(level["price"]) else "SELL"

    entry, stop, target, rr = _build_trade_levels(df, direction, min_rr)
    targets = _profit_targets(entry, stop, direction, max(min_rr, 5.0))
    confirmation = detect_entry_confirmation(df, level, direction)
    liquidity_ok, liquidity_reason = _liquidity_context(df, direction)
    bias = detect_bias(df, timeframe)
    structure = detect_market_structure(df)
    session = _session_name(pd.Timestamp(df.iloc[-1]["time"]).to_pydatetime())
    stop_clear = abs(entry - stop) > 0 and np.isfinite(stop) and np.isfinite(target)

    context = {
        "level": level,
        "direction": direction,
        "bias": bias,
        "structure": structure,
        "confirmation": confirmation,
        "liquidity_ok": liquidity_ok,
        "liquidity_reason": liquidity_reason,
        "stop_clear": stop_clear,
        "risk_reward": rr,
        "min_rr": min_rr,
        "session": session,
    }
    score, reasons = score_setup(context)
    grade = "A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 70 else "C"
    status = "allowed" if score >= min_score else "rejected"

    invalidation = (
        "Close below the rejection wick/internal swing low."
        if direction == "BUY"
        else "Close above the rejection wick/internal swing high."
    )
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "direction": direction,
        "setup_grade": grade,
        "setup_score": int(score),
        "profile_type": level["profile_type"],
        "key_level": level["key_level"],
        "entry_model": confirmation.get("model"),
        "entry": round(entry, 5),
        "stop_loss": round(stop, 5),
        "take_profit": round(target, 5),
        "tp1": round(targets["tp1"], 5),
        "tp2": round(targets["tp2"], 5),
        "tp3": round(targets["tp3"], 5),
        "tp4": round(targets["tp4"], 5) if "tp4" in targets else None,
        "tp5": round(targets["tp5"], 5) if "tp5" in targets else None,
        "risk_reward": round(rr, 2),
        "invalidation": invalidation,
        "bias": bias,
        "structure": structure.get("structure"),
        "session": session,
        "reasons": list(dict.fromkeys(reasons)),
        "status": status,
        "timestamp": pd.Timestamp(df.iloc[-1]["time"]).to_pydatetime(),
    }


def generate_preentry_candidate(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    min_score: int = 85,
    min_rr: float = 5.0,
) -> dict[str, Any] | None:
    df = _to_frame(candles)
    if len(df) < 80:
        return None

    level = _recent_aoi(df)
    if not level:
        return None

    direction = _preentry_direction(df, level)
    if direction is None:
        return None

    confirmation = detect_entry_confirmation(df, level, direction)
    if confirmation.get("confirmed"):
        return None

    candidates = [
        _structure_break_preentry(df, level, direction, timeframe, min_rr),
        _profile_retest_preentry(df, level, direction, timeframe, min_rr),
    ]
    valid = [
        candidate
        for candidate in candidates
        if candidate
        and int(candidate.get("setup_score") or 0) >= min_score
        and float(candidate.get("risk_reward") or 0.0) >= min_rr
    ]
    if not valid:
        return None

    valid.sort(
        key=lambda item: (
            int(item.get("setup_score") or 0),
            1 if str(item.get("pending_order_type") or "").endswith("_STOP") else 0,
        ),
        reverse=True,
    )
    candidate = dict(valid[0])
    candidate["symbol"] = symbol
    candidate["timeframe"] = timeframe
    candidate["timestamp"] = pd.Timestamp(df.iloc[-1]["time"]).to_pydatetime()
    return candidate
