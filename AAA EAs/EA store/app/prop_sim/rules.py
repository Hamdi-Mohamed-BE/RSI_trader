"""Prop programme registry and EA-compatibility rules.

Each programme is a JSON file in ``data/prop-rules``. Values carry their verification status (``official`` = read on
the firm's own page, ``secondary`` = reputable comparison/review page) and check date; the firm's current terms
always override. The engine only interprets the generic fields below, so adding a firm means adding a file.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from ..catalog import STORE_ROOT

RULES_ROOT = STORE_ROOT / "data" / "prop-rules"
LOGO_ROOT = STORE_ROOT / "static" / "prop-firms"
LOGO_EXTENSIONS = ("svg", "png", "webp")
MaxLossType = Literal["static", "eod_trailing", "eod_trailing_lock_initial"]
WEEKEND_BLOCK_SHARE = 0.10  # above this share of weekend-held trades the strategy is treated as multi-day


@dataclass(frozen=True)
class Phase:
    name: str
    target_pct: float
    min_trading_days: int = 0
    min_profitable_days: int = 0
    profitable_day_pct: float = 0.0
    time_limit_days: int | None = None


@dataclass(frozen=True)
class Payout:
    split_pct: float
    first_after_days: int
    every_days: int
    min_usd: float
    fee_refund: bool


@dataclass(frozen=True)
class Programme:
    id: str
    firm: str
    programme: str
    verification: dict[str, Any]
    ea_policy: dict[str, Any]
    platforms: tuple[str, ...]
    account_sizes: tuple[int, ...]
    fees: dict[str, float]
    fee_currency: str
    fee_note: str
    phases: tuple[Phase, ...]
    daily_loss_pct: float | None
    max_loss_pct: float
    max_loss_type: MaxLossType
    payout: Payout
    consistency_best_day_pct: float | None = None
    consistency_applies: str = "challenge"
    hold_time_min_seconds: int | None = None
    hold_time_applies: str = "funded"
    news: dict[str, str] = field(default_factory=lambda: {"challenge": "allowed", "funded": "allowed"})
    weekend_holding: dict[str, bool] = field(default_factory=lambda: {"challenge": True, "funded": True})
    straddle_allowed: bool = True
    handover_days: tuple[int, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.firm} — {self.programme}"

    @property
    def mt5(self) -> bool:
        return "MT5" in self.platforms

    def fee_for(self, size: int) -> float | None:
        value = self.fees.get(str(size))
        return float(value) if value is not None else None

    @property
    def firm_slug(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.firm.lower()).strip("-")

    @property
    def logo_url(self) -> str | None:
        """Local logo file ``static/prop-firms/<firm-slug>.{svg,png,webp}`` if the owner has added one."""
        for ext in LOGO_EXTENSIONS:
            if (LOGO_ROOT / f"{self.firm_slug}.{ext}").is_file():
                return f"/static/prop-firms/{self.firm_slug}.{ext}"
        return None

    def public(self) -> dict[str, Any]:
        """JSON-safe summary for the page."""
        return {
            "id": self.id, "firm": self.firm, "firm_slug": self.firm_slug, "logo_url": self.logo_url,
            "programme": self.programme, "label": self.label,
            "verification": self.verification, "ea_policy": self.ea_policy, "platforms": list(self.platforms),
            "account_sizes": list(self.account_sizes), "fees": self.fees, "fee_currency": self.fee_currency,
            "fee_note": self.fee_note,
            "phases": [phase.__dict__ for phase in self.phases],
            "daily_loss_pct": self.daily_loss_pct, "max_loss_pct": self.max_loss_pct,
            "max_loss_type": self.max_loss_type, "payout": self.payout.__dict__,
            "consistency_best_day_pct": self.consistency_best_day_pct,
            "hold_time_min_seconds": self.hold_time_min_seconds, "news": self.news,
            "weekend_holding": self.weekend_holding, "straddle_allowed": self.straddle_allowed,
            "handover_days": list(self.handover_days),
        }


def _programme(raw: dict[str, Any]) -> Programme:
    daily = raw.get("daily_loss") or None
    consistency = raw.get("consistency") or None
    hold = raw.get("hold_time") or None
    return Programme(
        id=str(raw["id"]), firm=str(raw["firm"]), programme=str(raw["programme"]),
        verification=dict(raw.get("verification") or {}), ea_policy=dict(raw.get("ea_policy") or {}),
        platforms=tuple(raw.get("platforms") or ()), account_sizes=tuple(int(s) for s in raw["account_sizes"]),
        fees={str(k): float(v) for k, v in (raw.get("fees") or {}).items()},
        fee_currency=str(raw.get("fee_currency") or "USD"), fee_note=str(raw.get("fee_note") or ""),
        phases=tuple(Phase(**p) for p in raw.get("phases") or ()),
        daily_loss_pct=float(daily["pct"]) if daily else None,
        max_loss_pct=float(raw["max_loss"]["pct"]), max_loss_type=raw["max_loss"]["type"],
        payout=Payout(**raw["payout"]),
        consistency_best_day_pct=float(consistency["best_day_max_pct_of_positive_profit"]) if consistency else None,
        consistency_applies=str(consistency.get("applies", "challenge")) if consistency else "challenge",
        hold_time_min_seconds=int(hold["min_seconds"]) if hold else None,
        hold_time_applies=str(hold.get("applies", "funded")) if hold else "funded",
        news=dict(raw.get("news") or {"challenge": "allowed", "funded": "allowed"}),
        weekend_holding={k: bool(v) for k, v in (raw.get("weekend_holding") or {}).items()} or
        {"challenge": True, "funded": True},
        straddle_allowed=bool(raw.get("straddle_allowed", True)),
        handover_days=tuple(int(d) for d in raw.get("handover_days") or ()),
    )


@lru_cache(maxsize=1)
def _load(root: str, stamp: float) -> dict[str, Programme]:
    programmes = [_programme(json.loads(path.read_text(encoding="utf-8"))) for path in sorted(Path(root).glob("*.json"))]
    return {p.id: p for p in sorted(programmes, key=lambda p: (p.firm, p.programme))}


def programmes() -> dict[str, Programme]:
    stamp = max((p.stat().st_mtime for p in RULES_ROOT.glob("*.json")), default=0.0)
    return _load(str(RULES_ROOT), stamp)


def get_programme(programme_id: str) -> Programme:
    try:
        return programmes()[programme_id]
    except KeyError as exc:
        raise ValueError(f"Unknown programme: {programme_id}") from exc


@dataclass(frozen=True)
class Compatibility:
    status: Literal["ok", "adjusted", "approval", "restricted", "blocked"]
    reasons: tuple[str, ...]

    @property
    def selectable(self) -> bool:
        return self.status != "blocked"


def compatibility(programme: Programme, profile: Any) -> Compatibility:
    """Decide whether an EA (``ledger.EaProfile``) can be simulated under a programme, and why not."""
    blocked: list[str] = []
    notes: list[str] = []
    if not programme.mt5:
        blocked.append("Programme does not offer MT5.")
    stages = [s for s in ("challenge", "funded") if s == "funded" or programme.phases]
    for stage in stages:
        if profile.weekend_holds and not programme.weekend_holding.get(stage, True):
            if profile.weekend_hold_share > WEEKEND_BLOCK_SHARE:
                blocked.append(f"Holds {profile.weekend_hold_share:.0%} of trades over weekends; weekend holding is "
                               f"not allowed on the {stage} account.")
            else:
                notes.append(f"{profile.weekend_hold_share:.1%} of trades were held over a weekend; on the {stage} "
                             "account they must be closed on Friday (use a Friday-close setting). The simulation keeps "
                             "the historical result of those trades.")
        if profile.news_ea and programme.news.get(stage, "allowed") != "allowed":
            blocked.append(f"Trades scheduled news; news trading is restricted on the {stage} account.")
    if profile.straddle and not programme.straddle_allowed:
        blocked.append("Uses a pre-news straddle; straddling is banned.")
    if programme.hold_time_min_seconds and profile.short_trade_share > 0:
        notes.append(f"{profile.short_trade_share:.0%} of trades close within {programme.hold_time_min_seconds}s; "
                     "their profit is voided in the funded stage (modelled).")
    if blocked:
        return Compatibility("blocked", tuple(dict.fromkeys(blocked)))
    policy = programme.ea_policy.get("status", "allowed")
    if policy == "approval":
        return Compatibility("approval", ("The firm requires written EA approval before use.", *notes))
    if policy == "restricted":
        return Compatibility("restricted", ("The firm restricts EAs (own code with proof of source).", *notes))
    return Compatibility("adjusted" if notes else "ok", tuple(notes))
