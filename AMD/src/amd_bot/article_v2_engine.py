from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math

import pandas as pd

from .config import Config
from .engine import (
    Trade,
    _find_limit_fill,
    ask,
    combine,
    regime_states,
    resample_ohlc,
)


@dataclass(frozen=True, slots=True)
class V2Params:
    """AMD v2 research parameters.

    Reversals require a liquidity sweep, local market-structure shift,
    displacement/FVG, and a subsequent limit retest. Continuations require a
    displacement close outside the Asia range followed by a confirmed hold.
    """

    enable_reversal: bool = True
    enable_continuation: bool = True
    trade_london: bool = True
    trade_new_york: bool = False
    max_trades_per_day: int = 1
    reversal_rr: float = 2.0
    continuation_rr: float = 2.0
    sweep_min_fraction: float = 0.02
    sweep_max_fraction: float = 0.60
    mss_lookback_bars: int = 3
    displacement_lookahead_bars: int = 8
    displacement_range_factor: float = 1.20
    displacement_body_fraction: float = 0.55
    displacement_close_location: float = 0.70
    fvg_min_fraction: float = 0.005
    fvg_entry_fraction: float = 0.50
    fvg_retest_bars: int = 12
    breakout_min_fraction: float = 0.04
    breakout_max_fraction: float = 0.60
    breakout_retest_tolerance_fraction: float = 0.04
    breakout_retest_bars: int = 12
    breakout_hold_fraction: float = 0.01
    continuation_require_fvg: bool = True
    stop_buffer_fraction: float = 0.03
    max_risk_fraction: float = 0.85
    volume_factor: float = 0.0
    require_vwap_alignment: bool = False
    use_regime_filter: bool = True
    london_window_minutes: int = 240
    ny_window_minutes: int = 180
    management_mode: str = "none"
    protect_trigger_r: float = 1.0
    protect_profit_r: float = 0.0
    partial_fraction: float = 0.0
    trail_start_r: float = 2.0
    trail_distance_r: float = 1.0


@dataclass(frozen=True, slots=True)
class V2Candidate:
    phase: str
    side: str
    signal_time: datetime
    entry_time: datetime
    entry_idx: int
    entry: float
    stop: float
    target: float
    liquidity_level: float


def _completed_m5(frame: pd.DataFrame) -> pd.DataFrame:
    bars = resample_ohlc(frame, "5min")
    if bars.empty:
        return bars
    bars["end_time"] = bars["time"] + pd.Timedelta(minutes=5)
    bars["range"] = bars["high"] - bars["low"]
    bars["prior_range_median"] = (
        bars["range"].shift(1).rolling(12, min_periods=6).median()
    )
    bars["prior_volume_median"] = (
        bars["tick_volume"].shift(1).rolling(12, min_periods=6).median()
    )
    typical = (bars["high"] + bars["low"] + bars["close"]) / 3.0
    weighted = typical * bars["tick_volume"].clip(lower=1)
    bars["vwap"] = weighted.cumsum() / bars["tick_volume"].clip(
        lower=1
    ).cumsum()
    return bars.reset_index(drop=True)


def _directional_quality(
    row: pd.Series,
    side: str,
    params: V2Params,
    *,
    require_displacement: bool,
) -> bool:
    candle_range = float(row["high"]) - float(row["low"])
    if candle_range <= 0:
        return False
    open_price = float(row["open"])
    close = float(row["close"])
    if side == "buy" and close <= open_price:
        return False
    if side == "sell" and close >= open_price:
        return False
    body_fraction = abs(close - open_price) / candle_range
    minimum_body = (
        params.displacement_body_fraction
        if require_displacement
        else min(params.displacement_body_fraction, 0.25)
    )
    if body_fraction < minimum_body:
        return False
    close_location = (
        (close - float(row["low"])) / candle_range
        if side == "buy"
        else (float(row["high"]) - close) / candle_range
    )
    minimum_location = (
        params.displacement_close_location
        if require_displacement
        else min(params.displacement_close_location, 0.55)
    )
    if close_location < minimum_location:
        return False
    if require_displacement:
        median_range = float(row.get("prior_range_median", math.nan))
        if not math.isfinite(median_range):
            return False
        if candle_range < median_range * params.displacement_range_factor:
            return False
    if params.volume_factor > 0:
        median_volume = float(row.get("prior_volume_median", math.nan))
        if not math.isfinite(median_volume):
            return False
        if float(row["tick_volume"]) < median_volume * params.volume_factor:
            return False
    if params.require_vwap_alignment:
        vwap = float(row.get("vwap", math.nan))
        if not math.isfinite(vwap):
            return False
        if side == "buy" and close < vwap:
            return False
        if side == "sell" and close > vwap:
            return False
    return True


