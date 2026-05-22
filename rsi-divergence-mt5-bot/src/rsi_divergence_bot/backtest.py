from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

import pandas as pd

from .config import AppConfig
from .decision import TradeDecision, evaluate_trade_signal, resolve_trade_filters
from .mt5_client import MT5Client
from .strategy import Signal, generate_signals


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


def _trade_pnl(client: MT5Client, signal: Signal, rows, tp_protection: bool) -> float:
    return float(_simulate_trade(client, signal, rows, tp_protection)["pnl"])


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
    for trade in ordered:
        day = pd.Timestamp(trade["sort_time"], unit="s", tz="UTC").strftime("%Y-%m-%d")
        bucket = by_day.setdefault(day, {"pnl": 0.0, "trades": 0, "wins": 0, "losses": 0})
        bucket["pnl"] += float(trade["pnl"])
        bucket["trades"] += 1
        if trade["pnl"] > 0:
            bucket["wins"] += 1
        elif trade["pnl"] < 0:
            bucket["losses"] += 1

    balance = float(starting_balance)
    rows: list[dict] = []
    for day in sorted(by_day.keys()):
        bucket = by_day[day]
        balance += bucket["pnl"]
        rows.append(
            {
                "date": day,
                "trades": bucket["trades"],
                "wins": bucket["wins"],
                "losses": bucket["losses"],
                "pnl": round(bucket["pnl"], 2),
                "balance": round(balance, 2),
            }
        )
    return rows


def _symbol_payload(item: SymbolBacktest) -> dict:
    payload = asdict(item)
    payload["trade_logs"] = [asdict(trade) for trade in (item.trade_logs or [])]
    payload["skipped_logs"] = [asdict(skip) for skip in (item.skipped_logs or [])]
    return payload


def _decision_rules_payload(config: AppConfig, filters) -> dict:
    return {
        "profile": config.bot.trade_decision_profile,
        "execution_filters_applied": filters.spread or filters.tp1_spread or filters.risk,
        "account_filters_applied": filters.existing_position or filters.max_setups,
        "filters": asdict(filters),
        "max_spread_atr": config.risk.max_spread_atr,
        "max_setup_risk_usd": config.risk.max_setup_risk_usd,
        "min_tp1_spread_multiple": config.risk.min_tp1_spread_multiple,
        "max_extension_atr": config.risk.max_extension_atr,
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
    tp_protection = strategy == "signal_with_tp_protection"
    signals = generate_signals(df, symbol_cfg, config.risk)
    point = 0.0
    try:
        info = client.symbol_info(symbol_cfg.symbol)
        point = float(getattr(info, "point", 0.0) or 0.0)
    except Exception as exc:  # noqa: BLE001
        if logger:
            logger.warning("BACKTEST %s could not read symbol point: %s", symbol_cfg.symbol, exc)

    balance = starting_balance
    peak = balance
    max_dd = 0.0
    wins = losses = skipped = 0
    trade_logs: list[BacktestTrade] = []
    skipped_logs: list[BacktestSkip] = []
    closed_trades: list[dict] = []
    events: list[dict] = []

    for event_id, signal in enumerate(signals, start=1):
        signal_index = df.index[df["time"] == signal.time]
        if len(signal_index) == 0:
            continue
        row_index = int(signal_index[0])
        decision = evaluate_trade_signal(
            client,
            config,
            signal,
            symbol_cfg,
            spread=_historical_spread_price(df.iloc[row_index], point),
            filters=filters,
        )
        if not decision.allowed:
            skipped += 1
            skipped_logs.append(_skip_log(signal, decision))
            if include_events:
                events.append(_event_payload(event_id, signal, decision, event_type="skip"))
            continue

        after = df.iloc[row_index + 1 :]
        simulation = _simulate_trade(client, signal, after.itertuples(), tp_protection)
        trade_pnl = float(simulation["pnl"])
        trade_logs.append(
            _trade_log(
                signal,
                trade_pnl,
                decision,
                exit_time=simulation.get("exit_time"),
                exit_kind=simulation.get("exit_kind"),
            )
        )
        if include_events:
            events.append(
                _event_payload(
                    event_id,
                    signal,
                    decision,
                    event_type="trade",
                    pnl=trade_pnl,
                    exit_time=simulation.get("exit_time"),
                    exit_kind=simulation.get("exit_kind"),
                )
            )
        sort_time = simulation.get("exit_time") or _bar_unix(signal.time)
        closed_trades.append(
            {
                "symbol": symbol_cfg.symbol,
                "pnl": round(trade_pnl, 2),
                "sort_time": int(sort_time),
            }
        )
        balance += trade_pnl
        peak = max(peak, balance)
        max_dd = max(max_dd, peak - balance)
        if trade_pnl > 0:
            wins += 1
        elif trade_pnl < 0:
            losses += 1

    trades = wins + losses
    return (
        SymbolBacktest(
            symbol=symbol_cfg.symbol,
            market_key=symbol_cfg.key,
            name=symbol_cfg.name,
            timeframe=symbol_cfg.timeframe,
            raw_signals=len(signals),
            skipped_signals=skipped,
            trades=trades,
            wins=wins,
            losses=losses,
            win_rate=round((wins / trades * 100) if trades else 0.0, 2),
            pnl=round(balance - starting_balance, 2),
            max_drawdown=round(max_dd, 2),
            trade_logs=trade_logs,
            skipped_logs=skipped_logs,
        ),
        closed_trades,
        events,
    )


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
    rows: list[SymbolBacktest] = []
    closed_trades: list[dict] = []
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
            rows.append(
                SymbolBacktest(
                    symbol=symbol_cfg.symbol,
                    market_key=symbol_cfg.key,
                    name=symbol_cfg.name,
                    timeframe=symbol_cfg.timeframe,
                    raw_signals=0,
                    skipped_signals=0,
                    trades=0,
                    wins=0,
                    losses=0,
                    win_rate=0.0,
                    pnl=0.0,
                    max_drawdown=0.0,
                    error=str(exc),
                    trade_logs=[],
                    skipped_logs=[],
                )
            )
            continue

        symbol_result, symbol_closed_trades, _events = _run_symbol_backtest(
            client,
            config,
            symbol_cfg,
            df,
            strategy,
            starting_balance,
            filters,
            logger=logger,
        )
        rows.append(symbol_result)
        closed_trades.extend(symbol_closed_trades)
    total_pnl = round(sum(item.pnl for item in rows), 2)
    daily_performance = _build_daily_performance(closed_trades, starting_balance)

    return {
        "strategy": strategy,
        "decision_rules": _decision_rules_payload(config, filters),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "starting_balance": round(starting_balance, 2),
        "total_pnl": total_pnl,
        "end_balance_if_sequential": round(starting_balance + total_pnl, 2),
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
