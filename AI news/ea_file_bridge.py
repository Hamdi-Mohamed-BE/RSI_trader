from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from calendar_provider import upcoming_us_events
from news_core import ROOT
from news_v9_direction import SUPPORTED_EVENTS
from predict_news import make_prediction


LOGGER = logging.getLogger("gold_news.ea_file_bridge")
BRIDGE_RELATIVE_PATH = Path("GoldNewsV9EA") / "bridge.json"
POLL_SECONDS = 5.0
_thread: threading.Thread | None = None
_stop_event = threading.Event()
_status_lock = threading.Lock()
_status: dict[str, Any] = {
    "status": "not_started",
    "path": None,
    "updated_at_utc": None,
    "message": None,
}


def _set_status(status: str, *, path: Path | None = None, message: str | None = None) -> None:
    with _status_lock:
        _status.update(
            {
                "status": status,
                "path": str(path) if path else _status.get("path"),
                "updated_at_utc": datetime.now(timezone.utc).isoformat(),
                "message": message,
            }
        )


def file_bridge_status() -> dict[str, Any]:
    with _status_lock:
        return dict(_status)


def next_event_payload(days: int = 30) -> dict[str, Any]:
    payload = upcoming_us_events(max(1, min(days, 30)))
    now = datetime.now(timezone.utc)
    unique: dict[tuple[str, str], dict[str, Any]] = {}
    for item in payload.get("events", []):
        event = str(item.get("event") or "").upper()
        if event not in SUPPORTED_EVENTS:
            continue
        try:
            release = datetime.fromisoformat(
                str(item["release_time"]).replace("Z", "+00:00")
            ).astimezone(timezone.utc)
        except (KeyError, TypeError, ValueError):
            continue
        if release <= now:
            continue
        key = (event, release.isoformat())
        candidate = {
            "event": event,
            "release_utc": release.isoformat(),
            "provider_name": item.get("provider_name"),
            "forecast": item.get("forecast"),
            "previous": item.get("previous"),
        }
        existing = unique.get(key)
        if existing is None or str(candidate.get("provider_name", "")).upper().startswith(event):
            unique[key] = candidate
    if not unique:
        return {
            "status": "NO_EVENT",
            "server_time_utc": now.isoformat(),
            "supported_events": list(SUPPORTED_EVENTS),
            "provider_status": payload.get("status"),
            "message": payload.get("message", "No supported event was found."),
        }
    selected = min(unique.values(), key=lambda row: row["release_utc"])
    return {
        "status": "OK",
        "server_time_utc": now.isoformat(),
        **selected,
        "provider": payload.get("provider"),
    }


def _resolve_common_files() -> Path:
    configured = os.getenv("GOLD_NEWS_MT5_COMMON_PATH", "").strip()
    if configured:
        return Path(configured).expanduser().resolve() / "Files"

    import MetaTrader5 as mt5

    terminal = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")
    if not mt5.initialize(path=terminal):
        raise RuntimeError(
            "GOLD_NEWS_MT5_COMMON_PATH is not set and MT5 discovery failed: "
            f"{mt5.last_error()}"
        )
    try:
        terminal_info = mt5.terminal_info()
        if terminal_info is None:
            raise RuntimeError("MT5 returned no terminal information for the file bridge.")
        return Path(terminal_info.commondata_path).resolve() / "Files"
    finally:
        mt5.shutdown()


def _locked_prediction(event: str, release: datetime) -> dict[str, Any] | None:
    path = ROOT / "predictions" / f"{release.strftime('%Y%m%dT%H%M%SZ')}-{event.lower()}.json"
    if not path.exists():
        return None
    try:
        prediction = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if prediction.get("event") != event or prediction.get("release_time_utc") != release.isoformat():
        return None
    return prediction


def _signal_fields(prediction: dict[str, Any]) -> dict[str, Any]:
    model = prediction.get("model", {})
    expected = prediction.get("expected_impulse_range_usd", {})
    return {
        "signal_status": "READY",
        "direction": prediction.get("gold_impact"),
        "confidence_pct": prediction.get("confidence_pct"),
        "confidence_tier": prediction.get("confidence_tier"),
        "action_tier": prediction.get("action_tier"),
        "active_call_allowed": model.get("active_call_allowed", False),
        "artifact_version": model.get("artifact_version"),
        "expected_min_abs_usd": expected.get("minimum_absolute_move"),
        "expected_median_abs_usd": expected.get("median_absolute_move"),
        "expected_max_abs_usd": expected.get("maximum_absolute_move"),
    }


def _write_snapshot(path: Path, snapshot: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(snapshot, separators=(",", ":")) + "\n",
        encoding="ascii",
    )
    os.replace(temporary, path)


def _bridge_loop(path: Path) -> None:
    current_identity: tuple[str, str] | None = None
    prediction: dict[str, Any] | None = None
    retry_after = datetime.min.replace(tzinfo=timezone.utc)
    while not _stop_event.is_set():
        now = datetime.now(timezone.utc)
        try:
            event_payload = next_event_payload(30)
            snapshot: dict[str, Any] = {
                "bridge_status": "OK",
                "bridge_version": 1,
                "heartbeat_epoch": int(now.timestamp()),
                **event_payload,
                "signal_status": "WAITING",
            }
            if event_payload.get("status") == "OK":
                event = str(event_payload["event"])
                release = datetime.fromisoformat(
                    str(event_payload["release_utc"]).replace("Z", "+00:00")
                ).astimezone(timezone.utc)
                identity = (event, release.isoformat())
                if identity != current_identity:
                    current_identity = identity
                    prediction = _locked_prediction(event, release)
                    retry_after = datetime.min.replace(tzinfo=timezone.utc)
                seconds_before = (release - now).total_seconds()
                if prediction is None and 480 <= seconds_before <= 900 and now >= retry_after:
                    try:
                        prediction = make_prediction(
                            event,
                            release,
                            forecast=event_payload.get("forecast"),
                            previous=event_payload.get("previous"),
                        )
                        LOGGER.info(
                            "File bridge locked %s %s at %.1f minutes before release.",
                            event,
                            prediction.get("gold_impact"),
                            seconds_before / 60,
                        )
                    except Exception as error:
                        retry_after = now + timedelta(seconds=30)
                        snapshot["signal_status"] = "ERROR"
                        snapshot["signal_error"] = str(error)
                        LOGGER.exception("File bridge prediction failed for %s.", event)
                if prediction is not None:
                    snapshot.update(_signal_fields(prediction))
                elif seconds_before < 480:
                    snapshot["signal_status"] = "MISSED"
            _write_snapshot(path, snapshot)
            _set_status("ready", path=path)
        except Exception as error:
            LOGGER.exception("MT5 file bridge update failed.")
            _set_status("error", path=path, message=str(error))
        _stop_event.wait(POLL_SECONDS)


def start_file_bridge() -> None:
    global _thread
    if _thread is not None and _thread.is_alive():
        return
    try:
        path = _resolve_common_files() / BRIDGE_RELATIVE_PATH
    except Exception as error:
        LOGGER.exception("MT5 file bridge could not resolve the common Files folder.")
        _set_status("error", message=str(error))
        return
    _stop_event.clear()
    _set_status("starting", path=path)
    _thread = threading.Thread(
        target=_bridge_loop,
        args=(path,),
        name="gold-news-mt5-file-bridge",
        daemon=True,
    )
    _thread.start()


def stop_file_bridge() -> None:
    _stop_event.set()
    thread = _thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=POLL_SECONDS + 1)