def _fvg(
    bars: pd.DataFrame,
    position: int,
    side: str,
    minimum_gap: float,
) -> tuple[float, float] | None:
    if position < 2:
        return None
    first = bars.iloc[position - 2]
    third = bars.iloc[position]
    if side == "buy":
        lower = float(first["high"])
        upper = float(third["low"])
    else:
        lower = float(third["high"])
        upper = float(first["low"])
    if upper - lower < minimum_gap:
        return None
    return lower, upper


def _m1_market_entry(
    frame: pd.DataFrame,
    when: datetime,
    side: str,
    point: float,
) -> tuple[int, float] | None:
    eligible = frame.index[frame["time"] >= when]
    if not len(eligible):
        return None
    idx = int(eligible[0])
    row = frame.loc[idx]
    price = ask(row, "open", point) if side == "buy" else float(row["open"])
    return idx, price


def _risk_valid(
    entry: float,
    stop: float,
    asia_range: float,
    point: float,
    params: V2Params,
) -> bool:
    risk = abs(entry - stop)
    return bool(
        risk > point
        and (
            params.max_risk_fraction <= 0
            or risk <= asia_range * params.max_risk_fraction
        )
    )


def _reversal_candidates(
    bars: pd.DataFrame,
    day_frame: pd.DataFrame,
    point: float,
    phase: str,
    start: datetime,
    end: datetime,
    asia_high: float,
    asia_low: float,
    params: V2Params,
) -> list[V2Candidate]:
    asia_range = asia_high - asia_low
    minimum_sweep = asia_range * params.sweep_min_fraction
    maximum_sweep = asia_range * params.sweep_max_fraction
    minimum_gap = max(asia_range * params.fvg_min_fraction, point)
    stop_buffer = max(asia_range * params.stop_buffer_fraction, point)
    session_positions = bars.index[
        (bars["time"] >= start) & (bars["time"] < end)
    ].tolist()
    result: list[V2Candidate] = []
    for sweep_position in session_positions:
        sweep = bars.iloc[sweep_position]
        high_sweep = float(sweep["high"]) - asia_high
        low_sweep = asia_low - float(sweep["low"])
        if (
            minimum_sweep <= high_sweep <= maximum_sweep
            and float(sweep["close"]) < asia_high
        ):
            side = "sell"
            liquidity = asia_high
            structural_stop = float(sweep["high"]) + stop_buffer
        elif (
            minimum_sweep <= low_sweep <= maximum_sweep
            and float(sweep["close"]) > asia_low
        ):
            side = "buy"
            liquidity = asia_low
            structural_stop = float(sweep["low"]) - stop_buffer
        else:
            continue
        reference_start = max(0, sweep_position - params.mss_lookback_bars)
        reference = bars.iloc[reference_start:sweep_position]
        if reference.empty:
            continue
        structure_level = (
            float(reference["high"].max())
            if side == "buy"
            else float(reference["low"].min())
        )
        confirmation_end = min(
            len(bars),
            sweep_position + 1 + params.displacement_lookahead_bars,
        )
        for confirmation_position in range(
            sweep_position + 1,
            confirmation_end,
        ):
            confirmation = bars.iloc[confirmation_position]
            if confirmation["time"] >= end:
                break
            close = float(confirmation["close"])
            structure_broken = (
                close > structure_level
                if side == "buy"
                else close < structure_level
            )
            if not structure_broken:
                continue
            if not _directional_quality(
                confirmation,
                side,
                params,
                require_displacement=True,
            ):
                continue
            gap = _fvg(bars, confirmation_position, side, minimum_gap)
            if gap is None:
                continue
            lower, upper = gap
            entry = lower + (upper - lower) * params.fvg_entry_fraction
            fill_start = confirmation["end_time"].to_pydatetime()
            fill_end = min(
                end,
                fill_start
                + timedelta(minutes=5 * params.fvg_retest_bars),
            )
            fill_idx = _find_limit_fill(
                day_frame,
                side,
                entry,
                fill_start,
                fill_end,
                point,
            )
            if fill_idx is None:
                continue
            if not _risk_valid(
                entry,
                structural_stop,
                asia_range,
                point,
                params,
            ):
                continue
            risk = abs(entry - structural_stop)
            target = (
                entry + params.reversal_rr * risk
                if side == "buy"
                else entry - params.reversal_rr * risk
            )
            result.append(
                V2Candidate(
                    phase=f"{phase}_v2_reversal",
                    side=side,
                    signal_time=fill_start,
                    entry_time=day_frame.at[fill_idx, "time"].to_pydatetime(),
                    entry_idx=fill_idx,
                    entry=entry,
                    stop=structural_stop,
                    target=target,
                    liquidity_level=liquidity,
                )
            )
            break
    return result


