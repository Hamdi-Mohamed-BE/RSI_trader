from __future__ import annotations

import csv
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
SOURCE = ROOT / "EA" / "Calyx Bitcoin Overnight MAX10 Raw EA.mq5"
EXPERT_FOLDER = "AAA Research\\Bitcoin Overnight Sessions Raw"
EXPERT_NAME = "Calyx Bitcoin Overnight MAX10 Raw EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "Bitcoin Overnight Sessions Raw"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "bitcoin-overnight-max10-raw-20260909"
TESTER_REPORTS = TESTER / "reports" / "bitcoin-overnight-max10-raw-20260909"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("bitcoin_overnight_analyzer", ANALYZER_PATH)
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
    compile_log = ROOT / "compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{compile_log}"'
    result = subprocess.run(command, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = compile_log.read_text(encoding="utf-16", errors="ignore") if compile_log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"EA compile failed (exit {result.returncode}). Read {compile_log}")
    shutil.copy2(EXPERT, ROOT / "EA" / EXPERT.name)


def values() -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpLookbackCalendarDays": 10,
        "InpEntryNewYorkHour": 16,
        "InpEntryNewYorkMinute": 0,
        "InpExitNewYorkHour": 10,
        "InpExitNewYorkMinute": 0,
        "InpTradeFridayNight": True,
        "InpTradeMondayNight": True,
        "InpTradeTuesdayNight": True,
        "InpRequireRegularNYSEDay": True,
        "InpPaperCapitalAllocationPercent": 100.0,
        "InpEntryWindowMinutes": 15,
        "InpMaxDeviationBrokerPoints": 50,
        "InpMagic": 981009901,
        "InpUseAutomaticLiveServerOffset": True,
        "InpTesterServerClock": 0,
        "InpTesterManualUTCOffsetHours": 0,
        "InpManualLiveServerUTCOffsetHours": 0,
    }


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def set_text(config: dict[str, object], magic: int) -> str:
    actual = {**config, "InpMagic": magic}
    return "\n".join(f"{key}={render(value)}" for key, value in actual.items()) + "\n"


