from __future__ import annotations

import logging
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Literal

import numpy as np
import pandas as pd

from .config import AppConfig
from .mt5_client import MT5Client
from .symbols import find_symbol_config, settings_mt5_symbol_from_config
from .timeframes import timeframe_seconds, validate_timeframe


StopLossMode = Literal["off", "atr", "percent"]
TakeProfitMode = Literal["off", "atr", "percent", "risk_reward"]


@dataclass(frozen=True)
class EniTrendBacktestSettings:
    symbols: tuple[str, ...] = ("BTCUSD",)
    execution_timeframe: str = "M15"
    higher_timeframe: str = "H4"
    volatility_lookback: int = 25
    trend_smoothing: int = 15
    volatility_multiplier: float = 3.8
    use_higher_timeframe_filter: bool = True
    volume: float = 0.01
    stop_loss_mode: StopLossMode = "atr"
    take_profit_mode: TakeProfitMode = "risk_reward"
    stop_loss_atr_length: int = 14
    stop_loss_atr_multiplier: float = 1.5
    take_profit_atr_multiplier: float = 3.0
    stop_loss_percent: float = 1.0
    take_profit_percent: float = 2.0
    risk_reward_ratio: float = 2.0
    use_break_even: bool = False
    break_even_trigger_r: float = 1.0
    break_even_offset: float = 0.0
    use_trailing_stop: bool = False
    trailing_stop_atr_multiplier: float = 2.0


@dataclass
class _SymbolSpec:
    requested: str
    display_symbol: str
    mt5_symbol: str
    name: str


@dataclass
class _PendingSignal:
    side: str
    signal_time: pd.Timestamp


@dataclass
class _OpenTrade:
    side: str
    signal_time: pd.Timestamp
    entry_time: pd.Timestamp
    entry: float
    volume: float
    initial_sl: float | None
    sl: float | None
    tp: float | None
    risk_distance: float
    entry_index: int


