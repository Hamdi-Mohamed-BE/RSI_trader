from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from itertools import product
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from ..schemas import RuntimeConfig
from .indicators import resample_ohlcv
from .profile import VolumeProfile, build_bar_profile
from .strategy import LtaOrderFlowEngine, SignalDecision


NY = ZoneInfo("America/New_York")
SESSION_HOURS = {
    "ASIA": (19, 2),
    "LONDON": (3, 11),
    "NEW_YORK": (8, 17),
}


@dataclass
class PendingEntry:
    decision: SignalDecision
    created_index: int


@dataclass
class OpenPosition:
    side: str
    entry: float
    stop: float
    target: float
    initial_stop: float
    risk_distance: float
    risk_amount: float
    score: float
    opened_at: pd.Timestamp
    highest_r: float = 0.0


def in_enabled_session(timestamp: pd.Timestamp, config: RuntimeConfig, symbol: str) -> bool:
    local = timestamp.tz_convert(NY) if timestamp.tzinfo else timestamp.tz_localize("UTC").tz_convert(NY)
    if local.weekday() not in config.weekdays:
        return False
    hour = local.hour + local.minute / 60
    sessions = config.symbols[symbol].sessions or config.sessions
    for session in sessions:
        start, end = SESSION_HOURS[session]
        if start < end and start <= hour < end:
            return True
        if start > end and (hour >= start or hour < end):
            return True
    return False


