from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class Signal:
    symbol: str
    session_date: str
    model: str
    direction: str
    signal_time: str
    signal_index: int
    or_high: float
    or_low: float
    stop_reference: float
    target_reference: float | None
    atr: float
    spread_points: int
    body_ratio: float
    relative_volume: float
    fvg_confluence: bool
    liquidity_confluence: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Trade:
    symbol: str
    session_date: str
    model: str
    direction: str
    signal_time: str
    entry_time: str
    exit_time: str
    entry: float
    stop: float
    target: float
    outcome: str
    r_multiple: float
    risk_amount: float
    pnl: float
    balance_after: float
    spread_points: int
    body_ratio: float
    relative_volume: float
    fvg_confluence: bool
    liquidity_confluence: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Metrics:
    starting_balance: float
    ending_balance: float
    net_profit: float
    return_percent: float
    trades: int
    wins: int
    losses: int
    breakeven: int
    win_rate: float
    profit_factor: float | str
    average_r: float
    max_drawdown_percent: float
    gross_profit: float
    gross_loss: float

    def to_dict(self) -> dict:
        return asdict(self)