@dataclass
class _SymbolAccumulator:
    spec: _SymbolSpec
    timeframe: str
    bars: int = 0
    raw_signals: int = 0
    aligned_signals: int = 0
    skipped_signals: int = 0
    wins: int = 0
    losses: int = 0
    pnl: float = 0.0
    peak_pnl: float = 0.0
    max_drawdown: float = 0.0
    trade_logs: list[dict] = field(default_factory=list)
    error: str | None = None

    def record_trade(self, trade: dict) -> None:
        trade_pnl = float(trade["pnl"])
        self.pnl += trade_pnl
        self.peak_pnl = max(self.peak_pnl, self.pnl)
        self.max_drawdown = max(self.max_drawdown, self.peak_pnl - self.pnl)
        if trade_pnl > 0:
            self.wins += 1
        elif trade_pnl < 0:
            self.losses += 1
        self.trade_logs.append(trade)

    def payload(self) -> dict:
        trades = self.wins + self.losses
        return {
            "symbol": self.spec.display_symbol,
            "mt5_symbol": self.spec.mt5_symbol,
            "name": self.spec.name,
            "timeframe": self.timeframe,
            "bars": self.bars,
            "raw_signals": self.raw_signals,
            "aligned_signals": self.aligned_signals,
            "skipped_signals": self.skipped_signals,
            "trades": trades,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round((self.wins / trades * 100.0) if trades else 0.0, 2),
            "pnl": round(self.pnl, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "trade_logs": self.trade_logs,
            "error": self.error,
        }


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _iso(value: pd.Timestamp | datetime | str) -> str:
    if isinstance(value, pd.Timestamp):
        return value.tz_convert("UTC").replace(microsecond=0).isoformat()
    if isinstance(value, datetime):
        return _utc(value).replace(microsecond=0).isoformat()
    return str(value)


MOMENTUM_BOT_COMMENT = "Momentum bot"


@dataclass(frozen=True)
class EniTrendLiveSignal:
    side: str
    setup_id: str
    signal_time: str
    entry: float
    sl: float | None
    tp: float | None
    volume: float
    atr: float
    risk_distance: float
    display_symbol: str
    mt5_symbol: str
    trend: int


def active_symbol_tokens(config: AppConfig) -> tuple[str, ...]:
    tokens = tuple(item.symbol for item in config.enabled_symbols)
    if not tokens:
        raise ValueError("No enabled symbols in Settings.")
    return tokens


def active_symbol_specs(config: AppConfig) -> list[_SymbolSpec]:
    return _symbols_from_settings(config, active_symbol_tokens(config))


def resolve_backtest_symbols(config: AppConfig, symbols: tuple[str, ...] | list[str]) -> tuple[str, ...]:
    cleaned = tuple(token.strip() for token in symbols if str(token).strip())
    if cleaned:
        return cleaned
    return active_symbol_tokens(config)


def _bars_needed(settings: EniTrendBacktestSettings) -> int:
    return max(settings.volatility_lookback, settings.trend_smoothing, settings.stop_loss_atr_length) + 120


def _fetch_signal_frame(client: MT5Client, spec: _SymbolSpec, settings: EniTrendBacktestSettings) -> pd.DataFrame:
    bars = _bars_needed(settings)
    execution_df = client.rates(spec.mt5_symbol, settings.execution_timeframe, bars)
    higher_df = None
    if settings.use_higher_timeframe_filter:
        higher_df = client.rates(spec.mt5_symbol, settings.higher_timeframe, bars)
    return _signal_frame(execution_df, higher_df, settings)


def detect_live_entry(
    client: MT5Client,
    spec: _SymbolSpec,
    settings: EniTrendBacktestSettings,
) -> EniTrendLiveSignal | None:
    frame = _fetch_signal_frame(client, spec, settings)
    if len(frame) < 2:
        return None
    closed = frame.iloc[-2]
    if bool(closed.buy_signal):
        side = "buy"
    elif bool(closed.sell_signal):
        side = "sell"
    else:
        return None

    tick = client.tick(spec.mt5_symbol)
    if tick is None:
        return None
    if isinstance(tick, dict):
        bid = float(tick.get("bid", 0.0) or 0.0)
        ask = float(tick.get("ask", 0.0) or 0.0)
    else:
        bid = float(getattr(tick, "bid", 0.0) or 0.0)
        ask = float(getattr(tick, "ask", 0.0) or 0.0)
    entry = ask if side == "buy" else bid
    atr_value = float(closed.risk_atr) if not pd.isna(closed.risk_atr) else 0.0
    sl, tp, risk_distance = _initial_sl_tp(side, entry, atr_value, settings)
    setup_id = f"enitrend:{spec.display_symbol}:{side}:{_iso(closed.time)}"
    return EniTrendLiveSignal(
        side=side,
        setup_id=setup_id,
        signal_time=_iso(closed.time),
        entry=entry,
        sl=sl,
        tp=tp,
        volume=settings.volume,
        atr=atr_value,
        risk_distance=risk_distance,
        display_symbol=spec.display_symbol,
        mt5_symbol=spec.mt5_symbol,
        trend=int(closed.trend),
    )


def latest_closed_trend(client: MT5Client, spec: _SymbolSpec, settings: EniTrendBacktestSettings) -> tuple[int, float, pd.Series] | None:
    frame = _fetch_signal_frame(client, spec, settings)
    if len(frame) < 2:
        return None
    closed = frame.iloc[-2]
    atr_value = float(closed.risk_atr) if not pd.isna(closed.risk_atr) else 0.0
    return int(closed.trend), atr_value, closed


def _symbols_from_settings(config: AppConfig, symbols: tuple[str, ...]) -> list[_SymbolSpec]:
    specs: list[_SymbolSpec] = []
    for token in symbols:
        requested = token.strip()
        if not requested:
            continue
        symbol_cfg = find_symbol_config(config.symbols, requested)
        if symbol_cfg is None:
            specs.append(
                _SymbolSpec(
                    requested=requested,
                    display_symbol=requested.upper(),
                    mt5_symbol=requested,
                    name=requested.upper(),
                )
            )
            continue
        specs.append(
            _SymbolSpec(
                requested=requested,
                display_symbol=symbol_cfg.symbol,
                mt5_symbol=settings_mt5_symbol_from_config(symbol_cfg, config),
                name=symbol_cfg.name,
            )
        )
    if not specs:
        raise ValueError("At least one symbol is required.")
    return specs


def _true_range(df: pd.DataFrame) -> pd.Series:
    previous_close = df["close"].shift(1)
    ranges = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - previous_close).abs(),
            (df["low"] - previous_close).abs(),
        ],
        axis=1,
    )
    return ranges.max(axis=1)


