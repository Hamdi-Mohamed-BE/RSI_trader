from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import math

import pandas as pd

from .config import Config
from .engine import (
    Trade,
    _simulate_open_trade,
    ask,
    combine,
    regime_states,
    resample_ohlc,
)


@dataclass(frozen=True, slots=True)
class ArticleParams:
    """Mechanical translation of the article's two executable AMD patterns."""

    enable_fade: bool = True
    enable_distribution: bool = True
    trade_london: bool = True
    trade_new_york: bool = True
    max_trades_per_day: int = 2
    fade_rr: float = 2.0
    distribution_rr: float = 2.0
    sweep_min_fraction: float = 0.02
    sweep_max_fraction: float = 0.60
    breakout_fraction: float = 0.03
    retest_tolerance_fraction: float = 0.04
    stop_buffer_fraction: float = 0.03
    volume_factor: float = 0.0
    use_regime_filter: bool = False
    london_window_minutes: int = 240
    ny_window_minutes: int = 180


@dataclass(frozen=True, slots=True)
class Candidate:
    phase: str
    side: str
    signal_time: datetime
    entry_time: datetime
    entry: float
    stop: float
    target: float
    liquidity_level: float


def params_from_config(config: Config) -> ArticleParams:
    return ArticleParams(
        enable_fade=config.article_enable_fade,
        enable_distribution=config.article_enable_distribution,
        trade_london=config.article_trade_london,
        trade_new_york=config.article_trade_new_york,
        max_trades_per_day=config.article_max_trades_per_day,
        fade_rr=config.article_fade_rr,
        distribution_rr=config.article_distribution_rr,
        sweep_min_fraction=config.article_sweep_min_fraction,
        sweep_max_fraction=config.article_sweep_max_fraction,
        breakout_fraction=config.article_breakout_fraction,
        retest_tolerance_fraction=config.article_retest_tolerance_fraction,
        stop_buffer_fraction=config.article_stop_buffer_fraction,
        volume_factor=config.article_volume_factor,
        use_regime_filter=config.regime_filter_enabled,
        london_window_minutes=config.article_london_window_minutes,
        ny_window_minutes=config.article_ny_window_minutes,
    )


def _completed_m5(day_frame: pd.DataFrame) -> pd.DataFrame:
    bars = resample_ohlc(day_frame, "5min")
    if bars.empty:
        return bars
    bars["end_time"] = bars["time"] + pd.Timedelta(minutes=5)
    bars["prior_volume_median"] = (
        bars["tick_volume"].shift(1).rolling(6, min_periods=3).median()
    )
    return bars


def _volume_ok(row: pd.Series, factor: float) -> bool:
    if factor <= 0:
        return True
    median = float(row.get("prior_volume_median", math.nan))
    return math.isfinite(median) and float(row["tick_volume"]) >= median * factor


def _next_m1_index(day_frame: pd.DataFrame, when: datetime) -> int | None:
    eligible = day_frame.index[day_frame["time"] >= when]
    return int(eligible[0]) if len(eligible) else None


def _market_entry(
    day_frame: pd.DataFrame,
    idx: int,
    side: str,
    point: float,
) -> float:
    row = day_frame.loc[idx]
    return (
        ask(row, "open", point)
        if side == "buy"
        else float(row["open"])
    )


def _fade_candidates(
    bars: pd.DataFrame,
    day_frame: pd.DataFrame,
    point: float,
    phase_prefix: str,
    start: datetime,
    end: datetime,
    asia_high: float,
    asia_low: float,
    params: ArticleParams,
) -> list[Candidate]:
    asia_range = asia_high - asia_low
    session = bars.loc[(bars["time"] >= start) & (bars["time"] < end)]
    result: list[Candidate] = []
    minimum = asia_range * params.sweep_min_fraction
    maximum = asia_range * params.sweep_max_fraction
    stop_buffer = max(asia_range * params.stop_buffer_fraction, point)
    for _, row in session.iterrows():
        if not _volume_ok(row, params.volume_factor):
            continue
        high_sweep = float(row["high"]) - asia_high
        low_sweep = asia_low - float(row["low"])
        side: str | None = None
        liquidity = math.nan
        structural_stop = math.nan
        if (
            minimum <= high_sweep <= maximum
            and float(row["close"]) < asia_high
        ):
            side = "sell"
            liquidity = asia_high
            structural_stop = float(row["high"]) + stop_buffer
        elif (
            minimum <= low_sweep <= maximum
            and float(row["close"]) > asia_low
        ):
            side = "buy"
            liquidity = asia_low
            structural_stop = float(row["low"]) - stop_buffer
        if side is None:
            continue
        entry_time = row["end_time"].to_pydatetime()
        entry_idx = _next_m1_index(day_frame, entry_time)
        if entry_idx is None:
            continue
        entry = _market_entry(day_frame, entry_idx, side, point)
        risk = abs(entry - structural_stop)
        if risk <= point:
            continue
        target = (
            entry + params.fade_rr * risk
            if side == "buy"
            else entry - params.fade_rr * risk
        )
        result.append(
            Candidate(
                phase=f"{phase_prefix}_fade",
                side=side,
                signal_time=entry_time,
                entry_time=entry_time,
                entry=entry,
                stop=structural_stop,
                target=target,
                liquidity_level=liquidity,
            )
        )
    return result


