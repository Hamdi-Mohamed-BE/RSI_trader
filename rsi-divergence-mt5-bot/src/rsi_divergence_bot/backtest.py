from __future__ import annotations

import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

import pandas as pd

from .config import AppConfig
from .decision import TradeDecision, evaluate_trade_signal, historical_spread_price, resolve_trade_filters, skip_should_mark_seen
from .live_session import LIVE_SCAN_BARS, collect_live_scan_opportunities, extended_history_start
from .mt5_client import MT5Client
from .portfolio import BacktestPortfolio
from .strategy import Signal
from .strategy_modes import (
    closes_opposite_before_entry,
    is_box_theory_strategy,
    is_partial_strategy,
    is_single_leg_strategy,
    tp_protection_enabled,
)
from .trade_execution import simulate_partial_trade, simulate_single_trade, simulate_split_trade


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
    scan_unix: int
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

    def scan_blocked(self, client: MT5Client, scan_unix: int) -> tuple[bool, float, float]:
        allowed, loss, loss_limit = self.check_entry(client, scan_unix)
        return (not allowed), loss, loss_limit

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


def _trade_pnl(client: MT5Client, signal: Signal, rows, tp_protection: bool, *, partial_execution: bool = False) -> float:
    if partial_execution:
        return float(simulate_partial_trade(client, signal, rows, tp_protection)["pnl"])
    return float(simulate_split_trade(client, signal, rows, tp_protection)["pnl"])


def _trade_pnl_as_of(client: MT5Client, trade: _OpenTrade, as_of_unix: int) -> float:
    if trade.exit_unix <= as_of_unix:
        return trade.full_pnl
    after = trade.df.iloc[trade.row_index + 1 :]
    rows = tuple(row for row in after.itertuples() if _bar_unix(row.time) <= as_of_unix)
    if not rows:
        return 0.0
    if trade.partial_execution:
        return float(simulate_partial_trade(client, trade.signal, rows, trade.tp_protection)["pnl"])
    return float(simulate_split_trade(client, trade.signal, rows, trade.tp_protection)["pnl"])


def _opposite_side(side: str) -> str:
    return "sell" if side == "buy" else "buy"


def _force_close_market_trades(
    daily_guard: DailyLossGuard,
    portfolio: BacktestPortfolio,
    client: MT5Client,
    market_key: str,
    as_of_unix: int,
    *,
    side: str | None = None,
) -> list[tuple[_OpenTrade, float]]:
    results: list[tuple[_OpenTrade, float]] = []
    for trade in list(daily_guard.open_trades):
        if trade.realized or trade.signal.market_key != market_key:
            continue
        if side is not None and trade.signal.side != side:
            continue
        pnl = _trade_pnl_as_of(client, trade, as_of_unix)
        daily_guard.balance += pnl
        trade.realized = True
        trade.full_pnl = pnl
        trade.exit_unix = as_of_unix
        results.append((trade, pnl))
    daily_guard.open_trades = [trade for trade in daily_guard.open_trades if not trade.realized]
    if results:
        portfolio.close_market_setups(market_key)
    return results


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


