from __future__ import annotations

import argparse
import atexit
from datetime import datetime, timedelta
import json
import os
import time
from pathlib import Path
from typing import Any

from .config import REPORTS_DIR, load_config
from .models import TRADE_SYMBOLS
from .mt5_client import MT5Client
from .orb_strategy import ORBSettings, confirmed_orb_signal, pending_orb_signals
from .session_time import DEFAULT_DATA_TIMEZONE, DEFAULT_SESSION_TIMEZONE, date_in_timezone, now_naive


ORB_MAGIC = 30062024
ORB_DIR = REPORTS_DIR / "orb_bot"
STATE_PATH = ORB_DIR / "orb_state.json"
EVENTS_PATH = ORB_DIR / "orb_events.jsonl"
LATEST_PATH = ORB_DIR / "latest.json"
LOCK_PATH = ORB_DIR / "orb.lock"
HEARTBEAT_PATH = ORB_DIR / "orb_heartbeat.json"


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "consumed": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "consumed": {}}
    if not isinstance(data, dict):
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "consumed": {}}
    data.setdefault("consumed", {})
    return data


def _write_state(state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write_json(STATE_PATH, state)


class ORBLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise RuntimeError("ORB worker is already running or the lock file still exists.")
        self.path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": datetime.now().isoformat(timespec="seconds")}, indent=2),
            encoding="utf-8",
        )
        self.acquired = True
        atexit.register(self.release)

    def release(self) -> None:
        if self.acquired:
            _write_json(
                HEARTBEAT_PATH,
                {
                    "pid": os.getpid(),
                    "status": "stopped",
                    "updated_at": datetime.now().isoformat(timespec="seconds"),
                },
            )
            self.path.unlink(missing_ok=True)
            self.acquired = False


