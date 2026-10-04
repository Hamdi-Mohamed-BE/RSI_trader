"""Recent-only website research previews, explicitly outside every active portfolio."""
from __future__ import annotations

import hashlib
from .catalog import Evidence, LogicStep, PACKAGE_ROOT, Product, STORE_ROOT

PERIODS = ("6m", "1y")
SOURCE = "native-mt5-hourly-profiles-20261003"
PROFILES = {
    "us30-hourly-profiles": ("US30", "US30", "BUY 02:00, 06:00; SELL 00:00, 15:00, 22:00"),
    "us100-hourly-profiles": ("US100", "USTEC", "BUY 02:00, 13:00, 20:00; SELL 14:00, 22:00"),
}
CAUTION = (
    "Research only: the hours were selected on the latest year, so neither recent window is an untouched holdout. "
    "These profiles failed the long-history validation gate. Zero-spread quotes occur frequently in the broker history; "
    "recorded-cost returns can overstate live performance. Fixed one CFD lot, no protective stop, and delayed/weekend "
    "exits are possible. Not included in the active BATs, shared portfolio, FTMO simulator or checkout."
)


def verified_cache(slug: str, mode: str, period: str, payload: dict | None) -> dict | None:
    """Fail closed if a recent web cache loses its source/ledger binding."""
    if slug not in PROFILES:
        return payload
    if mode != "standard" or period not in PERIODS or not payload:
        return None
    fp = payload.get("source_fingerprint", {})
    expected_start = "2025-10-03" if period == "1y" else "2026-04-03"
    if (payload.get("source") != SOURCE or payload.get("period_key") != period
        or payload.get("mode") != mode or fp.get("slug") != slug
        or payload.get("stats", {}).get("from") != expected_start
        or payload.get("end_exclusive") != "2026-10-03"
        or fp.get("expert_sha256") != "ec02943c4acd18d3832794414adebbf538f90a63ceb845b4c911532f11bd2592"
        or fp.get("source_sha256") != "4ad21890864fcaea74d43738c8545f2d3543a6c660017556b9114988a9c1ea53"):
        return None
    root = STORE_ROOT / "data/evidence-cache/v1"
    for path, key in (
        (root/"products"/slug/mode/f"{period}.trades.json", "cached_trades_sha256"),
        (root/"source-runs"/slug/mode/f"{period}.htm.gz", "archived_report_sha256"),
        (root/"source-runs"/slug/mode/f"{period}.deals.csv.gz", "archived_deals_sha256"),
    ):
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != fp.get(key):
            return None
    return payload


def website_products() -> list[Product]:
    from .evidence_cache import load_product_summary
    root = PACKAGE_ROOT / "Indices Hourly EA Pipeline 2026-10-03"
    products = []
    for slug, (asset, symbol, hours) in PROFILES.items():
        path = STORE_ROOT / "data/evidence-cache/v1/products" / slug / "standard/1y.json"
        if not path.is_file():
            continue  # Never invent performance if the bound cache is missing.
        payload = load_product_summary(slug, "standard", "1y")
        if payload is None:
            continue
        stats = payload["stats"]
        evidence = Evidence(
            label=payload["evidence_label"], period=payload["period"],
            return_pct=stats["return_pct"], profit_factor=stats["profit_factor"],
            drawdown_pct=stats["max_drawdown_pct"], win_rate_pct=stats["win_rate_pct"],
            trades=stats["trades"], sharpe_ratio=stats["sharpe_ratio"],
            max_win_streak=stats["max_win_streak"], max_loss_streak=stats["max_loss_streak"],
            recovery_factor=stats["recovery_factor"], history_quality=payload["history_quality"],
            source_note=payload["notice"], status="Research evidence", caution=CAUTION,
        )
        products.append(Product(
            label=f"{asset} Hourly Profiles", installer_label=f"Research only — {asset} Hourly Profiles",
            slug=slug, canonical=asset, timeframe="M1", period_minutes=1,
            expert="CalyxHourlyProfiles.ex5", expert_source=str(root/"CalyxHourlyProfiles.ex5"),
            set_source=str(root/f"{asset}.set"), category="Indices", asset_group="indices",
            strategy="New York hourly rotation", tagline="Selected New York buy/sell hours with a 60-minute timed exit. Research only; failed long-history validation.",
            description=f"One universal hourly EA, frozen {asset} profile. Broker test symbol: {symbol}. "
                        "Recent results are separate $10,000 native MT5 tests, not a combined portfolio or forecast.",
            session="Selected New York hours · Mon–Fri", exit_mode="60-minute timed exit; no SL / TP / trailing",
            deployment_session="Website research only — not installed",
            risk_note="Tests use one fixed CFD lot on $10,000, not 1% risk. No stop loss: loss is not capped. "
                      "Real-account use is disabled by default in the research build.",
            logic_audit="Source-code verified", logic_audit_note="Exact unchanged source, EX5 and SET fingerprints are retained with each native run. No live deployment is implied.",
            logic=[
                LogicStep(title="Frozen hour profile", detail=f"New York local time, with DST: {hours}. No hour re-selection for six months."),
                LogicStep(title="Scheduled entry", detail="First available tick in minute 00, Monday–Friday. Market order, one fixed CFD lot; one owned position at a time."),
                LogicStep(title="Timed exit", detail="Close after 60 minutes from the scheduled entry. Retry closed-market exits before allowing another entry. Actual delayed and weekend holds remain in the results."),
                LogicStep(title="Duplicate protection", detail="Consume the hour/day signal before placing an order. Persistent state prevents duplicate entry after manual closing or restarting. Owned position time restores the exit deadline."),
                LogicStep(title="Evidence boundaries", detail="Only 1-year and 6-month performance is published on this listing. All charts show closed balance; maximum drawdown separately includes floating equity."),
            ], limitations=[CAUTION, "One CFD lot is broker-specific, not one NQ/ES futures contract. A hedging account is required.",
                           "Recent windows overlap the selection period. No independent-broker or prospective validation is available."],
            price=0, accent="blue", website_only=True, supported_evidence_periods=PERIODS,
            standard_mode_label="Frozen hourly profile", evidence=evidence,
            one_year_evidence=evidence, one_year_return_pct=evidence.return_pct,
        ))
    return products
