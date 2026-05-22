from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import pandas as pd

from .config import AppConfig
from .decision import TradeDecision, evaluate_trade_signal, resolve_trade_filters
from .mt5_client import MT5Client
from .strategy import Signal, generate_signals
from .strategy_modes import is_partial_strategy, tp_protection_enabled


@dataclass
class BacktestTrade:
    time: str
    side: str
    entry: float
    sl: float
    tps: list[float]
    lot_per_leg: float
    risk_usd: float
    pnl: float
    session: str
    decision: str
    spread_atr: float
    exit_time: str | None = None
    exit_kind: str | None = None


@dataclass
class BacktestSkip:
    time: str
    side: str
    entry: float
    reason: str
    code: str
    spread_atr: float


@dataclass
class SymbolBacktest:
    symbol: str
    market_key: str
    name: str
    timeframe: str
    raw_signals: int
    skipped_signals: int
    trades: int
    wins: int
    losses: int
    win_rate: float
    pnl: float
    max_drawdown: float
    error: str | None = None
    trade_logs: list[BacktestTrade] | None = None
    skipped_logs: list[BacktestSkip] | None = None


@dataclass
class _OpenTrade:
    signal: Signal
    df: pd.DataFrame
    row_index: int
    tp_protection: bool
    partial_execution: bool
    entry_unix: int
    exit_unix: int
    full_pnl: float
    realized: bool = False


@dataclass
class _SignalJob:
    entry_unix: int
    symbol_cfg: object
    df: pd.DataFrame
    row_index: int
    signal: Signal
    point: float


@dataclass
class _SymbolAccumulator:
    symbol_cfg: object
    raw_signals: int
    trade_logs: list[BacktestTrade] = field(default_factory=list)
    skipped_logs: list[BacktestSkip] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    skipped: int = 0
    symbol_pnl: float = 0.0
    peak_pnl: float = 0.0
    max_dd: float = 0.0
    error: str | None = None

    def record_trade(self, trade_pnl: float) -> None:
        self.symbol_pnl += trade_pnl
        self.peak_pnl = max(self.peak_pnl, self.symbol_pnl)
        self.max_dd = max(self.max_dd, self.peak_pnl - self.symbol_pnl)
        if trade_pnl > 0:
            self.wins += 1
        elif trade_pnl < 0:
            self.losses += 1

    def to_result(self) -> SymbolBacktest:
        trades = self.wins + self.losses
        symbol_cfg = self.symbol_cfg
        return SymbolBacktest(
            symbol=symbol_cfg.symbol,
            market_key=symbol_cfg.key,
            name=symbol_cfg.name,
            timeframe=symbol_cfg.timeframe,
            raw_signals=self.raw_signals,
            skipped_signals=self.skipped,
            trades=trades,
            wins=self.wins,
            losses=self.losses,
            win_rate=round((self.wins / trades * 100) if trades else 0.0, 2),
            pnl=round(self.symbol_pnl, 2),
            max_drawdown=round(self.max_dd, 2),
            error=self.error,
            trade_logs=self.trade_logs,
            skipped_logs=self.skipped_logs,
        )