def _distribution_candidates(
    bars: pd.DataFrame,
    day_frame: pd.DataFrame,
    point: float,
    phase_prefix: str,
    start: datetime,
    end: datetime,
    asia_high: float,
    asia_low: float,
    params: ArticleParams,
) -> list[Candidate]:
    asia_range = asia_high - asia_low
    session = bars.loc[(bars["time"] >= start) & (bars["time"] < end)].copy()
    if session.empty:
        return []
    breakout_distance = asia_range * params.breakout_fraction
    tolerance = asia_range * params.retest_tolerance_fraction
    stop_buffer = max(asia_range * params.stop_buffer_fraction, point)
    result: list[Candidate] = []
    rows = list(session.iterrows())
    for position, (_, breakout) in enumerate(rows):
        if not _volume_ok(breakout, params.volume_factor):
            continue
        side: str | None = None
        edge = math.nan
        if float(breakout["close"]) >= asia_high + breakout_distance:
            side = "buy"
            edge = asia_high
        elif float(breakout["close"]) <= asia_low - breakout_distance:
            side = "sell"
            edge = asia_low
        if side is None:
            continue
        for _, retest in rows[position + 1 :]:
            if retest["time"] >= end:
                break
            bullish_confirmation = (
                float(retest["low"]) <= edge + tolerance
                and float(retest["close"]) >= edge
                and float(retest["close"]) > float(retest["open"])
            )
            bearish_confirmation = (
                float(retest["high"]) >= edge - tolerance
                and float(retest["close"]) <= edge
                and float(retest["close"]) < float(retest["open"])
            )
            if side == "buy" and not bullish_confirmation:
                continue
            if side == "sell" and not bearish_confirmation:
                continue
            if not _volume_ok(retest, params.volume_factor):
                continue
            entry_time = retest["end_time"].to_pydatetime()
            entry_idx = _next_m1_index(day_frame, entry_time)
            if entry_idx is None:
                break
            entry = _market_entry(day_frame, entry_idx, side, point)
            stop = (
                min(float(retest["low"]) - stop_buffer, edge - stop_buffer)
                if side == "buy"
                else max(float(retest["high"]) + stop_buffer, edge + stop_buffer)
            )
            risk = abs(entry - stop)
            if risk <= point:
                break
            target = (
                entry + params.distribution_rr * risk
                if side == "buy"
                else entry - params.distribution_rr * risk
            )
            result.append(
                Candidate(
                    phase=f"{phase_prefix}_distribution",
                    side=side,
                    signal_time=entry_time,
                    entry_time=entry_time,
                    entry=entry,
                    stop=stop,
                    target=target,
                    liquidity_level=edge,
                )
            )
            break
    return result


def article_candidates_for_day(
    day_frame: pd.DataFrame,
    point: float,
    config: Config,
    params: ArticleParams,
    day: date,
) -> tuple[list[Candidate], float, float]:
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
    session_specs: list[tuple[str, datetime, datetime]] = []
    if params.trade_london:
        session_start = combine(day, config.london_start)
        session_specs.append(
            (
                "london",
                session_start,
                session_start
                + timedelta(minutes=params.london_window_minutes),
            )
        )
    if params.trade_new_york:
        session_start = combine(day, config.ny_start)
        session_specs.append(
            (
                "new_york",
                session_start,
                session_start + timedelta(minutes=params.ny_window_minutes),
            )
        )
    daily_candidates: list[Candidate] = []
    for name, session_start, session_end in session_specs:
        candidates: list[Candidate] = []
        if params.enable_fade:
            candidates.extend(
                _fade_candidates(
                    bars,
                    day_frame,
                    point,
                    name,
                    session_start,
                    session_end,
                    asia_high,
                    asia_low,
                    params,
                )
            )
        if params.enable_distribution:
            candidates.extend(
                _distribution_candidates(
                    bars,
                    day_frame,
                    point,
                    name,
                    session_start,
                    session_end,
                    asia_high,
                    asia_low,
                    params,
                )
            )
        if candidates:
            daily_candidates.append(
                min(candidates, key=lambda candidate: candidate.signal_time)
            )
    daily_candidates.sort(key=lambda candidate: candidate.signal_time)
    return (
        daily_candidates[: params.max_trades_per_day],
        asia_high,
        asia_low,
    )


def backtest_article_model(
    frame: pd.DataFrame,
    symbol: str,
    point: float,
    config: Config,
    params: ArticleParams,
    start: datetime,
    end: datetime,
) -> list[Trade]:
    """Backtest sweep-fade and breakout-pullback AMD patterns.

    Signals use completed M5 candles and enter no earlier than the next M1
    candle. At most one candidate per named session is taken, with an optional
    daily cap.
    """
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
        daily_candidates, asia_high, asia_low = article_candidates_for_day(
            day_frame, point, config, params, day
        )
        if not math.isfinite(asia_high) or not math.isfinite(asia_low):
            continue
        for candidate in daily_candidates:
            entry_idx = _next_m1_index(day_frame, candidate.entry_time)
            if entry_idx is None:
                continue
            force_exit = combine(day, config.force_exit)
            trades.append(
                _simulate_open_trade(
                    day_frame,
                    symbol,
                    day,
                    candidate.phase,
                    candidate.side,
                    candidate.signal_time,
                    entry_idx,
                    candidate.entry,
                    candidate.stop,
                    candidate.target,
                    force_exit,
                    point,
                    config,
                    asia_high,
                    asia_low,
                    candidate.liquidity_level,
                )
            )
    return trades
