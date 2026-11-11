"""Research listings added 2026-11-10 (owner: "add the new EAs to the website"): Overnight Bias ORB, Vault Break (US100, video ideas) and Gold Band Wave (XAUUSD).
Website only: not sellable, not an installer item and not a website portfolio member. Figures come only from the bound evidence cache written by
BM Trading Robust Sets 2026-08-04/Merge 1Step 60d Search 2026-11-10/build_web.py (standalone native MT5 runs); a missing cache period is never invented."""
from __future__ import annotations

from .catalog import Evidence, LogicStep, PACKAGE_ROOT, Product, STORE_ROOT

PERIODS = ("6m", "1y", "3y", "5y")
NOTE = "Research only. Raw rules, not optimised; the raw test used 2019-2023 as development and the rest as out-of-sample. Not for sale."
EAS = {
    "overnight-bias-orb": dict(
        label="Overnight Bias ORB", canonical="USTEC", timeframe="M15", period=15, category="Indices", asset_group="indices", accent="blue",
        strategy="Opening-range breakout with an overnight bias",
        tagline="Trades the 09:30 New York range break only in the direction the overnight range points to.",
        description=("Overnight Bias ORB measures the overnight range (00:00-09:30 New York). If the 09:30 open is in its top third the day is long-only, in its bottom third "
                     "short-only, in the middle third no trade. The first M15 close beyond the 09:30-09:45 range in the bias direction enters, when ADX(14) is above 20. "
                     "Raw rules from a recorded interview, tested on Exness USTEC 2019-07 to 2026-11 (all years +117.5R, PF 1.35, equity DD 10.7%)."),
        session="New York 10:00-15:15 entries, flat 15:30", exit_mode="Stop 0.3 x 15-day average daily range, target 3x the stop, flat 15:30 NY",
        logic=[("Overnight range", "High and low of 00:00-09:30 New York on M15 bars."),
               ("Bias", "09:30 open in the top third: long only; bottom third: short only; middle: no trade that day."),
               ("Entry", "First M15 close above / below the 09:30-09:45 bar in the bias direction, ADX(14) > 20, until 15:15. One trade a day."),
               ("Exit", "Stop 0.3 x the 15-day average true daily range, target 3x that distance, close everything at 15:30 New York.")],
        source="Video ORB VWAP Ideas Raw 2026-11-09/EA/Video Ideas Raw EA.ex5", set_source="Video ORB VWAP Ideas Raw 2026-11-09/PLAN.md (InpStrategy 4)"),
    "vault-break": dict(
        label="Vault Break", canonical="USTEC", timeframe="M30", period=30, category="Indices", asset_group="indices", accent="blue",
        strategy="Session barrier breakout, long only",
        tagline="High win-rate US100 longs above a barrier set from the 01:00 New York open and above VWAP.",
        description=("Vault Break takes the M30 open at 01:00 New York (midnight Central Time) and sets a barrier 30% of the 15-session ATR above it. "
                     "An M30 close above both the barrier and the session VWAP between 11:00 and 15:00 buys, up to three trades a day, one at a time. "
                     "Target 40 points, stop 75 points, flat at 15:30. Raw rules from a recorded interview; the owner approved it for its high win rate although it "
                     "failed the raw gate (all years PF 1.06; Monte Carlo check failed)."),
        session="New York 11:00-15:00 entries, flat 15:30", exit_mode="Target 40 points, stop 75 points, flat 15:30 NY",
        logic=[("Barrier", "M30 open at 01:00 New York + 30% of the 15-session ATR; VWAP anchored at 01:00."),
               ("Entry", "M30 close above the barrier and the VWAP on a bar closing 11:00-15:00; buy at the next open. Up to 3 trades a day, one at a time."),
               ("Exit", "Target 40 points, stop 75 points, close everything at 15:30 New York.")],
        source="Video ORB VWAP Ideas Raw 2026-11-09/EA/Video Ideas Raw EA.ex5", set_source="Video ORB VWAP Ideas Raw 2026-11-09/PLAN.md (InpStrategy 2)"),
    "gold-band-wave": dict(
        label="Gold Band Wave", canonical="XAUUSD", timeframe="H4", period=240, category="Gold", asset_group="metals", accent="gold",
        strategy="Bollinger-band trend wave",
        tagline="Follows gold trends when the BBTrend wave crosses its signal line in the direction of the SMA200.",
        description=("BBTrend compares the distance between two Bollinger bands (20 and 50 bars, 2 deviations). A cross of BBTrend over its SMA9 signal opens a trade "
                     "when the close is on the same side of the SMA200; the opposite cross exits and can reverse. Stop 2 x ATR(14), no fixed target. "
                     "Raw rules from a pasted clip; all years +44.3R, PF 1.22, equity DD 19.3%; development 2019-23 flat, gains in 2024-26."),
        session="All day, H4 bars", exit_mode="Stop 2 x ATR(14); exit / reverse on the opposite cross; no target",
        logic=[("Wave", "BBTrend = (|lower20 - lower50| - |upper20 - upper50|) / middle20 x 100 on H4."),
               ("Signal", "SMA(9) of BBTrend. A cross up is a buy signal, a cross down a sell signal."),
               ("Trend filter", "Buy only above the SMA200, sell only below it."),
               ("Exit", "Stop 2 x ATR(14); close (and possibly reverse) on the opposite cross.")],
        source="Gold Band Wave Raw 2026-11-10/EA/Gold Band Wave Raw EA.ex5", set_source="Gold Band Wave Raw 2026-11-10/PLAN.md"),
}


