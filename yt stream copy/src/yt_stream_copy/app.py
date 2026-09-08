from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl
from yt_dlp import YoutubeDL

from .config import settings
from .interpreter import ContextInterpreter
from .mt5_bridge import account_summary, current_price, size_for_risk
from .store import Store
from .stream_worker import StreamWorker
from .vision import read_trading_screen


app = FastAPI(title="YT Stream Copy", version="0.1.0")
store = Store(settings.data_dir / "monitor.db")
active_session_id: int | None = None
active_channel = "Unknown"
context = ContextInterpreter(active_channel)


def on_transcript(text: str, frame_path: str | None) -> None:
    if active_session_id is None:
        return
    store.add_transcript(active_session_id, text, frame_path)
    signal = context.feed(text)
    if not signal:
        return
    if signal.get("status") == "exit_reported":
        opened = store.latest_open_signal(active_session_id, signal.get("symbol"))
        if opened:
            changes: dict[str, Any] = {
                "status": "paper_closed",
                "reason": f"{opened.get('reason', '')} Explicit stream exit detected.".strip(),
            }
            try:
                closing_side = "sell" if opened.get("side") == "buy" else "buy"
                changes["take_profit"] = opened.get("take_profit")
                quote = current_price(opened["symbol"], closing_side)
                changes["reason"] += f" Paper exit quote {quote['entry']}."
            except Exception:
                pass
            store.update_signal(opened["id"], changes)
            return
        store.add_signal(active_session_id, signal, frame_path)
        return

    if signal.get("status") == "level_update":
        opened = store.latest_open_signal(active_session_id, signal.get("symbol"))
        if opened:
            changes = {key: signal[key] for key in ("entry", "stop_loss", "take_profit") if signal.get(key) is not None}
            changes["reason"] = f"{opened.get('reason', '')} Later spoken trade level attached."
            merged_entry = changes.get("entry", opened.get("entry"))
            merged_stop = changes.get("stop_loss", opened.get("stop_loss"))
            if settings.auto_paper and merged_entry is not None and merged_stop is not None:
                try:
                    changes.update(size_for_risk(opened["symbol"], opened["side"], merged_entry, merged_stop, settings.risk_percent))
                    changes["status"] = "paper_open"
                except Exception as exc:
                    changes["reason"] += f" Paper sizing failed: {exc}."
            store.update_signal(opened["id"], changes)
            return
        store.add_signal(active_session_id, signal, frame_path)
        return

    if signal.get("status") != "confirmed_entry":
        store.add_signal(active_session_id, signal, frame_path)
        return

    if not signal.get("symbol") or not signal.get("side"):
        store.add_signal(active_session_id, signal, frame_path)
        return
    recent = store.recent_entry(active_session_id, signal["symbol"], signal["side"])
    if recent:
        changes = {key: signal[key] for key in ("stop_loss", "take_profit") if signal.get(key) is not None and recent.get(key) is None}
        if changes:
            store.update_signal(recent["id"], changes)
        return
    if signal.get("entry") is None:
        try:
            signal.update(current_price(signal["symbol"], signal["side"]))
            signal["reason"] += " Entry captured from the connected MT5 quote."
        except Exception as exc:
            signal["reason"] += f" Live quote unavailable: {exc}."
    signal_id = store.add_signal(active_session_id, signal, frame_path)
    if settings.auto_paper:
        if signal.get("stop_loss") is None:
            store.update_signal(signal_id, {
                "status": "paper_open_unprotected",
                "volume": settings.no_sl_paper_volume,
                "reason": signal["reason"] + (
                    f" No stop was stated; temporary paper volume is {settings.no_sl_paper_volume:g} lot. "
                    "It will be replaced by 1% risk sizing when a valid stop becomes available."
                ),
            })
        elif signal.get("entry") is not None:
            try:
                sizing = size_for_risk(signal["symbol"], signal["side"], signal["entry"], signal["stop_loss"], settings.risk_percent)
                store.update_signal(signal_id, {**sizing, "status": "paper_open"})
            except Exception as exc:
                store.update_signal(signal_id, {"status": "paper_open", "reason": f"{signal['reason']} Paper sizing failed: {exc}"})


