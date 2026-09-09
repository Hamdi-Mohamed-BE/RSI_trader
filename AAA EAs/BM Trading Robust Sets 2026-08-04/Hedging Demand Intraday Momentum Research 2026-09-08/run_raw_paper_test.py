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
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
TERMINAL = TESTER / "terminal64.exe"
METAEDITOR = TESTER / "MetaEditor64.exe"
SOURCE = ROOT / "EA" / "Calyx Last 30 Minute Momentum EA.mq5"
EXPERT_FOLDER = "AAA Research\\Hedging Demand Intraday Momentum"
EXPERT_NAME = "Calyx Last 30 Minute Momentum EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "Hedging Demand Intraday Momentum"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "hedging-demand-intraday-momentum-20260908"
TESTER_REPORTS = TESTER / "reports" / "hedging-demand-intraday-momentum-20260908"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("intraday_momentum_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the native MT5 report analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


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
    log = ROOT / "compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{log}"'
    result = subprocess.run(command, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = log.read_text(encoding="utf-16", errors="ignore") if log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"EA compile failed (exit {result.returncode}). Read {log}")
    shutil.copy2(EXPERT, ROOT / "EA" / EXPERT.name)


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def config(
    signal: int,
    cash_open: float = 9.5,
    signal_hour: float = 15.5,
    cash_close: float = 16.0,
    trade_monday: bool = True,
    trade_friday: bool = True,
) -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpSignal": signal,
        "InpCashOpenNyHour": cash_open,
        "InpSignalNyHour": signal_hour,
        "InpCashCloseNyHour": cash_close,
        "InpFirstHalfMinutes": 30,
        "InpTradeMonday": trade_monday,
        "InpTradeTuesday": True,
        "InpTradeWednesday": True,
        "InpTradeThursday": True,
        "InpTradeFriday": trade_friday,
        "InpRiskPercent": 1.0,
        "InpAtrPeriod": 14,
        "InpEmergencyStopAtrMultiple": 10.0,
        "InpExitSecondsBeforeClose": 30,
        "InpMaxDeviationBrokerPoints": 30,
        "InpMagic": 980908301,
        "InpUseAutomaticLiveServerOffset": True,
        "InpTesterServerClock": 0,
        "InpTesterManualUTCOffsetHours": 0,
        "InpManualLiveServerUTCOffsetHours": 0,
    }


def set_text(values: dict[str, object], magic: int) -> str:
    actual = {**values, "InpMagic": magic}
    return "\n".join(f"{key}={render(value)}" for key, value in actual.items()) + "\n"


def run_case(
    label: str,
    signal: int,
    period: str,
    start: str,
    end: str,
    sequence: int,
    *,
    symbol: str = "USTEC",
    cash_open: float = 9.5,
    signal_hour: float = 15.5,
    cash_close: float = 16.0,
    trade_monday: bool = True,
    trade_friday: bool = True,
) -> dict:
    values = config(signal, cash_open, signal_hour, cash_close, trade_monday, trade_friday)
    signature_payload = json.dumps(values, sort_keys=True).encode() + SOURCE.read_bytes()
    signature = hashlib.sha256(signature_payload).hexdigest()[:8]
    case_id = f"{symbol.lower()}--{label}--{period}--{signature}"
    local_report = REPORTS / period / f"{case_id}.htm"
    if local_report.is_file():
        return {
            "variant": label,
            "period": period,
            "config": values,
            "path": str(local_report),
            **ANALYZER.parse_report(local_report),
        }

    set_name = f"Calyx-Last30--{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(values, 980908300 + sequence), encoding="utf-8")
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
Report=reports\\hedging-demand-intraday-momentum-20260908\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:02d} {period:4s} {label}", flush=True)
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
        "variant": label,
        "period": period,
        "config": values,
        "path": str(local_report),
        **ANALYZER.parse_report(local_report),
    }
    print(
        f"DONE  {period:4s} {label:12s} return={parsed['return_pct']:+.2f}% "
        f"PF={parsed['profit_factor']:.2f} WR={parsed['win_rate_pct']:.2f}% "
        f"DD={parsed['max_drawdown_pct']:.2f}% trades={parsed['trades']}",
        flush=True,
    )
    time.sleep(2)
    return parsed


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def main() -> None:
    prepare()
    variants = [("ROD-main", 0), ("ONFH", 1), ("agreement", 2)]
    periods = [
        ("3y", "2023.09.01", "2026.09.01"),
        ("1y", "2025.09.01", "2026.09.01"),
    ]
    rows: list[dict] = []
    sequence = 0
    for period, start, end in periods:
        for label, signal in variants:
            sequence += 1
            rows.append(run_case(label, signal, period, start, end, sequence))

    audit = {
        "strategy": "Last-30-Minute Hedging Momentum",
        "paper": "Baltussen, Da, Lammers and Martens (2021), Journal of Financial Economics",
        "paper_url": "https://academicweb.nd.edu/~zda/intramom.pdf",
        "instrument": "USTEC (US100 CFD)",
        "raw_rule": "At 15:30 New York, trade in the sign of the return from the prior 16:00 close; exit at 16:00.",
        "paper_comparators": {
            "ONFH": "Use the sign of prior close to 10:00 New York.",
            "agreement": "Trade only when ROD and ONFH signs agree.",
        },
        "risk": "1% equity at a 10x M15 ATR catastrophic stop; no TP, trailing, breakeven, filters, or optimization.",
        "costs": "Native MT5 Every Tick, broker spread, commission, swap and random execution delay.",
        "execution_caveat": "The Exness USTEC contract reports the market closed at 15:30 New York on Mondays, so executable raw results contain Tuesday-Friday trades only.",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rows": [compact(row) for row in rows],
    }
    (ROOT / "raw-paper-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    with (ROOT / "raw-paper-results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["period", "variant", "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor"])
        for row in rows:
            writer.writerow([
                row["period"], row["variant"], row["return_pct"], row["profit_factor"],
                row["win_rate_pct"], row["max_drawdown_pct"], row["trades"],
                row["sharpe"], row["recovery_factor"],
            ])
    print(f"SAVED {ROOT / 'raw-paper-audit.json'}", flush=True)


if __name__ == "__main__":
    main()
