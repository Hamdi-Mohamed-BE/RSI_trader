from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    @property
    def is_buy(self) -> bool:
        return self is Direction.BUY


class EntryType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    AUTO = "AUTO"


@dataclass(frozen=True)
class Signal:
    source_id: str
    message_id: int
    created_at: datetime
    symbol: str
    direction: Direction
    entry_type: EntryType
    stop_loss: float
    take_profits: tuple[float, ...]
    raw_text: str
    entry_price: float | None = None
    recovered: bool = False

    @property
    def key(self) -> str:
        return f"{self.source_id}:{self.message_id}"

    @property
    def first_tp(self) -> float:
        return self.take_profits[0]

    @property
    def final_tp(self) -> float:
        return self.take_profits[-1]

    def age_seconds(self, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return max(0.0, (now - created.astimezone(timezone.utc)).total_seconds())


@dataclass(frozen=True)
class ParseOutcome:
    signal: Signal | None
    ignored_reason: str | None = None

    @property
    def accepted(self) -> bool:
        return self.signal is not None


@dataclass(frozen=True)
class OrderPlan:
    symbol: str
    direction: Direction
    entry_type: EntryType
    volume: float
    stop_loss: float
    take_profit: float
    break_even_trigger: float
    comment: str
    entry_price: float | None = None


@dataclass(frozen=True)
class BrokerOrderResult:
    ticket: int
    deal: int | None
    retcode: int
    comment: str


@dataclass(frozen=True)
class BrokerVolume:
    total_volume: float
    risk_money: float
    loss_per_lot: float
    raw_volume: float
    used_minimum_lot: bool


@dataclass(frozen=True)
class VolumeConstraints:
    minimum: float
    maximum: float
    step: float


@dataclass(frozen=True)
class TradeRecord:
    id: int
    signal_key: str
    message_id: int
    source_id: str
    symbol: str
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    break_even_trigger: float
    comment_prefix: str
    orders_json: str
    status: str
    break_even_done: bool
    created_at: datetime
