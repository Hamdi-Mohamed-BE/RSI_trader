"""Validated simulation requests, orchestration, caching and presets for the public prop simulator."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from ..catalog import PACKAGE_ROOT, STORE_ROOT, get_website_catalog
from .engine import SimConfig, fan_chart, sample_indices, simulate, summarise
from .ledger import Guards, Selection, build_features, load_ea
from .metrics import combo_stats, common_window
from .rules import LOGO_ROOT, RULES_ROOT, Programme, compatibility, get_programme, programmes

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
    "at the worst moment of the day; the second scenario uses closed trades only. These are assumptions, "
    "NOT guaranteed bounds on actual equity losses or pass rates (gaps can exceed stops).",
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
    period: Literal["6m", "1y", "3y", "5y"] = "3y"
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
    return json.loads(_cached_run(req.model_dump_json(), _data_stamp()))


@lru_cache(maxsize=128)
def _cached_run(payload: str, data_stamp: str) -> str:
    return json.dumps(_run(SimRequest.model_validate_json(payload)), allow_nan=False)


def _run(req: SimRequest) -> dict[str, Any]:
    programme = _validate(req)
    ledgers, profiles, compat = {}, {}, {}
    for pick in req.eas:
        loaded = load_ea(pick.slug, req.period, ftmo_mode(pick.slug))
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
    unbounded = any(p.risk_basis == "historical_loss_reference" for p in profiles.values())
    assumptions = list(ASSUMPTIONS)
    if unbounded:
        assumptions += [
            "Hourly EAs have NO SL: their risk input sizes against a frozen largest completed historical loss, "
            "NOT planned-stop R. The open-risk envelope reserves that reference only; actual floating losses "
            "can exceed it without bound. Neither scenario is a conservative upper/lower bound.",
            "Hourly evidence is the original source-broker fixed-lot ledger, normalized by its frozen cash-loss "
            "reference. This proxy assumes 0.01 lot step/minimum and skips below-minimum trades; it does not "
            "reproduce broker-specific conversion or the normal BAT's minimum-lot override.",
            "Hourly hours and sizing reference were selected on this same recent history and failed the "
            "long-history gate. This is NOT a native FTMO guarded-portfolio validation or a payout forecast.",
        ]
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
        "assumptions": assumptions,
        "historical_risk_experiment": unbounded,
        "notice": ("NO-STOP EXPERIMENT: historical-loss sizing is not a loss cap. Scenario rates are not "
                   "equity-risk bounds or validated FTMO forecasts; the guarded FTMO launcher excludes these EAs.")
                  if unbounded else "Cached standalone-ledger proxy, not an exact replay of the installed FTMO guard.",
    }


# ---- presets and catalogue ------------------------------------------------------------------------------------
def ftmo_mode(slug: str) -> str | None:
    """Avoid silently using Markov-safe evidence for FTMO's non-Markov Squeeze."""
    if not FTMO_PACKAGE.is_file():
        return None
    package = json.loads(FTMO_PACKAGE.read_text(encoding="utf-8"))
    row = next((e for e in package.get("entries", []) if e["slug"] == slug), {})
    if slug == "xau-squeeze-momentum-standard" and row.get("inputs", {}).get("InpUseMarkovRegimeFilter") == "false":
        return "standard"
    return None


def current_ftmo_preset() -> dict[str, Any] | None:
    """Current roster/settings selector; not a precomputed or validated forecast."""
    if not FTMO_PACKAGE.is_file():
        return None
    package = json.loads(FTMO_PACKAGE.read_text(encoding="utf-8"))
    entries = package.get("entries", [])
    balance = float(package.get("reference_balance") or 10_000)
    risk = float(package.get("risk_usd") or 50)
    return {
        "id": "ftmo-current", "label": f"Current FTMO profile · {len(entries)} EAs",
        "package_version": package.get("version"), "programme_id": "ftmo-2step-swing",
        "account_size": int(balance), "sizing": "fixed_usd", "period": "1y",
        "eas": [{"slug": e["slug"], "risk_pct": risk / balance * 100, "risk_usd": risk} for e in entries],
        "guards": {"max_open_risk_pct": 2.25, "max_entries_per_day": 7},
        "note": f"Synced from PACKAGE.json ({package.get('version', '')}); ${risk:g} per trade, news off. "
                "Loads the current selection only, NOT previously validated pass/payout numbers. "
                "Standalone cached settings, UTC resets and simulator controls do not exactly reproduce "
                "the native guard (including its three-loss stop, margin and same-symbol checks). "
                "Hourly no-SL EAs remain optional experiments, NOT in this guarded profile.",
    }