def _wilder_atr(df: pd.DataFrame, length: int) -> pd.Series:
    return _true_range(df).ewm(alpha=1.0 / float(length), adjust=False, min_periods=length).mean()


def _trend_frame(df: pd.DataFrame, settings: EniTrendBacktestSettings) -> pd.DataFrame:
    result = df.copy().reset_index(drop=True)
    close = result["close"].astype(float)
    basis = close.ewm(span=settings.trend_smoothing, adjust=False, min_periods=1).mean()
    candle_return = np.log(close / close.shift(1)).abs().replace([np.inf, -np.inf], np.nan)
    return_vol = candle_return.rolling(settings.volatility_lookback, min_periods=settings.volatility_lookback).mean() * close
    atr_vol = _wilder_atr(result, settings.volatility_lookback)
    zone_size = ((atr_vol + return_vol) / 2.0) * settings.volatility_multiplier
    upper_zone = basis + zone_size
    lower_zone = basis - zone_size

    trend_values: list[int] = []
    previous_trend = 0
    for index, price in enumerate(close):
        upper = upper_zone.iloc[index]
        lower = lower_zone.iloc[index]
        if not math.isnan(upper) and price > upper:
            previous_trend = 1
        elif not math.isnan(lower) and price < lower:
            previous_trend = -1
        trend_values.append(previous_trend)

    trend = pd.Series(trend_values, index=result.index, dtype="int64")
    previous = trend.shift(1).fillna(0).astype("int64")
    result["trend"] = trend
    result["buy_raw"] = (trend == 1) & (previous != 1)
    result["sell_raw"] = (trend == -1) & (previous != -1)
    result["basis"] = basis
    result["upper_zone"] = upper_zone
    result["lower_zone"] = lower_zone
    result["risk_atr"] = _wilder_atr(result, settings.stop_loss_atr_length)
    return result


def _attach_higher_timeframe(
    execution: pd.DataFrame,
    higher: pd.DataFrame,
    *,
    execution_timeframe: str,
    higher_timeframe: str,
) -> pd.DataFrame:
    exec_seconds = timeframe_seconds(execution_timeframe)
    higher_seconds = timeframe_seconds(higher_timeframe)
    left = execution.copy()
    left["_row"] = np.arange(len(left))
    left["_confirm_time"] = left["time"] + pd.to_timedelta(exec_seconds, unit="s")
    right = higher[["time", "trend"]].copy()
    right["_htf_confirm_time"] = right["time"] + pd.to_timedelta(higher_seconds, unit="s")
    right = right.rename(columns={"trend": "htf_trend"})
    merged = pd.merge_asof(
        left.sort_values("_confirm_time"),
        right[["_htf_confirm_time", "htf_trend"]].sort_values("_htf_confirm_time"),
        left_on="_confirm_time",
        right_on="_htf_confirm_time",
        direction="backward",
    )
    merged = merged.sort_values("_row").drop(columns=["_row", "_confirm_time", "_htf_confirm_time"])
    merged["htf_trend"] = merged["htf_trend"].fillna(0).astype("int64")
    return merged.reset_index(drop=True)


def _signal_frame(
    execution_df: pd.DataFrame,
    higher_df: pd.DataFrame | None,
    settings: EniTrendBacktestSettings,
) -> pd.DataFrame:
    execution = _trend_frame(execution_df, settings)
    if settings.use_higher_timeframe_filter:
        if higher_df is None:
            raise ValueError("Higher timeframe data is required when the HTF filter is enabled.")
        higher = _trend_frame(higher_df, settings)
        execution = _attach_higher_timeframe(
            execution,
            higher,
            execution_timeframe=settings.execution_timeframe,
            higher_timeframe=settings.higher_timeframe,
        )
    else:
        execution["htf_trend"] = 0

    if settings.use_higher_timeframe_filter:
        long_allowed = execution["htf_trend"] == 1
        short_allowed = execution["htf_trend"] == -1
    else:
        long_allowed = pd.Series(True, index=execution.index)
        short_allowed = pd.Series(True, index=execution.index)
    execution["buy_signal"] = execution["buy_raw"] & long_allowed
    execution["sell_signal"] = execution["sell_raw"] & short_allowed
    return execution


