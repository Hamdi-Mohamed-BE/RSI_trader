"""Validated simulation requests, orchestration, caching and presets for the public prop simulator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from ..catalog import PACKAGE_ROOT, STORE_ROOT
from .engine import SimConfig, fan_chart, sample_indices, simulate, summarise
from .ledger import Guards, Selection, available_eas, build_features, load_ea
from .metrics import combo_stats, common_window
from .rules import LOGO_ROOT, Programme, compatibility, get_programme, programmes

FTMO_PACKAGE = PACKAGE_ROOT / "FTMO Thirteen EA Deployment 2026-09-27" / "PACKAGE.json"
SUGGESTIONS = STORE_ROOT / "data" / "prop-sim" / "suggestions.json"
MAX_PATHS = 5000
ASSUMPTIONS = (
    "Evidence: each EA's cached native MT5 trade list for the chosen window, combined as an arithmetic overlay of "
    "separate tests (not one simultaneous shared-margin run).",
    "Every trade is re-sized from its own planned risk (R) to your risk; volume is rounded DOWN to 0.01 lot and "
    "trades that cannot reach the minimum lot are skipped and counted.",
    "Source-broker commissions and swaps are kept; spreads and costs at the prop firm can differ.",
    "Daily loss resets on the UTC calendar day of the evidence (firms often reset at CE(S)T or server midnight).",
    "Intraday floating drawdown is not recorded: 'conservative' assumes every open position sits at its full stop "
    "at the worst moment of the day; 'optimistic' uses closed trades only. The real result lies between them.",
    "Paths are built from whole historical calendar blocks, so all selected EAs keep their real day-by-day "
    "correlation. Frequencies are simulated scenario rates, not a guarantee or a forecast of your result.",
    "Daily equity stop / profit close: when the day's P/L reaches the level, the crossing trade is capped at it, "
    "other open positions are closed flat (0 R) and entries stop until the next day. This approximates a "
    "minute-level liquidation; the research audit with minute equity (Daily Equity Controls Audit 2026-09-29) is exact.",
    "Handover time between phases uses the programme's typical delay; firm review and payout processing time is "
    "not modelled. Fees are not refunded unless the programme states so.",
)


class EaPick(BaseModel):
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    risk_pct: float = Field(gt=0, le=3)


class SimRequest(BaseModel):
    programme_id: str = Field(max_length=80, pattern=r"^[a-z0-9-]+$")
    account_size: int = Field(gt=0, le=2_000_000)
    fee: float | None = Field(default=None, ge=0, le=100_000)
    eas: list[EaPick] = Field(min_length=1, max_length=40)
    sizing: Literal["pct_initial", "pct_balance"] = "pct_initial"
    daily_stop_pct: float | None = Field(default=None, gt=0, le=10)
    profit_lock_pct: float | None = Field(default=None, gt=0, le=20)
    max_open_risk_pct: float | None = Field(default=None, gt=0, le=30)
    max_entries_per_day: int | None = Field(default=None, ge=1, le=100)
    equity_stop_pct: float | None = Field(default=None, gt=0, le=20)
    profit_close_pct: float | None = Field(default=None, gt=0, le=30)
    period: Literal["1y", "3y", "5y"] = "3y"
    method: Literal["bootstrap", "rolling"] = "bootstrap"
    paths: int = Field(default=2000, ge=100, le=MAX_PATHS)
    horizon_days: int = Field(default=365, ge=30, le=730)
    block_days: int = Field(default=28, ge=7, le=90)
    seed: int = Field(default=20260929, ge=0, le=2**31 - 1)

    @field_validator("eas")
    @classmethod
    def unique_eas(cls, value: list[EaPick]) -> list[EaPick]:
        if len({pick.slug for pick in value}) != len(value):
            raise ValueError("Each EA can be selected once.")
        return value


def _validate(req: SimRequest) -> Programme:
    programme = get_programme(req.programme_id)
    if req.account_size not in programme.account_sizes:
        raise ValueError(f"{programme.label} offers account sizes {', '.join(map(str, programme.account_sizes))}.")
    return programme


def run_simulation(req: SimRequest) -> dict[str, Any]:
    return json.loads(_cached_run(req.model_dump_json()))


@lru_cache(maxsize=128)
def _cached_run(payload: str) -> str:
    return json.dumps(_run(SimRequest.model_validate_json(payload)), allow_nan=False)


def _run(req: SimRequest) -> dict[str, Any]:
    programme = _validate(req)
    ledgers, profiles, compat = {}, {}, {}
    for pick in req.eas:
        loaded = load_ea(pick.slug, req.period)
        if loaded is None:
            raise ValueError(f"No cached {req.period} evidence for '{pick.slug}'.")
        profile, trades = loaded
        verdict = compatibility(programme, profile)
        if not verdict.selectable:
            raise ValueError(f"{profile.label} cannot run on {programme.label}: {' '.join(verdict.reasons)}")
        ledgers[pick.slug], profiles[pick.slug] = trades, profile
        compat[pick.slug] = {"status": verdict.status, "reasons": list(verdict.reasons)}
    start, end = common_window([(p.start, p.end) for p in profiles.values()])
    selections = [Selection(p.slug, p.risk_pct) for p in req.eas]
    guards = Guards(daily_stop_pct=req.daily_stop_pct, profit_lock_pct=req.profit_lock_pct,
                    max_open_risk_pct=req.max_open_risk_pct, max_entries_per_day=req.max_entries_per_day,
                    equity_stop_pct=req.equity_stop_pct, profit_close_pct=req.profit_close_pct)
    challenge = build_features(ledgers, selections, req.account_size, guards, start, end)
    void = programme.hold_time_min_seconds if programme.hold_time_applies in ("funded", "both") else None
    funded = (build_features(ledgers, selections, req.account_size, guards, start, end, void) if void else challenge)
    fee = req.fee if req.fee is not None else programme.fee_for(req.account_size)
    cfg = SimConfig(account_size=req.account_size, fee=fee, sizing=req.sizing, horizon_days=req.horizon_days,
                    paths=min(req.paths, MAX_PATHS), method=req.method, block_days=req.block_days, seed=req.seed)
    idx = sample_indices(challenge.days, cfg)
    results = {
        mode: summarise(simulate(programme, challenge, funded, cfg, idx, mode), cfg, req.horizon_days)
        for mode in ("envelope", "closed")
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "programme": programme.public(),
        "request": req.model_dump(),
        "fee_used": fee,
        "fee_currency_note": (f"Default fee is the {programme.fee_currency} list price used as-is; enter your own "
                              "price in the account currency for an exact expected value.") if req.fee is None else "",
        "results": {"conservative": results["envelope"], "optimistic": results["closed"]},
        "stats": combo_stats(challenge, req.sizing),
        "fan": fan_chart(challenge.pnl, idx, req.sizing),
        "compatibility": compat,
        "eas": {slug: profile.public() for slug, profile in profiles.items()},
        "assumptions": list(ASSUMPTIONS),
    }


# ---- presets and catalogue ------------------------------------------------------------------------------------
def ftmo13_presets() -> list[dict[str, Any]]:
    """The saved FTMO 13-EA package, as installed and with the tested (not installed) -2% / +4% daily controls."""
    if not FTMO_PACKAGE.is_file():
        return []
    package = json.loads(FTMO_PACKAGE.read_text(encoding="utf-8"))
    balance = float(package.get("reference_balance") or 10_000)
    risk_usd = float(package.get("risk_usd") or 50)
    base = {
        "programme_id": "ftmo-2step-swing", "account_size": int(balance), "sizing": "fixed_usd", "risk_usd": risk_usd,
        "eas": [{"slug": e["slug"], "risk_pct": round(risk_usd / balance * 100, 4), "risk_usd": risk_usd}
                for e in package.get("entries", [])],
    }
    installed_note = (f"${risk_usd:,.0f} planned risk per trade on ${balance:,.0f} (volume rounded down), News EAs off. "
                      "Swing is used because Nasdaq Overnight and Nasdaq 5M hold overnight/weekend positions.")
    return [
        {**base, "id": "ftmo13-controls", "label": "FTMO 13 package + −2% / +4% daily controls",
         "guards": {"equity_stop_pct": 2.0, "profit_close_pct": 4.0},
         "note": installed_note + " Adds the −2% daily equity stop and +4% daily profit close that were tested in the "
                 "Daily Equity Controls Audit — tested, NOT installed on the live package."},
        {**base, "id": "ftmo13", "label": f"FTMO 13 package as installed ({package.get('version', '')})", "guards": {},
         "note": installed_note},
    ]

def load_suggestions() -> dict[str, Any] | None:
    if not SUGGESTIONS.is_file():
        return None
    return dict(json.loads(SUGGESTIONS.read_text(encoding="utf-8")))


@lru_cache(maxsize=4)
def _catalog(stamp: str) -> str:
    profiles = available_eas("3y")
    progs = programmes()
    matrix = {
        pid: {p.slug: {"status": (v := compatibility(prog, p)).status, "reasons": list(v.reasons)} for p in profiles}
        for pid, prog in progs.items()
    }
    return json.dumps({
        "programmes": [p.public() for p in progs.values()],
        "eas": [p.public() for p in profiles],
        "compatibility": matrix,
        "presets": ftmo13_presets(),
    })


def catalog_payload() -> dict[str, Any]:
    # Refresh hourly, and immediately when firm logos are added or replaced.
    logos = max((p.stat().st_mtime for p in LOGO_ROOT.glob("*")), default=0.0) if LOGO_ROOT.is_dir() else 0.0
    stamp = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H')}|{logos}"
    payload = json.loads(_catalog(stamp))
    payload["suggestions"] = load_suggestions()
    return payload
