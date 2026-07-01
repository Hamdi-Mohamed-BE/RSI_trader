from __future__ import annotations

import argparse
import atexit
from datetime import datetime, timedelta, timezone
from html import escape
from io import BytesIO
import json
import os
from pathlib import Path
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid

from .config import REPORTS_DIR, load_config
from .mt5_client import MT5Client, _mt5_timeframe, mt5
from .session_time import DEFAULT_SESSION_TIMEZONE, zone


SIGNALER_DIR = REPORTS_DIR / "telegram_signaler"
STATE_PATH = SIGNALER_DIR / "state.json"
EVENTS_PATH = SIGNALER_DIR / "events.jsonl"
LOCK_PATH = SIGNALER_DIR / "telegram_signaler.lock"
HEARTBEAT_PATH = SIGNALER_DIR / "heartbeat.json"

DEFAULT_STRATEGY_MAGICS = {
    27032024: "LTA",
    30062024: "ORB",
    20052024: "20PIP",
    26062540: "BPR",
    26061515: "SNIPER",
}
DEFAULT_STRATEGY_TIMEFRAMES = {
    "LTA": "M15",
    "ORB": "M5",
    "20PIP": "M5",
    "BPR": "M15",
    "SNIPER": "H4",
}
BUY_ORDER_TYPES = {2, 4, 6}
SELL_ORDER_TYPES = {3, 5, 7}
ORDER_TYPE_NAMES = {
    2: "BUY LIMIT",
    3: "SELL LIMIT",
    4: "BUY STOP",
    5: "SELL STOP",
    6: "BUY STOP LIMIT",
    7: "SELL STOP LIMIT",
}
TIMEFRAME_PATTERN = re.compile(r"\b(M1|M5|M15|M30|H1|H4|D1|W1)\b", re.IGNORECASE)


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(os.getenv(name, str(default)) or default))
    except ValueError:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _parse_strategy_magics(value: str | None) -> dict[int, str]:
    if not value:
        return dict(DEFAULT_STRATEGY_MAGICS)
    parsed: dict[int, str] = {}
    for item in value.split(","):
        if ":" not in item:
            continue
        name, raw_magic = item.split(":", 1)
        try:
            parsed[int(raw_magic.strip())] = name.strip().upper()
        except ValueError:
            continue
    return parsed or dict(DEFAULT_STRATEGY_MAGICS)


def _parse_strategy_timeframes(value: str | None) -> dict[str, str]:
    parsed = dict(DEFAULT_STRATEGY_TIMEFRAMES)
    if not value:
        return parsed
    for item in value.split(","):
        if ":" not in item:
            continue
        name, timeframe = item.split(":", 1)
        timeframe = timeframe.strip().upper()
        if timeframe in {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"}:
            parsed[name.strip().upper()] = timeframe
    return parsed


def _direction(record: dict[str, Any], pending: bool = False) -> str:
    order_type = _safe_int(record.get("type"), -1)
    if pending:
        if order_type in BUY_ORDER_TYPES:
            return "BUY"
        if order_type in SELL_ORDER_TYPES:
            return "SELL"
        return "UNKNOWN"
    return "SELL" if order_type == 1 else "BUY"


def _setup_timeframe(comment: str, strategy: str, defaults: dict[str, str]) -> str:
    match = TIMEFRAME_PATTERN.search(str(comment or ""))
    if match:
        return match.group(1).upper()
    return defaults.get(strategy.upper(), "M15")


def _price_changed(old: Any, new: Any, point: float = 0.0) -> bool:
    tolerance = max(abs(point) * 0.5, 1e-9)
    return abs(_safe_float(old) - _safe_float(new)) > tolerance


def _classify_stop_update(old: dict[str, Any], new: dict[str, Any]) -> tuple[str, str]:
    direction = str(new.get("direction") or _direction(new)).upper()
    entry = _safe_float(new.get("price_open"))
    old_sl = _safe_float(old.get("sl"))
    new_sl = _safe_float(new.get("sl"))
    point = _safe_float(new.get("point"))
    tolerance = max(point * 2.0, abs(entry) * 1e-7, 1e-8)
    if entry > 0 and abs(new_sl - entry) <= tolerance and abs(old_sl - entry) > tolerance:
        return "TP1 / BREAK EVEN", "TP1 was reached and the stop loss moved to break even."
    improved = (direction == "BUY" and new_sl > old_sl) or (direction == "SELL" and (old_sl <= 0 or new_sl < old_sl))
    if improved:
        return "STOP TRAILED", "The stop loss was trailed forward to protect more of the trade."
    return "STOP UPDATED", "The stop-loss level changed."


def _json_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    temporary.replace(path)


def _append_event(payload: dict[str, Any]) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"initialized": False, "orders": {}, "positions": {}, "updated_at": None}
    try:
        payload = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        payload = {}
    payload.setdefault("initialized", False)
    payload.setdefault("orders", {})
    payload.setdefault("positions", {})
    return payload


