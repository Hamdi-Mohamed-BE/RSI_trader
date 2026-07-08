from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class SignalParseSchema(BaseModel):
    is_signal: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    ignore_reason: Optional[str] = None
    message_type: Literal["signal", "ad", "result", "education", "reply", "forwarded", "unknown"]
    symbol_raw: Optional[str] = None
    side: Optional[Literal["buy", "sell"]] = None
    order_type: Optional[Literal["market", "pending"]] = None
    pending_type: Optional[Literal["buy_limit", "sell_limit", "buy_stop", "sell_stop"]] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profits: List[float] = Field(default_factory=list)
    final_take_profit: Optional[float] = None
    break_even_trigger_tp: Optional[float] = None
    risk_warnings: List[str] = Field(default_factory=list)
    parser_notes: List[str] = Field(default_factory=list)
