from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

import pandas as pd

from .config import RiskConfig, SilverOptimizedConfig, SymbolConfig
from .indicators import adx, atr, crossed_over, crossed_under, ema, rsi
from .sessions import in_allowed_session, session_name
from .strategy import Signal
from .timeframes import TIMEFRAME_MINUTES, validate_timeframe
from .trade_geometry import invalid_market_geometry

PRESET_PARAMS: dict[str, dict[str, float | int]] = {
    "BTCUSD": {
        "fast_len": 34,
        "slow_len": 89,
        "htf_len": 200,
        "rsi_len": 14,
        "adx_min": 20.0,
        "atr_len": 14,
        "stop_atr": 2.8,
        "tp_atr": 4.5,
        "trail_atr": 2.1,
    },
    "XAGUSD": {
        "fast_len": 21,
        "slow_len": 55,
        "htf_len": 180,
        "rsi_len": 14,
        "adx_min": 19.0,
        "atr_len": 14,
        "stop_atr": 2.4,
        "tp_atr": 3.8,
        "trail_atr": 1.8,
    },
    "XAUUSD": {
        "fast_len": 21,
        "slow_len": 55,
        "htf_len": 200,
        "rsi_len": 14,
        "adx_min": 17.0,
        "atr_len": 14,
        "stop_atr": 2.0,
        "tp_atr": 3.2,
        "trail_atr": 1.5,
    },
}


@dataclass(frozen=True)
class SilverParams:
    preset: str
    fast_len: int
    slow_len: int
    htf_len: int
    rsi_len: int
    adx_min: float
    atr_len: int
    stop_atr: float
    tp_atr: float
    trail_atr: float


def _normalize_htf_timeframe(value: str) -> str:
    raw = str(value or "D1").strip().upper()
    if raw in {"D", "1D", "DAY"}:
        return "D1"
    return validate_timeframe(raw)


def _pandas_resample_rule(timeframe: str) -> str:
    tf = _normalize_htf_timeframe(timeframe)
    if tf == "D1":
        return "1D"
    if tf == "W1":
        return "1W"
    if tf == "MN1":
        return "1ME"
    if tf.startswith("H"):
        return f"{TIMEFRAME_MINUTES[tf] // 60}h"
    if tf.startswith("M"):
        return f"{TIMEFRAME_MINUTES[tf]}min"
    raise ValueError(f"Unsupported HTF timeframe: {timeframe}")


def resolve_preset(symbol_cfg: SymbolConfig, cfg: SilverOptimizedConfig) -> str:
    if cfg.preset != "auto":
        return cfg.preset.upper()
    key = symbol_cfg.key.upper()
    name = symbol_cfg.name.upper()
    if "BTC" in key:
        return "BTCUSD"
    if "XAG" in key or "SILVER" in name:
        return "XAGUSD"
    if "XAU" in key or "GOLD" in name:
        return "XAUUSD"
    return "CUSTOM"


def resolve_params(symbol_cfg: SymbolConfig, cfg: SilverOptimizedConfig) -> SilverParams:
    preset = resolve_preset(symbol_cfg, cfg)
    if preset in PRESET_PARAMS:
        values = PRESET_PARAMS[preset]
        return SilverParams(
            preset=preset,
            fast_len=int(values["fast_len"]),
            slow_len=int(values["slow_len"]),
            htf_len=int(values["htf_len"]),
            rsi_len=int(values["rsi_len"]),
            adx_min=float(values["adx_min"]),
            atr_len=int(values["atr_len"]),
            stop_atr=float(values["stop_atr"]),
            tp_atr=float(values["tp_atr"]),
            trail_atr=float(values["trail_atr"]),
        )
    return SilverParams(
        preset="CUSTOM",
        fast_len=cfg.custom_fast_len,
        slow_len=cfg.custom_slow_len,
        htf_len=cfg.custom_htf_len,
        rsi_len=cfg.custom_rsi_len,
        adx_min=cfg.custom_adx_min,
        atr_len=cfg.custom_atr_len,
        stop_atr=cfg.custom_stop_atr,
        tp_atr=cfg.custom_tp_atr,
        trail_atr=cfg.custom_trail_atr,
    )


def _merge_htf_ema(df: pd.DataFrame, htf_timeframe: str, htf_len: int) -> pd.Series:
    work = df.copy()
    work["time"] = pd.to_datetime(work["time"], utc=True)
    indexed = work.set_index("time")
    rule = _pandas_resample_rule(htf_timeframe)
    htf = indexed.resample(rule).agg({"close": "last"}).dropna()
    htf["htf_ema"] = ema(htf["close"], htf_len)
    merged = htf["htf_ema"].reindex(indexed.index, method="ffill")
    return merged.reset_index(drop=True)


def prepare_frame(
    df: pd.DataFrame,
    symbol_cfg: SymbolConfig,
    cfg: SilverOptimizedConfig,
) -> tuple[pd.DataFrame, SilverParams]:
    params = resolve_params(symbol_cfg, cfg)
    out = df.copy().reset_index(drop=True)
    out["ema_fast"] = ema(out["close"], params.fast_len)
    out["ema_slow"] = ema(out["close"], params.slow_len)
    out["htf_ema"] = _merge_htf_ema(out, cfg.htf_timeframe, params.htf_len)
    out["rsi"] = rsi(out["close"], params.rsi_len)
    out["atr"] = atr(out, params.atr_len)
    _, _, out["adx"] = adx(out, 14)
    out["atr_pct"] = out["atr"] / out["close"] * 100.0
    out["atr_pct_ma"] = out["atr_pct"].rolling(window=50, min_periods=50).mean()
    return out, params


def _allow_long(cfg: SilverOptimizedConfig) -> bool:
    return cfg.trade_direction in {"long_only", "long_and_short"}


