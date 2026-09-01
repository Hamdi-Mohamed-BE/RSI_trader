from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BT = PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
TESTER = BT / "MQL5" / "Profiles" / "Tester"
CONFIG = BT / "backtest-configs" / "orb-volume-profile"
REPORTS = BT / "reports" / "orb-volume-profile"

MARKETS = {
    "xau": ("XAUUSD", "VALIDATED - XAUUSD M5 - 1pct.set"),
    "btc": ("BTCUSD", "REJECTED FINAL - BTCUSD M5 - 1pct.set"),
    "us30": ("US30", "VALIDATED MODEST - US30 M5 - 1pct.set"),
    "ustec": ("USTEC", "REJECTED FINAL - USTEC M5 - 1pct.set"),
    "us500": ("US500", "REJECTED FINAL - US500 M5 - 1pct.set"),
}

VARIANTS = {
    "control": (False, False, False, 1.00),
    "va": (True, False, False, 1.00),
    "poc": (False, True, False, 1.00),
    "lvn100": (False, False, True, 1.00),
    "va-poc": (True, True, False, 1.00),
    "va-lvn100": (True, False, True, 1.00),
    "full100": (True, True, True, 1.00),
}

PERIODS = {
    "dev": ("2024.01.02", "2024.12.31"),
    "selection": ("2025.01.02", "2025.08.06"),
    "final": ("2025.08.07", "2026.08.06"),
}


def inject_profile_inputs(text: str, variant: tuple[bool, bool, bool, float]) -> str:
    va, poc, lvn, threshold = variant
    names = {
        "InpUseProfileValueArea",
        "InpUseProfilePOCBias",
        "InpUseProfileBoundaryLVN",
        "InpProfileStartHour",
        "InpProfileStartMinute",
        "InpProfileBins",
        "InpProfileValueAreaPercent",
        "InpMaxBoundaryNodeRatio",
        "InpMinimumProfileTicks",
        "InpShowProfileLevels",
    }
    lines = [line for line in text.splitlines() if line.split("=", 1)[0] not in names]
    insertion = next((i + 1 for i, line in enumerate(lines) if line.startswith("InpSlowEMA=")), len(lines))
    profile = [
        f"InpUseProfileValueArea={str(va).lower()}||false||0||true||N",
        f"InpUseProfilePOCBias={str(poc).lower()}||false||0||true||N",
        f"InpUseProfileBoundaryLVN={str(lvn).lower()}||false||0||true||N",
        "InpProfileStartHour=8||8||1||8||N",
        "InpProfileStartMinute=0||0||1||0||N",
        "InpProfileBins=48||48||8||48||N",
        "InpProfileValueAreaPercent=70.0||70.0||5.0||70.0||N",
        f"InpMaxBoundaryNodeRatio={threshold:.2f}||1.0||0.25||1.0||N",
        "InpMinimumProfileTicks=100||100||10||100||N",
        "InpShowProfileLevels=false||false||0||true||N",
    ]
    lines[insertion:insertion] = profile
    return "\n".join(lines) + "\n"


def config_text(symbol: str, set_name: str, period: str, report_name: str) -> str:
    start, finish = PERIODS[period]
    return f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=BM Trading\\ORB Volume Data EA\\ORB Volume Data EA
ExpertParameters={set_name}
Symbol={symbol}
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
Report=reports\\orb-volume-profile\\{report_name}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""


def main() -> None:
    TESTER.mkdir(parents=True, exist_ok=True)
    CONFIG.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    for period in PERIODS:
        manifest = []
        for key, (symbol, source_name) in MARKETS.items():
            source = ROOT / "Best Settings" / source_name
            original = source.read_text(encoding="utf-8-sig")
            for variant_name, variant in VARIANTS.items():
                set_name = f"ORBVP {symbol} {variant_name}.set"
                (TESTER / set_name).write_text(inject_profile_inputs(original, variant), encoding="utf-8-sig")
                case = f"{period}-{key}-{variant_name}"
                ini = CONFIG / f"{case}.ini"
                ini.write_text(config_text(symbol, set_name, period, case), encoding="utf-8")
                manifest.append({
                    "case": case,
                    "market": key,
                    "symbol": symbol,
                    "variant": variant_name,
                    "period": period,
                    "config": str(ini),
                    "report": str(REPORTS / f"{case}.htm"),
                    "set": str(TESTER / set_name),
                })
        (CONFIG / f"{period}-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    locked = {
        "xau": {"control", "va"},
        "btc": {"control", "lvn100"},
        "us30": {"control"},
        "ustec": {"control", "va"},
        "us500": {"control"},
    }
    final_cases = json.loads((CONFIG / "final-manifest.json").read_text(encoding="utf-8"))
    locked_cases = [case for case in final_cases if case["variant"] in locked[case["market"]]]
    (CONFIG / "locked-final-manifest.json").write_text(json.dumps(locked_cases, indent=2), encoding="utf-8")
    print(f"Prepared {len(MARKETS) * len(VARIANTS)} cases for each research period.")


if __name__ == "__main__":
    main()
