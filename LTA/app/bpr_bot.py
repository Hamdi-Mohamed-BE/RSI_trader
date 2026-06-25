from __future__ import annotations

import atexit
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import time
from typing import Any

from .bpr_strategy import generate_bpr_signals, settings_from_env
from .bpr_strategy import BPRSettings
from .config import REPORTS_DIR, load_config
from .models import TRADE_SYMBOLS
from .mt5_client import MT5Client


BPR_MAGIC = 26062540
BPR_DIR = REPORTS_DIR / "bpr_bot"
BPR_DIR.mkdir(parents=True, exist_ok=True)
STATE_PATH = BPR_DIR / "bpr_state.json"
EVENTS_PATH = BPR_DIR / "bpr_events.jsonl"
LATEST_PATH = BPR_DIR / "latest.json"
LOCK_PATH = BPR_DIR / "bpr.lock"
HEARTBEAT_PATH = BPR_DIR / "bpr_heartbeat.json"


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


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except ValueError:
        return default


def _env_list(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def _env_float_map(name: str) -> dict[str, float]:
    value = os.getenv(name, "")
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


def _env_pair_float_map(name: str) -> dict[tuple[str, str], float]:
    value = os.getenv(name, "")
    result: dict[tuple[str, str], float] = {}
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        separator = ":" if ":" in item else "=" if "=" in item else None
        if not separator:
            continue
        raw_key, raw_value = item.split(separator, 1)
        key_separator = "." if "." in raw_key else "@" if "@" in raw_key else None
        if not key_separator:
            continue
        symbol, timeframe = raw_key.split(key_separator, 1)
        try:
            result[(symbol.strip().upper(), timeframe.strip().upper())] = float(raw_value.strip())
        except ValueError:
            continue
    return result


def _env_symbol_timeframes(name: str) -> dict[str, tuple[str, ...]]:
    value = os.getenv(name, "")
    result: dict[str, tuple[str, ...]] = {}
    for raw_item in value.split(","):
        item = raw_item.strip()
        if not item:
            continue
        separator = ":" if ":" in item else "=" if "=" in item else None
        if not separator:
            continue
        symbol, raw_values = item.split(separator, 1)
        timeframes = tuple(part.strip().upper() for part in raw_values.replace(";", "|").split("|") if part.strip())
        if timeframes:
            result[symbol.strip().upper()] = timeframes
    return result


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "consumed": {}, "placed": []}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "consumed": {}, "placed": []}
    if not isinstance(data, dict):
        return {"created_at": datetime.now().isoformat(timespec="seconds"), "consumed": {}, "placed": []}
    data.setdefault("consumed", {})
    data.setdefault("placed", [])
    return data


def _write_state(state: dict[str, Any]) -> None:
    state["updated_at"] = datetime.now().isoformat(timespec="seconds")
    _write_json(STATE_PATH, state)


def _signal_key(signal: dict[str, Any]) -> str:
    bpr = signal.get("bpr") or {}
    return "|".join(
        [
            str(signal.get("symbol") or ""),
            str(signal.get("timeframe") or ""),
            str(signal.get("direction") or ""),
            str(signal.get("execution_type") or ""),
            str(bpr.get("key") or ""),
            str(signal.get("trigger_price") or signal.get("entry") or ""),
        ]
    )


class BPRLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            raise RuntimeError("BPR bot is already running or the lock file still exists.")
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
                {"pid": os.getpid(), "status": "stopped", "updated_at": datetime.now().isoformat(timespec="seconds")},
            )
            self.path.unlink(missing_ok=True)
            self.acquired = False