def website_products() -> list[Product]:
    from .evidence_cache import load_product_summary
    out = []
    for slug, m in EAS.items():
        periods = tuple(p for p in PERIODS if (STORE_ROOT / "data/evidence-cache/v1/products" / slug / "standard" / f"{p}.json").is_file())
        if "1y" not in periods:
            continue  # never invent performance if the bound cache is missing
        payload = load_product_summary(slug, "standard", "1y")
        if payload is None:
            continue
        s = payload["stats"]
        ev = Evidence(label=payload["evidence_label"], period=payload["period"], return_pct=s["return_pct"], profit_factor=s["profit_factor"], drawdown_pct=s["max_drawdown_pct"],
                      win_rate_pct=s["win_rate_pct"], trades=s["trades"], sharpe_ratio=s.get("sharpe_ratio"), max_win_streak=s.get("max_win_streak"), max_loss_streak=s.get("max_loss_streak"),
                      recovery_factor=s.get("recovery_factor"), history_quality=payload["history_quality"], source_note=payload["notice"], status="Research evidence", caution=NOTE)
        out.append(Product(
            label=m["label"], installer_label=m["label"], slug=slug, canonical=m["canonical"], timeframe=m["timeframe"], period_minutes=m["period"],
            expert=m["source"].split("/")[-1], expert_source=m["source"], set_source=m["set_source"], category=m["category"], asset_group=m["asset_group"],
            strategy=m["strategy"], tagline=m["tagline"], description=m["description"], session=m["session"], exit_mode=m["exit_mode"],
            deployment_session="Research listing (not in the website portfolios)", risk_note="Standalone $10,000 native MT5 tests at 1% risk per trade; lots round up to the broker step.",
            logic_audit="Source-code verified", logic_audit_note="Rules are the frozen raw research EA; see the study folder named in the source path.",
            logic=[LogicStep(title=t, detail=d) for t, d in m["logic"]],
            limitations=[NOTE, "Exness broker history; earlier ticks are generated (real ticks from 2026-01-01). Live spreads and fills can differ.",
                         "Each period is a separate $10,000 run, not a combined portfolio or a forecast."],
            price=0, accent=m["accent"], website_only=True, research_note=NOTE, supported_evidence_periods=periods,
            standard_mode_label="Raw research rules", evidence=ev, one_year_evidence=ev, one_year_return_pct=ev.return_pct))
    return out
