from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / "_Backtests" / "MT5-Isolated-20260805"
TERMINAL = TESTER / "terminal64.exe"
METAEDITOR = TESTER / "MetaEditor64.exe"
SOURCE = ROOT / "EA" / "Calyx Night Effect Metals Raw EA.mq5"
EXPERT_FOLDER = "AAA Research\\Night Effect Metals"
EXPERT_NAME = "Calyx Night Effect Metals Raw EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "Night Effect Metals"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "night-effect-metals-20260909"
TESTER_REPORTS = TESTER / "reports" / "night-effect-metals-20260909"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"

ASSETS = [("XAUUSD", 0), ("XAGUSD", 1)]
PERIODS = [
    ("5y", "2021.09.01", "2026.09.01"),
    ("3y", "2023.09.01", "2026.09.01"),
    ("1y", "2025.09.01", "2026.09.01"),
]


def load_analyzer():
    spec = importlib.util.spec_from_file_location("night_effect_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the native MT5 report analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


def wait_for_terminal_to_close(timeout: int = 45) -> None:
    target = str(TERMINAL).replace("'", "''")
    command = (
        f"$target='{target}'; "
        "@(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
        "Where-Object { $_.ExecutablePath -ieq $target }).Count"
    )
    deadline = time.time() + timeout
    while time.time() < deadline:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        lines = result.stdout.strip().splitlines()
        if result.returncode == 0 and lines and lines[-1].strip() == "0":
            return
        time.sleep(1)
    raise RuntimeError("The isolated MT5 tester did not close cleanly")


def stop_stale_terminal() -> None:
    target = str(TERMINAL).replace("'", "''")
    command = (
        f"$target='{target}'; "
        "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
        "Where-Object { $_.ExecutablePath -ieq $target } | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-Command", command],
        check=True,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    wait_for_terminal_to_close()


def prepare() -> None:
    for directory in (EXPERT_DIR, TESTER_SETS, CONFIGS, TESTER_REPORTS, REPORTS, SETS):
        directory.mkdir(parents=True, exist_ok=True)
    for required in (TERMINAL, METAEDITOR, SOURCE, ANALYZER_PATH):
        if not required.is_file():
            raise FileNotFoundError(required)

    active_config = (
        Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal"
        / "D0E8209F77C8CF37AD8BF550E51FF075" / "config"
    )
    isolated_config = TESTER / "Config"
    isolated_config.mkdir(parents=True, exist_ok=True)
    for name in ("accounts.dat", "servers.dat", "common.ini"):
        source = active_config / name
        if source.is_file():
            shutil.copy2(source, isolated_config / name)

    shutil.copy2(SOURCE, EXPERT_DIR / SOURCE.name)
    compile_log = ROOT / "compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{compile_log}"'
    result = subprocess.run(command, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = compile_log.read_text(encoding="utf-16", errors="ignore") if compile_log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"EA compile failed (exit {result.returncode}). Read {compile_log}")
    shutil.copy2(EXPERT, ROOT / "EA" / EXPERT.name)


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def settings(asset_mode: int, magic: int) -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpAssetMode": asset_mode,
        "InpRiskPercent": 1.0,
        "InpAtrPeriod": 14,
        "InpEmergencyStopAtrMultiple": 2.0,
        "InpMaxDeviationPoints": 30,
        "InpMagic": magic,
        "InpUseAutomaticLiveServerOffset": True,
        "InpTesterServerUTCOffsetHours": 0,
        "InpManualLiveServerUTCOffsetHours": 0,
    }


def set_text(values: dict[str, object]) -> str:
    return "\n".join(f"{key}={render(value)}" for key, value in values.items()) + "\n"


def run_case(symbol: str, asset_mode: int, period: str, start: str, end: str,
             sequence: int, total_cases: int) -> dict:
    values = settings(asset_mode, 260909700 + sequence)
    signature = hashlib.sha256(
        json.dumps(values, sort_keys=True).encode() + SOURCE.read_bytes()
    ).hexdigest()[:8]
    case_id = f"{symbol.lower()}--raw-night-effect--{period}--{signature}"
    local_report = REPORTS / period / f"{case_id}.htm"
    if local_report.is_file():
        return {
            "symbol": symbol,
            "period": period,
            "config": values,
            "path": str(local_report),
            **ANALYZER.parse_report(local_report),
        }

    set_name = f"NightEffect--{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(values), encoding="utf-8")
    shutil.copy2(set_path, TESTER_SETS / set_name)
    tester_report = TESTER_REPORTS / f"{case_id}.htm"
    for stale in TESTER_REPORTS.glob(f"{case_id}*"):
        stale.unlink()

    ini = f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert={EXPERT_FOLDER}\\{EXPERT_NAME}
