from __future__ import annotations

from dataclasses import asdict, dataclass
from math import inf

import numpy as np
import pandas as pd

from .config import StrategyConfig
from .mt5_data import SymbolSpec


@dataclass(frozen=True)
class Setup:
    signal_time: pd.Timestamp
    first_test_time: pd.Timestamp
    resistance: float
    range_low: float
    entry: float
    stop: float
    target: float
    atr: float


@dataclass
class Trade:
    signal_time: pd.Timestamp
    opened: pd.Timestamp
    closed: pd.Timestamp
    entry: float
    stop: float
    target: float
    exit_price: float
    r_multiple: float
    cash_pnl: float
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class Result:
    start: pd.Timestamp
    end: pd.Timestamp
    starting_balance: float
    ending_balance: float
    trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    net_r: float
    return_pct: float
    max_drawdown_pct: float
    max_consecutive_losses: int
    records: list[Trade]
    equity: pd.DataFrame

    def summary(self) -> dict[str, object]:
        value = asdict(self)
        value.pop("records")
        value.pop("equity")
        value["start"] = str(self.start)
        value["end"] = str(self.end)
        return value


def atr(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    previous = frame["close"].shift(1)
    true_range = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - previous).abs(), (frame["low"] - previous).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy().sort_index()
    result["atr"] = atr(result)
    return result


def setup_at(frame: pd.DataFrame, index: int, config: StrategyConfig) -> Setup | None:
    # The second test is confirmed by the candle immediately to its right, so
    # the signal can only exist after that candle has closed.
    if index < config.impulse_bars + config.max_test_gap + 3:
        return None
    second_index = index - 1
    second = frame.iloc[second_index]
    confirmation = frame.iloc[index]
    if not config.session_start_utc <= frame.index[index].hour < config.session_end_utc:
        return None
    atr_value = float(confirmation.atr)
    if not np.isfinite(atr_value) or atr_value <= 0:
        return None
    if not (float(second.high) >= float(frame.iloc[second_index - 1].high) and float(second.high) >= float(confirmation.high)):
        return None
    if float(second.high - second.close) < config.rejection_atr * atr_value:
        return None
    earliest = second_index - config.max_test_gap
    latest = second_index - config.min_test_gap
    for first_index in range(latest, earliest - 1, -1):
        first = frame.iloc[first_index]
        if not (float(first.high) >= float(frame.iloc[first_index - 1].high) and float(first.high) >= float(frame.iloc[first_index + 1].high)):
            continue
        if float(first.high - first.close) < config.rejection_atr * atr_value:
            continue
        if abs(float(second.high - first.high)) > config.test_tolerance_atr * atr_value:
            continue
        resistance = max(float(first.high), float(second.high))
        between = frame.iloc[first_index:index + 1]
        middle = frame.iloc[first_index + 1:second_index]
        if middle.empty or resistance - float(middle.low.min()) < config.min_dip_atr * atr_value:
            continue
        if float(between.iloc[1:-1]["close"].max()) > resistance + config.test_tolerance_atr * atr_value:
            continue
        impulse_start = first_index - config.impulse_bars
        impulse = frame.iloc[impulse_start:first_index]
        peak_position = int(np.argmax(impulse["high"].to_numpy()))
        low_position = int(np.argmin(impulse["low"].to_numpy()))
        impulse_drop = float(impulse.iloc[peak_position].high - impulse.iloc[low_position].low)
        if peak_position >= low_position or impulse_drop < config.impulse_atr * atr_value:
            continue
        impulse_low = float(impulse.low.min())
        if float(first.high) - impulse_low < config.min_recovery_atr * atr_value:
            continue
        range_low = float(between.low.min())
        entry = resistance + config.entry_buffer_atr * atr_value
        stop = range_low - config.stop_buffer_atr * atr_value
        risk = entry - stop
        if not config.min_range_atr * atr_value <= risk <= config.max_range_atr * atr_value:
            continue
        return Setup(
            signal_time=frame.index[index], first_test_time=frame.index[first_index], resistance=resistance,
            range_low=range_low, entry=entry, stop=stop, target=entry + config.target_rr * risk, atr=atr_value,
        )
    return None


