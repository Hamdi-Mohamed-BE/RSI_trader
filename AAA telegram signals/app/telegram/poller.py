import re
from pathlib import Path
from sqlmodel import Session
from datetime import datetime

from app.core.config import settings
from app.core.logging import telegram_logger
from app.telegram.client import telegram_client_wrapper
from app.telegram.filters import filter_message
from app.db.database import engine
from app.db.models import TelegramMessage
from app.db.repositories import TelegramMessageRepository, SystemEventRepository, SettingsRepository


MEDIA_DIR = Path("app/static/telegram_media")
MEDIA_URL_PREFIX = "/static/telegram_media"


def parse_chat_reference(chat_link: str):
    web_match = re.search(r"web\.telegram\.org/[^#]*#(-?\d+)", chat_link)
    if web_match:
        raw_id = web_match.group(1)
        if raw_id.startswith("-") and not raw_id.startswith("-100"):
            return int(f"-100{raw_id[1:]}")
        return int(raw_id)
    private_match = re.match(r"https?://t\.me/c/(\d+)", chat_link)
    if private_match:
        return int(f"-100{private_match.group(1)}")
    if chat_link.lstrip("-").isdigit():
        return int(chat_link)
    return chat_link

class TelegramPoller:
    def __init__(self):
        self._running = False
        self._task = None

    async def _target(self, session: Session):
        chat_link = SettingsRepository.get(session, "telegram_chat_link", None) or settings.TELEGRAM_CHAT_LINK
        if not chat_link:
            telegram_logger.warning("TELEGRAM_CHAT_LINK is not set. Skipping poll.")
            return None, None, None, None

        client = await telegram_client_wrapper.get_client(
            api_id=SettingsRepository.get(session, "telegram_api_id", None),
            api_hash=SettingsRepository.get(session, "telegram_api_hash", None),
            bot_token=SettingsRepository.get(session, "telegram_bot_token", None),
            mode=SettingsRepository.get(session, "telegram_mode", None),
            session_string=settings.TELEGRAM_SESSION_STRING,
        )
        entity = parse_chat_reference(chat_link)
        target_entity = await client.get_input_entity(entity)
        chat_id = (
            getattr(target_entity, "channel_id", None)
            or getattr(target_entity, "chat_id", None)
            or getattr(target_entity, "user_id", None)
            or hash(chat_link)
        )
        return client, target_entity, chat_id, chat_link

    async def poll_messages(self, session: Session) -> list:
        """Polls new messages from the target channel and returns new database message instances."""
        try:
            client, target_entity, chat_id, chat_link = await self._target(session)
            if not client:
                return []

            last_msg_id = TelegramMessageRepository.get_latest_message_id(session, chat_id)
            
            telegram_logger.debug(f"Polling {chat_link} (ID: {chat_id}) since message ID {last_msg_id}...")
            
            # Fetch messages
            messages = []
            if last_msg_id == 0:
                # If database is empty, only get the very last message to avoid flooding on first run
                history = await client.get_messages(target_entity, limit=5)
            else:
                # Telethon get_messages with min_id gets messages newer than min_id
                history = await client.get_messages(target_entity, limit=50, min_id=last_msg_id)

            if not history:
                return []

            # Process history in reverse order (oldest first) so we process chronologically
            new_db_messages = []
            for msg in reversed(list(history)):
                # Double check in DB to prevent duplicates
                existing = TelegramMessageRepository.get_by_telegram_id(session, chat_id, msg.id)
                if existing:
                    continue

                # Prepare database record
                media_url = await self._download_image_media(msg, chat_id)
                db_msg = TelegramMessage(
                    chat_id=chat_id,
                    message_id=msg.id,
                    message_date=msg.date or datetime.utcnow(),
                    raw_text=msg.text or "",
                    media_url=media_url,
                    is_reply=bool(msg.reply_to),
                    is_forwarded=bool(msg.fwd_from),
                    is_edited=False  # Telethon has edit check, but for MVP keep simple
                )
                
                # Apply filters
                allow_replies = bool(SettingsRepository.get(session, "allow_reply_signals", False))
                should_ignore, reason = filter_message(msg, allow_reply_signals=allow_replies)
                if should_ignore:
                    db_msg.ignored = True
                    db_msg.ignore_reason = reason
                    db_msg.processed = True
                    telegram_logger.info(f"Message {msg.id} ignored. Reason: {reason}")
                
                saved_msg = TelegramMessageRepository.save(session, db_msg)
                new_db_messages.append(saved_msg)
                
            return new_db_messages

        except Exception as e:
            telegram_logger.error(f"Error polling Telegram messages: {e}", exc_info=True)
            SystemEventRepository.log(
                session, 
                level="error", 
                source="telegram", 
                message=f"Polling failed: {str(e)}"
            )
            return []

    async def refresh_recent_messages(self, session: Session, limit: int = 120) -> dict:
        """Refetch recent channel history and backfill missing text/image media in the DB."""
        try:
            client, target_entity, chat_id, chat_link = await self._target(session)
            if not client:
                return {"scanned": 0, "created": 0, "media_updated": 0}

            history = await client.get_messages(target_entity, limit=limit)
            if not history:
                return {"scanned": 0, "created": 0, "media_updated": 0}

            created = 0
            media_updated = 0
            allow_replies = bool(SettingsRepository.get(session, "allow_reply_signals", False))

            for msg in reversed(list(history)):
                existing = TelegramMessageRepository.get_by_telegram_id(session, chat_id, msg.id)
                media_url = getattr(existing, "media_url", None) if existing else None
                if not media_url:
                    media_url = await self._download_image_media(msg, chat_id)

                if existing:
                    changed = False
                    raw_text = msg.text or ""
                    if raw_text and existing.raw_text != raw_text:
                        existing.raw_text = raw_text
                        changed = True
                    if media_url and existing.media_url != media_url:
                        existing.media_url = media_url
                        media_updated += 1
                        changed = True
                    if changed:
                        TelegramMessageRepository.save(session, existing)
                    continue

                db_msg = TelegramMessage(
                    chat_id=chat_id,
                    message_id=msg.id,
                    message_date=msg.date or datetime.utcnow(),
                    raw_text=msg.text or "",
                    media_url=media_url,
                    is_reply=bool(msg.reply_to),
                    is_forwarded=bool(msg.fwd_from),
                    is_edited=False,
                )

                should_ignore, reason = filter_message(msg, allow_reply_signals=allow_replies)
                if should_ignore:
                    db_msg.ignored = True
                    db_msg.ignore_reason = reason
                    db_msg.processed = True

                TelegramMessageRepository.save(session, db_msg)
                created += 1

            return {"scanned": len(history), "created": created, "media_updated": media_updated}
        except Exception as e:
            telegram_logger.error(f"Error refreshing recent Telegram messages: {e}", exc_info=True)
            SystemEventRepository.log(
                session,
                level="error",
                source="telegram",
                message=f"Refresh recent messages failed: {str(e)}",
            )
            return {"scanned": 0, "created": 0, "media_updated": 0, "error": str(e)}

    @staticmethod
    def _image_extension(msg) -> str | None:
        if getattr(msg, "photo", None):
            return ".jpg"
        document = getattr(msg, "document", None)
        mime_type = getattr(document, "mime_type", "") if document else ""
        if not mime_type.startswith("image/"):
            return None
        if mime_type == "image/png":
            return ".png"
        if mime_type == "image/webp":
            return ".webp"
        if mime_type in {"image/jpeg", "image/jpg"}:
            return ".jpg"
        return ".jpg"

    async def _download_image_media(self, msg, chat_id: int) -> str | None:
        ext = self._image_extension(msg)
        if not ext:
            return None

        try:
            MEDIA_DIR.mkdir(parents=True, exist_ok=True)
            safe_chat_id = str(chat_id).replace("-", "m")
            target = MEDIA_DIR / f"{safe_chat_id}_{msg.id}{ext}"
            downloaded = await msg.download_media(file=str(target))
            if not downloaded:
                return None
            media_path = Path(downloaded)
            return f"{MEDIA_URL_PREFIX}/{media_path.name}"
        except Exception as exc:
            telegram_logger.warning(f"Failed to download image for message {msg.id}: {exc}")
            return None


telegram_poller = TelegramPoller()
