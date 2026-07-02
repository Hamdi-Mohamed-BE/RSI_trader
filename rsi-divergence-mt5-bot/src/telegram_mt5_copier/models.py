from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class TelegramMessage:
    chat_id: str
    message_id: int
    date: datetime
    text: str
    chat_name: str = ""
    edited: bool = False

    @property
    def key(self) -> str:
        return f"{self.chat_id}:{self.message_id}"


@dataclass(frozen=True)
class TradeSignal:
    symbol: str
    side: Literal["BUY", "SELL"]
    entry_low: float | None
    entry_high: float | None
    stop_loss: float
    take_profits: tuple[float, ...]
    market: bool
    raw_text: str

    @property
    def tp1(self) -> float:
        return self.take_profits[0]

    @property
    def final_tp(self) -> float:
        return self.take_profits[-1]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class WorkerStatus:
    running: bool = False
    mode: str = "bot"
    last_poll_at: str | None = None
    last_message_at: str | None = None
    last_action: str | None = None
    last_error: str | None = None
    received: int = 0
    copied: int = 0
    ignored: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

