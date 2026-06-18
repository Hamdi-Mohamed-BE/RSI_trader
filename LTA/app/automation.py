from __future__ import annotations

import argparse
import atexit
from datetime import datetime, timedelta
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .config import REPORTS_DIR, load_config
from .models import TRADE_SYMBOLS
from .mt5_client import MT5Client
from .scanner import DEFAULT_SCAN_TIMEFRAMES, scan_market


AUTOMATION_DIR = REPORTS_DIR / "automation"
LATEST_SCAN_PATH = AUTOMATION_DIR / "latest_scan.json"
PREPARED_ORDERS_PATH = AUTOMATION_DIR / "prepared_orders.jsonl"
PLACED_ORDERS_PATH = AUTOMATION_DIR / "placed_orders.jsonl"
SEEN_SIGNALS_PATH = AUTOMATION_DIR / "seen_signals.json"
TRADE_STATE_PATH = AUTOMATION_DIR / "trade_state.json"
BLOCKED_ORDERS_PATH = AUTOMATION_DIR / "blocked_orders.jsonl"
AUTOMATION_EVENTS_PATH = AUTOMATION_DIR / "automation_events.jsonl"
PROTECTION_LOG_PATH = AUTOMATION_DIR / "trade_protection.jsonl"
CLOSED_TRADE_EVENTS_PATH = AUTOMATION_DIR / "closed_trade_events.jsonl"
INSTANCE_LOCK_PATH = AUTOMATION_DIR / "automation.lock"
HEARTBEAT_PATH = AUTOMATION_DIR / "automation_heartbeat.json"
MAGIC_NUMBER = 27032024