def all_setups(frame: pd.DataFrame, config: StrategyConfig) -> dict[pd.Timestamp, Setup]:
    # Optimization calls this hundreds of times. Working on NumPy arrays avoids
    # constructing thousands of tiny pandas slices for every candidate.
    highs = frame["high"].to_numpy(dtype=float)
    lows = frame["low"].to_numpy(dtype=float)
    closes = frame["close"].to_numpy(dtype=float)
    atrs = frame["atr"].to_numpy(dtype=float)
    output: dict[pd.Timestamp, Setup] = {}
    warmup = config.impulse_bars + config.max_test_gap + 3
    for index in range(warmup, len(frame)):
        if not config.session_start_utc <= frame.index[index].hour < config.session_end_utc:
            continue
        second_index = index - 1
        atr_value = atrs[index]
        if not np.isfinite(atr_value) or atr_value <= 0:
            continue
        if not (highs[second_index] >= highs[second_index - 1] and highs[second_index] >= highs[index]):
            continue
        if highs[second_index] - closes[second_index] < config.rejection_atr * atr_value:
            continue
        earliest = second_index - config.max_test_gap
        latest = second_index - config.min_test_gap
        for first_index in range(latest, earliest - 1, -1):
            if not (highs[first_index] >= highs[first_index - 1] and highs[first_index] >= highs[first_index + 1]):
                continue
            if highs[first_index] - closes[first_index] < config.rejection_atr * atr_value:
                continue
            if abs(highs[second_index] - highs[first_index]) > config.test_tolerance_atr * atr_value:
                continue
            resistance = max(highs[first_index], highs[second_index])
            if first_index + 1 >= second_index or resistance - lows[first_index + 1:second_index].min() < config.min_dip_atr * atr_value:
                continue
            if closes[first_index + 1:index].max(initial=-np.inf) > resistance + config.test_tolerance_atr * atr_value:
                continue
            impulse_start = first_index - config.impulse_bars
            impulse_highs = highs[impulse_start:first_index]
            impulse_lows = lows[impulse_start:first_index]
            peak_position = int(np.argmax(impulse_highs))
            low_position = int(np.argmin(impulse_lows))
            if peak_position >= low_position or impulse_highs[peak_position] - impulse_lows[low_position] < config.impulse_atr * atr_value:
                continue
            if highs[first_index] - impulse_lows.min() < config.min_recovery_atr * atr_value:
                continue
            range_low = float(lows[first_index:index + 1].min())
            entry = resistance + config.entry_buffer_atr * atr_value
            stop = range_low - config.stop_buffer_atr * atr_value
            risk = entry - stop
            if not config.min_range_atr * atr_value <= risk <= config.max_range_atr * atr_value:
                continue
            output[frame.index[index]] = Setup(
                signal_time=frame.index[index], first_test_time=frame.index[first_index],
                resistance=float(resistance), range_low=range_low, entry=float(entry), stop=float(stop),
                target=float(entry + config.target_rr * risk), atr=float(atr_value),
            )
            break
    return output


