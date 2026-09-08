from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

from yt_dlp import YoutubeDL


class StreamWorker:
    def __init__(self, data_dir: Path, model_name: str, device: str, chunk_seconds: int,
                 frame_seconds: int, on_text: Callable[[str, str | None], None],
                 on_frame: Callable[[str], None] | None = None):
        self.data_dir = data_dir
        self.model_name = model_name
        self.device = device
        self.chunk_seconds = chunk_seconds
        self.frame_seconds = frame_seconds
        self.on_text = on_text
        self.on_frame = on_frame
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.process: subprocess.Popen | None = None
        self.frame_process: subprocess.Popen | None = None
        self.error: str | None = None

    def start(self, url: str, session_id: int) -> None:
        if self.thread and self.thread.is_alive():
            raise RuntimeError("A stream is already running")
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, args=(url, session_id), daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.process and self.process.poll() is None:
            self.process.terminate()
        if self.frame_process and self.frame_process.poll() is None:
            self.frame_process.terminate()

    def _run(self, url: str, session_id: int) -> None:
        try:
            from faster_whisper import WhisperModel
            work = self.data_dir / f"session-{session_id}"
            work.mkdir(parents=True, exist_ok=True)
            media_url = None
            while not self.stop_event.is_set() and not media_url:
                try:
                    with YoutubeDL({"quiet": True, "no_warnings": True,
                                    "format": "best[height<=720]/best", "noplaylist": True}) as ydl:
                        info = ydl.extract_info(url, download=False)
                    media_url = info.get("url")
                except Exception as exc:
                    message = str(exc).lower()
                    if "will begin" not in message and "upcoming" not in message and "no video formats" not in message:
                        self.error = str(exc)
                if not media_url:
                    time.sleep(10)
            if self.stop_event.is_set():
                return
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("ffmpeg was not found")
            pattern = str(work / "audio-%06d.wav")
            frames = work / "frames"
            frames.mkdir(parents=True, exist_ok=True)
            self.process = subprocess.Popen([
                ffmpeg, "-hide_banner", "-loglevel", "error", "-i", media_url, "-vn", "-ac", "1", "-ar", "16000",
                "-f", "segment", "-segment_time", str(self.chunk_seconds), "-reset_timestamps", "1", pattern,
            ])
            if self.on_frame:
                self.frame_process = subprocess.Popen([
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-i", media_url, "-an",
                    "-vf", f"fps=1/{max(1, self.frame_seconds)}", "-q:v", "3",
                    str(frames / "frame-%06d.jpg"),
                ])
            model_device = self.device
            if model_device == "auto":
                model_device = "cuda" if shutil.which("nvidia-smi") else "cpu"
            compute = "int8_float16" if model_device == "cuda" else "int8"
            try:
                model = WhisperModel(self.model_name, device=model_device, compute_type=compute)
            except Exception:
                model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
            processed: set[Path] = set()
            processed_frames: set[Path] = set()
            latest_frame: Path | None = None
            while not self.stop_event.is_set():
                frame_files = [item for item in sorted(frames.glob("frame-*.jpg")) if item.stat().st_size > 0]
                if frame_files:
                    latest_frame = frame_files[-1]
                    if latest_frame not in processed_frames and self.on_frame:
                        self.on_frame(str(latest_frame))
                        processed_frames.add(latest_frame)
                files = sorted(work.glob("audio-*.wav"))
                for chunk in files[:-1]:
                    if chunk in processed:
                        continue
                    segments, _ = model.transcribe(str(chunk), vad_filter=True, beam_size=3)
                    text = " ".join(segment.text.strip() for segment in segments).strip()
                    processed.add(chunk)
                    if text:
                        self.on_text(text, str(latest_frame) if latest_frame else None)
                if self.process.poll() is not None:
                    break
                time.sleep(1)
        except Exception as exc:
            self.error = str(exc)