class DailyLossGuard:
    """Mirrors live daily loss guard: block entries when equity is down >= max_daily_loss_pct."""

    def __init__(self, starting_balance: float, max_daily_loss_pct: float | None):
        self.enabled = max_daily_loss_pct is not None and max_daily_loss_pct > 0
        self.max_daily_loss_pct = float(max_daily_loss_pct or 0.0)
        self.balance = float(starting_balance)
        self.current_day: str | None = None
        self.day_start_balance = float(starting_balance)
        self.open_trades: list[_OpenTrade] = []

    def _utc_day(self, unix: int) -> str:
        return pd.Timestamp(int(unix), unit="s", tz="UTC").strftime("%Y-%m-%d")

    def _settle_through(self, as_of_unix: int) -> None:
        for trade in self.open_trades:
            if trade.realized or trade.exit_unix > as_of_unix:
                continue
            self.balance += trade.full_pnl
            trade.realized = True
        self.open_trades = [trade for trade in self.open_trades if not trade.realized]

    def _floating_pnl(self, client: MT5Client, as_of_unix: int) -> float:
        total = 0.0
        for trade in self.open_trades:
            if trade.entry_unix > as_of_unix:
                continue
            total += _trade_pnl_as_of(client, trade, as_of_unix)
        return total

    def equity_at(self, client: MT5Client, as_of_unix: int) -> float:
        self._settle_through(as_of_unix)
        return self.balance + self._floating_pnl(client, as_of_unix)

    def _roll_day(self, day: str, equity: float) -> None:
        if self.current_day == day:
            return
        if self.current_day is not None:
            self.day_start_balance = equity
        self.current_day = day

    def check_entry(self, client: MT5Client, entry_unix: int) -> tuple[bool, float, float]:
        if not self.enabled:
            return True, 0.0, 0.0
        equity = self.equity_at(client, entry_unix)
        self._roll_day(self._utc_day(entry_unix), equity)
        loss_limit = round(self.day_start_balance * self.max_daily_loss_pct / 100.0, 2)
        loss = round(max(0.0, self.day_start_balance - equity), 2)
        if loss_limit > 0 and loss >= loss_limit:
            return False, loss, loss_limit
        return True, loss, loss_limit

    def register_trade(
        self,
        signal: Signal,
        df: pd.DataFrame,
        row_index: int,
        tp_protection: bool,
        partial_execution: bool,
        entry_unix: int,
        exit_unix: int,
        full_pnl: float,
    ) -> None:
        self.open_trades.append(
            _OpenTrade(
                signal=signal,
                df=df,
                row_index=row_index,
                tp_protection=tp_protection,
                partial_execution=partial_execution,
                entry_unix=entry_unix,
                exit_unix=exit_unix,
                full_pnl=full_pnl,
            )
        )

    def finalize(self, client: MT5Client, as_of_unix: int) -> float:
        self._settle_through(as_of_unix)
        return self.balance


def _iso_time(value) -> str:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _trade_log(
    signal: Signal,
    pnl: float,
    decision: TradeDecision,
    *,
    exit_time: int | None = None,
    exit_kind: str | None = None,
) -> BacktestTrade:
    exit_iso = None
    if exit_time is not None:
        exit_iso = datetime.fromtimestamp(int(exit_time), tz=timezone.utc).replace(microsecond=0).isoformat()
    return BacktestTrade(
        time=_iso_time(signal.time),
        side=signal.side,
        entry=round(signal.entry, 5),
        sl=round(signal.sl, 5),
        tps=[round(tp, 5) for tp in signal.tps],
        lot_per_leg=signal.lot_per_leg,
        risk_usd=round(decision.risk_usd, 2),
        pnl=round(pnl, 2),
        session=signal.session,
        decision=decision.reason,
        spread_atr=round(decision.spread_atr, 3),
        exit_time=exit_iso,
        exit_kind=exit_kind,
    )


def _skip_log(signal: Signal, decision: TradeDecision) -> BacktestSkip:
    return BacktestSkip(
        time=_iso_time(signal.time),
        side=signal.side,
        entry=round(signal.entry, 5),
        reason=decision.reason,
        code=decision.code,
        spread_atr=round(decision.spread_atr, 3),
    )


def _historical_spread_price(row, point: float) -> float | None:
    try:
        spread_points = float(row.get("spread", 0.0))
    except AttributeError:
        spread_points = float(getattr(row, "spread", 0.0) or 0.0)
    if spread_points <= 0 or point <= 0:
        return None
    return spread_points * point