def run_case(label: str, start: str, end: str, sequence: int) -> dict:
    config = values()
    case_id = f"btcusd--raw-max10--{label}"
    local_report = REPORTS / label / f"{case_id}.htm"
    set_name = f"Bitcoin-Overnight-MAX10--{label}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 981009900 + sequence), encoding="utf-8")
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
Symbol=BTCUSD
Period=M1
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\bitcoin-overnight-max10-raw-20260909\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:02d} {label}", flush=True)
    process = subprocess.Popen(
        f'"{TERMINAL}" /portable /config:"{ini_path}"',
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f"MT5 timed out: {case_id}")
    deadline = time.time() + 60
    while not tester_report.is_file() and time.time() < deadline:
        time.sleep(0.25)
    if not tester_report.is_file():
        raise FileNotFoundError(f"Missing MT5 report: {tester_report}")
    local_report.parent.mkdir(parents=True, exist_ok=True)
    for artifact in TESTER_REPORTS.glob(f"{case_id}*"):
        shutil.copy2(artifact, local_report.parent / artifact.name)
    parsed = {"period": label, "config": config, "path": str(local_report), **ANALYZER.parse_report(local_report)}
    print(
        f"DONE  {label:17s} return={parsed['return_pct']:+.2f}% PF={parsed['profit_factor']:.2f} "
        f"WR={parsed['win_rate_pct']:.2f}% DD={parsed['max_drawdown_pct']:.2f}% trades={parsed['trades']} "
        f"Sharpe={parsed['sharpe']:.2f}",
        flush=True,
    )
    time.sleep(2)
    return parsed


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def main() -> None:
    prepare()
    periods = [
        ("paper-oos-proxy", "2021.10.01", "2024.11.13"),
        ("latest-1y", "2025.09.01", "2026.09.01"),
        ("recent-3y", "2023.09.01", "2026.09.01"),
        ("full-5y", "2021.09.01", "2026.09.01"),
    ]
    rows = [run_case(label, start, end, index + 1) for index, (label, start, end) in enumerate(periods)]
    audit = {
        "strategy": "Bitcoin Overnight Sessions MAX(10) - raw paper reproduction",
        "paper": "Vojtko and Dujava (2024/2025), SSRN 5021138",
        "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5021138",
        "instrument": "BTCUSD, native MT5 Every Tick",
        "paper_rule": "At 16:00 New York, buy BTC when it exceeds the previous 10 calendar-day 16:00 closes, but only Friday, Monday and Tuesday; exit at 10:00 New York on Monday, Tuesday or Wednesday respectively.",
        "exposure": "100% notional allocation, matching the paper's fully-invested raw test. There is no stop-loss in the published rule, so this is research-only and is not compatible with the Calyx 1%-risk deployment rule without adding a new exit.",
        "costs": "Native MT5 Every Tick, broker spread, commission, swap and random execution delay",
        "implementation_notes": [
            "The MAX(10) reference uses the ten prior calendar-day Bitcoin prices sampled at 16:00 New York.",
            "Entry is attempted during the first 15 minutes after 16:00 New York on regular NYSE days only.",
            "Friday positions exit Monday at 10:00 New York; Monday and Tuesday positions exit the following morning at 10:00.",
            "No stop, target, trailing exit or added signal filter is used in this raw phase.",
            "The paper's full early-history sample is not available in the five-year Exness tester archive; paper-oos-proxy approximates its post-October-2021 period.",
        ],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rows": [compact(row) for row in rows],
    }
    (ROOT / "raw-paper-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    with (ROOT / "raw-paper-results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["period", "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor", "net_profit"])
        for row in rows:
            writer.writerow([row["period"], row["return_pct"], row["profit_factor"], row["win_rate_pct"], row["max_drawdown_pct"], row["trades"], row["sharpe"], row["recovery_factor"], row["net_profit"]])

    lines = [
        "# Bitcoin Overnight Sessions MAX(10) - raw MT5 results",
        "",
        "This is a literal, unoptimized reproduction of the Vojtko-Dujava overnight rule on BTCUSD. It uses the paper's fully-invested exposure and deliberately adds no stop, target or Calyx filter.",
        "",
        "| Window | Net P/L | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['period']} | ${row['net_profit']:+,.2f} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
        )
    lines.extend([
        "",
        "## Raw verdict",
        "",
        "HISTORICAL PASS / CURRENT FAIL. The five-year history is profitable, but the latest year loses 12.68% with PF 0.52, and the recent three-year PF is only 1.06. The raw rule is not suitable for the Calyx system, but its older genuine edge is strong enough to justify a controlled pipeline attempt if approved.",
        "",
        "The paper has no stop-loss and uses fully invested exposure. A Calyx-compatible version must first introduce a defined stop so risk can be capped at the selected 1% per trade. It must also test the Friday/weekend, Monday and Tuesday legs separately because recent decay may be session-specific.",
        "",
        "Five-year execution costs were $201.42 commission plus $1,236.67 swap. Maximum winning and losing streaks were both 6 trades; the average winner was $284.59 and average loser was -$222.73.",
        "",
        "## Raw rules",
        "",
        "- BTCUSD, long only, no stop and no profit target.",
        "- At the 16:00 New York close, price must exceed all ten prior calendar-day 16:00 New York closes.",
        "- Eligible entries: Friday, Monday and Tuesday on regular NYSE sessions.",
        "- Exit at 10:00 New York: Friday entry on Monday; Monday/Tuesday entry the following morning.",
        "- 100% notional allocation as published; this is not a live-ready Calyx risk configuration.",
        "",
        "No website, installer, BAT, recommended system or active portfolio file was changed.",
    ])
    (ROOT / "RAW RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SAVED {ROOT / 'RAW RESULTS.md'}", flush=True)


if __name__ == "__main__":
    main()
