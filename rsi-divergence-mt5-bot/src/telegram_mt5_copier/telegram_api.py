from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from .models import TelegramMessage
from .settings import Settings
from .state import StateStore


class TelegramSourceError(RuntimeError):
    pass


class TelegramSource(ABC):
    @abstractmethod
    async def poll(self) -> list[TelegramMessage]:
        raise NotImplementedError

    async def close(self) -> None:
        return None


class BotApiSource(TelegramSource):
    def __init__(self, settings: Settings, state: StateStore):
        if not settings.telegram_bot_token:
            raise TelegramSourceError("TELEGRAM_BOT_TOKEN is required in bot mode.")
        self.settings = settings
        self.state = state
        self.base_url = f"https://api.telegram.org/bot{settings.telegram_bot_token}"
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(35.0, connect=10.0))

    async def poll(self) -> list[TelegramMessage]:
        offset = int(self.state.get_meta("telegram_bot_offset", "0") or 0)
        response = await self.client.get(
            f"{self.base_url}/getUpdates",
            params={
                "offset": offset,
                "timeout": min(25, max(1, self.settings.poll_seconds)),
                "allowed_updates": '["message","edited_message","channel_post","edited_channel_post"]',
            },
        )
        payload = response.json()
        if not response.is_success or not payload.get("ok"):
            raise TelegramSourceError(payload.get("description") or f"Telegram HTTP {response.status_code}")
        messages: list[TelegramMessage] = []
        highest = offset
        for update in payload.get("result", []):
            highest = max(highest, int(update["update_id"]) + 1)
            edited = "edited_message" in update or "edited_channel_post" in update
            message = (
                update.get("message")
                or update.get("edited_message")
                or update.get("channel_post")
                or update.get("edited_channel_post")
            )
            parsed = self._message(message, edited) if message else None
            if parsed is not None:
                messages.append(parsed)
        if highest != offset:
            self.state.set_meta("telegram_bot_offset", str(highest))
        return messages

    async def verify(self) -> dict:
        response = await self.client.get(f"{self.base_url}/getMe")
        payload = response.json()
        if not response.is_success or not payload.get("ok"):
            raise TelegramSourceError(payload.get("description") or "Bot token verification failed.")
        return payload["result"]

    async def close(self) -> None:
        await self.client.aclose()

    def _message(self, message: dict, edited: bool) -> TelegramMessage | None:
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id", ""))
        username = str(chat.get("username") or "")
        if not self._allowed(chat_id, username):
            return None
        text = str(message.get("text") or message.get("caption") or "").strip()
        if not text:
            return None
        chat_name = str(chat.get("title") or username or chat_id)
        return TelegramMessage(
            chat_id=chat_id,
            message_id=int(message["message_id"]),
            date=datetime.fromtimestamp(int(message["date"]), tz=timezone.utc),
            text=text,
            chat_name=chat_name,
            edited=edited,
        )

    def _allowed(self, chat_id: str, username: str) -> bool:
        sources = self.settings.source_chats
        if not sources:
            return True
        normalized_username = username.casefold().lstrip("@")
        for source in sources:
            token = source.casefold().strip()
            if token == chat_id.casefold():
                return True
            if token.lstrip("@") == normalized_username and normalized_username:
                return True
        return False


class UserApiSource(TelegramSource):
    def __init__(self, settings: Settings, state: StateStore):
        if not settings.telegram_api_id or not settings.telegram_api_hash:
            raise TelegramSourceError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH are required in user mode."
            )
        self.settings = settings
        self.state = state
        self.client = None

    async def poll(self) -> list[TelegramMessage]:
        await self._connect()
        messages: list[TelegramMessage] = []
        for chat in self.settings.source_chats:
            try:
                entity = await self.client.get_entity(_entity_token(chat))
                async for item in self.client.iter_messages(entity, limit=10):
                    text = str(item.message or "").strip()
                    if not text:
                        continue
                    messages.append(
                        TelegramMessage(
                            chat_id=str(item.chat_id),
                            message_id=int(item.id),
                            date=item.date.astimezone(timezone.utc),
                            text=text,
                            chat_name=str(getattr(entity, "title", None) or chat),
                            edited=bool(item.edit_date),
                        )
                    )
            except Exception as exc:
                raise TelegramSourceError(f"Cannot read Telegram source {chat}: {exc}") from exc
        return sorted(messages, key=lambda item: item.date)

    async def close(self) -> None:
        if self.client is not None:
            await self.client.disconnect()

    async def _connect(self) -> None:
        if self.client is not None and self.client.is_connected():
            return
        from telethon import TelegramClient

        self.settings.session_file.parent.mkdir(parents=True, exist_ok=True)
        self.client = TelegramClient(
            str(self.settings.session_file),
            self.settings.telegram_api_id,
            self.settings.telegram_api_hash,
        )
        await self.client.connect()
        if not await self.client.is_user_authorized():
            await self.client.disconnect()
            raise TelegramSourceError(
                "Telegram user session is not authorized. Run login.bat once."
            )


def build_source(settings: Settings, state: StateStore) -> TelegramSource:
    if settings.telegram_mode == "user":
        return UserApiSource(settings, state)
    return BotApiSource(settings, state)


def _entity_token(value: str):
    cleaned = value.strip()
    if cleaned.lstrip("-").isdigit():
        return int(cleaned)
    return cleaned
