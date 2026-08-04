from __future__ import annotations

from dataclasses import asdict, dataclass
from math import floor
from typing import Iterable

import numpy as np
import pandas as pd

from .config import StrategyConfig
from .mt5_data import SymbolSpec


@dataclass(frozen=True)
class GridPlan:
    created: pd.Timestamp
    side: int
    mode: str
    entries: tuple[float, ...]
    stop: float
    atr: float
    lot_each: float
    risk_cash: float


@dataclass
class TradeRecord:
    opened: pd.Timestamp
    closed: pd.Timestamp
    side: str
    mode: str
    levels_filled: int
    lot_total: float
    average_entry: float
    initial_stop: float
    exit_price: float
    pnl: float
    r_multiple: float
    reason: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class BacktestResult:
    start: pd.Timestamp
    end: pd.Timestamp
    starting_balance: float
    ending_balance: float
    net_profit: float
    return_pct: float
    trades: int
    wins: int
    losses: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    realized_drawdown_pct: float
    max_consecutive_losses: int
    exposure_pct_max: float
    records: list[TradeRecord]
    equity: pd.DataFrame

    def summary(self) -> dict[str, object]:
        values = asdict(self)
        values.pop("records")
        values.pop("equity")
        values["start"] = str(self.start)
        values["end"] = str(self.end)
        return values


def _rma(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def atr(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    previous = frame["close"].shift(1)
    true_range = pd.concat(
        [(frame["high"] - frame["low"]), (frame["high"] - previous).abs(), (frame["low"] - previous).abs()],
        axis=1,
    ).max(axis=1)
    return _rma(true_range, length)


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    change = series.diff()
    gain = _rma(change.clip(lower=0), length)
    loss = _rma((-change).clip(lower=0), length)
    relative = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + relative)).fillna(50)


