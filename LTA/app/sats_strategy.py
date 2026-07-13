from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


def _safe_div(num: float, den: float, fallback: float = 0.0) -> float:
    if den == 0 or not np.isfinite(num) or not np.isfinite(den):
        return fallback
    return num / den


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _map_clamp(value: float, in_low: float, in_high: float, out_low: float, out_high: float) -> float:
    ratio = _clamp(_safe_div(value - in_low, in_high - in_low, 0.0), 0.0, 1.0)
    return out_low + ratio * (out_high - out_low)


def _map_clamp_inv(value: float, in_low: float, in_high: float, out_high: float, out_low: float) -> float:
    ratio = _clamp(_safe_div(value - in_low, in_high - in_low, 0.0), 0.0, 1.0)
    return out_high - ratio * (out_high - out_low)


def _rma(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(alpha=1.0 / max(1, length), adjust=False, min_periods=length).mean()


def _atr(frame: pd.DataFrame, length: int) -> pd.Series:
    previous_close = frame["close"].shift(1)
    true_range = pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return _rma(true_range, length).fillna(0.0)


def _rsi(close: pd.Series, length: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = _rma(gain, length)
    avg_loss = _rma(loss, length)
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    return (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)


def _efficiency_ratio(close: pd.Series, length: int) -> pd.Series:
    change = (close - close.shift(length)).abs()
    volatility = close.diff().abs().rolling(length).sum()
    return (change / volatility.replace(0.0, np.nan)).fillna(0.0).clip(0.0, 1.0)


def _pivot_confirmations(frame: pd.DataFrame, strength: int) -> tuple[list[float | None], list[float | None]]:
    highs = frame["high"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    pivot_highs: list[float | None] = [None] * len(frame)
    pivot_lows: list[float | None] = [None] * len(frame)
    span = strength * 2 + 1
    for current in range(strength * 2, len(frame)):
        pivot_index = current - strength
        start = pivot_index - strength
        end = pivot_index + strength + 1
        if end - start != span:
            continue
        window_high = highs[start:end]
        window_low = lows[start:end]
        if highs[pivot_index] >= np.nanmax(window_high):
            pivot_highs[current] = highs[pivot_index]
        if lows[pivot_index] <= np.nanmin(window_low):
            pivot_lows[current] = lows[pivot_index]
    return pivot_highs, pivot_lows


@dataclass(frozen=True)
class SatsSettings:
    atr_len: int = 13
    base_mult: float = 2.0
    use_adaptive: bool = True
    er_length: int = 20
    adapt_strength: float = 0.5
    atr_baseline_len: int = 100
    use_tqi: bool = True
    quality_strength: float = 0.4
    quality_curve: float = 1.5
    smooth_multipliers: bool = True
    use_asym_bands: bool = True
    asym_strength: float = 0.5
    use_eff_atr: bool = True
    use_char_flip: bool = True
    char_flip_min_age: int = 5
    char_flip_high: float = 0.55
    char_flip_low: float = 0.25
    tqi_weight_er: float = 0.35
    tqi_weight_vol: float = 0.20
    tqi_weight_struct: float = 0.25
    tqi_weight_mom: float = 0.20
    tqi_struct_len: int = 20
    tqi_mom_len: int = 10
    pivot_len: int = 3
    rsi_len: int = 14
    rsi_overbought: int = 70
    rsi_oversold: int = 30
    rsi_lookback: int = 20
    vol_len: int = 20
    sl_atr_mult: float = 1.5
    sl_max_dist_atr: float = 4.0
    tp_mode: str = "Fixed"
    tp1_r: float = 1.0
    tp2_r: float = 2.0
    tp3_r: float = 3.0
    dyn_tqi_weight: float = 0.6
    dyn_vol_weight: float = 0.4
    dyn_min_scale: float = 0.5
    dyn_max_scale: float = 2.0
    dyn_floor_r1: float = 0.5
    dyn_ceil_r3: float = 8.0
    trade_timeout_bars: int = 100
    min_score: float = 0.0
    min_tqi: float = 0.0
    weekdays_only: bool = True


def _dynamic_tp_rs(settings: SatsSettings, tqi: float, vol_ratio: float) -> tuple[float, float, float, float]:
    if settings.tp_mode.strip().lower() != "dynamic":
        return settings.tp1_r, settings.tp2_r, settings.tp3_r, 1.0
    tqi_comp = _clamp(tqi, 0.0, 1.0)
    vol_comp = _clamp(_map_clamp(vol_ratio, 0.5, 2.0, 0.0, 1.0), 0.0, 1.0)
    weight_sum = settings.dyn_tqi_weight + settings.dyn_vol_weight
    weight_denom = weight_sum if weight_sum > 0 else 1.0
    raw_scale = (tqi_comp * settings.dyn_tqi_weight + vol_comp * settings.dyn_vol_weight) / weight_denom
    scale = settings.dyn_min_scale + raw_scale * (settings.dyn_max_scale - settings.dyn_min_scale)
    tp1_floor = min(settings.dyn_floor_r1, settings.dyn_ceil_r3)
    tp2_floor = min(settings.dyn_floor_r1 * (settings.tp2_r / max(settings.tp1_r, 0.01)), settings.dyn_ceil_r3)
    tp3_floor = min(settings.dyn_floor_r1 * (settings.tp3_r / max(settings.tp1_r, 0.01)), settings.dyn_ceil_r3)
    values = [
        _clamp(settings.tp1_r * scale, tp1_floor, settings.dyn_ceil_r3),
        _clamp(settings.tp2_r * scale, tp2_floor, settings.dyn_ceil_r3),
        _clamp(settings.tp3_r * scale, tp3_floor, settings.dyn_ceil_r3),
    ]
    values.sort()
    return values[0], values[1], values[2], scale


def build_sats_signals(candles: pd.DataFrame, settings: SatsSettings | None = None) -> pd.DataFrame:
    settings = settings or SatsSettings()
    frame = candles.copy().reset_index(drop=True)
    if frame.empty:
        return frame
    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["volume"] = pd.to_numeric(frame.get("volume", 0.0), errors="coerce").fillna(0.0)
    frame = frame.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

    raw_atr = _atr(frame, settings.atr_len)
    atr_baseline = raw_atr.rolling(settings.atr_baseline_len).mean().fillna(raw_atr)
    vol_ratio = (raw_atr / atr_baseline.replace(0.0, np.nan)).fillna(1.0)
    er = _efficiency_ratio(frame["close"], settings.er_length)
    atr_value = raw_atr * (0.5 + 0.5 * er) if settings.use_eff_atr else raw_atr

    volume_mean = frame["volume"].rolling(settings.vol_len).mean()
    volume_std = frame["volume"].rolling(settings.vol_len).std(ddof=0)
    vol_z = ((frame["volume"] - volume_mean) / volume_std.replace(0.0, np.nan)).fillna(0.0)
    has_volume = bool((frame["volume"] > 0).any())
    tqi_vol = vol_z.apply(lambda v: _map_clamp(float(v), -1.0, 2.0, 0.0, 1.0)) if has_volume else vol_ratio.apply(lambda v: _map_clamp(float(v), 0.6, 1.8, 0.0, 1.0))
    struct_hi = frame["high"].rolling(settings.tqi_struct_len).max()
    struct_lo = frame["low"].rolling(settings.tqi_struct_len).min()
    price_pos = ((frame["close"] - struct_lo) / (struct_hi - struct_lo).replace(0.0, np.nan)).fillna(0.5)
    tqi_struct = ((price_pos - 0.5).abs() * 2.0).clip(0.0, 1.0)
    window_change = frame["close"] - frame["close"].shift(settings.tqi_mom_len)
    up_moves = (frame["close"] > frame["close"].shift(1)).astype(float).rolling(settings.tqi_mom_len).sum().fillna(0.0)
    down_moves = (frame["close"] < frame["close"].shift(1)).astype(float).rolling(settings.tqi_mom_len).sum().fillna(0.0)
    tqi_mom = pd.Series(0.0, index=frame.index)
    tqi_mom = tqi_mom.mask(window_change > 0, up_moves / settings.tqi_mom_len)
    tqi_mom = tqi_mom.mask(window_change < 0, down_moves / settings.tqi_mom_len)
    tqi_weight_sum = settings.tqi_weight_er + settings.tqi_weight_vol + settings.tqi_weight_struct + settings.tqi_weight_mom
    tqi_weight_denom = tqi_weight_sum if tqi_weight_sum > 0 else 1.0
    tqi = (
        (er * settings.tqi_weight_er + tqi_vol * settings.tqi_weight_vol + tqi_struct * settings.tqi_weight_struct + tqi_mom * settings.tqi_weight_mom)
        / tqi_weight_denom
        if settings.use_tqi
        else pd.Series(0.5, index=frame.index)
    ).clip(0.0, 1.0)

    pivot_highs, pivot_lows = _pivot_confirmations(frame, settings.pivot_len)
    rsi = _rsi(frame["close"], settings.rsi_len)
    rsi_low = rsi.rolling(settings.rsi_lookback).min().fillna(rsi)
    rsi_high = rsi.rolling(settings.rsi_lookback).max().fillna(rsi)

    warmup = max(
        50,
        settings.atr_len,
        settings.atr_baseline_len,
        settings.er_length,
        settings.rsi_len,
        settings.rsi_lookback,
        settings.vol_len,
        settings.pivot_len * 2 + 1,
        settings.tqi_mom_len,
        settings.tqi_struct_len,
    ) + 10

    lower_band = np.full(len(frame), np.nan)
    upper_band = np.full(len(frame), np.nan)
    trend = np.full(len(frame), 1, dtype=int)
    active_sm = np.full(len(frame), np.nan)
    passive_sm = np.full(len(frame), np.nan)
    last_pivot_high = np.nan
    last_pivot_low = np.nan
    trend_start = 0
    signals: list[dict[str, Any]] = []

    for i in range(len(frame)):
        close = float(frame.at[i, "close"])
        high = float(frame.at[i, "high"])
        low = float(frame.at[i, "low"])
        prev_trend = int(trend[i - 1]) if i > 0 else 1

        if pivot_highs[i] is not None:
            last_pivot_high = float(pivot_highs[i])
        if pivot_lows[i] is not None:
            last_pivot_low = float(pivot_lows[i])

        legacy_adapt = 1.0 + settings.adapt_strength * (0.5 - float(er.iloc[i])) if settings.use_adaptive else 1.0
        quality_deviation = (1.0 - float(tqi.iloc[i])) ** settings.quality_curve if settings.use_tqi else 0.5
        tqi_mult = 1.0 - settings.quality_strength + settings.quality_strength * (0.6 + 0.8 * quality_deviation)
        sym_mult = settings.base_mult * legacy_adapt * tqi_mult
        active_raw = sym_mult
        passive_raw = sym_mult
        if settings.use_tqi and settings.use_asym_bands:
            asym_tighten = 1.0 - settings.asym_strength * float(tqi.iloc[i]) * 0.3
            asym_widen = 1.0 + settings.asym_strength * float(tqi.iloc[i]) * 0.4
            active_raw = sym_mult * asym_tighten
            passive_raw = sym_mult * asym_widen
        if i == 0 or not np.isfinite(active_sm[i - 1]):
            active_sm[i] = active_raw
            passive_sm[i] = passive_raw
        else:
            alpha = 0.15 if settings.smooth_multipliers else 1.0
            active_sm[i] = active_sm[i - 1] * (1.0 - alpha) + active_raw * alpha
            passive_sm[i] = passive_sm[i - 1] * (1.0 - alpha) + passive_raw * alpha

        lower_mult = active_sm[i] if prev_trend == 1 else passive_sm[i]
        upper_mult = passive_sm[i] if prev_trend == 1 else active_sm[i]
        lower_raw = close - lower_mult * float(atr_value.iloc[i])
        upper_raw = close + upper_mult * float(atr_value.iloc[i])
        if i == 0 or not np.isfinite(lower_band[i - 1]):
            lower_band[i] = lower_raw
            upper_band[i] = upper_raw
        else:
            prev_close = float(frame.at[i - 1, "close"])
            lower_band[i] = max(lower_raw, lower_band[i - 1]) if prev_close > lower_band[i - 1] else lower_raw
            upper_band[i] = min(upper_raw, upper_band[i - 1]) if prev_close < upper_band[i - 1] else upper_raw

        price_flip_up = i > 0 and prev_trend == -1 and close > upper_band[i - 1]
        price_flip_down = i > 0 and prev_trend == 1 and close < lower_band[i - 1]
        trend_age = i - trend_start
        char_window = max(settings.char_flip_min_age, 3)
        tqi_window_high = float(tqi.iloc[max(0, i - char_window + 1) : i + 1].max())
        char_base = (
            settings.use_char_flip
            and settings.use_tqi
            and trend_age >= settings.char_flip_min_age
            and tqi_window_high > settings.char_flip_high
            and float(tqi.iloc[i]) < settings.char_flip_low
            and i >= char_window
        )
        char_down = char_base and prev_trend == 1 and close < float(frame.at[i - char_window, "close"])
        char_up = char_base and prev_trend == -1 and close > float(frame.at[i - char_window, "close"])
        final_up = price_flip_up or char_up
        final_down = price_flip_down or char_down
        trend[i] = 1 if final_up else (-1 if final_down else prev_trend)
        if trend[i] != prev_trend:
            trend_start = i

        flip_up = i > 0 and trend[i] == 1 and prev_trend == -1
        flip_down = i > 0 and trend[i] == -1 and prev_trend == 1
        is_buy_score = trend[i] == 1
        dir_move = (float(frame.at[i - 3, "close"]) - close) if (is_buy_score and i >= 3) else ((close - float(frame.at[i - 3, "close"])) if i >= 3 else 0.0)
        atr_now = float(atr_value.iloc[i])
        mom_score = _map_clamp(_safe_div(dir_move, atr_now, 0.0), 0.3, 2.0, 0.0, 17.0)
        er_score = _map_clamp(float(er.iloc[i]), 0.15, 0.7, 0.0, 17.0)
        volume_score = _map_clamp(float(vol_z.iloc[i]), 0.0, 3.0, 0.0, 17.0) if has_volume else 12.0
        rsi_depth = max(0.0, settings.rsi_oversold - float(rsi_low.iloc[i])) if is_buy_score else max(0.0, float(rsi_high.iloc[i]) - settings.rsi_overbought)
        rsi_score = _map_clamp(rsi_depth, 0.0, 15.0, 0.0, 17.0)
        if is_buy_score and np.isfinite(last_pivot_low):
            pivot_dist = abs(close - last_pivot_low)
        elif (not is_buy_score) and np.isfinite(last_pivot_high):
            pivot_dist = abs(last_pivot_high - close)
        else:
            pivot_dist = 0.0
        struct_score = _map_clamp_inv(_safe_div(pivot_dist, atr_now, 0.0), 0.0, 1.5, 16.0, 6.0)
        break_depth = 0.0
        if i > 0:
            break_depth = max(0.0, upper_band[i - 1] - float(frame.at[i - 1, "close"])) if is_buy_score else max(0.0, float(frame.at[i - 1, "close"]) - lower_band[i - 1])
        break_score = _map_clamp(_safe_div(break_depth, atr_now, 0.0), 0.0, 1.0, 0.0, 16.0)
        score = mom_score + er_score + volume_score + rsi_score + struct_score + break_score

        if i >= warmup and (flip_up or flip_down):
            side = "BUY" if flip_up else "SELL"
            if score >= settings.min_score and float(tqi.iloc[i]) >= settings.min_tqi:
                if side == "BUY":
                    sl_base = last_pivot_low if np.isfinite(last_pivot_low) else low
                    raw_sl = sl_base - settings.sl_atr_mult * atr_now
                    min_sl = close - settings.sl_atr_mult * atr_now
                    stop = min(raw_sl, min_sl)
                    stop = max(stop, close - max(settings.sl_max_dist_atr, settings.sl_atr_mult) * atr_now)
                    risk = close - stop
                else:
                    sl_base = last_pivot_high if np.isfinite(last_pivot_high) else high
                    raw_sl = sl_base + settings.sl_atr_mult * atr_now
                    min_sl = close + settings.sl_atr_mult * atr_now
                    stop = max(raw_sl, min_sl)
                    stop = min(stop, close + max(settings.sl_max_dist_atr, settings.sl_atr_mult) * atr_now)
                    risk = stop - close
                if risk > 0:
                    tp1_r, tp2_r, tp3_r, tp_scale = _dynamic_tp_rs(settings, float(tqi.iloc[i]), float(vol_ratio.iloc[i]))
                    if side == "BUY":
                        tp1, tp2, tp3 = close + risk * tp1_r, close + risk * tp2_r, close + risk * tp3_r
                    else:
                        tp1, tp2, tp3 = close - risk * tp1_r, close - risk * tp2_r, close - risk * tp3_r
                    signals.append(
                        {
                            "index": i,
                            "time": frame.at[i, "time"],
                            "side": side,
                            "entry": close,
                            "stop_loss": stop,
                            "tp1": tp1,
                            "tp2": tp2,
                            "tp3": tp3,
                            "tp1_r": tp1_r,
                            "tp2_r": tp2_r,
                            "tp3_r": tp3_r,
                            "tp_scale": tp_scale,
                            "score": score,
                            "tqi": float(tqi.iloc[i]),
                            "er": float(er.iloc[i]),
                            "vol_z": float(vol_z.iloc[i]),
                            "vol_ratio": float(vol_ratio.iloc[i]),
                        }
                    )

    frame["sats_trend"] = trend
    frame["sats_lower_band"] = lower_band
    frame["sats_upper_band"] = upper_band
    frame["sats_tqi"] = tqi
    frame["sats_er"] = er
    frame["sats_vol_z"] = vol_z
    frame.attrs["signals"] = signals
    return frame


def simulate_sats_trades(
    candles: pd.DataFrame,
    symbol: str,
    settings: SatsSettings | None = None,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    settings = settings or SatsSettings()
    frame = build_sats_signals(candles, settings)
    signals = list(frame.attrs.get("signals", []))
    trades: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None
    signal_by_index = {int(signal["index"]): signal for signal in signals}

    for i, row in frame.iterrows():
        timestamp = row["time"]
        if settings.weekdays_only and pd.Timestamp(timestamp).weekday() >= 5:
            continue

        current_signal = signal_by_index.get(int(i))
        if active and current_signal and current_signal["side"] != active["side"]:
            risk = abs(float(active["entry"]) - float(active["stop_loss"]))
            open_r = -1.0
            if risk > 0:
                open_r = (
                    (float(row["close"]) - float(active["entry"])) / risk
                    if active["side"] == "BUY"
                    else (float(active["entry"]) - float(row["close"])) / risk
                )
            taken = (
                (active["tp1_r"] / 3.0 if active["hit_tp1"] else 0.0)
                + (active["tp2_r"] / 3.0 if active["hit_tp2"] else 0.0)
                + (active["tp3_r"] / 3.0 if active["hit_tp3"] else 0.0)
            )
            remaining = 1.0 - (1.0 / 3.0 if active["hit_tp1"] else 0.0) - (1.0 / 3.0 if active["hit_tp2"] else 0.0) - (1.0 / 3.0 if active["hit_tp3"] else 0.0)
            active.update({"exit_time": timestamp, "exit_price": float(row["close"]), "exit_reason": "flip_exit", "r_multiple": _clamp(taken + remaining * open_r, -1.0, active["tp3_r"])})
            trades.append(active)
            active = None

        if current_signal:
            if active is None:
                active = {
                    "symbol": symbol,
                    "entry_time": current_signal["time"],
                    "side": current_signal["side"],
                    "entry": current_signal["entry"],
                    "stop_loss": current_signal["stop_loss"],
                    "tp1": current_signal["tp1"],
                    "tp2": current_signal["tp2"],
                    "tp3": current_signal["tp3"],
                    "tp1_r": current_signal["tp1_r"],
                    "tp2_r": current_signal["tp2_r"],
                    "tp3_r": current_signal["tp3_r"],
                    "score": current_signal["score"],
                    "tqi": current_signal["tqi"],
                    "er": current_signal["er"],
                    "vol_z": current_signal["vol_z"],
                    "hit_tp1": False,
                    "hit_tp2": False,
                    "hit_tp3": False,
                    "tp1_hit_time": None,
                    "tp2_hit_time": None,
                    "tp3_hit_time": None,
                    "entry_index": int(i),
                }
            continue

        if not active or i <= int(active["entry_index"]):
            continue

        side = active["side"]
        sl_hit = float(row["low"]) <= active["stop_loss"] if side == "BUY" else float(row["high"]) >= active["stop_loss"]
        tp1_hit = (not sl_hit) and (float(row["high"]) >= active["tp1"] if side == "BUY" else float(row["low"]) <= active["tp1"])
        tp2_hit = (not sl_hit) and (float(row["high"]) >= active["tp2"] if side == "BUY" else float(row["low"]) <= active["tp2"])
        tp3_hit = (not sl_hit) and (float(row["high"]) >= active["tp3"] if side == "BUY" else float(row["low"]) <= active["tp3"])

        if tp1_hit and not active["hit_tp1"]:
            active["hit_tp1"] = True
            active["tp1_hit_time"] = timestamp
        if tp2_hit and not active["hit_tp2"]:
            active["hit_tp2"] = True
            active["tp2_hit_time"] = timestamp
        if tp3_hit and not active["hit_tp3"]:
            active["hit_tp3"] = True
            active["tp3_hit_time"] = timestamp

        trade_age = int(i) - int(active["entry_index"])
        timeout = trade_age >= settings.trade_timeout_bars
        if sl_hit or active["hit_tp3"] or timeout:
            if sl_hit:
                taken = (
                    (active["tp1_r"] / 3.0 if active["hit_tp1"] else 0.0)
                    + (active["tp2_r"] / 3.0 if active["hit_tp2"] else 0.0)
                )
                remaining = 1.0 - (1.0 / 3.0 if active["hit_tp1"] else 0.0) - (1.0 / 3.0 if active["hit_tp2"] else 0.0)
                r_multiple = taken + remaining * -1.0
                exit_reason = "stop_loss"
                exit_price = active["stop_loss"]
            elif active["hit_tp3"]:
                r_multiple = (active["tp1_r"] + active["tp2_r"] + active["tp3_r"]) / 3.0
                exit_reason = "tp3"
                exit_price = active["tp3"]
            else:
                risk = abs(float(active["entry"]) - float(active["stop_loss"]))
                open_r = (
                    (float(row["close"]) - float(active["entry"])) / risk
                    if side == "BUY"
                    else (float(active["entry"]) - float(row["close"])) / risk
                ) if risk > 0 else 0.0
                taken = (
                    (active["tp1_r"] / 3.0 if active["hit_tp1"] else 0.0)
                    + (active["tp2_r"] / 3.0 if active["hit_tp2"] else 0.0)
                )
                remaining = 1.0 - (1.0 / 3.0 if active["hit_tp1"] else 0.0) - (1.0 / 3.0 if active["hit_tp2"] else 0.0)
                r_multiple = taken + remaining * open_r
                exit_reason = "timeout"
                exit_price = float(row["close"])
            active.update({"exit_time": timestamp, "exit_price": exit_price, "exit_reason": exit_reason, "r_multiple": _clamp(float(r_multiple), -1.0, active["tp3_r"])})
            trades.append(active)
            active = None

    if active:
        last = frame.iloc[-1]
        risk = abs(float(active["entry"]) - float(active["stop_loss"]))
        open_r = (
            (float(last["close"]) - float(active["entry"])) / risk
            if active["side"] == "BUY"
            else (float(active["entry"]) - float(last["close"])) / risk
        ) if risk > 0 else 0.0
        active.update({"exit_time": last["time"], "exit_price": float(last["close"]), "exit_reason": "end_of_data", "r_multiple": _clamp(open_r, -1.0, active["tp3_r"])})
        trades.append(active)

    return trades, frame


def simulate_sats_three_leg_trades(
    candles: pd.DataFrame,
    symbol: str,
    settings: SatsSettings | None = None,
) -> tuple[list[dict[str, Any]], pd.DataFrame]:
    settings = settings or SatsSettings()
    frame = build_sats_signals(candles, settings)
    signals = list(frame.attrs.get("signals", []))
    signal_by_index = {int(signal["index"]): signal for signal in signals}
    trades: list[dict[str, Any]] = []
    legs: list[dict[str, Any]] = []
    idea_counter = 0

    def close_leg(leg: dict[str, Any], timestamp: Any, price: float, reason: str) -> None:
        risk = abs(float(leg["entry"]) - float(leg["initial_stop"]))
        if reason == "target":
            r_multiple = float(leg["target_r"])
        elif reason == "stop":
            if risk <= 0:
                r_multiple = 0.0
            else:
                r_multiple = (
                    (float(price) - float(leg["entry"])) / risk
                    if leg["side"] == "BUY"
                    else (float(leg["entry"]) - float(price)) / risk
                )
        else:
            if risk <= 0:
                r_multiple = 0.0
            else:
                r_multiple = (
                    (float(price) - float(leg["entry"])) / risk
                    if leg["side"] == "BUY"
                    else (float(leg["entry"]) - float(price)) / risk
                )
        item = dict(leg)
        item.update(
            {
                "exit_time": timestamp,
                "exit_price": float(price),
                "exit_reason": reason,
                "r_multiple": _clamp(float(r_multiple), -1.0, float(leg["target_r"])),
            }
        )
        trades.append(item)

    for i, row in frame.iterrows():
        timestamp = row["time"]
        if settings.weekdays_only and pd.Timestamp(timestamp).weekday() >= 5:
            continue

        current_signal = signal_by_index.get(int(i))
        if legs and current_signal and current_signal["side"] != legs[0]["side"]:
            for leg in legs:
                close_leg(leg, timestamp, float(row["close"]), "flip_exit")
            legs = []

        if current_signal and not legs:
            idea_counter += 1
            side = current_signal["side"]
            base = {
                "symbol": symbol,
                "idea_id": f"{symbol}-{pd.Timestamp(current_signal['time']).isoformat()}-{idea_counter}",
                "entry_time": current_signal["time"],
                "side": side,
                "entry": float(current_signal["entry"]),
                "initial_stop": float(current_signal["stop_loss"]),
                "stop_loss": float(current_signal["stop_loss"]),
                "score": float(current_signal["score"]),
                "tqi": float(current_signal["tqi"]),
                "er": float(current_signal["er"]),
                "vol_z": float(current_signal["vol_z"]),
                "entry_index": int(i),
                "entry_model": "three_leg_split",
                "risk_fraction": 1.0 / 3.0,
                "tp1_r": float(current_signal["tp1_r"]),
            }
            legs = [
                {**base, "leg": 1, "target": float(current_signal["tp1"]), "target_r": float(current_signal["tp1_r"])},
                {**base, "leg": 2, "target": float(current_signal["tp2"]), "target_r": float(current_signal["tp2_r"])},
                {**base, "leg": 3, "target": float(current_signal["tp3"]), "target_r": float(current_signal["tp3_r"])},
            ]
            continue

        if not legs or i <= int(legs[0]["entry_index"]):
            continue

        side = legs[0]["side"]
        low = float(row["low"])
        high = float(row["high"])
        close = float(row["close"])

        stopped: list[dict[str, Any]] = []
        for leg in legs:
            stop_hit = low <= float(leg["stop_loss"]) if side == "BUY" else high >= float(leg["stop_loss"])
            if stop_hit:
                stopped.append(leg)
        if stopped:
            for leg in stopped:
                close_leg(leg, timestamp, float(leg["stop_loss"]), "stop")
            legs = [leg for leg in legs if leg not in stopped]
            if not legs:
                continue

        target_hits: list[dict[str, Any]] = []
        for leg in legs:
            target_hit = high >= float(leg["target"]) if side == "BUY" else low <= float(leg["target"])
            if target_hit:
                target_hits.append(leg)

        hit_legs = {int(leg["leg"]) for leg in target_hits}
        for leg in target_hits:
            close_leg(leg, timestamp, float(leg["target"]), "target")
        legs = [leg for leg in legs if leg not in target_hits]

        if 1 in hit_legs:
            for leg in legs:
                if int(leg["leg"]) in {2, 3}:
                    leg["stop_loss"] = float(leg["entry"])
        if 2 in hit_legs:
            for leg in legs:
                if int(leg["leg"]) == 3:
                    leg["stop_loss"] = (
                        float(leg["entry"]) + abs(float(leg["entry"]) - float(leg["initial_stop"])) * float(leg.get("tp1_r", 1.0))
                        if side == "BUY"
                        else float(leg["entry"]) - abs(float(leg["entry"]) - float(leg["initial_stop"])) * float(leg.get("tp1_r", 1.0))
                    )

        if legs and int(i) - int(legs[0]["entry_index"]) >= settings.trade_timeout_bars:
            for leg in legs:
                close_leg(leg, timestamp, close, "timeout")
            legs = []

    if legs:
        last = frame.iloc[-1]
        for leg in legs:
            close_leg(leg, last["time"], float(last["close"]), "end_of_data")

    return trades, frame
