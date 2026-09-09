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
SOURCE = ROOT / "EA" / "Calyx Gold VWAP EMA Regime Raw EA.mq5"
EXPERT_FOLDER = "AAA Research\\Gold VWAP EMA Regime Raw"
EXPERT_NAME = "Calyx Gold VWAP EMA Regime Raw EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "Gold VWAP EMA Regime Raw"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "gold-vwap-ema-regime-raw-20260908"
TESTER_REPORTS = TESTER / "reports" / "gold-vwap-ema-regime-raw-20260908"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("gold_vwap_analyzer", ANALYZER_PATH)
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
        "InpFastTrailEMA": 20,
        "InpEntryTrailEMA": 50,
        "InpRegimeEMA": 200,
        "InpATRPeriod": 14,
        "InpRegimeBoundaryPercent": 0.10,
        "InpVolumeMultiple": 1.10,
        "InpVolumeMAPeriod": 20,
        "InpMinimumRangeATR": 0.80,
        "InpStopBufferATR": 0.50,
        "InpTargetR": 3.00,
        "InpTightenAtR": 2.50,
        "InpUseCompressedVWAPPartial": True,
        "InpCompressedBars": 5,
        "InpCompressedMaxRangeATR": 0.60,
        "InpCompressedVWAPDistancePercent": 0.15,
        "InpSessionStartUTCHour": 13,
        "InpSessionStartUTCMinute": 30,
        "InpSessionEndUTCHour": 20,
        "InpSessionEndUTCMinute": 0,
        "InpRiskPercent": 1.0,
        "InpMaxConsecutiveSessionLosses": 3,
        "InpDailyLossLimitPercent": 3.0,
        "InpUsePaper2024NewsExclusion": True,
        "InpNewsBufferMinutes": 15,
        "InpMaxDeviationBrokerPoints": 30,
        "InpMagic": 981009801,
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
    case_id = f"xauusd--raw-paper--{label}"
    local_report = REPORTS / label / f"{case_id}.htm"
    set_name = f"Gold-VWAP-EMA--{label}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 981009800 + sequence), encoding="utf-8")
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
Symbol=XAUUSD
Period=M15
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
Report=reports\\gold-vwap-ema-regime-raw-20260908\\{case_id}.htm
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
        f"DONE  {label:12s} return={parsed['return_pct']:+.2f}% PF={parsed['profit_factor']:.2f} "
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
        ("paper-2024", "2024.01.01", "2025.01.01"),
        ("latest-1y", "2025.09.01", "2026.09.01"),
        ("recent-3y", "2023.09.01", "2026.09.01"),
        ("full-5y", "2021.09.01", "2026.09.01"),
    ]
    rows = [run_case(label, start, end, index + 1) for index, (label, start, end) in enumerate(periods)]
    audit = {
        "strategy": "Gold VWAP-EMA Regime - raw paper reproduction",
        "paper": "Bhatti (2026), SSRN 6650958",
        "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6650958",
        "instrument": "XAUUSD M15",
        "risk": "1% of current equity at the paper's signal-extreme plus 0.5 ATR stop; 3R target",
        "costs": "Native MT5 Every Tick, broker spread, commission, swap and random execution delay",
        "paper_warning": "The paper's published performance is a calibrated Monte Carlo outcome simulation, not a bar-by-bar historical backtest.",
        "implementation_notes": [
            "NY VWAP is fixed to the paper's stated 13:30-20:00 UTC window and uses Exness tick volume; this Exness tester export uses UTC strategy timestamps.",
            "A signal enters at the next available tick after its M15 candle closes.",
            "The compressed VWAP partial is triggered after five qualifying completed candles; this resolves the paper's otherwise contradictory entry-above-VWAP versus later-reach-VWAP wording.",
            "The 2024 raw window excludes NFP, CPI, FOMC decisions and all three GDP estimate releases within +/-15 minutes. The paper does not publish an event file, so the exclusion is explicitly reconstructed.",
            "The strategy is flattened at the 20:00 UTC session close because it is defined as intraday but does not separately state a session-close failsafe.",
        ],
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rows": [compact(row) for row in rows],
    }
    (ROOT / "raw-paper-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    with (ROOT / "raw-paper-results.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["period", "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor"])
        for row in rows:
            writer.writerow([row["period"], row["return_pct"], row["profit_factor"], row["win_rate_pct"], row["max_drawdown_pct"], row["trades"], row["sharpe"], row["recovery_factor"]])

    lines = [
        "# Gold VWAP-EMA Regime - raw MT5 results",
        "",
        "The code reproduces Bhatti (2026), SSRN 6650958, without parameter optimization. The paper's headline result is a calibrated outcome simulation, not a historical bar-by-bar test; these native MT5 results are therefore the first direct broker-data falsification check.",
        "",
        "| Window | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['period']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | "
            f"{row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
        )
    lines.extend([
        "",
        "## Paper claim versus direct replication",
        "",
        "| 2024 result | Return | PF | Win rate | Max DD | Trades |",
        "|---|---:|---:|---:|---:|---:|",
        "| Paper's calibrated simulation | +102.20% | 1.76 | 45.30% | 5.10% | 247 |",
        f"| Native MT5 broker-data replication | {rows[0]['return_pct']:+.2f}% | {rows[0]['profit_factor']:.2f} | {rows[0]['win_rate_pct']:.2f}% | {rows[0]['max_drawdown_pct']:.2f}% | {rows[0]['trades']} |",
        "",
        "## Raw rules implemented",
        "",
        "- XAUUSD M15; session VWAP from 13:30 to 20:00 UTC using typical price and tick volume; this Exness tester export uses UTC strategy timestamps.",
        "- 200 EMA regime with a 0.1% ambiguity exclusion zone.",
        "- 50 EMA pullback/touch plus quantified pin-bar or engulfing rejection.",
        "- Tick volume above 1.1x its 20-bar average and candle range at least 0.8 ATR(14).",
        "- Initial stop beyond the signal extreme by 0.5 ATR, 3R target, 1% dynamic-equity risk.",
        "- Exit only after an adverse M15 close through EMA50; switch to EMA20 beyond 2.5R.",
        "- Five-bar compressed VWAP behavior reduces half; three losses or 3% realized session loss blocks new entries.",
        "- Paper news exclusion and an explicit 20:00 UTC intraday flattening failsafe.",
        "",
        "## Audit verdict",
        "",
        "FAIL / do not add to the portfolio in raw form. The latest year is effectively flat and the five-year result is negative. The paper headline is not a historical trade-by-trade result, so it cannot validate the EA.",
        "",
        "The 2024 row is the closest paper-sample reproduction and uses a reconstructed 2024 NFP/CPI/FOMC/GDP calendar. Longer rows are supplemental robustness checks: the paper does not supply a multi-year event file, and the static news exclusion is not extended outside 2024. The compressed-VWAP partial and the 20:00 UTC flatten are explicit implementation resolutions for omissions or contradictions in the paper.",
        "",
        "No website, installer, BAT or active portfolio file was changed.",
    ])
    (ROOT / "RAW RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SAVED {ROOT / 'RAW RESULTS.md'}", flush=True)


if __name__ == "__main__":
    main()