class SingleInstanceLock:
    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def _running(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            try:
                existing_pid = int(json.loads(self.path.read_text(encoding="utf-8")).get("pid") or 0)
            except (OSError, ValueError, json.JSONDecodeError):
                existing_pid = 0
            if self._running(existing_pid):
                raise RuntimeError(f"Telegram signaler is already running with PID {existing_pid}.")
            self.path.unlink(missing_ok=True)
        _json_write(self.path, {"pid": os.getpid(), "started_at": datetime.now().isoformat(timespec="seconds")})

    def release(self) -> None:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}
        except (OSError, json.JSONDecodeError):
            payload = {}
        if _safe_int(payload.get("pid")) == os.getpid():
            self.path.unlink(missing_ok=True)


class TelegramAPI:
    def __init__(self, token: str, chat_id: str, timeout: int = 12) -> None:
        self.token = token.strip()
        self.chat_id = chat_id.strip()
        self.timeout = max(3, timeout)

    @property
    def configured(self) -> bool:
        return bool(self.token and self.chat_id)

    def _decode(self, response: Any) -> dict[str, Any]:
        payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(str(payload.get("description") or "Telegram rejected the request."))
        return payload.get("result") or {}

    def send_message(self, text: str, reply_to: int | None = None) -> dict[str, Any]:
        fields: dict[str, Any] = {"chat_id": self.chat_id, "text": text, "parse_mode": "HTML"}
        if reply_to:
            fields["reply_parameters"] = json.dumps(
                {"message_id": int(reply_to), "allow_sending_without_reply": True}
            )
        body = json.dumps(fields).encode("utf-8")
        request = Request(
            f"https://api.telegram.org/bot{self.token}/sendMessage",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            return self._decode(response)

    def send_photo(self, photo: bytes, caption: str, reply_to: int | None = None) -> dict[str, Any]:
        boundary = f"----CodexSignal{uuid.uuid4().hex}"
        chunks: list[bytes] = []

        def add_field(name: str, value: Any) -> None:
            chunks.extend(
                [
                    f"--{boundary}\r\n".encode(),
                    f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                    str(value).encode("utf-8"),
                    b"\r\n",
                ]
            )

        add_field("chat_id", self.chat_id)
        add_field("caption", caption)
        add_field("parse_mode", "HTML")
        if reply_to:
            add_field(
                "reply_parameters",
                json.dumps({"message_id": int(reply_to), "allow_sending_without_reply": True}),
            )
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                b'Content-Disposition: form-data; name="photo"; filename="trade-chart.png"\r\n',
                b"Content-Type: image/png\r\n\r\n",
                photo,
                b"\r\n",
                f"--{boundary}--\r\n".encode(),
            ]
        )
        request = Request(
            f"https://api.telegram.org/bot{self.token}/sendPhoto",
            data=b"".join(chunks),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout) as response:
            return self._decode(response)


