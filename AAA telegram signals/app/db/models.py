from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlmodel import SQLModel, Field, Column, JSON, String, Text
import json

class Settings(SQLModel, table=True):
    __tablename__ = "settings"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(unique=True, index=True)
    value_json: str = Field(description="JSON serialized value")
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def get_value(self) -> Any:
        try:
            return json.loads(self.value_json)
        except Exception:
            return self.value_json

    @classmethod
    def set_value(cls, key: str, value: Any) -> "Settings":
        return cls(key=key, value_json=json.dumps(value), updated_at=datetime.utcnow())


class TelegramChannel(SQLModel, table=True):
    __tablename__ = "telegram_channels"

    id: Optional[int] = Field(default=None, primary_key=True)
    chat_link: str = Field(unique=True, index=True)
    attr: str = Field(default="Telegram")
    enabled: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TelegramMessage(SQLModel, table=True):
    __tablename__ = "telegram_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_channel_id: Optional[int] = Field(default=None, index=True)
    chat_id: int = Field(index=True)
    message_id: int = Field(index=True)
    message_date: datetime
    raw_text: str = Field(sa_column=Column(Text))
    media_url: Optional[str] = Field(default=None)
    is_reply: bool = Field(default=False)
    is_forwarded: bool = Field(default=False)
    is_edited: bool = Field(default=False)
    ignored: bool = Field(default=False)
    ignore_reason: Optional[str] = Field(default=None)
    processed: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LLMParseResult(SQLModel, table=True):
    __tablename__ = "llm_parse_results"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_message_db_id: int = Field(index=True)
    provider: str = Field(default="gemini")
    model: str
    prompt_version: str = Field(default="v1")
    raw_response_json: str = Field(sa_column=Column(Text))
    normalized_json: str = Field(sa_column=Column(Text))
    confidence: float = Field(default=0.0)
    is_signal: bool = Field(default=False)
    error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OrderAttempt(SQLModel, table=True):
    __tablename__ = "order_attempts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_message_db_id: int = Field(index=True)
    signal_hash: Optional[str] = Field(default=None, index=True)
    symbol_raw: str
    broker_symbol: Optional[str] = Field(default=None)
    side: str
    order_type: str  # market or pending
    pending_type: Optional[str] = Field(default=None)
    entry_price: Optional[float] = Field(default=None)
    stop_loss: Optional[float] = Field(default=None)
    take_profits_json: str = Field(default="[]")
    final_take_profit: Optional[float] = Field(default=None)
    break_even_trigger_tp: Optional[float] = Field(default=None)
    lot: float = Field(default=0.0)
    risk_mode: str
    risk_amount: float
    status: str  # pending_validation, ignored, validation_failed, order_check_failed, send_failed, placed
    mt5_request_json: Optional[str] = Field(sa_column=Column(Text), default=None)
    mt5_result_json: Optional[str] = Field(sa_column=Column(Text), default=None)
    error: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def take_profits(self) -> List[float]:
        try:
            return json.loads(self.take_profits_json)
        except Exception:
            return []


class ManagedTrade(SQLModel, table=True):
    __tablename__ = "managed_trades"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_attempt_id: int = Field(index=True)
    mt5_ticket: int = Field(unique=True, index=True)
    position_identifier: Optional[int] = Field(default=None)
    symbol_raw: str
    broker_symbol: str
    side: str
    lot: float
    entry_price: float
    stop_loss_original: float
    stop_loss_current: float
    take_profits_json: str = Field(default="[]")
    final_take_profit: float
    break_even_trigger_tp: Optional[float] = Field(default=None)
    break_even_enabled: bool = Field(default=True)
    break_even_done: bool = Field(default=False)
    break_even_done_at: Optional[datetime] = Field(default=None)
    tp2_partial_done: bool = Field(default=False)
    tp2_partial_done_at: Optional[datetime] = Field(default=None)
    tp2_partial_volume: Optional[float] = Field(default=None)
    status: str = Field(default="active")  # active, closed, unknown
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @property
    def take_profits(self) -> List[float]:
        try:
            return json.loads(self.take_profits_json)
        except Exception:
            return []


class SystemEvent(SQLModel, table=True):
    __tablename__ = "system_events"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    level: str = Field(default="info")  # info, warning, error, success
    source: str  # e.g., system, telegram, llm, mt5, risk
    message: str = Field(sa_column=Column(Text))
    details_json: Optional[str] = Field(sa_column=Column(Text), default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
