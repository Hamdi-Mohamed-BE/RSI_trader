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


def _signal_log_fields(signal: dict[str, Any]) -> dict[str, Any]:
    return {
        "symbol": signal.get("symbol"),
        "timeframe": signal.get("timeframe"),
        "direction": signal.get("direction"),
        "setup_score": signal.get("setup_score"),
        "setup_grade": signal.get("setup_grade"),
        "key_level": signal.get("key_level"),
        "entry_model": signal.get("entry_model"),
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
    return "|".join(
        [
            str(signal.get("symbol")),
            str(signal.get("timeframe")),
            str(signal.get("direction")),
            str(signal.get("key_level")),
            str(signal.get("entry_model")),
            str(signal.get("last_candle_time") or signal.get("timestamp")),
        ]
    )


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
        self.one_position_per_symbol = _env_bool("AUTO_ONE_POSITION_PER_SYMBOL", True)
        self.trade_protection_enabled = _env_bool("AUTO_PROTECT_OPEN_TRADES", True)
        self.protection_final_rr = max(1.0, _env_float("AUTO_PROTECTION_FINAL_RR", self.config.min_risk_reward))
        self.symbol_result_cooldown_minutes = _env_int("AUTO_SYMBOL_RESULT_COOLDOWN_MINUTES", 60)
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

    def _mark_consumed(self, signal: dict[str, Any], ticket: dict[str, Any], placement: dict[str, Any] | None) -> None:
        consumed = self.trade_state.setdefault("consumed_signals", {})
        payload = {
            "status": "placed",
            "created_at": ticket.get("created_at"),
            "symbol": signal.get("symbol"),
            "broker_symbol": signal.get("broker_symbol"),
            "timeframe": signal.get("timeframe"),
            "direction": signal.get("direction"),
            "key_level": signal.get("key_level"),
            "entry_model": signal.get("entry_model"),
            "last_candle_time": signal.get("last_candle_time") or signal.get("timestamp"),
            "placement": placement,
        }
        consumed[_signal_key(signal)] = payload
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

    def _print_cycle_details(self, payload: dict[str, Any]) -> None:
        if self.log_detail_limit <= 0:
            return

        for ticket in payload.get("prepared", [])[: self.log_detail_limit]:
            signal = ticket.get("signal") or {}
            order = ticket.get("order") or {}
            sizing = order.get("lot_sizing") or {}
            spread_check = order.get("spread_check") or {}
            spread_text = ""
            if spread_check:
                spread_text = (
                    f" spread={float(spread_check.get('spread_risk_percent') or 0.0):.1f}%"
                    f"/{float(spread_check.get('spread_points') or 0.0):.1f}pts"
                )
            print(
                "  prepared "
                f"{signal.get('symbol')} {signal.get('timeframe')} {signal.get('direction')} "
                f"S{signal.get('setup_score')} lot={order.get('lot')} "
                f"risk={self._money(sizing.get('estimated_risk'))}/{self._money(sizing.get('risk_budget'))}"
                f"{spread_text} "
                f"comment='{order.get('comment')}'"
            )

        for ticket in payload.get("placed", [])[: self.log_detail_limit]:
            signal = ticket.get("signal") or {}
            order = ticket.get("order") or {}
            placement = ticket.get("placement") or {}
            result = placement.get("result") or {}
            status = "placed" if placement.get("placed") else "failed"
            broker_ticket = result.get("order") or result.get("deal") or "-"
            quote = placement.get("quote") or {}
            spread_text = ""
            if quote:
                spread_text = f" spread={float(quote.get('spread_points') or 0.0):.1f}pts"
            print(
                "  mt5 "
                f"{status} {signal.get('symbol')} {signal.get('timeframe')} "
                f"S{signal.get('setup_score')} lot={order.get('lot')} ticket={broker_ticket}{spread_text} "
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

    def _set_symbol_cooldown(self, symbol: str, now: datetime, event: dict[str, Any]) -> dict[str, Any] | None:
        if self.symbol_result_cooldown_minutes <= 0:
            return None
        until = now + timedelta(minutes=self.symbol_result_cooldown_minutes)
        payload = {
            "status": "active",
            "symbol": symbol,
            "until": until.isoformat(timespec="seconds"),
            "created_at": now.isoformat(timespec="seconds"),
            "minutes": self.symbol_result_cooldown_minutes,
            "outcome": event.get("outcome"),
            "ticket": event.get("ticket"),
            "exit_reason": event.get("exit_reason"),
        }
        self.trade_state.setdefault("symbol_cooldowns", {})[symbol] = payload
        return payload

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
        event.update(
            {
                "status": "closed_processed",
                "outcome": outcome,
                "exit_reason": history.get("exit_reason"),
                "exit_price": history.get("exit_price"),
                "profit": history.get("profit"),
                "closed_at": history.get("closed_at"),
            }
        )

        if outcome in {"TP", "SL"}:
            cooldown = self._set_symbol_cooldown(str(state.get("symbol")), now, event)
            event["cooldown"] = cooldown
            event["status"] = "closed_symbol_cooldown_started" if cooldown else "closed_no_cooldown_configured"
        elif outcome == "BE":
            event["status"] = "closed_break_even_no_cooldown"
        else:
            event["status"] = "closed_other_no_cooldown"

        state["status"] = "closed_processed"
        state["closed_outcome"] = outcome
        state["closed_at"] = history.get("closed_at") or now.isoformat(timespec="seconds")
        state["exit_price"] = history.get("exit_price")
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
        active_symbol_cooldowns = self.active_symbol_cooldowns(now)
        scan = scan_market(
            symbols=TRADE_SYMBOLS,
            timeframes=self.timeframes,
            min_score=self.config.min_setup_score,
            min_rr=self.config.min_risk_reward,
        )
        _log_automation_event(
            "scan_summary",
            now,
            symbols=list(TRADE_SYMBOLS),
            timeframes=list(self.timeframes),
            allowed_count=len(scan.get("allowed", [])),
            near_miss_count=len(scan.get("near_misses", [])),
            active_symbol_cooldown_count=len(active_symbol_cooldowns),
            protection_action_count=len(protection_actions),
            live_trading=self.config.live_trading,
            auto_place_trades=self.auto_place_trades,
            max_lot_risk_pct=self.max_lot_risk_pct,
            max_spread_risk_percent=self.max_spread_risk_percent,
            max_spread_points=self.max_spread_points,
        )
        prepared: list[dict[str, Any]] = []
        placed: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []

        for signal in scan["allowed"]:
            key = _signal_key(signal)
            legacy_key = _legacy_signal_key(signal)
            open_positions_any = self.client.open_positions(signal["symbol"])
            open_positions_magic = self.client.open_positions(signal["symbol"], magic=MAGIC_NUMBER)
            symbol_cooldown = active_symbol_cooldowns.get(signal["symbol"])
            block_reasons: list[str] = []

            if symbol_cooldown:
                block_reasons.append(
                    f"Symbol is cooling down after {symbol_cooldown.get('outcome')} until {symbol_cooldown.get('until')}."
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
                    self._mark_consumed(signal, ticket, placement)

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
            "one_position_per_symbol": self.one_position_per_symbol,
            "symbol_result_cooldown_minutes": self.symbol_result_cooldown_minutes,
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
            "blocked_count": len(blocked),
            "prepared": prepared,
            "placed": placed,
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
        print(f"One position per symbol: {self.one_position_per_symbol}")
        print(f"Trade protection: {self.trade_protection_enabled}; final RR: 1:{self.protection_final_rr:g}")
        print(f"TP/SL symbol cooldown: {self.symbol_result_cooldown_minutes} minutes; BE exits do not cool down.")
        print(f"Detail log: {AUTOMATION_EVENTS_PATH}")
        print(f"Console detail limit per cycle: {self.log_detail_limit}")
        print("Press Ctrl+C to stop.")
        while True:
            payload = self.run_once()
            allowed = len(payload["scan"]["allowed"])
            near = len(payload["scan"]["near_misses"])
            prepared = payload["prepared_count"]
            protected = payload["trade_protection"]["modified_count"]
            cooldowns = len(payload["active_symbol_cooldowns"])
            print(
                f"[{payload['checked_at']}] A+={allowed} near={near} prepared={prepared} placed={payload['placed_count']} blocked={payload['blocked_count']} protected={protected} cooldowns={cooldowns}"
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
