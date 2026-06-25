from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import timezone

from telethon import TelegramClient, events

from .config import Settings
from .models import Signal
from .parser import SignalParser
from .storage import Storage

logger = logging.getLogger(__name__)

SignalHandler = Callable[[Signal], None]


class TelegramSignalService:
    def __init__(
        self,
        settings: Settings,
        storage: Storage,
        parser: SignalParser,
        handle_signal: SignalHandler,
    ) -> None:
        self.settings = settings
        self.storage = storage
        self.parser = parser
        self.handle_signal = handle_signal
        self.client = TelegramClient(
            settings.telegram_session,
            int(settings.telegram_api_id or 0),
            settings.telegram_api_hash,
        )

    async def run_forever(self) -> None:
        await self.client.start(phone=self.settings.telegram_phone or None)
        logger.info("Telegram connected. Watching channel %s.", self.settings.telegram_channel)

        await self._catch_up_recent()

        @self.client.on(events.NewMessage(chats=self.settings.telegram_channel))
        async def _on_new_message(event: events.NewMessage.Event) -> None:
            await self._process_message(event.message)

        await self.client.run_until_disconnected()

    async def _catch_up_recent(self) -> None:
        async for message in self.client.iter_messages(self.settings.telegram_channel, limit=50):
            await self._process_message(message)

    async def _process_message(self, message: object) -> None:
        message_id = int(getattr(message, "id", 0))
        source_id = str(self.settings.telegram_channel)
        if self.storage.has_message(source_id, message_id):
            return

        created_at = getattr(message, "date", None)
        if created_at is not None and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        text = getattr(message, "raw_text", None) or getattr(message, "message", None) or ""
        forwarded = bool(getattr(message, "fwd_from", None) or getattr(message, "forward", None))

        outcome = self.parser.parse(
            text,
            source_id=source_id,
            message_id=message_id,
            created_at=created_at,
            forwarded=forwarded,
        )

        if not outcome.accepted:
            self.storage.record_message(
                source_id,
                message_id,
                status="ignored",
                reason=outcome.ignored_reason,
                raw_text=text,
            )
            logger.debug("Ignored Telegram message %s: %s", message_id, outcome.ignored_reason)
            return

        await asyncio.to_thread(self.handle_signal, outcome.signal)
