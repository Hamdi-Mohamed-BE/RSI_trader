from __future__ import annotations

import argparse
import atexit
from datetime import date, datetime, timedelta
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .adaptive_risk import (
    apply_dynamic_stop,
    dynamic_stop_settings,
    maybe_close_invalid_position,
    smart_exit_settings,
)
from .config import REPORTS_DIR, load_config
from .models import TRADE_SYMBOLS
from .mt5_client import MT5Client
from .orb_strategy import ORBSettings, confirmed_orb_signal, pending_orb_signals
from .pip_utils import parse_pip_size_map, pip_size_for
from .scanner import scan_market
from .session_time import DEFAULT_DATA_TIMEZONE, DEFAULT_SESSION_TIMEZONE, now_naive, parse_hhmm, zone


CHALLENGE_MAGIC = 20052024
CHALLENGE_DIR = REPORTS_DIR / "20pip_challenge"
STATE_PATH = CHALLENGE_DIR / "challenge_state.json"
EVENTS_PATH = CHALLENGE_DIR / "challenge_events.jsonl"
LATEST_PATH = CHALLENGE_DIR / "latest.json"
LOCK_PATH = CHALLENGE_DIR / "challenge.lock"
HEARTBEAT_PATH = CHALLENGE_DIR / "challenge_heartbeat.json"


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


def _symbol_watchlist_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value and value.strip().upper() in {"AUTO_SYMBOLS", "LTA", "LTA_BOT", "MAIN", "MAIN_BOT"}:
        return _env_list("AUTO_SYMBOLS", default)
    symbols = _env_list(name, _env_list("AUTO_SYMBOLS", default))
    return symbols or default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _challenge_signal_quality_sort_key(signal: dict[str, Any]) -> tuple[float, float, float, int]:
    score = _safe_float(signal.get("setup_score"))
    rr = _safe_float(signal.get("risk_reward"))
    orb = signal.get("orb") or {}
    range_atr = _safe_float(orb.get("range_atr"), 999.0)
    range_quality = 100.0 - min(100.0, abs(range_atr - 1.0) * 40.0)
    execution = str(signal.get("execution_type") or "").upper()
    pending_type = str(signal.get("pending_order_type") or "").upper()
    execution_rank = 2 if execution == "MARKET" else 1 if pending_type in {"BUY_STOP", "SELL_STOP"} else 0
    return (score, rr, range_quality, execution_rank)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_lock_payload(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _challenge_process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        ps = (
            f"$p = Get-CimInstance Win32_Process -Filter \"ProcessId = {int(pid)}\" "
            "-ErrorAction SilentlyContinue; "
            "if ($p) { $p.CommandLine }"
        )
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=3,
            )
        except Exception:
            return False
        command_line = (result.stdout or "").lower()
        return "app.challenge_20pip" in command_line or "challenge_20pip.py" in command_line
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _today_key(now: datetime) -> str:
    return now.date().isoformat()


def _default_state(start_balance: float) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "challenge_balance": round(start_balance, 2),
        "level": 1,
        "last_trade_date": None,
        "open_trades": {},
        "closed_trades": {},
        "stats": {
            "wins": 0,
            "losses": 0,
            "break_evens": 0,
            "placements": 0,
        },
    }


def _read_state(start_balance: float) -> dict[str, Any]:
    if not STATE_PATH.exists():
        return _default_state(start_balance)
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return _default_state(start_balance)
    if not isinstance(data, dict):
        return _default_state(start_balance)
    default = _default_state(start_balance)
    for key, value in default.items():
        data.setdefault(key, value)
    data.setdefault("open_trades", {})
    data.setdefault("closed_trades", {})
    data.setdefault("stats", default["stats"])
    for key, value in default["stats"].items():
        data["stats"].setdefault(key, value)
    return data


