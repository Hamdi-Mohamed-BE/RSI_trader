from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class SymbolSpec:
    name: str
    description: str
    path: str
    digits: int
    point: float
    tick_size: float
    tick_value: float
    contract_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    stops_level_points: int
    freeze_level_points: int
    spread_points: int
    trade_mode: int
    filling_mode: int
    visible: bool


@dataclass(frozen=True, slots=True)
class Candidate:
    symbol: str
    description: str
    score: float
    reasons: tuple[str, ...]
    tradable: bool
    visible: bool


@dataclass(slots=True)
class Trade:
    strategy: str
    side: str
    entry_time: datetime
    entry: float
    stop: float
    target: float | None
    volume: float
    risk_cash: float
    exit_time: datetime | None = None
    exit: float | None = None
    pnl: float = 0.0
    exit_reason: str = ""
    spread_cost: float = 0.0
    slippage_cost: float = 0.0
    mae: float = 0.0
    mfe: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def holding_minutes(self) -> float:
        if self.exit_time is None:
            return 0.0
        return (self.exit_time - self.entry_time).total_seconds() / 60.0


@dataclass(frozen=True, slots=True)
class Skip:
    date: str
    strategy: str
    reason: str