def _simulate_trade(client: MT5Client, signal: Signal, rows, tp_protection: bool) -> dict:
    active = [True for _ in signal.tps]
    stops = [signal.sl for _ in signal.tps]
    pnl = 0.0
    close = signal.entry
    exit_time: int | None = None
    exit_kind = "close"
    last_bar_time: int | None = None

    def row_unix(row) -> int:
        ts = getattr(row, "time", None)
        if hasattr(ts, "timestamp"):
            return int(ts.timestamp())
        return int(pd.Timestamp(ts).timestamp())

    for row in rows:
        high = float(row.high)
        low = float(row.low)
        close = float(row.close)
        bar_time = row_unix(row)
        last_bar_time = bar_time
        if signal.side == "buy":
            for index, is_active in enumerate(active):
                if is_active and low <= stops[index]:
                    pnl += client.money_for_distance(signal.symbol, signal.lot_per_leg, stops[index] - signal.entry)
                    active[index] = False
                    exit_kind = "sl"
            for index, tp in enumerate(signal.tps):
                if active[index] and high >= tp:
                    pnl += client.money_for_distance(signal.symbol, signal.lot_per_leg, tp - signal.entry)
                    active[index] = False
                    exit_kind = f"tp{index + 1}"
                    if tp_protection:
                        for move_index, still_active in enumerate(active):
                            if still_active and stops[move_index] < tp:
                                stops[move_index] = tp
        else:
            for index, is_active in enumerate(active):
                if is_active and high >= stops[index]:
                    pnl += client.money_for_distance(signal.symbol, signal.lot_per_leg, signal.entry - stops[index])
                    active[index] = False
                    exit_kind = "sl"
            for index, tp in enumerate(signal.tps):
                if active[index] and low <= tp:
                    pnl += client.money_for_distance(signal.symbol, signal.lot_per_leg, signal.entry - tp)
                    active[index] = False
                    exit_kind = f"tp{index + 1}"
                    if tp_protection:
                        for move_index, still_active in enumerate(active):
                            if still_active and stops[move_index] > tp:
                                stops[move_index] = tp
        if not any(active):
            exit_time = bar_time
            return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

    exit_time = last_bar_time
    for index, is_active in enumerate(active):
        if not is_active:
            continue
        if signal.side == "buy":
            pnl += client.money_for_distance(signal.symbol, signal.lot_per_leg, close - signal.entry)
        else:
            pnl += client.money_for_distance(signal.symbol, signal.lot_per_leg, signal.entry - close)
    return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}


def _simulate_trade_partial(client: MT5Client, signal: Signal, rows, tp_protection: bool) -> dict:
    tps = list(signal.tps)
    if not tps:
        return {"pnl": 0.0, "exit_time": None, "exit_kind": "close"}

    total_volume = signal.lot_per_leg * len(tps)
    slice_volume = total_volume / len(tps)
    remaining_volume = total_volume
    sl = float(signal.sl)
    partial_closed = 0
    pnl = 0.0
    exit_time: int | None = None
    exit_kind = "close"
    last_bar_time: int | None = None

    def row_unix(row) -> int:
        ts = getattr(row, "time", None)
        if hasattr(ts, "timestamp"):
            return int(ts.timestamp())
        return int(pd.Timestamp(ts).timestamp())

    def pnl_for_slice(volume: float, exit_price: float) -> float:
        if signal.side == "buy":
            return client.money_for_distance(signal.symbol, volume, exit_price - signal.entry)
        return client.money_for_distance(signal.symbol, volume, signal.entry - exit_price)

    for row in rows:
        high = float(row.high)
        low = float(row.low)
        close = float(row.close)
        bar_time = row_unix(row)
        last_bar_time = bar_time

        if remaining_volume <= 0:
            exit_time = bar_time
            return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

        if signal.side == "buy":
            if low <= sl:
                pnl += pnl_for_slice(remaining_volume, sl)
                exit_kind = "sl"
                exit_time = bar_time
                return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

            while partial_closed < len(tps) - 1 and high >= tps[partial_closed]:
                close_volume = slice_volume if partial_closed < len(tps) - 2 else remaining_volume - slice_volume
                close_volume = min(close_volume, remaining_volume)
                if close_volume <= 0:
                    break
                pnl += pnl_for_slice(close_volume, tps[partial_closed])
                remaining_volume -= close_volume
                partial_closed += 1
                exit_kind = f"tp{partial_closed}"
                if tp_protection:
                    sl = max(sl, tps[partial_closed - 1])

            if remaining_volume > 0 and high >= tps[-1]:
                pnl += pnl_for_slice(remaining_volume, tps[-1])
                exit_kind = f"tp{len(tps)}"
                exit_time = bar_time
                return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}
        else:
            if high >= sl:
                pnl += pnl_for_slice(remaining_volume, sl)
                exit_kind = "sl"
                exit_time = bar_time
                return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

            while partial_closed < len(tps) - 1 and low <= tps[partial_closed]:
                close_volume = slice_volume if partial_closed < len(tps) - 2 else remaining_volume - slice_volume
                close_volume = min(close_volume, remaining_volume)
                if close_volume <= 0:
                    break
                pnl += pnl_for_slice(close_volume, tps[partial_closed])
                remaining_volume -= close_volume
                partial_closed += 1
                exit_kind = f"tp{partial_closed}"
                if tp_protection:
                    sl = min(sl, tps[partial_closed - 1])

            if remaining_volume > 0 and low <= tps[-1]:
                pnl += pnl_for_slice(remaining_volume, tps[-1])
                exit_kind = f"tp{len(tps)}"
                exit_time = bar_time
                return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}

    exit_time = last_bar_time
    if remaining_volume > 0:
        pnl += pnl_for_slice(remaining_volume, close)
    return {"pnl": pnl, "exit_time": exit_time, "exit_kind": exit_kind}


