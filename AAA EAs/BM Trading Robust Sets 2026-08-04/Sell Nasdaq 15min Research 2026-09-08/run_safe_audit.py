from __future__ import annotations

import csv
import importlib.util
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PIPELINE_PATH = ROOT / "run_pipeline.py"


def load_pipeline():
    spec = importlib.util.spec_from_file_location("sell_nasdaq_pipeline", PIPELINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the Sell Nasdaq pipeline")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PIPELINE = load_pipeline()


def safe(config: dict[str, object]) -> dict[str, object]:
    result = deepcopy(config)
    result.update({
        "InpUseMarkovRegimeFilter": True,
        "InpMarkovReturnWindow": 40,
        "InpMarkovThreshold": 0.05,
        "InpMarkovSignalGate": 0.05,
        "InpMarkovMinLabels": 252,
        "InpMarkovHistoryBars": 2600,
    })
    return result


def compact(row: dict) -> dict:
    return {
        key: row[key]
        for key in (
            "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct",
            "trades", "sharpe", "recovery_factor", "history_quality",
        )
    }


def table_line(label: str, row: dict) -> str:
    return (
        f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
        f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | "
        f"{row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
    )


def main() -> None:
    PIPELINE.prepare()
    audit_path = ROOT / "FINAL AUDIT.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    raw_london = PIPELINE.base_config(require_london=True)
    selected = {**PIPELINE.base_config(require_london=False), **audit["selected_config"]}

    # Keep reruns idempotent: the comparison reports may already be cached from a
    # prior audit, so rebuild the baseline count from the original pipeline only.
    sequence = sum(
        1
        for path in PIPELINE.REPORTS.rglob("*.htm")
        if not any(part in {"standard-full", "safe-locked", "safe-full"} for part in path.parts)
    )
    sequence += 1
    raw_london_standard_full = PIPELINE.run_case("standard-full", "raw-london-standard", raw_london, "2023.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    raw_london_safe_locked = PIPELINE.run_case("safe-locked", "raw-london-safe", safe(raw_london), "2025.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    raw_london_safe_full = PIPELINE.run_case("safe-full", "raw-london-safe", safe(raw_london), "2023.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    selected_safe_locked = PIPELINE.run_case("safe-locked", "pipeline-selected-safe", safe(selected), "2025.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    selected_safe_full = PIPELINE.run_case("safe-full", "pipeline-selected-safe", safe(selected), "2023.09.01", "2026.09.01", 0, sequence)

    standard_locked_report = Path(audit["final"]["raw_london"]["path"])
    standard_locked = {
        **audit["final"]["raw_london"],
        **PIPELINE.ANALYZER.parse_report(standard_locked_report),
    }
    standard_mc = PIPELINE.ANALYZER.monte_carlo(
        PIPELINE.ANALYZER.trade_outcomes(standard_locked["deals"]),
        standard_locked["initial_balance"],
        10_000,
    )
    raw_safe_mc = PIPELINE.ANALYZER.monte_carlo(
        PIPELINE.ANALYZER.trade_outcomes(raw_london_safe_locked["deals"]),
        raw_london_safe_locked["initial_balance"],
        10_000,
    )
    selected_safe_mc = PIPELINE.ANALYZER.monte_carlo(
        PIPELINE.ANALYZER.trade_outcomes(selected_safe_locked["deals"]),
        selected_safe_locked["initial_balance"],
        10_000,
    )

    safe_rows = [raw_london_safe_locked, selected_safe_locked]
    qualified_safe = [
        row for row in safe_rows
        if row["return_pct"] > 0 and row["profit_factor"] >= 1.30 and row["trades"] >= 30
    ]
    best_safe = max(qualified_safe or safe_rows, key=PIPELINE.selection_score)
    best_safe_name = "raw-london-safe" if best_safe["variant"] == "raw-london-safe" else "pipeline-selected-safe"
    best_safe_mc = raw_safe_mc if best_safe_name == "raw-london-safe" else selected_safe_mc

    standard_pass = (
        standard_locked["return_pct"] > 0
        and standard_locked["profit_factor"] >= 1.30
        and standard_locked["trades"] >= 30
        and standard_mc["return_p5_pct"] > 0
    )
    safe_pass = (
        best_safe["return_pct"] > 0
        and best_safe["profit_factor"] >= 1.30
        and best_safe["trades"] >= 30
        and best_safe_mc["return_p5_pct"] > 0
    )
    if standard_pass:
        decision = "PASS FOR ISOLATED DEMO FORWARD TESTING — the raw London-confirmed version is the Best Recommended research candidate."
    else:
        decision = "WATCH ONLY — the raw London-confirmed version is best, but it does not clear the full locked-year and Monte-Carlo promotion gate."
    if safe_pass:
        safe_decision = "KEEP SAFE PRESET FOR ISOLATED DEMO TESTING."
    else:
        safe_decision = "DO NOT PROMOTE SAFE MODE — it did not clear the independent promotion gate."

    standard_set = ROOT / "Sets" / "Sell Nasdaq 15min - best research Standard - 1pct.set"
    standard_set.write_text(PIPELINE.set_text(raw_london, 980908998), encoding="utf-8")
    best_safe_config = safe(raw_london if best_safe_name == "raw-london-safe" else selected)
    safe_set = ROOT / "Sets" / "Sell Nasdaq 15min - best research Full Safe - 1pct.set"
    if safe_pass:
        safe_set.write_text(PIPELINE.set_text(best_safe_config, 980908997), encoding="utf-8")
        published_safe_set = str(safe_set)
    else:
        safe_set.unlink(missing_ok=True)
        published_safe_set = None

    audit["best_research_version"] = "raw 600/1000 with bearish 09:15-09:30 London confirmation"
    audit["safe_audit"] = {
        "gate": "independent completed-D1 Markov direction veto, 40-bar return / 5% threshold / 0.05 signal",
        "raw_london_safe_locked": PIPELINE.clean(raw_london_safe_locked),
        "raw_london_safe_full": PIPELINE.clean(raw_london_safe_full),
        "raw_london_standard_full": PIPELINE.clean(raw_london_standard_full),
        "pipeline_selected_safe_locked": PIPELINE.clean(selected_safe_locked),
        "pipeline_selected_safe_full": PIPELINE.clean(selected_safe_full),
        "standard_raw_london_monte_carlo": standard_mc,
        "raw_london_safe_monte_carlo": raw_safe_mc,
        "pipeline_selected_safe_monte_carlo": selected_safe_mc,
        "best_safe_version": best_safe_name,
        "decision": safe_decision,
        "safe_set": published_safe_set,
    }
    audit["decision"] = decision
    audit["standard_set"] = str(standard_set)
    audit["native_mt5_cases"] = sequence
    audit_path.write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")

    rows = [
        {"version": "raw-no-london-locked", **compact(audit["final"]["raw_no_london"])},
        {"version": "raw-with-london-locked", **compact(audit["final"]["raw_london"])},
        {"version": "raw-with-london-full", **compact(raw_london_standard_full)},
        {"version": "pipeline-selected-locked", **compact(audit["final"]["selected_locked"])},
        {"version": "pipeline-selected-full", **compact(audit["final"]["selected_full"])},
        {"version": "raw-with-london-safe-locked", **compact(raw_london_safe_locked)},
        {"version": "raw-with-london-safe-full", **compact(raw_london_safe_full)},
        {"version": "pipeline-selected-safe-locked", **compact(selected_safe_locked)},
        {"version": "pipeline-selected-safe-full", **compact(selected_safe_full)},
    ]
    with (ROOT / "FINAL AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    report_path = ROOT / "FINAL REPORT.md"
    report = report_path.read_text(encoding="utf-8").split("\n## Safe-mode audit\n", 1)[0].rstrip()
    report += "\n\n## Safe-mode audit\n\n"
    report += "The Safe version uses the same completed-D1, no-lookahead Markov direction veto already used by the Calyx Full Safe system. It does not change the 1% research risk.\n\n"
    report += "| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |\n"
    report += "|---|---:|---:|---:|---:|---:|---:|---:|\n"
    report += table_line("Raw London Standard — locked", audit["final"]["raw_london"]) + "\n"
    report += table_line("Raw London Standard — full 3y", raw_london_standard_full) + "\n"
    report += table_line("Raw London Full Safe — locked", raw_london_safe_locked) + "\n"
    report += table_line("Pipeline-selected Full Safe — locked", selected_safe_locked) + "\n"
    report += table_line("Raw London Full Safe — full 3y", raw_london_safe_full) + "\n"
    report += table_line("Pipeline-selected Full Safe — full 3y", selected_safe_full) + "\n\n"
    report += f"- Standard raw-London Monte Carlo return P5: {standard_mc['return_p5_pct']:+.2f}%\n"
    report += f"- Best Safe Monte Carlo return P5: {best_safe_mc['return_p5_pct']:+.2f}%\n"
    report += f"- Safe decision: **{safe_decision}**\n"
    report += f"- Overall decision: **{decision}**\n"
    report += "- Active portfolio, recommended BAT and website remain unchanged pending user review.\n"
    report_path.write_text(report, encoding="utf-8")

    print(json.dumps({
        "decision": decision,
        "safe_decision": safe_decision,
        "standard_locked": compact(standard_locked),
        "standard_full": compact(raw_london_standard_full),
        "standard_mc_p5": standard_mc["return_p5_pct"],
        "raw_london_safe_locked": compact(raw_london_safe_locked),
        "raw_london_safe_mc_p5": raw_safe_mc["return_p5_pct"],
        "pipeline_selected_safe_locked": compact(selected_safe_locked),
        "pipeline_selected_safe_mc_p5": selected_safe_mc["return_p5_pct"],
        "cases": sequence,
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
