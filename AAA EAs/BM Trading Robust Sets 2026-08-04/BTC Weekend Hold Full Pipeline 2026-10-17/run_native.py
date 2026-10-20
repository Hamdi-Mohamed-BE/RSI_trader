"""Serial isolated-native research checks; never production installation.

Raw screens precede selection. Confirmations require the persisted selection
freeze and do not change that selection, including after bad OOS results.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import native
import search

ROOT = Path(__file__).resolve().parent


def read(name):
    return native.read(ROOT / name)


def run_batch(stage, suffix=""):
    if suffix and suffix not in ("-v2", "-v3"):
        raise ValueError("Only explicit implementation-repair version suffixes allowed")
    cases = []
    if stage == "raw":
        for label, start in (("6m", "2024-04-17"), ("1y", "2023-10-17"), ("3y", "2021-10-17"), ("5y", "2019-10-17")):
            cases.append(("raw-preoos-" + label + "-m1", search.BASELINE, start, "2024-10-17", 1, "raw pre-OOS screen"))
    else:
        frozen, selection = read("FROZEN.json"), read("SELECTION.json")
        for name, expected in frozen["locked"]["files"].items():
            if native.sha(ROOT / name) != expected:
                raise RuntimeError("Frozen input changed: " + name)
        chosen = frozen["selected_config"]
        if search.config_id(chosen) != selection["selected_config_id"]:
            raise RuntimeError("Frozen selected candidate identity differs")
        for who, config in (("baseline", search.BASELINE), ("selected", chosen)):
            cases.append((who + "-oos-m1", config, "2024-10-17", "2026-10-17", 1, "OOS coarse/native parity"))
            for label, start in (("6m", "2026-04-17"), ("1y", "2025-10-17"), ("oos", "2024-10-17"), ("3y", "2023-10-17"), ("5y", "2021-10-17")):
                cases.append((who + "-" + label + "-m4", config, start, "2026-10-17", 4, "frozen diagnostic, no reselection"))
        cases += [("selected-older-validation-m4", chosen, "2023-10-17", "2024-10-17", 4, "older validation confirmation"),
                  ("selected-development-m4", chosen, "2018-01-01", "2023-10-17", 4, "development confirmation; tester-start shifts remain hard failures")]
    records = []
    progress_name = "NATIVE " + stage.upper() + suffix.upper().replace("-", " ") + " PROGRESS.json"
    for tag, config, start, end, model, scope in cases:
        tag += suffix
        print(json.dumps({"event": "begin", "tag": tag, "start": start, "end_exclusive": end, "model": model}), flush=True)
        path = ROOT / "native" / tag / "results.json"
        try:
            if path.exists():
                result = native.read(path)
                if result["candidate"] != config or result["start"] != start or result["end_exclusive"] != end or result["native"]["manifest"]["model"] != model:
                    raise RuntimeError("Existing case has different inputs")
                if result["native"]["manifest"]["build"]["source_sha256"] != native.sha(ROOT / "EA/BtcWeekend.mq5"):
                    raise RuntimeError("Existing native source hash differs")
            else:
                result = native.run_case(tag, config, start, end, model=model, delay_ms=150)
            record = {"tag": tag, "status": "RECORDED", "scope": scope, "start": start, "end_exclusive": end, "model": model,
                      "candidate": config, "metrics": result["metrics"], "audit": result.get("audit", result.get("audits")),
                      "statistics": result["statistics"], "native": result["native"], "results_path": str(path.relative_to(ROOT))}
        except Exception as error:
            record = {"tag": tag, "status": "FAILED_NOT_REPLACED", "scope": scope, "start": start,
                      "end_exclusive": end, "model": model, "error": type(error).__name__ + ": " + str(error)}
        records.append(record)
        native.save(ROOT / progress_name, {"updated_at_utc": datetime.now(timezone.utc).isoformat(), "cases": records, "stage": stage})
        if stage == "confirm" and record["status"] == "RECORDED" and model == 4 and ("-oos-" in tag or "-older-validation-" in tag or "-development-" in tag):
            from native_robustness import analyze_native_case
            diagnostics_path = ROOT / "NATIVE ROBUSTNESS.json"
            diagnostics = native.read(diagnostics_path) if diagnostics_path.exists() else {}
            try:
                diagnostics[tag] = analyze_native_case(ROOT, tag, paths=10000)
            except Exception as error:
                diagnostics[tag] = {"status": "AUDIT_FAILED_NOT_SUBSTITUTED", "error": type(error).__name__ + ": " + str(error)}
            native.save(diagnostics_path, diagnostics)
        print(json.dumps({"event": "end", "tag": tag, "status": record["status"], "metrics": record.get("metrics"), "error": record.get("error")}), flush=True)
    all_cases = []
    for path in sorted(ROOT.glob("NATIVE *PROGRESS.json")):
        all_cases += native.read(path)["cases"]
    native.save(ROOT / "NATIVE AUDIT.json", {"status": "COMPLETED_WITH_EXPLICIT_FAILURES" if any(x["status"] != "RECORDED" for x in all_cases) else "NATIVE_RUNS_RECORDED",
        "cases": all_cases, "promotion_passed": False, "no_live_changes": True,
        "basis": "Native costs/spreads under present tester specification, strict DOWN-rounded 1x current-equity notional. Not a reconstruction of historical financing.",
        "real_tick_scope": "Model4 is a requested mode, not proof every period has real ticks. Read each run's generated/real tick coverage notes and report history quality.",
        "promotion_note": "Retrospective OOS and incomplete historical cost/coverage gates are not waived by native replay."})
    return records


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["raw", "confirm"])
    parser.add_argument("--suffix", default="")
    args = parser.parse_args()
    print(json.dumps({"cases_finished": len(run_batch(args.stage, args.suffix))}))
