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
from .sats_strategy import SatsSettings, simulate_sats_trades


BOT_DIR = REPORTS_DIR / "sats_bot"
STATE_PATH = BOT_DIR / "state.json"
LATEST_PATH = BOT_DIR / "latest.json"
EVENTS_PATH = BOT_DIR / "events.jsonl"
LOCK_PATH = BOT_DIR / "worker.lock"
MAGIC_NUMBER = 26071312


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


def _env_symbols(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _append_event(payload: dict[str, Any]) -> None:
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str) + "\n")


def _read_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"signals": {}}
    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"signals": {}}
    data.setdefault("signals", {})
    return data


class WorkerLock:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.acquired = False

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        stale_seconds = max(120, _env_int("SATS_LOCK_STALE_SECONDS", 900))
        if self.path.exists() and time.time() - self.path.stat().st_mtime < stale_seconds:
            raise RuntimeError("SATS worker is already running or its lock is still fresh.")
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


class SatsBot:
    def __init__(self) -> None:
        self.config = load_config()
        self.client = MT5Client()
        self.symbols = _env_symbols("SATS_SYMBOLS", ("BTCUSD", "XAUUSD", "US30", "US100"))
        self.timeframe = os.getenv("SATS_TIMEFRAME", "M15").strip().upper() or "M15"
        self.history_days = max(3, _env_int("SATS_HISTORY_DAYS", 35))
        self.interval_seconds = max(10, _env_int("SATS_SCAN_INTERVAL_SECONDS", 60))
        self.live_trading = _env_bool("SATS_LIVE_TRADING", False)
        self.place_orders = _env_bool("SATS_PLACE_ORDERS", False)
        self.entry_mode = (os.getenv("SATS_ENTRY_MODE") or "SINGLE_AVERAGED").strip().upper()
        if self.entry_mode not in {"SINGLE_AVERAGED", "THREE_LEG_SPLIT"}:
            self.entry_mode = "SINGLE_AVERAGED"
        self.max_age_bars = max(1, _env_int("SATS_SIGNAL_MAX_AGE_BARS", 2))
        self.risk_percent = max(0.0, _env_float("SATS_RISK_PERCENT", self.config.max_lot_risk_pct))
        self.static_lot = max(0.0, _env_float("SATS_STATIC_LOT", self.config.static_lot))
        self.settings = SatsSettings(
            min_score=max(0.0, _env_float("SATS_MIN_SCORE", 60.0)),
            min_tqi=max(0.0, _env_float("SATS_MIN_TQI", 0.35)),
            tp_mode=os.getenv("SATS_TP_MODE", "Fixed"),
            trade_timeout_bars=max(5, _env_int("SATS_TRADE_TIMEOUT_BARS", 100)),
        )
        self.state = _read_state()

    def _signal_key(self, symbol: str, signal: dict[str, Any]) -> str:
        return f"{symbol}|{self.timeframe}|{signal['side']}|{signal['entry_time']}"

    def _lot_for_signal(
        self,
        signal: dict[str, Any],
        risk_percent: float | None = None,
        static_lot: float | None = None,
    ) -> dict[str, Any]:
        order_signal = {
            "symbol": signal["symbol"],
            "direction": signal["side"],
            "entry": signal["entry"],
            "stop_loss": signal["stop_loss"],
            "take_profit": signal["tp3"],
        }
        if (os.getenv("SATS_LOT_SIZING_MODE") or self.config.lot_sizing_mode).strip().upper() == "RISK_PERCENT":
            return self.client.risk_based_lot(
                order_signal,
                risk_percent=self.risk_percent if risk_percent is None else risk_percent,
                fallback_balance=self.config.starting_balance,
                require_account_balance=self.live_trading and self.place_orders,
            )
        return self.client.static_lot_sizing(
            order_signal,
            configured_lot=self.static_lot if static_lot is None else static_lot,
        )

    def _target_plan(self, signal: dict[str, Any]) -> list[dict[str, Any]]:
        if self.entry_mode != "THREE_LEG_SPLIT":
            return [{"leg": 1, "take_profit": signal["tp3"], "risk_share": 1.0}]
        return [
            {"leg": 1, "take_profit": signal["tp1"], "risk_share": 1.0 / 3.0},
            {"leg": 2, "take_profit": signal["tp2"], "risk_share": 1.0 / 3.0},
            {"leg": 3, "take_profit": signal["tp3"], "risk_share": 1.0 / 3.0},
        ]

    def scan_once(self) -> dict[str, Any]:
        now = datetime.now()
        start = now - timedelta(days=self.history_days)
        results: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        errors: list[dict[str, Any]] = []
        for symbol in self.symbols:
            try:
                candles = self.client.fetch_candles(symbol, self.timeframe, start, now, max_bars=200000)
                if candles is None or len(candles) < 300:
                    errors.append({"symbol": symbol, "error": f"Insufficient history: {0 if candles is None else len(candles)}"})
                    continue
                trades, frame = simulate_sats_trades(candles, symbol, self.settings)
                signals = list(frame.attrs.get("signals", []))
                latest_signal = signals[-1] if signals else None
                payload = {
                    "symbol": symbol,
                    "timeframe": self.timeframe,
                    "signals": len(signals),
                    "latest_signal": latest_signal,
                }
                results.append(payload)
                if not latest_signal:
                    continue
                age_bars = len(frame) - 1 - int(latest_signal["index"])
                if age_bars > self.max_age_bars:
                    continue
                signal = {
                    "symbol": symbol,
                    "side": latest_signal["side"],
                    "entry_time": str(latest_signal["time"]),
                    "entry": float(latest_signal["entry"]),
                    "stop_loss": float(latest_signal["stop_loss"]),
                    "tp1": float(latest_signal["tp1"]),
                    "tp2": float(latest_signal["tp2"]),
                    "tp3": float(latest_signal["tp3"]),
                    "score": float(latest_signal["score"]),
                    "tqi": float(latest_signal["tqi"]),
                }
                key = self._signal_key(symbol, signal)
                if self.state["signals"].get(key):
                    continue
                action: dict[str, Any] = {"signal": signal, "entry_mode": self.entry_mode, "legs": []}
                for target in self._target_plan(signal):
                    sizing = self._lot_for_signal(
                        signal,
                        risk_percent=self.risk_percent * float(target["risk_share"]),
                        static_lot=self.static_lot * float(target["risk_share"]),
                    )
                    leg_action: dict[str, Any] = {"leg": target["leg"], "take_profit": target["take_profit"], "sizing": sizing}
                    if not sizing.get("ok"):
                        action["legs"].append(leg_action)
                        continue
                    prepared = self.client.prepare_order(
                        {
                            "symbol": symbol,
                            "direction": signal["side"],
                            "entry": signal["entry"],
                            "stop_loss": signal["stop_loss"],
                            "take_profit": target["take_profit"],
                            "timeframe": self.timeframe,
                            "setup_score": signal["score"],
                            "setup_grade": "SATS",
                        },
                        lot=float(sizing["lot"]),
                        live_trading=self.live_trading and self.place_orders,
                    )
                    prepared["magic"] = MAGIC_NUMBER
                    prepared["comment"] = f"SATS {symbol} {self.timeframe} L{target['leg']}"[:31]
                    leg_action["prepared"] = prepared
                    if self.live_trading and self.place_orders:
                        leg_action["result"] = self.client.place_order(prepared)
                    else:
                        leg_action["result"] = {"placed": False, "message": "SATS live trading/place orders disabled."}
                    action["legs"].append(leg_action)
                self.state["signals"][key] = {
                    "seen_at": now.isoformat(timespec="seconds"),
                    "entry_mode": self.entry_mode,
                    "placed": any(bool((leg.get("result") or {}).get("placed")) for leg in action["legs"]),
                }
                actions.append(action)
            except Exception as exc:
                errors.append({"symbol": symbol, "error": str(exc)})
        _write_json(STATE_PATH, self.state)
        payload = {
            "time": now.isoformat(timespec="seconds"),
            "live_trading": self.live_trading,
            "place_orders": self.place_orders,
            "symbols": self.symbols,
            "timeframe": self.timeframe,
            "entry_mode": self.entry_mode,
            "results": results,
            "actions": actions,
            "errors": errors,
        }
        _write_json(LATEST_PATH, payload)
        _append_event(payload)
        return payload

    def run_forever(self) -> None:
        while True:
            started = time.time()
            payload = self.scan_once()
            fresh = len(payload["actions"])
            print(
                f"[{payload['time']}] SATS scanned={len(payload['results'])} "
                f"fresh_actions={fresh} errors={len(payload['errors'])} "
                f"live={self.live_trading and self.place_orders}"
            )
            for action in payload["actions"][:5]:
                sig = action["signal"]
                first_result = ((action.get("legs") or [{}])[0].get("result") or {})
                print(
                    f"  {sig['symbol']} {sig['side']} score={sig['score']:.1f} "
                    f"tqi={sig['tqi']:.2f} entry={sig['entry']:.5f} "
                    f"sl={sig['stop_loss']:.5f} tp={sig['tp3']:.5f} "
                    f"legs={len(action.get('legs') or [])} placed={first_result.get('placed')} "
                    f"msg={first_result.get('message')}"
                )
            elapsed = time.time() - started
            time.sleep(max(1.0, self.interval_seconds - elapsed))


def main() -> None:
    lock = WorkerLock(LOCK_PATH)
    lock.acquire()
    try:
        SatsBot().run_forever()
    finally:
        lock.release()


if __name__ == "__main__":
    main()
