from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BT = PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
EXPERT_TARGET = BT / "MQL5" / "Experts" / "BM Trading" / "BAT Portfolio 2026-08-09"
SET_TARGET = BT / "MQL5" / "Profiles" / "Tester"
CONFIG_TARGET = BT / "backtest-configs" / "bat-portfolio-20260809"
REPORT_TARGET = BT / "reports" / "bat-portfolio-20260809"

START = "2025.08.07"
FINISH = "2026.08.06"

CASES = [
    {
        "id": "01-lta-volume-profile", "label": "LTA Volume Profile", "symbol": "XAUUSD", "period": "M15",
        "expert": "LTA_Concepts_EA.ex5", "expert_source": "LTA volume profile/EA/LTA_Concepts_EA.ex5",
        "set_source": "LTA volume profile/Best Settings/RETEST PASSED 2026-08-07 - LTA - XAUUSD M15 - 1pct.set",
    },
    {
        "id": "02-orb-volume-profile", "label": "ORB Volume Profile", "symbol": "XAUUSD", "period": "M5",
        "expert": "ORB Volume Data EA.ex5", "expert_source": "ORB Volume Data EA/ORB Volume Data EA.ex5",
        "set_source": "ORB Volume Data EA/Volume Profile Settings/VISUAL PROFILE - XAUUSD M5 - validated baseline.set",
    },
    {
        "id": "03-atr-candle-breakout", "label": "ATR Candle Breakout", "symbol": "XAUUSD", "period": "H1",
        "expert": "ATR Candle Breakout EA.ex5", "expert_source": "ATR Candle Breakout EA/ATR Candle Breakout EA.ex5",
        "set_source": "ATR Candle Breakout EA/RETEST PASSED 2026-08-07 - ATR Candle Breakout - XAUUSD H1 - 1pct.set",
    },
    {
        "id": "04-aaa-final-asia-breakout", "label": "AAA Final Asia Breakout", "symbol": "XAUUSD", "period": "H1",
        "expert": "AAA Final Asia Breakout EA.ex5", "expert_source": "AAA Final EAs/AAA Final Asia Breakout EA/AAA Final Asia Breakout EA.ex5",
        "set_source": "AAA Final EAs/AAA Final Asia Breakout EA/RETEST PASSED 2026-08-07 - Asia Breakout - XAUUSD H1 - 1pct.set",
    },
    {
        "id": "05-aaa-final-dmc", "label": "AAA Final DmC", "symbol": "XAUUSD", "period": "H1",
        "expert": "AAA Final DmC EA.ex5", "expert_source": "AAA Final EAs/AAA Final DmC EA/AAA Final DmC EA.ex5",
        "set_source": "AAA Final EAs/AAA Final DmC EA/RETEST PASSED 2026-08-07 - DmC - XAUUSD H1 - 1pct.set",
    },
    {
        "id": "06-go-long", "label": "Go Long", "symbol": "US30", "period": "D1",
        "expert": "Go Long EA.ex5", "expert_source": "Go Long EA/Go Long EA.ex5",
        "set_source": "Go Long EA/RETEST INCLUDED 2026-08-07 - Go Long - US30 D1 - 1pct.set",
    },
    {
        "id": "07-aaa-final-ema3", "label": "AAA Final EMA3", "symbol": "XAUUSD", "period": "H4",
        "expert": "AAA Final EMA3 EA.ex5", "expert_source": "AAA Final EAs/AAA Final EMA3 EA/AAA Final EMA3 EA.ex5",
        "set_source": "AAA Final EAs/AAA Final EMA3 EA/RETEST INCLUDED 2026-08-07 - EMA3 - XAUUSD H4 - 1pct.set",
    },
    {
        "id": "08-aaa-final-xau-weakness", "label": "AAA Final XAU Weakness", "symbol": "XAUUSD", "period": "M15",
        "expert": "AAA Final XAU Weakness EA.ex5", "expert_source": "AAA Final EAs/AAA Final XAU Weakness EA/AAA Final XAU Weakness EA.ex5",
        "set_source": "AAA Final EAs/AAA Final XAU Weakness EA/RETEST INCLUDED 2026-08-07 - XAU Weakness - XAUUSD M15 - 1pct.set",
    },
    {
        "id": "09-ninja-turtle-scalper", "label": "Ninja Turtle Scalper", "symbol": "EURUSD", "period": "M5",
        "expert": "Ninja Turtle Scalper EA.ex5", "expert_source": "Ninja Turtle Scalper EA/Ninja Turtle Scalper EA.ex5",
        "set_source": "Ninja Turtle Scalper EA/RETEST INCLUDED 2026-08-07 - Ninja Turtle - EURUSD M5 - 1pct.set",
    },
    {
        "id": "10-nasdaq-overnight", "label": "Nasdaq Overnight", "symbol": "USTEC", "period": "M1",
        "expert": "Nasdaq Overnight Negative Day EA.ex5", "expert_source": "Nasdaq Overnight Negative Day EA/Nasdaq Overnight Negative Day EA.ex5",
        "set_source": "Nasdaq Overnight Negative Day EA/RETEST INCLUDED 2026-08-07 - Nasdaq Overnight - USTEC M1 - 1pct.set",
    },
    {
        "id": "11-turnaround-tuesday", "label": "Turnaround Tuesday", "symbol": "USTEC", "period": "D1",
        "expert": "Turnaround Tuesday EA.ex5", "expert_source": "Turnaround Tuesday EA/Turnaround Tuesday EA.ex5",
        "set_source": "Turnaround Tuesday EA/RETEST INCLUDED 2026-08-07 - Turnaround Tuesday - USTEC D1 - 1pct.set",
    },
    {
        "id": "12-aaa-final-us100-weakness", "label": "AAA Final US100 Weakness", "symbol": "USTEC", "period": "M15",
        "expert": "AAA Final US100 Weakness EA.ex5", "expert_source": "AAA Final EAs/AAA Final US100 Weakness EA/AAA Final US100 Weakness EA.ex5",
        "set_source": "AAA Final EAs/AAA Final US100 Weakness EA/RETEST INCLUDED 2026-08-07 - US100 Weakness - USTEC M15 - 1pct.set",
    },
    {
        "id": "13-aaa-final-news-pulse", "label": "AAA Final News Pulse - TEMP TEST", "symbol": "XAUUSD", "period": "M1",
        "expert": "AAA Final News Pulse EA.ex5", "expert_source": "AAA Final EAs/AAA Final News Pulse EA/AAA Final News Pulse EA.ex5",
        "set_source": "AAA Final EAs/AAA Final News Pulse EA/TEMP TEST INCLUDED 2026-08-07 - News Pulse - XAUUSD M1 - 1pct.set",
    },
]


