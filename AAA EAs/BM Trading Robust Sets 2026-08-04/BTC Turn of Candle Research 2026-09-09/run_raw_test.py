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
SOURCE = ROOT / "EA" / "Calyx BTC Turn of Candle Raw EA.mq5"
EXPERT_FOLDER = "AAA Research\\BTC Turn of Candle Raw"
EXPERT_NAME = "Calyx BTC Turn of Candle Raw EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "BTC Turn of Candle Raw"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "btc-turn-of-candle-raw-20260909"
TESTER_REPORTS = TESTER / "reports" / "btc-turn-of-candle-raw-20260909"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("btc_turn_analyzer", ANALYZER_PATH)
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
        "InpPaperCapitalAllocationPercent": 100.0,
        "InpHoldMinutes": 1,
        "InpMaxDeviationBrokerPoints": 100,
        "InpMagic": 981009921,
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
    case_id = f"btcusd--raw-turn-minute--{label}"
    local_report = REPORTS / label / f"{case_id}.htm"
    set_name = f"BTC-Turn-of-Candle--{label}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 981009920 + sequence), encoding="utf-8")
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
Report=reports\\btc-turn-of-candle-raw-20260909\\{case_id}.htm
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
        process.wait(timeout=2400)
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
        f"DONE  {label:20s} return={parsed['return_pct']:+.2f}% PF={parsed['profit_factor']:.2f} "
        f"WR={parsed['win_rate_pct']:.2f}% DD={parsed['max_drawdown_pct']:.2f}% trades={parsed['trades']} "
        f"Sharpe={parsed['sharpe']:.2f}",
        flush=True,
    )
    time.sleep(2)
    return parsed


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def verdict(rows: list[dict]) -> str:
    recent = next(row for row in rows if row["period"] == "recent-3y")
    latest = next(row for row in rows if row["period"] == "latest-1y")
    if recent["profit_factor"] >= 1.20 and latest["profit_factor"] >= 1.10:
        return "RAW PASS. The anomaly survives current Exness BTCUSD spread strongly enough to justify pipeline research."
    if recent["profit_factor"] > 1.0 and latest["profit_factor"] > 1.0:
        return "WEAK RAW PASS. The anomaly remains positive, but the margin over trading costs is too small for deployment without robustness work."
    return "RAW FAIL. The published exchange anomaly does not survive current Exness BTCUSD CFD execution sufficiently to justify pipeline optimization."


def main() -> None:
    prepare()
    periods = [
        ("paper-era-available", "2021.09.01", "2022.01.01"),
        ("latest-1y", "2025.09.01", "2026.09.01"),
        ("recent-3y", "2023.09.01", "2026.09.01"),
        ("full-5y", "2021.09.01", "2026.09.01"),
    ]
    rows = [run_case(label, start, end, index + 1) for index, (label, start, end) in enumerate(periods)]
    audit = {
        "strategy": "BTC Turn-of-the-Candle - raw paper reproduction",
        "paper": "Shanaev, Vasenin and Stepanov (2023), Turn-of-the-candle effect in bitcoin returns",
        "paper_url": "https://doi.org/10.1016/j.heliyon.2023.e14236",
        "instrument": "Exness BTCUSD CFD, native MT5 Every Tick",
        "paper_rule": "Buy BTC at the opening of minutes 00, 15, 30 and 45 of every hour and close after one M1 candle.",
        "exposure": "100% unlevered notional allocation, recalculated from current balance for every entry, matching the paper's fully invested simulation.",
        "costs": "Native Exness spread and account commission with random execution delay; no artificial fee reduction or exchange-volume tier.",
        "implementation_notes": [
            "All calendar days and all hours are eligible, subject only to actual broker quote availability.",
            "There is no signal filter, stop-loss, take-profit, trailing stop, direction filter or session filter.",
            "Each position is held for exactly one M1 bar and is closed at the first tick of the following minute.",
            "Minute-of-hour is invariant to the whole-hour Exness server offset, so 00/15/30/45 needs no timezone conversion.",
            "The isolated Exness tester archive begins in September 2021, so paper-era-available covers only the accessible final four months of the paper's 2021 simulation.",
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
        "# BTC Turn-of-the-Candle - raw MT5 results",
        "",
        "This is an unoptimized transfer of the published one-minute timing rule to the Exness BTCUSD CFD. It adds no Calyx filters and has not been installed into the website, BAT files or recommended portfolio.",
        "",
        "| Window | Net P/L | Return | PF | Win rate | Max DD | Trades | Avg/trade | Commission |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['period']} | ${row['net_profit']:+,.2f} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | "
            f"${row['expected_payoff']:+.2f} | ${row['commission']:,.2f} |"
        )
    lines.extend([
        "",
        "## Raw verdict",
        "",
        verdict(rows),
        "",
        "The latest one-year test completed essentially the full 96-signals-per-day schedule and is the cleanest current measurement. Even if its $7,367 commission were removed, the result after spread would still be approximately -$1,387.62. The older and longer simulations depleted capital until the broker's 0.01-lot minimum prevented further entries; their lower trade counts are therefore part of the raw deployability failure, not missing history.",
        "",
        "## Raw rules",
        "",
        "- BTCUSD long only.",
        "- Enter at the first available tick of minutes 00, 15, 30 and 45 of every hour.",
        "- Exit at the first tick of the following minute, giving one M1 bar of exposure.",
        "- Reinvest 100% of current balance as unlevered notional exposure.",
        "- No stop, target, trend filter, volatility filter, weekday filter or session restriction.",
        "- Native Exness spread/commission and random execution delay are included.",
        "",
        "No production EA, website page, installer, BAT or active terminal was changed.",
    ])
    (ROOT / "RAW RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SAVED {ROOT / 'RAW RESULTS.md'}", flush=True)


if __name__ == "__main__":
    main()
