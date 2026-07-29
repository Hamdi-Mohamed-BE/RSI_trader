from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date


@dataclass(slots=True)
class Trade:
    symbol: str
    session_date: date
    direction: str
    entry_mode: str
    stop_mode: str
    rr_target: float
    entry_time: str
    exit_time: str
    entry: float
    stop: float
    target: float
    exit_price: float
    pnl_r: float
    outcome: str
    asian_high: float
    asian_low: float
    asian_range: float
    adr: float
    range_adr_fraction: float
    exit_mode: str = "fixed"
    trail_start_r: float = 0.0
    trail_distance_r: float = 0.0
    mae_r: float = 0.0
    ambiguous_bar: bool = False

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class Metrics:
    symbol: str
    trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate_pct: float
    profit_factor: float
    net_r: float
    average_r: float
    gross_profit_r: float
    gross_loss_r: float
    max_drawdown_pct: float
    ending_balance: float
    net_profit: float
    return_pct: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