def run_backtest(
    raw: pd.DataFrame,
    config: StrategyConfig,
    spec: SymbolSpec,
    starting_balance: float = 10_000.0,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
) -> Result:
    frame = raw if "atr" in raw.columns else prepare(raw)
    start = pd.Timestamp(start or frame.index.min())
    end = pd.Timestamp(end or frame.index.max())
    if start.tzinfo is None:
        start = start.tz_localize("UTC")
    if end.tzinfo is None:
        end = end.tz_localize("UTC")
    setups = all_setups(frame, config)
    balance = starting_balance
    peak = balance
    max_dd = 0.0
    records: list[Trade] = []
    equity_rows: list[tuple[pd.Timestamp, float]] = []
    pending: Setup | None = None
    pending_age = 0
    active: tuple[Setup, pd.Timestamp, int, float] | None = None
    cooldown = 0
    consecutive = max_consecutive = 0

    test = frame.loc[start:end]
    timestamps = test.index
    highs = test["high"].to_numpy(dtype=float)
    lows = test["low"].to_numpy(dtype=float)
    closes = test["close"].to_numpy(dtype=float)
    spreads = test["spread"].to_numpy(dtype=float) if "spread" in test.columns else np.zeros(len(test))
    for position in range(len(test)):
        timestamp = timestamps[position]
        high = highs[position]
        low = lows[position]
        close = closes[position]
        spread = min(max(spreads[position] * spec.point, 0.0), config.max_spread_price * 4)
        if cooldown > 0:
            cooldown -= 1
        if active is not None:
            plan, opened, held, risk_cash = active
            held += 1
            stop_hit = low <= plan.stop
            target_hit = high >= plan.target
            if stop_hit or target_hit or held >= config.max_hold_bars:
                if stop_hit:
                    exit_price, reason = plan.stop, "STOP"
                elif target_hit:
                    exit_price, reason = plan.target, "TARGET"
                else:
                    exit_price, reason = close, "TIME"
                r_multiple = (exit_price - plan.entry) / (plan.entry - plan.stop)
                cash_pnl = risk_cash * r_multiple
                balance += cash_pnl
                records.append(Trade(plan.signal_time, opened, timestamp, plan.entry, plan.stop, plan.target, exit_price, r_multiple, cash_pnl, reason))
                if cash_pnl < 0:
                    consecutive += 1
                    max_consecutive = max(max_consecutive, consecutive)
                else:
                    consecutive = 0
                active = None
                cooldown = config.cooldown_bars
            else:
                active = (plan, opened, held, risk_cash)
        elif pending is not None:
            pending_age += 1
            triggered = high + spread >= pending.entry
            invalid = low <= pending.stop
            if pending_age <= config.activation_delay_bars:
                # A breakout during the observation delay is already gone; do
                # not arm a late stop order behind it.
                if triggered or invalid:
                    pending = None
            elif triggered:
                risk_cash = balance * config.risk_pct / 100.0
                active = (pending, timestamp, 0, risk_cash)
                if invalid:
                    cash_pnl = -risk_cash
                    balance += cash_pnl
                    records.append(Trade(pending.signal_time, timestamp, timestamp, pending.entry, pending.stop, pending.target, pending.stop, -1.0, cash_pnl, "AMBIGUOUS_STOP"))
                    consecutive += 1
                    max_consecutive = max(max_consecutive, consecutive)
                    active = None
                    cooldown = config.cooldown_bars
                pending = None
            elif invalid or pending_age >= config.pending_expiry_bars:
                pending = None
        if active is None and pending is None and cooldown == 0 and timestamp in setups:
            pending = setups[timestamp]
            pending_age = 0
        mark_equity = balance
        if active is not None:
            plan, _, _, risk_cash = active
            mark_r = (close - plan.entry) / (plan.entry - plan.stop)
            mark_equity += risk_cash * mark_r
        peak = max(peak, mark_equity)
        max_dd = max(max_dd, (peak - mark_equity) / peak * 100 if peak else 0)
        equity_rows.append((timestamp, mark_equity))

    if active is not None:
        plan, opened, _, risk_cash = active
        last = frame.loc[:end].iloc[-1]
        exit_price = float(last.close)
        r_multiple = (exit_price - plan.entry) / (plan.entry - plan.stop)
        cash_pnl = risk_cash * r_multiple
        balance += cash_pnl
        records.append(Trade(plan.signal_time, opened, frame.loc[:end].index[-1], plan.entry, plan.stop, plan.target, exit_price, r_multiple, cash_pnl, "END"))
    wins = sum(item.cash_pnl > 0 for item in records)
    losses = sum(item.cash_pnl < 0 for item in records)
    gross_win = sum(max(item.cash_pnl, 0) for item in records)
    gross_loss = -sum(min(item.cash_pnl, 0) for item in records)
    pf = gross_win / gross_loss if gross_loss else (inf if gross_win else 0.0)
    return Result(
        start=start, end=end, starting_balance=float(starting_balance), ending_balance=float(balance),
        trades=int(len(records)), wins=int(wins), losses=int(losses),
        win_rate=float(100 * wins / len(records) if records else 0.0),
        profit_factor=float(pf), net_r=float(sum(item.r_multiple for item in records)),
        return_pct=float((balance / starting_balance - 1) * 100), max_drawdown_pct=float(max_dd),
        max_consecutive_losses=int(max_consecutive), records=records,
        equity=pd.DataFrame(equity_rows, columns=["time", "equity"]).set_index("time"),
    )
