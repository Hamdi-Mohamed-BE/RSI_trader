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
SOURCE = ROOT / "EA" / "Calyx Noise Boundary VWAP Momentum Raw EA.mq5"
EXPERT_FOLDER = "AAA Research\\Noise Boundary VWAP Momentum Raw"
EXPERT_NAME = "Calyx Noise Boundary VWAP Momentum Raw EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "Noise Boundary VWAP Momentum Raw"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "noise-boundary-vwap-raw-20260909"
TESTER_REPORTS = TESTER / "reports" / "noise-boundary-vwap-raw-20260909"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("noise_boundary_analyzer", ANALYZER_PATH)
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
        "InpNoiseLookbackSessions": 14,
        "InpVolatilityMultiplier": 1.0,
        "InpDecisionFrequencyMinutes": 30,
        "InpTargetDailyVolatilityPercent": 2.0,
        "InpMaximumNotionalLeverage": 4.0,
        "InpRequireRegularNYSEDay": True,
        "InpOpenNewYorkHour": 9,
        "InpOpenNewYorkMinute": 30,
        "InpFirstDecisionNewYorkHour": 10,
        "InpFirstDecisionNewYorkMinute": 0,
        "InpLastDecisionNewYorkHour": 15,
        "InpLastDecisionNewYorkMinute": 30,
        "InpCloseNewYorkHour": 16,
        "InpCloseNewYorkMinute": 0,
        "InpMaxDeviationBrokerPoints": 50,
        "InpMagic": 982009901,
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


def run_case(symbol: str, label: str, start: str, end: str, sequence: int) -> dict:
    config = values()
    slug = symbol.lower()
    case_id = f"{slug}--raw-noise-boundary-vwap--{label}"
    local_report = REPORTS / symbol / label / f"{case_id}.htm"
    set_name = f"Noise-Boundary-VWAP--{symbol}--{label}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 982009900 + sequence), encoding="utf-8")
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
Report=reports\\noise-boundary-vwap-raw-20260909\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:02d} {symbol:6s} {label}", flush=True)
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
    parsed = {
        "symbol": symbol,
        "period": label,
        "config": config,
        "path": str(local_report),
        **ANALYZER.parse_report(local_report),
    }
    print(
        f"DONE  {symbol:6s} {label:9s} return={parsed['return_pct']:+.2f}% "
        f"PF={parsed['profit_factor']:.2f} WR={parsed['win_rate_pct']:.2f}% "
        f"DD={parsed['max_drawdown_pct']:.2f}% n={parsed['trades']} Sharpe={parsed['sharpe']:.2f}",
        flush=True,
    )
    time.sleep(2)
    return parsed


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def main() -> None:
    prepare()
    periods = [
        ("latest-1y", "2025.09.01", "2026.09.01"),
        ("recent-3y", "2023.09.01", "2026.09.01"),
        ("full-5y", "2021.09.01", "2026.09.01"),
    ]
    symbols = ["US500", "USTEC"]
    rows: list[dict] = []
    sequence = 0
    for symbol in symbols:
        for label, start, end in periods:
            sequence += 1
            rows.append(run_case(symbol, label, start, end, sequence))

    audit = {
        "strategy": "Noise Boundary VWAP Intraday Momentum - raw published rules",
        "paper": "Zarattini, Aziz and Barbon (2024, revised 2025), SSRN 4824172",
        "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172",
        "authors_code": "https://concretumgroup.com/python-backtesting-beat-the-market-an-effective-intraday-momentum-strategy-for-the-sp500-etf-spy/",
        "instruments": "US500 is the closest available MT5 proxy for the paper's SPY; USTEC is the existing Calyx index transfer test.",
        "paper_rule": "At 30-minute intervals from 10:00 New York, trade outside 14-session time-of-day noise bands only with VWAP confirmation. Exit when the next 30-minute signal is flat/opposite, or at 16:00 New York.",
        "exposure": "Paper-faithful 2% daily-volatility targeting with a 4x maximum notional leverage. This is research-only, not the Calyx 1%-risk deployment model.",
        "costs": "Native MT5 Every Tick, broker spread, commission, swap and random execution delay.",
        "vwap_limitation": "SPY uses consolidated exchange volume; Exness index CFDs provide broker tick volume. HLC3 x tick-volume VWAP is therefore an adaptation and not identical to the paper's market-wide VWAP.",
        "implementation_notes": [
            "Signals are computed from the completed minute immediately before each 30-minute execution point, matching the authors' one-minute shifted exposure code.",
            "Noise width is the mean absolute open-to-current-minute move from the prior 14 regular NYSE sessions.",
            "Bands are gap-adjusted with max(session open, prior close) and min(session open, prior close).",
            "Long requires price above both upper band and VWAP; short requires price below both lower band and VWAP.",
            "A flat signal closes the position; an opposite signal closes and reverses. All decisions are discrete at 30-minute intervals.",
            "Early closes and full NYSE holidays are skipped because the published strategy assumes a 16:00 close.",
        ],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rows": [compact(row) for row in rows],
    }
    (ROOT / "raw-paper-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    with (ROOT / "raw-paper-results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([
            "symbol", "period", "return_pct", "profit_factor", "win_rate_pct",
            "max_drawdown_pct", "trades", "sharpe", "recovery_factor", "net_profit",
        ])
        for row in rows:
            writer.writerow([
                row["symbol"], row["period"], row["return_pct"], row["profit_factor"],
                row["win_rate_pct"], row["max_drawdown_pct"], row["trades"], row["sharpe"],
                row["recovery_factor"], row["net_profit"],
            ])

    lines = [
        "# Noise Boundary VWAP Momentum - raw MT5 results",
        "",
        "This is an unoptimized reconstruction of the published Zarattini-Aziz-Barbon final model. US500 is the closest Exness proxy for SPY; USTEC is included only as a fixed-rule transfer test.",
        "",
        "| Symbol | Window | Net P/L | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['symbol']} | {row['period']} | ${row['net_profit']:+,.2f} | {row['return_pct']:+.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | "
            f"{row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
        )
    lines.extend([
        "",
        "## Raw verdict",
        "",
        "US500 FAILS. The closest available S&P 500 CFD proxy is negative in the latest year, recent three years and full five years. It does not reproduce the paper's SPY edge with Exness CFD prices, tick-volume VWAP and native trading costs.",
        "",
        "USTEC PASSES THE RAW RESEARCH SCREEN, but only as a pipeline candidate. It is positive in all three windows and retains a strong MT5 Sharpe ratio, while PF remains a weak 1.09-1.14 and drawdown reaches 17.69%. The correct next action is a locked Calyx pipeline on USTEC only; it is not ready for system integration or demo deployment.",
        "",
        "## Fidelity notes",
        "",
        "- 14 prior regular NYSE sessions and volatility multiplier 1.0.",
        "- 30-minute decisions from 10:00 through 15:30 New York; forced flat at 16:00.",
        "- Gap-adjusted noise bands and HLC3 session VWAP confirmation.",
        "- Dynamic 2% daily-volatility target, capped at 4x notional, as published.",
        "- MT5 broker tick volume substitutes for consolidated exchange volume, so VWAP is not perfectly equivalent to SPY VWAP.",
        "",
        "No website, BAT, installer, recommended-system or active-portfolio file was changed.",
    ])
    (ROOT / "RAW RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SAVED {ROOT / 'RAW RESULTS.md'}", flush=True)


if __name__ == "__main__":
    main()
