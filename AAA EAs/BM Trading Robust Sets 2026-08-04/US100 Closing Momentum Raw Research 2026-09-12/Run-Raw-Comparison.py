from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
ASSET = os.getenv("CLOSING_MOMENTUM_ASSET", "USTEC").upper()
if ASSET not in {"USTEC", "XAUUSD"}:
    raise ValueError(f"Unsupported closing-momentum asset: {ASSET}")
OUTPUT_ROOT = ROOT if ASSET == "USTEC" else PACKAGE / "XAU Closing Momentum Raw Research 2026-09-12"
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
TERMINAL = TESTER / "terminal64.exe"
EDITOR = TESTER / "MetaEditor64.exe"
SOURCE = ROOT / "EA" / "US100 Closing Momentum Raw EA.mq5"
EXPERT_FOLDER = Path("AAA Research") / f"{ASSET} Closing Momentum 20260912"
EXPERT_NAME = "US100 Closing Momentum Raw EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / EXPERT_FOLDER
EXPERT_SOURCE = EXPERT_DIR / f"{EXPERT_NAME}.mq5"
EXPERT_TARGET = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
SETS = OUTPUT_ROOT / "Sets"
REPORTS = OUTPUT_ROOT / "Backtest Reports"
CONFIGS = TESTER / "backtest-configs" / f"{ASSET.lower()}-closing-momentum-20260912"
TESTER_REPORTS = TESTER / "reports" / f"{ASSET.lower()}-closing-momentum-20260912"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"
CACHE = PACKAGE / ".." / "EA store" / "data" / "evidence-cache" / "v1" / "products" / "nasdaq-overnight" / "standard"

WINDOWS = {
    "6m": ("2026.03.05", "2026.09.05"),
    "1y": ("2025.09.05", "2026.09.05"),
    "3y": ("2023.09.05", "2026.09.05"),
    "5y": ("2021.09.05", "2026.09.05"),
}
MODEL = int(os.getenv("CLOSING_MOMENTUM_MODEL", "1"))
REQUESTED_PERIODS = {
    item.strip() for item in os.getenv("CLOSING_MOMENTUM_PERIODS", ",".join(WINDOWS)).split(",") if item.strip()
}