class TelegramTradeSignaler:
    def __init__(self) -> None:
        self.enabled = _env_bool("TELEGRAM_SIGNALER_ENABLED", False)
        self.poll_seconds = max(2, _env_int("TELEGRAM_SIGNALER_POLL_SECONDS", 5))
        self.send_chart = _env_bool("TELEGRAM_SIGNALER_SEND_CHART", True)
        self.chart_bars = max(40, min(300, _env_int("TELEGRAM_SIGNALER_CHART_BARS", 100)))
        self.notify_existing = _env_bool("TELEGRAM_SIGNALER_NOTIFY_EXISTING", True)
        self.timezone_name = os.getenv("TELEGRAM_SIGNALER_TIMEZONE", DEFAULT_SESSION_TIMEZONE)
        self.magics = _parse_strategy_magics(os.getenv("TELEGRAM_SIGNALER_STRATEGY_MAGICS"))
        self.strategy_timeframes = _parse_strategy_timeframes(os.getenv("TELEGRAM_SIGNALER_TIMEFRAMES"))
        self.api = TelegramAPI(
            os.getenv("TELEGRAM_BOT_TOKEN", ""),
            os.getenv("TELEGRAM_CHAT_ID", ""),
            _env_int("TELEGRAM_SIGNALER_TIMEOUT_SECONDS", 12),
        )
        self.client = MT5Client()
        self.state = _load_state()

    @property
    def ready(self) -> bool:
        return self.enabled and self.api.configured

    def _strategy(self, record: dict[str, Any]) -> str | None:
        return self.magics.get(_safe_int(record.get("magic")))

    def _format_time(self, timestamp: Any) -> str:
        value = _safe_int(timestamp)
        if value <= 0:
            instant = datetime.now(timezone.utc)
        else:
            instant = datetime.fromtimestamp(value, tz=timezone.utc)
        local = instant.astimezone(zone(self.timezone_name, "UTC"))
        return local.strftime("%Y-%m-%d %H:%M:%S %Z")

    @staticmethod
    def _point_and_digits(symbol: str) -> tuple[float, int]:
        if mt5 is None:
            return 0.0, 5
        info = mt5.symbol_info(symbol)
        if info is None:
            return 0.0, 5
        return _safe_float(getattr(info, "point", 0.0)), _safe_int(getattr(info, "digits", 5), 5)

    @staticmethod
    def _format_price(value: Any, digits: int) -> str:
        number = _safe_float(value)
        return "-" if number <= 0 else f"{number:.{max(0, digits)}f}"

    def _snapshot(self, record: dict[str, Any], pending: bool) -> dict[str, Any]:
        symbol = str(record.get("symbol") or "")
        strategy = self._strategy(record) or "UNKNOWN"
        point, digits = self._point_and_digits(symbol)
        comment = str(record.get("comment") or "")
        return {
            "ticket": _safe_int(record.get("ticket")),
            "time": _safe_int(record.get("time_setup") if pending else record.get("time")),
            "time_msc": _safe_int(record.get("time_setup_msc") if pending else record.get("time_msc")),
            "type": _safe_int(record.get("type"), -1),
            "magic": _safe_int(record.get("magic")),
            "strategy": strategy,
            "symbol": symbol,
            "direction": _direction(record, pending=pending),
            "timeframe": _setup_timeframe(comment, strategy, self.strategy_timeframes),
            "volume": _safe_float(record.get("volume_initial") if pending else record.get("volume")),
            "price_open": _safe_float(record.get("price_open")),
            "price_current": _safe_float(record.get("price_current")),
            "sl": _safe_float(record.get("sl")),
            "tp": _safe_float(record.get("tp")),
            "profit": _safe_float(record.get("profit")),
            "comment": comment,
            "expiration": _safe_int(record.get("time_expiration")),
            "point": point,
            "digits": digits,
            "pending": pending,
        }

    def _tracked_orders(self) -> dict[str, dict[str, Any]]:
        return {
            str(item["ticket"]): item
            for raw in self.client.pending_orders()
            if self._strategy(raw)
            for item in [self._snapshot(raw, pending=True)]
        }

    def _tracked_positions(self) -> dict[str, dict[str, Any]]:
        return {
            str(item["ticket"]): item
            for raw in self.client.open_positions()
            if self._strategy(raw)
            for item in [self._snapshot(raw, pending=False)]
        }

    def _chart_png(self, trade: dict[str, Any]) -> bytes | None:
        if not self.send_chart or mt5 is None:
            return None
        timeframe = str(trade.get("timeframe") or "M15").upper()
        mt5_timeframe = _mt5_timeframe(timeframe)
        if mt5_timeframe is None:
            return None
        rates = mt5.copy_rates_from_pos(str(trade.get("symbol") or ""), mt5_timeframe, 0, self.chart_bars)
        if rates is None or len(rates) < 10:
            return None
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.dates as mdates
            import matplotlib.pyplot as plt
            from matplotlib.patches import Rectangle
        except Exception:
            return None

        times = [datetime.fromtimestamp(int(row["time"]), tz=timezone.utc) for row in rates]
        x_values = mdates.date2num(times)
        candle_width = (x_values[1] - x_values[0]) * 0.68 if len(x_values) > 1 else 0.005
        fig, axis = plt.subplots(figsize=(12.8, 7.2), dpi=120)
        fig.patch.set_facecolor("#080d18")
        axis.set_facecolor("#080d18")
        axis.grid(True, color="#263244", alpha=0.55, linewidth=0.6)
        for x_value, row in zip(x_values, rates):
            open_price = float(row["open"])
            close_price = float(row["close"])
            high = float(row["high"])
            low = float(row["low"])
            color = "#22c997" if close_price >= open_price else "#ff5d6c"
            axis.vlines(x_value, low, high, color=color, linewidth=0.9)
            body_low = min(open_price, close_price)
            body_height = max(abs(close_price - open_price), max(high - low, 1e-9) * 0.015)
            axis.add_patch(
                Rectangle(
                    (x_value - candle_width / 2, body_low),
                    candle_width,
                    body_height,
                    facecolor=color,
                    edgecolor=color,
                    linewidth=0.6,
                )
            )

        entry = _safe_float(trade.get("price_open"))
        stop = _safe_float(trade.get("sl"))
        target = _safe_float(trade.get("tp"))
        current = _safe_float(trade.get("price_current"))
        levels = [
            (entry, "ENTRY", "#4da3ff", 1.4),
            (stop, "SL", "#ff5d6c", 1.2),
            (target, "TP", "#22c997", 1.2),
            (current, "CURRENT", "#f3c969", 0.9),
        ]
        for price, label, color, width in levels:
            if price <= 0:
                continue
            axis.axhline(price, color=color, linewidth=width, linestyle="--" if label == "CURRENT" else "-")
            axis.text(
                0.995,
                price,
                f" {label} {self._format_price(price, _safe_int(trade.get('digits'), 5))} ",
                transform=axis.get_yaxis_transform(),
                ha="right",
                va="center",
                color="#ffffff",
                fontsize=8,
                bbox={"facecolor": color, "edgecolor": "none", "alpha": 0.88, "pad": 2.0},
            )

        axis.set_title(
            f"{trade.get('strategy')} | {trade.get('symbol')} {trade.get('direction')} | {timeframe}",
            color="#f6f8fc",
            loc="left",
            fontsize=14,
            pad=14,
        )
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M", tz=timezone.utc))
        axis.tick_params(colors="#aab4c5", labelsize=8)
        axis.yaxis.tick_right()
        for spine in axis.spines.values():
            spine.set_color("#263244")
        axis.margins(x=0.02, y=0.12)
        fig.tight_layout()
        output = BytesIO()
        fig.savefig(output, format="png", facecolor=fig.get_facecolor(), bbox_inches="tight")
        plt.close(fig)
        return output.getvalue()

    def _signal_text(self, trade: dict[str, Any], pending: bool) -> str:
        digits = _safe_int(trade.get("digits"), 5)
        strategy = escape(str(trade.get("strategy") or "UNKNOWN"))
        symbol = escape(str(trade.get("symbol") or ""))
        direction = escape(str(trade.get("direction") or ""))
        heading = "PRE-ORDER PLACED" if pending else "LIVE ENTRY"
        order_name = ORDER_TYPE_NAMES.get(_safe_int(trade.get("type")), direction) if pending else direction
        lines = [
            f"<b>{strategy} | {heading}</b>",
            f"<b>{symbol} {escape(order_name)}</b>",
            f"Entry: <code>{self._format_price(trade.get('price_open'), digits)}</code>",
            f"Stop Loss: <code>{self._format_price(trade.get('sl'), digits)}</code>",
            f"Take Profit: <code>{self._format_price(trade.get('tp'), digits)}</code>",
            f"Volume: <code>{_safe_float(trade.get('volume')):g}</code>",
            f"Order time: <code>{escape(self._format_time(trade.get('time')))}</code>",
            f"Setup timeframe: <code>{escape(str(trade.get('timeframe') or '-'))}</code>",
            f"Ticket: <code>{_safe_int(trade.get('ticket'))}</code>",
        ]
        if pending and _safe_int(trade.get("expiration")) > 0:
            lines.append(f"Expires: <code>{escape(self._format_time(trade.get('expiration')))}</code>")
        if trade.get("comment"):
            lines.append(f"Comment: <code>{escape(str(trade.get('comment')))[:120]}</code>")
        return "\n".join(lines)

    def _send(self, text: str, reply_to: int | None = None, chart_trade: dict[str, Any] | None = None) -> dict[str, Any]:
        chart_error: str | None = None
        try:
            chart = self._chart_png(chart_trade) if chart_trade else None
            if chart:
                try:
                    result = self.api.send_photo(chart, text, reply_to=reply_to)
                    return {
                        "sent": True,
                        "message_id": _safe_int(result.get("message_id")),
                        "result": result,
                        "chart_sent": True,
                    }
                except (HTTPError, URLError, TimeoutError, RuntimeError, OSError, ValueError) as exc:
                    chart_error = str(exc)
            result = self.api.send_message(text, reply_to=reply_to)
            return {
                "sent": True,
                "message_id": _safe_int(result.get("message_id")),
                "result": result,
                "chart_sent": False,
                "chart_error": chart_error,
            }
        except (HTTPError, URLError, TimeoutError, RuntimeError, OSError, ValueError) as exc:
            return {"sent": False, "message": str(exc), "chart_error": chart_error}

    def _send_original(self, trade: dict[str, Any], pending: bool) -> None:
        response = self._send(self._signal_text(trade, pending), chart_trade=trade)
        trade["telegram_message_id"] = _safe_int(response.get("message_id")) if response.get("sent") else 0
        trade["telegram_sent_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _append_event(
            {
                "created_at": trade["telegram_sent_at"],
                "event": "pending_signal_sent" if pending else "live_signal_sent",
                "strategy": trade.get("strategy"),
                "symbol": trade.get("symbol"),
                "ticket": trade.get("ticket"),
                "response": response,
            }
        )

    def _reply(self, trade: dict[str, Any], heading: str, message: str, details: list[str] | None = None) -> None:
        lines = [
            f"<b>{escape(str(trade.get('strategy') or 'UNKNOWN'))} | {escape(heading)}</b>",
            f"<b>{escape(str(trade.get('symbol') or ''))} {escape(str(trade.get('direction') or ''))}</b>",
            escape(message),
        ]
        if details:
            lines.extend(details)
        response = self._send("\n".join(lines), reply_to=_safe_int(trade.get("telegram_message_id")) or None)
        _append_event(
            {
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "event": heading.lower().replace(" ", "_"),
                "strategy": trade.get("strategy"),
                "symbol": trade.get("symbol"),
                "ticket": trade.get("ticket"),
                "reply_to": trade.get("telegram_message_id"),
                "response": response,
            }
        )

    @staticmethod
    def _matching_removed_order(
        position: dict[str, Any],
        removed_orders: dict[str, dict[str, Any]],
    ) -> tuple[str, dict[str, Any]] | None:
        candidates = [
            (ticket, order)
            for ticket, order in removed_orders.items()
            if order.get("magic") == position.get("magic")
            and order.get("symbol") == position.get("symbol")
            and order.get("direction") == position.get("direction")
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: _safe_int(item[1].get("time")))

    def _closed_details(self, ticket: int) -> dict[str, Any]:
        if mt5 is None:
            return {}
        try:
            deals = mt5.history_deals_get(position=int(ticket)) or []
        except Exception:
            deals = []
        exits = []
        for deal in deals:
            payload = deal._asdict()
            entry_type = _safe_int(payload.get("entry"), -1)
            if entry_type in {
                getattr(mt5, "DEAL_ENTRY_OUT", 1),
                getattr(mt5, "DEAL_ENTRY_OUT_BY", 3),
                getattr(mt5, "DEAL_ENTRY_INOUT", 2),
            }:
                exits.append(payload)
        if not exits:
            return {}
        latest = max(exits, key=lambda item: _safe_int(item.get("time_msc") or item.get("time")))
        return {
            "price": _safe_float(latest.get("price")),
            "time": _safe_int(latest.get("time")),
            "profit": sum(
                _safe_float(item.get("profit"))
                + _safe_float(item.get("commission"))
                + _safe_float(item.get("swap"))
                + _safe_float(item.get("fee"))
                for item in exits
            ),
            "comment": str(latest.get("comment") or ""),
            "reason": _safe_int(latest.get("reason"), -1),
        }

    def _process_position_update(self, old: dict[str, Any], new: dict[str, Any]) -> None:
        new["telegram_message_id"] = _safe_int(old.get("telegram_message_id"))
        point = _safe_float(new.get("point"))
        details: list[str] = []
        headings: list[str] = []
        messages: list[str] = []
        if _price_changed(old.get("sl"), new.get("sl"), point):
            heading, message = _classify_stop_update(old, new)
            headings.append(heading)
            messages.append(message)
            details.append(
                f"SL: <code>{self._format_price(old.get('sl'), _safe_int(new.get('digits'), 5))}</code> -> "
                f"<code>{self._format_price(new.get('sl'), _safe_int(new.get('digits'), 5))}</code>"
            )
        if _price_changed(old.get("tp"), new.get("tp"), point):
            headings.append("TP UPDATED")
            messages.append("The take-profit target was updated by the strategy.")
            details.append(
                f"TP: <code>{self._format_price(old.get('tp'), _safe_int(new.get('digits'), 5))}</code> -> "
                f"<code>{self._format_price(new.get('tp'), _safe_int(new.get('digits'), 5))}</code>"
            )
        if headings:
            details.append(f"Current: <code>{self._format_price(new.get('price_current'), _safe_int(new.get('digits'), 5))}</code>")
            self._reply(new, " + ".join(headings), " ".join(messages), details)

    def run_once(self) -> dict[str, Any]:
        if not self.ready:
            return {
                "ok": False,
                "message": "Set TELEGRAM_SIGNALER_ENABLED=true, TELEGRAM_BOT_TOKEN, and TELEGRAM_CHAT_ID in .env.",
            }
        if not self.client.connect():
            return {"ok": False, "message": "MT5 is not connected."}

        current_orders = self._tracked_orders()
        current_positions = self._tracked_positions()
        previous_orders = self.state.get("orders") or {}
        previous_positions = self.state.get("positions") or {}
        initialized = bool(self.state.get("initialized"))
        events = {"new_orders": 0, "new_positions": 0, "updates": 0, "closed": 0, "removed_orders": 0}

        if not initialized:
            if self.notify_existing:
                for order in current_orders.values():
                    self._send_original(order, pending=True)
                    events["new_orders"] += 1
                for position in current_positions.values():
                    self._send_original(position, pending=False)
                    events["new_positions"] += 1
            self.state = {
                "initialized": True,
                "orders": current_orders,
                "positions": current_positions,
                "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            _json_write(STATE_PATH, self.state)
            return {"ok": True, "bootstrap": True, **events}

        removed_orders = {ticket: item for ticket, item in previous_orders.items() if ticket not in current_orders}
        matched_removed_orders: set[str] = set()

        for ticket, order in current_orders.items():
            previous = previous_orders.get(ticket)
            if previous:
                order["telegram_message_id"] = _safe_int(previous.get("telegram_message_id"))
                continue
            self._send_original(order, pending=True)
            events["new_orders"] += 1

        for ticket, position in current_positions.items():
            previous = previous_positions.get(ticket)
            if previous:
                self._process_position_update(previous, position)
                position["telegram_message_id"] = _safe_int(previous.get("telegram_message_id"))
                if _price_changed(previous.get("sl"), position.get("sl"), _safe_float(position.get("point"))) or _price_changed(
                    previous.get("tp"), position.get("tp"), _safe_float(position.get("point"))
                ):
                    events["updates"] += 1
                continue

            matched = self._matching_removed_order(position, removed_orders)
            if matched:
                order_ticket, order = matched
                matched_removed_orders.add(order_ticket)
                position["telegram_message_id"] = _safe_int(order.get("telegram_message_id"))
                self._reply(
                    position,
                    "PENDING ORDER FILLED",
                    "The pre-order was triggered and is now a live position.",
                    [
                        f"Entry: <code>{self._format_price(position.get('price_open'), _safe_int(position.get('digits'), 5))}</code>",
                        f"Fill time: <code>{escape(self._format_time(position.get('time')))}</code>",
                        f"Position ticket: <code>{ticket}</code>",
                    ],
                )
            else:
                self._send_original(position, pending=False)
            events["new_positions"] += 1

        for ticket, order in removed_orders.items():
            if ticket in matched_removed_orders:
                continue
            self._reply(
                order,
                "PENDING ORDER REMOVED",
                "The pre-order is no longer active. It may have been cancelled, rejected, or expired.",
                [f"Order ticket: <code>{ticket}</code>"],
            )
            events["removed_orders"] += 1

        for ticket, position in previous_positions.items():
            if ticket in current_positions:
                continue
            close = self._closed_details(_safe_int(ticket))
            position["telegram_message_id"] = _safe_int(position.get("telegram_message_id"))
            profit = _safe_float(close.get("profit"))
            outcome = "WIN" if profit > 0 else "LOSS" if profit < 0 else "BREAK EVEN"
            self._reply(
                position,
                f"TRADE CLOSED | {outcome}",
                "The position is closed.",
                [
                    f"Exit: <code>{self._format_price(close.get('price'), _safe_int(position.get('digits'), 5))}</code>",
                    f"Result: <code>{profit:+.2f}</code>",
                    f"Close time: <code>{escape(self._format_time(close.get('time')))}</code>",
                    f"Position ticket: <code>{ticket}</code>",
                ],
            )
            events["closed"] += 1

        self.state = {
            "initialized": True,
            "orders": current_orders,
            "positions": current_positions,
            "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        _json_write(STATE_PATH, self.state)
        _json_write(
            HEARTBEAT_PATH,
            {
                "pid": os.getpid(),
                "status": "watching",
                "updated_at": self.state["updated_at"],
                "events": events,
            },
        )
        return {"ok": True, "bootstrap": False, **events}

    def run_forever(self) -> None:
        print("Telegram trade signaler started.")
        print("Watching strategies: " + ", ".join(f"{name}={magic}" for magic, name in self.magics.items()))
        print(f"Polling MT5 every {self.poll_seconds}s. Chart snapshots: {self.send_chart}.")
        if not self.enabled:
            print("Disabled: set TELEGRAM_SIGNALER_ENABLED=true in .env.")
        if not self.api.configured:
            print("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env.")
        print("This watcher never places or modifies MT5 orders.")
        print("Press Ctrl+C to stop.")
        while True:
            result = self.run_once()
            now = datetime.now().isoformat(timespec="seconds")
            _json_write(
                HEARTBEAT_PATH,
                {
                    "pid": os.getpid(),
                    "status": "watching" if result.get("ok") else "waiting_for_configuration",
                    "updated_at": now,
                    "result": result,
                },
            )
            if result.get("ok"):
                print(
                    f"[{now}] orders={result.get('new_orders', 0)} positions={result.get('new_positions', 0)} "
                    f"updates={result.get('updates', 0)} closed={result.get('closed', 0)} "
                    f"removed={result.get('removed_orders', 0)}"
                )
            else:
                print(f"[{now}] waiting: {result.get('message')}")
            time.sleep(self.poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Telegram signal and trade-update watcher for all MT5 bots.")
    parser.add_argument("--once", action="store_true", help="Poll MT5 once and exit.")
    args = parser.parse_args()
    load_config()
    lock = SingleInstanceLock(LOCK_PATH)
    lock.acquire()
    atexit.register(lock.release)
    signaler = TelegramTradeSignaler()
    atexit.register(signaler.client.shutdown)
    if args.once:
        print(json.dumps(signaler.run_once(), indent=2, default=str))
        return
    signaler.run_forever()


if __name__ == "__main__":
    main()