def _decision_rules_payload(config: AppConfig, filters, *, strategy: str) -> dict:
    risk_cfg = config.risk
    payload = {
        "profile": config.bot.trade_decision_profile,
        "bot_strategy": config.bot.strategy,
        "backtest_strategy": strategy,
        "signal_selection": "live_poll_mirror",
        "scan_bars": LIVE_SCAN_BARS,
        "poll_seconds": config.bot.poll_seconds,
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
        "enabled_symbols": len(config.enabled_symbols),
    }
    if is_box_theory_strategy(strategy):
        payload["box_theory"] = config.box_theory.model_dump()
    return payload


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
    *,
    start_unix: int,
    end_unix: int,
    logger: logging.Logger | None = None,
) -> tuple[list[_SignalJob], int]:
    point = _symbol_point(client, symbol_cfg.symbol, logger)
    opportunities, raw_signals = collect_live_scan_opportunities(
        df,
        symbol_cfg,
        config,
        start_unix=start_unix,
        end_unix=end_unix,
        point=point,
        retry_max_setups=filters.max_setups,
    )
    jobs: list[_SignalJob] = []
    for opportunity in opportunities:
        jobs.append(
            _SignalJob(
                scan_unix=opportunity.scan_unix,
                entry_unix=opportunity.entry_unix,
                symbol_cfg=symbol_cfg,
                df=df,
                row_index=opportunity.row_index,
                signal=opportunity.signal,
                point=point,
            )
        )
    return jobs, raw_signals


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
) -> tuple[list[dict], list[dict], float]:
    tp_protection = tp_protection_enabled(strategy)
    partial_execution = is_partial_strategy(strategy)
    single_leg = is_single_leg_strategy(strategy)
    box_mode = closes_opposite_before_entry(strategy)
    daily_guard = DailyLossGuard(starting_balance, config.risk.effective_daily_loss_pct())
    portfolio = BacktestPortfolio()
    closed_trades: list[dict] = []
    events: list[dict] = []
    symbol_order = {symbol_cfg.symbol: index for index, symbol_cfg in enumerate(config.enabled_symbols)}

    jobs_sorted = sorted(
        jobs,
        key=lambda item: (item.scan_unix, symbol_order.get(item.symbol_cfg.symbol, 999)),
    )

    current_scan: int | None = None
    scan_blocked = False
    blocked_loss = 0.0
    blocked_limit = 0.0

    for event_id, job in enumerate(jobs_sorted, start=1):
        symbol_key = job.symbol_cfg.symbol
        accumulator = accumulators[symbol_key]
        if accumulator.error:
            continue

        if job.scan_unix != current_scan:
            portfolio.settle_through(job.scan_unix)
            current_scan = job.scan_unix
            scan_blocked, blocked_loss, blocked_limit = daily_guard.scan_blocked(client, job.scan_unix)

        if scan_blocked:
            placeholder = evaluate_trade_signal(
                client,
                config,
                job.signal,
                job.symbol_cfg,
                spread=historical_spread_price(job.df.iloc[job.row_index], job.point),
                seen=portfolio.is_seen(job.signal.setup_id),
                filters=filters,
                market_position_keys=portfolio.open_market_keys() if filters.existing_position else None,
                active_setup_count=portfolio.active_setup_count() if filters.max_setups else None,
            )
            skip_decision = _daily_loss_skip_decision(
                job.signal,
                placeholder,
                loss=blocked_loss,
                loss_limit=blocked_limit,
                max_daily_loss_pct=daily_guard.max_daily_loss_pct,
            )
            accumulator.skipped += 1
            accumulator.skipped_logs.append(_skip_log(job.signal, skip_decision))
            if include_events:
                events.append(_event_payload(event_id, job.signal, skip_decision, event_type="skip"))
            continue

        if portfolio.is_seen(job.signal.setup_id):
            decision = evaluate_trade_signal(
                client,
                config,
                job.signal,
                job.symbol_cfg,
                seen=True,
                filters=filters,
            )
            accumulator.skipped += 1
            accumulator.skipped_logs.append(_skip_log(job.signal, decision))
            if include_events:
                events.append(_event_payload(event_id, job.signal, decision, event_type="skip"))
            continue

        if box_mode:
            for trade, early_pnl in _force_close_market_trades(
                daily_guard,
                portfolio,
                client,
                job.signal.market_key,
                job.scan_unix,
                side=_opposite_side(job.signal.side),
            ):
                early_decision = TradeDecision(
                    allowed=True,
                    code="force_close",
                    reason="Box Theory pyramiding=0: closed opposite position",
                    risk_usd=0.0,
                    spread=0.0,
                    spread_atr=0.0,
                    tp1_distance=0.0,
                    min_tp1_distance=0.0,
                )
                trade_log = _trade_log(
                    trade.signal,
                    early_pnl,
                    early_decision,
                    exit_time=job.scan_unix,
                    exit_kind="reverse",
                )
                accumulator.trade_logs.append(trade_log)
                accumulator.record_trade(early_pnl)
                closed_trades.append(
                    {
                        "symbol": trade.signal.symbol,
                        "side": trade.signal.side,
                        "entry_time": _iso_time(trade.signal.time),
                        "exit_time": trade_log.exit_time,
                        "exit_kind": "reverse",
                        "pnl": round(early_pnl, 2),
                        "sort_time": job.scan_unix,
                    }
                )

            if job.signal.market_key in portfolio.open_market_keys():
                decision = TradeDecision(
                    allowed=False,
                    code="pyramiding",
                    reason="Box Theory pyramiding=0: same-side position still open",
                    risk_usd=0.0,
                    spread=0.0,
                    spread_atr=0.0,
                    tp1_distance=0.0,
                    min_tp1_distance=0.0,
                )
                accumulator.skipped += 1
                accumulator.skipped_logs.append(_skip_log(job.signal, decision))
                if include_events:
                    events.append(_event_payload(event_id, job.signal, decision, event_type="skip"))
                continue

        position_keys = portfolio.open_market_keys() if filters.existing_position and not box_mode else None
        setup_count = portfolio.active_setup_count() if filters.max_setups else None
        decision = evaluate_trade_signal(
            client,
            config,
            job.signal,
            job.symbol_cfg,
            spread=historical_spread_price(job.df.iloc[job.row_index], job.point),
            seen=False,
            filters=filters,
            market_position_keys=position_keys,
            active_setup_count=setup_count,
        )
        if not decision.allowed:
            if skip_should_mark_seen(decision.code):
                portfolio.mark_seen(job.signal.setup_id)
            accumulator.skipped += 1
            accumulator.skipped_logs.append(_skip_log(job.signal, decision))
            if include_events:
                events.append(_event_payload(event_id, job.signal, decision, event_type="skip"))
            continue

        after = job.df.iloc[job.row_index + 1 :]
        if partial_execution:
            simulation = simulate_partial_trade(client, job.signal, after.itertuples(), tp_protection)
        elif single_leg:
            simulation = simulate_single_trade(client, job.signal, after.itertuples())
        else:
            simulation = simulate_split_trade(client, job.signal, after.itertuples(), tp_protection)
        trade_pnl = float(simulation["pnl"])
        exit_unix = int(simulation.get("exit_time") or job.entry_unix)
        portfolio.mark_seen(job.signal.setup_id)
        portfolio.register_open(job.signal.setup_id, job.signal.market_key, exit_unix)
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
    starting_balance: float,
    filters,
    *,
    start_unix: int,
    end_unix: int,
    include_events: bool = False,
    logger: logging.Logger | None = None,
) -> tuple[SymbolBacktest, list[dict], list[dict]]:
    strategy = config.bot.strategy
    jobs, raw_signals = _collect_signal_jobs(
        client,
        config,
        symbol_cfg,
        df,
        filters,
        start_unix=start_unix,
        end_unix=end_unix,
        logger=logger,
    )
    accumulator = _SymbolAccumulator(symbol_cfg=symbol_cfg, raw_signals=raw_signals)
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
    starting_balance: float = 1000.0,
    logger: logging.Logger | None = None,
) -> dict:
    strategy = config.bot.strategy
    filters = resolve_trade_filters(config)
    client.initialize()
    start_utc = start if start.tzinfo is not None else start.replace(tzinfo=timezone.utc)
    end_utc = end if end.tzinfo is not None else end.replace(tzinfo=timezone.utc)
    start_unix = int(start_utc.timestamp())
    end_unix = int(end_utc.timestamp())
    accumulators: dict[str, _SymbolAccumulator] = {}
    all_jobs: list[_SignalJob] = []
    symbols = config.enabled_symbols

    t0 = time.perf_counter()
    for index, symbol_cfg in enumerate(symbols, start=1):
        symbol_t0 = time.perf_counter()
        if logger:
            logger.info(
                "BACKTEST %s/%s %s %s",
                index,
                len(symbols),
                symbol_cfg.symbol,
                symbol_cfg.timeframe,
            )
        try:
            fetch_start = extended_history_start(start_utc, symbol_cfg.timeframe)
            df = client.rates_range(symbol_cfg.symbol, symbol_cfg.timeframe, fetch_start, end_utc)
        except Exception as exc:  # noqa: BLE001
            accumulators[symbol_cfg.symbol] = _SymbolAccumulator(
                symbol_cfg=symbol_cfg,
                raw_signals=0,
                error=str(exc),
            )
            continue

        jobs, raw_signals = _collect_signal_jobs(
            client,
            config,
            symbol_cfg,
            df,
            filters,
            start_unix=start_unix,
            end_unix=end_unix,
            logger=logger,
        )
        accumulators[symbol_cfg.symbol] = _SymbolAccumulator(symbol_cfg=symbol_cfg, raw_signals=raw_signals)
        all_jobs.extend(jobs)
        if logger:
            logger.info(
                "BACKTEST %s done bars=%s raw=%s jobs=%s %.1fs",
                symbol_cfg.symbol,
                len(df),
                raw_signals,
                len(jobs),
                time.perf_counter() - symbol_t0,
            )

    exec_t0 = time.perf_counter()

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
    if logger:
        logger.info(
            "BACKTEST FINISHED symbols=%s jobs=%s trades=%s total_pnl=%s collect=%.1fs exec=%.1fs total=%.1fs",
            len(symbols),
            len(all_jobs),
            sum(row.trades for row in rows),
            total_pnl,
            exec_t0 - t0,
            time.perf_counter() - exec_t0,
            time.perf_counter() - t0,
        )

    return {
        "strategy": strategy,
        "decision_rules": _decision_rules_payload(config, filters, strategy=strategy),
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
) -> dict:
    strategy = config.bot.strategy
    filters = resolve_trade_filters(config)
    client.initialize()

    symbol_cfg = next((item for item in config.symbols if item.symbol == symbol), None)
    if symbol_cfg is None:
        raise ValueError(f"Unknown symbol: {symbol}")

    if timeframe not in {"M1", "M5", "M15", "M30", "H1"}:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    start_utc = start if start.tzinfo is not None else start.replace(tzinfo=timezone.utc)
    end_utc = end if end.tzinfo is not None else end.replace(tzinfo=timezone.utc)
    start_unix = int(start_utc.timestamp())
    end_unix = int(end_utc.timestamp())
    effective_symbol_cfg = symbol_cfg.model_copy(update={"timeframe": timeframe})
    fetch_start = extended_history_start(start_utc, timeframe)
    df = client.rates_range(symbol, timeframe, fetch_start, end_utc)
    symbol_result, _closed_trades, events = _run_symbol_backtest(
        client,
        config,
        effective_symbol_cfg,
        df,
        1000.0,
        filters,
        start_unix=start_unix,
        end_unix=end_unix,
        include_events=True,
    )

    return {
        "symbol": symbol,
        "name": symbol_cfg.name,
        "timeframe": timeframe,
        "configured_timeframe": symbol_cfg.timeframe,
        "settings_timeframe_match": timeframe == symbol_cfg.timeframe,
        "strategy": strategy,
        "decision_rules": _decision_rules_payload(config, filters, strategy=strategy),
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