def _continuation_candidates(
    bars: pd.DataFrame,
    day_frame: pd.DataFrame,
    point: float,
    phase: str,
    start: datetime,
    end: datetime,
    asia_high: float,
    asia_low: float,
    params: V2Params,
) -> list[V2Candidate]:
    asia_range = asia_high - asia_low
    minimum_breakout = asia_range * params.breakout_min_fraction
    maximum_breakout = asia_range * params.breakout_max_fraction
    minimum_gap = max(asia_range * params.fvg_min_fraction, point)
    tolerance = asia_range * params.breakout_retest_tolerance_fraction
    stop_buffer = max(asia_range * params.stop_buffer_fraction, point)
    session_positions = bars.index[
        (bars["time"] >= start) & (bars["time"] < end)
    ].tolist()
    result: list[V2Candidate] = []
    for breakout_position in session_positions:
        breakout = bars.iloc[breakout_position]
        upper_break = float(breakout["close"]) - asia_high
        lower_break = asia_low - float(breakout["close"])
        if minimum_breakout <= upper_break <= maximum_breakout:
            side = "buy"
            edge = asia_high
        elif minimum_breakout <= lower_break <= maximum_breakout:
            side = "sell"
            edge = asia_low
        else:
            continue
        if not _directional_quality(
            breakout,
            side,
            params,
            require_displacement=True,
        ):
            continue
        if (
            params.continuation_require_fvg
            and _fvg(bars, breakout_position, side, minimum_gap) is None
        ):
            continue
        retest_end = min(
            len(bars),
            breakout_position + 1 + params.breakout_retest_bars,
        )
        for retest_position in range(breakout_position + 1, retest_end):
            retest = bars.iloc[retest_position]
            if retest["time"] >= end:
                break
            if side == "buy":
                confirmed = bool(
                    float(retest["low"]) <= edge + tolerance
                    and float(retest["close"])
                    >= edge + asia_range * params.breakout_hold_fraction
                )
            else:
                confirmed = bool(
                    float(retest["high"]) >= edge - tolerance
                    and float(retest["close"])
                    <= edge - asia_range * params.breakout_hold_fraction
                )
            if not confirmed or not _directional_quality(
                retest,
                side,
                params,
                require_displacement=False,
            ):
                continue
            market = _m1_market_entry(
                day_frame,
                retest["end_time"].to_pydatetime(),
                side,
                point,
            )
            if market is None:
                break
            entry_idx, entry = market
            stop = (
                min(float(retest["low"]) - stop_buffer, edge - stop_buffer)
                if side == "buy"
                else max(float(retest["high"]) + stop_buffer, edge + stop_buffer)
            )
            if not _risk_valid(entry, stop, asia_range, point, params):
                break
            risk = abs(entry - stop)
            target = (
                entry + params.continuation_rr * risk
                if side == "buy"
                else entry - params.continuation_rr * risk
            )
            result.append(
                V2Candidate(
                    phase=f"{phase}_v2_continuation",
                    side=side,
                    signal_time=retest["end_time"].to_pydatetime(),
                    entry_time=day_frame.at[entry_idx, "time"].to_pydatetime(),
                    entry_idx=entry_idx,
                    entry=entry,
                    stop=stop,
                    target=target,
                    liquidity_level=edge,
                )
            )
            break
    return result


