from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import replace
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

        await self._log_recent_messages()
        await self._catch_up_recent()

        @self.client.on(events.NewMessage(chats=self.settings.telegram_channel))
        async def _on_new_message(event: events.NewMessage.Event) -> None:
            await self._process_message(event.message, live=True)

        await self.client.run_until_disconnected()

    async def _log_recent_messages(self) -> None:
        count = max(0, int(self.settings.recent_message_log_count))
        if count == 0:
            return

        logger.info("Last %s Telegram message(s), newest first:", count)
        found = 0
        async for message in self.client.iter_messages(self.settings.telegram_channel, limit=count):
            found += 1
            logger.info(
                "  #%s %s forwarded=%s | %s",
                int(getattr(message, "id", 0)),
                self._message_date_text(message),
                "yes" if self._is_forwarded(message) else "no",
                self._preview(message),
            )
        if found == 0:
            logger.info("  No messages found in this channel.")

    async def _catch_up_recent(self) -> None:
        count = max(0, int(self.settings.rescan_message_count))
        if count == 0:
            return
        logger.info(
            "Re-scanning the last %s Telegram messages for active signals up to %ss old.",
            count,
            self.settings.rescan_max_age_seconds,
        )
        async for message in self.client.iter_messages(self.settings.telegram_channel, limit=count):
            await self._process_message(message, verbose=False, recovery=True)

    async def _process_message(
        self,
        message: object,
        *,
        live: bool = False,
        verbose: bool = True,
        recovery: bool = False,
    ) -> None:
        message_id = int(getattr(message, "id", 0))
        source_id = str(self.settings.telegram_channel)
        existing = self.storage.message_record(source_id, message_id)
        if existing and not (recovery and existing.get("status") == "ignored"):
            if live:
                logger.info("Telegram message #%s already handled.", message_id)
            return

        created_at = getattr(message, "date", None)
        if created_at is not None and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        text = getattr(message, "raw_text", None) or getattr(message, "message", None) or ""
        forwarded = self._is_forwarded(message)

        if live:
            logger.info(
                "New Telegram message #%s forwarded=%s | %s",
                message_id,
                "yes" if forwarded else "no",
                self._text_preview(text),
            )

        outcome = self.parser.parse(
            text,
            source_id=source_id,
            message_id=message_id,
            created_at=created_at,
            forwarded=forwarded,
            max_age_seconds=(
                self.settings.rescan_max_age_seconds
                if recovery
                else self.settings.max_signal_age_seconds
            ),
        )

        if not outcome.accepted:
            self.storage.record_message(
                source_id,
                message_id,
                status="ignored",
                reason=outcome.ignored_reason,
                raw_text=text,
            )
            if verbose:
                logger.info(
                    "Ignored Telegram message #%s: %s | %s",
                    message_id,
                    outcome.ignored_reason,
                    self._text_preview(text),
                )
            else:
                logger.debug("Ignored Telegram message #%s: %s", message_id, outcome.ignored_reason)
            return

        signal = outcome.signal
        assert signal is not None
        if recovery:
            signal = replace(signal, recovered=True)
        if recovery and existing:
            self.storage.delete_message(source_id, message_id)
            logger.info(
                "Recovered previously ignored Telegram message #%s (%s).",
                message_id,
                existing.get("reason") or "no reason recorded",
            )
        logger.info(
            "Accepted Telegram message #%s as signal: %s %s %s SL=%s TP=%s.",
            message_id,
            signal.symbol,
            signal.direction.value,
            signal.entry_type.value,
            signal.stop_loss,
            ", ".join(str(tp) for tp in signal.take_profits),
        )
        await asyncio.to_thread(self.handle_signal, signal)

    def _preview(self, message: object) -> str:
        text = getattr(message, "raw_text", None) or getattr(message, "message", None) or ""
        return self._text_preview(text)

    def _text_preview(self, text: str, max_length: int = 180) -> str:
        preview = " ".join(text.split())
        if not preview:
            return "[no text]"
        if len(preview) <= max_length:
            return preview
        return f"{preview[: max_length - 3]}..."

    def _message_date_text(self, message: object) -> str:
        value = getattr(message, "date", None)
        return value.isoformat() if value is not None else "no-date"

    def _is_forwarded(self, message: object) -> bool:
        return bool(getattr(message, "fwd_from", None) or getattr(message, "forward", None))
