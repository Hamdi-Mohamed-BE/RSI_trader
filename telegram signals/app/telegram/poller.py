import asyncio
import re
from sqlmodel import Session
from datetime import datetime
from telethon import functions, types

from app.core.config import settings
from app.core.logging import telegram_logger
from app.telegram.client import telegram_client_wrapper
from app.telegram.filters import filter_message
from app.db.database import engine
from app.db.models import TelegramMessage
from app.db.repositories import TelegramMessageRepository, SystemEventRepository, SettingsRepository


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

    async def poll_messages(self, session: Session) -> list:
        """Polls new messages from the target channel and returns new database message instances."""
        chat_link = SettingsRepository.get(session, "telegram_chat_link", None) or settings.TELEGRAM_CHAT_LINK
        if not chat_link:
            telegram_logger.warning("TELEGRAM_CHAT_LINK is not set. Skipping poll.")
            return []

        try:
            client = await telegram_client_wrapper.get_client(
                api_id=SettingsRepository.get(session, "telegram_api_id", None),
                api_hash=SettingsRepository.get(session, "telegram_api_hash", None),
                bot_token=SettingsRepository.get(session, "telegram_bot_token", None),
                mode=SettingsRepository.get(session, "telegram_mode", None),
                session_string=settings.TELEGRAM_SESSION_STRING,
            )
            
            # Resolve the entity (channel or chat group)
            # Support: integer chat IDs, usernames, t.me links, and web.telegram.org URLs
            entity = parse_chat_reference(chat_link)

            # Try to resolve input entity
            target_entity = await client.get_input_entity(entity)
            
            # Get last processed message ID from database
            # We fetch chat_id using the resolved entity's id (which is positive)
            chat_id = getattr(target_entity, 'channel_id', None) or getattr(target_entity, 'chat_id', None) or getattr(target_entity, 'user_id', None)
            if not chat_id:
                # If we couldn't resolve, let's fallback to hashing chat_link or converting it
                chat_id = hash(chat_link)

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
                db_msg = TelegramMessage(
                    chat_id=chat_id,
                    message_id=msg.id,
                    message_date=msg.date or datetime.utcnow(),
                    raw_text=msg.text or "",
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