def _risk_distance(entry: float, atr_value: float, settings: EniTrendBacktestSettings) -> float:
    if settings.stop_loss_mode == "percent":
        return entry * (settings.stop_loss_percent / 100.0)
    if settings.stop_loss_mode == "atr":
        return atr_value * settings.stop_loss_atr_multiplier
    if settings.take_profit_mode == "risk_reward":
        return atr_value * settings.stop_loss_atr_multiplier
    return 0.0


def _initial_sl_tp(
    side: str,
    entry: float,
    atr_value: float,
    settings: EniTrendBacktestSettings,
) -> tuple[float | None, float | None, float]:
    risk_distance = _risk_distance(entry, atr_value, settings)
    if settings.stop_loss_mode == "off":
        stop_loss = None
    elif side == "buy":
        stop_loss = entry - risk_distance
    else:
        stop_loss = entry + risk_distance

    if settings.take_profit_mode == "off":
        take_profit = None
    elif settings.take_profit_mode == "percent":
        pct_distance = entry * (settings.take_profit_percent / 100.0)
        take_profit = entry + pct_distance if side == "buy" else entry - pct_distance
    elif settings.take_profit_mode == "atr":
        atr_distance = atr_value * settings.take_profit_atr_multiplier
        take_profit = entry + atr_distance if side == "buy" else entry - atr_distance
    else:
        rr_distance = risk_distance * settings.risk_reward_ratio
        take_profit = entry + rr_distance if side == "buy" else entry - rr_distance
    return stop_loss, take_profit, risk_distance


def _open_trade(
    side: str,
    pending: _PendingSignal,
    row,
    row_index: int,
    settings: EniTrendBacktestSettings,
) -> _OpenTrade:
    entry = float(row.open)
    atr_value = float(row.risk_atr) if not pd.isna(row.risk_atr) else 0.0
    initial_sl, tp, risk_distance = _initial_sl_tp(side, entry, atr_value, settings)
    return _OpenTrade(
        side=side,
        signal_time=pending.signal_time,
        entry_time=row.time,
        entry=entry,
        volume=settings.volume,
        initial_sl=initial_sl,
        sl=initial_sl,
        tp=tp,
        risk_distance=risk_distance,
        entry_index=row_index,
    )


def _money_for_move(
    client: MT5Client,
    symbol: str,
    volume: float,
    side: str,
    entry: float,
    exit_price: float,
) -> float:
    price_distance = abs(exit_price - entry)
    try:
        money = float(client.money_for_distance(symbol, volume, price_distance))
    except Exception:  # noqa: BLE001
        money = price_distance * volume
    profitable = exit_price > entry if side == "buy" else exit_price < entry
    return money if profitable else -money


def _close_trade(
    client: MT5Client,
    spec: _SymbolSpec,
    position: _OpenTrade,
    exit_price: float,
    exit_time: pd.Timestamp,
    exit_kind: str,
    row_index: int,
) -> dict:
    pnl = _money_for_move(client, spec.mt5_symbol, position.volume, position.side, position.entry, exit_price)
    return {
        "symbol": spec.display_symbol,
        "mt5_symbol": spec.mt5_symbol,
        "side": position.side,
        "signal_time": _iso(position.signal_time),
        "entry_time": _iso(position.entry_time),
        "exit_time": _iso(exit_time),
        "entry": round(position.entry, 5),
        "exit": round(exit_price, 5),
        "initial_sl": round(position.initial_sl, 5) if position.initial_sl is not None else None,
        "final_sl": round(position.sl, 5) if position.sl is not None else None,
        "tp": round(position.tp, 5) if position.tp is not None else None,
        "volume": position.volume,
        "risk_distance": round(position.risk_distance, 5),
        "exit_kind": exit_kind,
        "bars_held": max(0, row_index - position.entry_index + 1),
        "pnl": round(pnl, 2),
    }


