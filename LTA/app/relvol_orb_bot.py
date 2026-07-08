from __future__ import annotations

import atexit
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import time
from typing import Any

from .config import REPORTS_DIR, load_config
from .mt5_client import MT5Client
from .relvol_orb_strategy import latest_eligible_setups, settings_for_symbol, settings_from_env
from .session_time import zone


BOT_DIR = REPORTS_DIR / "relvol_orb_bot"
STATE_PATH = BOT_DIR / "state.json"
LATEST_PATH = BOT_DIR / "latest.json"
EVENTS_PATH = BOT_DIR / "events.jsonl"
LOCK_PATH = BOT_DIR / "worker.lock"
HEARTBEAT_PATH = BOT_DIR / "heartbeat.json"
MAGIC_NUMBER = 26070831


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _append_event(payload: dict[str, Any]) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"days": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"days": {}}
    data.setdefault("days", {})
    return data


class WorkerLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stale_seconds = max(120, _env_int("RELVOL_ORB_LOCK_STALE_SECONDS", 900))
        if self.path.exists() and time.time() - self.path.stat().st_mtime < stale_seconds:
            raise RuntimeError("Relative-volume ORB worker is already running or its lock is still fresh.")
        self.path.unlink(missing_ok=True)
        self.path.write_text(
            json.dumps({"pid": os.getpid(), "started_at": datetime.now().isoformat(timespec="seconds")}),
            encoding="utf-8",
        )
        self.acquired = True
        atexit.register(self.release)

    def touch(self) -> None:
        if self.acquired:
            self.path.touch()

    def release(self) -> None:
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False