def _allow_short(cfg: SilverOptimizedConfig) -> bool:
    return cfg.trade_direction in {"short_only", "long_and_short"}


def _make_signal(
    frame: pd.DataFrame,
    index: int,
    side: str,
    symbol_cfg: SymbolConfig,
    params: SilverParams,
    risk_cfg: RiskConfig | None,
) -> Signal | None:
    row = frame.iloc[index]
    time_value = row.time.to_pydatetime() if hasattr(row.time, "to_pydatetime") else row.time
    if risk_cfg and not in_allowed_session(time_value, symbol_cfg.sessions):
        return None

    entry = float(row.close)
    atr_val = float(row.atr)
    if side == "buy":
        sl = entry - atr_val * params.stop_atr
        tp = entry + atr_val * params.tp_atr
        tps = [tp]
    else:
        sl = entry + atr_val * params.stop_atr
        tp = entry - atr_val * params.tp_atr
        tps = [tp]
    risk_distance = abs(entry - sl)
    if risk_distance <= 0 or invalid_market_geometry(side, entry, sl, tps):
        return None

    setup_key = f"silver:{symbol_cfg.key}:{side}:{time_value.isoformat()}"
    return Signal(
        setup_id=sha1(setup_key.encode("utf-8")).hexdigest()[:8],
        symbol=symbol_cfg.symbol,
        market_key=symbol_cfg.key,
        name=symbol_cfg.name,
        side=side,
        time=time_value,
        entry=entry,
        sl=sl,
        tps=tps,
        lot_per_leg=symbol_cfg.lot_per_leg,
        risk_distance=risk_distance,
        session=session_name(time_value),
        reason=f"silver_optimized {side} adaptive trend pullback ({params.preset})",
        algorithm="silver_optimized",
        trail_atr_mult=params.trail_atr,
        ema_fast_len=params.fast_len,
        ema_slow_len=params.slow_len,
        atr_at_entry=atr_val,
    )


def _long_condition(frame: pd.DataFrame, index: int, cfg: SilverOptimizedConfig, params: SilverParams) -> bool:
    row = frame.iloc[index]
    if pd.isna(row.htf_ema) or pd.isna(row.adx) or pd.isna(row.atr_pct_ma):
        return False
    up_trend = row.close > row.htf_ema and row.ema_fast > row.ema_slow and row.close > row.ema_slow
    trend_strength = float(row.adx) >= params.adx_min
    vol_ok = not cfg.use_vol_filter or float(row.atr_pct) > float(row.atr_pct_ma) * 0.80
    recent_pullback = frame["rsi"].iloc[max(0, index - 7) : index + 1].min() < 48
    long_trigger = crossed_over(frame["close"], frame["ema_fast"], index) or crossed_over(frame["rsi"], 50, index)
    return bool(up_trend and trend_strength and vol_ok and recent_pullback and long_trigger)


def _short_condition(frame: pd.DataFrame, index: int, cfg: SilverOptimizedConfig, params: SilverParams) -> bool:
    row = frame.iloc[index]
    if pd.isna(row.htf_ema) or pd.isna(row.adx) or pd.isna(row.atr_pct_ma):
        return False
    down_trend = row.close < row.htf_ema and row.ema_fast < row.ema_slow and row.close < row.ema_slow
    trend_strength = float(row.adx) >= params.adx_min
    vol_ok = not cfg.use_vol_filter or float(row.atr_pct) > float(row.atr_pct_ma) * 0.80
    recent_pullback = frame["rsi"].iloc[max(0, index - 7) : index + 1].max() > 52
    short_trigger = crossed_under(frame["close"], frame["ema_fast"], index) or crossed_under(frame["rsi"], 50, index)
    return bool(down_trend and trend_strength and vol_ok and recent_pullback and short_trigger)


def generate_signals(
    df: pd.DataFrame,
    symbol_cfg: SymbolConfig,
    risk_cfg: RiskConfig | None,
    cfg: SilverOptimizedConfig,
) -> list[Signal]:
    frame, params = prepare_frame(df, symbol_cfg, cfg)
    warmup = max(params.htf_len, params.slow_len, 50, params.fast_len) + 8
    signals: list[Signal] = []
    for index in range(warmup, len(frame)):
        if _allow_long(cfg) and _long_condition(frame, index, cfg, params):
            signal = _make_signal(frame, index, "buy", symbol_cfg, params, risk_cfg)
            if signal is not None:
                signals.append(signal)
                continue
        if _allow_short(cfg) and _short_condition(frame, index, cfg, params):
            signal = _make_signal(frame, index, "sell", symbol_cfg, params, risk_cfg)
            if signal is not None:
                signals.append(signal)
    return signals


def signal_at_closed_index(
    df: pd.DataFrame,
    end_index: int,
    symbol_cfg: SymbolConfig,
    risk_cfg: RiskConfig | None,
    cfg: SilverOptimizedConfig,
) -> Signal | None:
    if end_index < 0 or end_index >= len(df):
        return None
    closed = df.iloc[: end_index + 1]
    signals = generate_signals(closed, symbol_cfg, risk_cfg, cfg)
    if not signals:
        return None
    latest = signals[-1]
    row_time = closed.iloc[-1]["time"]
    if hasattr(row_time, "to_pydatetime"):
        row_time = row_time.to_pydatetime()
    return latest if latest.time == row_time else None


def latest_closed_signal(
    df: pd.DataFrame,
    symbol_cfg: SymbolConfig,
    risk_cfg: RiskConfig | None,
    cfg: SilverOptimizedConfig,
) -> Signal | None:
    if len(df) < 2:
        return None
    closed = df.iloc[:-1]
    return signal_at_closed_index(closed, len(closed) - 1, symbol_cfg, risk_cfg, cfg)
