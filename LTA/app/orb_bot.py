from __future__ import annotations

import argparse
import atexit
from dataclasses import replace
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
PROTECTION_LOG_PATH = ORB_DIR / "orb_trade_protection.jsonl"


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


def _env_float_map(name: str) -> dict[str, float]:
    value = os.getenv(name)
    if not value:
        return {}
    result: dict[str, float] = {}
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        separator = ":" if ":" in item else "=" if "=" in item else None
        if not separator:
            continue
        symbol, raw_value = item.split(separator, 1)
        try:
            result[symbol.strip().upper()] = float(raw_value.strip())
        except ValueError:
            continue
    return result


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _orb_signal_quality_sort_key(signal: dict[str, Any]) -> tuple[float, float, float, int]:
    score = _safe_float(signal.get("setup_score"))
    rr = _safe_float(signal.get("configured_risk_reward"), _safe_float(signal.get("risk_reward")))
    orb = signal.get("orb") or {}
    range_atr = _safe_float(orb.get("range_atr"), 999.0)
    range_quality = 100.0 - min(100.0, abs(range_atr - 1.0) * 40.0)
    execution = str(signal.get("execution_type") or "").upper()
    pending_type = str(signal.get("pending_order_type") or "").upper()
    execution_rank = 2 if execution == "MARKET" else 1 if pending_type in {"BUY_STOP", "SELL_STOP"} else 0
    return (score, rr, range_quality, execution_rank)