def _write_state(state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write_json(STATE_PATH, state)


class ChallengeLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            payload = _read_lock_payload(self.path)
            try:
                pid = int(payload.get("pid") or 0)
            except (TypeError, ValueError):
                pid = 0
            if _challenge_process_is_alive(pid):
                raise RuntimeError(
                    f"20 Pip Challenge worker is already running with PID {pid}. "
                    "Close that challenge window or run stop_20pip_challenge.bat first."
                )
            _append_jsonl(
                EVENTS_PATH,
                {
                    "event": "challenge_stale_lock_removed",
                    "removed_at": datetime.now().isoformat(timespec="seconds"),
                    "lock_path": str(self.path),
                    "lock_payload": payload,
                },
            )
            self.path.unlink(missing_ok=True)
            HEARTBEAT_PATH.unlink(missing_ok=True)
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


class TwentyPipChallengeBot:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = MT5Client()
        self.start_balance = max(1.0, _env_float("CHALLENGE20_START_BALANCE", 20.0))
        self.risk_percent = max(0.0, _env_float("CHALLENGE20_RISK_PERCENT", 23.0))
        self.target_percent = max(0.0, _env_float("CHALLENGE20_TARGET_PERCENT", 30.0))
        self.exit_mode = os.getenv("CHALLENGE20_EXIT_MODE", "FIXED_PIPS").strip().upper() or "FIXED_PIPS"
        self.take_profit_pips = max(0.1, _env_float("CHALLENGE20_TAKE_PROFIT_PIPS", 20.0))
        self.stop_loss_pips = max(0.1, _env_float("CHALLENGE20_STOP_LOSS_PIPS", 15.4))
        self.pip_size_overrides = parse_pip_size_map(os.getenv("CHALLENGE20_SYMBOL_PIP_SIZE"))
        self.weekdays_only = _env_bool("CHALLENGE20_WEEKDAYS_ONLY", True)
        self.close_at_session_end = _env_bool("CHALLENGE20_CLOSE_AT_SESSION_END", True)
        self.allowed_weekdays = set(
            _env_list("CHALLENGE20_ALLOWED_WEEKDAYS", ("MON", "TUE", "WED", "THU", "FRI"))
        )
        self.max_levels = max(1, _env_int("CHALLENGE20_LEVELS", 30))
        self.strategy = os.getenv("CHALLENGE20_STRATEGY", "LTA").strip().upper() or "LTA"
        if self.strategy not in {"LTA", "ORB"}:
            self.strategy = "LTA"
        self.interval_seconds = max(10, _env_int("CHALLENGE20_SCAN_INTERVAL_SECONDS", 60))
        self.symbols = _symbol_watchlist_env("CHALLENGE20_SYMBOLS", TRADE_SYMBOLS)
        self.timeframes = _env_list("CHALLENGE20_TIMEFRAMES", ("M5", "M15"))
        self.min_setup_score = max(1, min(100, _env_int("CHALLENGE20_MIN_SETUP_SCORE", 90)))
        self.one_trade_per_day = _env_bool("CHALLENGE20_ONE_TRADE_PER_DAY", True)
        self.live_trading = _env_bool("CHALLENGE20_LIVE_TRADING", False)
        self.place_trades = _env_bool("CHALLENGE20_PLACE_TRADES", False)
        self.max_account_risk_percent = max(0.0, _env_float("CHALLENGE20_MAX_ACCOUNT_RISK_PERCENT", 23.0))
        self.max_spread_risk_percent = max(0.0, _env_float("CHALLENGE20_MAX_SPREAD_RISK_PERCENT", 15.0))
        self.max_spread_points = max(0.0, _env_float("CHALLENGE20_MAX_SPREAD_POINTS", 0.0))
        self.protect_open_trades = _env_bool("CHALLENGE20_PROTECT_OPEN_TRADES", True)
        self.protection_final_rr = max(1.0, _env_float("CHALLENGE20_PROTECTION_FINAL_RR", self.reward_risk or 3.0))
        self.tp1_partial_close_enabled = _env_bool("CHALLENGE20_TP1_PARTIAL_CLOSE", False)
        self.tp1_partial_close_pct = max(0.0, min(100.0, _env_float("CHALLENGE20_TP1_PARTIAL_CLOSE_PCT", 0.0)))
        self.dynamic_stop_settings = dynamic_stop_settings("CHALLENGE20")
        self.smart_exit_settings = smart_exit_settings("CHALLENGE20")
        self.allow_pending = _env_bool("CHALLENGE20_ALLOW_PENDING", False)
        self.orb_timeframe = os.getenv("CHALLENGE20_ORB_TIMEFRAME", os.getenv("ORB_TIMEFRAME", "M15")).strip().upper() or "M15"
        self.orb_lookback_days = max(3, _env_int("CHALLENGE20_ORB_LOOKBACK_DAYS", _env_int("ORB_LOOKBACK_DAYS", 10)))
        self.orb_settings = ORBSettings(
            session_start=os.getenv("CHALLENGE20_ORB_SESSION_START", os.getenv("ORB_SESSION_START", "09:30")),
            session_end=os.getenv("CHALLENGE20_ORB_SESSION_END", os.getenv("ORB_SESSION_END", "16:00")),
            range_minutes=max(1, _env_int("CHALLENGE20_ORB_RANGE_MINUTES", _env_int("ORB_RANGE_MINUTES", 15))),
            reward_risk=max(0.5, self.reward_risk),
            buffer_atr=max(0.0, _env_float("CHALLENGE20_ORB_BREAK_BUFFER_ATR", _env_float("ORB_BREAK_BUFFER_ATR", 0.0))),
            min_range_atr=max(0.0, _env_float("CHALLENGE20_ORB_MIN_RANGE_ATR", _env_float("ORB_MIN_RANGE_ATR", 0.0))),
            max_range_atr=max(0.0, _env_float("CHALLENGE20_ORB_MAX_RANGE_ATR", _env_float("ORB_MAX_RANGE_ATR", 999.0))),
            max_signal_age_minutes=max(1, _env_int("CHALLENGE20_ORB_MAX_SIGNAL_AGE_MINUTES", _env_int("ORB_MAX_SIGNAL_AGE_MINUTES", 30))),
            session_timezone=os.getenv("CHALLENGE20_ORB_SESSION_TIMEZONE", os.getenv("ORB_SESSION_TIMEZONE", os.getenv("MARKET_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE))),
            data_timezone=os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE),
        )
        self.state = _read_state(self.start_balance)
        self.state["level"] = self.level_for_balance(float(self.state.get("challenge_balance") or self.start_balance))
        _write_state(self.state)

    @property
    def reward_risk(self) -> float:
        if self.exit_mode == "FIXED_PIPS":
            return self.take_profit_pips / self.stop_loss_pips
        if self.risk_percent <= 0:
            return 0.0
        return self.target_percent / self.risk_percent

    def target_balance(self) -> float:
        return self.start_balance * ((1 + self.target_percent / 100) ** self.max_levels)

    def level_for_balance(self, balance: float) -> int:
        if balance <= self.start_balance:
            return 1
        level = 1
        target_multiplier = 1 + self.target_percent / 100
        running = self.start_balance
        while level < self.max_levels and balance >= running * target_multiplier:
            running *= target_multiplier
            level += 1
        return level

    def level_target(self, level: int) -> float:
        return self.start_balance * ((1 + self.target_percent / 100) ** level)

    def challenge_balance(self) -> float:
        return float(self.state.get("challenge_balance") or self.start_balance)

    def risk_amount(self) -> float:
        return self.challenge_balance() * (self.risk_percent / 100)

    def account_balance(self) -> float:
        account = self.client.account_info()
        return float((account or {}).get("balance") or 0.0)

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
    def _base_symbol_from_broker_symbol(broker_symbol: str) -> str:
        upper = broker_symbol.upper()
        for symbol in (
            "XAUUSD",
            "XAGUSD",
            "BTCUSD",
            "US30",
            "EURUSD",
            "GBPUSD",
            "USDJPY",
            "USDCHF",
            "USDCAD",
            "AUDUSD",
            "NZDUSD",
        ):
            if symbol in upper:
                return symbol
        return broker_symbol

    def sync_open_positions(self, now: datetime) -> list[dict[str, Any]]:
        positions = self.client.open_positions(magic=CHALLENGE_MAGIC)
        open_tickets = {str(position.get("ticket")) for position in positions if position.get("ticket")}
        open_trades = self.state.setdefault("open_trades", {})
        actions: list[dict[str, Any]] = []

        for position in positions:
            ticket = str(position.get("ticket") or "")
            if not ticket or ticket in open_trades:
                continue
            broker_symbol = str(position.get("symbol") or "")
            direction = "SELL" if int(position.get("type") or 0) == 1 else "BUY"
            entry = float(position.get("price_open") or 0.0)
            stop = float(position.get("sl") or 0.0)
            risk_amount = 0.0
            if entry > 0 and stop > 0:
                estimated = self.client.estimate_trade_risk(
                    self._base_symbol_from_broker_symbol(broker_symbol),
                    direction,
                    float(position.get("volume") or 0.0),
                    entry,
                    stop,
                )
                risk_amount = float(estimated.get("risk") or 0.0)
            open_trades[ticket] = {
                "ticket": ticket,
                "symbol": self._base_symbol_from_broker_symbol(broker_symbol),
                "broker_symbol": broker_symbol,
                "direction": direction,
                "volume": position.get("volume"),
                "entry": entry,
                "initial_stop": stop,
                "stop_loss": stop,
                "take_profit": position.get("tp"),
                "risk_amount": risk_amount,
                "challenge_balance_at_entry": self.challenge_balance(),
                "level": self.state.get("level"),
                "opened_at": datetime.fromtimestamp(int(position.get("time") or 0)).isoformat(timespec="seconds")
                if position.get("time")
                else now.isoformat(timespec="seconds"),
                "status": "open",
            }
            reconciliation = self._reconcile_fixed_position(open_trades[ticket])
            actions.append({"status": "synced_open_position", "ticket": ticket})
            if reconciliation is not None:
                actions[-1]["fixed_pip_reconciliation"] = reconciliation

        for ticket, trade in list(open_trades.items()):
            if ticket in open_tickets:
                continue
            history = self.client.closed_position_deal(int(ticket))
            if not history.get("found"):
                trade["status"] = "closed_pending_history"
                actions.append({"status": "closed_pending_history", "ticket": ticket, "history": history})
                continue

            profit = float(history.get("profit") or 0.0)
            balance = max(0.0, self.challenge_balance() + profit)
            self.state["challenge_balance"] = round(balance, 2)
            self.state["level"] = self.level_for_balance(balance)
            outcome = "BE"
            if profit > 0:
                outcome = "WIN"
                self.state.setdefault("stats", {})["wins"] = int(self.state.setdefault("stats", {}).get("wins") or 0) + 1
            elif profit < 0:
                outcome = "LOSS"
                self.state.setdefault("stats", {})["losses"] = int(self.state.setdefault("stats", {}).get("losses") or 0) + 1
            else:
                self.state.setdefault("stats", {})["break_evens"] = int(self.state.setdefault("stats", {}).get("break_evens") or 0) + 1

            closed = {
                **trade,
                "status": "closed",
                "closed_at": history.get("closed_at") or now.isoformat(timespec="seconds"),
                "outcome": outcome,
                "profit": round(profit, 2),
                "challenge_balance_after": round(balance, 2),
                "history": history,
            }
            self.state.setdefault("closed_trades", {})[ticket] = closed
            del open_trades[ticket]
            self._log_event("position_closed", ticket=ticket, outcome=outcome, profit=profit, balance=balance)
            actions.append({"status": "closed_processed", "ticket": ticket, "outcome": outcome, "profit": profit})

        if self.challenge_balance() <= 0:
            self.state["status"] = "failed"
        elif self.challenge_balance() >= self.target_balance():
            self.state["status"] = "completed"

        _write_state(self.state)
        return actions

    def protect_open_positions(self, now: datetime) -> list[dict[str, Any]]:
        if not self.protect_open_trades:
            return []

        positions = self.client.open_positions(magic=CHALLENGE_MAGIC)
        open_trades = self.state.setdefault("open_trades", {})
        actions: list[dict[str, Any]] = []

        for position in positions:
            ticket = str(position.get("ticket") or "")
            if not ticket:
                continue

            trade = open_trades.setdefault(
                ticket,
                {
                    "ticket": ticket,
                    "symbol": self._base_symbol_from_broker_symbol(str(position.get("symbol") or "")),
                    "broker_symbol": position.get("symbol"),
                    "status": "open",
                },
            )
            broker_symbol = str(position.get("symbol") or trade.get("broker_symbol") or "")
            direction = str(trade.get("direction") or ("SELL" if int(position.get("type") or 0) == 1 else "BUY")).upper()
            entry = float(position.get("price_open") or trade.get("entry") or 0.0)
            initial_stop = float(trade.get("initial_stop") or trade.get("stop_loss") or position.get("sl") or 0.0)
            current_stop = float(position.get("sl") or 0.0)
            take_profit = float(position.get("tp") or trade.get("take_profit") or 0.0)
            risk = abs(entry - initial_stop)

            action: dict[str, Any] = {
                "checked_at": now.isoformat(timespec="seconds"),
                "ticket": ticket,
                "symbol": trade.get("symbol"),
                "broker_symbol": broker_symbol,
                "direction": direction,
                "entry": entry,
                "initial_stop": initial_stop,
                "current_stop": current_stop,
                "take_profit": take_profit,
                "status": "waiting",
                "stage": int(trade.get("stage") or 0),
            }

            if entry <= 0 or initial_stop <= 0 or risk <= 0:
                action["status"] = "skipped_missing_initial_risk"
                actions.append(action)
                continue

            smart_exit = maybe_close_invalid_position(
                self.client,
                position,
                self.smart_exit_settings,
                live_trading=self.live_trading,
                now=now,
                comment="20PIP setup invalidated",
            )
            if smart_exit is not None:
                action["smart_exit"] = smart_exit
                action["status"] = f"smart_exit_{smart_exit['status']}"
                trade["status"] = action["status"]
                actions.append(action)
                self._log_event("challenge_smart_exit", action=action)
                if smart_exit["status"] in {"closed", "dry_run"}:
                    continue

            quote = self.client.current_quote(broker_symbol) or self.client.current_quote(str(trade.get("symbol") or ""))
            if not quote:
                action["status"] = "skipped_no_quote"
                actions.append(action)
                continue

            market_price = float(quote["bid"] if direction == "BUY" else quote["ask"])
            final_stage = max(1, int(round(self.protection_final_rr)))
            stage_targets = {
                stage: self._level_at_r(entry, risk, direction, float(stage))
                for stage in range(1, final_stage + 1)
            }
            hit_stage = 0
            for stage, target in stage_targets.items():
                if self._stage_is_hit(market_price, target, direction):
                    hit_stage = stage

            action["market_price"] = market_price
            action["targets"] = {f"tp{stage}": target for stage, target in stage_targets.items()}
            action["hit_stage"] = hit_stage

            if hit_stage <= 0:
                trade["stage"] = max(int(trade.get("stage") or 0), 0)
                trade["status"] = "waiting_for_tp1"
                actions.append(action)
                continue

            partial_payload: dict[str, Any] = {
                "enabled": self.tp1_partial_close_enabled,
                "percent": self.tp1_partial_close_pct,
                "done": bool(trade.get("tp1_partial_done")),
                "status": trade.get("tp1_partial_status"),
            }
            action["tp1_partial_close"] = partial_payload
            if self.tp1_partial_close_enabled and self.tp1_partial_close_pct > 0 and not trade.get("tp1_partial_done"):
                result = self.client.close_partial_position(
                    ticket=int(ticket),
                    symbol=broker_symbol,
                    direction=direction,
                    current_volume=float(position.get("volume") or 0.0),
                    close_percent=self.tp1_partial_close_pct,
                    comment=f"20PIP TP1 {self.tp1_partial_close_pct:g}%",
                )
                partial_payload["result"] = result
                if result.get("closed"):
                    status = "closed"
                elif result.get("permanent_skip"):
                    status = "skipped"
                else:
                    status = "failed"
                partial_payload["status"] = status
                if result.get("closed") or result.get("permanent_skip"):
                    trade["tp1_partial_done"] = True
                    trade["tp1_partial_status"] = status
                    trade["tp1_partial_at"] = now.isoformat(timespec="seconds")
                    trade["tp1_partial_percent"] = self.tp1_partial_close_pct
                    trade["tp1_partial_closed_volume"] = result.get("closed_volume")
                    trade["tp1_partial_remaining_volume"] = result.get("remaining_volume")

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
                trade["stage"] = max(int(trade.get("stage") or 0), hit_stage)
                trade["status"] = action["status"]
                trade["last_stop"] = current_stop
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
                trade["stage"] = max(int(trade.get("stage") or 0), hit_stage)
                trade["status"] = action["status"]
                trade["last_stop"] = desired_stop
                trade["last_modified_at"] = now.isoformat(timespec="seconds")
            else:
                action["status"] = "modify_failed"
                trade["status"] = action["status"]

            self._log_event("challenge_trade_protection", action=action)
            actions.append(action)

        _write_state(self.state)
        return actions

    def _already_traded_today(self, now: datetime) -> bool:
        if not self.one_trade_per_day:
            return False
        if self.state.get("last_trade_date") == _today_key(now):
            return True
        for trade in self.state.get("open_trades", {}).values():
            opened_at = _parse_datetime(trade.get("opened_at"))
            if opened_at and opened_at.date() == now.date():
                return True
        return False

    def _adjust_signal_target(
        self,
        signal: dict[str, Any],
        quote: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        adjusted = dict(signal)
        direction = str(adjusted.get("direction") or "").upper()
        symbol = str(adjusted.get("symbol") or "")
        execution_type = str(adjusted.get("execution_type") or "MARKET").upper()
        pending_entry = float(adjusted.get("trigger_price") or 0.0)
        entry = float(adjusted.get("entry") or 0.0)
        if quote and execution_type != "PENDING":
            entry = float(quote["ask"] if direction == "BUY" else quote["bid"])
        elif execution_type == "PENDING" and pending_entry > 0:
            entry = pending_entry

        if self.exit_mode == "FIXED_PIPS":
            info = self.client.symbol_info(symbol) or {}
            point = float(info.get("point") or (quote or {}).get("point") or 0.0)
            digits = int(info.get("digits") or (quote or {}).get("digits") or 5)
            pip_size = pip_size_for(
                symbol,
                point=point,
                digits=digits,
                overrides=self.pip_size_overrides,
            )
            stop_distance = pip_size * self.stop_loss_pips
            target_distance = pip_size * self.take_profit_pips
            broker_minimum = max(
                float(info.get("trade_stops_level") or 0.0) * point,
                float(info.get("trade_freeze_level") or 0.0) * point,
            )
            if direction not in {"BUY", "SELL"} or entry <= 0 or pip_size <= 0:
                adjusted["fixed_pip_error"] = "Invalid direction, entry, or pip size."
                return adjusted
            if broker_minimum > 0 and min(stop_distance, target_distance) < broker_minimum:
                adjusted["fixed_pip_error"] = (
                    f"Broker minimum distance {broker_minimum:g} exceeds the fixed-pip challenge distance."
                )
                return adjusted
            stop = entry - stop_distance if direction == "BUY" else entry + stop_distance
            target = entry + target_distance if direction == "BUY" else entry - target_distance
            adjusted["entry"] = self.client.normalize_price(symbol, entry)
            adjusted["stop_loss"] = self.client.normalize_price(symbol, stop)
            adjusted["take_profit"] = self.client.normalize_price(symbol, target)
            adjusted["tp1"] = adjusted["take_profit"]
            adjusted["tp2"] = None
            adjusted["tp3"] = None
            adjusted["tp4"] = None
            adjusted["tp5"] = None
            adjusted["risk_reward"] = round(self.reward_risk, 4)
            adjusted["configured_risk_reward"] = round(self.reward_risk, 4)
            adjusted["fixed_pip_plan"] = {
                "pip_size": pip_size,
                "stop_loss_pips": self.stop_loss_pips,
                "take_profit_pips": self.take_profit_pips,
                "entry": adjusted["entry"],
                "stop_loss": adjusted["stop_loss"],
                "take_profit": adjusted["take_profit"],
            }
            adjusted.setdefault("reasons", [])
            adjusted["reasons"] = [
                *adjusted["reasons"],
                f"20 Pip Challenge: fixed {self.take_profit_pips:g}-pip TP and {self.stop_loss_pips:g}-pip SL.",
            ]
            return adjusted

        stop = float(adjusted.get("stop_loss") or 0.0)
        risk = abs(entry - stop)
        rr = self.reward_risk
        if entry <= 0 or stop <= 0 or risk <= 0 or rr <= 0:
            return adjusted
        target = entry + risk * rr if direction == "BUY" else entry - risk * rr
        adjusted["take_profit"] = round(target, 5)
        adjusted["tp1"] = round(self._level_at_r(entry, risk, direction, 1.0), 5)
        adjusted["tp2"] = round(self._level_at_r(entry, risk, direction, 2.0), 5) if rr >= 2 else None
        adjusted["tp3"] = round(target, 5) if rr >= 3 else None
        adjusted["tp4"] = None
        adjusted["tp5"] = None
        adjusted["risk_reward"] = round(rr, 3)
        adjusted.setdefault("reasons", [])
        adjusted["reasons"] = [
            *adjusted["reasons"],
            f"Legacy challenge target: risk {self.risk_percent:g}% to seek {self.target_percent:g}% ({rr:.2f}R).",
        ]
        return adjusted

    def _apply_adaptive_stop(self, signal: dict[str, Any], now: datetime) -> dict[str, Any]:
        if not self.dynamic_stop_settings.enabled:
            return signal
        symbol = str(signal.get("symbol") or "")
        timeframe = str(signal.get("timeframe") or "M15").upper()
        minutes = {
            "M1": 1,
            "M5": 5,
            "M15": 15,
            "M30": 30,
            "H1": 60,
            "H4": 240,
            "D1": 1440,
            "W1": 10080,
        }.get(timeframe, 15)
        candles = self.client.fetch_candles(
            symbol,
            timeframe,
            now - timedelta(minutes=minutes * 140),
            now,
            max_bars=140,
        )
        return apply_dynamic_stop(signal, candles, self.dynamic_stop_settings)

    def _risk_lot_from_challenge_bank(self, signal: dict[str, Any], risk_amount: float, will_send: bool) -> dict[str, Any]:
        symbol = str(signal.get("symbol") or "")
        direction = str(signal.get("direction") or "").upper()
        stop_loss = float(signal.get("stop_loss") or 0.0)
        quote = self.client.current_quote(symbol)
        if will_send and not quote:
            return {"ok": False, "message": "Live quote is unavailable.", "risk_amount": risk_amount}
        entry_price = float(signal.get("entry") or 0.0)
        entry_source = "signal_entry"
        if quote and self.exit_mode != "FIXED_PIPS":
            entry_price = float(quote["ask"] if direction == "BUY" else quote["bid"])
            entry_source = "current_quote"
        if risk_amount <= 0 or entry_price <= 0 or stop_loss <= 0 or entry_price == stop_loss:
            return {
                "ok": False,
                "message": "Invalid challenge risk, entry, or stop.",
                "risk_amount": risk_amount,
                "entry_price": entry_price,
                "stop_loss": stop_loss,
            }

        account_balance = self.account_balance()
        account_risk_cap = account_balance * (self.max_account_risk_percent / 100)
        if will_send and account_balance < self.start_balance:
            return {
                "ok": False,
                "message": "Current MT5 balance is below the challenge start balance.",
                "account_balance": account_balance,
                "start_balance": self.start_balance,
            }
        if self.max_account_risk_percent > 0 and account_balance > 0 and risk_amount > account_risk_cap:
            return {
                "ok": False,
                "message": "Challenge risk amount exceeds the configured account-risk cap.",
                "risk_amount": risk_amount,
                "account_balance": account_balance,
                "account_risk_cap": account_risk_cap,
                "max_account_risk_percent": self.max_account_risk_percent,
            }

        per_lot = self.client.estimate_trade_risk(symbol, direction, 1.0, entry_price, stop_loss)
        risk_per_lot = float(per_lot.get("risk") or 0.0)
        if not per_lot.get("ok") or risk_per_lot <= 0:
            return {
                "ok": False,
                "message": "Could not estimate risk per 1.0 lot.",
                "risk_amount": risk_amount,
                "per_lot": per_lot,
            }

        raw_lot = risk_amount / risk_per_lot
        lot = self.client.normalize_lot_down(symbol, raw_lot)
        constraints = self.client.lot_constraints(symbol)
        use_broker_minimum = _env_bool(
            "CHALLENGE20_USE_BROKER_MIN_LOT",
            _env_bool("USE_BROKER_MIN_LOT_WHEN_RISK_TOO_SMALL", True),
        )
        minimum_lot_override = False
        if lot <= 0:
            if not use_broker_minimum:
                return {
                    "ok": False,
                    "message": "Risk amount is below broker minimum lot risk and minimum-lot override is disabled.",
                    "risk_amount": risk_amount,
                    "risk_per_1_lot": risk_per_lot,
                    "raw_lot": raw_lot,
                    "lot_constraints": constraints,
                }
            lot = float(constraints["min"])
            minimum_lot_override = True

        estimated = self.client.estimate_trade_risk(symbol, direction, lot, entry_price, stop_loss)
        final_risk = float(estimated.get("risk") or 0.0)
        return {
            "ok": bool(estimated.get("ok")) and final_risk > 0,
            "message": (
                "Challenge is using the broker minimum lot above its requested risk amount."
                if minimum_lot_override
                else "Challenge lot calculated."
            ),
            "symbol": symbol,
            "direction": direction,
            "entry_price": entry_price,
            "entry_source": entry_source,
            "stop_loss": stop_loss,
            "quote": quote,
            "challenge_balance": self.challenge_balance(),
            "risk_percent": self.risk_percent,
            "risk_amount": risk_amount,
            "target_percent": self.target_percent,
            "reward_risk": self.reward_risk,
            "risk_per_1_lot": risk_per_lot,
            "raw_lot": raw_lot,
            "lot": lot,
            "estimated_risk": final_risk,
            "actual_risk_percent_of_account": (final_risk / account_balance * 100.0) if account_balance > 0 else None,
            "risk_overrun": max(0.0, final_risk - risk_amount),
            "minimum_lot_override": minimum_lot_override,
            "account_balance": account_balance,
            "max_account_risk_percent": self.max_account_risk_percent,
            "risk_method": estimated.get("method"),
        }

    def _order_comment(self, signal: dict[str, Any]) -> str:
        level = int(self.state.get("level") or 1)
        score = int(signal.get("setup_score") or 0)
        timeframe = str(signal.get("timeframe") or "")[:5]
        strategy = self.strategy[:3]
        return f"20PIP {strategy} L{level} S{score} {timeframe}"[:31]

    def _session_is_open(self) -> bool:
        local_now = datetime.now(zone(self.orb_settings.session_timezone))
        current = local_now.hour * 60 + local_now.minute
        start_value = parse_hhmm(self.orb_settings.session_start, "19:00")
        end_value = parse_hhmm(self.orb_settings.session_end, "02:00")
        start = start_value.hour * 60 + start_value.minute
        end = end_value.hour * 60 + end_value.minute
        if start < end:
            return start <= current < end
        return current >= start or current < end

    def _close_positions_after_session(self) -> list[dict[str, Any]]:
        if not self.close_at_session_end or self._session_is_open():
            return []
        actions: list[dict[str, Any]] = []
        for order in self.client.pending_orders(magic=CHALLENGE_MAGIC):
            result = self.client.cancel_pending_order(
                int(order.get("ticket") or 0),
                str(order.get("symbol") or ""),
            )
            actions.append({"action": "cancel_pending", "order": order, "result": result})
        for position in self.client.open_positions(magic=CHALLENGE_MAGIC):
            direction = "SELL" if int(position.get("type") or 0) == 1 else "BUY"
            result = self.client.close_position(
                ticket=int(position.get("ticket") or 0),
                symbol=str(position.get("symbol") or ""),
                direction=direction,
                volume=float(position.get("volume") or 0.0),
                comment="20PIP session close",
                live_trading=self.live_trading,
            )
            actions.append({"action": "close_position", "position": position, "result": result})
        return actions

    def _reconcile_fixed_position(self, record: dict[str, Any]) -> dict[str, Any] | None:
        if self.exit_mode != "FIXED_PIPS":
            return None
        symbol = str(record.get("symbol") or record.get("broker_symbol") or "")
        broker_symbol = str(record.get("broker_symbol") or symbol)
        direction = str(record.get("direction") or "").upper()
        entry = float(record.get("entry") or 0.0)
        info = self.client.symbol_info(symbol) or {}
        pip_size = pip_size_for(
            symbol,
            point=float(info.get("point") or 0.0),
            digits=int(info.get("digits") or 0),
            overrides=self.pip_size_overrides,
        )
        if direction not in {"BUY", "SELL"} or entry <= 0 or pip_size <= 0:
            return {"modified": False, "message": "Could not reconcile fixed-pip levels."}
        stop_distance = pip_size * self.stop_loss_pips
        target_distance = pip_size * self.take_profit_pips
        stop = entry - stop_distance if direction == "BUY" else entry + stop_distance
        target = entry + target_distance if direction == "BUY" else entry - target_distance
        stop = self.client.normalize_price(symbol, stop)
        target = self.client.normalize_price(symbol, target)
        result = self.client.modify_position_sl_tp(
            ticket=int(record.get("ticket") or 0),
            symbol=broker_symbol,
            stop_loss=stop,
            take_profit=target,
        )
        record["initial_stop"] = stop
        record["stop_loss"] = stop
        record["take_profit"] = target
        record["fixed_pip_reconciliation"] = result
        return result

    def _scan_orb_challenge(self) -> dict[str, Any]:
        scan: dict[str, Any] = {
            "allowed": [],
            "preplace": [],
            "near_misses": [],
            "rejected": [],
            "errors": [],
        }
        now = now_naive(self.orb_settings.data_timezone)
        start = now - timedelta(days=self.orb_lookback_days)
        for symbol in self.symbols:
            try:
                candles = self.client.fetch_candles(symbol, self.orb_timeframe, start, now)
                if candles is None or len(candles) < 64:
                    scan["rejected"].append(
                        {
                            "symbol": symbol,
                            "timeframe": self.orb_timeframe,
                            "reason": "Not enough candles for ORB challenge scan.",
                        }
                    )
                    continue

                confirmed = confirmed_orb_signal(candles, symbol, self.orb_timeframe, self.orb_settings, now=now)
                if confirmed and int(confirmed.get("setup_score") or 0) >= self.min_setup_score:
                    scan["allowed"].append(confirmed)
                elif confirmed:
                    scan["near_misses"].append(
                        {
                            **confirmed,
                            "reason": f"ORB score below challenge threshold {self.min_setup_score}.",
                        }
                    )

                if self.allow_pending:
                    for pending in pending_orb_signals(candles, symbol, self.orb_timeframe, self.orb_settings, now=now):
                        if int(pending.get("setup_score") or 0) >= max(85, self.min_setup_score - 5):
                            scan["preplace"].append(pending)
                        else:
                            scan["near_misses"].append(
                                {
                                    **pending,
                                    "reason": "ORB pending score below challenge threshold.",
                                }
                            )
            except Exception as exc:
                scan["errors"].append({"symbol": symbol, "timeframe": self.orb_timeframe, "error": str(exc)})
        return scan

    def _record_position_after_placement(
        self,
        signal: dict[str, Any],
        order: dict[str, Any],
        placement: dict[str, Any],
        now: datetime,
        risk_amount: float,
    ) -> dict[str, Any] | None:
        positions = self.client.open_positions(signal["symbol"], magic=CHALLENGE_MAGIC)
        known = set(self.state.setdefault("open_trades", {}))
        candidates = [position for position in positions if str(position.get("ticket") or "") not in known]
        if not candidates:
            return None
        candidates.sort(key=lambda item: int(item.get("time") or 0), reverse=True)
        position = candidates[0]
        ticket = str(position.get("ticket") or "")
        if not ticket:
            return None
        record = {
            "ticket": ticket,
            "symbol": signal.get("symbol"),
            "broker_symbol": order.get("broker_symbol"),
            "direction": signal.get("direction"),
            "volume": position.get("volume") or order.get("lot"),
            "entry": position.get("price_open") or order.get("entry"),
            "stop_loss": position.get("sl") or order.get("stop_loss"),
            "take_profit": position.get("tp") or order.get("take_profit"),
            "risk_amount": risk_amount,
            "challenge_balance_at_entry": self.challenge_balance(),
            "level": self.state.get("level"),
            "opened_at": now.isoformat(timespec="seconds"),
            "signal": signal,
            "order": order,
            "placement": placement,
            "status": "open",
        }
        self.state.setdefault("open_trades", {})[ticket] = record
        self._reconcile_fixed_position(record)
        return record

    def run_once(self) -> dict[str, Any]:
        now = datetime.now()
        self._heartbeat("scanning")
        sync_actions = self.sync_open_positions(now)
        session_close_actions = self._close_positions_after_session()
        protection_actions = self.protect_open_positions(now)
        blocks: list[str] = []
        weekend_pending_actions: list[dict[str, Any]] = []
        prepared: dict[str, Any] | None = None
        placement: dict[str, Any] | None = None
        selected_signal: dict[str, Any] | None = None

        if self.state.get("status") != "active":
            blocks.append(f"Challenge status is {self.state.get('status')}.")
        if self.strategy == "ORB" and not self._session_is_open():
            blocks.append("ORB challenge session is closed; no new challenge entry is allowed.")
        challenge_timezone = os.getenv(
            "CHALLENGE20_ORB_SESSION_TIMEZONE",
            os.getenv("MARKET_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE),
        )
        current_weekday = datetime.now(zone(challenge_timezone)).strftime("%a").upper()[:3]
        if self.weekdays_only and current_weekday not in self.allowed_weekdays:
            blocks.append(
                f"Challenge entry-day block is active for {current_weekday}; "
                f"allowed days are {','.join(sorted(self.allowed_weekdays))}."
            )
            if self.live_trading:
                for order in self.client.pending_orders(magic=CHALLENGE_MAGIC):
                    result = self.client.cancel_pending_order(
                        int(order.get("ticket") or 0),
                        str(order.get("symbol") or ""),
                    )
                    weekend_pending_actions.append({"order": order, "result": result})
        if self.reward_risk <= 0:
            blocks.append("Challenge reward/risk is invalid.")
        if self.state.get("open_trades"):
            blocks.append("A 20 Pip Challenge position is already open.")
        if self._already_traded_today(now):
            blocks.append("One-trade-per-day rule is active and today's challenge trade is already used.")

        scan: dict[str, Any] = {
            "allowed": [],
            "preplace": [],
            "near_misses": [],
            "rejected": [],
            "errors": [],
        }
        if not blocks:
            if self.strategy == "ORB":
                scan = self._scan_orb_challenge()
            elif self.strategy in {"HYBRID", "MULTI", "SUITE"}:
                if self.strategy in {"HYBRID", "MULTI"}:
                    scan = self._scan_orb_challenge()
                suite_candidates: list[dict[str, Any]] = []
                try:
                    from .strategy_suite import challenge_entry_candidates

                    lookback_days = max(1, int(os.getenv("CHALLENGE20_SUITE_LOOKBACK_DAYS", "3") or 3))
                    suite_candidates = challenge_entry_candidates(
                        date.today() - timedelta(days=lookback_days),
                        date.today(),
                        tuple(self.symbols),
                    )
                except Exception as exc:
                    scan.setdefault("errors", []).append({"source": "strategy_suite", "error": str(exc)})
                scan.setdefault("allowed", []).extend(suite_candidates)
            else:
                scan = scan_market(
                    symbols=self.symbols,
                    timeframes=self.timeframes,
                    min_score=self.min_setup_score,
                    preplace_min_score=max(85, self.min_setup_score - 5),
                    min_rr=max(1.0, self.reward_risk),
                )
            candidates = list(scan.get("allowed", []))
            if self.allow_pending:
                candidates.extend(scan.get("preplace", []))
            candidates.sort(key=_challenge_signal_quality_sort_key, reverse=True)
            for rank, candidate in enumerate(candidates, start=1):
                candidate["selector_rank"] = rank
                candidate["selector_score_tuple"] = _challenge_signal_quality_sort_key(candidate)
            if not candidates:
                blocks.append("No challenge-qualified LTA setup found.")
            else:
                selected_signal = (
                    self._adjust_signal_target(candidates[0])
                    if self.exit_mode == "FIXED_PIPS"
                    else self._adjust_signal_target(self._apply_adaptive_stop(candidates[0], now))
                )

        if selected_signal:
            will_send = self.live_trading and self.place_trades
            if self.exit_mode == "FIXED_PIPS":
                quote = self.client.current_quote(str(selected_signal.get("symbol") or ""))
                selected_signal = self._adjust_signal_target(selected_signal, quote=quote)
                if selected_signal.get("fixed_pip_error"):
                    blocks.append(str(selected_signal["fixed_pip_error"]))
            else:
                selected_signal = self.client.normalize_signal_for_execution(selected_signal)
            spread_check = self.client.spread_check(
                selected_signal,
                max_spread_risk_percent=self.max_spread_risk_percent,
                max_spread_points=self.max_spread_points,
            )
            if blocks:
                spread_check = {"ok": False, "message": "Challenge signal blocked before spread validation."}
            elif not spread_check.get("ok"):
                blocks.extend(str(reason) for reason in (spread_check.get("reasons") or [spread_check.get("message")]))
            else:
                risk_amount = self.risk_amount()
                lot_sizing = self._risk_lot_from_challenge_bank(selected_signal, risk_amount, will_send)
                if not lot_sizing.get("ok"):
                    blocks.append(str(lot_sizing.get("message") or "Challenge lot sizing failed."))
                else:
                    order = self.client.prepare_order(
                        selected_signal,
                        lot=float(lot_sizing["lot"]),
                        live_trading=will_send,
                    )
                    order["magic"] = CHALLENGE_MAGIC
                    order["comment"] = self._order_comment(selected_signal)
                    order["lot_sizing"] = lot_sizing
                    order["spread_check"] = spread_check
                    order["spread_limits"] = {
                        "max_spread_risk_percent": self.max_spread_risk_percent,
                        "max_spread_points": self.max_spread_points,
                    }
                    prepared = {
                        "created_at": now.isoformat(timespec="seconds"),
                        "signal": selected_signal,
                        "order": order,
                        "challenge": {
                            "level": self.state.get("level"),
                            "challenge_balance": self.challenge_balance(),
                            "risk_amount": risk_amount,
                            "risk_percent": self.risk_percent,
                            "target_percent": self.target_percent,
                            "reward_risk": self.reward_risk,
                            "target_balance": self.target_balance(),
                        },
                    }
                    self._log_event("challenge_order_prepared", prepared=prepared)

                    if will_send:
                        is_pending = str(selected_signal.get("execution_type") or "").upper() == "PENDING"
                        placement = (
                            self.client.place_pending_order(order)
                            if is_pending
                            else self.client.place_order(order)
                        )
                        self._log_event("challenge_order_sent", placement=placement, prepared=prepared)
                        if placement.get("placed"):
                            self.state["last_trade_date"] = _today_key(now)
                            self.state.setdefault("stats", {})["placements"] = int(
                                self.state.setdefault("stats", {}).get("placements") or 0
                            ) + 1
                            record = None if is_pending else self._record_position_after_placement(
                                selected_signal, order, placement, now, risk_amount
                            )
                            if record:
                                prepared["tracked_position"] = record
                            _write_state(self.state)

        payload = {
            "checked_at": now.isoformat(timespec="seconds"),
            "status": self.state.get("status"),
            "symbols": list(self.symbols),
            "timeframes": list(self.timeframes),
            "strategy": self.strategy,
            "orb": {
                "timeframe": self.orb_timeframe,
                "session_start": self.orb_settings.session_start,
                "session_end": self.orb_settings.session_end,
                "session_timezone": self.orb_settings.session_timezone,
                "range_minutes": self.orb_settings.range_minutes,
            }
            if self.strategy == "ORB"
            else None,
            "live_trading": self.live_trading,
            "place_trades": self.place_trades,
            "one_trade_per_day": self.one_trade_per_day,
            "challenge_balance": self.challenge_balance(),
            "level": self.state.get("level"),
            "level_target": round(self.level_target(int(self.state.get("level") or 1)), 2),
            "final_target_balance": round(self.target_balance(), 2),
            "risk_percent": self.risk_percent,
            "target_percent": self.target_percent,
            "reward_risk": round(self.reward_risk, 3),
            "exit_plan": {
                "mode": self.exit_mode,
                "take_profit_pips": self.take_profit_pips,
                "stop_loss_pips": self.stop_loss_pips,
                "pip_size_overrides": self.pip_size_overrides,
            },
            "weekdays_only": self.weekdays_only,
            "allowed_weekdays": sorted(self.allowed_weekdays),
            "weekend_pending_actions": weekend_pending_actions,
            "close_at_session_end": self.close_at_session_end,
            "session_close_actions": session_close_actions,
            "trade_protection": {
                "enabled": self.protect_open_trades,
                "final_rr": self.protection_final_rr,
                "tp1_partial_close": {
                    "enabled": self.tp1_partial_close_enabled,
                    "percent": self.tp1_partial_close_pct,
                },
                "dynamic_stop": self.dynamic_stop_settings.__dict__,
                "smart_exit": self.smart_exit_settings.__dict__,
                "checked_count": len(protection_actions),
                "modified_count": sum(1 for action in protection_actions if action.get("status") == "modified"),
                "actions": protection_actions,
            },
            "risk_amount": round(self.risk_amount(), 2),
            "open_trade_count": len(self.state.get("open_trades", {})),
            "sync_actions": sync_actions,
            "blocked": blocks,
            "prepared": prepared,
            "placement": placement,
            "scan": scan,
            "state_path": str(STATE_PATH),
            "events_path": str(EVENTS_PATH),
        }
        _write_json(LATEST_PATH, payload)
        self._heartbeat("waiting")
        return payload

    def run_forever(self) -> None:
        print("20 Pip Challenge worker started.")
        print(f"Strategy: {self.strategy}")
        print(f"Symbols: {', '.join(self.symbols)} | timeframes: {', '.join(self.timeframes)}")
        if self.strategy == "ORB":
            print(
                f"ORB: {self.orb_settings.range_minutes}m range, "
                f"{self.orb_settings.session_start}-{self.orb_settings.session_end} "
                f"{self.orb_settings.session_timezone}, timeframe {self.orb_timeframe}."
            )
        print(
            f"Challenge bank: ${self.challenge_balance():.2f}, level {self.state.get('level')}/{self.max_levels}, "
            f"final target about ${self.target_balance():,.2f}."
        )
        if self.exit_mode == "FIXED_PIPS":
            print(
                f"Risk {self.risk_percent:g}% with fixed TP {self.take_profit_pips:g} pips / "
                f"SL {self.stop_loss_pips:g} pips ({self.reward_risk:.2f}R), "
                f"one trade/day={self.one_trade_per_day}."
            )
        else:
            print(
                f"Risk {self.risk_percent:g}% to target {self.target_percent:g}% "
                f"({self.reward_risk:.2f}R), one trade/day={self.one_trade_per_day}."
            )
        print(f"Weekday entries only: {self.weekdays_only}")
        print(f"Allowed challenge days: {', '.join(sorted(self.allowed_weekdays))}")
        print(f"Live trading: {self.live_trading}; CHALLENGE20_PLACE_TRADES: {self.place_trades}")
        print(f"State: {STATE_PATH}")
        print("Press Ctrl+C to stop.")
        while True:
            payload = self.run_once()
            blocked = "; ".join(payload.get("blocked") or [])
            print(
                f"[{payload['checked_at']}] level={payload['level']} "
                f"bank=${payload['challenge_balance']:.2f} risk=${payload['risk_amount']:.2f} "
                f"open={payload['open_trade_count']} prepared={bool(payload['prepared'])} "
                f"placed={bool((payload.get('placement') or {}).get('placed'))}"
                + (f" blocked={blocked[:180]}" if blocked else "")
            )
            time.sleep(self.interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="20 Pip Challenge sub-bot.")
    parser.add_argument("--once", action="store_true", help="Run one scan and exit.")
    args = parser.parse_args()

    lock = ChallengeLock(LOCK_PATH)
    lock.acquire()
    bot = TwentyPipChallengeBot()
    if args.once:
        print(json.dumps(bot.run_once(), indent=2, default=str))
        return
    bot.run_forever()


if __name__ == "__main__":
    main()