class Backtester:
    def __init__(self, config: RuntimeConfig):
        self.config = config

    def run_symbol(
        self,
        symbol: str,
        minute_bars: pd.DataFrame,
        starting_balance: float = 300.0,
        test_start: datetime | None = None,
    ) -> dict:
        bars = resample_ohlcv(minute_bars, self.config.signal_timeframe_minutes)
        engine = LtaOrderFlowEngine(self.config)
        bars = engine.prepare(bars)
        if test_start is not None:
            start_timestamp = pd.Timestamp(test_start)
            if start_timestamp.tzinfo is None:
                start_timestamp = start_timestamp.tz_localize("UTC")
            warmup = int(bars.index.searchsorted(start_timestamp))
        else:
            warmup = max(100, min(len(bars) // 3, self.config.profile_lookback_days * 24 * 4))
        if len(bars) <= warmup + 5:
            raise ValueError(f"Not enough history to backtest {symbol}.")

        balance = float(starting_balance)
        peak = balance
        maximum_drawdown = 0.0
        pending: PendingEntry | None = None
        position: OpenPosition | None = None
        trades: list[dict] = []
        equity: list[dict] = [{"time": bars.index[warmup].isoformat(), "balance": balance}]
        trades_by_day: dict[str, int] = defaultdict(int)
        symbol_config = self.config.symbols[symbol]
        profiles: dict[str, VolumeProfile] = {}

        for index in range(warmup, len(bars)):
            timestamp = bars.index[index]
            candle = bars.iloc[index]
            day_key = timestamp.tz_convert(NY).strftime("%Y-%m-%d")

            if position is None and pending is not None:
                if index - pending.created_index > self.config.pending_expiry_bars:
                    pending = None
                else:
                    fill, cancel = self._pending_outcome(pending.decision, candle)
                    if cancel:
                        pending = None
                    elif fill is not None:
                        position = self._open_position(
                            pending.decision,
                            fill,
                            balance,
                            timestamp,
                            symbol_config.spread_bps,
                            symbol_config.slippage_bps,
                        )
                        trades_by_day[day_key] += 1
                        pending = None

            if position is not None:
                exit_result = self._manage_position(position, candle)
                if exit_result is not None:
                    exit_price, reason, multiple = exit_result
                    pnl = position.risk_amount * multiple
                    balance += pnl
                    trades.append(
                        {
                            "opened_at": position.opened_at.isoformat(),
                            "closed_at": timestamp.isoformat(),
                            "side": position.side,
                            "entry": round(position.entry, 8),
                            "exit": round(exit_price, 8),
                            "stop": round(position.initial_stop, 8),
                            "target": round(position.target, 8),
                            "score": position.score,
                            "r_multiple": round(multiple, 4),
                            "pnl": round(pnl, 2),
                            "balance": round(balance, 2),
                            "exit_reason": reason,
                        }
                    )
                    position = None
                    peak = max(peak, balance)
                    maximum_drawdown = max(maximum_drawdown, (peak - balance) / peak if peak else 0.0)
                    equity.append({"time": timestamp.isoformat(), "balance": round(balance, 2)})

            can_scan = (
                position is None
                and pending is None
                and trades_by_day[day_key] < self.config.max_trades_per_day
                and in_enabled_session(timestamp, self.config, symbol)
            )
            if can_scan:
                window = bars.iloc[: index + 1]
                if day_key not in profiles:
                    completed = minute_bars.loc[minute_bars.index < timestamp].tail(
                        self.config.profile_lookback_days * 24 * 60
                    )
                    profiles[day_key] = build_bar_profile(
                        completed, self.config.profile_bins, self.config.value_area_percent
                    )
                try:
                    decision = engine.evaluate(
                        symbol, window, profile_override=profiles[day_key]
                    )
                except ValueError:
                    continue
                if decision.status == "A_PLUS":
                    if decision.order_type == "MARKET":
                        position = self._open_position(
                            decision,
                            float(candle["close"]),
                            balance,
                            timestamp,
                            symbol_config.spread_bps,
                            symbol_config.slippage_bps,
                        )
                        trades_by_day[day_key] += 1
                    else:
                        pending = PendingEntry(decision=decision, created_index=index)

        if position is not None:
            candle = bars.iloc[-1]
            multiple = self._mark_to_market_multiple(position, float(candle["close"]))
            pnl = position.risk_amount * multiple
            balance += pnl
            trades.append(
                {
                    "opened_at": position.opened_at.isoformat(),
                    "closed_at": bars.index[-1].isoformat(),
                    "side": position.side,
                    "entry": round(position.entry, 8),
                    "exit": round(float(candle["close"]), 8),
                    "stop": round(position.initial_stop, 8),
                    "target": round(position.target, 8),
                    "score": position.score,
                    "r_multiple": round(multiple, 4),
                    "pnl": round(pnl, 2),
                    "balance": round(balance, 2),
                    "exit_reason": "END_OF_TEST",
                }
            )
            equity.append({"time": bars.index[-1].isoformat(), "balance": round(balance, 2)})

        metrics = calculate_metrics(trades, starting_balance, balance, maximum_drawdown)
        return {
            "symbol": symbol,
            "metrics": metrics,
            "monthly": monthly_breakdown(trades, starting_balance),
            "trades": trades,
            "equity": equity,
            "data_quality": {
                "profile_source": "ohlcv-1m",
                "order_book_used": False,
                "costs_included": True,
                "note": "Backtest uses CME one-minute traded volume; live scans can add trades and MBP-10.",
            },
        }

    def _open_position(
        self,
        decision: SignalDecision,
        nominal_fill: float,
        balance: float,
        timestamp: pd.Timestamp,
        spread_bps: float,
        slippage_bps: float,
    ) -> OpenPosition:
        direction = 1 if decision.direction == "BUY" else -1
        cost_rate = (spread_bps / 2 + slippage_bps) / 10_000
        fill = nominal_fill * (1 + direction * cost_rate)
        initial_stop = float(decision.stop_loss)
        nominal_risk = abs(float(decision.entry) - initial_stop)
        risk_distance = max(abs(fill - initial_stop), nominal_risk * 0.25)
        return OpenPosition(
            side=decision.direction,
            entry=fill,
            stop=initial_stop,
            target=float(decision.take_profit),
            initial_stop=initial_stop,
            risk_distance=risk_distance,
            risk_amount=balance * self.config.risk_percent / 100,
            score=decision.score,
            opened_at=timestamp,
        )

    def _manage_position(
        self, position: OpenPosition, candle: pd.Series
    ) -> tuple[float, str, float] | None:
        high, low = float(candle["high"]), float(candle["low"])
        if position.side == "BUY":
            if low <= position.stop:
                return position.stop, "STOP", (position.stop - position.entry) / position.risk_distance
            if high >= position.target:
                return position.target, "TARGET", (position.target - position.entry) / position.risk_distance
            favorable_r = (high - position.entry) / position.risk_distance
        else:
            if high >= position.stop:
                return position.stop, "STOP", (position.entry - position.stop) / position.risk_distance
            if low <= position.target:
                return position.target, "TARGET", (position.entry - position.target) / position.risk_distance
            favorable_r = (position.entry - low) / position.risk_distance

        position.highest_r = max(position.highest_r, favorable_r)
        if self.config.trail_enabled and favorable_r >= self.config.trail_step_r:
            completed_steps = int(favorable_r // self.config.trail_step_r)
            locked_r = max(0.0, (completed_steps - 1) * self.config.trail_step_r)
            if position.side == "BUY":
                position.stop = max(position.stop, position.entry + locked_r * position.risk_distance)
            else:
                position.stop = min(position.stop, position.entry - locked_r * position.risk_distance)
        return None

    @staticmethod
    def _pending_outcome(
        decision: SignalDecision, candle: pd.Series
    ) -> tuple[float | None, bool]:
        entry = float(decision.entry)
        if float(candle["low"]) <= entry <= float(candle["high"]):
            return entry, False
        if decision.direction == "BUY" and float(candle["low"]) <= float(decision.stop_loss):
            return None, True
        if decision.direction == "SELL" and float(candle["high"]) >= float(decision.stop_loss):
            return None, True
        return None, False

    @staticmethod
    def _mark_to_market_multiple(position: OpenPosition, price: float) -> float:
        if position.side == "BUY":
            return (price - position.entry) / position.risk_distance
        return (position.entry - price) / position.risk_distance


def calculate_metrics(
    trades: list[dict], starting_balance: float, ending_balance: float, max_drawdown: float
) -> dict:
    wins = [trade for trade in trades if trade["pnl"] > 0]
    losses = [trade for trade in trades if trade["pnl"] < 0]
    gross_profit = sum(trade["pnl"] for trade in wins)
    gross_loss = abs(sum(trade["pnl"] for trade in losses))
    return {
        "starting_balance": round(starting_balance, 2),
        "ending_balance": round(ending_balance, 2),
        "net_profit": round(ending_balance - starting_balance, 2),
        "return_percent": round((ending_balance / starting_balance - 1) * 100, 2),
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 2) if trades else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else None,
        "max_drawdown_percent": round(max_drawdown * 100, 2),
        "average_r": round(float(np.mean([t["r_multiple"] for t in trades])), 3) if trades else 0.0,
    }


def monthly_breakdown(trades: list[dict], starting_balance: float) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for trade in trades:
        grouped[trade["closed_at"][:7]].append(trade)
    rows: list[dict] = []
    running_balance = starting_balance
    for month, month_trades in sorted(grouped.items()):
        opening = running_balance
        pnl = sum(trade["pnl"] for trade in month_trades)
        running_balance += pnl
        wins = sum(1 for trade in month_trades if trade["pnl"] > 0)
        rows.append(
            {
                "month": month,
                "opening_balance": round(opening, 2),
                "closing_balance": round(running_balance, 2),
                "pnl": round(pnl, 2),
                "return_percent": round(pnl / opening * 100, 2) if opening else 0.0,
                "trades": len(month_trades),
                "win_rate": round(wins / len(month_trades) * 100, 2),
            }
        )
    return rows


def optimize_symbol(
    symbol: str,
    bars: pd.DataFrame,
    base_config: RuntimeConfig,
    starting_balance: float,
    test_start: datetime | None = None,
) -> tuple[RuntimeConfig, dict]:
    candidates = product(
        (60.0, 66.0, 72.0, 76.0),
        (2.0, 2.5, 3.0, 4.0),
        (1.4, 1.9),
        (("NEW_YORK",), ("LONDON", "NEW_YORK")),
    )
    best_score = float("-inf")
    best_config = deepcopy(base_config)
    best_result: dict | None = None
    for minimum_score, reward_risk, atr_multiplier, sessions in candidates:
        config = deepcopy(base_config)
        config.symbols[symbol].minimum_score = minimum_score
        config.symbols[symbol].sessions = list(sessions)
        config.symbols[symbol].reward_risk = reward_risk
        config.symbols[symbol].atr_stop_multiplier = atr_multiplier
        result = Backtester(config).run_symbol(
            symbol, bars, starting_balance, test_start=test_start
        )
        metrics = result["metrics"]
        if metrics["trades"] < 3:
            continue
        score = optimization_score(metrics, config.optimize_objective)
        if score > best_score:
            best_score, best_config, best_result = score, config, result
    if best_result is None:
        return base_config, Backtester(base_config).run_symbol(
            symbol, bars, starting_balance, test_start=test_start
        )
    best_result["optimization_score"] = round(best_score, 3)
    return best_config, best_result


def optimization_score(metrics: dict, objective: str) -> float:
    growth = float(metrics["return_percent"])
    drawdown = float(metrics["max_drawdown_percent"])
    trade_bonus = min(float(metrics["trades"]), 30.0) * 0.1
    if objective == "growth":
        return growth - drawdown * 0.25 + trade_bonus
    if objective == "drawdown":
        return growth - drawdown * 1.5 + trade_bonus
    return growth - drawdown * 0.75 + trade_bonus