def _update_protective_stops(position: _OpenTrade, row, settings: EniTrendBacktestSettings) -> None:
    atr_value = float(row.risk_atr) if not pd.isna(row.risk_atr) else 0.0
    if settings.use_break_even and position.risk_distance > 0:
        trigger_distance = position.risk_distance * settings.break_even_trigger_r
        if position.side == "buy" and float(row.high) - position.entry >= trigger_distance:
            candidate = position.entry + settings.break_even_offset
            position.sl = max(position.sl, candidate) if position.sl is not None else candidate
        if position.side == "sell" and position.entry - float(row.low) >= trigger_distance:
            candidate = position.entry - settings.break_even_offset
            position.sl = min(position.sl, candidate) if position.sl is not None else candidate

    if settings.use_trailing_stop and atr_value > 0:
        if position.side == "buy":
            candidate = float(row.close) - atr_value * settings.trailing_stop_atr_multiplier
            position.sl = max(position.sl, candidate) if position.sl is not None else candidate
        else:
            candidate = float(row.close) + atr_value * settings.trailing_stop_atr_multiplier
            position.sl = min(position.sl, candidate) if position.sl is not None else candidate


def _exit_from_bar(position: _OpenTrade, row) -> tuple[float, str] | None:
    high = float(row.high)
    low = float(row.low)
    close = float(row.close)
    if position.side == "buy":
        if position.sl is not None and low <= position.sl:
            return position.sl, "stop_loss"
        if position.tp is not None and high >= position.tp:
            return position.tp, "take_profit"
        if int(row.trend) == -1:
            return close, "trend_flip"
    else:
        if position.sl is not None and high >= position.sl:
            return position.sl, "stop_loss"
        if position.tp is not None and low <= position.tp:
            return position.tp, "take_profit"
        if int(row.trend) == 1:
            return close, "trend_flip"
    return None


def _simulate_symbol(
    client: MT5Client,
    spec: _SymbolSpec,
    df: pd.DataFrame,
    settings: EniTrendBacktestSettings,
) -> _SymbolAccumulator:
    accumulator = _SymbolAccumulator(spec=spec, timeframe=settings.execution_timeframe, bars=len(df))
    accumulator.raw_signals = int(df["buy_raw"].sum() + df["sell_raw"].sum())
    accumulator.aligned_signals = int(df["buy_signal"].sum() + df["sell_signal"].sum())
    accumulator.skipped_signals = max(0, accumulator.raw_signals - accumulator.aligned_signals)

    pending: _PendingSignal | None = None
    position: _OpenTrade | None = None
    for row_index, row in enumerate(df.itertuples(index=False)):
        if pending is not None and position is None:
            position = _open_trade(pending.side, pending, row, row_index, settings)
            pending = None

        if position is not None:
            exit_data = _exit_from_bar(position, row)
            if exit_data is not None:
                exit_price, exit_kind = exit_data
                trade = _close_trade(client, spec, position, exit_price, row.time, exit_kind, row_index)
                accumulator.record_trade(trade)
                position = None
            else:
                _update_protective_stops(position, row, settings)

        if position is None:
            if bool(row.buy_signal):
                pending = _PendingSignal(side="buy", signal_time=row.time)
            elif bool(row.sell_signal):
                pending = _PendingSignal(side="sell", signal_time=row.time)

    if position is not None and len(df) > 0:
        last = df.iloc[-1]
        trade = _close_trade(
            client,
            spec,
            position,
            float(last["close"]),
            last["time"],
            "period_end",
            len(df) - 1,
        )
        accumulator.record_trade(trade)
    return accumulator


def _trade_sort_time(trade: dict) -> int:
    return int(pd.Timestamp(trade["exit_time"]).timestamp())


def _build_daily_performance(trades: list[dict], starting_balance: float) -> list[dict]:
    if not trades:
        return []
    rows: list[dict] = []
    balance = float(starting_balance)
    grouped: dict[str, dict] = {}
    for trade in sorted(trades, key=_trade_sort_time):
        day = pd.Timestamp(trade["exit_time"]).strftime("%Y-%m-%d")
        bucket = grouped.setdefault(
            day,
            {
                "date": day,
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl": 0.0,
                "start_balance": round(balance, 2),
                "trade_rows": [],
            },
        )
        pnl = float(trade["pnl"])
        balance += pnl
        bucket["trades"] += 1
        bucket["wins"] += 1 if pnl > 0 else 0
        bucket["losses"] += 1 if pnl < 0 else 0
        bucket["pnl"] += pnl
        bucket["trade_rows"].append({**trade, "balance_after": round(balance, 2)})
        bucket["balance"] = round(balance, 2)

    for day in sorted(grouped):
        row = grouped[day]
        row["pnl"] = round(row["pnl"], 2)
        rows.append(row)
    return rows


