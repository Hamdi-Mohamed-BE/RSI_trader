from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal


OrderKind = Literal["MARKET", "SELL_LIMIT", "SELL_STOP"]


@dataclass(frozen=True)
class PlannedOrder:
    setup: str
    signal_time: datetime
    expiry_time: datetime
    kind: OrderKind
    entry: float
    stop: float
    target: float | None
    risk_share: float
    invalidation_high: float
    runner: bool = False


@dataclass(frozen=True)
class DayPlan:
    symbol: str
    ny_date: str
    setup: str
    h4_trend: str
    candle2_color: str
    london_high: float
    london_low: float
    reference_high: float
    reference_low: float
    previous_h4_high: float
    previous_h4_low: float
    status: str
    reasons: tuple[str, ...]
    orders: tuple[PlannedOrder, ...]

    def to_dict(self) -> dict[str, object]:
        raw = asdict(self)
        raw["orders"] = [asdict(item) for item in self.orders]
        return raw


@dataclass(frozen=True)
class Trade:
    symbol: str
    ny_date: str
    setup: str
    order_kind: str
    entry_time: datetime
    exit_time: datetime
    entry: float
    stop: float
    exit_price: float
    target: float | None
    risk_share: float
    r_multiple: float
    reason: str


@dataclass(frozen=True)
class Stats:
    trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate: float
    profit_factor: float
    expectancy_r: float
    net_r: float
    net_profit: float
    ending_balance: float
    max_drawdown_pct: float
    max_consecutive_losses: int


@dataclass(frozen=True)
class BacktestResult:
    symbol: str
    start: datetime
    end: datetime
    parameters: dict[str, object]
    trades: tuple[Trade, ...]
    stats: Stats