def _trade_pnl(client: MT5Client, signal: Signal, rows, tp_protection: bool, *, partial_execution: bool = False) -> float:
    if partial_execution:
        return float(_simulate_trade_partial(client, signal, rows, tp_protection)["pnl"])
    return float(_simulate_trade(client, signal, rows, tp_protection)["pnl"])


def _trade_pnl_as_of(client: MT5Client, trade: _OpenTrade, as_of_unix: int) -> float:
    if trade.exit_unix <= as_of_unix:
        return trade.full_pnl
    after = trade.df.iloc[trade.row_index + 1 :]
    rows = tuple(row for row in after.itertuples() if _bar_unix(row.time) <= as_of_unix)
    if not rows:
        return 0.0
    if trade.partial_execution:
        return float(_simulate_trade_partial(client, trade.signal, rows, trade.tp_protection)["pnl"])
    return float(_simulate_trade(client, trade.signal, rows, trade.tp_protection)["pnl"])


def _bar_unix(value) -> int:
    if hasattr(value, "timestamp"):
        return int(value.timestamp())
    return int(pd.Timestamp(value).timestamp())


def _candles_payload(df) -> list[dict]:
    candles: list[dict] = []
    for row in df.itertuples():
        candles.append(
            {
                "time": _bar_unix(row.time),
                "open": round(float(row.open), 5),
                "high": round(float(row.high), 5),
                "low": round(float(row.low), 5),
                "close": round(float(row.close), 5),
            }
        )
    return candles


def _build_daily_performance(closed_trades: list[dict], starting_balance: float) -> list[dict]:
    if not closed_trades:
        return []

    ordered = sorted(closed_trades, key=lambda item: item["sort_time"])
    by_day: dict[str, dict] = {}
    balance = float(starting_balance)

    for trade in ordered:
        day = pd.Timestamp(trade["sort_time"], unit="s", tz="UTC").strftime("%Y-%m-%d")
        bucket = by_day.setdefault(
            day,
            {
                "pnl": 0.0,
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "start_balance": None,
                "trade_rows": [],
            },
        )
        if bucket["start_balance"] is None:
            bucket["start_balance"] = round(balance, 2)

        pnl = float(trade["pnl"])
        balance += pnl
        bucket["pnl"] += pnl
        bucket["trades"] += 1
        if pnl > 0:
            bucket["wins"] += 1
        elif pnl < 0:
            bucket["losses"] += 1

        exit_time = trade.get("exit_time")
        if not exit_time:
            exit_time = pd.Timestamp(trade["sort_time"], unit="s", tz="UTC").replace(microsecond=0).isoformat()

        bucket["trade_rows"].append(
            {
                "symbol": trade["symbol"],
                "side": trade.get("side"),
                "entry_time": trade.get("entry_time"),
                "exit_time": exit_time,
                "exit_kind": trade.get("exit_kind"),
                "pnl": round(pnl, 2),
                "balance_after": round(balance, 2),
            }
        )

    rows: list[dict] = []
    for day in sorted(by_day.keys()):
        bucket = by_day[day]
        end_balance = bucket["trade_rows"][-1]["balance_after"] if bucket["trade_rows"] else bucket["start_balance"]
        rows.append(
            {
                "date": day,
                "trades": bucket["trades"],
                "wins": bucket["wins"],
                "losses": bucket["losses"],
                "pnl": round(bucket["pnl"], 2),
                "start_balance": bucket["start_balance"],
                "balance": round(float(end_balance or starting_balance), 2),
                "trade_rows": bucket["trade_rows"],
            }
        )
    return rows