def _warmup_start(start: datetime, timeframe: str, settings: EniTrendBacktestSettings) -> datetime:
    warmup_bars = max(settings.volatility_lookback, settings.trend_smoothing, settings.stop_loss_atr_length) + 80
    return _utc(start) - timedelta(seconds=timeframe_seconds(timeframe) * warmup_bars)


def _filtered_window(df: pd.DataFrame, start: datetime, end: datetime) -> pd.DataFrame:
    start_ts = pd.Timestamp(_utc(start))
    end_ts = pd.Timestamp(_utc(end))
    return df[(df["time"] >= start_ts) & (df["time"] <= end_ts)].reset_index(drop=True)


def run_enitrend_backtest(
    client: MT5Client,
    config: AppConfig,
    settings: EniTrendBacktestSettings,
    start: datetime,
    end: datetime,
    starting_balance: float = 1000.0,
    logger: logging.Logger | None = None,
) -> dict:
    execution_timeframe = validate_timeframe(settings.execution_timeframe)
    higher_timeframe = validate_timeframe(settings.higher_timeframe)
    settings = EniTrendBacktestSettings(
        **{
            **asdict(settings),
            "execution_timeframe": execution_timeframe,
            "higher_timeframe": higher_timeframe,
        }
    )
    start_utc = _utc(start)
    end_utc = _utc(end)
    if start_utc >= end_utc:
        raise ValueError("Start must be before end.")
    if starting_balance <= 0:
        raise ValueError("Starting balance must be greater than 0.")
    if settings.volume <= 0:
        raise ValueError("Volume must be greater than 0.")

    client.initialize()
    symbol_specs = _symbols_from_settings(config, resolve_backtest_symbols(config, settings.symbols))
    symbol_rows: list[dict] = []
    all_trades: list[dict] = []

    for index, spec in enumerate(symbol_specs, start=1):
        if logger:
            logger.info(
                "ENITREND BACKTEST %s/%s %s mt5=%s tf=%s htf=%s",
                index,
                len(symbol_specs),
                spec.display_symbol,
                spec.mt5_symbol,
                settings.execution_timeframe,
                settings.higher_timeframe,
            )
        try:
            execution_df = client.rates_range(
                spec.mt5_symbol,
                settings.execution_timeframe,
                _warmup_start(start_utc, settings.execution_timeframe, settings),
                end_utc,
            )
            higher_df = None
            if settings.use_higher_timeframe_filter:
                higher_df = client.rates_range(
                    spec.mt5_symbol,
                    settings.higher_timeframe,
                    _warmup_start(start_utc, settings.higher_timeframe, settings),
                    end_utc,
                )
            signals = _signal_frame(execution_df, higher_df, settings)
            signals = _filtered_window(signals, start_utc, end_utc)
            accumulator = _simulate_symbol(client, spec, signals, settings)
            payload = accumulator.payload()
            symbol_rows.append(payload)
            all_trades.extend(payload["trade_logs"])
        except Exception as exc:  # noqa: BLE001
            if logger:
                logger.exception("ENITREND BACKTEST failed for %s: %s", spec.display_symbol, exc)
            failed = _SymbolAccumulator(spec=spec, timeframe=settings.execution_timeframe, error=str(exc))
            symbol_rows.append(failed.payload())

    total_pnl = round(sum(float(row.get("pnl") or 0.0) for row in symbol_rows), 2)
    daily_performance = _build_daily_performance(all_trades, starting_balance)
    return {
        "subsystem": "dynamic_volatility_momentum",
        "strategy": "EniTrend-style momentum alignment",
        "note": "Recreated technical strategy logic inspired by visible dynamic-zone momentum behavior; not a proprietary clone.",
        "start": start_utc.isoformat(),
        "end": end_utc.isoformat(),
        "starting_balance": round(starting_balance, 2),
        "total_pnl": total_pnl,
        "end_balance_if_sequential": round(starting_balance + total_pnl, 2),
        "settings": asdict(settings),
        "symbols": symbol_rows,
        "daily_performance": daily_performance,
    }
