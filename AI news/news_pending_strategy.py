from __future__ import annotations

import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "news-event-days"
CALENDAR_PATH = ROOT / "news_15y_calendar.csv"
PREDICTION_PATH = ROOT / "gold_direction_v2.csv"


@dataclass(frozen=True)
class Instrument:
    symbol: str
    pip_size: float
    breakout_sl_pips: float = 90.0
    reentry_sl_pips: float = 50.0
    reentry_rr: float = 5.0


@dataclass(frozen=True)
class StrategyConfig:
    mode: str
    reward_risk: float
    spread_buffer_multiplier: float
    min_buffer_pips: float = 2.0
    pending_minutes: int = 15
    max_hold_minutes: int = 180
    allow_reentry: bool = True
    buy_reentry_fib: float = 0.60
    sell_reentry_fib: float = 0.50


@dataclass
class Trade:
    symbol: str
    event: str
    release_utc: str
    leg: str
    side: str
    order_type: str
    entry_time: str
    exit_time: str
    intended_entry: float
    fill_price: float
    stop_loss: float
    take_profit: float
    exit_price: float
    result_r: float
    outcome: str
    spread_at_fill_pips: float
    same_bar_ambiguous: bool = False

    def to_dict(self) -> dict:
        return asdict(self)


def normalize_rows(raw: object) -> list[dict[str, float]]:
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, float]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        stamp = item.get("timestamp") or item.get("time")
        if stamp is None:
            continue
        value = float(stamp)
        if value < 10_000_000_000:
            value *= 1000
        try:
            rows.append(
                {
                    "timestamp": int(round(value / 60_000) * 60_000),
                    "open": float(item["open"]),
                    "high": float(item["high"]),
                    "low": float(item["low"]),
                    "close": float(item["close"]),
                    "volume": float(item.get("volume") or 0.0),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    return rows


def load_day(symbol: str, day: str, side: str) -> dict[int, dict[str, float]]:
    path = DATA_DIR / f"{symbol.lower()}-m1-{side}-{day}.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {int(row["timestamp"]): row for row in normalize_rows(raw)}


def load_events(start: datetime, end: datetime) -> list[dict]:
    rows = []
    with CALENDAR_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            released = datetime.fromisoformat(row["release_utc"]).astimezone(timezone.utc)
            if start <= released < end:
                rows.append({**row, "released": released})
    return sorted(rows, key=lambda row: row["released"])


def load_predictions() -> dict[str, str]:
    predictions: dict[str, str] = {}
    with PREDICTION_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            direction = row.get("predicted_gold_impact", "").upper()
            if direction in {"POSITIVE", "NEGATIVE"}:
                predictions[row["release_utc"]] = "buy" if direction == "POSITIVE" else "sell"
    return predictions


def _bar(data: dict[int, dict[str, float]], stamp: int) -> dict[str, float] | None:
    return data.get(stamp)


def _spread_pips(
    bid: dict[str, float],
    ask: dict[str, float],
    instrument: Instrument,
) -> float:
    return max(0.0, (ask["close"] - bid["close"]) / instrument.pip_size)


def _exit_trade(
    *,
    instrument: Instrument,
    event: dict,
    leg: str,
    side: str,
    order_type: str,
    intended_entry: float,
    fill_price: float,
    entry_stamp: int,
    stop_loss: float,
    take_profit: float,
    bid: dict[int, dict[str, float]],
    ask: dict[int, dict[str, float]],
    max_exit_stamp: int,
    spread_at_fill_pips: float,
) -> Trade:
    risk = abs(intended_entry - stop_loss)
    exit_price = fill_price
    exit_stamp = entry_stamp
    outcome = "TIME"
    same_bar_ambiguous = False

    stamps = [
        stamp
        for stamp in sorted(set(bid) & set(ask))
        if entry_stamp <= stamp <= max_exit_stamp
    ]
    for stamp in stamps:
        bid_bar = bid[stamp]
        ask_bar = ask[stamp]
        if side == "buy":
            stop_hit = bid_bar["low"] <= stop_loss
            target_hit = bid_bar["high"] >= take_profit
            if stamp == entry_stamp and target_hit:
                same_bar_ambiguous = True
                target_hit = False
            if stop_hit:
                exit_price = min(stop_loss, bid_bar["open"])
                outcome = "SL"
            elif target_hit:
                exit_price = max(take_profit, bid_bar["open"])
                outcome = "TP"
            else:
                continue
        else:
            stop_hit = ask_bar["high"] >= stop_loss
            target_hit = ask_bar["low"] <= take_profit
            if stamp == entry_stamp and target_hit:
                same_bar_ambiguous = True
                target_hit = False
            if stop_hit:
                exit_price = max(stop_loss, ask_bar["open"])
                outcome = "SL"
            elif target_hit:
                exit_price = min(take_profit, ask_bar["open"])
                outcome = "TP"
            else:
                continue
        exit_stamp = stamp
        break
    else:
        exit_stamp = stamps[-1] if stamps else entry_stamp
        if side == "buy" and exit_stamp in bid:
            exit_price = bid[exit_stamp]["close"]
        elif side == "sell" and exit_stamp in ask:
            exit_price = ask[exit_stamp]["close"]

    raw_pnl = exit_price - fill_price if side == "buy" else fill_price - exit_price
    result_r = raw_pnl / risk if risk > 0 else 0.0
    return Trade(
        symbol=instrument.symbol.upper(),
        event=event["event"],
        release_utc=event["released"].isoformat(),
        leg=leg,
        side=side,
        order_type=order_type,
        entry_time=datetime.fromtimestamp(entry_stamp / 1000, timezone.utc).isoformat(),
        exit_time=datetime.fromtimestamp(exit_stamp / 1000, timezone.utc).isoformat(),
        intended_entry=intended_entry,
        fill_price=fill_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        exit_price=exit_price,
        result_r=result_r,
        outcome=outcome,
        spread_at_fill_pips=spread_at_fill_pips,
        same_bar_ambiguous=same_bar_ambiguous,
    )


def _trigger_breakout(
    *,
    instrument: Instrument,
    event: dict,
    config: StrategyConfig,
    sides: tuple[str, ...],
    bid: dict[int, dict[str, float]],
    ask: dict[int, dict[str, float]],
    range_high: float,
    range_low: float,
) -> tuple[Trade | None, bool]:
    release_stamp = int(event["released"].timestamp() * 1000)
    placed_stamp = release_stamp - 30 * 60_000
    expiry_stamp = release_stamp + config.pending_minutes * 60_000
    stop_distance = instrument.breakout_sl_pips * instrument.pip_size

    prior_stamp = placed_stamp - 60_000
    prior_bid = _bar(bid, prior_stamp)
    prior_ask = _bar(ask, prior_stamp)
    if not prior_bid or not prior_ask:
        return None, False
    initial_spread = _spread_pips(prior_bid, prior_ask, instrument)
    buffer = max(
        config.min_buffer_pips,
        initial_spread * config.spread_buffer_multiplier,
    ) * instrument.pip_size
    sell_anchor = (
        range_low + config.sell_reentry_fib * (range_high - range_low)
        if config.mode == "forecast" and sides == ("sell",)
        else range_low
    )
    entries = {
        "buy": range_high + buffer,
        "sell": min(sell_anchor - buffer, prior_bid["close"] - buffer),
    }
    collision = False

    for stamp in range(placed_stamp, expiry_stamp + 1, 60_000):
        bid_bar = _bar(bid, stamp)
        ask_bar = _bar(ask, stamp)
        if not bid_bar or not ask_bar:
            continue
        triggered = []
        if "buy" in sides and ask_bar["high"] >= entries["buy"]:
            triggered.append("buy")
        if "sell" in sides and bid_bar["low"] <= entries["sell"]:
            triggered.append("sell")
        if len(triggered) == 2:
            collision = True
            buy_distance = max(0.0, entries["buy"] - ask_bar["open"])
            sell_distance = max(0.0, bid_bar["open"] - entries["sell"])
            triggered = ["buy" if buy_distance <= sell_distance else "sell"]
        if triggered:
            side = triggered[0]
            intended = entries[side]
            if side == "buy":
                fill = max(intended, ask_bar["open"])
                stop = intended - stop_distance
                target = intended + config.reward_risk * stop_distance
            else:
                fill = min(intended, bid_bar["open"])
                stop = intended + stop_distance
                target = intended - config.reward_risk * stop_distance
            trade = _exit_trade(
                instrument=instrument,
                event=event,
                leg="breakout",
                side=side,
                order_type=f"{side}_stop",
                intended_entry=intended,
                fill_price=fill,
                entry_stamp=stamp,
                stop_loss=stop,
                take_profit=target,
                bid=bid,
                ask=ask,
                max_exit_stamp=release_stamp + config.max_hold_minutes * 60_000,
                spread_at_fill_pips=_spread_pips(bid_bar, ask_bar, instrument),
            )
            return trade, collision

        if stamp < release_stamp:
            current_spread = _spread_pips(bid_bar, ask_bar, instrument)
            live_buffer = max(
                config.min_buffer_pips,
                current_spread * config.spread_buffer_multiplier,
            ) * instrument.pip_size
            entries["buy"] = max(entries["buy"], range_high + live_buffer)
            entries["sell"] = min(
                entries["sell"],
                sell_anchor - live_buffer,
                bid_bar["close"] - live_buffer,
            )
    return None, collision


def _trigger_reentry(
    *,
    instrument: Instrument,
    event: dict,
    config: StrategyConfig,
    breakout: Trade,
    bid: dict[int, dict[str, float]],
    ask: dict[int, dict[str, float]],
    range_high: float,
    range_low: float,
) -> Trade | None:
    if not config.allow_reentry or breakout.outcome != "SL":
        return None
    release_stamp = int(event["released"].timestamp() * 1000)
    expiry_stamp = release_stamp + config.pending_minutes * 60_000
    start_stamp = int(datetime.fromisoformat(breakout.exit_time).timestamp() * 1000) + 60_000
    if start_stamp > expiry_stamp:
        return None

    width = range_high - range_low
    if breakout.side == "buy":
        intended = range_low + config.buy_reentry_fib * width
    else:
        intended = range_low + config.sell_reentry_fib * width
    stop_distance = instrument.reentry_sl_pips * instrument.pip_size

    for stamp in range(start_stamp, expiry_stamp + 1, 60_000):
        bid_bar = _bar(bid, stamp)
        ask_bar = _bar(ask, stamp)
        if not bid_bar or not ask_bar:
            continue
        if breakout.side == "buy":
            triggered = ask_bar["low"] <= intended
            fill = min(intended, ask_bar["open"])
            stop = intended - stop_distance
            target = intended + instrument.reentry_rr * stop_distance
        else:
            triggered = bid_bar["high"] >= intended
            fill = max(intended, bid_bar["open"])
            stop = intended + stop_distance
            target = intended - instrument.reentry_rr * stop_distance
        if not triggered:
            continue
        return _exit_trade(
            instrument=instrument,
            event=event,
            leg="reentry",
            side=breakout.side,
            order_type=f"{breakout.side}_limit",
            intended_entry=intended,
            fill_price=fill,
            entry_stamp=stamp,
            stop_loss=stop,
            take_profit=target,
            bid=bid,
            ask=ask,
            max_exit_stamp=release_stamp + config.max_hold_minutes * 60_000,
            spread_at_fill_pips=_spread_pips(bid_bar, ask_bar, instrument),
        )
    return None


def simulate_event(
    instrument: Instrument,
    event: dict,
    config: StrategyConfig,
    forecast_side: str | None,
) -> dict:
    day = event["released"].date().isoformat()
    bid = load_day(instrument.symbol, day, "bid")
    ask = load_day(instrument.symbol, day, "ask")
    if not bid or not ask:
        return {"status": "missing_bid_ask", "trades": []}

    release_stamp = int(event["released"].timestamp() * 1000)
    range_stamps = range(release_stamp - 60 * 60_000, release_stamp - 30 * 60_000, 60_000)
    range_bid = [bid[stamp] for stamp in range_stamps if stamp in bid]
    range_ask = [ask[stamp] for stamp in range_stamps if stamp in ask]
    if len(range_bid) < 25 or len(range_ask) < 25:
        return {"status": "missing_pre_range", "trades": []}

    range_high = max(row["high"] for row in range_ask)
    range_low = min(row["low"] for row in range_bid)
    if not math.isfinite(range_high - range_low) or range_high <= range_low:
        return {"status": "invalid_range", "trades": []}

    if config.mode == "forecast":
        if forecast_side not in {"buy", "sell"}:
            return {"status": "missing_forecast", "trades": []}
        sides = (forecast_side,)
    elif config.mode == "oco":
        sides = ("buy", "sell")
    else:
        raise ValueError(f"Unsupported mode: {config.mode}")

    breakout, collision = _trigger_breakout(
        instrument=instrument,
        event=event,
        config=config,
        sides=sides,
        bid=bid,
        ask=ask,
        range_high=range_high,
        range_low=range_low,
    )
    if not breakout:
        return {
            "status": "expired",
            "trades": [],
            "range_high": range_high,
            "range_low": range_low,
            "collision": collision,
        }

    trades = [breakout]
    reentry = _trigger_reentry(
        instrument=instrument,
        event=event,
        config=config,
        breakout=breakout,
        bid=bid,
        ask=ask,
        range_high=range_high,
        range_low=range_low,
    )
    if reentry:
        trades.append(reentry)
    return {
        "status": "traded",
        "trades": [trade.to_dict() for trade in trades],
        "range_high": range_high,
        "range_low": range_low,
        "collision": collision,
    }


def performance(trades: list[dict], risk_pct: float = 1.0, start_balance: float = 10_000.0) -> dict:
    gross_profit = sum(max(0.0, float(trade["result_r"])) for trade in trades)
    gross_loss = -sum(min(0.0, float(trade["result_r"])) for trade in trades)
    winners = sum(float(trade["result_r"]) > 0 for trade in trades)
    equity = start_balance
    peak = equity
    max_drawdown = 0.0
    max_drawdown_r = 0.0
    running_r = 0.0
    peak_r = 0.0
    for trade in sorted(trades, key=lambda row: (row["entry_time"], row["leg"])):
        result_r = float(trade["result_r"])
        equity += equity * (risk_pct / 100.0) * result_r
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown = max(max_drawdown, 100.0 * (peak - equity) / peak)
        running_r += result_r
        peak_r = max(peak_r, running_r)
        max_drawdown_r = max(max_drawdown_r, peak_r - running_r)
    return {
        "trades": len(trades),
        "wins": winners,
        "losses": len(trades) - winners,
        "win_rate_pct": 100.0 * winners / len(trades) if trades else 0.0,
        "profit_factor": gross_profit / gross_loss if gross_loss > 0 else None,
        "net_r": gross_profit - gross_loss,
        "max_drawdown_r": max_drawdown_r,
        "start_balance": start_balance,
        "ending_balance": equity,
        "return_pct": 100.0 * (equity / start_balance - 1.0),
        "max_drawdown_pct": max_drawdown,
    }
