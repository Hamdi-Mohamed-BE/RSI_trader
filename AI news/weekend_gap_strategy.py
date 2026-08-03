from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from math import inf
from typing import Iterable, Sequence


@dataclass(frozen=True)
class StrategyConfig:
    offset_usd: float = 1.5
    placement_lead_minutes: int = 5
    stop_usd: float = 20.0
    reward_risk: float = 4.0
    max_hold_market_minutes: int = 720


@dataclass(frozen=True)
class WeekendWindow:
    close_index: int
    reopen_index: int


@dataclass
class Trade:
    weekend_open: str
    side: str
    source: str
    reference_time: str
    entry_time: str
    exit_time: str
    pending_price: float
    fill_price: float
    stop_loss: float
    take_profit: float
    exit_price: float
    result_r: float
    outcome: str
    spread_usd_at_entry: float


@dataclass
class BacktestResult:
    config: StrategyConfig
    total_weekends: int
    expired: int
    trades: list[Trade]
    metrics: dict

    def to_dict(self) -> dict:
        return {
            "config": asdict(self.config),
            "total_weekends": self.total_weekends,
            "expired": self.expired,
            "metrics": self.metrics,
            "trades": [asdict(trade) for trade in self.trades],
        }


def utc_time(row: dict) -> datetime:
    return datetime.fromtimestamp(int(row["time"]), timezone.utc)


def find_weekend_windows(rows: Sequence[dict]) -> list[WeekendWindow]:
    windows: list[WeekendWindow] = []
    for index in range(1, len(rows)):
        before = utc_time(rows[index - 1])
        after = utc_time(rows[index])
        if after - before < timedelta(hours=24):
            continue
        if before.weekday() not in (4, 5) or after.weekday() not in (6, 0):
            continue
        windows.append(WeekendWindow(index - 1, index))
    return windows


def _spread_usd(row: dict, point: float) -> float:
    return max(0.0, float(row.get("spread", 0))) * point


def _ask(row: dict, field: str, point: float) -> float:
    return float(row[field]) + _spread_usd(row, point)


def _first_trigger(
    rows: Sequence[dict],
    start: int,
    end: int,
    buy_stop: float,
    sell_stop: float,
    point: float,
) -> tuple[str, int, float, str] | None:
    for index in range(start, end + 1):
        row = rows[index]
        buy_hit = _ask(row, "high", point) >= buy_stop
        sell_hit = float(row["low"]) <= sell_stop
        if not buy_hit and not sell_hit:
            continue
        if buy_hit and sell_hit:
            # M1 cannot reveal the intrabar path. Resolve later using the worse
            # completed trade so the backtest does not benefit from hindsight.
            return "both", index, 0.0, "friday"
        if buy_hit:
            fill = max(buy_stop, _ask(row, "open", point))
            return "buy", index, fill, "friday"
        fill = min(sell_stop, float(row["open"]))
        return "sell", index, fill, "friday"
    return None


def _simulate_exit(
    rows: Sequence[dict],
    entry_index: int,
    side: str,
    fill_price: float,
    pending_price: float,
    config: StrategyConfig,
    point: float,
) -> tuple[float, int, str, float, float, float]:
    if side == "buy":
        stop = pending_price - config.stop_usd
        target = pending_price + config.stop_usd * config.reward_risk
    else:
        stop = pending_price + config.stop_usd
        target = pending_price - config.stop_usd * config.reward_risk

    final_index = min(len(rows) - 1, entry_index + config.max_hold_market_minutes - 1)
    for index in range(entry_index, final_index + 1):
        row = rows[index]
        if side == "buy":
            open_exit = float(row["open"])
            if index == entry_index and open_exit >= target:
                exit_price, outcome = open_exit, "TP_GAP"
            elif index == entry_index and open_exit <= stop:
                exit_price, outcome = open_exit, "SL_GAP"
            elif float(row["low"]) <= stop:
                exit_price, outcome = stop, "SL"
            elif index > entry_index and float(row["high"]) >= target:
                exit_price, outcome = target, "TP"
            else:
                continue
            result_r = (exit_price - fill_price) / config.stop_usd
        else:
            ask_open = _ask(row, "open", point)
            ask_low = _ask(row, "low", point)
            ask_high = _ask(row, "high", point)
            if index == entry_index and ask_open <= target:
                exit_price, outcome = ask_open, "TP_GAP"
            elif index == entry_index and ask_open >= stop:
                exit_price, outcome = ask_open, "SL_GAP"
            elif ask_high >= stop:
                exit_price, outcome = stop, "SL"
            elif index > entry_index and ask_low <= target:
                exit_price, outcome = target, "TP"
            else:
                continue
            result_r = (fill_price - exit_price) / config.stop_usd
        return result_r, index, outcome, stop, target, exit_price

    row = rows[final_index]
    exit_price = float(row["close"]) if side == "buy" else _ask(row, "close", point)
    result_r = (
        (exit_price - fill_price) / config.stop_usd
        if side == "buy"
        else (fill_price - exit_price) / config.stop_usd
    )
    return result_r, final_index, "TIME", stop, target, exit_price


