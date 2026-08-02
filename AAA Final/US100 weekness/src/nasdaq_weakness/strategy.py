from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from .config import Config
from .models import DayPlan, PlannedOrder


NY = ZoneInfo("America/New_York")
LONDON = ZoneInfo("Europe/London")
UTC = timezone.utc


def resample_bars(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    indexed = frame.set_index("time")
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "tick_volume": "sum",
        "spread": "median",
        "real_volume": "sum",
    }
    result = (
        indexed.resample(rule, label="left", closed="left")
        .agg(agg)
        .dropna(subset=["open", "high", "low", "close"])
        .reset_index()
    )
    return result


def _utc(local_date: date, value: tuple[int, int], zone: ZoneInfo) -> datetime:
    local = datetime.combine(
        local_date, time(value[0], value[1]), tzinfo=zone
    )
    return local.astimezone(UTC)


def _row_at(frame: pd.DataFrame, stamp: datetime):
    found = frame.loc[frame["time"] == pd.Timestamp(stamp)]
    return None if found.empty else found.iloc[0]


def _previous_h4(h4: pd.DataFrame, ny_open: datetime):
    complete = h4.loc[
        h4["time"] + pd.Timedelta(hours=4) <= pd.Timestamp(ny_open)
    ]
    if complete.empty:
        return None, complete
    return complete.iloc[-1], complete


def h4_trend(complete_h4: pd.DataFrame) -> str:
    if len(complete_h4) < 9:
        return "neutral"
    highs: list[float] = []
    lows: list[float] = []
    values_h = complete_h4["high"].to_numpy(dtype=float)
    values_l = complete_h4["low"].to_numpy(dtype=float)
    # A pivot is only usable after two bars have closed to its right.
    for index in range(2, len(complete_h4) - 2):
        if values_h[index] >= np.max(values_h[index - 2 : index + 3]):
            highs.append(float(values_h[index]))
        if values_l[index] <= np.min(values_l[index - 2 : index + 3]):
            lows.append(float(values_l[index]))
    if len(highs) >= 2 and len(lows) >= 2:
        if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
            return "bullish"
        if highs[-1] < highs[-2] and lows[-1] < lows[-2]:
            return "bearish"
    return "neutral"


def available_ny_dates(frame: pd.DataFrame) -> list[date]:
    local = frame["time"].dt.tz_convert(NY)
    return sorted(set(local.dt.date))


