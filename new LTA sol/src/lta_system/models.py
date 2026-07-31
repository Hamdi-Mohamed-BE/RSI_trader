from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class VolumeProfile:
    name: str
    start: datetime
    end: datetime
    low: float
    high: float
    poc: float
    vah: float
    val: float
    hvns: tuple[float, ...] = ()
    lvns: tuple[float, ...] = ()
    source: str = "TICK_VOLUME_APPROX"


@dataclass(frozen=True)
class Zone:
    zone_id: str
    kind: str
    pattern: str
    created_at: datetime
    proximal: float
    distal: float
    impulse_atr: float
    touches: int
    fresh: bool

    @property
    def low(self) -> float:
        return min(self.proximal, self.distal)

    @property
    def high(self) -> float:
        return max(self.proximal, self.distal)


@dataclass(frozen=True)
class Signal:
    time: datetime
    symbol: str
    direction: str
    model: str
    archetype: str
    grade: str
    score: int
    entry: float
    stop: float
    target: float
    rr: float
    level: float
    level_name: str
    zone_id: str | None
    context_quality: str
    reasons: tuple[str, ...]
    invalidation: str
    volume_source: str = "TICK_VOLUME_APPROX"

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["time"] = self.time.isoformat()
        return result


@dataclass(frozen=True)
class Trade:
    signal_time: datetime
    entry_time: datetime
    exit_time: datetime
    symbol: str
    direction: str
    model: str
    grade: str
    entry: float
    stop: float
    target: float
    exit_price: float
    result_r: float
    risk_cash: float
    pnl_cash: float
    balance_after: float
    exit_reason: str
    mae_r: float
    mfe_r: float

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in ("signal_time", "entry_time", "exit_time"):
            result[key] = getattr(self, key).isoformat()
        return result


@dataclass(frozen=True)
class BacktestStats:
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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

