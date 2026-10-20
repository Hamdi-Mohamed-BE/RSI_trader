"""Reporting-only supplements after the immutable BTC research selection.

No optimisation, parameter selection, terminal calls, or production writes.
Missing intraday paths cannot invalidate known closed cash, but they do prevent
floating-equity/prop-account claims. Keep both evidence scopes visible.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import shutil

import cash_only_mc
import native
import run_pipeline

ROOT = Path(__file__).resolve().parent


def finalize():
    frozen = native.read(ROOT / "FROZEN.json")
    for name, expected in frozen["locked"]["files"].items():
        if native.sha(ROOT / name) != expected:
            raise RuntimeError("Frozen file changed: " + name)
    version = native.read(ROOT / "V2 FREEZE.json")
    for name, expected in version["locked_files"].items():
        if native.sha(ROOT / name) != expected:
            raise RuntimeError("Versioned implementation file changed: " + name)
    progress = native.read(ROOT / "NATIVE CONFIRM PROGRESS.json")
    if len(progress["cases"]) != 14:
        raise RuntimeError("Native batch is not finished; never publish a partial run as complete")
    repaired = native.read(ROOT / "NATIVE CONFIRM V2 PROGRESS.json")
    if len(repaired["cases"]) != 8:
        raise RuntimeError("Versioned candidate confirmation batch is not finished")
    supplements = {}
    for tag in ("baseline-oos-m4", "selected-oos-m4-v2", "selected-older-validation-m4-v2", "selected-5y-m4-v2", "selected-development-m4-v2"):
        if (ROOT / "native" / tag / "results.json").exists():
            supplements[tag] = cash_only_mc.analyze_cash_only(ROOT, tag, paths=10000)
        else:
            supplements[tag] = {"status": "UNAVAILABLE_NO_VALID_NATIVE_CASE", "no_substitution": True}
    original = native.read(ROOT / "NATIVE ROBUSTNESS.json") if (ROOT / "NATIVE ROBUSTNESS.json").exists() else {}
    original["closed_cash_only_supplement"] = {
        "method_scope": "Reporting-only supplement. Does not waive any price-history, floating-equity, historical-cost, older-validation, or promotion gate.",
        "receipt": {"created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_sha256": native.sha(ROOT / "cash_only_mc.py"), "finalizer_sha256": native.sha(ROOT / "finish.py"),
            "frozen_selection_sha256": native.sha(ROOT / "SELECTION.json"), "tested_unique_configurations": 345,
            "no_new_configuration_or_selection": True, "closed_balance_dd_only": True,
            "why_added": "Complete closed-position cash can be resampled without inventing absent M1 floating paths. Missing/unexplained cash weeks remain unavailable; conditional observed-week results are labelled."},
        "cases": supplements}
    native.save(ROOT / "NATIVE ROBUSTNESS.json", original)
    audit = native.read(ROOT / "NATIVE AUDIT.json")
    audit["cost_components"] = []
    for case in audit["cases"]:
        if case["status"] != "RECORDED":
            continue
        result = native.read(ROOT / case["results_path"])
        components = {key: sum(position[key] for position in result["trades"]) for key in ("gross_profit", "swap", "commission", "fee", "net_profit")}
        audit["cost_components"].append({"tag": case["tag"], **components,
            "basis": "Native executed volumes/cash path; constant present tester specification/account costs, not a historical fee-rate reconstruction"})
        case["independent_verification"] = result["verification"]
    audit["promotion_passed"] = False
    audit["versioned_implementation_receipt"] = native.read(ROOT / "V2 FREEZE.json")
    audit["full_development_confirmation"] = "Unavailable when native history shifts the 2018 requested start; no shorter result is silently substituted."
    native.save(ROOT / "NATIVE AUDIT.json", audit)
    sets = ROOT / "Sets"
    sets.mkdir(exist_ok=True)
    for who in ("baseline", "selected"):
        source = ROOT / "native" / (who + "-oos-m4" + ("-v2" if who == "selected" else "")) / "Parameters.set"
        if source.exists():
            shutil.copyfile(source, sets / (who + "-RESEARCH-TESTER-ONLY.set"))
    run_pipeline.final_report()
    final = native.read(ROOT / "FINAL.json")
    final["verdict"] = "Not promoted. No finalist passed older-validation requirements. The frozen exploratory candidate also lost money in two-year native costed replay; its positive gross result did not survive the present tester costs."
    final["native_oos_comparison"] = {"cases": [case for case in audit["cases"] if case["tag"] in ("baseline-oos-m4", "selected-oos-m4-v2")],
        "dates": "2024-10-17 to2026-10-17 exclusive; retrospective OOS",
        "capital_basis": "$10,000 initial, broker-volume DOWN-rounded one-times-current-equity notional; NOT 1% stop-risk sizing",
        "cost_scope": "Present tester account/contract costs, not historical financing reconstruction", "real_tick_coverage": "39% of this two-year Model4 replay; remainder generated fallback"}
    final["cautions"].append("The candidate's initial native test stopped before trades on a daily-bar iteration bug. A separately hash-frozen V2 repair preserved the original selection, parameters, source files and failed attempts; no OOS-based reselection occurred.")
    native.save(ROOT / "FINAL.json", final)
    from report import build_report
    build_report(ROOT)
    print(json.dumps({"status": "RESEARCH_REPORT_COMPLETE_NOT_PROMOTED", "report": str(ROOT / "Results.html"), "no_live_changes": True}))


if __name__ == "__main__":
    finalize()