def on_frame(frame_path: str) -> None:
    if active_session_id is None or not settings.screen_ocr:
        return
    try:
        read = read_trading_screen(frame_path)
        if read["text"]:
            store.add_screen_read(active_session_id, frame_path, read["text"], read["prices"])
        opened = store.latest_open_signal(active_session_id)
        if not opened:
            return
        changes = {
            key: read[key] for key in ("entry", "stop_loss", "take_profit")
            if read.get(key) is not None and opened.get(key) is None
        }
        if changes:
            changes["reason"] = f"{opened.get('reason', '')} Missing level recovered from labelled stream screen text."
            merged_entry = changes.get("entry", opened.get("entry"))
            merged_stop = changes.get("stop_loss", opened.get("stop_loss"))
            if settings.auto_paper and merged_entry is not None and merged_stop is not None:
                try:
                    changes.update(size_for_risk(opened["symbol"], opened["side"], merged_entry, merged_stop, settings.risk_percent))
                    changes["status"] = "paper_open"
                except Exception as exc:
                    changes["reason"] += f" Paper sizing failed: {exc}."
            store.update_signal(opened["id"], changes)
    except Exception:
        # Screen reading is supplementary; audio monitoring must never stop because OCR failed.
        return


worker = StreamWorker(
    settings.data_dir, settings.whisper_model, settings.whisper_device,
    settings.chunk_seconds, settings.frame_seconds, on_transcript, on_frame,
)


class StartRequest(BaseModel):
    url: HttpUrl


class TranscriptRequest(BaseModel):
    text: str


class SignalUpdate(BaseModel):
    symbol: str | None = None
    side: str | None = None
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    status: str | None = None
    reason: str | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "web" / "index.html")


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    data = store.dashboard()
    data["mt5"] = account_summary()
    data["worker"] = {"running": bool(worker.thread and worker.thread.is_alive()), "error": worker.error}
    data["risk_percent"] = settings.risk_percent
    data["no_sl_paper_volume"] = settings.no_sl_paper_volume
    data["auto_paper"] = settings.auto_paper
    return data


@app.post("/api/session/start")
def start(request: StartRequest) -> dict[str, Any]:
    global active_session_id, active_channel
    if worker.thread and worker.thread.is_alive():
        raise HTTPException(409, "A stream is already running")
    try:
        with YoutubeDL({
            "quiet": True,
            "skip_download": True,
            "noplaylist": True,
            "ignore_no_formats_error": True,
        }) as ydl:
            info = ydl.extract_info(str(request.url), download=False)
        active_channel = info.get("channel") or info.get("uploader") or "Unknown"
        title = info.get("title") or ""
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(400, f"Could not inspect the YouTube stream: {exc}") from exc
    active_session_id = store.create_session(str(request.url), active_channel, title)
    context.reset(active_channel)
    worker.error = None
    worker.start(str(request.url), active_session_id)
    return {"ok": True, "session_id": active_session_id, "channel": active_channel, "title": title}


@app.post("/api/session/stop")
def stop() -> dict[str, bool]:
    global active_session_id
    worker.stop()
    if active_session_id is not None:
        store.stop_session(active_session_id)
    active_session_id = None
    return {"ok": True}


@app.post("/api/transcript")
def add_transcript(request: TranscriptRequest) -> dict[str, Any]:
    if active_session_id is None:
        raise HTTPException(409, "Start a session first")
    on_transcript(request.text, None)
    return {"ok": True}


@app.patch("/api/signals/{signal_id}")
def update_signal(signal_id: int, request: SignalUpdate) -> dict[str, bool]:
    store.update_signal(signal_id, request.model_dump(exclude_none=True))
    return {"ok": True}


@app.post("/api/signals/{signal_id}/approve")
def approve(signal_id: int) -> dict[str, Any]:
    signal = next((item for item in store.dashboard()["signals"] if item["id"] == signal_id), None)
    if not signal:
        raise HTTPException(404, "Signal not found")
    required = (signal.get("symbol"), signal.get("side"), signal.get("entry"), signal.get("stop_loss"))
    if any(value is None for value in required):
        raise HTTPException(422, "Symbol, side, entry and stop loss are required")
    try:
        sizing = size_for_risk(signal["symbol"], signal["side"], signal["entry"], signal["stop_loss"], settings.risk_percent)
    except Exception as exc:
        raise HTTPException(422, str(exc)) from exc
    store.update_signal(signal_id, {**sizing, "status": "approved"})
    return {"ok": True, **sizing, "comment": signal.get("mt5_comment")}


@app.post("/api/signals/{signal_id}/reject")
def reject(signal_id: int) -> dict[str, bool]:
    store.update_signal(signal_id, {"status": "rejected"})
    return {"ok": True}
