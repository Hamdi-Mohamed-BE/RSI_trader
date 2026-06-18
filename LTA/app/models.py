from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


TradeSymbol = Literal["XAUUSD", "XAGUSD", "BTCUSD"]
Symbol = Literal["ALL", "XAUUSD", "XAGUSD", "BTCUSD"]
Timeframe = Literal["M1", "M5", "M15", "M30", "H1", "H4", "D1"]

TRADE_SYMBOLS: tuple[str, ...] = ("XAUUSD", "XAGUSD", "BTCUSD")
ALLOWED_SYMBOLS: tuple[str, ...] = ("ALL", *TRADE_SYMBOLS)
ALLOWED_TIMEFRAMES: tuple[str, ...] = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")


class BacktestRequest(BaseModel):
    symbol: Symbol = "XAUUSD"
    timeframe: Timeframe = "M15"
    start: date
    end: date
    starting_balance: float = Field(default=1000.0, gt=0)
    lot_size: float = Field(default=0.01, gt=0)
    symbol_lots: dict[str, float] = Field(
        default_factory=lambda: {"XAUUSD": 0.01, "XAGUSD": 0.01, "BTCUSD": 0.01}
    )
    risk_per_trade_percent: float = Field(default=1.0, gt=0, le=10)
    max_daily_loss_percent: float = Field(default=3.0, gt=0, le=50)
    max_drawdown_percent: float = Field(default=8.0, gt=0, le=80)
    max_trades_per_day: int = Field(default=3, ge=1, le=50)
    min_setup_score: int = Field(default=90, ge=1, le=100)
    min_risk_reward: float = Field(default=2.0, ge=0.5, le=20)
    use_demo_if_mt5_unavailable: bool = True


class Signal(BaseModel):
    symbol: str
    timeframe: str
    direction: str | None = None
    setup_grade: str
    setup_score: int
    profile_type: str | None = None
    key_level: str | None = None
    entry_model: str | None = None
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    risk_reward: float | None = None
    invalidation: str | None = None
    reasons: list[str] = Field(default_factory=list)
    status: Literal["allowed", "rejected"] = "rejected"
    timestamp: datetime | None = None


class TradeResult(BaseModel):
    opened_at: datetime
    closed_at: datetime
    symbol: str
    timeframe: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    exit_price: float
    result: Literal["win", "loss", "timeout"]
    pnl: float
    r_multiple: float
    balance_after: float
    setup_score: int
    setup_grade: str
    key_level: str
    entry_model: str
    reasons: list[str]


class BacktestReport(BaseModel):
    symbol: str
    timeframe: str
    start: date
    end: date
    data_source: str
    starting_balance: float
    ending_balance: float
    net_profit: float
    total_return_percent: float = 0.0
    win_rate: float
    total_trades: int
    wins: int
    losses: int
    timeouts: int
    max_drawdown: float
    profit_factor: float = 0.0
    average_win: float = 0.0
    average_loss: float = 0.0
    average_risk_reward: float
    average_r_multiple: float
    sharpe_ratio: float = 0.0
    best_trade: float | None
    worst_trade: float | None
    a_plus_setups_taken: int
    setups_rejected: int
    rejected_reason_breakdown: dict[str, int]
    equity_curve: list[float] = Field(default_factory=list)
    symbol_summaries: list[dict[str, Any]] = Field(default_factory=list)
    trades: list[TradeResult]
    rejected_setups: list[Signal]
    json_report: str | None = None
    csv_report: str | None = None
    warnings: list[str] = Field(default_factory=list)


def model_to_dict(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()
