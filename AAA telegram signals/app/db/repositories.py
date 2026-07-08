from datetime import datetime
from typing import List, Optional, Any, Dict
from sqlmodel import Session, select, desc
import json

from app.db.models import Settings, TelegramMessage, LLMParseResult, OrderAttempt, ManagedTrade, SystemEvent

class SettingsRepository:
    @staticmethod
    def get(session: Session, key: str, default: Any = None) -> Any:
        statement = select(Settings).where(Settings.key == key)
        result = session.exec(statement).first()
        if result:
            return result.get_value()
        return default

    @staticmethod
    def set(session: Session, key: str, value: Any):
        statement = select(Settings).where(Settings.key == key)
        db_setting = session.exec(statement).first()
        value_json = json.dumps(value)
        if db_setting:
            db_setting.value_json = value_json
            db_setting.updated_at = datetime.utcnow()
        else:
            db_setting = Settings(key=key, value_json=value_json)
            session.add(db_setting)
        session.commit()
        session.refresh(db_setting)
        return db_setting


class TelegramMessageRepository:
    @staticmethod
    def save(session: Session, message: TelegramMessage) -> TelegramMessage:
        session.add(message)
        session.commit()
        session.refresh(message)
        return message

    @staticmethod
    def get_by_telegram_id(session: Session, chat_id: int, message_id: int) -> Optional[TelegramMessage]:
        statement = select(TelegramMessage).where(
            TelegramMessage.chat_id == chat_id,
            TelegramMessage.message_id == message_id
        )
        return session.exec(statement).first()

    @staticmethod
    def get_latest_message_id(session: Session, chat_id: int) -> int:
        statement = select(TelegramMessage).where(
            TelegramMessage.chat_id == chat_id
        ).order_by(desc(TelegramMessage.message_id)).limit(1)
        result = session.exec(statement).first()
        return result.message_id if result else 0

    @staticmethod
    def get_recent(session: Session, limit: int = 20) -> List[TelegramMessage]:
        statement = select(TelegramMessage).order_by(desc(TelegramMessage.message_date)).limit(limit)
        return list(session.exec(statement).all())


class LLMParseResultRepository:
    @staticmethod
    def save(session: Session, result: LLMParseResult) -> LLMParseResult:
        session.add(result)
        session.commit()
        session.refresh(result)
        return result


class OrderAttemptRepository:
    @staticmethod
    def save(session: Session, attempt: OrderAttempt) -> OrderAttempt:
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        return attempt

    @staticmethod
    def get_recent(session: Session, limit: int = 20) -> List[OrderAttempt]:
        statement = select(OrderAttempt).order_by(desc(OrderAttempt.created_at)).limit(limit)
        return list(session.exec(statement).all())

    @staticmethod
    def get_trades_count_for_day(session: Session, date_str: str) -> int:
        # Simple date count
        # In SQLite, we can compare string format
        # or use datetime range
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        statement = select(OrderAttempt).where(
            OrderAttempt.created_at >= today_start,
            OrderAttempt.status == "placed"
        )
        return len(session.exec(statement).all())

    @staticmethod
    def get_placed_by_signal_hash(session: Session, signal_hash: str) -> Optional[OrderAttempt]:
        if not signal_hash:
            return None
        statement = (
            select(OrderAttempt)
            .where(
                OrderAttempt.signal_hash == signal_hash,
                OrderAttempt.status == "placed",
            )
            .order_by(desc(OrderAttempt.created_at))
            .limit(1)
        )
        return session.exec(statement).first()


class ManagedTradeRepository:
    @staticmethod
    def save(session: Session, trade: ManagedTrade) -> ManagedTrade:
        session.add(trade)
        session.commit()
        session.refresh(trade)
        return trade

    @staticmethod
    def get_active(session: Session) -> List[ManagedTrade]:
        statement = select(ManagedTrade).where(ManagedTrade.status == "active")
        return list(session.exec(statement).all())

    @staticmethod
    def get_recent(session: Session, limit: int = 20) -> List[ManagedTrade]:
        statement = select(ManagedTrade).order_by(desc(ManagedTrade.created_at)).limit(limit)
        return list(session.exec(statement).all())

    @staticmethod
    def get_by_ticket(session: Session, ticket: int) -> Optional[ManagedTrade]:
        statement = select(ManagedTrade).where(ManagedTrade.mt5_ticket == ticket)
        return session.exec(statement).first()


class SystemEventRepository:
    @staticmethod
    def log(session: Session, level: str, source: str, message: str, details: Optional[Dict[str, Any]] = None) -> SystemEvent:
        details_str = json.dumps(details) if details else None
        event = SystemEvent(level=level, source=source, message=message, details_json=details_str)
        session.add(event)
        session.commit()
        session.refresh(event)
        return event

    @staticmethod
    def get_recent(session: Session, limit: int = 20) -> List[SystemEvent]:
        statement = select(SystemEvent).order_by(desc(SystemEvent.created_at)).limit(limit)
        return list(session.exec(statement).all())
