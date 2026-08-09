from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BT = PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
TESTER = BT / "MQL5" / "Profiles" / "Tester"
CONFIG = BT / "backtest-configs" / "gold-liquidity-sweep"
REPORTS = BT / "reports" / "gold-liquidity-sweep"

VARIANTS = {
    "aggressive-core": {"mode": 0, "window": True, "start": 7, "end": 18, "disp": 0.80, "recovery": 0.55, "body": 0.45},
    "momentum-core": {"mode": 1, "window": True, "start": 7, "end": 18, "disp": 0.80, "recovery": 0.55, "body": 0.45},
    "mss-retest-core": {"mode": 2, "window": True, "start": 7, "end": 18, "disp": 0.80, "recovery": 0.55, "body": 0.45},
    "aggressive-all": {"mode": 0, "window": False, "start": 0, "end": 23, "disp": 0.80, "recovery": 0.55, "body": 0.45},
    "momentum-all": {"mode": 1, "window": False, "start": 0, "end": 23, "disp": 0.80, "recovery": 0.55, "body": 0.45},
    "aggressive-ny": {"mode": 0, "window": True, "start": 12, "end": 18, "disp": 0.80, "recovery": 0.55, "body": 0.45},
    "momentum-ny": {"mode": 1, "window": True, "start": 12, "end": 18, "disp": 0.80, "recovery": 0.55, "body": 0.45},
    "momentum-loose": {"mode": 1, "window": True, "start": 7, "end": 18, "disp": 0.60, "recovery": 0.50, "body": 0.35},
    "aggressive-core-loose": {"mode": 0, "window": True, "start": 7, "end": 18, "disp": 0.60, "recovery": 0.50, "body": 0.45},
    "aggressive-all-loose": {"mode": 0, "window": False, "start": 0, "end": 23, "disp": 0.60, "recovery": 0.50, "body": 0.45},
}

PERIODS = {
    "smoke": ("2024.01.02", "2024.12.31"),
    "dev": ("2022.01.03", "2024.12.31"),
    "selection": ("2025.01.02", "2025.08.06"),
    "final": ("2025.08.07", "2026.08.06"),
    "full": ("2022.01.03", "2026.08.06"),
}


def set_text(name: str, values: dict) -> str:
    magic = 86080810 + list(VARIANTS).index(name)
    items = [
        ("InpEnableTrading", "true"),
        ("InpSignalTimeframe", "5"),
        ("InpEntryMode", str(values["mode"])),
        ("InpStructurePivotDepth", "2"),
        ("InpStructureLookback", "120"),
        ("InpZoneLookbackBars", "96"),
        ("InpZoneBreakLookback", "8"),
        ("InpZoneDisplacementATR", f"{values['disp']:.2f}"),
        ("InpSweepBufferATR", "0.03"),
        ("InpSweepRecoveryFraction", f"{values['recovery']:.2f}"),
        ("InpConfirmationBars", "4"),
        ("InpConfirmationBodyRatio", f"{values['body']:.2f}"),
        ("InpRetestBars", "5"),
        ("InpStopBufferATR", "0.08"),
        ("InpMaximumStopATR", "2.50"),
        ("InpMinimumRewardRisk", "1.20"),
        ("InpMaximumRewardRisk", "3.00"),
        ("InpMaximumHoldingMinutes", "180"),
        ("InpMaximumTradesPerDay", "2"),
        ("InpRiskPercent", "1.00"),
        ("InpMaximumSpreadATRPercent", "8.0"),
        ("InpMaxDeviationPoints", "30"),
        ("InpMagic", str(magic)),
        ("InpUseTradingWindow", str(values["window"]).lower()),
        ("InpStartHourUTC", str(values["start"])),
        ("InpEndHourUTC", str(values["end"])),
        ("InpWeekdaysOnly", "true"),
        ("InpUseAutomaticLiveServerOffset", "true"),
        ("InpTesterServerUTCOffsetHours", "0"),
        ("InpManualLiveServerUTCOffsetHours", "0"),
    ]
    return "\n".join(f"{key}={value}||{value}||0||{value}||N" for key, value in items) + "\n"


def config_text(set_name: str, period: str, report_name: str) -> str:
    start, finish = PERIODS[period]
    return f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=BM Trading\\Gold Liquidity Sweep EA\\Gold Liquidity Sweep EA
ExpertParameters={set_name}
Symbol=XAUUSD
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate={start}
ToDate={finish}
ForwardMode=0
Report=reports\\gold-liquidity-sweep\\{report_name}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""


def main() -> None:
    TESTER.mkdir(parents=True, exist_ok=True)
    CONFIG.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    for name, values in VARIANTS.items():
        set_name = f"GLS {name}.set"
        (TESTER / set_name).write_text(set_text(name, values), encoding="utf-8-sig")
    for period in PERIODS:
        manifest = []
        names = (["aggressive-core-loose", "aggressive-all-loose"]
                 if period == "smoke" else list(VARIANTS))
        for name in names:
            case = f"{period}-{name}"
            set_name = f"GLS {name}.set"
            ini = CONFIG / f"{case}.ini"
            ini.write_text(config_text(set_name, period, case), encoding="utf-8")
            manifest.append({
                "case": case,
                "variant": name,
                "period": period,
                "config": str(ini),
                "report": str(REPORTS / f"{case}.htm"),
                "set": str(TESTER / set_name),
            })
        (CONFIG / f"{period}-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    aggressive = {
        "aggressive-core", "aggressive-all", "aggressive-ny",
        "aggressive-core-loose", "aggressive-all-loose",
    }
    dev_cases = json.loads((CONFIG / "dev-manifest.json").read_text(encoding="utf-8"))
    (CONFIG / "dev-shortlist-manifest.json").write_text(
        json.dumps([case for case in dev_cases if case["variant"] in aggressive], indent=2),
        encoding="utf-8",
    )
    for period in ("selection", "final", "full"):
        cases = json.loads((CONFIG / f"{period}-manifest.json").read_text(encoding="utf-8"))
        (CONFIG / f"{period}-locked-manifest.json").write_text(
            json.dumps([case for case in cases if case["variant"] == "aggressive-core"], indent=2),
            encoding="utf-8",
        )
    print("Prepared gold-liquidity research cases.")


if __name__ == "__main__":
    main()
