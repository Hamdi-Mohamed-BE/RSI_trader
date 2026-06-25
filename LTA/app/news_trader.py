from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
import os
from pathlib import Path
from typing import Any

from .config import REPORTS_DIR
from .mt5_client import MT5Client
from .news_effect import parse_news_time, upcoming_news_events


NEWS_MAGIC_DEFAULT = 26062530
NEWS_DIR = REPORTS_DIR / "news_bot"
NEWS_DIR.mkdir(parents=True, exist_ok=True)
NEWS_STATE_PATH = NEWS_DIR / "news_state.json"
NEWS_EVENTS_LOG_PATH = NEWS_DIR / "news_trade_events.jsonl"


DEFAULT_TRIGGER_POINTS = {
    "XAUUSD": 40.0,
    "XAGUSD": 30.0,
    "EURUSD": 10.0,
    "BTCUSD": 5000.0,
    "US30": 80.0,
}
DEFAULT_STOP_POINTS = {
    "XAUUSD": 250.0,
    "XAGUSD": 120.0,
    "EURUSD": 80.0,
    "BTCUSD": 15000.0,
    "US30": 250.0,
}


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _int_env(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default)) or default))
    except ValueError:
        return default


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def _read_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _event_code(event_time: datetime) -> str:
    return event_time.astimezone(timezone.utc).strftime("%m%d%H%M")


def _short_symbol(symbol: str) -> str:
    return "".join(ch for ch in symbol.upper() if ch.isalnum())[:6]


def _event_symbols(event: dict[str, Any], allowed_symbols: tuple[str, ...]) -> tuple[str, ...]:
    raw = str(event.get("symbols") or "").strip()
    if raw:
        requested = tuple(item.strip().upper() for item in raw.split(",") if item.strip())
        selected = tuple(symbol for symbol in allowed_symbols if symbol.upper() in requested)
        if selected:
            return selected
    currency = str(event.get("currency") or "").upper()
    if currency == "USD":
        return allowed_symbols
    return allowed_symbols


def _side_code(side: str) -> str:
    return "B" if side.upper() == "BUY" else "S"


@dataclass(frozen=True)
class NewsOrderPlan:
    symbol: str
    side: str
    pending_order_type: str
    trigger_price: float
    stop_loss: float
    take_profit: float
    stop_points: float
    trigger_offset_points: float
    comment: str


