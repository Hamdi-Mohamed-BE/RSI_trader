from __future__ import annotations

import importlib.util
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
ONE_YEAR_PREP = PACKAGE / "Active BAT Backtest 2026-08-12" / "Prepare-Active-BAT-Backtest.py"
BT = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
EXPERT_TARGET = BT / "MQL5" / "Experts" / "BM Trading" / "Active BAT 5Y 2026-08-12"
SET_TARGET = BT / "MQL5" / "Profiles" / "Tester"
CONFIG_TARGET = BT / "backtest-configs" / "active-bat-5y-20260812"
REPORT_TARGET = BT / "reports" / "active-bat-5y-20260812"
OUTPUT_REPORTS = ROOT / "MT5 Reports"
START = "2021.08.11"
FINISH = "2026.08.10"

spec = importlib.util.spec_from_file_location("one_year_cases", ONE_YEAR_PREP)
source = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(source)
CASES = [case for case in source.CASES if case["id"] != "09-ninja-turtle-scalper"]


def config_text(case: dict, set_name: str) -> str:
    return f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=BM Trading\\Active BAT 5Y 2026-08-12\\{Path(case['expert']).stem}
ExpertParameters={set_name}
Symbol={case['symbol']}
Period={case['period']}
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate={START}
ToDate={FINISH}
ForwardMode=0
Report=reports\\active-bat-5y-20260812\\{case['id']}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""


def main() -> None:
    for path in (EXPERT_TARGET, SET_TARGET, CONFIG_TARGET, REPORT_TARGET, OUTPUT_REPORTS):
        path.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case in CASES:
        expert_source = PACKAGE / case["expert_source"]
        set_source = PACKAGE / case["set_source"]
        if not expert_source.exists():
            raise FileNotFoundError(expert_source)
        if not set_source.exists():
            raise FileNotFoundError(set_source)
        shutil.copy2(expert_source, EXPERT_TARGET / case["expert"])
        set_name = f"ACTIVE BAT 5Y 20260812 {case['id']}.set"
        shutil.copy2(set_source, SET_TARGET / set_name)
        config = CONFIG_TARGET / f"{case['id']}.ini"
        config.write_text(config_text(case, set_name), encoding="utf-8-sig")
        manifest.append({
            **case,
            "chart": f"{case['symbol']} {case['period']}",
            "set_name": set_name,
            "config": str(config),
            "report": str(REPORT_TARGET / f"{case['id']}.htm"),
        })
    (CONFIG_TARGET / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8-sig")
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8-sig")
    print(f"Prepared {len(manifest)} five-year active-BAT cases.")


if __name__ == "__main__":
    main()