def _build_trade(
    rows: Sequence[dict],
    window: WeekendWindow,
    reference_index: int,
    entry_index: int,
    side: str,
    source: str,
    fill_price: float,
    pending_price: float,
    config: StrategyConfig,
    point: float,
) -> Trade:
    result_r, exit_index, outcome, stop, target, exit_price = _simulate_exit(
        rows, entry_index, side, fill_price, pending_price, config, point
    )
    return Trade(
        weekend_open=utc_time(rows[window.reopen_index]).isoformat(),
        side=side.upper(),
        source=source,
        reference_time=utc_time(rows[reference_index]).isoformat(),
        entry_time=utc_time(rows[entry_index]).isoformat(),
        exit_time=utc_time(rows[exit_index]).isoformat(),
        pending_price=round(pending_price, 6),
        fill_price=round(fill_price, 6),
        stop_loss=round(stop, 6),
        take_profit=round(target, 6),
        exit_price=round(exit_price, 6),
        result_r=round(result_r, 6),
        outcome=outcome,
        spread_usd_at_entry=round(_spread_usd(rows[entry_index], point), 6),
    )


def calculate_metrics(trades: Iterable[Trade]) -> dict:
    items = list(trades)
    values = [trade.result_r for trade in items]
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = max(max_drawdown, peak - equity)
    return {
        "trades": len(items),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100 * len(wins) / len(items), 2) if items else 0.0,
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else (inf if gross_profit else 0.0),
        "net_r": round(sum(values), 4),
        "gross_profit_r": round(gross_profit, 4),
        "gross_loss_r": round(gross_loss, 4),
        "max_drawdown_r": round(max_drawdown, 4),
        "average_r": round(sum(values) / len(items), 4) if items else 0.0,
        "friday_fills": sum(trade.source == "friday" for trade in items),
        "reopen_fills": sum(trade.source == "reopen" for trade in items),
    }


def backtest(
    rows: Sequence[dict],
    point: float,
    config: StrategyConfig,
    *,
    windows: Sequence[WeekendWindow] | None = None,
) -> BacktestResult:
    chosen_windows = list(windows) if windows is not None else find_weekend_windows(rows)
    trades: list[Trade] = []
    expired = 0
    for window in chosen_windows:
        reference_index = window.close_index - config.placement_lead_minutes
        if reference_index < 0:
            expired += 1
            continue
        reference = rows[reference_index]
        buy_stop = float(reference["high"]) + config.offset_usd
        sell_stop = float(reference["low"]) - config.offset_usd
        trigger = _first_trigger(
            rows,
            reference_index + 1,
            window.close_index,
            buy_stop,
            sell_stop,
            point,
        )
        if trigger is None:
            reopen = rows[window.reopen_index]
            ask_open = _ask(reopen, "open", point)
            bid_open = float(reopen["open"])
            buy_hit = ask_open >= buy_stop
            sell_hit = bid_open <= sell_stop
            if not buy_hit and not sell_hit:
                expired += 1
                continue
            if buy_hit and sell_hit:
                trigger = ("both", window.reopen_index, 0.0, "reopen")
            elif buy_hit:
                trigger = ("buy", window.reopen_index, ask_open, "reopen")
            else:
                trigger = ("sell", window.reopen_index, bid_open, "reopen")

        side, entry_index, fill, source = trigger
        if side == "both":
            buy_fill = max(buy_stop, _ask(rows[entry_index], "open", point))
            sell_fill = min(sell_stop, float(rows[entry_index]["open"]))
            candidates = [
                _build_trade(rows, window, reference_index, entry_index, "buy", source, buy_fill, buy_stop, config, point),
                _build_trade(rows, window, reference_index, entry_index, "sell", source, sell_fill, sell_stop, config, point),
            ]
            trades.append(min(candidates, key=lambda item: item.result_r))
            continue
        pending_price = buy_stop if side == "buy" else sell_stop
        trades.append(
            _build_trade(
                rows,
                window,
                reference_index,
                entry_index,
                side,
                source,
                fill,
                pending_price,
                config,
                point,
            )
        )
    return BacktestResult(config, len(chosen_windows), expired, trades, calculate_metrics(trades))


def metrics_for_period(trades: Sequence[Trade], start: datetime, end: datetime) -> dict:
    selected = [
        trade
        for trade in trades
        if start <= datetime.fromisoformat(trade.weekend_open) < end
    ]
    return calculate_metrics(selected)