def _env_bool(name: str, default: bool) -> bool:
    import os

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    import os

    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    import os

    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    import os

    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def _parse_time_minutes(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        hour_text, minute_text = value.strip().split(":", 1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (ValueError, AttributeError):
        return default
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return default
    return hour * 60 + minute


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _heartbeat_is_fresh(max_age_seconds: int) -> bool:
    if not HEARTBEAT_PATH.exists():
        return False
    age = time.time() - HEARTBEAT_PATH.stat().st_mtime
    return age <= max_age_seconds


def _write_heartbeat(status: str = "running") -> None:
    _write_json(
        HEARTBEAT_PATH,
        {
            "pid": os.getpid(),
            "status": status,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        },
    )


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
    return records


def _signal_log_fields(signal: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": signal.get("symbol"),
        "timeframe": signal.get("timeframe"),
        "direction": signal.get("direction"),
        "setup_score": signal.get("setup_score"),
        "setup_grade": signal.get("setup_grade"),
        "key_level": signal.get("key_level"),
        "entry_model": signal.get("entry_model"),
        "execution_type": signal.get("execution_type"),
        "pending_order_type": signal.get("pending_order_type"),
        "trigger_price": signal.get("trigger_price"),
        "preplace_valid_if": signal.get("preplace_valid_if"),
        "entry": signal.get("entry"),
        "stop_loss": signal.get("stop_loss"),
        "take_profit": signal.get("take_profit"),
        "risk_reward": signal.get("risk_reward"),
        "last_candle_time": signal.get("last_candle_time") or signal.get("timestamp"),
    }


def _log_automation_event(event: str, now: datetime, signal: dict[str, Any] | None = None, **extra: Any) -> None:
    payload: dict[str, Any] = {
        "created_at": now.isoformat(timespec="seconds"),
        "event": event,
    }
    if signal:
        payload.update(_signal_log_fields(signal))
    payload.update(extra)
    _append_jsonl(AUTOMATION_EVENTS_PATH, payload)


def _read_seen_signals() -> dict[str, str]:
    if not SEEN_SIGNALS_PATH.exists():
        return {}
    try:
        data = json.loads(SEEN_SIGNALS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _write_seen_signals(seen: dict[str, str]) -> None:
    SEEN_SIGNALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEEN_SIGNALS_PATH.write_text(json.dumps(seen, indent=2), encoding="utf-8")


def _default_trade_state() -> dict[str, Any]:
    return {
        "consumed_signals": {},
        "protected_positions": {},
        "closed_positions": {},
        "symbol_cooldowns": {},
        "last_updated": None,
    }


def _read_trade_state() -> dict[str, Any]:
    if not TRADE_STATE_PATH.exists():
        return _default_trade_state()
    try:
        data = json.loads(TRADE_STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_trade_state()
        data.setdefault("consumed_signals", {})
        data.setdefault("protected_positions", {})
        data.setdefault("closed_positions", {})
        data.setdefault("symbol_cooldowns", {})
        return data
    except json.JSONDecodeError:
        return _default_trade_state()


def _write_trade_state(state: dict[str, Any]) -> None:
    state["last_updated"] = datetime.now().isoformat(timespec="seconds")
    TRADE_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRADE_STATE_PATH.write_text(json.dumps(state, indent=2, default=str), encoding="utf-8")


def _signal_key(signal: dict[str, Any]) -> str:
    parts = [
        str(signal.get("symbol")),
        str(signal.get("timeframe")),
        str(signal.get("direction")),
        str(signal.get("key_level")),
        str(signal.get("entry_model")),
        str(signal.get("last_candle_time") or signal.get("timestamp")),
    ]
    if str(signal.get("execution_type") or "").upper() == "PENDING":
        parts.extend([str(signal.get("pending_order_type")), str(signal.get("trigger_price") or signal.get("entry"))])
    return "|".join(parts)


def _legacy_signal_key(signal: dict[str, Any]) -> str:
    return "|".join(
        [
            str(signal.get("symbol")),
            str(signal.get("timeframe")),
            str(signal.get("direction")),
            str(signal.get("key_level")),
            str(signal.get("entry_model")),
        ]
    )


def _migrate_placed_orders_to_state(state: dict[str, Any]) -> None:
    consumed = state.setdefault("consumed_signals", {})
    if not PLACED_ORDERS_PATH.exists():
        return
    with PLACED_ORDERS_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            signal = payload.get("signal") or {}
            if not signal:
                continue
            for key in (_signal_key(signal), _legacy_signal_key(signal)):
                consumed.setdefault(
                    key,
                    {
                        "status": "placed_before_state_tracking",
                        "created_at": payload.get("created_at"),
                        "symbol": signal.get("symbol"),
                        "timeframe": signal.get("timeframe"),
                        "direction": signal.get("direction"),
                        "key_level": signal.get("key_level"),
                        "last_candle_time": signal.get("last_candle_time") or signal.get("timestamp"),
                    },
                )


def _pid_is_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _other_automation_pids() -> list[int]:
    command = (
        "Get-CimInstance Win32_Process | "
        "Where-Object { $_.ExecutablePath -like '*python.exe' -and $_.CommandLine -like '*-m app.automation*' } | "
        "Select-Object -ExpandProperty ProcessId"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except Exception:
        return []
    current_pid = os.getpid()
    pids: list[int] = []
    for line in result.stdout.splitlines():
        try:
            pid = int(line.strip())
        except ValueError:
            continue
        if pid != current_pid:
            pids.append(pid)
    return pids


class SingleInstanceLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stale_seconds = _env_int("AUTO_LOCK_STALE_SECONDS", 180)
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                pid = int(data.get("pid") or 0)
            except (json.JSONDecodeError, ValueError):
                pid = 0
            if _pid_is_running(pid) or _heartbeat_is_fresh(stale_seconds):
                raise RuntimeError("Automation worker is already running or heartbeat is still fresh.")
            self.path.unlink(missing_ok=True)

        self.path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": datetime.now().isoformat(timespec="seconds")}, indent=2),
            encoding="utf-8",
        )
        self.acquired = True
        atexit.register(self.release)

    def release(self) -> None:
        if self.acquired:
            _write_heartbeat("stopped")
            self.path.unlink(missing_ok=True)
            self.acquired = False


class TradeAutomation:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = MT5Client()
        self.timeframes = _env_list("AUTO_SCAN_TIMEFRAMES", DEFAULT_SCAN_TIMEFRAMES)
        self.interval_seconds = _env_int("AUTO_SCAN_INTERVAL_SECONDS", 60)
        self.cooldown_minutes = _env_int("AUTO_SIGNAL_COOLDOWN_MINUTES", 120)
        self.auto_place_trades = _env_bool("AUTO_PLACE_TRADES", False)
        self.auto_preplace_orders = _env_bool("AUTO_PREPLACE_ORDERS", False)
        self.preplace_min_score = max(1, min(100, _env_int("AUTO_PREPLACE_MIN_SCORE", 85)))
        self.preplace_expiry_minutes = max(0, _env_int("AUTO_PREPLACE_EXPIRY_MINUTES", 240))
        self.one_pending_per_symbol = _env_bool("AUTO_ONE_PENDING_PER_SYMBOL", True)
        self.one_position_per_symbol = _env_bool("AUTO_ONE_POSITION_PER_SYMBOL", True)
        self.trade_protection_enabled = _env_bool("AUTO_PROTECT_OPEN_TRADES", True)
        self.protection_final_rr = max(1.0, _env_float("AUTO_PROTECTION_FINAL_RR", self.config.min_risk_reward))
        self.max_consecutive_losses = max(0, _env_int("AUTO_MAX_CONSECUTIVE_LOSSES", 2))
        self.symbol_max_losses_per_day = max(0, _env_int("AUTO_SYMBOL_MAX_LOSSES_PER_DAY", 1))
        self.symbol_max_daily_loss_r = max(0.0, _env_float("AUTO_SYMBOL_MAX_DAILY_LOSS_R", 1.0))
        self.symbol_loss_lockout_rest_of_session = _env_bool("AUTO_SYMBOL_LOSS_LOCKOUT_REST_OF_SESSION", True)
        self.strict_session_start = _parse_time_minutes(os.getenv("AUTO_STRICT_SESSION_START"), 10 * 60)
        self.strict_session_end = _parse_time_minutes(os.getenv("AUTO_STRICT_SESSION_END"), 13 * 60)
        self.strict_session_min_score = max(1, min(100, _env_int("AUTO_STRICT_SESSION_MIN_SCORE", 95)))
        self.strict_session_preplace_min_score = max(
            1,
            min(100, _env_int("AUTO_STRICT_SESSION_PREPLACE_MIN_SCORE", 90)),
        )
        self.strict_session_require_internal_break = _env_bool("AUTO_STRICT_SESSION_REQUIRE_INTERNAL_BREAK", True)
        self.symbol_activity_cooldown_minutes = _env_int(
            "AUTO_SYMBOL_ACTIVITY_COOLDOWN_MINUTES",
            _env_int("AUTO_SYMBOL_RESULT_COOLDOWN_MINUTES", 60),
        )
        self.max_lot_risk_pct = max(0.0, float(self.config.max_lot_risk_pct))
        self.max_spread_risk_percent = max(0.0, float(self.config.max_spread_risk_percent))
        self.max_spread_points = max(0.0, float(self.config.max_spread_points))
        self.log_detail_limit = max(0, _env_int("AUTO_LOG_DETAIL_LIMIT", 8))
        self.seen: dict[str, datetime] = {
            key: datetime.fromisoformat(value) for key, value in _read_seen_signals().items()
        }
        self.trade_state = _read_trade_state()
        _migrate_placed_orders_to_state(self.trade_state)
        _write_trade_state(self.trade_state)

    def _cooldown_active(self, key: str, now: datetime) -> bool:
        seen_at = self.seen.get(key)
        if not seen_at:
            return False
        return now - seen_at < timedelta(minutes=self.cooldown_minutes)

    def _mark_consumed(
        self,
        signal: dict[str, Any],
        ticket: dict[str, Any],
        placement: dict[str, Any] | None,
        status: str = "placed",
        include_legacy: bool = True,
    ) -> None:
        consumed = self.trade_state.setdefault("consumed_signals", {})
        payload = {
            "status": status,
            "created_at": ticket.get("created_at"),
            "symbol": signal.get("symbol"),
            "broker_symbol": signal.get("broker_symbol"),
            "timeframe": signal.get("timeframe"),
            "direction": signal.get("direction"),
            "key_level": signal.get("key_level"),
            "entry_model": signal.get("entry_model"),
            "execution_type": signal.get("execution_type"),
            "pending_order_type": signal.get("pending_order_type"),
            "trigger_price": signal.get("trigger_price"),
            "last_candle_time": signal.get("last_candle_time") or signal.get("timestamp"),
            "placement": placement,
        }
        consumed[_signal_key(signal)] = payload
        if include_legacy:
            consumed[_legacy_signal_key(signal)] = payload
        _write_trade_state(self.trade_state)

    @staticmethod
    def _position_direction(position: dict[str, Any]) -> str:
        return "SELL" if int(position.get("type") or 0) == 1 else "BUY"

    @staticmethod
    def _level_at_r(entry: float, risk: float, direction: str, r_multiple: float) -> float:
        if direction == "BUY":
            return entry + risk * r_multiple
        return entry - risk * r_multiple

    @staticmethod
    def _stage_is_hit(market_price: float, target: float, direction: str) -> bool:
        if direction == "BUY":
            return market_price >= target
        return market_price <= target

    @staticmethod
    def _stop_is_better(current_stop: float, desired_stop: float, direction: str) -> bool:
        if current_stop <= 0:
            return True
        if direction == "BUY":
            return desired_stop > current_stop
        return desired_stop < current_stop

    @staticmethod
    def _base_symbol_from_broker_symbol(broker_symbol: str) -> str:
        upper = broker_symbol.upper()
        for symbol in TRADE_SYMBOLS:
            if symbol in upper:
                return symbol
        return broker_symbol

    @staticmethod
    def _money(value: Any) -> str:
        try:
            return f"${float(value):.2f}"
        except (TypeError, ValueError):
            return "$?"

    @staticmethod
    def _day_bounds(now: datetime) -> tuple[datetime, datetime]:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return start, start + timedelta(days=1)

    @staticmethod
    def _minutes_of_day(value: datetime) -> int:
        return value.hour * 60 + value.minute

    @staticmethod
    def _float_or_none(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _signal_time(self, signal: dict[str, Any], now: datetime) -> datetime:
        return (
            _parse_datetime(signal.get("last_candle_time"))
            or _parse_datetime(signal.get("timestamp"))
            or now
        )

    def _in_strict_session_window(self, signal: dict[str, Any], now: datetime) -> bool:
        if self.strict_session_start == self.strict_session_end:
            return False
        minutes = self._minutes_of_day(self._signal_time(signal, now))
        if self.strict_session_start < self.strict_session_end:
            return self.strict_session_start <= minutes < self.strict_session_end
        return minutes >= self.strict_session_start or minutes < self.strict_session_end

    def _strict_session_reasons(self, signal: dict[str, Any], now: datetime, pending: bool = False) -> list[str]:
        if not self._in_strict_session_window(signal, now):
            return []

        reasons: list[str] = []
        score = int(signal.get("setup_score") or 0)
        min_score = self.strict_session_preplace_min_score if pending else self.strict_session_min_score
        if score < min_score:
            reasons.append(
                f"Strict 10:00-13:00 filter requires score >= {min_score}; setup score is {score}."
            )

        model = str(signal.get("entry_model") or "")
        if self.strict_session_require_internal_break and "Internal Structure" not in model:
            reasons.append("Strict 10:00-13:00 filter requires internal-structure confirmation.")

        if pending and str(signal.get("pending_order_type") or "").upper() not in {"BUY_STOP", "SELL_STOP"}:
            reasons.append("Strict 10:00-13:00 filter allows only break-stop pending orders, not retest limits.")
        return reasons

    def _session_end(self, value: datetime) -> datetime:
        minutes = self._minutes_of_day(value)
        day_start = value.replace(hour=0, minute=0, second=0, microsecond=0)
        if 8 * 60 <= minutes < 17 * 60:
            return day_start + timedelta(hours=17)
        if 3 * 60 <= minutes < 8 * 60:
            return day_start + timedelta(hours=8)
        if minutes >= 19 * 60:
            return day_start + timedelta(days=1, hours=2)
        if minutes < 2 * 60:
            return day_start + timedelta(hours=2)
        return day_start + timedelta(days=1)

    def _closed_r_multiple(self, state: dict[str, Any], history: dict[str, Any]) -> float | None:
        entry = self._float_or_none(state.get("entry"))
        initial_stop = self._float_or_none(state.get("initial_stop"))
        exit_price = self._float_or_none(history.get("exit_price"))
        direction = str(state.get("direction") or "").upper()
        if entry is None or initial_stop is None or exit_price is None or initial_stop <= 0:
            return None
        risk = abs(entry - initial_stop)
        if risk <= 0:
            return None
        if direction == "BUY":
            return (exit_price - entry) / risk
        if direction == "SELL":
            return (entry - exit_price) / risk
        return None

    @staticmethod
    def _event_is_loss(event: dict[str, Any]) -> bool:
        outcome = str(event.get("outcome") or "").upper()
        if outcome == "BE":
            return False
        profit = TradeAutomation._float_or_none(event.get("profit"))
        if profit is not None and profit < 0:
            return True
        return outcome == "SL"

    def daily_bot_stats(self, now: datetime) -> dict[str, Any]:
        start, end = self._day_bounds(now)
        placed_today = 0
        for record in _read_jsonl(PLACED_ORDERS_PATH):
            created_at = _parse_datetime(record.get("created_at"))
            if not created_at or created_at < start or created_at >= end:
                continue
            placement = record.get("placement") or {}
            if placement.get("placed"):
                placed_today += 1

        closed_today: list[dict[str, Any]] = []
        symbols: dict[str, dict[str, Any]] = {}
        for event in self.trade_state.get("closed_positions", {}).values():
            if not isinstance(event, dict):
                continue
            event_at = (
                _parse_datetime(event.get("closed_at"))
                or _parse_datetime(event.get("event_at"))
                or _parse_datetime(event.get("checked_at"))
            )
            if not event_at or event_at < start or event_at >= end:
                continue
            closed_today.append({**event, "_event_at": event_at.isoformat(timespec="seconds")})
            symbol = str(event.get("symbol") or event.get("broker_symbol") or "").upper()
            if not symbol:
                continue
            item = symbols.setdefault(
                symbol,
                {
                    "symbol": symbol,
                    "closed": 0,
                    "losses": 0,
                    "wins": 0,
                    "break_evens": 0,
                    "net_profit": 0.0,
                    "net_r": 0.0,
                },
            )
            item["closed"] += 1
            profit = self._float_or_none(event.get("profit")) or 0.0
            item["net_profit"] += profit
            r_multiple = self._float_or_none(event.get("r_multiple"))
            if r_multiple is None:
                r_multiple = -1.0 if self._event_is_loss(event) else 0.0
            item["net_r"] += r_multiple
            if self._event_is_loss(event):
                item["losses"] += 1
            elif str(event.get("outcome") or "").upper() == "BE":
                item["break_evens"] += 1
            else:
                item["wins"] += 1

        closed_today.sort(key=lambda item: item.get("_event_at") or "")
        consecutive_losses = 0
        for event in reversed(closed_today):
            if self._event_is_loss(event):
                consecutive_losses += 1
                continue
            break

        return {
            "date": start.date().isoformat(),
            "placed_today": placed_today,
            "closed_today": len(closed_today),
            "consecutive_losses": consecutive_losses,
            "symbols": symbols,
            "max_trades_per_day": self.config.max_trades_per_day,
            "max_consecutive_losses": self.max_consecutive_losses,
        }

    def account_circuit_breaker_reasons(self, stats: dict[str, Any], cycle_commitments: int = 0) -> list[str]:
        reasons: list[str] = []
        projected_trades = int(stats.get("placed_today") or 0) + int(cycle_commitments)
        if self.config.max_trades_per_day > 0 and projected_trades >= self.config.max_trades_per_day:
            reasons.append(
                f"Daily bot trade cap reached: {projected_trades}/{self.config.max_trades_per_day} total placements today."
            )
        if self.max_consecutive_losses > 0 and int(stats.get("consecutive_losses") or 0) >= self.max_consecutive_losses:
            reasons.append(
                f"Whole-bot kill switch active after {stats.get('consecutive_losses')} consecutive losses."
            )
        return reasons

    def symbol_day_block_reasons(self, signal: dict[str, Any], stats: dict[str, Any]) -> list[str]:
        symbol = str(signal.get("symbol") or "").upper()
        symbol_stats = (stats.get("symbols") or {}).get(symbol) or {}
        reasons: list[str] = []
        losses = int(symbol_stats.get("losses") or 0)
        net_r = float(symbol_stats.get("net_r") or 0.0)
        if self.symbol_max_losses_per_day > 0 and losses >= self.symbol_max_losses_per_day:
            reasons.append(f"{symbol} is locked for the day after {losses} failed A+ setup.")
        if self.symbol_max_daily_loss_r > 0 and net_r <= -self.symbol_max_daily_loss_r:
            reasons.append(f"{symbol} is locked for the day after reaching {net_r:.2f}R.")
        return reasons

    def _print_cycle_details(self, payload: dict[str, Any]) -> None:
        if self.log_detail_limit <= 0:
            return

        for ticket in payload.get("prepared", [])[: self.log_detail_limit]:
            signal = ticket.get("signal") or {}
            order = ticket.get("order") or {}
            sizing = order.get("lot_sizing") or {}
            spread_check = order.get("spread_check") or {}
            mode = "pending" if order.get("execution_type") == "PENDING" else "prepared"
            trigger_text = ""
            if order.get("execution_type") == "PENDING":
                trigger_text = f" {order.get('pending_order_type')}@{order.get('trigger_price')}"
            spread_text = ""
            if spread_check:
                spread_text = (
                    f" spread={float(spread_check.get('spread_risk_percent') or 0.0):.1f}%"
                    f"/{float(spread_check.get('spread_points') or 0.0):.1f}pts"
                )
            print(
                f"  {mode} "
                f"{signal.get('symbol')} {signal.get('timeframe')} {signal.get('direction')} "
                f"S{signal.get('setup_score')} lot={order.get('lot')}{trigger_text} "
                f"risk={self._money(sizing.get('estimated_risk'))}/{self._money(sizing.get('risk_budget'))}"
                f"{spread_text} "
                f"comment='{order.get('comment')}'"
            )

        for ticket in payload.get("placed", [])[: self.log_detail_limit]:
            signal = ticket.get("signal") or {}
            order = ticket.get("order") or {}
            placement = ticket.get("placement") or {}
            result = placement.get("result") or {}
            order_kind = "pending" if order.get("execution_type") == "PENDING" else "mt5"
            status = "placed" if placement.get("placed") else "failed"
            broker_ticket = result.get("order") or result.get("deal") or "-"
            quote = placement.get("quote") or {}
            spread_text = ""
            if quote:
                spread_text = f" spread={float(quote.get('spread_points') or 0.0):.1f}pts"
            trigger_text = ""
            if order.get("execution_type") == "PENDING":
                trigger_text = f" {order.get('pending_order_type')}@{order.get('trigger_price')}"
            print(
                f"  {order_kind} "
                f"{status} {signal.get('symbol')} {signal.get('timeframe')} "
                f"S{signal.get('setup_score')} lot={order.get('lot')}{trigger_text} ticket={broker_ticket}{spread_text} "
                f"msg='{placement.get('message')}'"
            )

        for ticket in payload.get("blocked", [])[: self.log_detail_limit]:
            signal = ticket.get("signal") or {}
            reasons = ticket.get("reasons") or []
            reason = str(reasons[0]) if reasons else str(ticket.get("status"))
            print(
                "  blocked "
                f"{signal.get('symbol')} {signal.get('timeframe')} {signal.get('direction')} "
                f"S{signal.get('setup_score')}: {reason[:160]}"
            )

        protection = payload.get("trade_protection") or {}
        modified_actions = [
            action
            for action in protection.get("actions", [])
            if action.get("status") == "modified"
        ][: self.log_detail_limit]
        for action in modified_actions:
            print(
                "  protected "
                f"{action.get('symbol')} ticket={action.get('ticket')} "
                f"stage=TP{action.get('hit_stage')} sl->{action.get('desired_stop')}"
            )

    def active_symbol_cooldowns(self, now: datetime) -> dict[str, dict[str, Any]]:
        cooldowns = self.trade_state.setdefault("symbol_cooldowns", {})
        active: dict[str, dict[str, Any]] = {}
        changed = False
        for symbol, payload in list(cooldowns.items()):
            until = _parse_datetime(payload.get("until"))
            if until and now < until:
                active[symbol] = payload
                continue
            if payload.get("status") != "expired":
                payload["status"] = "expired"
                payload["expired_at"] = now.isoformat(timespec="seconds")
                changed = True
        if changed:
            _write_trade_state(self.trade_state)
        return active

    def _set_symbol_cooldown_until(
        self,
        symbol: str,
        now: datetime,
        event: dict[str, Any],
        until: datetime,
        minutes: int | None = None,
    ) -> dict[str, Any] | None:
        if not symbol or until <= now:
            return None
        event_at = _parse_datetime(
            event.get("event_at")
            or event.get("closed_at")
            or event.get("opened_at")
            or event.get("created_at")
            or now
        ) or now
        event_type = str(event.get("event_type") or event.get("event") or "activity")
        payload = {
            "status": "active",
            "symbol": symbol,
            "until": until.isoformat(timespec="seconds"),
            "created_at": now.isoformat(timespec="seconds"),
            "minutes": minutes,
            "event_type": event_type,
            "event_at": event_at.isoformat(timespec="seconds"),
            "source": event.get("source"),
            "outcome": event.get("outcome"),
            "ticket": event.get("ticket"),
            "position_id": event.get("position_id"),
            "broker_symbol": event.get("broker_symbol"),
            "exit_reason": event.get("exit_reason"),
            "profit": event.get("profit"),
        }
        self.trade_state.setdefault("symbol_cooldowns", {})[symbol] = payload
        return payload

    def _set_symbol_cooldown(self, symbol: str, now: datetime, event: dict[str, Any]) -> dict[str, Any] | None:
        if self.symbol_activity_cooldown_minutes <= 0:
            return None
        event_at = _parse_datetime(
            event.get("event_at")
            or event.get("closed_at")
            or event.get("opened_at")
            or event.get("created_at")
            or now
        ) or now
        until = event_at + timedelta(minutes=self.symbol_activity_cooldown_minutes)
        return self._set_symbol_cooldown_until(
            symbol,
            now,
            event,
            until,
            minutes=self.symbol_activity_cooldown_minutes,
        )

    def refresh_symbol_activity_cooldowns(self, now: datetime) -> list[dict[str, Any]]:
        if self.symbol_activity_cooldown_minutes <= 0:
            return []

        activities = self.client.recent_trade_activity(
            TRADE_SYMBOLS,
            lookback_minutes=self.symbol_activity_cooldown_minutes,
        )
        updates: list[dict[str, Any]] = []
        cooldowns = self.trade_state.setdefault("symbol_cooldowns", {})
        changed = False
        for symbol, activity in activities.items():
            before = dict(cooldowns.get(symbol) or {})
            cooldown = self._set_symbol_cooldown(symbol, now, activity)
            if not cooldown:
                continue
            if (
                self.symbol_loss_lockout_rest_of_session
                and str(activity.get("event_type") or "").lower() == "closed"
                and self._float_or_none(activity.get("profit")) is not None
                and float(activity.get("profit") or 0.0) < 0
            ):
                activity_at = _parse_datetime(activity.get("event_at")) or now
                session_until = self._session_end(activity_at)
                current_until = _parse_datetime(cooldown.get("until"))
                if current_until and current_until > session_until:
                    session_until = current_until
                cooldown = self._set_symbol_cooldown_until(
                    symbol,
                    now,
                    {**activity, "event_type": "loss_session_lockout"},
                    session_until,
                ) or cooldown
            was_changed = (
                before.get("until") != cooldown.get("until")
                or before.get("event_at") != cooldown.get("event_at")
                or before.get("event_type") != cooldown.get("event_type")
                or before.get("ticket") != cooldown.get("ticket")
                or before.get("position_id") != cooldown.get("position_id")
            )
            if was_changed:
                changed = True
                update = {
                    "symbol": symbol,
                    "activity": activity,
                    "cooldown": cooldown,
                }
                updates.append(update)
                _log_automation_event(
                    "symbol_activity_cooldown",
                    now,
                    symbol=symbol,
                    event_type=activity.get("event_type"),
                    event_at=activity.get("event_at"),
                    source=activity.get("source"),
                    ticket=activity.get("ticket"),
                    position_id=activity.get("position_id"),
                    broker_symbol=activity.get("broker_symbol"),
                    cooldown=cooldown,
                )
        if changed:
            _write_trade_state(self.trade_state)
        return updates

    @staticmethod
    def _is_break_even_exit(state: dict[str, Any], exit_price: float) -> bool:
        entry = float(state.get("entry") or 0.0)
        initial_stop = float(state.get("initial_stop") or 0.0)
        if entry <= 0 or exit_price <= 0:
            return False
        risk = abs(entry - initial_stop) if initial_stop > 0 else 0.0
        tolerance = max(risk * 0.05, abs(entry) * 0.00002, 1e-9)
        return abs(exit_price - entry) <= tolerance

    def _classify_closed_position(self, state: dict[str, Any], history: dict[str, Any]) -> str:
        exit_price = float(history.get("exit_price") or 0.0)
        exit_reason = str(history.get("exit_reason") or "OTHER")
        if self._is_break_even_exit(state, exit_price):
            return "BE"
        if exit_reason in {"TP", "SL"}:
            return exit_reason

        direction = str(state.get("direction") or "")
        take_profit = float(state.get("take_profit") or 0.0)
        if take_profit > 0 and exit_price > 0:
            if direction == "BUY" and exit_price >= take_profit:
                return "TP"
            if direction == "SELL" and exit_price <= take_profit:
                return "TP"
        return "OTHER"

    def _process_closed_position(self, ticket: str, state: dict[str, Any], now: datetime) -> dict[str, Any] | None:
        closed_positions = self.trade_state.setdefault("closed_positions", {})
        if ticket in closed_positions or state.get("status") == "closed_processed":
            return None

        history = self.client.closed_position_deal(int(ticket))
        event = {
            "checked_at": now.isoformat(timespec="seconds"),
            "ticket": ticket,
            "symbol": state.get("symbol"),
            "broker_symbol": state.get("broker_symbol"),
            "status": "closed_pending_history",
            "history": history,
        }
        if not history.get("found"):
            state["status"] = "closed_pending_history"
            state["last_seen_at"] = now.isoformat(timespec="seconds")
            return event

        outcome = self._classify_closed_position(state, history)
        r_multiple = self._closed_r_multiple(state, history)
        event.update(
            {
                "status": "closed_processed",
                "event_type": "closed",
                "event_at": history.get("closed_at") or now.isoformat(timespec="seconds"),
                "outcome": outcome,
                "exit_reason": history.get("exit_reason"),
                "exit_price": history.get("exit_price"),
                "profit": history.get("profit"),
                "r_multiple": round(r_multiple, 3) if r_multiple is not None else None,
                "closed_at": history.get("closed_at"),
            }
        )

        cooldown = self._set_symbol_cooldown(str(state.get("symbol")), now, event)
        if self.symbol_loss_lockout_rest_of_session and self._event_is_loss(event):
            event_at = _parse_datetime(event.get("event_at")) or now
            session_until = self._session_end(event_at)
            current_until = _parse_datetime((cooldown or {}).get("until"))
            if current_until and current_until > session_until:
                session_until = current_until
            loss_cooldown = self._set_symbol_cooldown_until(
                str(state.get("symbol")),
                now,
                {**event, "event_type": "loss_session_lockout"},
                session_until,
            )
            if loss_cooldown:
                cooldown = loss_cooldown
        event["cooldown"] = cooldown
        event["status"] = "closed_symbol_activity_cooldown_started" if cooldown else "closed_no_activity_cooldown"

        state["status"] = "closed_processed"
        state["closed_outcome"] = outcome
        state["closed_at"] = history.get("closed_at") or now.isoformat(timespec="seconds")
        state["exit_price"] = history.get("exit_price")
        state["r_multiple"] = event.get("r_multiple")
        closed_positions[ticket] = event
        _append_jsonl(CLOSED_TRADE_EVENTS_PATH, event)
        return event

    def _position_state(self, ticket: str, position: dict[str, Any]) -> dict[str, Any]:
        protected = self.trade_state.setdefault("protected_positions", {})
        existing = protected.get(ticket, {})
        broker_symbol = str(position.get("symbol") or existing.get("broker_symbol") or "")
        direction = self._position_direction(position)
        entry = float(position.get("price_open") or existing.get("entry") or 0.0)
        current_stop = float(position.get("sl") or 0.0)
        take_profit = float(position.get("tp") or 0.0)
        initial_stop = float(existing.get("initial_stop") or current_stop or 0.0)

        if initial_stop <= 0 and take_profit > 0 and entry > 0:
            one_r = abs(take_profit - entry) / self.protection_final_rr
            initial_stop = entry - one_r if direction == "BUY" else entry + one_r

        payload = {
            **existing,
            "ticket": ticket,
            "broker_symbol": broker_symbol,
            "symbol": existing.get("symbol") or self._base_symbol_from_broker_symbol(broker_symbol),
            "direction": direction,
            "entry": entry,
            "initial_stop": initial_stop,
            "take_profit": take_profit,
            "status": "open",
            "last_seen_at": datetime.now().isoformat(timespec="seconds"),
        }
        protected[ticket] = payload
        return payload

    def protect_open_positions(self, now: datetime) -> list[dict[str, Any]]:
        if not self.trade_protection_enabled:
            return []

        actions: list[dict[str, Any]] = []
        positions = self.client.open_positions(magic=MAGIC_NUMBER)
        protected_positions = self.trade_state.setdefault("protected_positions", {})
        open_tickets = {str(position.get("ticket")) for position in positions if position.get("ticket")}

        for stale_ticket in set(protected_positions) - open_tickets:
            state = protected_positions[stale_ticket]
            if state.get("status") == "closed_processed":
                continue
            closed_event = self._process_closed_position(stale_ticket, state, now)
            if closed_event:
                actions.append(closed_event)
                _log_automation_event(
                    "position_closed",
                    now,
                    ticket=stale_ticket,
                    symbol=closed_event.get("symbol"),
                    broker_symbol=closed_event.get("broker_symbol"),
                    status=closed_event.get("status"),
                    outcome=closed_event.get("outcome"),
                    exit_reason=closed_event.get("exit_reason"),
                    exit_price=closed_event.get("exit_price"),
                    profit=closed_event.get("profit"),
                    cooldown=closed_event.get("cooldown"),
                )

        for position in positions:
            ticket = str(position.get("ticket") or "")
            if not ticket:
                continue

            state = self._position_state(ticket, position)
            direction = state["direction"]
            broker_symbol = state["broker_symbol"]
            entry = float(state["entry"])
            initial_stop = float(state["initial_stop"])
            take_profit = float(state["take_profit"] or position.get("tp") or 0.0)
            current_stop = float(position.get("sl") or 0.0)
            risk = abs(entry - initial_stop)

            action = {
                "checked_at": now.isoformat(timespec="seconds"),
                "ticket": ticket,
                "symbol": state["symbol"],
                "broker_symbol": broker_symbol,
                "direction": direction,
                "entry": entry,
                "initial_stop": initial_stop,
                "current_stop": current_stop,
                "take_profit": take_profit,
                "status": "waiting",
                "stage": int(state.get("stage") or 0),
            }

            if entry <= 0 or initial_stop <= 0 or risk <= 0:
                action["status"] = "skipped_missing_initial_risk"
                actions.append(action)
                continue

            quote = self.client.current_quote(broker_symbol) or self.client.current_quote(str(state["symbol"]))
            if not quote:
                action["status"] = "skipped_no_quote"
                actions.append(action)
                continue

            market_price = float(quote["bid"] if direction == "BUY" else quote["ask"])
            hit_stage = 0
            final_stage = max(1, int(round(self.protection_final_rr)))
            stage_targets = {
                stage: self._level_at_r(entry, risk, direction, float(stage))
                for stage in range(1, final_stage + 1)
            }
            for stage, target in stage_targets.items():
                if self._stage_is_hit(market_price, target, direction):
                    hit_stage = stage

            action["market_price"] = market_price
            action["targets"] = {f"tp{stage}": target for stage, target in stage_targets.items()}
            for stage, target in stage_targets.items():
                action[f"tp{stage}"] = target
            action["hit_stage"] = hit_stage

            if hit_stage <= 0:
                state["stage"] = max(int(state.get("stage") or 0), 0)
                state["status"] = "waiting_for_tp1"
                actions.append(action)
                continue

            if hit_stage == 1:
                desired_stop = entry
                action["rule"] = "tp1_hit_move_sl_to_break_even"
            else:
                desired_stop = stage_targets[hit_stage - 1]
                action["rule"] = f"tp{hit_stage}_hit_trail_sl_to_tp{hit_stage - 1}"

            desired_stop = self.client.normalize_price(broker_symbol, desired_stop)
            action["desired_stop"] = desired_stop

            if not self._stop_is_better(current_stop, desired_stop, direction):
                action["status"] = "already_protected"
                state["stage"] = max(int(state.get("stage") or 0), hit_stage)
                state["status"] = action["status"]
                state["last_stop"] = current_stop
                actions.append(action)
                continue

            if (direction == "BUY" and desired_stop >= market_price) or (direction == "SELL" and desired_stop <= market_price):
                action["status"] = "skipped_stop_too_close_to_market"
                actions.append(action)
                continue

            result = self.client.modify_position_sl_tp(
                ticket=int(ticket),
                symbol=broker_symbol,
                stop_loss=desired_stop,
                take_profit=take_profit if take_profit > 0 else None,
            )
            action["modify_result"] = result
            if result.get("modified"):
                action["status"] = "modified"
                state["stage"] = max(int(state.get("stage") or 0), hit_stage)
                state["status"] = action["status"]
                state["last_stop"] = desired_stop
                state["last_modified_at"] = now.isoformat(timespec="seconds")
            else:
                action["status"] = "modify_failed"
                state["status"] = action["status"]

            actions.append(action)
            _append_jsonl(PROTECTION_LOG_PATH, action)
            if result.get("modified"):
                _log_automation_event(
                    "protection_modified",
                    now,
                    ticket=ticket,
                    symbol=state["symbol"],
                    broker_symbol=broker_symbol,
                    direction=direction,
                    stage=hit_stage,
                    old_stop=current_stop,
                    new_stop=desired_stop,
                    take_profit=take_profit,
                    market_price=market_price,
                )

        _write_trade_state(self.trade_state)
        return actions

    def run_once(self) -> dict[str, Any]:
        now = datetime.now()
        _write_heartbeat("scanning")
        protection_actions = self.protect_open_positions(now)
        activity_cooldown_updates = self.refresh_symbol_activity_cooldowns(now)
        active_symbol_cooldowns = self.active_symbol_cooldowns(now)
        daily_bot_stats = self.daily_bot_stats(now)
        scan = scan_market(
            symbols=TRADE_SYMBOLS,
            timeframes=self.timeframes,
            min_score=self.config.min_setup_score,
            preplace_min_score=self.preplace_min_score,
            min_rr=self.config.min_risk_reward,
        )
        _log_automation_event(
            "scan_summary",
            now,
            symbols=list(TRADE_SYMBOLS),
            timeframes=list(self.timeframes),
            allowed_count=len(scan.get("allowed", [])),
            preplace_count=len(scan.get("preplace", [])),
            near_miss_count=len(scan.get("near_misses", [])),
            active_symbol_cooldown_count=len(active_symbol_cooldowns),
            activity_cooldown_update_count=len(activity_cooldown_updates),
            protection_action_count=len(protection_actions),
            live_trading=self.config.live_trading,
            auto_place_trades=self.auto_place_trades,
            auto_preplace_orders=self.auto_preplace_orders,
            preplace_min_score=self.preplace_min_score,
            preplace_expiry_minutes=self.preplace_expiry_minutes,
            max_lot_risk_pct=self.max_lot_risk_pct,
            max_spread_risk_percent=self.max_spread_risk_percent,
            max_spread_points=self.max_spread_points,
            daily_bot_stats=daily_bot_stats,
        )
        prepared: list[dict[str, Any]] = []
        placed: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        pending_prepared: list[dict[str, Any]] = []
        pending_placed: list[dict[str, Any]] = []
        cycle_trade_commitments = 0

        for signal in scan["allowed"]:
            key = _signal_key(signal)
            legacy_key = _legacy_signal_key(signal)
            open_positions_any = self.client.open_positions(signal["symbol"])
            open_positions_magic = self.client.open_positions(signal["symbol"], magic=MAGIC_NUMBER)
            symbol_cooldown = active_symbol_cooldowns.get(signal["symbol"])
            block_reasons: list[str] = []

            block_reasons.extend(self.account_circuit_breaker_reasons(daily_bot_stats, cycle_trade_commitments))
            block_reasons.extend(self.symbol_day_block_reasons(signal, daily_bot_stats))
            block_reasons.extend(self._strict_session_reasons(signal, now, pending=False))
            if symbol_cooldown:
                activity_label = symbol_cooldown.get("event_type") or symbol_cooldown.get("outcome") or "activity"
                activity_time = symbol_cooldown.get("event_at") or symbol_cooldown.get("created_at")
                block_reasons.append(
                    f"Symbol is cooling down after recent {activity_label} at {activity_time} until {symbol_cooldown.get('until')}."
                )
            if key in self.trade_state.get("consumed_signals", {}) or legacy_key in self.trade_state.get("consumed_signals", {}):
                block_reasons.append("This signal was already placed and saved in trade_state.json.")
            if self._cooldown_active(key, now) or self._cooldown_active(legacy_key, now):
                block_reasons.append("Signal is still inside the cooldown window.")
            if self.one_position_per_symbol and open_positions_any:
                block_reasons.append("An open position already exists on this symbol.")
            elif open_positions_magic:
                block_reasons.append("An open LTA automation position already exists on this symbol.")

            if block_reasons:
                blocked_ticket = {
                    "created_at": now.isoformat(timespec="seconds"),
                    "status": "blocked_duplicate_or_open_position",
                    "duplicate_key": key,
                    "legacy_key": legacy_key,
                    "setup_score": signal.get("setup_score"),
                    "setup_grade": signal.get("setup_grade"),
                    "signal": signal,
                    "reasons": block_reasons,
                    "safety": {
                        "open_positions_same_symbol_any": len(open_positions_any),
                        "open_positions_same_symbol_magic": len(open_positions_magic),
                        "one_position_per_symbol": self.one_position_per_symbol,
                        "symbol_cooldown": symbol_cooldown,
                        "daily_bot_stats": daily_bot_stats,
                    },
                }
                blocked.append(blocked_ticket)
                _append_jsonl(BLOCKED_ORDERS_PATH, blocked_ticket)
                _log_automation_event(
                    "signal_blocked",
                    now,
                    signal,
                    status=blocked_ticket["status"],
                    reasons=block_reasons,
                    safety=blocked_ticket["safety"],
                )
                continue

            will_send_to_mt5 = self.config.live_trading and self.auto_place_trades
            spread_check = self.client.spread_check(
                signal,
                max_spread_risk_percent=self.max_spread_risk_percent,
                max_spread_points=self.max_spread_points,
            )
            if not spread_check.get("ok"):
                spread_reasons = spread_check.get("reasons") or [spread_check.get("message") or "Spread check failed."]
                blocked_ticket = {
                    "created_at": now.isoformat(timespec="seconds"),
                    "status": "blocked_spread",
                    "duplicate_key": key,
                    "legacy_key": legacy_key,
                    "setup_score": signal.get("setup_score"),
                    "setup_grade": signal.get("setup_grade"),
                    "signal": signal,
                    "reasons": [str(reason) for reason in spread_reasons],
                    "spread_check": spread_check,
                    "safety": {
                        "live_trading": self.config.live_trading,
                        "auto_place_trades": self.auto_place_trades,
                        "will_send_to_mt5": will_send_to_mt5,
                        "max_spread_risk_percent": self.max_spread_risk_percent,
                        "max_spread_points": self.max_spread_points,
                        "open_positions_same_symbol_any": len(open_positions_any),
                        "open_positions_same_symbol_magic": len(open_positions_magic),
                        "one_position_per_symbol": self.one_position_per_symbol,
                        "symbol_cooldown": symbol_cooldown,
                        "daily_bot_stats": daily_bot_stats,
                    },
                }
                blocked.append(blocked_ticket)
                _append_jsonl(BLOCKED_ORDERS_PATH, blocked_ticket)
                _log_automation_event(
                    "signal_blocked",
                    now,
                    signal,
                    status=blocked_ticket["status"],
                    reasons=blocked_ticket["reasons"],
                    spread_check=spread_check,
                    safety=blocked_ticket["safety"],
                )
                continue

            lot_sizing = self.client.risk_based_lot(
                signal,
                risk_percent=self.max_lot_risk_pct,
                fallback_balance=self.config.starting_balance,
                require_account_balance=will_send_to_mt5,
                quote=spread_check.get("quote"),
            )
            if not lot_sizing.get("ok"):
                blocked_ticket = {
                    "created_at": now.isoformat(timespec="seconds"),
                    "status": "blocked_lot_sizing",
                    "duplicate_key": key,
                    "legacy_key": legacy_key,
                    "setup_score": signal.get("setup_score"),
                    "setup_grade": signal.get("setup_grade"),
                    "signal": signal,
                    "reasons": [str(lot_sizing.get("message") or "Risk-based lot sizing failed.")],
                    "lot_sizing": lot_sizing,
                    "safety": {
                        "live_trading": self.config.live_trading,
                        "auto_place_trades": self.auto_place_trades,
                        "will_send_to_mt5": will_send_to_mt5,
                        "max_lot_risk_pct": self.max_lot_risk_pct,
                        "open_positions_same_symbol_any": len(open_positions_any),
                        "open_positions_same_symbol_magic": len(open_positions_magic),
                        "one_position_per_symbol": self.one_position_per_symbol,
                        "symbol_cooldown": symbol_cooldown,
                        "daily_bot_stats": daily_bot_stats,
                    },
                }
                blocked.append(blocked_ticket)
                _append_jsonl(BLOCKED_ORDERS_PATH, blocked_ticket)
                _log_automation_event(
                    "signal_blocked",
                    now,
                    signal,
                    status=blocked_ticket["status"],
                    reasons=blocked_ticket["reasons"],
                    lot_sizing=lot_sizing,
                    safety=blocked_ticket["safety"],
                )
                continue

            lot = float(lot_sizing["lot"])
            order = self.client.prepare_order(
                signal,
                lot=lot,
                live_trading=will_send_to_mt5,
            )
            order["lot_sizing"] = lot_sizing
            order["spread_check"] = spread_check
            order["spread_limits"] = {
                "max_spread_risk_percent": self.max_spread_risk_percent,
                "max_spread_points": self.max_spread_points,
            }
            ticket = {
                "created_at": now.isoformat(timespec="seconds"),
                "status": "prepared",
                "duplicate_key": key,
                "legacy_key": legacy_key,
                "setup_score": signal.get("setup_score"),
                "setup_grade": signal.get("setup_grade"),
                "signal": signal,
                "order": order,
                "safety": {
                    "live_trading": self.config.live_trading,
                    "auto_place_trades": self.auto_place_trades,
                    "open_positions_same_symbol_any": len(open_positions_any),
                    "open_positions_same_symbol_magic": len(open_positions_magic),
                    "one_position_per_symbol": self.one_position_per_symbol,
                    "will_send_to_mt5": will_send_to_mt5,
                    "max_lot_risk_pct": self.max_lot_risk_pct,
                    "max_spread_risk_percent": self.max_spread_risk_percent,
                    "max_spread_points": self.max_spread_points,
                },
            }
            prepared.append(ticket)
            _append_jsonl(PREPARED_ORDERS_PATH, ticket)
            _log_automation_event(
                "order_prepared",
                now,
                signal,
                broker_symbol=order.get("broker_symbol"),
                lot=order.get("lot"),
                comment=order.get("comment"),
                will_send_to_mt5=will_send_to_mt5,
                lot_sizing=lot_sizing,
                spread_check=spread_check,
            )
            self.seen[key] = now
            self.seen[legacy_key] = now
            _write_seen_signals({item_key: item_value.isoformat() for item_key, item_value in self.seen.items()})

            if will_send_to_mt5:
                placement = self.client.place_order(order)
                placed_payload = {**ticket, "status": "sent_to_mt5", "placement": placement}
                if placement.get("placed"):
                    activity = {
                        "event_type": "opened",
                        "event_at": now.isoformat(timespec="seconds"),
                        "source": "order_placement",
                        "ticket": (placement.get("result") or {}).get("order") or (placement.get("result") or {}).get("deal"),
                        "broker_symbol": order.get("broker_symbol"),
                    }
                    cooldown = self._set_symbol_cooldown(signal["symbol"], now, activity)
                    if cooldown:
                        active_symbol_cooldowns[signal["symbol"]] = cooldown
                        placed_payload["activity_cooldown"] = cooldown
                        _log_automation_event(
                            "symbol_activity_cooldown",
                            now,
                            signal,
                            symbol=signal["symbol"],
                            event_type=activity["event_type"],
                            event_at=activity["event_at"],
                            source=activity["source"],
                            ticket=activity["ticket"],
                            broker_symbol=activity["broker_symbol"],
                            cooldown=cooldown,
                        )
                placed.append(placed_payload)
                _append_jsonl(PLACED_ORDERS_PATH, placed_payload)
                result = placement.get("result") or {}
                _log_automation_event(
                    "order_sent_to_mt5",
                    now,
                    signal,
                    broker_symbol=order.get("broker_symbol"),
                    lot=order.get("lot"),
                    comment=order.get("comment"),
                    placed=placement.get("placed"),
                    message=placement.get("message"),
                    retcode=result.get("retcode"),
                    order_ticket=result.get("order") or result.get("deal"),
                    request=placement.get("request"),
                    quote=placement.get("quote"),
                    spread_check=placement.get("spread_check") or order.get("spread_check"),
                )
                if placement.get("placed"):
                    cycle_trade_commitments += 1
                    self._mark_consumed(signal, ticket, placement)

        if self.auto_preplace_orders:
            for signal in scan.get("preplace", []):
                key = _signal_key(signal)
                legacy_key = _legacy_signal_key(signal)
                open_positions_any = self.client.open_positions(signal["symbol"])
                open_positions_magic = self.client.open_positions(signal["symbol"], magic=MAGIC_NUMBER)
                pending_orders_magic = self.client.pending_orders(signal["symbol"], magic=MAGIC_NUMBER)
                symbol_cooldown = active_symbol_cooldowns.get(signal["symbol"])
                block_reasons: list[str] = []

                block_reasons.extend(self.account_circuit_breaker_reasons(daily_bot_stats, cycle_trade_commitments))
                block_reasons.extend(self.symbol_day_block_reasons(signal, daily_bot_stats))
                block_reasons.extend(self._strict_session_reasons(signal, now, pending=True))
                if symbol_cooldown:
                    activity_label = symbol_cooldown.get("event_type") or symbol_cooldown.get("outcome") or "activity"
                    activity_time = symbol_cooldown.get("event_at") or symbol_cooldown.get("created_at")
                    block_reasons.append(
                        f"Symbol is cooling down after recent {activity_label} at {activity_time} until {symbol_cooldown.get('until')}."
                    )
                if key in self.trade_state.get("consumed_signals", {}) or legacy_key in self.trade_state.get("consumed_signals", {}):
                    block_reasons.append("This pending signal was already placed and saved in trade_state.json.")
                if self._cooldown_active(key, now) or self._cooldown_active(legacy_key, now):
                    block_reasons.append("Pending signal is still inside the cooldown window.")
                if self.one_position_per_symbol and open_positions_any:
                    block_reasons.append("An open position already exists on this symbol.")
                elif open_positions_magic:
                    block_reasons.append("An open LTA automation position already exists on this symbol.")
                if self.one_pending_per_symbol and pending_orders_magic:
                    block_reasons.append("An LTA pending order already exists on this symbol.")

                if block_reasons:
                    blocked_ticket = {
                        "created_at": now.isoformat(timespec="seconds"),
                        "status": "blocked_pending_duplicate_or_open_position",
                        "duplicate_key": key,
                        "legacy_key": legacy_key,
                        "setup_score": signal.get("setup_score"),
                        "setup_grade": signal.get("setup_grade"),
                        "signal": signal,
                        "reasons": block_reasons,
                        "safety": {
                            "open_positions_same_symbol_any": len(open_positions_any),
                            "open_positions_same_symbol_magic": len(open_positions_magic),
                            "pending_orders_same_symbol_magic": len(pending_orders_magic),
                            "one_position_per_symbol": self.one_position_per_symbol,
                            "one_pending_per_symbol": self.one_pending_per_symbol,
                            "symbol_cooldown": symbol_cooldown,
                            "daily_bot_stats": daily_bot_stats,
                        },
                    }
                    blocked.append(blocked_ticket)
                    _append_jsonl(BLOCKED_ORDERS_PATH, blocked_ticket)
                    _log_automation_event(
                        "pending_signal_blocked",
                        now,
                        signal,
                        status=blocked_ticket["status"],
                        reasons=block_reasons,
                        safety=blocked_ticket["safety"],
                    )
                    continue

                will_send_pending_to_mt5 = self.config.live_trading and self.auto_place_trades and self.auto_preplace_orders
                spread_check = self.client.spread_check(
                    signal,
                    max_spread_risk_percent=self.max_spread_risk_percent,
                    max_spread_points=self.max_spread_points,
                )
                if not spread_check.get("ok"):
                    spread_reasons = spread_check.get("reasons") or [spread_check.get("message") or "Spread check failed."]
                    blocked_ticket = {
                        "created_at": now.isoformat(timespec="seconds"),
                        "status": "blocked_pending_spread",
                        "duplicate_key": key,
                        "legacy_key": legacy_key,
                        "setup_score": signal.get("setup_score"),
                        "setup_grade": signal.get("setup_grade"),
                        "signal": signal,
                        "reasons": [str(reason) for reason in spread_reasons],
                        "spread_check": spread_check,
                        "safety": {
                            "live_trading": self.config.live_trading,
                            "auto_place_trades": self.auto_place_trades,
                            "auto_preplace_orders": self.auto_preplace_orders,
                            "will_send_to_mt5": will_send_pending_to_mt5,
                            "max_spread_risk_percent": self.max_spread_risk_percent,
                            "max_spread_points": self.max_spread_points,
                            "open_positions_same_symbol_any": len(open_positions_any),
                            "open_positions_same_symbol_magic": len(open_positions_magic),
                            "pending_orders_same_symbol_magic": len(pending_orders_magic),
                            "one_position_per_symbol": self.one_position_per_symbol,
                            "one_pending_per_symbol": self.one_pending_per_symbol,
                            "symbol_cooldown": symbol_cooldown,
                            "daily_bot_stats": daily_bot_stats,
                        },
                    }
                    blocked.append(blocked_ticket)
                    _append_jsonl(BLOCKED_ORDERS_PATH, blocked_ticket)
                    _log_automation_event(
                        "pending_signal_blocked",
                        now,
                        signal,
                        status=blocked_ticket["status"],
                        reasons=blocked_ticket["reasons"],
                        spread_check=spread_check,
                        safety=blocked_ticket["safety"],
                    )
                    continue

                lot_sizing = self.client.risk_based_lot(
                    signal,
                    risk_percent=self.max_lot_risk_pct,
                    fallback_balance=self.config.starting_balance,
                    require_account_balance=will_send_pending_to_mt5,
                    quote=spread_check.get("quote"),
                )
                if not lot_sizing.get("ok"):
                    blocked_ticket = {
                        "created_at": now.isoformat(timespec="seconds"),
                        "status": "blocked_pending_lot_sizing",
                        "duplicate_key": key,
                        "legacy_key": legacy_key,
                        "setup_score": signal.get("setup_score"),
                        "setup_grade": signal.get("setup_grade"),
                        "signal": signal,
                        "reasons": [str(lot_sizing.get("message") or "Risk-based lot sizing failed.")],
                        "lot_sizing": lot_sizing,
                        "safety": {
                            "live_trading": self.config.live_trading,
                            "auto_place_trades": self.auto_place_trades,
                            "auto_preplace_orders": self.auto_preplace_orders,
                            "will_send_to_mt5": will_send_pending_to_mt5,
                            "max_lot_risk_pct": self.max_lot_risk_pct,
                            "open_positions_same_symbol_any": len(open_positions_any),
                            "open_positions_same_symbol_magic": len(open_positions_magic),
                            "pending_orders_same_symbol_magic": len(pending_orders_magic),
                            "one_position_per_symbol": self.one_position_per_symbol,
                            "one_pending_per_symbol": self.one_pending_per_symbol,
                            "symbol_cooldown": symbol_cooldown,
                            "daily_bot_stats": daily_bot_stats,
                        },
                    }
                    blocked.append(blocked_ticket)
                    _append_jsonl(BLOCKED_ORDERS_PATH, blocked_ticket)
                    _log_automation_event(
                        "pending_signal_blocked",
                        now,
                        signal,
                        status=blocked_ticket["status"],
                        reasons=blocked_ticket["reasons"],
                        lot_sizing=lot_sizing,
                        safety=blocked_ticket["safety"],
                    )
                    continue

                lot = float(lot_sizing["lot"])
                order = self.client.prepare_order(
                    signal,
                    lot=lot,
                    live_trading=will_send_pending_to_mt5,
                )
                if self.preplace_expiry_minutes > 0:
                    order["expires_at"] = (now + timedelta(minutes=self.preplace_expiry_minutes)).isoformat(timespec="seconds")
                order["lot_sizing"] = lot_sizing
                order["spread_check"] = spread_check
                order["spread_limits"] = {
                    "max_spread_risk_percent": self.max_spread_risk_percent,
                    "max_spread_points": self.max_spread_points,
                }
                ticket = {
                    "created_at": now.isoformat(timespec="seconds"),
                    "status": "pending_prepared",
                    "duplicate_key": key,
                    "legacy_key": legacy_key,
                    "setup_score": signal.get("setup_score"),
                    "setup_grade": signal.get("setup_grade"),
                    "signal": signal,
                    "order": order,
                    "safety": {
                        "live_trading": self.config.live_trading,
                        "auto_place_trades": self.auto_place_trades,
                        "auto_preplace_orders": self.auto_preplace_orders,
                        "open_positions_same_symbol_any": len(open_positions_any),
                        "open_positions_same_symbol_magic": len(open_positions_magic),
                        "pending_orders_same_symbol_magic": len(pending_orders_magic),
                        "one_position_per_symbol": self.one_position_per_symbol,
                        "one_pending_per_symbol": self.one_pending_per_symbol,
                        "will_send_to_mt5": will_send_pending_to_mt5,
                        "max_lot_risk_pct": self.max_lot_risk_pct,
                        "max_spread_risk_percent": self.max_spread_risk_percent,
                        "max_spread_points": self.max_spread_points,
                        "expires_at": order.get("expires_at"),
                    },
                }
                prepared.append(ticket)
                pending_prepared.append(ticket)
                _append_jsonl(PREPARED_ORDERS_PATH, ticket)
                _log_automation_event(
                    "pending_order_prepared",
                    now,
                    signal,
                    broker_symbol=order.get("broker_symbol"),
                    lot=order.get("lot"),
                    pending_order_type=order.get("pending_order_type"),
                    trigger_price=order.get("trigger_price"),
                    expires_at=order.get("expires_at"),
                    comment=order.get("comment"),
                    will_send_to_mt5=will_send_pending_to_mt5,
                    lot_sizing=lot_sizing,
                    spread_check=spread_check,
                )
                self.seen[key] = now
                self.seen[legacy_key] = now
                _write_seen_signals({item_key: item_value.isoformat() for item_key, item_value in self.seen.items()})

                if will_send_pending_to_mt5:
                    placement = self.client.place_pending_order(order)
                    placed_payload = {**ticket, "status": "pending_sent_to_mt5", "placement": placement}
                    placed.append(placed_payload)
                    pending_placed.append(placed_payload)
                    _append_jsonl(PLACED_ORDERS_PATH, placed_payload)
                    result = placement.get("result") or {}
                    _log_automation_event(
                        "pending_order_sent_to_mt5",
                        now,
                        signal,
                        broker_symbol=order.get("broker_symbol"),
                        lot=order.get("lot"),
                        pending_order_type=order.get("pending_order_type"),
                        trigger_price=order.get("trigger_price"),
                        expires_at=order.get("expires_at"),
                        comment=order.get("comment"),
                        placed=placement.get("placed"),
                        message=placement.get("message"),
                        retcode=result.get("retcode"),
                        order_ticket=result.get("order") or result.get("deal"),
                        request=placement.get("request"),
                        quote=placement.get("quote"),
                        spread_check=placement.get("spread_check") or order.get("spread_check"),
                    )
                    if placement.get("placed"):
                        cycle_trade_commitments += 1
                        self._mark_consumed(
                            signal,
                            ticket,
                            placement,
                            status="pending_order_placed",
                            include_legacy=False,
                        )

        daily_bot_stats_payload = {
            **daily_bot_stats,
            "cycle_trade_commitments": cycle_trade_commitments,
            "projected_placed_today": int(daily_bot_stats.get("placed_today") or 0) + cycle_trade_commitments,
        }
        payload = {
            "checked_at": now.isoformat(timespec="seconds"),
            "interval_seconds": self.interval_seconds,
            "timeframes": list(self.timeframes),
            "lot_sizing": {
                "mode": "risk_percent_of_current_balance",
                "max_lot_risk_pct": self.max_lot_risk_pct,
                "env": "MAX_LOT_RISK_PCT",
            },
            "spread_guard": {
                "mode": "ask_bid_spread_vs_stop_distance",
                "max_spread_risk_percent": self.max_spread_risk_percent,
                "max_spread_points": self.max_spread_points,
                "env_risk_percent": "MAX_SPREAD_RISK_PERCENT",
                "env_points": "MAX_SPREAD_POINTS",
            },
            "live_trading": self.config.live_trading,
            "auto_place_trades": self.auto_place_trades,
            "auto_preplace_orders": self.auto_preplace_orders,
            "preplace_min_score": self.preplace_min_score,
            "preplace_expiry_minutes": self.preplace_expiry_minutes,
            "one_position_per_symbol": self.one_position_per_symbol,
            "one_pending_per_symbol": self.one_pending_per_symbol,
            "symbol_activity_cooldown_minutes": self.symbol_activity_cooldown_minutes,
            "process_controls": {
                "max_trades_per_day_total": self.config.max_trades_per_day,
                "max_consecutive_losses": self.max_consecutive_losses,
                "symbol_max_losses_per_day": self.symbol_max_losses_per_day,
                "symbol_max_daily_loss_r": self.symbol_max_daily_loss_r,
                "symbol_loss_lockout_rest_of_session": self.symbol_loss_lockout_rest_of_session,
                "strict_session_start": os.getenv("AUTO_STRICT_SESSION_START", "10:00"),
                "strict_session_end": os.getenv("AUTO_STRICT_SESSION_END", "13:00"),
                "strict_session_min_score": self.strict_session_min_score,
                "strict_session_preplace_min_score": self.strict_session_preplace_min_score,
                "strict_session_require_internal_break": self.strict_session_require_internal_break,
            },
            "daily_bot_stats": daily_bot_stats_payload,
            "activity_cooldown_updates": activity_cooldown_updates,
            "active_symbol_cooldowns": active_symbol_cooldowns,
            "trade_protection": {
                "enabled": self.trade_protection_enabled,
                "final_rr": self.protection_final_rr,
                "checked_count": len(protection_actions),
                "modified_count": sum(1 for action in protection_actions if action.get("status") == "modified"),
                "actions": protection_actions,
            },
            "prepared_count": len(prepared),
            "placed_count": len(placed),
            "pending_prepared_count": len(pending_prepared),
            "pending_placed_count": len(pending_placed),
            "blocked_count": len(blocked),
            "prepared": prepared,
            "placed": placed,
            "pending_prepared": pending_prepared,
            "pending_placed": pending_placed,
            "blocked": blocked,
            "scan": scan,
        }
        _write_json(LATEST_SCAN_PATH, payload)
        _write_heartbeat("waiting")
        return payload

    def run_forever(self) -> None:
        print("LTA automation worker started.")
        print(f"Scanning {', '.join(TRADE_SYMBOLS)} on {', '.join(self.timeframes)} every {self.interval_seconds}s.")
        print(f"Dynamic lot sizing: risk {self.max_lot_risk_pct:g}% of current account balance per trade.")
        print(
            f"Spread guard: max {self.max_spread_risk_percent:g}% of stop distance"
            + (f", max {self.max_spread_points:g} points." if self.max_spread_points > 0 else ".")
        )
        print(f"Live trading: {self.config.live_trading}; AUTO_PLACE_TRADES: {self.auto_place_trades}")
        print(
            f"Pre-place pending orders: {self.auto_preplace_orders}; "
            f"min score: {self.preplace_min_score}; expiry: {self.preplace_expiry_minutes} minutes."
        )
        print(f"One position per symbol: {self.one_position_per_symbol}")
        print(f"One pending order per symbol: {self.one_pending_per_symbol}")
        print(
            f"Daily process controls: max trades={self.config.max_trades_per_day}, "
            f"max loss streak={self.max_consecutive_losses}, "
            f"symbol losses/day={self.symbol_max_losses_per_day}, "
            f"symbol max daily loss={self.symbol_max_daily_loss_r:g}R."
        )
        print(
            f"Strict window: {os.getenv('AUTO_STRICT_SESSION_START', '10:00')}-"
            f"{os.getenv('AUTO_STRICT_SESSION_END', '13:00')} requires "
            f"S{self.strict_session_min_score}+ and internal-structure confirmation."
        )
        print(f"Trade protection: {self.trade_protection_enabled}; final RR: 1:{self.protection_final_rr:g}")
        print(f"Symbol activity cooldown: {self.symbol_activity_cooldown_minutes} minutes after any open or close.")
        print(f"Detail log: {AUTOMATION_EVENTS_PATH}")
        print(f"Console detail limit per cycle: {self.log_detail_limit}")
        print("Press Ctrl+C to stop.")
        while True:
            payload = self.run_once()
            allowed = len(payload["scan"]["allowed"])
            preplace = len(payload["scan"].get("preplace", []))
            near = len(payload["scan"]["near_misses"])
            prepared = payload["prepared_count"]
            pending_prepared = payload["pending_prepared_count"]
            pending_placed = payload["pending_placed_count"]
            protected = payload["trade_protection"]["modified_count"]
            cooldowns = len(payload["active_symbol_cooldowns"])
            daily = payload.get("daily_bot_stats") or {}
            print(
                f"[{payload['checked_at']}] A+={allowed} preplace={preplace} near={near} "
                f"prepared={prepared} placed={payload['placed_count']} "
                f"pending={pending_prepared}/{pending_placed} blocked={payload['blocked_count']} "
                f"protected={protected} cooldowns={cooldowns} "
                f"day_trades={daily.get('projected_placed_today', daily.get('placed_today', 0))}/{self.config.max_trades_per_day} "
                f"loss_streak={daily.get('consecutive_losses', 0)}"
            )
            self._print_cycle_details(payload)
            time.sleep(self.interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="LTA A+ setup automation worker.")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
    args = parser.parse_args()

    lock = SingleInstanceLock(INSTANCE_LOCK_PATH)
    lock.acquire()
    worker = TradeAutomation()
    if args.once:
        payload = worker.run_once()
        print(json.dumps(payload, indent=2, default=str))
        return
    worker.run_forever()


if __name__ == "__main__":
    main()
