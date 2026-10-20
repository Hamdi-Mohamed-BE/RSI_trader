"""Versioned daily-bar loader repair; fixed original selection, no reoptimisation."""
from datetime import datetime, timezone
from pathlib import Path
import json

import native_v2 as native
import native_robustness

ROOT = Path(__file__).resolve().parent


def freeze():
    path = ROOT / "V2 FREEZE.json"
    if path.exists():
        raise RuntimeError("Versioned implementation already frozen")
    original = native.read(ROOT / "FROZEN.json")
    for name, expected in original["locked"]["files"].items():
        if native.sha(ROOT / name) != expected:
            raise RuntimeError("Original frozen file differs: " + name)
    native.save(path, {"created_at_utc": datetime.now(timezone.utc).isoformat(), "research_only": True,
        "original_freeze_sha256": native.sha(ROOT / "FROZEN.json"),
        "selected_config": original["selected_config"], "no_reselection": True,
        "reason": "Implementation-only daily-bar loader repair after failed zero-trade native attempts; original files and failed cases retained.",
        "semantic_change": "Request next closed feature open from last_bar+feature_seconds, not last_bar+1 second. Eligible missing bars remain stale/missing; other history errors remain fatal.",
        "locked_files": {name: native.sha(ROOT / name) for name in ("native_v2.py", "EA/BtcWeekendV2.mq5", "run_native_v2.py")}})


def run():
    version = native.read(ROOT / "V2 FREEZE.json")
    if native.sha(ROOT / "FROZEN.json") != version["original_freeze_sha256"]:
        raise RuntimeError("Original selection freeze changed")
    original = native.read(ROOT / "FROZEN.json")
    for name, expected in original["locked"]["files"].items():
        if native.sha(ROOT / name) != expected:
            raise RuntimeError("Original frozen file differs: " + name)
    for name, expected in version["locked_files"].items():
        if native.sha(ROOT / name) != expected:
            raise RuntimeError("V2 frozen file differs: " + name)
    if version["selected_config"] != original["selected_config"]:
        raise RuntimeError("Parameter mutation rejected")
    config = original["selected_config"]
    cases = [("selected-oos-m1-v2", "2024-10-17", "2026-10-17", 1)]
    cases += [("selected-" + label + "-m4-v2", start, "2026-10-17", 4) for label, start in
              (("6m", "2026-04-17"), ("1y", "2025-10-17"), ("oos", "2024-10-17"), ("3y", "2023-10-17"), ("5y", "2021-10-17"))]
    cases += [("selected-older-validation-m4-v2", "2023-10-17", "2024-10-17", 4),
              ("selected-development-m4-v2", "2018-01-01", "2023-10-17", 4)]
    records = []
    for tag, start, end, model in cases:
        print(json.dumps({"event": "begin", "tag": tag, "start": start, "end_exclusive": end, "model": model}), flush=True)
        try:
            result = native.run_case(tag, config, start, end, model=model, delay_ms=150)
            record = {"tag": tag, "status": "RECORDED", "scope": "Same frozen candidate; versioned daily-loader correction, no reselection",
                      "candidate": config, "start": start, "end_exclusive": end, "model": model, "metrics": result["metrics"],
                      "statistics": result["statistics"], "native": result["native"],
                      "results_path": "native/" + tag + "/results.json", "implementation_receipt": "V2 FREEZE.json"}
        except Exception as error:
            record = {"tag": tag, "status": "FAILED_NOT_REPLACED", "start": start, "end_exclusive": end, "model": model,
                      "error": type(error).__name__ + ": " + str(error), "implementation_receipt": "V2 FREEZE.json"}
        records.append(record)
        native.save(ROOT / "NATIVE CONFIRM V2 PROGRESS.json", {"cases": records, "implementation": "V2 daily loader only"})
        if record["status"] == "RECORDED" and model == 4 and any(key in tag for key in ("-oos-", "-older-validation-", "-development-")):
            target = ROOT / "NATIVE ROBUSTNESS.json"
            robust = native.read(target) if target.exists() else {}
            try:
                robust[tag] = native_robustness.analyze_native_case(ROOT, tag, paths=10000)
            except Exception as error:
                robust[tag] = {"status": "AUDIT_FAILED_NOT_SUBSTITUTED", "error": type(error).__name__ + ": " + str(error)}
            native.save(target, robust)
        print(json.dumps({"event": "end", "tag": tag, "status": record["status"], "metrics": record.get("metrics"), "error": record.get("error")}), flush=True)
    audit = native.read(ROOT / "NATIVE AUDIT.json")
    all_cases = []
    for path in sorted(ROOT.glob("NATIVE *PROGRESS.json")):
        all_cases += native.read(path)["cases"]
    audit.update({"cases": all_cases, "status": "COMPLETED_WITH_EXPLICIT_FAILURES", "versioned_repair": version,
                  "promotion_passed": False, "no_live_changes": True})
    native.save(ROOT / "NATIVE AUDIT.json", audit)
    return records


if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["freeze"]:
        freeze()
    elif sys.argv[1:] == ["run"]:
        print(json.dumps({"cases_finished": len(run())}))
    else:
        raise SystemExit("Use freeze, then run. Both operate on research files only.")