class ORBBot:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = MT5Client()
        self.symbols = _env_list("ORB_SYMBOLS", TRADE_SYMBOLS)
        self.timeframe = os.getenv("ORB_TIMEFRAME", "M15").strip().upper() or "M15"
        self.interval_seconds = max(10, _env_int("ORB_SCAN_INTERVAL_SECONDS", 60))
        self.lookback_days = max(3, _env_int("ORB_LOOKBACK_DAYS", 10))
        self.live_trading = _env_bool("ORB_LIVE_TRADING", False)
        self.place_trades = _env_bool("ORB_PLACE_TRADES", False)
        self.prepare_pending = _env_bool("ORB_PREPARE_PENDING", True)
        self.place_pending = _env_bool("ORB_PLACE_PENDING", False)
        self.one_trade_per_symbol_per_day = _env_bool("ORB_ONE_TRADE_PER_SYMBOL_PER_DAY", True)
        self.risk_percent = max(0.0, _env_float("ORB_MAX_LOT_RISK_PCT", self.config.max_lot_risk_pct))
        self.max_spread_risk_percent = max(0.0, _env_float("ORB_MAX_SPREAD_RISK_PERCENT", self.config.max_spread_risk_percent))
        self.max_spread_points = max(0.0, _env_float("ORB_MAX_SPREAD_POINTS", self.config.max_spread_points))
        self.pending_expiry_minutes = max(0, _env_int("ORB_PENDING_EXPIRY_MINUTES", 360))
        self.settings = ORBSettings(
            session_start=os.getenv("ORB_SESSION_START", "09:30"),
            session_end=os.getenv("ORB_SESSION_END", "16:00"),
            range_minutes=max(1, _env_int("ORB_RANGE_MINUTES", 30)),
            reward_risk=max(0.5, _env_float("ORB_RR", 2.0)),
            buffer_atr=max(0.0, _env_float("ORB_BREAK_BUFFER_ATR", 0.0)),
            min_range_atr=max(0.0, _env_float("ORB_MIN_RANGE_ATR", 0.0)),
            max_range_atr=max(0.0, _env_float("ORB_MAX_RANGE_ATR", 999.0)),
            max_signal_age_minutes=max(1, _env_int("ORB_MAX_SIGNAL_AGE_MINUTES", 30)),
            session_timezone=os.getenv("ORB_SESSION_TIMEZONE", os.getenv("MARKET_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE)),
            data_timezone=os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE),
        )
        self.state = _read_state()
        _write_state(self.state)

    def _heartbeat(self, status: str) -> None:
        _write_json(
            HEARTBEAT_PATH,
            {
                "pid": os.getpid(),
                "status": status,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            },
        )

    def _log_event(self, event: str, **payload: Any) -> None:
        _append_jsonl(
            EVENTS_PATH,
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "event": event,
                **payload,
            },
        )

    @staticmethod
    def _state_key(signal: dict[str, Any]) -> str:
        timestamp = signal.get("timestamp")
        data_timezone = os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE)
        session_timezone = os.getenv("ORB_SESSION_TIMEZONE", os.getenv("MARKET_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE))
        if isinstance(timestamp, datetime):
            day = date_in_timezone(timestamp, data_timezone, session_timezone).isoformat()
        else:
            try:
                parsed = datetime.fromisoformat(str(timestamp))
                day = date_in_timezone(parsed, data_timezone, session_timezone).isoformat()
            except ValueError:
                day = now_naive(session_timezone).date().isoformat()
        return "|".join(
            [
                day,
                str(signal.get("symbol") or ""),
                str(signal.get("timeframe") or ""),
                str(signal.get("direction") or ""),
                str(signal.get("execution_type") or ""),
            ]
        )

    def _already_consumed(self, signal: dict[str, Any]) -> bool:
        if not self.one_trade_per_symbol_per_day:
            return False
        key = self._state_key(signal)
        if key in self.state.get("consumed", {}):
            return True
        symbol = str(signal.get("symbol") or "")
        positions = self.client.open_positions(symbol, magic=ORB_MAGIC)
        pending = self.client.pending_orders(symbol, magic=ORB_MAGIC)
        return bool(positions or pending)

    def _mark_consumed(self, signal: dict[str, Any], status: str, payload: dict[str, Any]) -> None:
        self.state.setdefault("consumed", {})[self._state_key(signal)] = {
            "status": status,
            "symbol": signal.get("symbol"),
            "timeframe": signal.get("timeframe"),
            "direction": signal.get("direction"),
            "execution_type": signal.get("execution_type"),
            "timestamp": signal.get("timestamp"),
            "payload": payload,
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
        _write_state(self.state)

    def _load_candles(self, symbol: str, now: datetime):
        start = now - timedelta(days=self.lookback_days)
        return self.client.fetch_candles(symbol, self.timeframe, start, now)

    def _order_comment(self, signal: dict[str, Any]) -> str:
        direction = str(signal.get("direction") or "")[:1]
        score = int(signal.get("setup_score") or 0)
        return f"ORB {direction} S{score} {self.timeframe}"[:31]

    def _prepare_signal(self, signal: dict[str, Any], now: datetime) -> tuple[dict[str, Any] | None, list[str]]:
        blocks: list[str] = []
        quote = self.client.current_quote(str(signal.get("symbol") or ""))
        spread = self.client.spread_check(
            signal,
            max_spread_risk_percent=self.max_spread_risk_percent,
            max_spread_points=self.max_spread_points,
            quote=quote,
        )
        if not spread.get("ok"):
            blocks.extend(str(reason) for reason in (spread.get("reasons") or [spread.get("message")]))
            return None, blocks

        sizing = self.client.risk_based_lot(
            signal,
            self.risk_percent,
            fallback_balance=self.config.starting_balance,
            require_account_balance=self.live_trading and (self.place_trades or self.place_pending),
            quote=quote,
        )
        if not sizing.get("ok"):
            blocks.append(str(sizing.get("message") or "ORB lot sizing failed."))
            return None, blocks

        is_pending = str(signal.get("execution_type") or "").upper() == "PENDING"
        will_send = self.live_trading and ((is_pending and self.place_pending) or ((not is_pending) and self.place_trades))
        order = self.client.prepare_order(signal, lot=float(sizing["lot"]), live_trading=will_send)
        order["magic"] = ORB_MAGIC
        order["comment"] = self._order_comment(signal)
        order["lot_sizing"] = sizing
        order["spread_check"] = spread
        order["spread_limits"] = {
            "max_spread_risk_percent": self.max_spread_risk_percent,
            "max_spread_points": self.max_spread_points,
        }
        if is_pending and self.pending_expiry_minutes > 0:
            order["expires_at"] = now + timedelta(minutes=self.pending_expiry_minutes)
        return order, blocks

    def run_once(self) -> dict[str, Any]:
        now = now_naive(self.settings.data_timezone)
        self._heartbeat("scanning")
        prepared: list[dict[str, Any]] = []
        placements: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []

        for symbol in self.symbols:
            candles = self._load_candles(symbol, now)
            if candles is None or len(candles) < 120:
                errors.append({"symbol": symbol, "error": f"Not enough {self.timeframe} candles."})
                continue

            signals: list[dict[str, Any]] = []
            confirmed = confirmed_orb_signal(candles, symbol, self.timeframe, self.settings, now=now)
            if confirmed:
                signals.append(confirmed)
            elif self.prepare_pending:
                signals.extend(pending_orb_signals(candles, symbol, self.timeframe, self.settings, now=now))

            for signal in signals:
                if self._already_consumed(signal):
                    blocked.append({"symbol": symbol, "direction": signal.get("direction"), "reason": "ORB signal already consumed today."})
                    continue
                order, reasons = self._prepare_signal(signal, now)
                if not order:
                    blocked.append({"symbol": symbol, "direction": signal.get("direction"), "reasons": reasons})
                    continue
                ticket = {
                    "created_at": now.isoformat(timespec="seconds"),
                    "signal": signal,
                    "order": order,
                }
                prepared.append(ticket)
                self._log_event("orb_order_prepared", ticket=ticket)

                placement: dict[str, Any] | None = None
                if order.get("live_trading"):
                    if str(signal.get("execution_type") or "").upper() == "PENDING":
                        placement = self.client.place_pending_order(order)
                    else:
                        placement = self.client.place_order(order)
                    placements.append({"signal": signal, "placement": placement})
                    self._log_event("orb_order_sent", signal=signal, placement=placement)
                    if placement.get("placed"):
                        self._mark_consumed(signal, "placed", placement)
                else:
                    self._mark_consumed(signal, "prepared", {"message": "Prepared only; ORB live placement is disabled."})

        payload = {
            "checked_at": now.isoformat(timespec="seconds"),
            "symbols": list(self.symbols),
            "timeframe": self.timeframe,
            "settings": self.settings.__dict__,
            "live_trading": self.live_trading,
            "place_trades": self.place_trades,
            "prepare_pending": self.prepare_pending,
            "place_pending": self.place_pending,
            "risk_percent": self.risk_percent,
            "prepared_count": len(prepared),
            "placement_count": len(placements),
            "blocked": blocked,
            "errors": errors,
            "prepared": prepared,
            "placements": placements,
            "state_path": str(STATE_PATH),
            "events_path": str(EVENTS_PATH),
        }
        _write_json(LATEST_PATH, payload)
        self._heartbeat("waiting")
        return payload

    def run_forever(self) -> None:
        print("ORB worker started.")
        print(f"Symbols: {', '.join(self.symbols)} | timeframe: {self.timeframe}")
        print(
            f"Session {self.settings.session_start}-{self.settings.session_end} {self.settings.session_timezone}, "
            f"range={self.settings.range_minutes}m, RR={self.settings.reward_risk:g}."
        )
        print(f"Candle/data timezone: {self.settings.data_timezone}.")
        print(f"Live trading: {self.live_trading}; ORB_PLACE_TRADES: {self.place_trades}; ORB_PLACE_PENDING: {self.place_pending}")
        print(f"State: {STATE_PATH}")
        print("Press Ctrl+C to stop.")
        while True:
            payload = self.run_once()
            print(
                f"[{payload['checked_at']}] prepared={payload['prepared_count']} "
                f"sent={payload['placement_count']} blocked={len(payload['blocked'])} errors={len(payload['errors'])}"
            )
            time.sleep(self.interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="ORB sub-bot.")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
    args = parser.parse_args()

    lock = ORBLock(LOCK_PATH)
    lock.acquire()
    bot = ORBBot()
    if args.once:
        print(json.dumps(bot.run_once(), indent=2, default=str))
        return
    bot.run_forever()


if __name__ == "__main__":
    main()