def _symbol_payload(item: SymbolBacktest) -> dict:
    payload = asdict(item)
    payload["trade_logs"] = [asdict(trade) for trade in (item.trade_logs or [])]
    payload["skipped_logs"] = [asdict(skip) for skip in (item.skipped_logs or [])]
    return payload


def _decision_rules_payload(config: AppConfig, filters) -> dict:
    risk_cfg = config.risk
    return {
        "profile": config.bot.trade_decision_profile,
        "execution_filters_applied": filters.spread or filters.tp1_spread or filters.risk,
        "account_filters_applied": filters.existing_position or filters.max_setups,
        "daily_loss_guard_applied": risk_cfg.daily_loss_guard_active(),
        "filters": asdict(filters),
        "max_spread_atr": config.risk.max_spread_atr,
        "max_setup_risk_usd": config.risk.max_setup_risk_usd,
        "min_tp1_spread_multiple": config.risk.min_tp1_spread_multiple,
        "max_extension_atr": config.risk.max_extension_atr,
        "use_daily_loss_guard": risk_cfg.use_daily_loss_guard,
        "max_daily_loss_pct": risk_cfg.max_daily_loss_pct,
    }


def _event_payload(
    event_id: int,
    signal: Signal,
    decision: TradeDecision,
    *,
    event_type: str,
    pnl: float = 0.0,
    exit_time: int | None = None,
    exit_kind: str | None = None,
) -> dict:
    return {
        "id": event_id,
        "bar_time": _bar_unix(signal.time),
        "type": event_type,
        "side": signal.side,
        "entry": round(signal.entry, 5),
        "sl": round(signal.sl, 5),
        "tps": [round(tp, 5) for tp in signal.tps],
        "pnl": round(float(pnl), 2),
        "exit_time": exit_time,
        "exit_kind": exit_kind,
        "reason": decision.reason,
        "code": decision.code,
        "session": signal.session,
        "risk_usd": round(decision.risk_usd, 2),
    }


def _daily_loss_skip_decision(
    signal: Signal,
    decision: TradeDecision,
    *,
    loss: float,
    loss_limit: float,
    max_daily_loss_pct: float,
) -> TradeDecision:
    return TradeDecision(
        allowed=False,
        code="daily_loss_guard",
        reason=(
            f"daily loss guard: loss ${loss:.2f} >= limit ${loss_limit:.2f} "
            f"({max_daily_loss_pct:g}% of start-of-day balance)"
        ),
        risk_usd=decision.risk_usd,
        spread=decision.spread,
        spread_atr=decision.spread_atr,
        tp1_distance=decision.tp1_distance,
        min_tp1_distance=decision.min_tp1_distance,
    )


def _symbol_point(client: MT5Client, symbol: str, logger: logging.Logger | None = None) -> float:
    try:
        info = client.symbol_info(symbol)
        return float(getattr(info, "point", 0.0) or 0.0)
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.warning("BACKTEST %s could not read symbol point: %s", symbol, exc)
        return 0.0


def _collect_signal_jobs(
    client: MT5Client,
    config: AppConfig,
    symbol_cfg,
    df: pd.DataFrame,
    filters,
    logger: logging.Logger | None = None,
) -> tuple[list[_SignalJob], int]:
    signals = generate_signals(df, symbol_cfg, config.risk)
    point = _symbol_point(client, symbol_cfg.symbol, logger)
    jobs: list[_SignalJob] = []
    for signal in signals:
        signal_index = df.index[df["time"] == signal.time]
        if len(signal_index) == 0:
            continue
        jobs.append(
            _SignalJob(
                entry_unix=_bar_unix(signal.time),
                symbol_cfg=symbol_cfg,
                df=df,
                row_index=int(signal_index[0]),
                signal=signal,
                point=point,
            )
        )
    return jobs, len(signals)


