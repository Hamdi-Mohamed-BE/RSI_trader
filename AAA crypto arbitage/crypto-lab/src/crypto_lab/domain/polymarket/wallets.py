"""Wallet analytics for the copy-trading research (Model D).

Stats are descriptive, not predictive: a high historical win rate is partly luck and survivorship. The copy engine
must select wallets walk-forward (rank on a past window, evaluate on the next one).
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from statistics import median

ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    rank: int
    wallet: str
    user_name: str
    pnl: Decimal
    volume: Decimal


@dataclass(frozen=True, slots=True)
class WalletTrade:
    wallet: str
    tx_hash: str
    asset: str
    condition_id: str
    side: str  # BUY | SELL
    size: Decimal
    price: Decimal
    outcome: str
    outcome_index: int
    title: str
    slug: str
    event_slug: str
    at: datetime

    @property
    def usdc(self) -> Decimal:
        return self.size * self.price


@dataclass(frozen=True, slots=True)
class ClosedPosition:
    wallet: str
    asset: str
    condition_id: str
    avg_price: Decimal
    total_bought: Decimal
    realized_pnl: Decimal
    cur_price: Decimal
    outcome: str
    title: str
    slug: str
    event_slug: str
    closed_at: datetime | None


class WalletStyle(StrEnum):
    HEDGED = "hedged"  # often holds both sides of a market: arbitrage / market making
    FAVOURITE = "favourite"  # mostly buys at high prices (> 0.85)
    LONGSHOT = "longshot"  # mostly buys at low prices (< 0.20)
    DIRECTIONAL = "directional"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class WalletStats:
    closed_positions: int
    wins: int
    losses: int
    win_rate: float | None
    win_rate_lower95: float | None
    realized_pnl: Decimal
    profit_factor: float | None
    trades: int
    active_days: int
    trades_per_day: float | None
    median_trade_usdc: Decimal | None
    both_sides_ratio: float | None
    avg_buy_price: Decimal | None
    first_trade_at: datetime | None
    last_trade_at: datetime | None
    style: WalletStyle


def wilson_lower_bound(successes: int, n: int, z: float = 1.96) -> float | None:
    """Lower bound of the Wilson score interval: a win rate that small samples cannot inflate."""
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return max(0.0, (centre - margin) / denom)


def _style(both_sides_ratio: float | None, avg_buy: Decimal | None) -> WalletStyle:
    if both_sides_ratio is None or avg_buy is None:
        return WalletStyle.UNKNOWN
    if both_sides_ratio >= 0.3:
        return WalletStyle.HEDGED
    if avg_buy >= Decimal("0.85"):
        return WalletStyle.FAVOURITE
    if avg_buy <= Decimal("0.20"):
        return WalletStyle.LONGSHOT
    return WalletStyle.DIRECTIONAL


def compute_wallet_stats(closed: Sequence[ClosedPosition], trades: Sequence[WalletTrade]) -> WalletStats:
    wins = sum(1 for c in closed if c.realized_pnl > 0)
    losses = sum(1 for c in closed if c.realized_pnl < 0)
    decided = wins + losses
    gross_win = sum((c.realized_pnl for c in closed if c.realized_pnl > 0), ZERO)
    gross_loss = -sum((c.realized_pnl for c in closed if c.realized_pnl < 0), ZERO)

    buys = [t for t in trades if t.side.upper() == "BUY"]
    outcomes_by_condition: defaultdict[str, set[int]] = defaultdict(set)
    for t in buys:
        outcomes_by_condition[t.condition_id].add(t.outcome_index)
    both = sum(1 for s in outcomes_by_condition.values() if len(s) >= 2)
    both_ratio = both / len(outcomes_by_condition) if outcomes_by_condition else None

    buy_usdc = sum((t.usdc for t in buys), ZERO)
    buy_shares = sum((t.size for t in buys), ZERO)
    avg_buy = (buy_usdc / buy_shares) if buy_shares else None

    times = sorted(t.at for t in trades)
    days = {t.at.date() for t in trades}
    span_days = ((times[-1] - times[0]).total_seconds() / 86400 + 1) if times else 0

    return WalletStats(
        closed_positions=len(closed),
        wins=wins,
        losses=losses,
        win_rate=wins / decided if decided else None,
        win_rate_lower95=wilson_lower_bound(wins, decided),
        realized_pnl=sum((c.realized_pnl for c in closed), ZERO),
        profit_factor=float(gross_win / gross_loss) if gross_loss else None,
        trades=len(trades),
        active_days=len(days),
        trades_per_day=len(trades) / span_days if span_days else None,
        median_trade_usdc=Decimal(str(median([float(t.usdc) for t in trades]))) if trades else None,
        both_sides_ratio=both_ratio,
        avg_buy_price=avg_buy,
        first_trade_at=times[0] if times else None,
        last_trade_at=times[-1] if times else None,
        style=_style(both_ratio, avg_buy),
    )