def ftmo13_presets() -> list[dict[str, Any]]:
    """The saved FTMO 13-EA package, as installed and with the tested (not installed) -2% / +4% daily controls."""
    if not FTMO_PACKAGE.is_file():
        return []
    package = json.loads(FTMO_PACKAGE.read_text(encoding="utf-8"))
    if package.get('gold_target_release'):
        # Fixed-$50 guarded fills and new targets have not been rerun together.
        # Generic cache re-sizing must not masquerade as the installed FTMO package.
        return []
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
    if (PACKAGE_ROOT / 'Gold Targets Deployment 2026-10-02/SELECTION.json').is_file():
        return None  # Earlier frozen combinations used the old Gold target ledgers.
    if not SUGGESTIONS.is_file():
        return None
    return dict(json.loads(SUGGESTIONS.read_text(encoding="utf-8")))


@lru_cache(maxsize=4)
def _catalog(stamp: str) -> str:
    rows, profiles = [], {}
    current = current_ftmo_preset()
    members = {e["slug"] for e in current["eas"]} if current else set()
    for product in get_website_catalog():
        loaded = {period: value for period in ("3y", "1y", "6m", "5y")
                  if (value := load_ea(product.slug, period, ftmo_mode(product.slug))) is not None and value[1]}
        profile = next((value[0] for value in loaded.values()), None)
        row = profile.public() if profile else {
            "slug": product.slug, "label": product.label, "symbol": product.canonical,
            "timeframe": product.timeframe, "trades": 0, "period": None,
            "risk_basis": "unavailable", "risk_note": "No cached ledger with usable sizing evidence.",
        }
        row.update(supported_periods=list(loaded), period_trade_counts={p: v[0].trades for p, v in loaded.items()},
                   ftmo_profile_member=product.slug in members)
        rows.append(row)
        profiles[product.slug] = profile
    progs = programmes()
    matrix = {
        pid: {slug: ({"status": (v := compatibility(prog, p)).status, "reasons": list(v.reasons)} if p else
                     {"status": "blocked", "reasons": ["No cached ledger with usable sizing evidence; listed for catalogue sync only."]})
              for slug, p in profiles.items()}
        for pid, prog in progs.items()
    }
    return json.dumps({
        "programmes": [p.public() for p in progs.values()],
        "eas": rows,
        "compatibility": matrix,
        "presets": ([current] if current else []) + ftmo13_presets(),
        "default_preset_id": "ftmo-current" if current else None,
        "catalog_count": len(rows),
    })


def _data_stamp() -> str:
    """Invalidate catalogue and run caches when package/roster/evidence files change."""
    import hashlib
    from ..evidence_cache import CACHE_ROOT
    inputs = [FTMO_PACKAGE, PACKAGE_ROOT / "_Auto Deploy/Install-BMTradingPortfolio.ps1",
              PACKAGE_ROOT / "Hourly Profiles Deployment 2026-10-04/RELEASE.json"]
    inputs += list((CACHE_ROOT / "products").glob("*/*/*.json"))
    inputs += list(RULES_ROOT.glob("*.json"))
    fingerprints = "|".join(f"{p}:{p.stat().st_mtime_ns}:{p.stat().st_size}" for p in inputs if p.is_file())
    return hashlib.sha256(fingerprints.encode()).hexdigest()


def catalog_payload() -> dict[str, Any]:
    # Refresh hourly, and immediately when package/evidence or firm logos change.
    logos = max((p.stat().st_mtime for p in LOGO_ROOT.glob("*")), default=0.0) if LOGO_ROOT.is_dir() else 0.0
    stamp = f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H')}|{logos}|{_data_stamp()}"
    payload = json.loads(_catalog(stamp))
    payload["suggestions"] = load_suggestions()
    return payload