def config_text(case: dict, set_name: str) -> str:
    return f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert=BM Trading\\BAT Portfolio 2026-08-09\\{Path(case['expert']).stem}
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
Report=reports\\bat-portfolio-20260809\\{case['id']}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""


def main() -> None:
    EXPERT_TARGET.mkdir(parents=True, exist_ok=True)
    SET_TARGET.mkdir(parents=True, exist_ok=True)
    CONFIG_TARGET.mkdir(parents=True, exist_ok=True)
    REPORT_TARGET.mkdir(parents=True, exist_ok=True)
    ROOT.mkdir(parents=True, exist_ok=True)

    manifest = []
    for case in CASES:
        expert_source = PACKAGE / case["expert_source"]
        set_source = PACKAGE / case["set_source"]
        if not expert_source.exists():
            raise FileNotFoundError(expert_source)
        if not set_source.exists():
            raise FileNotFoundError(set_source)
        shutil.copy2(expert_source, EXPERT_TARGET / case["expert"])
        set_name = f"BAT13 {case['id']}.set"
        shutil.copy2(set_source, SET_TARGET / set_name)
        config = CONFIG_TARGET / f"{case['id']}.ini"
        config.write_text(config_text(case, set_name), encoding="utf-8")
        manifest.append({
            **case,
            "chart": f"{case['symbol']} {case['period']}",
            "set_name": set_name,
            "config": str(config),
            "report": str(REPORT_TARGET / f"{case['id']}.htm"),
        })
    manifest_path = CONFIG_TARGET / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (CONFIG_TARGET / "manifest-without-lta.json").write_text(json.dumps(manifest[1:], indent=2), encoding="utf-8")
    (CONFIG_TARGET / "manifest-lta-only.json").write_text(json.dumps(manifest[:1], indent=2), encoding="utf-8")
    (CONFIG_TARGET / "manifest-orb-only.json").write_text(json.dumps(manifest[1:2], indent=2), encoding="utf-8")
    (CONFIG_TARGET / "manifest-after-orb.json").write_text(json.dumps(manifest[2:], indent=2), encoding="utf-8")
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Prepared {len(manifest)} BAT portfolio cases: {manifest_path}")


if __name__ == "__main__":
    main()