class RelVolOrbBot:
    def __init__(self) -> None:
        self.config = load_config()
        self.settings = settings_from_env()
        self.client = MT5Client()
        self.live_trading = _env_bool("RELVOL_ORB_LIVE_TRADING", False)
        self.place_orders = _env_bool("RELVOL_ORB_PLACE_ORDERS", False)
        self.interval_seconds = max(10, _env_int("RELVOL_ORB_SCAN_INTERVAL_SECONDS", 60))
        self.lookback_days = max(30, _env_int("RELVOL_ORB_HISTORY_DAYS", 55))
        self.failsafe_target_r = max(2.0, _env_float("RELVOL_ORB_FAILSAFE_TARGET_R", 20.0))
        self.max_spread_risk_percent = max(
            0.0,
            _env_float("RELVOL_ORB_MAX_SPREAD_RISK_PERCENT", 15.0),
        )
        self.max_spread_points = max(0.0, _env_float("RELVOL_ORB_MAX_SPREAD_POINTS", 0.0))
        self.state = _read_state()

    def _local_now(self) -> datetime:
        return datetime.now(zone(self.settings.session_timezone))

    def _session_clock(self, value: str) -> int:
        try:
            hour, minute = (int(part) for part in value.split(":", 1))
        except (TypeError, ValueError):
            return 0
        return hour * 60 + minute

    @staticmethod
    def _position_direction(position: dict[str, Any]) -> str:
        return "SELL" if int(position.get("type") or 0) == 1 else "BUY"

    def _manage_session_end(self, now: datetime) -> list[dict[str, Any]]:
        actions: list[dict[str, Any]] = []
        minutes = now.hour * 60 + now.minute
        end_minutes = self._session_clock(self.settings.session_end)
        if minutes < end_minutes:
            return actions
        for order in self.client.pending_orders(magic=MAGIC_NUMBER):
            if self.live_trading and self.place_orders:
                result = self.client.cancel_pending_order(
                    int(order.get("ticket") or 0),
                    str(order.get("symbol") or ""),
                )
            else:
                result = {"ok": False, "dry_run": True, "message": "EOD pending cancellation not sent."}
            actions.append({"action": "cancel_eod_pending", "order": order, "result": result})
        for position in self.client.open_positions(magic=MAGIC_NUMBER):
            result = self.client.close_position(
                ticket=int(position.get("ticket") or 0),
                symbol=str(position.get("symbol") or ""),
                direction=self._position_direction(position),
                volume=float(position.get("volume") or 0.0),
                comment="RVORB EOD",
                live_trading=self.live_trading and self.place_orders,
            )
            actions.append({"action": "close_eod_position", "position": position, "result": result})
        return actions

    def _fetch_history(self, now: datetime) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        histories: dict[str, Any] = {}
        errors: list[dict[str, Any]] = []
        data_now = now.astimezone(zone(self.settings.data_timezone)).replace(tzinfo=None)
        start = data_now - timedelta(days=self.lookback_days)
        for symbol in self.settings.symbols:
            try:
                candles = self.client.fetch_candles(symbol, "M5", start, data_now, max_bars=100000)
            except Exception as exc:
                errors.append({"symbol": symbol, "error": str(exc)})
                continue
            if candles is None or len(candles) < 1000:
                errors.append({"symbol": symbol, "error": f"Insufficient M5 history: {0 if candles is None else len(candles)}"})
                continue
            histories[symbol] = candles
        return histories, errors

    def _leverage_capped_lot(self, symbol: str, entry: float, requested: float) -> float:
        account = self.client.account_info() or {}
        balance = float(account.get("balance") or self.config.starting_balance)
        contract_size = max(1e-12, self.client.contract_size(symbol))
        cap = balance * self.settings.max_leverage / max(entry * contract_size, 1e-12)
        return self.client.normalize_lot_down(symbol, min(requested, cap))

    def _prepare_candidate(self, setup: dict[str, Any], now: datetime) -> dict[str, Any]:
        symbol = str(setup["symbol"])
        direction = str(setup["direction"])
        trigger = float(setup["trigger_price"])
        quote = self.client.current_quote(symbol)
        if not quote:
            return {"status": "blocked_no_quote", "setup": setup}
        if direction == "BUY" and trigger <= float(quote["ask"]):
            return {"status": "blocked_trigger_already_crossed", "setup": setup, "quote": quote}
        if direction == "SELL" and trigger >= float(quote["bid"]):
            return {"status": "blocked_trigger_already_crossed", "setup": setup, "quote": quote}

        stop_fraction = float(setup.get("atr_stop_fraction") or self.settings.atr_stop_fraction)
        stop_distance = float(setup["daily_atr"]) * stop_fraction
        stop_loss = trigger - stop_distance if direction == "BUY" else trigger + stop_distance
        take_profit = (
            trigger + stop_distance * self.failsafe_target_r
            if direction == "BUY"
            else trigger - stop_distance * self.failsafe_target_r
        )
        signal = {
            "symbol": symbol,
            "direction": direction,
            "execution_type": "PENDING",
            "pending_order_type": setup["pending_order_type"],
            "trigger_price": trigger,
            "entry": trigger,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
        }
        if self.settings.lot_sizing_mode == "STATIC_LOT":
            configured_lot = float(self.settings.symbol_lots.get(symbol, 0.0))
            if configured_lot <= 0:
                return {
                    "status": "blocked_missing_static_lot",
                    "setup": setup,
                    "message": f"No RELVOL_ORB_SYMBOL_LOTS value is configured for {symbol}.",
                }
            sizing = self.client.static_lot_sizing(signal, configured_lot=configured_lot, quote=quote)
        else:
            sizing = self.client.risk_based_lot(
                signal,
                risk_percent=self.settings.risk_percent,
                fallback_balance=self.config.starting_balance,
                require_account_balance=self.live_trading and self.place_orders,
                quote=quote,
            )
        if not sizing.get("ok"):
            return {"status": "blocked_lot_sizing", "setup": setup, "sizing": sizing}
        lot = self._leverage_capped_lot(symbol, trigger, float(sizing["lot"]))
        if lot <= 0:
            return {"status": "blocked_leverage_or_minimum_lot", "setup": setup, "sizing": sizing}

        spread_check = self.client.spread_check(
            signal,
            max_spread_risk_percent=self.max_spread_risk_percent,
            max_spread_points=self.max_spread_points,
            quote=quote,
        )
        if not spread_check.get("ok"):
            return {"status": "blocked_spread", "setup": setup, "spread_check": spread_check}

        session_end = datetime.combine(
            setup["session_date"],
            time_from_string(self.settings.session_end),
            tzinfo=zone(self.settings.session_timezone),
        )
        order = {
            "live_trading": self.live_trading and self.place_orders,
            "symbol": symbol,
            "broker_symbol": self.client.resolve_symbol(symbol) or symbol,
            "direction": direction,
            "execution_type": "PENDING",
            "pending_order_type": setup["pending_order_type"],
            "trigger_price": trigger,
            "entry": trigger,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "lot": lot,
            "magic": MAGIC_NUMBER,
            "comment": f"RVORB {symbol} {direction[0]}"[:31],
            "expires_at": session_end,
            "spread_limits": {
                "max_spread_risk_percent": self.max_spread_risk_percent,
                "max_spread_points": self.max_spread_points,
            },
        }
        placement = self.client.place_pending_order(order)
        return {
            "status": "placed" if placement.get("placed") else "prepared",
            "setup": {key: value for key, value in setup.items() if key != "future_bars"},
            "order": order,
            "sizing": sizing,
            "spread_check": spread_check,
            "placement": placement,
        }

    def run_once(self) -> dict[str, Any]:
        now = self._local_now()
        _write_json(
            HEARTBEAT_PATH,
            {"pid": os.getpid(), "status": "scanning", "updated_at": now.isoformat(timespec="seconds")},
        )
        eod_actions = self._manage_session_end(now)
        minutes = now.hour * 60 + now.minute
        minimum_range = min(
            settings_for_symbol(self.settings, symbol).range_minutes
            for symbol in self.settings.symbols
        )
        range_end = self._session_clock(self.settings.session_start) + minimum_range
        session_end = self._session_clock(self.settings.session_end)
        results: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        if now.weekday() < 5 and range_end <= minutes < session_end:
            histories, errors = self._fetch_history(now)
            candidates = latest_eligible_setups(histories, self.settings, session_day=now.date())
            day_state = self.state.setdefault("days", {}).setdefault(str(now.date()), {})
            for setup in candidates:
                symbol = str(setup["symbol"])
                if symbol in day_state:
                    results.append({"status": "blocked_already_processed_today", "symbol": symbol})
                    continue
                if self.client.open_positions(symbol, magic=MAGIC_NUMBER) or self.client.pending_orders(
                    symbol, magic=MAGIC_NUMBER
                ):
                    results.append({"status": "blocked_existing_exposure", "symbol": symbol})
                    continue
                result = self._prepare_candidate(setup, now)
                results.append(result)
                if result["status"] in {"placed", "blocked_trigger_already_crossed"}:
                    day_state[symbol] = {
                        "status": result["status"],
                        "updated_at": now.isoformat(timespec="seconds"),
                    }
        _write_json(STATE_PATH, self.state)
        payload = {
            "checked_at": now.isoformat(timespec="seconds"),
            "paper_strategy": "relative-volume opening-range breakout",
            "symbols": list(self.settings.symbols),
            "range_minutes": self.settings.range_minutes,
            "relative_volume_min": self.settings.relative_volume_min,
            "atr_stop_fraction": self.settings.atr_stop_fraction,
            "top_n": self.settings.top_n,
            "symbol_profiles": self.settings.symbol_profiles,
            "risk_percent": self.settings.risk_percent,
            "lot_sizing_mode": self.settings.lot_sizing_mode,
            "symbol_lots": self.settings.symbol_lots,
            "live_trading": self.live_trading,
            "place_orders": self.place_orders,
            "candidate_count": len(candidates),
            "candidates": [{key: value for key, value in item.items() if key != "future_bars"} for item in candidates],
            "results": results,
            "errors": errors,
            "eod_actions": eod_actions,
        }
        _write_json(LATEST_PATH, payload)
        _append_event(payload)
        _write_json(
            HEARTBEAT_PATH,
            {"pid": os.getpid(), "status": "waiting", "updated_at": now.isoformat(timespec="seconds")},
        )
        return payload

    def run_forever(self, lock: WorkerLock) -> None:
        print("Relative-volume ORB bot started.")
        print(
            f"Symbols: {', '.join(self.settings.symbols)} | top={self.settings.top_n} | "
            f"profiles={self.settings.symbol_profiles or 'global defaults'}."
        )
        print(
            f"Live={self.live_trading}; place={self.place_orders}; risk={self.settings.risk_percent:g}% | "
            f"lots={self.settings.lot_sizing_mode}:{self.settings.symbol_lots or 'dynamic'} | "
            f"session={self.settings.session_start}-{self.settings.session_end} {self.settings.session_timezone}."
        )
        print("Press Ctrl+C to stop.")
        while True:
            lock.touch()
            payload = self.run_once()
            print(
                f"[{payload['checked_at']}] candidates={payload['candidate_count']} "
                f"results={len(payload['results'])} errors={len(payload['errors'])} "
                f"eod={len(payload['eod_actions'])}"
            )
            for item in payload["results"]:
                setup = item.get("setup") or {}
                placement = item.get("placement") or {}
                print(
                    f"  {item.get('status')} {setup.get('symbol')} {setup.get('direction')} "
                    f"RV={float(setup.get('relative_volume') or 0.0):.2f} "
                    f"entry={(item.get('order') or {}).get('trigger_price')} "
                    f"msg='{placement.get('message', '')}'"
                )
            time.sleep(self.interval_seconds)


def time_from_string(value: str):
    from datetime import time as clock_time

    try:
        hour, minute = (int(part) for part in value.split(":", 1))
    except (TypeError, ValueError):
        hour, minute = 16, 0
    return clock_time(hour=hour, minute=minute)


def main() -> None:
    lock = WorkerLock(LOCK_PATH)
    lock.acquire()
    bot = RelVolOrbBot()
    bot.run_forever(lock)


if __name__ == "__main__":
    main()