def build_day_plan(
    frame_m1: pd.DataFrame,
    symbol: str,
    ny_date: date,
    config: Config,
    m15: pd.DataFrame | None = None,
    h4: pd.DataFrame | None = None,
    as_of: datetime | None = None,
) -> DayPlan:
    m15 = resample_bars(frame_m1, "15min") if m15 is None else m15
    h4 = resample_bars(frame_m1, "4h") if h4 is None else h4
    ny_open = _utc(ny_date, (9, 30), NY)
    reference_time = _utc(ny_date, (9, 15), NY)
    candle1_time = ny_open
    candle2_time = _utc(ny_date, (9, 45), NY)
    signal2_time = _utc(ny_date, (10, 0), NY)
    expiry = _utc(ny_date, config.order_expiry_ny, NY)

    reference = _row_at(m15, reference_time)
    candle1 = _row_at(m15, candle1_time)
    candle2 = _row_at(m15, candle2_time)
    previous_h4, completed_h4 = _previous_h4(h4, ny_open)
    london_start = _utc(ny_date, (8, 0), LONDON)
    london = frame_m1.loc[
        (frame_m1["time"] >= pd.Timestamp(london_start))
        & (frame_m1["time"] < pd.Timestamp(ny_open))
    ]
    missing: list[str] = []
    if reference is None:
        missing.append("09:15 reference M15 candle")
    if candle1 is None:
        missing.append("09:30 NY candle 1")
    require_candle2 = as_of is None or as_of >= signal2_time
    if candle2 is None and require_candle2:
        missing.append("09:45 NY candle 2")
    if previous_h4 is None:
        missing.append("previous completed H4 candle")
    if london.empty:
        missing.append("London range")
    if missing:
        return DayPlan(
            symbol=symbol,
            ny_date=ny_date.isoformat(),
            setup="NONE",
            h4_trend="unknown",
            candle2_color="unknown",
            london_high=float("nan"),
            london_low=float("nan"),
            reference_high=float("nan"),
            reference_low=float("nan"),
            previous_h4_high=float("nan"),
            previous_h4_low=float("nan"),
            status="INVALID",
            reasons=("Missing " + ", ".join(missing),),
            orders=(),
        )

    trend = h4_trend(completed_h4)
    london_high = float(london["high"].max())
    london_low = float(london["low"].min())
    reference_high = float(reference["high"])
    reference_low = float(reference["low"])
    reference_mid = (reference_high + reference_low) / 2
    h4_high = float(previous_h4["high"])
    h4_low = float(previous_h4["low"])
    h4_mid = (h4_high + h4_low) / 2
    c2_color = "unknown"
    if candle2 is not None and require_candle2:
        c2_color = (
            "green"
            if float(candle2["close"]) > float(candle2["open"])
            else "red"
        )
    conversion = config.note_point_to_price
    target_rr = config.effective_target_rr
    reasons: list[str] = []
    orders: list[PlannedOrder] = []

    weakness = (
        float(candle1["open"]) < h4_mid
        and float(reference["close"]) < reference_mid
        and float(reference["close"]) <= reference_high
    )
    bullish_continuation = (
        trend == "bullish"
        and abs(london_high - float(candle1["high"])) < 200 * conversion
    )

    use_s1 = config.strategy_mode in {"S1", "ALL"} and weakness
    if use_s1:
        entry = float(candle1["open"])
        stop = entry + 50 * conversion
        fixed_target = entry - target_rr * (stop - entry)
        invalidation = max(reference_high, h4_mid)
        orders = [
            PlannedOrder(
                setup="S1",
                signal_time=ny_open,
                expiry_time=expiry,
                kind="MARKET",
                entry=entry,
                stop=stop,
                target=fixed_target,
                risk_share=0.5,
                invalidation_high=invalidation,
            ),
            PlannedOrder(
                setup="S1",
                signal_time=ny_open,
                expiry_time=expiry,
                kind="MARKET",
                entry=entry,
                stop=stop,
                target=fixed_target,
                risk_share=0.5,
                invalidation_high=invalidation,
                runner=True,
            ),
        ]
        reasons.extend(
            (
                "09:30 price below previous H4 midpoint",
                "reference M15 close below its midpoint",
                "split fixed 2R leg and trailing runner",
            )
        )
        setup = "S1"
    elif config.strategy_mode == "S1":
        setup = "NONE"
        reasons.append("Nasdaq weakness filter not confirmed at 09:30")
    elif bullish_continuation:
        setup = "NONE"
        reasons.append("Bullish H4 continuation filter rejected the short")
    elif c2_color == "green" and config.strategy_mode in {"S2A", "ALL"}:
        stop = london_high + 10 * conversion
        entries = (
            (("MARKET", float(candle2["close"])),)
            if config.s2a_entry_model == "DIRECT"
            else (
                ("SELL_LIMIT", reference_high),
                ("SELL_STOP", reference_low),
            )
        )
        if stop <= max(value for _, value in entries):
            setup = "NONE"
            reasons.append("London-high stop is not above both short entries")
        else:
            setup = "S2A"
            share = 1.0 if len(entries) == 1 else 0.5
            for kind, entry in entries:
                risk = stop - entry
                orders.append(
                    PlannedOrder(
                        setup=setup,
                        signal_time=signal2_time,
                        expiry_time=expiry,
                        kind=kind,
                        entry=entry,
                        stop=stop,
                        target=entry - target_rr * risk,
                        risk_share=share,
                        invalidation_high=london_high,
                    )
                )
            reasons.extend(
                (
                    "NY candle 2 closed green",
                    (
                        "direct post-10:00 fade"
                        if config.s2a_entry_model == "DIRECT"
                        else "fade entries at both reference-candle edges"
                    ),
                    f"target {target_rr:.1f}R cap",
                )
            )
    elif c2_color == "red" and config.strategy_mode in {"S2B", "ALL"}:
        setup = "S2B"
        red_high = float(candle2["high"])
        red_low = float(candle2["low"])
        red_mid = (red_high + red_low) / 2
        entries = (
            (
                (
                    "SELL_LIMIT",
                    float(candle2["close"]) + 50 * conversion,
                ),
            )
            if config.s2b_entry_model == "CLOSE_PLUS_50"
            else (("SELL_LIMIT", red_mid), ("SELL_STOP", red_low))
        )
        share = 1.0 if len(entries) == 1 else 0.5
        for kind, entry in entries:
            stop = entry + 100 * conversion
            orders.append(
                PlannedOrder(
                    setup=setup,
                    signal_time=signal2_time,
                    expiry_time=expiry,
                    kind=kind,
                    entry=entry,
                    stop=stop,
                    target=entry - target_rr * (stop - entry),
                    risk_share=share,
                    invalidation_high=max(red_high, london_high),
                )
            )
        reasons.extend(
            (
                "NY candle 2 closed red",
                (
                    "sell limit 50 configured points above candle-2 close"
                    if config.s2b_entry_model == "CLOSE_PLUS_50"
                    else "midpoint pullback plus red-low continuation orders"
                ),
                f"target {target_rr:.1f}R cap",
            )
        )
    else:
        setup = "NONE"
        reasons.append(
            f"Candle-2 color {c2_color} does not match enabled setup "
            f"{config.strategy_mode}"
        )

    status = "VALID" if orders else "WAITING"
    if orders and as_of is not None and as_of >= expiry:
        status = "EXPIRED"
        reasons.append("Signal window expired; no late entry is allowed")
    return DayPlan(
        symbol=symbol,
        ny_date=ny_date.isoformat(),
        setup=setup,
        h4_trend=trend,
        candle2_color=c2_color,
        london_high=london_high,
        london_low=london_low,
        reference_high=reference_high,
        reference_low=reference_low,
        previous_h4_high=h4_high,
        previous_h4_low=h4_low,
        status=status,
        reasons=tuple(reasons),
        orders=tuple(orders),
    )


def plans_between(
    frame_m1: pd.DataFrame,
    symbol: str,
    config: Config,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[DayPlan]:
    plans: list[DayPlan] = []
    m15 = resample_bars(frame_m1, "15min")
    h4 = resample_bars(frame_m1, "4h")
    for value in available_ny_dates(frame_m1):
        if start_date is not None and value < start_date:
            continue
        if end_date is not None and value > end_date:
            continue
        plan = build_day_plan(frame_m1, symbol, value, config, m15, h4)
        if plan.orders:
            plans.append(plan)
    return plans