def adx(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    up = frame["high"].diff()
    down = -frame["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=frame.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=frame.index)
    tr = atr(frame, 1)
    smoothed_tr = _rma(tr, length).replace(0, np.nan)
    plus_di = 100 * _rma(plus_dm, length) / smoothed_tr
    minus_di = 100 * _rma(minus_dm, length) / smoothed_tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _rma(dx, length)


def _resample(frame: pd.DataFrame, rule: str) -> pd.DataFrame:
    return frame.resample(rule, label="right", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        spread=("spread", "median"),
    ).dropna()


def prepare_features(m5: pd.DataFrame) -> pd.DataFrame:
    m15 = _resample(m5, "15min")
    h1 = _resample(m5, "1h")
    h4 = _resample(m5, "4h")
    m15["m15_atr"] = atr(m15)
    m15["m15_rsi"] = rsi(m15["close"])
    m15["m15_ema20"] = m15["close"].ewm(span=20, adjust=False).mean()
    mid = m15["close"].rolling(20).mean()
    deviation = m15["close"].rolling(20).std(ddof=0)
    m15["bb_upper"] = mid + 2 * deviation
    m15["bb_lower"] = mid - 2 * deviation
    m15["m15_break_high"] = m15["high"].rolling(12).max().shift(1)
    m15["m15_break_low"] = m15["low"].rolling(12).min().shift(1)
    h1["h1_ema50"] = h1["close"].ewm(span=50, adjust=False).mean()
    h1["h1_ema200"] = h1["close"].ewm(span=200, adjust=False).mean()
    h1["h1_adx"] = adx(h1)
    h1["h1_slope"] = h1["h1_ema50"].diff(3)
    h4["h4_ema20"] = h4["close"].ewm(span=20, adjust=False).mean()
    h4["h4_ema50"] = h4["close"].ewm(span=50, adjust=False).mean()
    h4["h4_slope"] = h4["h4_ema20"].diff(2)

    m15_columns = [
        "open", "high", "low", "close", "m15_atr", "m15_rsi", "m15_ema20", "bb_upper", "bb_lower",
        "m15_break_high", "m15_break_low"
    ]
    h1_columns = ["close", "h1_ema50", "h1_ema200", "h1_adx", "h1_slope"]
    h4_columns = ["close", "h4_ema20", "h4_ema50", "h4_slope"]
    feature = pd.merge_asof(
        m5.sort_index(),
        m15[m15_columns].rename(columns={c: f"m15_{c}" for c in ["open", "high", "low", "close"]}),
        left_index=True,
        right_index=True,
        direction="backward",
    )
    feature = pd.merge_asof(
        feature,
        h4[h4_columns].rename(columns={"close": "h4_close"}),
        left_index=True,
        right_index=True,
        direction="backward",
    )
    feature = pd.merge_asof(
        feature,
        h1[h1_columns].rename(columns={"close": "h1_close"}),
        left_index=True,
        right_index=True,
        direction="backward",
    )
    feature["signal_bar"] = feature.index.minute.isin([0, 15, 30, 45])
    return feature


def _value(row, name: str):
    return row.get(name) if isinstance(row, pd.Series) else getattr(row, name)


def signal_from_row(row, config: StrategyConfig) -> int:
    if not bool(_value(row, "signal_bar")):
        return 0
    required = ["m15_atr", "m15_rsi", "h1_adx", "h1_ema50", "h1_ema200", "h4_ema20", "h4_ema50"]
    if any(pd.isna(_value(row, name)) for name in required):
        return 0
    timestamp = row.name if isinstance(row, pd.Series) else row.Index
    hour = timestamp.hour
    if not config.session_start_utc <= hour < config.session_end_utc:
        return 0
    if config.mode in {"trend", "momentum", "breakout"}:
        long_trend = (
            _value(row, "h1_close") > _value(row, "h1_ema200")
            and _value(row, "h1_ema50") > _value(row, "h1_ema200")
            and _value(row, "h1_slope") > 0
            and _value(row, "h4_close") > _value(row, "h4_ema50")
            and _value(row, "h4_ema20") >= _value(row, "h4_ema50")
            and _value(row, "h4_slope") > 0
            and config.adx_min <= _value(row, "h1_adx") <= config.adx_max
        )
        short_trend = (
            _value(row, "h1_close") < _value(row, "h1_ema200")
            and _value(row, "h1_ema50") < _value(row, "h1_ema200")
            and _value(row, "h1_slope") < 0
            and _value(row, "h4_close") < _value(row, "h4_ema50")
            and _value(row, "h4_ema20") <= _value(row, "h4_ema50")
            and _value(row, "h4_slope") < 0
            and config.adx_min <= _value(row, "h1_adx") <= config.adx_max
        )
        if config.mode in {"momentum", "breakout"}:
            long_break = (
                _value(row, "m15_close") > _value(row, "m15_break_high")
                and _value(row, "m15_close") > _value(row, "m15_open")
                and _value(row, "m15_rsi") >= config.rsi_short_min
            )
            short_break = (
                _value(row, "m15_close") < _value(row, "m15_break_low")
                and _value(row, "m15_close") < _value(row, "m15_open")
                and _value(row, "m15_rsi") <= config.rsi_long_max
            )
            return 1 if long_trend and long_break else -1 if short_trend and short_break else 0
        long_rejection = (
            _value(row, "m15_low") <= _value(row, "m15_ema20")
            and _value(row, "m15_close") >= _value(row, "m15_ema20")
            and _value(row, "m15_close") > _value(row, "m15_open")
            and _value(row, "m15_rsi") <= config.rsi_long_max
        )
        short_rejection = (
            _value(row, "m15_high") >= _value(row, "m15_ema20")
            and _value(row, "m15_close") <= _value(row, "m15_ema20")
            and _value(row, "m15_close") < _value(row, "m15_open")
            and _value(row, "m15_rsi") >= config.rsi_short_min
        )
        return 1 if long_trend and long_rejection else -1 if short_trend and short_rejection else 0
    if _value(row, "h1_adx") > config.range_adx_max:
        return 0
    if _value(row, "m15_low") <= _value(row, "bb_lower") and _value(row, "m15_close") > _value(row, "m15_low") and _value(row, "m15_rsi") <= config.rsi_long_max:
        return 1
    if _value(row, "m15_high") >= _value(row, "bb_upper") and _value(row, "m15_close") < _value(row, "m15_high") and _value(row, "m15_rsi") >= config.rsi_short_min:
        return -1
    return 0


def _floor_volume(value: float, step: float) -> float:
    return floor((value + 1e-12) / step) * step


def build_plan(
    timestamp: pd.Timestamp,
    anchor: float,
    side: int,
    atr_value: float,
    balance: float,
    config: StrategyConfig,
    spec: SymbolSpec,
) -> GridPlan | None:
    if side not in {-1, 1} or not np.isfinite(atr_value) or atr_value <= 0:
        return None
    direction = side if config.mode == "momentum" else -side
    entries = tuple(
        anchor + direction * atr_value * (config.first_offset_atr + config.grid_step_atr * index)
        for index in range(config.grid_levels)
    )
    if config.mode == "momentum":
        stop = anchor - side * atr_value * config.stop_extra_atr
    else:
        deepest = min(entries) if side == 1 else max(entries)
        stop = deepest - atr_value * config.stop_extra_atr if side == 1 else deepest + atr_value * config.stop_extra_atr
    risk_cash = balance * config.risk_pct / 100
    risk_per_lot = sum(abs(entry - stop) * spec.contract_size for entry in entries)
    if risk_per_lot <= 0:
        return None
    lot_each = _floor_volume(risk_cash / risk_per_lot, spec.volume_step)
    if lot_each < spec.volume_min:
        return None
    lot_each = min(lot_each, spec.volume_max)
    return GridPlan(timestamp, side, config.mode, entries, stop, atr_value, lot_each, risk_cash)


def planned_loss(plan: GridPlan, spec: SymbolSpec) -> float:
    return sum(abs(entry - plan.stop) * spec.contract_size * plan.lot_each for entry in plan.entries)


def run_backtest(
    raw_m5: pd.DataFrame,
    config: StrategyConfig,
    spec: SymbolSpec,
    starting_balance: float = 10_000.0,
    prepared: bool = False,
) -> BacktestResult:
    frame = raw_m5.copy() if prepared else prepare_features(raw_m5)
    balance = starting_balance
    peak_balance = balance
    peak_equity = balance
    max_dd = 0.0
    realized_dd = 0.0
    max_exposure = 0.0
    records: list[TradeRecord] = []
    equity_rows: list[tuple[pd.Timestamp, float, float]] = []
    plan: GridPlan | None = None
    filled: list[float] = []
    opened_at: pd.Timestamp | None = None
    current_stop = 0.0
    target = 0.0
    initial_risk_price = 0.0
    planned_index = 0
    plan_created_position = -1
    opened_position = -1
    last_exit_index = -10_000
    current_day = None
    day_start_balance = balance

    def close_basket(timestamp: pd.Timestamp, exit_price: float, reason: str) -> None:
        nonlocal balance, plan, filled, opened_at, current_stop, target, initial_risk_price, planned_index, last_exit_index
        if plan is None or not filled or opened_at is None:
            return
        average = float(np.mean(filled))
        pnl = sum((exit_price - entry) * plan.side * spec.contract_size * plan.lot_each for entry in filled)
        risk = sum(abs(entry - plan.stop) * spec.contract_size * plan.lot_each for entry in filled)
        balance += pnl
        records.append(
            TradeRecord(
                opened=opened_at,
                closed=timestamp,
                side="BUY" if plan.side == 1 else "SELL",
                mode=plan.mode,
                levels_filled=len(filled),
                lot_total=plan.lot_each * len(filled),
                average_entry=average,
                initial_stop=plan.stop,
                exit_price=exit_price,
                pnl=pnl,
                r_multiple=pnl / risk if risk else 0.0,
                reason=reason,
            )
        )
        last_exit_index = planned_index
        plan = None
        filled = []
        opened_at = None
        current_stop = target = initial_risk_price = 0.0

    for position, row in enumerate(frame.itertuples()):
        timestamp = row.Index
        planned_index = position
        spread_price = max(float(row.spread) * spec.point, 0.0)
        if current_day != timestamp.date():
            current_day = timestamp.date()
            day_start_balance = balance

        # Existing orders and positions are processed before a fresh signal is created.
        if plan is not None:
            while len(filled) < len(plan.entries):
                entry = plan.entries[len(filled)]
                if plan.mode == "momentum":
                    touched = (row.high + spread_price >= entry) if plan.side == 1 else (row.low <= entry)
                else:
                    touched = (row.low + spread_price <= entry) if plan.side == 1 else (row.high >= entry)
                if not touched:
                    break
                filled.append(entry)
                opened_at = opened_at or timestamp
                if opened_position < 0:
                    opened_position = position
                average = float(np.mean(filled))
                current_stop = plan.stop
                initial_risk_price = abs(average - plan.stop)
                if plan.mode == "momentum":
                    extreme = max(plan.entries) if plan.side == 1 else min(plan.entries)
                    target = extreme + plan.side * config.target_atr * plan.atr
                else:
                    target = average + plan.side * config.target_atr * plan.atr

            if filled:
                average = float(np.mean(filled))
                bid_high, bid_low = float(row.high), float(row.low)
                ask_high, ask_low = bid_high + spread_price, bid_low + spread_price
                stop_hit = bid_low <= current_stop if plan.side == 1 else ask_high >= current_stop
                target_hit = bid_high >= target if plan.side == 1 else ask_low <= target
                if stop_hit:
                    close_basket(timestamp, current_stop, "STOP")
                elif target_hit:
                    close_basket(timestamp, target, "TARGET")
                else:
                    favorable = (bid_high - average) if plan.side == 1 else (average - ask_low)
                    if initial_risk_price > 0 and config.be_trigger_r > 0 and favorable >= config.be_trigger_r * initial_risk_price:
                        lock = average + plan.side * config.be_lock_r * initial_risk_price
                        current_stop = max(current_stop, lock) if plan.side == 1 else min(current_stop, lock)
                    if config.trail_start_r > 0 and favorable >= config.trail_start_r * initial_risk_price:
                        trail = (bid_high - config.trail_distance_atr * plan.atr) if plan.side == 1 else (ask_low + config.trail_distance_atr * plan.atr)
                        current_stop = max(current_stop, trail) if plan.side == 1 else min(current_stop, trail)
                    if opened_at is not None and position - opened_position >= config.max_hold_bars:
                        exit_price = float(row.close) if plan.side == 1 else float(row.close) + spread_price
                        close_basket(timestamp, exit_price, "TIME")
            elif position - plan_created_position >= config.pending_expiry_bars:
                plan = None

        if plan is None and position - last_exit_index >= config.cooldown_bars:
            daily_loss_pct = max(0.0, (day_start_balance - balance) / day_start_balance * 100) if day_start_balance else 0.0
            if spread_price <= config.max_spread_price and daily_loss_pct < config.max_daily_loss_pct:
                side = signal_from_row(row, config)
                if side:
                    anchor = float(row.close)
                    if config.mode == "breakout":
                        anchor = float(row.m15_break_high if side == 1 else row.m15_break_low)
                    plan = build_plan(timestamp, anchor, side, float(row.m15_atr), balance, config, spec)
                    if plan is not None:
                        plan_created_position = position
                        opened_position = -1

        unrealized = 0.0
        exposure = 0.0
        if plan is not None and filled:
            mark = float(row.close) if plan.side == 1 else float(row.close) + spread_price
            unrealized = sum((mark - entry) * plan.side * spec.contract_size * plan.lot_each for entry in filled)
            exposure = sum(abs(entry - plan.stop) * spec.contract_size * plan.lot_each for entry in filled)
        equity = balance + unrealized
        peak_equity = max(peak_equity, equity)
        peak_balance = max(peak_balance, balance)
        max_dd = max(max_dd, (peak_equity - equity) / peak_equity * 100 if peak_equity else 0.0)
        realized_dd = max(realized_dd, (peak_balance - balance) / peak_balance * 100 if peak_balance else 0.0)
        max_exposure = max(max_exposure, exposure / max(equity, 1.0) * 100)
        equity_rows.append((timestamp, balance, equity))

    if plan is not None and filled:
        last = frame.iloc[-1]
        spread_price = float(last.get("spread", 0.0)) * spec.point
        exit_price = float(last["close"]) if plan.side == 1 else float(last["close"]) + spread_price
        close_basket(frame.index[-1], exit_price, "END")

    wins = sum(record.pnl > 0 for record in records)
    losses = sum(record.pnl < 0 for record in records)
    gross_profit = sum(max(record.pnl, 0.0) for record in records)
    gross_loss = -sum(min(record.pnl, 0.0) for record in records)
    streak = max_streak = 0
    for record in records:
        streak = streak + 1 if record.pnl < 0 else 0
        max_streak = max(max_streak, streak)
    equity_frame = pd.DataFrame(equity_rows, columns=["time", "balance", "equity"]).set_index("time")
    return BacktestResult(
        start=frame.index[0], end=frame.index[-1], starting_balance=starting_balance,
        ending_balance=balance, net_profit=balance - starting_balance,
        return_pct=(balance / starting_balance - 1) * 100,
        trades=len(records), wins=wins, losses=losses,
        win_rate=wins / len(records) * 100 if records else 0.0,
        profit_factor=gross_profit / gross_loss if gross_loss else (float("inf") if gross_profit else 0.0),
        max_drawdown_pct=max_dd, realized_drawdown_pct=realized_dd,
        max_consecutive_losses=max_streak, exposure_pct_max=max_exposure,
        records=records, equity=equity_frame,
    )


def records_frame(records: Iterable[TradeRecord]) -> pd.DataFrame:
    return pd.DataFrame([record.to_dict() for record in records])