def v2_candidates_for_day(
    day_frame: pd.DataFrame,
    point: float,
    config: Config,
    params: V2Params,
    day: date,
) -> tuple[list[V2Candidate], float, float]:
    asia_start = combine(day, config.asia_start)
    asia_end = combine(day, config.asia_end)
    asia = day_frame.loc[
        (day_frame["time"] >= asia_start)
        & (day_frame["time"] < asia_end)
    ]
    if len(asia) < 120:
        return [], math.nan, math.nan
    asia_high = float(asia["high"].max())
    asia_low = float(asia["low"].min())
    if asia_high <= asia_low:
        return [], asia_high, asia_low
    bars = _completed_m5(day_frame)
    sessions: list[tuple[str, datetime, datetime]] = []
    if params.trade_london:
        start = combine(day, config.london_start)
        sessions.append(
            (
                "london",
                start,
                start + timedelta(minutes=params.london_window_minutes),
            )
        )
    if params.trade_new_york:
        start = combine(day, config.ny_start)
        sessions.append(
            (
                "new_york",
                start,
                start + timedelta(minutes=params.ny_window_minutes),
            )
        )
    candidates: list[V2Candidate] = []
    for phase, start, end in sessions:
        session_candidates: list[V2Candidate] = []
        if params.enable_reversal:
            session_candidates.extend(
                _reversal_candidates(
                    bars,
                    day_frame,
                    point,
                    phase,
                    start,
                    end,
                    asia_high,
                    asia_low,
                    params,
                )
            )
        if params.enable_continuation:
            session_candidates.extend(
                _continuation_candidates(
                    bars,
                    day_frame,
                    point,
                    phase,
                    start,
                    end,
                    asia_high,
                    asia_low,
                    params,
                )
            )
        if session_candidates:
            candidates.append(
                min(
                    session_candidates,
                    key=lambda candidate: candidate.entry_time,
                )
            )
    candidates.sort(key=lambda candidate: candidate.entry_time)
    return candidates[: params.max_trades_per_day], asia_high, asia_low