ExpertParameters={set_name}
Symbol={symbol}
Period=M15
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=1
ExecutionMode=1
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\night-effect-metals-20260909\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:02d}/{total_cases} {period:2s} {symbol}", flush=True)
    stop_stale_terminal()
    process = subprocess.Popen(
        f'"{TERMINAL}" /portable /config:"{ini_path}"',
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        process.wait(timeout=1200)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f"MT5 timed out: {case_id}")

    deadline = time.time() + 1200
    while not tester_report.is_file() and time.time() < deadline:
        time.sleep(0.25)
    if not tester_report.is_file():
        raise FileNotFoundError(f"Missing MT5 report: {tester_report}")
    local_report.parent.mkdir(parents=True, exist_ok=True)
    for artifact in TESTER_REPORTS.glob(f"{case_id}*"):
        shutil.copy2(artifact, local_report.parent / artifact.name)
    parsed = {
        "symbol": symbol,
        "period": period,
        "config": values,
        "path": str(local_report),
        **ANALYZER.parse_report(local_report),
    }
    print(
        f"DONE  {period:2s} {symbol:6s} return={parsed['return_pct']:+.2f}% "
        f"PF={parsed['profit_factor']:.2f} WR={parsed['win_rate_pct']:.2f}% "
        f"DD={parsed['max_drawdown_pct']:.2f}% trades={parsed['trades']}",
        flush=True,
    )
    return parsed


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def main() -> None:
    prepare()
    rows: list[dict] = []
    total_cases = len(ASSETS) * len(PERIODS)
    sequence = 0
    for period, start, end in PERIODS:
        for symbol, asset_mode in ASSETS:
            sequence += 1
            rows.append(run_case(symbol, asset_mode, period, start, end, sequence, total_cases))

    audit = {
        "strategy": "Precious-metals night effect - raw CFD clock transfer",
        "paper": "Ma, Bouri, Xu and Zhou, The night effect of intraday trading: Evidence from Chinese gold and silver futures markets, Global Finance Journal 64 (2025), 101084",
        "paper_url": "https://doi.org/10.1016/j.gfj.2025.101084",
        "working_paper_url": "https://acfr.aut.ac.nz/__data/assets/pdf_file/0008/686816/4a-Z-Ivy-Zhou.pdf",
        "raw_rule": {
            "signal": "Direction of 13:00-13:30 UTC, the direct clock conversion of SHFE 21:00-21:30 Beijing night interval 1.",
            "XAUUSD": "Trade the same direction during 01:00-01:30 UTC on the next trading day (SHFE day interval 1).",
            "XAGUSD": "Trade the same direction during 17:30-18:00 UTC on the signal date and 01:00-01:30, 03:00-03:30, 05:30-06:00 and 06:30-07:00 UTC on the next trading day (SHFE night 10 and day 1/5/6/8).",
        },
        "dates": "2021-09-01 through 2026-09-01, with nested 5y, 3y and 1y windows.",
        "assets": [symbol for symbol, _ in ASSETS],
        "risk": "1% equity at a 2x H1 ATR emergency stop; positions otherwise close at the paper's half-hour boundary. The EA skips a trade if the broker minimum lot would exceed 1%.",
        "costs": "Native MT5 Every Tick, broker spread, commission, swap and random execution delay.",
        "caveat": "This preserves the paper's Beijing clock and significant windows on continuous XAUUSD/XAGUSD CFDs; it does not claim the CFDs are SHFE futures.",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rows": [compact(row) for row in rows],
    }
    (ROOT / "raw-paper-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    with (ROOT / "raw-paper-results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["period", "symbol", "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor", "history_quality"])
        for row in rows:
            writer.writerow([
                row["period"], row["symbol"], row["return_pct"], row["profit_factor"],
                row["win_rate_pct"], row["max_drawdown_pct"], row["trades"],
                row["sharpe"], row["recovery_factor"], row["history_quality"],
            ])
    print(f"SAVED {ROOT / 'raw-paper-audit.json'}", flush=True)


if __name__ == "__main__":
    main()
