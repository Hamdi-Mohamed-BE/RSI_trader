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
SOURCE = ROOT / "EA" / "Calyx London Open FX Momentum EA.mq5"
EXPERT_FOLDER = "AAA Research\\London Open FX Momentum"
EXPERT_NAME = "Calyx London Open FX Momentum EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "London Open FX Momentum"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "london-open-fx-momentum-20260908"
TESTER_REPORTS = TESTER / "reports" / "london-open-fx-momentum-20260908"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("london_open_analyzer", ANALYZER_PATH)
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


def config(exit_hour: float, reverse: bool) -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpLondonOpenHour": 8.0,
        "InpFormationMinutes": 30,
        "InpExitLondonHour": exit_hour,
        "InpReverseSignal": reverse,
        "InpTradeMonday": True,
        "InpTradeTuesday": True,
        "InpTradeWednesday": True,
        "InpTradeThursday": True,
        "InpTradeFriday": True,
        "InpRiskPercent": 1.0,
        "InpAtrPeriod": 14,
        "InpEmergencyStopAtrMultiple": 10.0,
        "InpExitSecondsEarly": 30,
        "InpMaxDeviationBrokerPoints": 20,
        "InpMagic": 980908401,
        "InpUseAutomaticLiveServerOffset": True,
        "InpTesterServerClock": 0,
        "InpTesterManualUTCOffsetHours": 0,
        "InpManualLiveServerUTCOffsetHours": 0,
    }


def set_text(values: dict[str, object], magic: int) -> str:
    actual = {**values, "InpMagic": magic}
    return "\n".join(f"{key}={render(value)}" for key, value in actual.items()) + "\n"


def run_case(
    symbol: str,
    exit_hour: float,
    period: str,
    start: str,
    end: str,
    sequence: int,
) -> dict:
    reverse = symbol == "GBPUSD"
    values = config(exit_hour, reverse)
    signature_payload = json.dumps(values, sort_keys=True).encode() + SOURCE.read_bytes()
    signature = hashlib.sha256(signature_payload).hexdigest()[:8]
    exit_label = str(exit_hour).replace(".", "-")
    case_id = f"{symbol.lower()}--exit-{exit_label}--{period}--{signature}"
    local_report = REPORTS / period / f"{case_id}.htm"
    if local_report.is_file():
        return {
            "symbol": symbol,
            "exit_london": exit_hour,
            "direction": "reverse" if reverse else "momentum",
            "period": period,
            "config": values,
            "path": str(local_report),
            **ANALYZER.parse_report(local_report),
        }

    set_name = f"Calyx-LondonOpen--{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(values, 980908400 + sequence), encoding="utf-8")
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
Report=reports\\london-open-fx-momentum-20260908\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(
        f"START {sequence:02d} {period:2s} {symbol:6s} "
        f"exit={exit_hour:04.1f} {'reverse' if reverse else 'momentum'}",
        flush=True,
    )
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
        "exit_london": exit_hour,
        "direction": "reverse" if reverse else "momentum",
        "period": period,
        "config": values,
        "path": str(local_report),
        **ANALYZER.parse_report(local_report),
    }
    print(
        f"DONE  {period:2s} {symbol:6s} exit={exit_hour:04.1f} "
        f"return={parsed['return_pct']:+.2f}% PF={parsed['profit_factor']:.2f} "
        f"WR={parsed['win_rate_pct']:.2f}% DD={parsed['max_drawdown_pct']:.2f}% "
        f"trades={parsed['trades']}",
        flush=True,
    )
    time.sleep(2)
    return parsed


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def result_line(row: dict) -> str:
    return (
        f"| {row['period']} | {row['symbol']} | {row['direction']} | "
        f"{row['exit_london']:04.1f} | {row['return_pct']:+.2f}% | "
        f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | "
        f"{row['max_drawdown_pct']:.2f}% | {row['trades']} | "
        f"{row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
    )


def write_report(rows: list[dict]) -> None:
    lines = [
        "# London Open FX Momentum - raw paper reproduction",
        "",
        "## Rule implemented",
        "",
        "- Observe the first 30 minutes after the 08:00 Europe/London open.",
        "- Enter at 08:30 in the sign of that return.",
        "- Reverse the direction for GBPUSD, as reported by the paper.",
        "- Exit at the stated Europe/London time. No profit target, trailing stop, breakeven, or indicator filter.",
        "- Risk is 1% of current equity at a 10x M15 ATR catastrophic stop. This stop is operational protection because the paper uses a time exit and publishes no stop.",
        "- MT5 1-minute OHLC screening includes the recorded Exness spread, commission, swap, and random execution delay.",
        "",
        "## Reproducibility limitation",
        "",
        "The paper states that the intraday exit was selected on 2012-2018 data but does not publish the selected exit time or its candidate grid. Therefore 16:00, 16:30, and 17:00 London are reported side-by-side and none is silently presented as the author's undisclosed choice.",
        "",
        "## Results",
        "",
        "| Period | Symbol | Direction | Exit London | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(result_line(row) for row in rows)
    lines += [
        "",
        "## Scope",
        "",
        "Raw research only. The active portfolio, website, recommended installer, and BAT files are unchanged pending user review.",
    ]
    (ROOT / "RAW RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    prepare()
    symbols = ("USDJPY", "GBPJPY", "GBPUSD", "EURUSD")
    exits = (16.0, 16.5, 17.0)
    periods = (
        ("3y", "2023.09.01", "2026.09.01"),
        ("1y", "2025.09.01", "2026.09.01"),
    )
    rows: list[dict] = []
    sequence = 0
    for period, start, end in periods:
        for symbol in symbols:
            for exit_hour in exits:
                sequence += 1
                rows.append(run_case(symbol, exit_hour, period, start, end, sequence))

    audit = {
        "strategy": "London Open 30-minute FX momentum",
        "paper": "Seeck (2026), Intraday Momentum in Spot FX and Currency Futures",
        "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7008318",
        "paper_sample": "Dukascopy M5, 2012-2024; IS 2012-2018, OOS 2019-2024",
        "tested_symbols": list(symbols),
        "raw_rule": "Sign of 08:00-08:30 Europe/London return; enter 08:30; GBPUSD reversed; time exit.",
        "exit_disclosure_gap": "The paper does not publish the selected exit time or candidate grid; 16:00, 16:30, and 17:00 London are shown separately.",
        "risk": "1% dynamic equity at a 10x M15 ATR catastrophic stop; no TP, trailing, breakeven, filters, or optimization.",
        "costs": "MT5 1-minute OHLC screening with recorded Exness spread, commission, swap, and random execution delay.",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "active_system_changed": False,
        "rows": [compact(row) for row in rows],
    }
    (ROOT / "raw-paper-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    with (ROOT / "raw-paper-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "period", "symbol", "direction", "exit_london", "return_pct",
            "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades",
            "sharpe", "recovery_factor", "history_quality",
        ])
        for row in rows:
            writer.writerow([
                row["period"], row["symbol"], row["direction"], row["exit_london"],
                row["return_pct"], row["profit_factor"], row["win_rate_pct"],
                row["max_drawdown_pct"], row["trades"], row["sharpe"],
                row["recovery_factor"], row["history_quality"],
            ])
    write_report(rows)
    print(json.dumps({"cases": sequence, "rows": [compact(row) for row in rows]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
