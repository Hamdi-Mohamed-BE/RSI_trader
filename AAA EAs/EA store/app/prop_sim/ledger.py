"""Evidence ledger: cached native MT5 trades -> R-normalised trades -> sized, guarded daily features.

Every trade's result is expressed in R (net P/L ÷ planned risk at entry, from the cache's ``estimated_r``), then
re-sized to the user's risk. Guards (daily stop, profit lock, open-risk cap, entries per day) are applied in one
chronological pass over the historical timeline, because they depend only on that day's own events. Only the
account balance is path-dependent, which the engine handles.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache
from typing import Any

import numpy as np

from ..catalog import Product, get_product, get_sellable_catalog
from ..evidence_cache import CACHE_ROOT, validate_period

LOT_STEP = 0.01
SHORT_TRADE_SECONDS = 120


@dataclass(frozen=True)
class LedgerTrade:
    ea: str
    symbol: str
    opened: datetime
    closed: datetime
    r: float  # net result in R at the source's planned risk
    volume: float
    risk_cash: float

    @property
    def seconds(self) -> float:
        return (self.closed - self.opened).total_seconds()


@dataclass(frozen=True)
class EaProfile:
    slug: str
    label: str
    symbol: str
    timeframe: str
    mode: str
    start: date
    end: date
    trades: int
    weekend_holds: bool
    weekend_hold_share: float
    news_ea: bool
    straddle: bool
    short_trade_share: float
    evidence_status: str

    def public(self) -> dict[str, Any]:
        return {"slug": self.slug, "label": self.label, "symbol": self.symbol, "timeframe": self.timeframe,
                "mode": self.mode, "from": self.start.isoformat(), "to": self.end.isoformat(),
                "trades": self.trades, "weekend_holds": self.weekend_holds,
                "weekend_hold_share": round(self.weekend_hold_share, 4), "news_ea": self.news_ea,
                "straddle": self.straddle, "short_trade_share": round(self.short_trade_share, 4),
                "evidence_status": self.evidence_status}


def recommended_mode(product: Product) -> str:
    if product.recommended_dynamic_mode and product.dynamic_mode_supported:
        return "dynamic"
    if product.recommended_safe_mode and product.safe_filter_supported:
        return "safe"
    return "standard"


def _dt(value: Any) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _holds_weekend(opened: datetime, closed: datetime) -> bool:
    day = opened.date()
    while day <= closed.date():
        if day.weekday() == 5:  # Saturday: position open while FX/CFD markets are closed
            midday = datetime.combine(day, datetime.min.time()) + timedelta(hours=12)
            if opened <= midday <= closed:
                return True
        day += timedelta(days=1)
    return False


@lru_cache(maxsize=256)
def _load(slug: str, mode: str, period: str, stamp: int) -> tuple[EaProfile, tuple[LedgerTrade, ...]] | None:
    base = CACHE_ROOT / "products" / slug / mode
    summary_path, trades_path = base / f"{period}.json", base / f"{period}.trades.json"
    if not summary_path.is_file() or not trades_path.is_file():
        return None
    summary = json.loads(summary_path.read_text(encoding="utf-8-sig"))
    rows = json.loads(trades_path.read_text(encoding="utf-8-sig"))
    product = get_product(slug)
    stats = summary.get("stats") or {}
    start, end = _dt(stats.get("from")), _dt(stats.get("to"))
    if product is None or start is None or end is None:
        return None
    trades: list[LedgerTrade] = []
    for row in rows:
        opened, closed = _dt(row.get("open_time")), _dt(row.get("close_time"))
        risk = float(row.get("estimated_risk_cash") or 0.0)
        if opened is None or closed is None or risk <= 0:
            continue
        r = row.get("estimated_r")
        r_value = float(r) if r is not None else float(row.get("net_profit") or 0.0) / risk
        trades.append(LedgerTrade(slug, str(row.get("symbol") or product.canonical), opened, closed, r_value,
                                  float(row.get("volume") or 0.0), risk))
    trades.sort(key=lambda t: (t.opened, t.closed))
    news = slug.startswith("news-pulse-")
    weekend = sum(_holds_weekend(t.opened, t.closed) for t in trades)
    profile = EaProfile(
        slug=slug, label=product.label, symbol=product.canonical, timeframe=product.timeframe, mode=mode,
        start=start.date(), end=end.date(), trades=len(trades),
        weekend_holds=weekend > 0,
        weekend_hold_share=weekend / len(trades) if trades else 0.0,
        news_ea=news, straddle=news,
        short_trade_share=(sum(t.seconds < SHORT_TRADE_SECONDS for t in trades) / len(trades)) if trades else 0.0,
        evidence_status=product.evidence.status if product.evidence else "pending",
    )
    return profile, tuple(trades)


def load_ea(slug: str, period: str) -> tuple[EaProfile, tuple[LedgerTrade, ...]] | None:
    validate_period(period)
    product = get_product(slug)
    if product is None or product.evidence is None:
        return None
    mode = "standard" if slug.startswith("news-pulse-") else recommended_mode(product)
    path = CACHE_ROOT / "products" / slug / mode / f"{period}.trades.json"
    stamp = path.stat().st_mtime_ns if path.is_file() else 0
    return _load(slug, mode, period, stamp)


def available_eas(period: str) -> list[EaProfile]:
    profiles = []
    for product in get_sellable_catalog():
        loaded = load_ea(product.slug, period)
        if loaded is not None and loaded[1]:
            profiles.append(loaded[0])
    return profiles


# --------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Selection:
    slug: str
    risk_pct: float  # planned risk per trade, % of the initial account balance


@dataclass(frozen=True)
class Guards:
    daily_stop_pct: float | None = None  # stop new entries once the day's closed loss reaches this % of initial
    profit_lock_pct: float | None = None  # stop new entries once the day's closed gain reaches this %
    max_open_risk_pct: float | None = None  # skip entries that would push open planned risk above this %
    max_entries_per_day: int | None = None
    # Daily equity controls (the '-2% daily equity stop / +4% profit close' flow). When the day's P/L reaches the
    # level, the crossing trade is capped at it, every other open position is closed flat (0 R; intraday marks are
    # not recorded) and no new entries are taken until the next day. Approximation of a minute-level liquidation.
    equity_stop_pct: float | None = None
    profit_close_pct: float | None = None


@dataclass
class Features:
    """Daily arrays over the evidence window (calendar days), in fractions of the initial balance."""

    start: date
    days: int
    pnl: np.ndarray
    low_closed: np.ndarray  # worst intraday closed-P/L point (<= 0)
    low_envelope: np.ndarray  # worst point if every open position sat at its full stop (<= 0)
    opened: np.ndarray  # accepted entries per day
    per_ea_pnl: dict[str, np.ndarray] = field(default_factory=dict)
    accepted: list[dict[str, Any]] = field(default_factory=list)
    skipped: dict[str, int] = field(default_factory=dict)


def build_features(ledgers: dict[str, tuple[LedgerTrade, ...]], selections: list[Selection], account_size: float,
                   guards: Guards, start: date, end: date, void_short_profit_seconds: int | None = None) -> Features:
    """Apply sizing, lot rounding and guards on the historical timeline and aggregate to daily features."""
    risk_of = {s.slug: s.risk_pct / 100.0 for s in selections}
    trades = [t for s in selections for t in ledgers.get(s.slug, ()) if start <= t.opened.date() <= end]
    events: list[tuple[datetime, int, int]] = []  # (time, 0=close first on ties / 1=open, trade index)
    for i, t in enumerate(trades):
        events.append((t.opened, 1, i))
        events.append((t.closed, 0, i))
    events.sort(key=lambda e: (e[0], e[1], e[2]))

    n_days = (end - start).days + 1
    pnl = np.zeros(n_days)
    low_closed = np.zeros(n_days)
    low_env = np.zeros(n_days)
    opened = np.zeros(n_days)
    per_ea: defaultdict[str, np.ndarray] = defaultdict(lambda: np.zeros(n_days))
    skipped: defaultdict[str, int] = defaultdict(int)
    accepted: dict[int, tuple[float, float]] = {}  # index -> (risk fraction actually used, pnl fraction)
    accepted_rows: list[dict[str, Any]] = []

    day_key = -1
    day_realized = 0.0
    day_entries = 0
    open_risk = 0.0
    halted: str | None = None  # reason the day was flattened by an equity control
    for when, kind, i in events:
        d = (when.date() - start).days
        if d != day_key:
            # Positions carried into every day since the last event (including quiet days) count at full stop.
            if open_risk > 0:
                for x in range(max(day_key + 1, 0), min(d, n_days - 1) + 1):
                    low_env[x] = min(low_env[x], -open_risk)
            day_key, day_realized, day_entries, halted = d, 0.0, 0, None
        t = trades[i]
        if kind == 1:  # entry
            rf = risk_of[t.ea]
            reason = halted
            if reason is not None:
                pass
            elif guards.daily_stop_pct is not None and day_realized <= -guards.daily_stop_pct / 100:
                reason = "daily loss guard"
            elif guards.profit_lock_pct is not None and day_realized >= guards.profit_lock_pct / 100:
                reason = "daily profit lock"
            elif guards.max_entries_per_day is not None and day_entries >= guards.max_entries_per_day:
                reason = "entries-per-day cap"
            elif guards.max_open_risk_pct is not None and open_risk + rf > guards.max_open_risk_pct / 100 + 1e-12:
                reason = "open-risk cap"
            scale = 1.0
            if reason is None and t.volume > 0:
                wanted = t.volume * (rf * account_size) / t.risk_cash
                rounded = math.floor(wanted / LOT_STEP + 1e-9) * LOT_STEP
                if rounded < LOT_STEP:
                    reason = "below minimum lot"
                else:
                    scale = rounded / wanted
            if reason:
                skipped[reason] += 1
                continue
            used = rf * scale
            result = t.r * used
            if void_short_profit_seconds is not None and t.seconds < void_short_profit_seconds and result > 0:
                result = 0.0
            accepted[i] = (used, result)
            open_risk += used
            day_entries += 1
            if 0 <= d < n_days:
                opened[d] += 1
                low_env[d] = min(low_env[d], day_realized - open_risk)
        elif i in accepted:  # exit of an accepted trade
            used, result = accepted.pop(i)
            open_risk = max(0.0, open_risk - used)
            trigger = None
            if guards.equity_stop_pct is not None and day_realized + result <= -guards.equity_stop_pct / 100:
                result, trigger = -guards.equity_stop_pct / 100 - day_realized, "daily equity stop"
            elif guards.profit_close_pct is not None and day_realized + result >= guards.profit_close_pct / 100:
                result, trigger = guards.profit_close_pct / 100 - day_realized, "daily profit close"
            day_realized += result
            if 0 <= d < n_days:
                pnl[d] += result
                per_ea[t.ea][d] += result
                low_closed[d] = min(low_closed[d], day_realized)
                low_env[d] = min(low_env[d], day_realized - open_risk)
                accepted_rows.append({"ea": t.ea, "opened": t.opened.isoformat(), "closed": when.isoformat(),
                                      "pnl": result, "r": t.r, "risk": used})
            if trigger:
                halted = trigger
                for j in list(accepted):  # flatten every other open position at 0 R
                    other_used, _ = accepted.pop(j)
                    skipped[f"closed flat by {trigger}"] += 1
                    if 0 <= d < n_days:
                        accepted_rows.append({"ea": trades[j].ea, "opened": trades[j].opened.isoformat(),
                                              "closed": when.isoformat(), "pnl": 0.0, "r": 0.0,
                                              "risk": other_used, "forced": trigger})
                open_risk = 0.0
    return Features(start=start, days=n_days, pnl=pnl, low_closed=low_closed, low_envelope=low_env, opened=opened,
                    per_ea_pnl=dict(per_ea), accepted=accepted_rows, skipped=dict(skipped))
