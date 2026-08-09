from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BT = PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
TESTER = BT / "MQL5" / "Profiles" / "Tester"
CONFIG = BT / "backtest-configs" / "nq-drift-vwap"
REPORTS = BT / "reports" / "nq-drift-vwap"

# A small, declared sensitivity grid.  The stop and the video guardrails remain fixed.
VARIANTS = {
    "exact":       {"drift": 0.100, "first": False, "long_tp": 40, "short_tp": 50},
    "first-only":  {"drift": 0.100, "first": True,  "long_tp": 40, "short_tp": 50},
    "drift-075":   {"drift": 0.075, "first": False, "long_tp": 40, "short_tp": 50},
    "drift-125":   {"drift": 0.125, "first": False, "long_tp": 40, "short_tp": 50},
    "target-40":   {"drift": 0.100, "first": False, "long_tp": 40, "short_tp": 40},
    "target-50":   {"drift": 0.100, "first": False, "long_tp": 50, "short_tp": 50},
}

PERIODS = {
    "smoke": ("2024.01.02", "2024.12.31"),
    "dev": ("2022.01.03", "2024.12.31"),
    "selection": ("2025.01.02", "2025.08.06"),
    "final": ("2025.08.07", "2026.08.06"),
    "full": ("2022.01.03", "2026.08.06"),
}


def set_text(name: str, values: dict) -> str:
    magic = 86080850 + list(VARIANTS).index(name)
    items = [
        ("InpEnableTrading", "true"),
        ("InpSignalTimeframe", "5"),
        ("InpVWAPTimeframe", "15"),
        ("InpDriftLookbackBars", "4"),
        ("InpMinimumHourlyDriftPercent", f"{values['drift']:.3f}"),
        ("InpRequireFirstPullbackOnly", str(values["first"]).lower()),
        ("InpIndexPointSize", "1.0"),
        ("InpStopPoints", "80.0"),
        ("InpLongTargetPoints", f"{values['long_tp']:.1f}"),
        ("InpShortTargetPoints", f"{values['short_tp']:.1f}"),
        ("InpMaximumTradesPerDay", "4"),
        ("InpMaximumLossesPerDay", "2"),
        ("InpRiskPercent", "1.0"),
        ("InpMaximumSpreadIndexPoints", "10.0"),
        ("InpMaxDeviationPoints", "50"),
        ("InpMagic", str(magic)),
        ("InpAnchorHourNY", "9"),
        ("InpAnchorMinuteNY", "30"),
        ("InpStartTradingHourNY", "10"),
        ("InpStartTradingMinuteNY", "30"),
        ("InpStopNewTradesHourNY", "15"),
        ("InpStopNewTradesMinuteNY", "30"),
        ("InpFlatHourNY", "15"),
        ("InpFlatMinuteNY", "55"),
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
Expert=BM Trading\\NQ Drift VWAP Pullback EA\\NQ Drift VWAP Pullback EA
ExpertParameters={set_name}
Symbol=USTEC
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
Report=reports\\nq-drift-vwap\\{report_name}.htm
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
        set_name = f"NQ Drift {name}.set"
        (TESTER / set_name).write_text(set_text(name, values), encoding="utf-8-sig")
    for period in PERIODS:
        cases = []
        names = ["exact"] if period == "smoke" else list(VARIANTS)
        for name in names:
            case = f"{period}-{name}"
            set_name = f"NQ Drift {name}.set"
            ini = CONFIG / f"{case}.ini"
            ini.write_text(config_text(set_name, period, case), encoding="utf-8")
            cases.append({
                "case": case,
                "variant": name,
                "period": period,
                "config": str(ini),
                "report": str(REPORTS / f"{case}.htm"),
                "set": str(TESTER / set_name),
            })
        (CONFIG / f"{period}-manifest.json").write_text(json.dumps(cases, indent=2), encoding="utf-8")
        if period == "dev":
            (CONFIG / "dev-remainder-manifest.json").write_text(
                json.dumps([case for case in cases if case["variant"] != "exact"], indent=2),
                encoding="utf-8",
            )
            (CONFIG / "dev-first-only-manifest.json").write_text(
                json.dumps([case for case in cases if case["variant"] == "first-only"], indent=2),
                encoding="utf-8",
            )
        if period in {"selection", "final", "full"}:
            (CONFIG / f"{period}-locked-manifest.json").write_text(
                json.dumps([case for case in cases if case["variant"] == "exact"], indent=2),
                encoding="utf-8",
            )
    print("Prepared NQ Drift VWAP research cases.")


if __name__ == "__main__":
    main()
