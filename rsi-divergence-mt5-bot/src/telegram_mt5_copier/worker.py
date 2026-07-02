from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from .models import TelegramMessage, WorkerStatus
from .mt5_copier import MT5Copier, MT5CopyError
from .settings import Settings, load_settings
from .signal_parser import parse_signal
from .state import StateStore
from .telegram_api import TelegramSource, build_source


class CopierWorker:
    def __init__(self, settings: Settings, state: StateStore, status: WorkerStatus):
        self.settings = settings
        self.state = state
        self.status = status
        self.stop_event = asyncio.Event()
        self.source: TelegramSource | None = None

    async def run(self) -> None:
        self.status.running = True
        self.status.mode = self.settings.telegram_mode
        self.status.last_error = None
        try:
            self.source = build_source(self.settings, self.state)
            while not self.stop_event.is_set():
                try:
                    messages = await self.source.poll()
                    self.status.last_poll_at = datetime.now(timezone.utc).isoformat()
                    for message in messages:
                        await self._process(message)
                    actions = await asyncio.to_thread(
                        MT5Copier(self.settings, self.state).protect_trades
                    )
                    if actions:
                        self.status.last_action = actions[-1]
                    self.status.last_error = None
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    self.status.last_error = str(exc)
                    self.status.last_action = "poll failed"
                try:
                    await asyncio.wait_for(
                        self.stop_event.wait(), timeout=self.settings.poll_seconds
                    )
                except TimeoutError:
                    pass
        finally:
            if self.source is not None:
                await self.source.close()
            self.status.running = False

    async def stop(self) -> None:
        self.stop_event.set()

    async def _process(self, message: TelegramMessage) -> None:
        if self.state.is_processed(message):
            return
        self.status.received += 1
        self.status.last_message_at = message.date.isoformat()
        age = (datetime.now(timezone.utc) - message.date).total_seconds()
        if age > self.settings.max_message_age_seconds:
            self.state.record_message(message, "IGNORED", error=f"message is {age:.0f}s old")
            self.status.ignored += 1
            return
        signal = parse_signal(message.text, self.settings.aliases)
        if signal is None:
            self.state.record_message(message, "IGNORED", error="not a complete trade signal")
            self.status.ignored += 1
            return
        if not self.settings.live_trading:
            self.state.record_message(message, "PREPARED", signal=signal)
            self.status.last_action = f"prepared {signal.symbol} {signal.side}"
            return
        try:
            placement = await asyncio.to_thread(
                MT5Copier(self.settings, self.state).place, signal, message.key
            )
            self.state.record_message(message, "COPIED", signal=signal)
            self.status.copied += 1
            self.status.last_action = (
                f"copied {placement.symbol} {placement.side} {placement.volume:g} lot"
            )
        except MT5CopyError as exc:
            status = "IGNORED" if "already" in str(exc).lower() else "ERROR"
            self.state.record_message(message, status, signal=signal, error=str(exc))
            if status == "IGNORED":
                self.status.ignored += 1
            self.status.last_error = str(exc)


class WorkerManager:
    def __init__(self):
        self.state = StateStore()
        self.status = WorkerStatus()
        self.worker: CopierWorker | None = None
        self.task: asyncio.Task | None = None

    async def start(self) -> dict:
        if self.task is not None and not self.task.done():
            return self.status.to_dict()
        settings = load_settings()
        self.worker = CopierWorker(settings, self.state, self.status)
        self.task = asyncio.create_task(self.worker.run(), name="telegram-mt5-copier")
        await asyncio.sleep(0)
        return self.status.to_dict()

    async def stop(self) -> dict:
        if self.worker is not None:
            await self.worker.stop()
        if self.task is not None:
            try:
                await asyncio.wait_for(self.task, timeout=10)
            except TimeoutError:
                self.task.cancel()
        self.worker = None
        self.task = None
        return self.status.to_dict()

    async def restart(self) -> dict:
        await self.stop()
        return await self.start()