def _simulate_v2_trade(
    frame: pd.DataFrame,
    symbol: str,
    session_date: date,
    candidate: V2Candidate,
    force_exit: datetime,
    point: float,
    params: V2Params,
    asia_high: float,
    asia_low: float,
) -> Trade:
    entry = candidate.entry
    stop = candidate.stop
    side = candidate.side
    risk = abs(entry - stop)
    if risk <= 0:
        raise ValueError("Trade risk must be positive")
    mode = params.management_mode
    if mode not in {"none", "be_confirmed", "partial_be", "trail"}:
        raise ValueError(f"Unsupported management mode: {mode}")
    partial_fraction = (
        params.partial_fraction if mode == "partial_be" else 0.0
    )
    if not 0 <= partial_fraction < 1:
        raise ValueError("partial_fraction must be in [0, 1)")
    current_stop = stop
    protected = False
    partial_taken = False
    remaining = 1.0
    realized_r = 0.0
    favorable_price = entry
    exit_idx = candidate.entry_idx
    runner_r = 0.0
    exit_reason = "force_exit"
    mae_r = 0.0
    window = frame.loc[
        (frame.index >= candidate.entry_idx) & (frame["time"] < force_exit)
    ]
    for idx, row in window.iterrows():
        exit_idx = int(idx)
        bid_low = float(row["low"])
        bid_high = float(row["high"])
        ask_low = ask(row, "low", point)
        ask_high = ask(row, "high", point)
        if side == "buy":
            mae_r = max(mae_r, max(0.0, entry - bid_low) / risk)
            if bid_low <= current_stop:
                runner_r = (current_stop - entry) / risk
                exit_reason = "protected_stop" if protected else "stop"
                break
            if bid_high >= candidate.target:
                runner_r = (candidate.target - entry) / risk
                exit_reason = "target"
                break
            if (
                partial_fraction > 0
                and not partial_taken
                and bid_high >= entry + params.protect_trigger_r * risk
            ):
                realized_r += partial_fraction * params.protect_trigger_r
                remaining -= partial_fraction
                partial_taken = True
            favorable_price = max(favorable_price, bid_high)
        else:
            mae_r = max(mae_r, max(0.0, ask_high - entry) / risk)
            if ask_high >= current_stop:
                runner_r = (entry - current_stop) / risk
                exit_reason = "protected_stop" if protected else "stop"
                break
            if ask_low <= candidate.target:
                runner_r = (entry - candidate.target) / risk
                exit_reason = "target"
                break
            if (
                partial_fraction > 0
                and not partial_taken
                and ask_low <= entry - params.protect_trigger_r * risk
            ):
                realized_r += partial_fraction * params.protect_trigger_r
                remaining -= partial_fraction
                partial_taken = True
            favorable_price = min(favorable_price, ask_low)
        bar_end = pd.Timestamp(row["time"]) + pd.Timedelta(minutes=1)
        completed_m5 = bar_end.minute % 5 == 0
        if (
            mode in {"be_confirmed", "partial_be", "trail"}
            and not protected
            and completed_m5
        ):
            close = (
                float(row["close"])
                if side == "buy"
                else ask(row, "close", point)
            )
            confirmed = (
                close >= entry + params.protect_trigger_r * risk
                if side == "buy"
                else close <= entry - params.protect_trigger_r * risk
            )
            if confirmed:
                current_stop = (
                    entry + params.protect_profit_r * risk
                    if side == "buy"
                    else entry - params.protect_profit_r * risk
                )
                protected = True
        if mode == "trail":
            favorable_r = (
                (favorable_price - entry) / risk
                if side == "buy"
                else (entry - favorable_price) / risk
            )
            if favorable_r >= params.trail_start_r:
                trailing_stop = (
                    favorable_price - params.trail_distance_r * risk
                    if side == "buy"
                    else favorable_price + params.trail_distance_r * risk
                )
                current_stop = (
                    max(current_stop, trailing_stop)
                    if side == "buy"
                    else min(current_stop, trailing_stop)
                )
                protected = True
    else:
        if not window.empty:
            exit_idx = int(window.index[-1])
            row = frame.loc[exit_idx]
            exit_price = (
                float(row["close"])
                if side == "buy"
                else ask(row, "close", point)
            )
            runner_r = (
                (exit_price - entry) / risk
                if side == "buy"
                else (entry - exit_price) / risk
            )
    pnl_r = realized_r + remaining * runner_r
    synthetic_exit = (
        entry + pnl_r * risk
        if side == "buy"
        else entry - pnl_r * risk
    )
    if partial_taken:
        exit_reason = f"partial_{exit_reason}"
    return Trade(
        symbol=symbol,
        session_date=session_date.isoformat(),
        phase=candidate.phase,
        side=side,
        signal_time=candidate.signal_time.isoformat(),
        entry_time=frame.at[candidate.entry_idx, "time"].isoformat(),
        exit_time=frame.at[exit_idx, "time"].isoformat(),
        entry=entry,
        initial_stop=stop,
        final_stop=current_stop,
        target=candidate.target,
        exit_price=synthetic_exit,
        initial_risk=risk,
        pnl_r=pnl_r,
        mae_r=mae_r,
        exit_reason=exit_reason,
        stop_locked=protected,
        asia_high=asia_high,
        asia_low=asia_low,
        asia_range=asia_high - asia_low,
        liquidity_level=candidate.liquidity_level,
    )


def backtest_v2_model(
    frame: pd.DataFrame,
    symbol: str,
    point: float,
    config: Config,
    params: V2Params,
    start: datetime,
    end: datetime,
) -> list[Trade]:
    states = regime_states(frame, config) if params.use_regime_filter else {}
    source = frame.loc[(frame["time"] >= start) & (frame["time"] < end)].copy()
    source = source.reset_index(drop=True)
    if source.empty:
        return []
    source["_session_date"] = source["time"].dt.date
    daily_frames = {
        day: group.drop(columns="_session_date").reset_index(drop=True)
        for day, group in source.groupby("_session_date", sort=False)
    }
    trades: list[Trade] = []
    dates = pd.date_range(start.date(), end.date(), freq="D", inclusive="left")
    for stamp in dates:
        day = stamp.date()
        day_frame = daily_frames.get(day)
        if day_frame is None or day_frame.empty:
            continue
        if params.use_regime_filter:
            state = states.get(day)
            if state is None or not state.allowed:
                continue
        candidates, asia_high, asia_low = v2_candidates_for_day(
            day_frame,
            point,
            config,
            params,
            day,
        )
        if not math.isfinite(asia_high) or not math.isfinite(asia_low):
            continue
        for candidate in candidates:
            trades.append(
                _simulate_v2_trade(
                    day_frame,
                    symbol,
                    day,
                    candidate,
                    combine(day, config.force_exit),
                    point,
                    params,
                    asia_high,
                    asia_low,
                )
            )
    return trades
