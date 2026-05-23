"""Box Theory strategy (removable module).

Daily previous-day high/low box + M15-style trap entries (John Wick hammer / shooting star).
Delete this file plus `signal_engine.py` routing and `box_theory` entries in strategy_modes/config/UI to uninstall.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha1

import pandas as pd

from .config import AppConfig, RiskConfig, SymbolConfig
from .sessions import in_allowed_session, session_name
from .strategy import Signal


@dataclass(frozen=True)
class BoxTheoryParams:
    zone_edge_fraction: float = 0.25
    aggressive_body_frac: float = 0.55
    aggressive_range_frac: float = 0.25
    wick_body_ratio_min: float = 2.0
    max_body_range_ratio: float = 0.35
    sl_buffer_frac: float = 0.005


def resolve_box_theory_params(config: AppConfig) -> BoxTheoryParams:
    cfg = config.box_theory
    return BoxTheoryParams(
        zone_edge_fraction=cfg.zone_edge_fraction,
        aggressive_body_frac=cfg.aggressive_body_frac,
        aggressive_range_frac=cfg.aggressive_range_frac,
        wick_body_ratio_min=cfg.wick_body_ratio_min,
        max_body_range_ratio=cfg.max_body_range_ratio,
        sl_buffer_frac=cfg.sl_buffer_frac,
    )


def _bar_date(value) -> object:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert("UTC")
    return ts.date()


def attach_previous_day_box(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["_date"] = out["time"].map(_bar_date)
    daily = out.groupby("_date", sort=True).agg(day_high=("high", "max"), day_low=("low", "min"))
    dates = list(daily.index)
    prev_high: list[float | None] = []
    prev_low: list[float | None] = []
    prev_mid: list[float | None] = []
    lookup: dict[object, tuple[float, float, float]] = {}
    for index in range(1, len(dates)):
        prev = daily.iloc[index - 1]
        high = float(prev.day_high)
        low = float(prev.day_low)
        lookup[dates[index]] = (high, low, (high + low) / 2.0)
    for date_value in out["_date"]:
        box = lookup.get(date_value)
        if box is None:
            prev_high.append(None)
            prev_low.append(None)
            prev_mid.append(None)
        else:
            prev_high.append(box[0])
            prev_low.append(box[1])
            prev_mid.append(box[2])
    out["box_high"] = prev_high
    out["box_low"] = prev_low
    out["box_mid"] = prev_mid
    return out


def box_zone(close: float, box_low: float, box_high: float, edge_fraction: float) -> str:
    height = box_high - box_low
    if height <= 0:
        return "none"
    position = (close - box_low) / height
    if position >= 1.0 - edge_fraction:
        return "top"
    if position <= edge_fraction:
        return "bottom"
    return "middle"


def _candle_parts(row) -> tuple[float, float, float, float, float, float, float, float]:
    open_price = float(row.open)
    high = float(row.high)
    low = float(row.low)
    close = float(row.close)
    range_size = high - low
    body = abs(close - open_price)
    if close >= open_price:
        lower_wick = open_price - low
        upper_wick = high - close
    else:
        lower_wick = close - low
        upper_wick = high - open_price
    return open_price, high, low, close, range_size, body, lower_wick, upper_wick


def is_aggressive_bear(row, box_height: float, params: BoxTheoryParams) -> bool:
    open_price, high, low, close, range_size, body, lower_wick, upper_wick = _candle_parts(row)
    if close >= open_price or range_size <= 0 or box_height <= 0:
        return False
    bear_body = open_price - close
    if bear_body / range_size < params.aggressive_body_frac:
        return False
    if range_size / box_height < params.aggressive_range_frac:
        return False
    return True


def is_aggressive_bull(row, box_height: float, params: BoxTheoryParams) -> bool:
    open_price, high, low, close, range_size, body, lower_wick, upper_wick = _candle_parts(row)
    if close <= open_price or range_size <= 0 or box_height <= 0:
        return False
    bull_body = close - open_price
    if bull_body / range_size < params.aggressive_body_frac:
        return False
    if range_size / box_height < params.aggressive_range_frac:
        return False
    return True


def is_john_wick_hammer(row, params: BoxTheoryParams) -> bool:
    open_price, high, low, close, range_size, body, lower_wick, upper_wick = _candle_parts(row)
    if close <= open_price or range_size <= 0:
        return False
    green_body = close - open_price
    hammer_lower = open_price - low
    if green_body / range_size > params.max_body_range_ratio:
        return False
    if green_body <= 0:
        return hammer_lower / range_size >= 0.5
    return hammer_lower / green_body >= params.wick_body_ratio_min


def is_shooting_star(row, params: BoxTheoryParams) -> bool:
    open_price, high, low, close, range_size, body, lower_wick, upper_wick = _candle_parts(row)
    if close >= open_price or range_size <= 0:
        return False
    red_body = open_price - close
    star_upper = high - open_price
    if red_body / range_size > params.max_body_range_ratio:
        return False
    if red_body <= 0:
        return star_upper / range_size >= 0.5
    return star_upper / red_body >= params.wick_body_ratio_min


def _make_signal(
    frame: pd.DataFrame,
    index: int,
    side: str,
    cfg: SymbolConfig,
    params: BoxTheoryParams,
    risk_cfg: RiskConfig | None,
    *,
    reason: str,
) -> Signal | None:
    row = frame.iloc[index]
    box_low = row.box_low
    box_high = row.box_high
    if pd.isna(box_low) or pd.isna(box_high):
        return None

    box_low_f = float(box_low)
    box_high_f = float(box_high)
    box_height = box_high_f - box_low_f
    if box_height <= 0:
        return None

    time_value = row.time.to_pydatetime() if hasattr(row.time, "to_pydatetime") else row.time
    if risk_cfg and not in_allowed_session(time_value, cfg.sessions):
        return None

    entry = float(row.close)
    buffer = box_height * params.sl_buffer_frac
    if side == "buy":
        trap = frame.iloc[index - 1]
        sl = float(trap.low) - buffer
        tp = box_high_f
        if not (sl < entry < tp):
            return None
    else:
        trap = frame.iloc[index - 1]
        sl = float(trap.high) + buffer
        tp = box_low_f
        if not (tp < entry < sl):
            return None

    risk_distance = abs(entry - sl)
    if risk_distance <= 0:
        return None

    setup_key = f"box_theory:{cfg.key}:{side}:{time_value.isoformat()}"
    return Signal(
        setup_id=sha1(setup_key.encode("utf-8")).hexdigest()[:8],
        symbol=cfg.symbol,
        market_key=cfg.key,
        name=cfg.name,
        side=side,
        time=time_value,
        entry=entry,
        sl=sl,
        tps=[tp],
        lot_per_leg=cfg.lot_per_leg,
        risk_distance=risk_distance,
        session=session_name(time_value),
        reason=reason,
    )


def generate_signals(
    df: pd.DataFrame,
    cfg: SymbolConfig,
    config: AppConfig,
    risk_cfg: RiskConfig | None = None,
) -> list[Signal]:
    params = resolve_box_theory_params(config)
    frame = attach_previous_day_box(df).reset_index(drop=True)
    signals: list[Signal] = []

    for index in range(2, len(frame)):
        row = frame.iloc[index]
        trap = frame.iloc[index - 1]
        aggressive = frame.iloc[index - 2]
        if pd.isna(row.box_low) or pd.isna(row.box_high):
            continue

        box_low = float(row.box_low)
        box_high = float(row.box_high)
        box_height = box_high - box_low
        if box_height <= 0:
            continue

        zone = box_zone(float(aggressive.close), box_low, box_high, params.zone_edge_fraction)
        if zone == "bottom":
            if not is_aggressive_bear(aggressive, box_height, params):
                continue
            if not is_john_wick_hammer(trap, params):
                continue
            if float(row.close) <= float(trap.high):
                continue
            signal = _make_signal(
                frame,
                index,
                "buy",
                cfg,
                params,
                risk_cfg,
                reason="Box Theory BUY: bottom trap + John Wick break",
            )
            if signal:
                signals.append(signal)
            continue

        if zone == "top":
            if not is_aggressive_bull(aggressive, box_height, params):
                continue
            if not is_shooting_star(trap, params):
                continue
            if float(row.close) >= float(trap.low):
                continue
            signal = _make_signal(
                frame,
                index,
                "sell",
                cfg,
                params,
                risk_cfg,
                reason="Box Theory SELL: top trap + shooting star break",
            )
            if signal:
                signals.append(signal)

    return signals


def signal_at_closed_index(
    df: pd.DataFrame,
    end_index: int,
    cfg: SymbolConfig,
    config: AppConfig,
    risk_cfg: RiskConfig,
) -> Signal | None:
    if end_index < 0 or end_index >= len(df):
        return None
    closed = df.iloc[: end_index + 1]
    signals = generate_signals(closed, cfg, config, risk_cfg)
    if not signals:
        return None
    latest = signals[-1]
    row_time = closed.iloc[-1]["time"]
    if hasattr(row_time, "to_pydatetime"):
        row_time = row_time.to_pydatetime()
    return latest if latest.time == row_time else None


def latest_closed_signal(df: pd.DataFrame, cfg: SymbolConfig, config: AppConfig, risk_cfg: RiskConfig) -> Signal | None:
    if len(df) < 2:
        return None
    closed = df.iloc[:-1]
    return signal_at_closed_index(closed, len(closed) - 1, cfg, config, risk_cfg)