def _execute_backtest_jobs(
    client: MT5Client,
    config: AppConfig,
    jobs: list[_SignalJob],
    accumulators: dict[str, _SymbolAccumulator],
    strategy: str,
    starting_balance: float,
    filters,
    *,
    include_events: bool = False,
    end_unix: int | None = None,
    logger: logging.Logger | None = None,
) -> tuple[list[dict], list[dict]]:
    tp_protection = tp_protection_enabled(strategy)
    partial_execution = is_partial_strategy(strategy)
    daily_guard = DailyLossGuard(starting_balance, config.risk.effective_daily_loss_pct())
    closed_trades: list[dict] = []
    events: list[dict] = []

    for event_id, job in enumerate(sorted(jobs, key=lambda item: item.entry_unix), start=1):
        symbol_key = job.symbol_cfg.symbol
        accumulator = accumulators[symbol_key]
        if accumulator.error:
            continue

        decision = evaluate_trade_signal(
            client,
            config,
            job.signal,
            job.symbol_cfg,
            spread=_historical_spread_price(job.df.iloc[job.row_index], job.point),
            filters=filters,
        )
        if not decision.allowed:
            accumulator.skipped += 1
            accumulator.skipped_logs.append(_skip_log(job.signal, decision))
            if include_events:
                events.append(_event_payload(event_id, job.signal, decision, event_type="skip"))
            continue

        allowed, loss, loss_limit = daily_guard.check_entry(client, job.entry_unix)
        if not allowed:
            skip_decision = _daily_loss_skip_decision(
                job.signal,
                decision,
                loss=loss,
                loss_limit=loss_limit,
                max_daily_loss_pct=daily_guard.max_daily_loss_pct,
            )
            accumulator.skipped += 1
            accumulator.skipped_logs.append(_skip_log(job.signal, skip_decision))
            if include_events:
                events.append(_event_payload(event_id, job.signal, skip_decision, event_type="skip"))
            if logger:
                logger.info(
                    "BACKTEST DAILY LOSS SKIP %s entry=%s loss=%.2f limit=%.2f",
                    symbol_key,
                    _iso_time(job.signal.time),
                    loss,
                    loss_limit,
                )
            continue

        after = job.df.iloc[job.row_index + 1 :]
        if partial_execution:
            simulation = _simulate_trade_partial(client, job.signal, after.itertuples(), tp_protection)
        else:
            simulation = _simulate_trade(client, job.signal, after.itertuples(), tp_protection)
        trade_pnl = float(simulation["pnl"])
        exit_unix = int(simulation.get("exit_time") or job.entry_unix)
        daily_guard.register_trade(
            job.signal,
            job.df,
            job.row_index,
            tp_protection,
            partial_execution,
            job.entry_unix,
            exit_unix,
            trade_pnl,
        )
        trade_log = _trade_log(
            job.signal,
            trade_pnl,
            decision,
            exit_time=simulation.get("exit_time"),
            exit_kind=simulation.get("exit_kind"),
        )
        accumulator.trade_logs.append(trade_log)
        accumulator.record_trade(trade_pnl)
        if include_events:
            events.append(
                _event_payload(
                    event_id,
                    job.signal,
                    decision,
                    event_type="trade",
                    pnl=trade_pnl,
                    exit_time=simulation.get("exit_time"),
                    exit_kind=simulation.get("exit_kind"),
                )
            )
        closed_trades.append(
            {
                "symbol": symbol_key,
                "side": job.signal.side,
                "entry_time": _iso_time(job.signal.time),
                "exit_time": trade_log.exit_time,
                "exit_kind": simulation.get("exit_kind"),
                "pnl": round(trade_pnl, 2),
                "sort_time": exit_unix,
            }
        )

    if end_unix is not None:
        final_balance = daily_guard.finalize(client, end_unix)
    else:
        final_balance = daily_guard.balance
    return closed_trades, events, final_balance


def _run_symbol_backtest(
    client: MT5Client,
    config: AppConfig,
    symbol_cfg,
    df: pd.DataFrame,
    strategy: str,
    starting_balance: float,
    filters,
    *,
    include_events: bool = False,
    logger: logging.Logger | None = None,
) -> tuple[SymbolBacktest, list[dict], list[dict]]:
    jobs, raw_signals = _collect_signal_jobs(client, config, symbol_cfg, df, filters, logger)
    accumulator = _SymbolAccumulator(symbol_cfg=symbol_cfg, raw_signals=raw_signals)
    end_unix = _bar_unix(df.iloc[-1]["time"]) if len(df) else 0
    closed_trades, events, _final_balance = _execute_backtest_jobs(
        client,
        config,
        jobs,
        {symbol_cfg.symbol: accumulator},
        strategy,
        starting_balance,
        filters,
        include_events=include_events,
        end_unix=end_unix,
        logger=logger,
    )
    return accumulator.to_result(), closed_trades, events


