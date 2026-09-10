from __future__ import annotations

import csv
import importlib.util
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PIPELINE_PATH = ROOT / "run_pipeline.py"


def load_pipeline():
    spec = importlib.util.spec_from_file_location("squeeze_pipeline", PIPELINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load squeeze pipeline")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


P = load_pipeline()


def position_metrics(row: dict) -> dict:
    """Aggregate partial deals back into one position-level observation."""
    outcomes: list[float] = []
    current: float | None = None
    for deal in row.get("deals", []):
        entry = deal.get("entry")
        cash = float(deal.get("cashflow", 0.0))
        if entry == "in":
            if current is not None:
                outcomes.append(current)
            current = cash
        elif entry in {"out", "out by"} and current is not None:
            current += cash
    if current is not None:
        outcomes.append(current)
    wins = [value for value in outcomes if value > 0.0]
    losses = [value for value in outcomes if value < 0.0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    return {
        "position_trades": len(outcomes),
        "position_win_rate_pct": len(wins) / len(outcomes) * 100.0 if outcomes else 0.0,
        "position_profit_factor": gross_profit / gross_loss if gross_loss else (99.0 if gross_profit else 0.0),
        "position_outcomes": outcomes,
    }


def enrich(row: dict) -> dict:
    row.update(position_metrics(row))
    return row


def clean(row: dict) -> dict:
    return {key: value for key, value in row.items() if key not in {"deals", "position_outcomes"}}


def config_overall(risk: float = 1.0) -> dict:
    return {
        **P.base_config(),
        "InpRiskPercent": risk,
        "InpSqueezeLength": 24,
        "InpBollingerMultiplier": 1.8,
        "InpKeltnerMultiplier": 1.3,
        "InpMomentumLength": 28,
        "InpTrendSMAPeriod": 200,
        "InpATRPeriod": 14,
        "InpATRMethod": 0,
        "InpStopATR": 3.5,
        "InpTargetR": 1.5,
        "InpTrailingMode": 1,
        "InpTrailATR": 3.5,
        "InpMomentumExitMode": 2,
        "InpMomentumFadeFraction": 0.5,
        "InpSessionStartHourUTC": 0,
        "InpSessionEndHourUTC": 24,
        "InpWeekdayMask": 62,
    }


def config_partial(risk: float = 1.0) -> dict:
    return {
        **config_overall(risk),
        "InpTrailATR": 3.0,
        "InpPartialExitAtR": 2.0,
        "InpPartialExitFraction": 0.5,
    }


def config_short_target(risk: float = 1.0) -> dict:
    return {
        **config_overall(risk),
        "InpStopATR": 3.0,
        "InpTargetR": 0.5,
        "InpTrailATR": 3.0,
    }


def make_chart(rows: list[dict], destination: Path) -> None:
    import matplotlib.pyplot as plt

    selected = [row for row in rows if row["phase"] in {"candidate-locked", "candidate-3y"}]
    labels = [f"{row['label']}\n{row['phase'].replace('candidate-', '')}" for row in selected]
    returns = [row["return_pct"] for row in selected]
    colors = ["#2f80ed" if "overall" in row["label"] else "#63e6be" for row in selected]
    fig, axes = plt.subplots(2, 1, figsize=(14, 11), constrained_layout=True)
    axes[0].barh(range(len(selected)), returns, color=colors)
    axes[0].set_yticks(range(len(selected)), labels)
    axes[0].invert_yaxis()
    axes[0].axvline(0, color="#333", linewidth=0.8)
    axes[0].set_xlabel("Net return (%)")
    axes[0].set_title("XAU squeeze candidates — native MT5 evidence")
    for index, row in enumerate(selected):
        axes[0].text(
            returns[index], index,
            f" {row['return_pct']:+.2f}% | PF {row['profit_factor']:.2f} | "
            f"WR {row['position_win_rate_pct']:.1f}% | DD {row['max_drawdown_pct']:.2f}% | "
            f"positions {row['position_trades']}",
            va="center", fontsize=8,
        )
    for row in selected:
        if row["phase"] != "candidate-3y":
            continue
        equity = [100.0]
        for pnl in row["position_outcomes"]:
            equity.append(equity[-1] + pnl / 100.0)
        axes[1].plot(equity, label=row["label"], linewidth=1.5)
    axes[1].set_title("Three-year position-level equity paths (start = 100)")
    axes[1].set_xlabel("Closed positions")
    axes[1].set_ylabel("Equity index")
    axes[1].grid(alpha=0.2)
    axes[1].legend()
    fig.savefig(destination, dpi=170, facecolor="white")
    plt.close(fig)


def main() -> None:
    P.prepare()
    sequence = 2000
    rows: list[dict] = []

    def run(asset, phase, label, config, window, model=0, execution=0):
        nonlocal sequence
        sequence += 1
        row = enrich(P.run_case(asset, phase, label, config, window, sequence, model, execution))
        rows.append(row)
        return row

    # Literal reconstruction, kept separate because its 5% risk is deliberately aggressive.
    raw = P.raw_config(5.0)
    raw_3y = run("XAU", "raw-final", "literal-5pct-3y", raw, P.THREE_YEAR, 0)
    raw_locked = run("XAU", "raw-final", "literal-5pct-locked-real", raw, P.LOCKED, 4)
    raw_5y = run("XAU", "raw-final", "literal-5pct-5y", raw, P.FIVE_YEAR, 0)

    # Broad, explainable candidate chosen from the stable development plateau.
    structure = config_overall(1.0)
    overall_dev = run("XAU", "candidate-development", "overall-1pct", structure, P.DEVELOPMENT, 0)
    overall_validation = run("XAU", "candidate-validation", "overall-1pct", structure, P.VALIDATION, 0)
    overall_locked_1 = run("XAU", "candidate-locked", "overall-1pct-real", structure, P.LOCKED, 4)
    overall_3y_1 = run("XAU", "candidate-3y", "overall-1pct", structure, P.THREE_YEAR, 0)

    risk_rows = [
        run("XAU", "risk-final", f"overall-risk-{risk}", config_overall(risk), P.THREE_YEAR, 1)
        for risk in (0.25, 0.5, 0.75, 1.0, 1.25)
    ]
    eligible_risk = [
        row for row in risk_rows
        if row["return_pct"] > 0.0 and row["max_drawdown_pct"] <= 8.0 and row["profit_factor"] > 1.0
    ]
    selected_risk = max((float(row["config"]["InpRiskPercent"]) for row in eligible_risk), default=0.5)
    recommended = config_overall(selected_risk)
    overall_locked = run("XAU", "recommended-locked", f"overall-{selected_risk}pct-real", recommended, P.LOCKED, 4)
    overall_3y = run("XAU", "recommended-3y", f"overall-{selected_risk}pct", recommended, P.THREE_YEAR, 0)
    overall_5y = run("XAU", "recommended-5y", f"overall-{selected_risk}pct", recommended, P.FIVE_YEAR, 0)
    random_delay = run("XAU", "recommended-stress", "overall-random-delay", recommended, P.THREE_YEAR, 0, -1)
    fixed_delay = run("XAU", "recommended-stress", "overall-500ms", recommended, P.THREE_YEAR, 0, 500)
    safe = {**recommended, "InpUseMarkovRegimeFilter": True}
    safe_3y = run("XAU", "recommended-safe", "overall-markov-3y", safe, P.THREE_YEAR, 0)
    safe_locked = run("XAU", "recommended-safe", "overall-markov-locked-real", safe, P.LOCKED, 4)
    xag_3y = run("XAG", "cross-market-final", "xau-overall-frozen-3y", recommended, P.THREE_YEAR, 0)
    xag_locked = run("XAG", "cross-market-final", "xau-overall-frozen-locked-real", recommended, P.LOCKED, 4)

    # Two honest high-win-rate routes: partial management and a short fixed target.
    high_candidates = []
    for family, factory in (("partial-2r", config_partial), ("target-0p5r", config_short_target)):
        cfg = factory(1.0)
        dev = run("XAU", "highwr-development", family, cfg, P.DEVELOPMENT, 0)
        validation = run("XAU", "highwr-validation", family, cfg, P.VALIDATION, 0)
        locked = run("XAU", "highwr-locked", family, cfg, P.LOCKED, 4)
        three_year = run("XAU", "highwr-3y", family, cfg, P.THREE_YEAR, 0)
        high_candidates.append({
            "family": family, "factory": factory, "config": cfg, "development": dev,
            "validation": validation, "locked": locked, "three_year": three_year,
        })
    safe_development = run("XAU", "highwr-development", "markov-safe", safe, P.DEVELOPMENT, 0)
    safe_validation = run("XAU", "highwr-validation", "markov-safe", safe, P.VALIDATION, 0)
    high_candidates.append({
        "family": "markov-safe", "factory": None, "config": safe,
        "development": safe_development, "validation": safe_validation,
        "locked": safe_locked, "three_year": safe_3y,
    })
    defensible = [
        item for item in high_candidates
        if item["validation"]["return_pct"] > 0.0
        and item["locked"]["return_pct"] > 0.0
        and item["validation"]["position_profit_factor"] > 1.0
        and item["locked"]["position_profit_factor"] > 1.0
        and item["locked"]["position_trades"] >= 10
    ]
    high_pick = max(
        defensible or high_candidates,
        key=lambda item: (
            min(item["validation"]["position_win_rate_pct"], item["locked"]["position_win_rate_pct"]),
            item["locked"]["position_profit_factor"],
        ),
    )
    high_cfg = deepcopy(high_pick["config"])
    high_5y = run("XAU", "highwr-final", f"{high_pick['family']}-5y", high_cfg, P.FIVE_YEAR, 0)
    high_random = run("XAU", "highwr-stress", f"{high_pick['family']}-random", high_cfg, P.THREE_YEAR, 0, -1)
    high_fixed = run("XAU", "highwr-stress", f"{high_pick['family']}-500ms", high_cfg, P.THREE_YEAR, 0, 500)

    tested = len({P.config_signature(row["config"]) for row in rows}) + 126
    audit_xau = P.run_enhanced(overall_locked, "XAU Squeeze Momentum — recommended locked",
                               ROOT / "Enhanced Audit" / "Recommended", tested)
    audit_high = P.run_enhanced(high_pick["locked"], "XAU Squeeze Momentum — high WR locked",
                                ROOT / "Enhanced Audit" / "High WR", tested)
    audit_xag = P.run_enhanced(xag_locked, "XAU Squeeze Momentum — XAG frozen locked",
                               ROOT / "Enhanced Audit" / "XAG", tested)
    monte_carlo = {
        "recommended_3y": P.monte_carlo(overall_3y),
        "recommended_locked": P.monte_carlo(overall_locked),
        "high_wr_3y": P.monte_carlo(high_pick["three_year"]),
        "xag_3y": P.monte_carlo(xag_3y),
    }

    fields = [
        "asset", "symbol", "phase", "label", "return_pct", "profit_factor", "win_rate_pct",
        "position_profit_factor", "position_win_rate_pct", "position_trades", "max_drawdown_pct",
        "trades", "sharpe", "recovery_factor", "history_quality", "path",
    ]
    with (ROOT / "final-candidate-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(clean(row) for row in rows)

    payload = {
        "date_windows": {
            "development": P.DEVELOPMENT, "purged_validation": P.VALIDATION,
            "locked": P.LOCKED, "three_year": P.THREE_YEAR, "five_year": P.FIVE_YEAR,
        },
        "raw": {"three_year": clean(raw_3y), "locked": clean(raw_locked), "five_year": clean(raw_5y)},
        "overall_1pct_screen": {
            "development": clean(overall_dev), "validation": clean(overall_validation),
            "locked": clean(overall_locked_1), "three_year": clean(overall_3y_1),
        },
        "recommended": {
            "risk_percent": selected_risk, "config": recommended,
            "locked": clean(overall_locked), "three_year": clean(overall_3y), "five_year": clean(overall_5y),
            "random_delay": clean(random_delay), "fixed_500ms": clean(fixed_delay),
        },
        "safe": {"three_year": clean(safe_3y), "locked": clean(safe_locked)},
        "xag_frozen": {"three_year": clean(xag_3y), "locked": clean(xag_locked)},
        "high_win_rate_candidates": [
            {key: clean(value) if isinstance(value, dict) and "return_pct" in value else value
             for key, value in item.items() if key != "factory"}
            for item in high_candidates
        ],
        "high_win_rate_pick": {
            "family": high_pick["family"], "risk_percent": float(high_cfg["InpRiskPercent"]),
            "development": clean(high_pick["development"]), "validation": clean(high_pick["validation"]),
            "locked": clean(high_pick["locked"]), "three_year": clean(high_pick["three_year"]),
            "five_year": clean(high_5y), "random_delay": clean(high_random), "fixed_500ms": clean(high_fixed),
        },
        "risk_sweep": [clean(row) for row in risk_rows],
        "monte_carlo": monte_carlo,
        "enhanced_audit": {"recommended": audit_xau, "high_win_rate": audit_high, "xag": audit_xag},
        "tested_configurations_including_development_grid": tested,
    }
    (ROOT / "final-candidate-results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    make_chart(rows, ROOT / "xau-squeeze-final-comparison.png")

    def metric(name: str, row: dict) -> str:
        return (
            f"| {name} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['position_win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | "
            f"{row['position_trades']} | {row['sharpe']:.2f} | {row['history_quality']} |"
        )

    report = [
        "# XAU Squeeze Momentum — final full-pipeline candidates", "",
        "Research only. No website, BAT installer, active profile, or live account was changed.", "",
        "Position-level win rate and trade count are used below. This prevents partial exits from inflating MT5's deal-level figures.", "",
        "| Version / period | Return | PF | Position win rate | Max equity DD | Positions | Sharpe | Quality |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        metric("Literal raw 5% — 3Y", raw_3y),
        metric("Literal raw 5% — locked real ticks", raw_locked),
        metric(f"Recommended {selected_risk}% — 3Y", overall_3y),
        metric(f"Recommended {selected_risk}% — locked real ticks", overall_locked),
        metric("Recommended — random delay", random_delay),
        metric("Recommended — 500 ms", fixed_delay),
        metric("Markov safe — 3Y", safe_3y),
        metric("Markov safe — locked real ticks", safe_locked),
        metric(f"High-WR {high_pick['family']} — 3Y", high_pick["three_year"]),
        metric(f"High-WR {high_pick['family']} — locked real ticks", high_pick["locked"]),
        metric("XAG frozen — 3Y", xag_3y),
        metric("XAG frozen — locked real ticks", xag_locked), "",
        "## Chronological gate", "",
        metric("Recommended development", overall_dev),
        metric("Recommended purged validation", overall_validation),
        metric("Recommended locked real ticks", overall_locked), "",
        "## Selected configurations", "", "### Best overall", "", "```json",
        json.dumps(recommended, indent=2), "```", "", "### Highest defensible win rate", "", "```json",
        json.dumps(high_cfg, indent=2), "```", "",
        f"Enhanced verdicts: recommended **{audit_xau.get('verdict', 'UNKNOWN')}**, "
        f"high-WR **{audit_high.get('verdict', 'UNKNOWN')}**, XAG **{audit_xag.get('verdict', 'UNKNOWN')}**.", "",
        "No backtest can guarantee future profitability. A candidate is considered defensible only if it remains positive in both "
        "the purged validation year and locked real-tick year with position-level PF above 1.",
    ]
    (ROOT / "FINAL CANDIDATE REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(f"COMPLETE {ROOT / 'FINAL CANDIDATE REPORT.md'}", flush=True)


if __name__ == "__main__":
    main()