def _rank_orb_signals(signals: list[dict[str, Any]], candidate_limit: int = 0) -> list[dict[str, Any]]:
    ranked = sorted(signals, key=_orb_signal_quality_sort_key, reverse=True)
    if candidate_limit > 0:
        ranked = ranked[:candidate_limit]
    for index, signal in enumerate(ranked, start=1):
        signal.setdefault("selector_rank", index)
        signal.setdefault("selector_score_tuple", _orb_signal_quality_sort_key(signal))
    return ranked


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "consumed": {}, "protected_positions": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "consumed": {}}
    if not isinstance(data, dict):
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "consumed": {}}
    data.setdefault("consumed", {})
    data.setdefault("protected_positions", {})
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
        self.max_trades_per_day = max(0, _env_int("ORB_MAX_TRADES_PER_DAY", 1))
        self.best_setup_selector = _env_bool("ORB_BEST_SETUP_SELECTOR", True)
        self.best_setup_candidate_limit = max(0, _env_int("ORB_BEST_SETUP_CANDIDATE_LIMIT", 0))
        self.risk_percent = max(0.0, _env_float("ORB_MAX_LOT_RISK_PCT", self.config.max_lot_risk_pct))
        self.max_spread_risk_percent = max(0.0, _env_float("ORB_MAX_SPREAD_RISK_PERCENT", self.config.max_spread_risk_percent))
        self.max_spread_points = max(0.0, _env_float("ORB_MAX_SPREAD_POINTS", self.config.max_spread_points))
        self.pending_expiry_minutes = max(0, _env_int("ORB_PENDING_EXPIRY_MINUTES", 360))
        self.log_detail_limit = max(0, _env_int("ORB_LOG_DETAIL_LIMIT", 8))
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
        self.symbol_rr = _env_float_map("ORB_SYMBOL_RR")
        self.symbol_protection_rr = _env_float_map("ORB_SYMBOL_PROTECTION_RR")
        self.protect_open_trades = _env_bool("ORB_PROTECT_OPEN_TRADES", True)
        self.protection_final_rr = max(1.0, _env_float("ORB_PROTECTION_FINAL_RR", self.settings.reward_risk))
        self.tp1_partial_close_enabled = _env_bool("ORB_TP1_PARTIAL_CLOSE", True)
        self.tp1_partial_close_pct = max(0.0, min(100.0, _env_float("ORB_TP1_PARTIAL_CLOSE_PCT", 50.0)))
        self.state = _read_state()
        _write_state(self.state)

    def _base_symbol_from_broker_symbol(self, broker_symbol: str) -> str:
        upper = broker_symbol.upper()
        for symbol in (*self.symbols, *TRADE_SYMBOLS):
            if symbol in upper:
                return symbol
        return broker_symbol

    def _rr_for_symbol(self, symbol: str | None) -> float:
        base = str(symbol or "").upper()
        if base not in self.symbol_rr:
            base = self._base_symbol_from_broker_symbol(base)
        try:
            return max(0.5, float(self.symbol_rr.get(base, self.settings.reward_risk)))
        except (TypeError, ValueError):
            return self.settings.reward_risk

    def _protection_rr_for_symbol(self, symbol: str | None) -> float:
        base = str(symbol or "").upper()
        if base not in self.symbol_protection_rr and base not in self.symbol_rr:
            base = self._base_symbol_from_broker_symbol(base)
        value = self.symbol_protection_rr.get(base, self.symbol_rr.get(base, self.protection_final_rr))
        try:
            return max(1.0, float(value))
        except (TypeError, ValueError):
            return self.protection_final_rr

    def _settings_for_symbol(self, symbol: str) -> ORBSettings:
        return replace(self.settings, reward_risk=self._rr_for_symbol(symbol))

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

    @staticmethod
    def _session_day(signal: dict[str, Any]) -> str:
        timestamp = signal.get("timestamp")
        data_timezone = os.getenv("MARKET_DATA_TIMEZONE", DEFAULT_DATA_TIMEZONE)
        session_timezone = os.getenv("ORB_SESSION_TIMEZONE", os.getenv("MARKET_SESSION_TIMEZONE", DEFAULT_SESSION_TIMEZONE))
        if isinstance(timestamp, datetime):
            return date_in_timezone(timestamp, data_timezone, session_timezone).isoformat()
        try:
            return date_in_timezone(datetime.fromisoformat(str(timestamp)), data_timezone, session_timezone).isoformat()
        except ValueError:
            return now_naive(session_timezone).date().isoformat()

    def _consumed_count_for_day(self, session_day: str) -> int:
        consumed = self.state.get("consumed", {})
        count = 0
        for key, item in consumed.items():
            key_day = str(key).split("|", 1)[0]
            if key_day != session_day:
                continue
            if str(item.get("status") or "").lower() in {"placed", "prepared"}:
                count += 1
        return count

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
            "risk_reward": signal.get("risk_reward"),
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
        rr = signal.get("risk_reward")
        rr_text = f" R{float(rr):g}" if rr else ""
        return f"ORB {direction} S{score} {self.timeframe}{rr_text}"[:31]

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

    def _position_state(self, ticket: str, position: dict[str, Any]) -> dict[str, Any]:
        protected = self.state.setdefault("protected_positions", {})
        existing = protected.get(ticket, {})
        broker_symbol = str(position.get("symbol") or existing.get("broker_symbol") or "")
        symbol = existing.get("symbol") or self._base_symbol_from_broker_symbol(broker_symbol)
        final_rr = max(1.0, float(existing.get("final_rr") or self._protection_rr_for_symbol(symbol)))
        direction = self._position_direction(position)
        entry = float(position.get("price_open") or existing.get("entry") or 0.0)
        current_stop = float(position.get("sl") or 0.0)
        take_profit = float(position.get("tp") or 0.0)
        initial_stop = float(existing.get("initial_stop") or current_stop or 0.0)

        if initial_stop <= 0 and take_profit > 0 and entry > 0:
            one_r = abs(take_profit - entry) / final_rr
            initial_stop = entry - one_r if direction == "BUY" else entry + one_r

        payload = {
            **existing,
            "ticket": ticket,
            "broker_symbol": broker_symbol,
            "symbol": symbol,
            "final_rr": final_rr,
            "direction": direction,
            "entry": entry,
            "initial_stop": initial_stop,
            "take_profit": take_profit,
            "status": "open",
            "last_seen_at": datetime.now().isoformat(timespec="seconds"),
        }
        protected[ticket] = payload
        return payload

    def _handle_tp1_partial_close(
        self,
        ticket: str,
        position: dict[str, Any],
        state: dict[str, Any],
        action: dict[str, Any],
        now: datetime,
    ) -> None:
        partial_payload: dict[str, Any] = {
            "enabled": self.tp1_partial_close_enabled,
            "percent": self.tp1_partial_close_pct,
            "done": bool(state.get("tp1_partial_done")),
            "status": state.get("tp1_partial_status"),
        }
        action["tp1_partial_close"] = partial_payload

        if not self.tp1_partial_close_enabled or self.tp1_partial_close_pct <= 0 or state.get("tp1_partial_done"):
            return

        volume = float(position.get("volume") or 0.0)
        if volume <= 0:
            partial_payload["status"] = "skipped_missing_volume"
            return

        result = self.client.close_partial_position(
            ticket=int(ticket),
            symbol=str(state.get("broker_symbol") or position.get("symbol") or ""),
            direction=str(state.get("direction") or ""),
            current_volume=volume,
            close_percent=self.tp1_partial_close_pct,
            comment=f"ORB TP1 {self.tp1_partial_close_pct:g}%",
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
            state["tp1_partial_done"] = True
            state["tp1_partial_status"] = status
            state["tp1_partial_at"] = now.isoformat(timespec="seconds")
            state["tp1_partial_percent"] = self.tp1_partial_close_pct
            state["tp1_partial_closed_volume"] = result.get("closed_volume")
            state["tp1_partial_remaining_volume"] = result.get("remaining_volume")

        if result.get("closed"):
            event_name = "orb_tp1_partial_close_closed"
        elif result.get("permanent_skip"):
            event_name = "orb_tp1_partial_close_skipped"
        else:
            event_name = "orb_tp1_partial_close_failed"
        event = {
            "checked_at": now.isoformat(timespec="seconds"),
            "event": event_name,
            "ticket": ticket,
            "symbol": state.get("symbol"),
            "broker_symbol": state.get("broker_symbol"),
            "direction": state.get("direction"),
            "volume": volume,
            "percent": self.tp1_partial_close_pct,
            "result": result,
        }
        _append_jsonl(PROTECTION_LOG_PATH, event)
        self._log_event(
            event_name,
            ticket=ticket,
            symbol=state.get("symbol"),
            broker_symbol=state.get("broker_symbol"),
            direction=state.get("direction"),
            volume=volume,
            percent=self.tp1_partial_close_pct,
            result=result,
        )

    def protect_open_positions(self, now: datetime) -> list[dict[str, Any]]:
        if not self.protect_open_trades:
            return []

        actions: list[dict[str, Any]] = []
        positions = self.client.open_positions(magic=ORB_MAGIC)
        protected_positions = self.state.setdefault("protected_positions", {})
        open_tickets = {str(position.get("ticket")) for position in positions if position.get("ticket")}

        for stale_ticket in set(protected_positions) - open_tickets:
            state = protected_positions[stale_ticket]
            if state.get("status") == "closed":
                continue
            state["status"] = "closed"
            state["closed_seen_at"] = now.isoformat(timespec="seconds")
            actions.append(
                {
                    "checked_at": now.isoformat(timespec="seconds"),
                    "ticket": stale_ticket,
                    "symbol": state.get("symbol"),
                    "broker_symbol": state.get("broker_symbol"),
                    "status": "closed_seen",
                }
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

            action: dict[str, Any] = {
                "checked_at": now.isoformat(timespec="seconds"),
                "ticket": ticket,
                "symbol": state["symbol"],
                "broker_symbol": broker_symbol,
                "final_rr": float(state.get("final_rr") or self._protection_rr_for_symbol(state["symbol"])),
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

            quote = self.client.current_quote(broker_symbol)
            if not quote:
                action["status"] = "skipped_no_quote"
                actions.append(action)
                continue

            market_price = float(quote["bid"] if direction == "BUY" else quote["ask"])
            final_stage = max(1, int(round(float(action["final_rr"]))))
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

            self._handle_tp1_partial_close(ticket, position, state, action, now)

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
                self._log_event(
                    "orb_protection_modified",
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
            else:
                action["status"] = "modify_failed"
                state["status"] = action["status"]

            actions.append(action)
            _append_jsonl(PROTECTION_LOG_PATH, action)

        _write_state(self.state)
        return actions

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

    @staticmethod
    def _short_text(value: Any, limit: int = 180) -> str:
        text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
        return text if len(text) <= limit else text[: limit - 3] + "..."

    def _print_cycle_details(self, payload: dict[str, Any]) -> None:
        if self.log_detail_limit <= 0:
            return

        for error in payload.get("errors", [])[: self.log_detail_limit]:
            symbol = error.get("symbol") or "?"
            message = error.get("error") or error.get("message") or error
            print(f"  error {symbol}: {self._short_text(message)}")

        for item in payload.get("blocked", [])[: self.log_detail_limit]:
            symbol = item.get("symbol") or "?"
            direction = item.get("direction") or ""
            reasons = item.get("reasons") or [item.get("reason") or item.get("message") or "blocked"]
            reason_text = "; ".join(str(reason) for reason in reasons if reason)
            print(f"  blocked {symbol} {direction}: {self._short_text(reason_text)}")

        for item in payload.get("placements", [])[: self.log_detail_limit]:
            placement = item.get("placement") or {}
            if placement.get("placed"):
                continue
            signal = item.get("signal") or {}
            symbol = signal.get("symbol") or "?"
            direction = signal.get("direction") or ""
            order_type = signal.get("pending_order_type") or signal.get("execution_type") or ""
            message = placement.get("message") or placement.get("error") or "placement failed"
            print(f"  failed {symbol} {direction} {order_type}: {self._short_text(message)}")

    def run_once(self) -> dict[str, Any]:
        now = now_naive(self.settings.data_timezone)
        self._heartbeat("scanning")
        protection_actions = self.protect_open_positions(now)
        prepared: list[dict[str, Any]] = []
        placements: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        cycle_commitments = 0

        cycle_signals: list[dict[str, Any]] = []
        for symbol in self.symbols:
            symbol_settings = self._settings_for_symbol(symbol)
            candles = self._load_candles(symbol, now)
            if candles is None or len(candles) < 120:
                errors.append({"symbol": symbol, "error": f"Not enough {self.timeframe} candles."})
                continue

            signals: list[dict[str, Any]] = []
            confirmed = confirmed_orb_signal(candles, symbol, self.timeframe, symbol_settings, now=now)
            if confirmed:
                signals.append(confirmed)
            elif self.prepare_pending:
                signals.extend(pending_orb_signals(candles, symbol, self.timeframe, symbol_settings, now=now))

            cycle_signals.extend(signals)

        if self.best_setup_selector:
            cycle_signals = _rank_orb_signals(cycle_signals, self.best_setup_candidate_limit)

        for signal in cycle_signals:
            symbol = str(signal.get("symbol") or "")
            if self._already_consumed(signal):
                blocked.append(
                    {
                        "symbol": symbol,
                        "direction": signal.get("direction"),
                        "rank": signal.get("selector_rank"),
                        "reason": "ORB signal already consumed today.",
                    }
                )
                continue
            session_day = self._session_day(signal)
            consumed_today = self._consumed_count_for_day(session_day) + cycle_commitments
            if self.max_trades_per_day > 0 and consumed_today >= self.max_trades_per_day:
                blocked.append(
                    {
                        "symbol": symbol,
                        "direction": signal.get("direction"),
                        "rank": signal.get("selector_rank"),
                        "reason": f"ORB_MAX_TRADES_PER_DAY reached for {session_day}.",
                        "max_trades_per_day": self.max_trades_per_day,
                        "consumed_today": consumed_today,
                    }
                )
                continue
            order, reasons = self._prepare_signal(signal, now)
            if not order:
                blocked.append(
                    {
                        "symbol": symbol,
                        "direction": signal.get("direction"),
                        "rank": signal.get("selector_rank"),
                        "reasons": reasons,
                    }
                )
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
                    cycle_commitments += 1
            else:
                self._mark_consumed(signal, "prepared", {"message": "Prepared only; ORB live placement is disabled."})
                cycle_commitments += 1

        payload = {
            "checked_at": now.isoformat(timespec="seconds"),
            "symbols": list(self.symbols),
            "timeframe": self.timeframe,
            "settings": self.settings.__dict__,
            "settings_by_symbol": {
                symbol: self._settings_for_symbol(symbol).__dict__
                for symbol in self.symbols
            },
            "symbol_rr": self.symbol_rr,
            "symbol_protection_rr": self.symbol_protection_rr,
            "live_trading": self.live_trading,
            "place_trades": self.place_trades,
            "prepare_pending": self.prepare_pending,
            "place_pending": self.place_pending,
            "risk_percent": self.risk_percent,
            "max_trades_per_day": self.max_trades_per_day,
            "best_setup_selector": self.best_setup_selector,
            "best_setup_candidate_limit": self.best_setup_candidate_limit,
            "ranked_signal_count": len(cycle_signals),
            "top_ranked_signals": [
                {
                    "rank": item.get("selector_rank"),
                    "symbol": item.get("symbol"),
                    "direction": item.get("direction"),
                    "execution_type": item.get("execution_type"),
                    "pending_order_type": item.get("pending_order_type"),
                    "score": item.get("setup_score"),
                    "rr": item.get("risk_reward"),
                    "range_atr": (item.get("orb") or {}).get("range_atr"),
                }
                for item in cycle_signals[:5]
            ],
            "trade_protection": {
                "enabled": self.protect_open_trades,
                "final_rr": self.protection_final_rr,
                "symbol_final_rr": {
                    symbol: self._protection_rr_for_symbol(symbol)
                    for symbol in self.symbols
                },
                "tp1_partial_close": {
                    "enabled": self.tp1_partial_close_enabled,
                    "percent": self.tp1_partial_close_pct,
                },
                "checked_count": len(protection_actions),
                "modified_count": sum(1 for action in protection_actions if action.get("status") == "modified"),
                "actions": protection_actions,
                "log_path": str(PROTECTION_LOG_PATH),
            },
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
        if self.symbol_rr:
            print(
                "Per-symbol RR: "
                + ", ".join(f"{symbol}=1:{rr:g}" for symbol, rr in sorted(self.symbol_rr.items()))
            )
        print(f"Candle/data timezone: {self.settings.data_timezone}.")
        print(f"Trade protection: {self.protect_open_trades}; default final RR: {self.protection_final_rr:g}.")
        print(f"Max ORB trades per day: {self.max_trades_per_day if self.max_trades_per_day > 0 else 'unlimited'}.")
        print(
            f"Best setup selector: {self.best_setup_selector}; "
            f"candidate limit: {self.best_setup_candidate_limit if self.best_setup_candidate_limit > 0 else 'unlimited'}."
        )
        print(f"Live trading: {self.live_trading}; ORB_PLACE_TRADES: {self.place_trades}; ORB_PLACE_PENDING: {self.place_pending}")
        print(f"State: {STATE_PATH}")
        print("Press Ctrl+C to stop.")
        while True:
            payload = self.run_once()
            protection = payload.get("trade_protection") or {}
            print(
                f"[{payload['checked_at']}] prepared={payload['prepared_count']} "
                f"sent={payload['placement_count']} blocked={len(payload['blocked'])} errors={len(payload['errors'])} "
                f"protected={protection.get('modified_count', 0)}/{protection.get('checked_count', 0)}"
            )
            self._print_cycle_details(payload)
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