def run_backtest(
    client: MT5Client,
    config: AppConfig,
    start: datetime,
    end: datetime,
    strategy: str,
    starting_balance: float = 1000.0,
    logger: logging.Logger | None = None,
) -> dict:
    filters = resolve_trade_filters(config)
    client.initialize()
    end_utc = end if end.tzinfo is not None else end.replace(tzinfo=timezone.utc)
    end_unix = int(end_utc.timestamp())
    accumulators: dict[str, _SymbolAccumulator] = {}
    all_jobs: list[_SignalJob] = []
    symbols = config.enabled_symbols

    for index, symbol_cfg in enumerate(symbols, start=1):
        if logger:
            logger.info(
                "BACKTEST %s/%s %s %s",
                index,
                len(symbols),
                symbol_cfg.symbol,
                symbol_cfg.timeframe,
            )
        try:
            df = client.rates_range(symbol_cfg.symbol, symbol_cfg.timeframe, start, end)
        except Exception as exc:  # noqa: BLE001
            accumulators[symbol_cfg.symbol] = _SymbolAccumulator(
                symbol_cfg=symbol_cfg,
                raw_signals=0,
                error=str(exc),
            )
            continue

        jobs, raw_signals = _collect_signal_jobs(client, config, symbol_cfg, df, filters, logger)
        accumulators[symbol_cfg.symbol] = _SymbolAccumulator(symbol_cfg=symbol_cfg, raw_signals=raw_signals)
        all_jobs.extend(jobs)

    closed_trades, _events, final_balance = _execute_backtest_jobs(
        client,
        config,
        all_jobs,
        accumulators,
        strategy,
        starting_balance,
        filters,
        end_unix=end_unix,
        logger=logger,
    )
    rows = [accumulators[symbol_cfg.symbol].to_result() for symbol_cfg in symbols if symbol_cfg.symbol in accumulators]
    total_pnl = round(final_balance - starting_balance, 2)
    daily_performance = _build_daily_performance(closed_trades, starting_balance)

    return {
        "strategy": strategy,
        "decision_rules": _decision_rules_payload(config, filters),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "starting_balance": round(starting_balance, 2),
        "total_pnl": total_pnl,
        "end_balance_if_sequential": round(final_balance, 2),
        "daily_performance": daily_performance,
        "symbols": [_symbol_payload(item) for item in rows],
    }


def run_chart_backtest(
    client: MT5Client,
    config: AppConfig,
    symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    strategy: str,
) -> dict:
    filters = resolve_trade_filters(config)
    client.initialize()

    symbol_cfg = next((item for item in config.symbols if item.symbol == symbol), None)
    if symbol_cfg is None:
        raise ValueError(f"Unknown symbol: {symbol}")

    if timeframe not in {"M1", "M5", "M15", "M30", "H1"}:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    effective_symbol_cfg = symbol_cfg.model_copy(update={"timeframe": timeframe})
    df = client.rates_range(symbol, timeframe, start, end)
    symbol_result, _closed_trades, events = _run_symbol_backtest(
        client,
        config,
        effective_symbol_cfg,
        df,
        strategy,
        1000.0,
        filters,
        include_events=True,
    )

    return {
        "symbol": symbol,
        "name": symbol_cfg.name,
        "timeframe": timeframe,
        "configured_timeframe": symbol_cfg.timeframe,
        "settings_timeframe_match": timeframe == symbol_cfg.timeframe,
        "strategy": strategy,
        "decision_rules": _decision_rules_payload(config, filters),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "candles": _candles_payload(df),
        "events": events,
        "summary": {
            "bars": len(df),
            "raw_signals": symbol_result.raw_signals,
            "trades": symbol_result.trades,
            "skipped": symbol_result.skipped_signals,
            "wins": symbol_result.wins,
            "losses": symbol_result.losses,
            "pnl": symbol_result.pnl,
        },
    }