class NewsStraddleTrader:
    def __init__(self, symbols: tuple[str, ...]) -> None:
        self.symbols = tuple(symbol.upper() for symbol in symbols)
        self.client = MT5Client()
        self.magic = _int_env("NEWS_MAGIC", NEWS_MAGIC_DEFAULT)
        self.live_trading = _bool_env("NEWS_LIVE_TRADING", _bool_env("LIVE_TRADING", False))
        self.place_pending = _bool_env("NEWS_PLACE_PENDING", False)
        self.use_fallback_times = _bool_env("NEWS_USE_EVENT_TIME_FALLBACK", True)
        self.preplace_seconds = max(1, _int_env("NEWS_PREPLACE_SECONDS", 60))
        self.preplace_window_seconds = max(self.preplace_seconds, _int_env("NEWS_PREPLACE_WINDOW_SECONDS", self.preplace_seconds))
        self.allow_late_seconds = max(0, _int_env("NEWS_ALLOW_LATE_SECONDS", 0))
        self.lookahead_minutes = max(1, _int_env("NEWS_LOOKAHEAD_MINUTES", 10))
        self.pending_expiry_minutes = max(1, _int_env("NEWS_PENDING_EXPIRY_MINUTES", 15))
        self.risk_pct = _float_env("NEWS_RISK_PCT", 3.0)
        self.rr = max(0.1, _float_env("NEWS_RR", 2.0))
        self.max_spread_risk_percent = _float_env("NEWS_MAX_SPREAD_RISK_PERCENT", 0.0)
        self.max_spread_points = _float_env("NEWS_MAX_SPREAD_POINTS", 0.0)
        self.trigger_spread_multiplier = max(0.0, _float_env("NEWS_TRIGGER_OFFSET_SPREAD_MULTIPLIER", 2.0))
        self.stop_spread_multiplier = max(0.0, _float_env("NEWS_STOP_SPREAD_MULTIPLIER", 8.0))
        self.stop_range_multiplier = max(0.0, _float_env("NEWS_STOP_RANGE_MULTIPLIER", 1.25))
        self.pre_range_bars = max(1, _int_env("NEWS_PRE_RANGE_BARS", 3))
        self.max_symbols_per_event = max(0, _int_env("NEWS_MAX_SYMBOLS_PER_EVENT", 0))
        self.one_straddle_per_symbol = _bool_env("NEWS_ONE_STRADDLE_PER_SYMBOL", True)
        self.cancel_opposite_on_fill = _bool_env("NEWS_CANCEL_OPPOSITE_ON_FILL", True)

    def _state(self) -> dict[str, Any]:
        return _read_json(NEWS_STATE_PATH, {"placed_sides": {}})

    def _save_state(self, state: dict[str, Any]) -> None:
        state["updated_at"] = datetime.now().isoformat(timespec="seconds")
        _write_json(NEWS_STATE_PATH, state)

    def _side_key(self, event_code: str, symbol: str, side: str) -> str:
        return f"{event_code}|{symbol.upper()}|{side.upper()}"

    def _point_and_digits(self, symbol: str) -> tuple[float, int, float]:
        info = self.client.symbol_info(symbol) or {}
        point = float(info.get("point") or 0.0)
        digits = int(info.get("digits") or 5)
        if point <= 0:
            point = 10 ** -digits
        stop_level_points = float(info.get("trade_stops_level") or 0.0)
        return point, digits, stop_level_points

    def _recent_range_points(self, symbol: str, point: float) -> float:
        if point <= 0:
            return 0.0
        end = datetime.now()
        start = end - timedelta(minutes=max(10, self.pre_range_bars + 5))
        candles = self.client.fetch_candles(symbol, "M1", start, end, max_bars=max(10, self.pre_range_bars + 5))
        if candles is None or candles.empty:
            return 0.0
        recent = candles.tail(self.pre_range_bars)
        if recent.empty:
            return 0.0
        return max(0.0, (float(recent["high"].max()) - float(recent["low"].min())) / point)

    def _trigger_points(self, symbol: str, quote: dict[str, float], stop_level_points: float) -> float:
        default = DEFAULT_TRIGGER_POINTS.get(symbol.upper(), 20.0)
        configured = _float_env(f"NEWS_{symbol.upper()}_TRIGGER_OFFSET_POINTS", _float_env("NEWS_TRIGGER_OFFSET_POINTS", default))
        spread_points = float(quote.get("spread_points") or 0.0)
        return max(configured, spread_points * self.trigger_spread_multiplier, stop_level_points + 2.0, 1.0)

    def _stop_points(self, symbol: str, quote: dict[str, float], point: float, trigger_points: float, stop_level_points: float) -> float:
        default = DEFAULT_STOP_POINTS.get(symbol.upper(), max(trigger_points * 4.0, 100.0))
        configured = _float_env(f"NEWS_{symbol.upper()}_STOP_POINTS", _float_env("NEWS_STOP_POINTS", default))
        range_points = self._recent_range_points(symbol, point) * self.stop_range_multiplier
        spread_points = float(quote.get("spread_points") or 0.0) * self.stop_spread_multiplier
        broker_min = max(stop_level_points * 2.0, trigger_points * 2.0)
        return max(configured, range_points, spread_points, broker_min, 1.0)

    def _plan_orders(self, symbol: str, event_code: str) -> tuple[list[NewsOrderPlan], dict[str, Any] | None]:
        quote = self.client.current_quote(symbol)
        if not quote:
            return [], {"symbol": symbol, "message": "No live quote is available."}
        point, digits, stop_level_points = self._point_and_digits(symbol)
        trigger_points = self._trigger_points(symbol, quote, stop_level_points)
        stop_points = self._stop_points(symbol, quote, point, trigger_points, stop_level_points)
        trigger_distance = trigger_points * point
        stop_distance = stop_points * point
        ask = float(quote["ask"])
        bid = float(quote["bid"])
        buy_trigger = round(ask + trigger_distance, digits)
        sell_trigger = round(bid - trigger_distance, digits)
        plans = [
            NewsOrderPlan(
                symbol=symbol,
                side="BUY",
                pending_order_type="BUY_STOP",
                trigger_price=buy_trigger,
                stop_loss=round(buy_trigger - stop_distance, digits),
                take_profit=round(buy_trigger + stop_distance * self.rr, digits),
                stop_points=stop_points,
                trigger_offset_points=trigger_points,
                comment=f"NEWS {event_code} {_short_symbol(symbol)} B"[:31],
            ),
            NewsOrderPlan(
                symbol=symbol,
                side="SELL",
                pending_order_type="SELL_STOP",
                trigger_price=sell_trigger,
                stop_loss=round(sell_trigger + stop_distance, digits),
                take_profit=round(sell_trigger - stop_distance * self.rr, digits),
                stop_points=stop_points,
                trigger_offset_points=trigger_points,
                comment=f"NEWS {event_code} {_short_symbol(symbol)} S"[:31],
            ),
        ]
        return plans, None

    def _order_exists(self, symbol: str, event_code: str, side: str) -> bool:
        side_marker = f" {_side_code(side)}"
        prefix = f"NEWS {event_code}"
        for order in self.client.pending_orders(symbol, magic=self.magic):
            comment = str(order.get("comment") or "")
            if prefix in comment and side_marker in comment:
                return True
        for position in self.client.open_positions(symbol, magic=self.magic):
            comment = str(position.get("comment") or "")
            if prefix in comment and side_marker in comment:
                return True
        return False

    def _cancel_triggered_opposites(self) -> list[dict[str, Any]]:
        if not self.cancel_opposite_on_fill:
            return []
        cancelled: list[dict[str, Any]] = []
        for symbol in self.symbols:
            positions = self.client.open_positions(symbol, magic=self.magic)
            if not positions:
                continue
            orders = self.client.pending_orders(symbol, magic=self.magic)
            for position in positions:
                comment = str(position.get("comment") or "")
                if not comment.startswith("NEWS "):
                    continue
                parts = comment.split()
                if len(parts) < 2:
                    continue
                prefix = f"NEWS {parts[1]}"
                for order in orders:
                    order_comment = str(order.get("comment") or "")
                    if prefix not in order_comment:
                        continue
                    result = self.client.cancel_pending_order(int(order.get("ticket") or 0), symbol=symbol)
                    payload = {
                        "time": datetime.now().isoformat(timespec="seconds"),
                        "event": "news_opposite_pending_cancel",
                        "symbol": symbol,
                        "position": position.get("ticket"),
                        "order": order.get("ticket"),
                        "comment": order_comment,
                        "result": result,
                    }
                    _append_jsonl(NEWS_EVENTS_LOG_PATH, payload)
                    cancelled.append(payload)
        return cancelled

    def _event_is_in_preplace_window(self, event_time: datetime, now: datetime) -> tuple[bool, float, str]:
        seconds_to_event = (event_time - now).total_seconds()
        earliest = self.preplace_window_seconds
        if seconds_to_event > earliest:
            return False, seconds_to_event, f"waiting; event is {seconds_to_event:.0f}s away"
        if seconds_to_event < -self.allow_late_seconds:
            return False, seconds_to_event, f"late; event passed {-seconds_to_event:.0f}s ago"
        return True, seconds_to_event, "inside pre-place window"

    def process(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        events = upcoming_news_events(self.lookahead_minutes, include_scheduled_fallback=self.use_fallback_times)
        state = self._state()
        placed_sides = state.setdefault("placed_sides", {})
        summary: dict[str, Any] = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "bot": "news",
            "live_trading": self.live_trading,
            "place_pending": self.place_pending,
            "magic": self.magic,
            "events_seen": len(events),
            "events_in_window": 0,
            "prepared": 0,
            "placed": 0,
            "blocked": 0,
            "cancelled_opposites": 0,
            "messages": [],
            "placements": [],
        }
        cancelled = self._cancel_triggered_opposites()
        summary["cancelled_opposites"] = len(cancelled)

        for event in events:
            event_time = parse_news_time(event.get("time_utc") or event.get("time"))
            if event_time is None:
                continue
            event_code = _event_code(event_time)
            in_window, seconds_to_event, window_message = self._event_is_in_preplace_window(event_time, now)
            label = event.get("title") or event.get("event") or event_code
            summary["messages"].append(f"{label}: {window_message}")
            if not in_window:
                continue
            summary["events_in_window"] += 1
            symbols = _event_symbols(event, self.symbols)
            if self.max_symbols_per_event:
                symbols = symbols[: self.max_symbols_per_event]
            for symbol in symbols:
                if self.one_straddle_per_symbol:
                    active = self.client.open_positions(symbol, magic=self.magic)
                    if active:
                        summary["blocked"] += 1
                        summary["messages"].append(f"{symbol}: active news position exists; straddle skipped.")
                        continue
                plans, error = self._plan_orders(symbol, event_code)
                if error:
                    summary["blocked"] += 1
                    summary["messages"].append(f"{symbol}: {error['message']}")
                    continue
                for plan in plans:
                    side_key = self._side_key(event_code, symbol, plan.side)
                    if side_key in placed_sides or self._order_exists(symbol, event_code, plan.side):
                        summary["messages"].append(f"{symbol} {plan.side}: already placed for {event_code}.")
                        continue

                    signal = {
                        "symbol": symbol,
                        "direction": plan.side,
                        "execution_type": "PENDING",
                        "pending_order_type": plan.pending_order_type,
                        "trigger_price": plan.trigger_price,
                        "entry": plan.trigger_price,
                        "stop_loss": plan.stop_loss,
                        "take_profit": plan.take_profit,
                        "timeframe": "M1",
                        "setup_score": 96,
                        "setup_grade": "NEWS",
                    }
                    lot_sizing = self.client.risk_based_lot(
                        signal,
                        risk_percent=self.risk_pct,
                        require_account_balance=self.live_trading and self.place_pending,
                    )
                    if not lot_sizing.get("ok"):
                        summary["blocked"] += 1
                        summary["messages"].append(f"{symbol} {plan.side}: lot blocked - {lot_sizing.get('message')}")
                        _append_jsonl(
                            NEWS_EVENTS_LOG_PATH,
                            {
                                "time": datetime.now().isoformat(timespec="seconds"),
                                "event": "news_order_blocked_lot",
                                "news": event,
                                "symbol": symbol,
                                "side": plan.side,
                                "plan": plan.__dict__,
                                "lot_sizing": lot_sizing,
                            },
                        )
                        continue

                    order = {
                        "live_trading": self.live_trading and self.place_pending,
                        "symbol": symbol,
                        "broker_symbol": self.client.resolve_symbol(symbol) or symbol,
                        "direction": plan.side,
                        "execution_type": "PENDING",
                        "pending_order_type": plan.pending_order_type,
                        "trigger_price": plan.trigger_price,
                        "entry": plan.trigger_price,
                        "stop_loss": plan.stop_loss,
                        "take_profit": plan.take_profit,
                        "tp1": plan.trigger_price + (plan.trigger_price - plan.stop_loss)
                        if plan.side == "BUY"
                        else plan.trigger_price - (plan.stop_loss - plan.trigger_price),
                        "lot": float(lot_sizing["lot"]),
                        "magic": self.magic,
                        "comment": plan.comment,
                        "expires_at": (datetime.now() + timedelta(minutes=self.pending_expiry_minutes)).isoformat(timespec="seconds"),
                        "spread_limits": {
                            "max_spread_risk_percent": self.max_spread_risk_percent,
                            "max_spread_points": self.max_spread_points,
                        },
                    }
                    summary["prepared"] += 1
                    placement = self.client.place_pending_order(order)
                    placed = bool(placement.get("placed"))
                    if placed:
                        placed_sides[side_key] = {
                            "placed_at": datetime.now().isoformat(timespec="seconds"),
                            "event_code": event_code,
                            "symbol": symbol,
                            "side": plan.side,
                            "ticket": (placement.get("result") or {}).get("order"),
                            "comment": plan.comment,
                            "event_time_utc": event_time.isoformat(),
                        }
                        summary["placed"] += 1
                    else:
                        summary["blocked"] += 1
                    payload = {
                        "time": datetime.now().isoformat(timespec="seconds"),
                        "event": "news_pending_order_sent",
                        "placed": placed,
                        "seconds_to_event": seconds_to_event,
                        "news": event,
                        "symbol": symbol,
                        "side": plan.side,
                        "order": order,
                        "lot_sizing": lot_sizing,
                        "placement": placement,
                    }
                    summary["placements"].append(payload)
                    _append_jsonl(NEWS_EVENTS_LOG_PATH, payload)
                    message = placement.get("message") or ("placed" if placed else "failed")
                    summary["messages"].append(f"{symbol} {plan.side}: {message}")

        self._save_state(state)
        return summary