class BPRBot:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = MT5Client()
        self.symbols = _env_list("BPR_SYMBOLS", TRADE_SYMBOLS)
        self.timeframes = _env_list("BPR_TIMEFRAMES", ("M15", "M30"))
        self.symbol_timeframes = _env_symbol_timeframes("BPR_SYMBOL_TIMEFRAMES")
        self.lookback_days = max(3, _env_int("BPR_LOOKBACK_DAYS", 10))
        self.interval_seconds = max(10, _env_int("BPR_SCAN_INTERVAL_SECONDS", 60))
        self.live_trading = _env_bool("BPR_LIVE_TRADING", self.config.live_trading)
        self.place_trades = _env_bool("BPR_PLACE_TRADES", False)
        self.place_pending = _env_bool("BPR_PLACE_PENDING", False)
        self.one_position_per_symbol = _env_bool("BPR_ONE_POSITION_PER_SYMBOL", True)
        self.one_pending_per_symbol = _env_bool("BPR_ONE_PENDING_PER_SYMBOL", True)
        self.max_trades_per_day = max(0, _env_int("BPR_MAX_TRADES_PER_DAY", 3))
        self.risk_percent = max(0.0, _env_float("BPR_MAX_LOT_RISK_PCT", self.config.max_lot_risk_pct))
        self.max_spread_risk_percent = max(0.0, _env_float("BPR_MAX_SPREAD_RISK_PERCENT", self.config.max_spread_risk_percent))
        self.max_spread_points = max(0.0, _env_float("BPR_MAX_SPREAD_POINTS", self.config.max_spread_points))
        self.pending_expiry_minutes = max(0, _env_int("BPR_PENDING_EXPIRY_MINUTES", 180))
        self.log_detail_limit = max(0, _env_int("BPR_LOG_DETAIL_LIMIT", 8))
        self.settings = settings_from_env()
        self.symbol_rr = _env_float_map("BPR_SYMBOL_RR")
        self.symbol_min_score = _env_float_map("BPR_SYMBOL_MIN_SCORE")
        self.timeframe_rr = _env_pair_float_map("BPR_TIMEFRAME_RR")
        self.timeframe_min_score = _env_pair_float_map("BPR_TIMEFRAME_MIN_SCORE")
        self.state = _read_state()
        _write_state(self.state)

    def _settings_for_symbol(self, symbol: str, timeframe: str | None = None) -> BPRSettings:
        base = self.settings
        pair = (symbol.upper(), str(timeframe or "").upper())
        return BPRSettings(
            reward_risk=max(0.5, float(self.timeframe_rr.get(pair, self.symbol_rr.get(symbol.upper(), base.reward_risk)))),
            min_score=max(0, int(self.timeframe_min_score.get(pair, self.symbol_min_score.get(symbol.upper(), base.min_score)))),
            fvg_lookback_bars=base.fvg_lookback_bars,
            min_gap_atr=base.min_gap_atr,
            min_displacement_atr=base.min_displacement_atr,
            stop_atr_buffer=base.stop_atr_buffer,
            max_zone_atr=base.max_zone_atr,
            allow_pending=base.allow_pending,
            max_signal_age_bars=base.max_signal_age_bars,
        )

    def _timeframes_for_symbol(self, symbol: str) -> tuple[str, ...]:
        return self.symbol_timeframes.get(symbol.upper(), self.timeframes)

    def _placed_today_count(self) -> int:
        today = datetime.now().date().isoformat()
        count = 0
        for item in self.state.get("placed", []):
            if str(item.get("placed_at") or "")[:10] == today:
                count += 1
        return count

    def _signal_to_order(self, signal: dict[str, Any], lot: float, live: bool) -> dict[str, Any]:
        order = self.client.prepare_order(signal, lot=lot, live_trading=live)
        order["magic"] = BPR_MAGIC
        order["comment"] = f"BPR S{int(signal.get('setup_score') or 0)} {signal.get('timeframe')}"[:31]
        if order.get("execution_type") == "PENDING" and self.pending_expiry_minutes > 0:
            order["expires_at"] = (datetime.now() + timedelta(minutes=self.pending_expiry_minutes)).isoformat(timespec="seconds")
        return order

    def run_once(self) -> dict[str, Any]:
        now = datetime.now()
        prepared: list[dict[str, Any]] = []
        placed: list[dict[str, Any]] = []
        blocked: list[dict[str, Any]] = []
        candidates: list[dict[str, Any]] = []
        placed_today = self._placed_today_count()

        for symbol in self.symbols:
            for timeframe in self._timeframes_for_symbol(symbol):
                symbol_settings = self._settings_for_symbol(symbol, timeframe)
                start = now - timedelta(days=self.lookback_days)
                candles = self.client.fetch_candles(symbol, timeframe, start, now)
                if candles is None or len(candles) < 120:
                    blocked.append({"symbol": symbol, "timeframe": timeframe, "reason": "not enough candle history"})
                    continue
                signals = generate_bpr_signals(candles, symbol, timeframe, symbol_settings, include_pending=True)
                if signals:
                    candidates.extend(signals[-3:])

        candidates.sort(key=lambda item: (float(item.get("setup_score") or 0), item.get("opened_at") or now), reverse=True)
        for signal in candidates:
            key = _signal_key(signal)
            symbol = str(signal.get("symbol") or "")
            is_pending = str(signal.get("execution_type") or "").upper() == "PENDING"
            will_send = self.live_trading and ((is_pending and self.place_pending) or ((not is_pending) and self.place_trades))
            reasons: list[str] = []
            if key in self.state.get("consumed", {}):
                reasons.append("BPR signal was already consumed.")
            if self.max_trades_per_day > 0 and placed_today + len(placed) >= self.max_trades_per_day:
                reasons.append(f"BPR daily trade cap reached: {self.max_trades_per_day}.")
            open_any = self.client.open_positions(symbol)
            open_magic = self.client.open_positions(symbol, magic=BPR_MAGIC)
            pending_magic = self.client.pending_orders(symbol, magic=BPR_MAGIC)
            if self.one_position_per_symbol and open_any:
                reasons.append("An open position already exists on this symbol.")
            elif open_magic:
                reasons.append("An open BPR position already exists on this symbol.")
            if is_pending and self.one_pending_per_symbol and pending_magic:
                reasons.append("A BPR pending order already exists on this symbol.")
            if reasons:
                blocked.append({"signal": signal, "reasons": reasons})
                continue

            spread_check = self.client.spread_check(
                signal,
                max_spread_risk_percent=self.max_spread_risk_percent,
                max_spread_points=self.max_spread_points,
            )
            if not spread_check.get("ok"):
                blocked.append({"signal": signal, "reasons": spread_check.get("reasons") or [spread_check.get("message")], "spread_check": spread_check})
                continue
            lot_sizing = self.client.risk_based_lot(
                signal,
                risk_percent=self.risk_percent,
                fallback_balance=self.config.starting_balance,
                require_account_balance=will_send,
                quote=spread_check.get("quote"),
            )
            if not lot_sizing.get("ok"):
                blocked.append({"signal": signal, "reasons": [lot_sizing.get("message")], "lot_sizing": lot_sizing})
                continue
            order = self._signal_to_order(signal, float(lot_sizing["lot"]), will_send)
            order["spread_check"] = spread_check
            order["lot_sizing"] = lot_sizing
            order["spread_limits"] = {
                "max_spread_risk_percent": self.max_spread_risk_percent,
                "max_spread_points": self.max_spread_points,
            }
            ticket = {
                "created_at": now.isoformat(timespec="seconds"),
                "status": "prepared",
                "key": key,
                "signal": signal,
                "order": order,
                "will_send_to_mt5": will_send,
            }
            prepared.append(ticket)
            _append_jsonl(EVENTS_PATH, {"event": "bpr_order_prepared", **ticket})
            if will_send:
                placement = self.client.place_pending_order(order) if is_pending else self.client.place_order(order)
                placed_ticket = {**ticket, "status": "sent_to_mt5", "placement": placement}
                placed.append(placed_ticket)
                _append_jsonl(EVENTS_PATH, {"event": "bpr_order_sent_to_mt5", **placed_ticket})
                if placement.get("placed"):
                    self.state.setdefault("consumed", {})[key] = now.isoformat(timespec="seconds")
                    self.state.setdefault("placed", []).append(
                        {
                            "placed_at": now.isoformat(timespec="seconds"),
                            "symbol": symbol,
                            "timeframe": signal.get("timeframe"),
                            "direction": signal.get("direction"),
                            "ticket": (placement.get("result") or {}).get("order") or (placement.get("result") or {}).get("deal"),
                            "key": key,
                        }
                    )
                    _write_state(self.state)
            else:
                self.state.setdefault("consumed", {})[key] = now.isoformat(timespec="seconds")
                _write_state(self.state)

        payload = {
            "checked_at": now.isoformat(timespec="seconds"),
            "symbols": list(self.symbols),
            "timeframes": list(self.timeframes),
            "symbol_timeframes": {key: list(value) for key, value in self.symbol_timeframes.items()},
            "live_trading": self.live_trading,
            "place_trades": self.place_trades,
            "place_pending": self.place_pending,
            "risk_percent": self.risk_percent,
            "settings": self.settings.__dict__,
            "symbol_rr": self.symbol_rr,
            "symbol_min_score": self.symbol_min_score,
            "timeframe_rr": {f"{symbol}.{timeframe}": value for (symbol, timeframe), value in self.timeframe_rr.items()},
            "timeframe_min_score": {f"{symbol}.{timeframe}": value for (symbol, timeframe), value in self.timeframe_min_score.items()},
            "candidates": len(candidates),
            "prepared_count": len(prepared),
            "placed_count": len(placed),
            "blocked_count": len(blocked),
            "prepared": prepared[: self.log_detail_limit],
            "placed": placed[: self.log_detail_limit],
            "blocked": blocked[: self.log_detail_limit],
        }
        _write_json(LATEST_PATH, payload)
        _write_json(HEARTBEAT_PATH, {"pid": os.getpid(), "status": "running", "updated_at": now.isoformat(timespec="seconds"), "payload": payload})
        return payload

    def loop(self) -> None:
        print("BPR bot starting.")
        print(f"Symbols: {', '.join(self.symbols)} | timeframes: {', '.join(self.timeframes)}")
        print(f"Live trading: {self.live_trading}; place market: {self.place_trades}; place pending: {self.place_pending}")
        print(f"Risk: {self.risk_percent:g}% | RR: 1:{self.settings.reward_risk:g}")
        print("Press Ctrl+C to stop.")
        while True:
            payload = self.run_once()
            print(
                f"[{payload['checked_at']}] candidates={payload['candidates']} "
                f"prepared={payload['prepared_count']} placed={payload['placed_count']} "
                f"blocked={payload['blocked_count']}"
            )
            for item in payload["prepared"][: self.log_detail_limit]:
                signal = item.get("signal") or {}
                order = item.get("order") or {}
                pending_text = f" {order.get('pending_order_type')}@{order.get('trigger_price')}" if order.get("execution_type") == "PENDING" else ""
                print(
                    f"  prepared {signal.get('symbol')} {signal.get('timeframe')} {signal.get('direction')} "
                    f"S{signal.get('setup_score')} lot={order.get('lot')}{pending_text}"
                )
            time.sleep(self.interval_seconds)


def main() -> None:
    lock = BPRLock(LOCK_PATH)
    lock.acquire()
    try:
        BPRBot().loop()
    finally:
        lock.release()


if __name__ == "__main__":
    main()