def load_analyzer():
    spec = importlib.util.spec_from_file_location("mt5_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared MT5 report parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


def set_text(magic: int) -> str:
    if ASSET == "XAUUSD":
        entry_hour, entry_minute, exit_hour, exit_minute, require_dst = 13, 0, 13, 30, "false"
    else:
        entry_hour, entry_minute, exit_hour, exit_minute, require_dst = 15, 30, 16, 0, "true"
    return f"""InpEnableTrading=true
InpEntryHour={entry_hour}
InpEntryMinute={entry_minute}
InpExitHour={exit_hour}
InpExitMinute={exit_minute}
InpEntryWindowMinutes=10
InpExitWindowMinutes=30
InpRequireNyDstSession={require_dst}
InpRiskPercent=1
InpEmergencyStopPercent=2
InpMaxSpreadPoints=0
InpMaxDeviationPoints=30
InpMagic={magic}
InpUseAutomaticLiveServerOffset=true
InpTesterServerUTCOffsetHours=0
InpManualLiveServerUTCOffsetHours=0
"""


def prepare() -> None:
    for path in (OUTPUT_ROOT / "EA", EXPERT_DIR, SETS, REPORTS, CONFIGS, TESTER_REPORTS, TESTER_SETS):
        path.mkdir(parents=True, exist_ok=True)
    if not TERMINAL.is_file() or not EDITOR.is_file() or not SOURCE.is_file():
        raise FileNotFoundError("The source or isolated MT5 tools are missing")
    active = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "D0E8209F77C8CF37AD8BF550E51FF075" / "config"
    isolated = TESTER / "Config"
    isolated.mkdir(parents=True, exist_ok=True)
    for name in ("accounts.dat", "servers.dat", "common.ini"):
        source = active / name
        if source.is_file():
            shutil.copy2(source, isolated / name)
    shutil.copy2(SOURCE, EXPERT_SOURCE)
    log_path = OUTPUT_ROOT / "compile.log"
    if log_path.exists():
        log_path.unlink()
    command = f'"{EDITOR}" /portable /compile:"{EXPERT_SOURCE}" /log:"{log_path}"'
    result = subprocess.run(
        command,
        cwd=TESTER,
        timeout=180,
        creationflags=subprocess.CREATE_NO_WINDOW,
        check=False,
    )
    detail = log_path.read_text(encoding="utf-16", errors="ignore") if log_path.is_file() else "no compile log"
    if "0 errors, 0 warnings" not in detail or not EXPERT_TARGET.is_file():
        raise RuntimeError(f"MetaEditor compile failed ({result.returncode})\n{detail}")
    shutil.copy2(EXPERT_TARGET, OUTPUT_ROOT / "EA" / EXPERT_TARGET.name)


def run_period(period: str, start: str, end: str, sequence: int) -> dict:
    set_name = f"Closing-Momentum-Raw-{period}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(84123000 + sequence), encoding="utf-8")
    shutil.copy2(set_path, TESTER_SETS / set_name)
    report_name = f"{ASSET.lower()}-closing-momentum-raw-model{MODEL}-{period}.htm"
    tester_report = TESTER_REPORTS / report_name
    for stale in TESTER_REPORTS.glob(f"{ASSET.lower()}-closing-momentum-raw-model{MODEL}-{period}*"):
        stale.unlink()
    ini = (
        "[Common]\r\nLogin=472334559\r\nServer=Exness-MT5Trial16\r\n\r\n"
        "[Tester]\r\n"
        f"Expert={str(EXPERT_FOLDER).replace('/', chr(92))}\\{EXPERT_NAME}\r\n"
        f"ExpertParameters={set_name}\r\nSymbol={ASSET}\r\nPeriod=M1\r\n"
        "Login=472334559\r\nDeposit=10000\r\nCurrency=USD\r\nLeverage=1:2000\r\n"
        f"Model={MODEL}\r\nExecutionMode=1\r\nOptimization=0\r\n"
        f"FromDate={start}\r\nToDate={end}\r\nForwardMode=0\r\n"
        f"Report=reports\\{ASSET.lower()}-closing-momentum-20260912\\{report_name}\r\n"
        "ReplaceReport=1\r\nShutdownTerminal=1\r\nUseCloud=0\r\nVisual=0\r\n"
    )
    config_path = CONFIGS / f"{period}.ini"
    config_path.write_text(ini, encoding="utf-16")
    print(f"START {period} {start} to {end}", flush=True)
    process = subprocess.Popen(
        [str(TERMINAL), "/portable", f"/config:{config_path.relative_to(TESTER)}"],
        cwd=TESTER,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f"MT5 timed out: {period}")
    deadline = time.time() + 15
    while not tester_report.is_file() and time.time() < deadline:
        time.sleep(0.25)
    if not tester_report.is_file():
        raise FileNotFoundError(f"Missing MT5 report: {tester_report}")
    for artifact in TESTER_REPORTS.glob(f"{ASSET.lower()}-closing-momentum-raw-model{MODEL}-{period}*"):
        shutil.copy2(artifact, REPORTS / artifact.name)
    parsed = ANALYZER.parse_report(tester_report)
    return {"period": period, "from": start.replace(".", "-"), "to": end.replace(".", "-"), **parsed}


def overnight_row(period: str) -> dict:
    payload = json.loads((CACHE / f"{period}.json").read_text(encoding="utf-8"))
    stats = payload["stats"]
    return {
        "period": period,
        "from": stats["from"],
        "to": stats["to"],
        "return_pct": stats["return_pct"],
        "profit_factor": stats["profit_factor"],
        "win_rate_pct": stats["win_rate_pct"],
        "max_drawdown_pct": stats["max_drawdown_pct"],
        "trades": stats["trades"],
        "sharpe": stats["sharpe_ratio"],
        "recovery_factor": stats["recovery_factor"],
        "commission": stats["commission"],
        "swap": stats["swap"],
        "total_costs": stats["total_costs"],
        "history_quality": stats["history_quality"],
    }


def main() -> int:
    prepare()
    closing_rows = []
    selected = [(period, bounds) for period, bounds in WINDOWS.items() if period in REQUESTED_PERIODS]
    for sequence, (period, (start, end)) in enumerate(selected, start=1):
        closing_rows.append(run_period(period, start, end, sequence))
    payload = {
        "generated_at": "2026-09-12",
        "instrument": f"{ASSET} (Exness CFD)",
        "model": MODEL,
        "method": f"Native MT5 {'Every Tick' if MODEL == 0 else '1-minute-OHLC'} comparison, random execution delay, broker spread/commission/swap, USD 10,000, 1% risk sized to a 2% emergency price stop.",
        "signal": (
            "At 13:00 New York, follow the sign of the return from the previous 13:30 COMEX gold close; flatten in the final tradable minute before 13:30 New York."
            if ASSET == "XAUUSD"
            else "At 15:30 New York, follow the sign of the return from the previous 16:00 cash close; flatten in the final tradable minute before 16:00 New York. Skip standard-time dates because Exness USTEC does not quote through the required final half hour then."
        ),
        "paper_fidelity_note": "Entry direction and 30-minute exit are raw. The 2% emergency stop is a shared execution safety device used only to size both strategies at the same 1% equity risk.",
        "closing_momentum": [{k: v for k, v in row.items() if k != "deals"} for row in closing_rows],
        "nasdaq_overnight": [overnight_row(period) for period, _ in selected] if ASSET == "USTEC" else [],
    }
    (OUTPUT_ROOT / f"results-model{MODEL}.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
