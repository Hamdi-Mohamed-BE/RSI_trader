from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

from .enums import JobStatus, OrderType, Side, TradeAction


class ContractSpec(BaseModel):
    symbol: str
    tick_size: Decimal = Field(gt=0)
    tick_value: Decimal = Field(gt=0)
    volume_min: Decimal = Field(gt=0)
    volume_max: Decimal = Field(gt=0)
    volume_step: Decimal = Field(gt=0)
    contract_size: Decimal = Field(default=Decimal("1"), gt=0)


class AccountSnapshot(BaseModel):
    account_id: UUID
    equity: Decimal = Field(gt=0)
    free_margin: Decimal = Field(ge=0)
    currency: str = "USD"
    contract: ContractSpec


class SourceTradeMessage(BaseModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["source_trade"] = "source_trade"
    event_uid: UUID = Field(default_factory=uuid4)
    sequence: int = Field(ge=1)
    source_account_id: UUID
    source_order_id: str
    source_position_id: str | None = None
    action: TradeAction
    side: Side
    symbol: str
    volume: Decimal = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    stop_loss: Decimal | None = Field(default=None, gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)
    magic_number: int = 0
    comment: str = ""
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_stop_direction(self) -> "SourceTradeMessage":
        if self.action in {TradeAction.MARKET_OPEN, TradeAction.PENDING_CREATE}:
            if (
                self.stop_loss is not None
                and self.side is Side.BUY
                and self.stop_loss >= self.entry_price
            ):
                raise ValueError("A buy stop loss must be below entry.")
            if (
                self.stop_loss is not None
                and self.side is Side.SELL
                and self.stop_loss <= self.entry_price
            ):
                raise ValueError("A sell stop loss must be above entry.")
        return self


class FollowerCommand(BaseModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["follower_command"] = "follower_command"
    job_uid: UUID
    source_event_uid: UUID
    follower_account_id: UUID
    source_order_id: str
    source_position_id: str | None = None
    target_order_id: str | None = None
    target_position_id: str | None = None
    action: TradeAction
    side: Side
    order_type: OrderType = OrderType.MARKET
    symbol: str
    volume: Decimal = Field(gt=0)
    entry_price: Decimal = Field(gt=0)
    stop_loss: Decimal | None = Field(default=None, gt=0)
    take_profit: Decimal | None = Field(default=None, gt=0)
    expiration_at: datetime | None = None
    max_slippage_points: int = Field(default=30, ge=0)
    sent_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ExecutionAck(BaseModel):
    protocol_version: Literal[1] = 1
    message_type: Literal["execution_ack"] = "execution_ack"
    job_uid: UUID
    follower_account_id: UUID
    status: JobStatus
    broker_order_id: str | None = None
    broker_position_id: str | None = None
    requested_price: Decimal | None = None
    filled_price: Decimal | None = None
    filled_volume: Decimal | None = None
    broker_result_code: int | None = None
    error: str = ""
    received_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
