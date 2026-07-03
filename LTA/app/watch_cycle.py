from __future__ import annotations

from datetime import datetime
import json
import os
from typing import Any

from .automation import (
    HEARTBEAT_PATH,
    INSTANCE_LOCK_PATH,
    LATEST_SCAN_PATH,
    MAGIC_NUMBER,
    SingleInstanceLock,
    TradeAutomation,
)
from .config import load_config
from .mt5_client import MT5Client


def _float_list(value: str | None) -> list[float]:
    levels: list[float] = []
    for item in str(value or "").split(","):
        try:
            levels.append(float(item.strip()))
        except ValueError:
            continue
    return levels


def _read_latest() -> dict[str, Any]:
    if not LATEST_SCAN_PATH.exists():
        return {}
    try:
        return json.loads(LATEST_SCAN_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _candidate(item: dict[str, Any]) -> dict[str, Any]:
    signal = item.get("signal") if "signal" in item else item
    order = item.get("order") or {}
    return {
        "symbol": signal.get("symbol"),
        "timeframe": signal.get("timeframe"),
        "direction": signal.get("direction"),
        "score": signal.get("setup_score"),
        "grade": signal.get("setup_grade"),
        "entry_model": signal.get("entry_model"),
        "order_type": order.get("pending_order_type") or signal.get("pending_order_type"),
        "entry": order.get("trigger_price") or signal.get("trigger_price") or signal.get("entry"),
        "stop_loss": order.get("stop_loss") or signal.get("stop_loss"),
        "take_profit": order.get("take_profit") or signal.get("take_profit"),
    }


def _heartbeat_status() -> dict[str, Any]:
    if not HEARTBEAT_PATH.exists():
        return {}
    try:
        return json.loads(HEARTBEAT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def run_watch_cycle() -> dict[str, Any]:
    config = load_config()
    lock = SingleInstanceLock(INSTANCE_LOCK_PATH)
    cycle_mode = "scanned"
    lock_message = None
    try:
        lock.acquire()
    except RuntimeError as exc:
        cycle_mode = "existing_worker"
        lock_message = str(exc)
        payload = _read_latest()
    else:
        try:
            payload = TradeAutomation().run_once()
        finally:
            lock.release()

    client = MT5Client()
    quote = client.current_quote("XAUUSD") or {}
    pending = client.pending_orders("XAUUSD", magic=MAGIC_NUMBER)
    client.shutdown()

    scan = payload.get("scan") or {}
    valid_pending = [
        item
        for item in scan.get("preplace", [])
        if int(item.get("setup_score") or 0) >= 92
        and str(item.get("setup_grade") or "").upper() in {"A+", "PRE-A+"}
    ]
    reference_levels = _float_list(os.getenv("WATCH_REFERENCE_LEVELS"))
    midpoint = None
    if quote.get("bid") is not None and quote.get("ask") is not None:
        midpoint = (float(quote["bid"]) + float(quote["ask"])) / 2.0

    result = {
        "checked_at": payload.get("checked_at") or datetime.now().isoformat(timespec="seconds"),
        "mode": cycle_mode,
        "worker": _heartbeat_status(),
        "lock_message": lock_message,
        "live_trading": config.live_trading,
        "lot_mode": config.lot_sizing_mode,
        "lot": config.static_lot if config.lot_sizing_mode == "STATIC_LOT" else None,
        "risk_percent": config.max_lot_risk_pct if config.lot_sizing_mode == "RISK_PERCENT" else None,
        "quote": {
            "bid": quote.get("bid"),
            "ask": quote.get("ask"),
            "spread_points": quote.get("spread_points"),
        },
        "counts": {
            "a_plus_market": len(scan.get("allowed", [])),
            "valid_preorders": len(valid_pending),
            "prepared": int(payload.get("prepared_count") or 0),
            "placed": int(payload.get("placed_count") or 0),
            "pending_prepared": int(payload.get("pending_prepared_count") or 0),
            "pending_placed": int(payload.get("pending_placed_count") or 0),
            "blocked": int(payload.get("blocked_count") or 0),
        },
        "candidates": [_candidate(item) for item in valid_pending[:3]],
        "placed_orders": [_candidate(item) for item in payload.get("placed", [])[-3:]],
        "broker_pending": [
            {
                "ticket": item.get("ticket"),
                "direction": item.get("direction"),
                "type": item.get("type"),
                "volume": item.get("volume_current") or item.get("volume_initial"),
                "entry": item.get("price_open"),
                "stop_loss": item.get("sl"),
                "take_profit": item.get("tp"),
                "comment": item.get("comment"),
            }
            for item in pending
        ],
        "reference": {
            "label": os.getenv("WATCH_REFERENCE_LABEL", ""),
            "levels": [
                {
                    "price": level,
                    "distance": round(level - midpoint, 3) if midpoint is not None else None,
                }
                for level in reference_levels
            ],
            "execution_authority": "MT5 completed candles and the LTA 92+ gate",
        },
    }
    return result


def main() -> None:
    print(json.dumps(run_watch_cycle(), separators=(",", ":"), default=str))


if __name__ == "__main__":
    main()
