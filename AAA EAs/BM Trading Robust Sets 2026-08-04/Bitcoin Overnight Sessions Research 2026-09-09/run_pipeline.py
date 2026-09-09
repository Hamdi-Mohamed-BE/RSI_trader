from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import time
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
TERMINAL = TESTER / "terminal64.exe"
METAEDITOR = TESTER / "MetaEditor64.exe"
SOURCE = ROOT / "EA" / "Calyx Bitcoin Overnight MAX10 Raw EA.mq5"
EXPERT_FOLDER = "AAA Research\\Bitcoin Overnight Sessions Pipeline"
EXPERT_NAME = "Calyx Bitcoin Overnight MAX10 Raw EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "Bitcoin Overnight Sessions Pipeline"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "bitcoin-overnight-pipeline-20260909"
TESTER_REPORTS = TESTER / "reports" / "bitcoin-overnight-pipeline-20260909"
REPORTS = ROOT / "Pipeline Backtest Reports"
SETS = ROOT / "Pipeline Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"
RAW_AUDIT = ROOT / "raw-paper-audit.json"

DEVELOPMENT_START = "2021.09.01"
DEVELOPMENT_END = "2024.03.01"
LOCKED_START = "2024.03.01"
LOCKED_END = "2026.09.01"
LATEST_START = "2025.09.01"
FULL_START = "2021.09.01"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("bitcoin_overnight_pipeline_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the MT5 report analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


def prepare() -> None:
    for directory in (EXPERT_DIR, TESTER_SETS, CONFIGS, TESTER_REPORTS, REPORTS, SETS):
        directory.mkdir(parents=True, exist_ok=True)
    for required in (TERMINAL, METAEDITOR, SOURCE, ANALYZER_PATH, RAW_AUDIT):
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
    log = ROOT / "pipeline-compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{log}"'
    result = subprocess.run(command, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = log.read_text(encoding="utf-16", errors="ignore") if log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"EA compile failed (exit {result.returncode}). Read {log}")
    shutil.copy2(EXPERT, ROOT / "EA" / EXPERT.name)


def base_config() -> dict[str, object]:
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
        "InpUseDefinedRiskStop": True,
        "InpRiskPercent": 1.0,
        "InpDirectionMode": 0,
        "InpStopMode": 1,
        "InpStopPercent": 3.0,
        "InpStopATRTimeframe": 16408,
        "InpStopATRPeriod": 14,
        "InpStopATRMultiplier": 1.0,
        "InpTargetR": 0.0,
        "InpBreakEvenAtR": 0.0,
        "InpTrailStartR": 0.0,
        "InpTrailATRTimeframe": 16385,
        "InpTrailATRPeriod": 14,
        "InpTrailATRMultiplier": 1.0,
        "InpRegimeMode": 0,
        "InpMinimumDailyATRPercent": 0.0,
        "InpMaximumDailyATRPercent": 0.0,
        "InpEntryWindowMinutes": 15,
        "InpMaxDeviationBrokerPoints": 50,
        "InpMagic": 981009950,
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
    actual = {**deepcopy(config), "InpMagic": magic}
    return "\n".join(f"{key}={render(value)}" for key, value in actual.items()) + "\n"


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def run_case(phase: str, variant: str, config: dict[str, object], start: str, end: str,
             model: int, sequence: int) -> dict:
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    case_id = f"btcusd--{variant}--{phase}--{signature}"
    local_report = REPORTS / phase / f"{case_id}.htm"
    if local_report.is_file():
        return {"variant": variant, "phase": phase, "config": deepcopy(config),
                "path": str(local_report), **ANALYZER.parse_report(local_report)}

    set_name = f"BTC-Overnight-{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 981009950 + sequence), encoding="utf-8")
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
Model={model}
ExecutionMode=1
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\bitcoin-overnight-pipeline-20260909\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {phase:14s} {variant}", flush=True)
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
    parsed = {"variant": variant, "phase": phase, "config": deepcopy(config),
              "path": str(local_report), **ANALYZER.parse_report(local_report)}
    print(
        f"DONE  {phase:14s} {variant:18s} return={parsed['return_pct']:+.2f}% "
        f"PF={parsed['profit_factor']:.2f} WR={parsed['win_rate_pct']:.2f}% "
        f"DD={parsed['max_drawdown_pct']:.2f}% n={parsed['trades']}",
        flush=True,
    )
    time.sleep(2)
    return parsed


def selection_score(row: dict, minimum_trades: int = 35) -> float:
    if row["trades"] < 12 or row["profit_factor"] <= 0:
        return -10000.0 + row["trades"]
    sample_penalty = max(0, minimum_trades - row["trades"]) * 0.30
    return (
        row["return_pct"]
        + 13.0 * math.log(max(row["profit_factor"], 0.05))
        - 1.20 * row["max_drawdown_pct"]
        + 0.18 * row["win_rate_pct"]
        + 0.40 * row["sharpe"]
        + 0.35 * row["recovery_factor"]
        - sample_penalty
    )


def choose(rows: list[dict], numeric: bool = False) -> dict:
    for row in rows:
        row["selection_score"] = selection_score(row)
    if numeric and len(rows) >= 3:
        raw = [row["selection_score"] for row in rows]
        for index, row in enumerate(rows):
            neighbors = raw[max(0, index - 1): min(len(raw), index + 2)]
            row["selection_score"] = 0.60 * raw[index] + 0.40 * sorted(neighbors)[len(neighbors) // 2]
    adequately_sampled = [row for row in rows if row["trades"] >= 20]
    eligible = [row for row in adequately_sampled if row["return_pct"] > 0 and row["profit_factor"] > 1]
    return max(eligible or adequately_sampled or rows, key=lambda item: item["selection_score"])


def phase_cases(selected: dict[str, object]) -> list[tuple[str, list[tuple[str, dict[str, object]]], bool]]:
    def variants(items):
        return [(label, {**deepcopy(selected), **changes}) for label, changes in items]

    return [
        ("stop", variants([
            ("percent-100", {"InpStopMode": 0, "InpStopPercent": 1.0}),
            ("percent-150", {"InpStopMode": 0, "InpStopPercent": 1.5}),
            ("percent-200", {"InpStopMode": 0, "InpStopPercent": 2.0}),
            ("percent-300", {"InpStopMode": 0, "InpStopPercent": 3.0}),
            ("percent-500", {"InpStopMode": 0, "InpStopPercent": 5.0}),
            ("daily-atr-050", {"InpStopMode": 1, "InpStopATRTimeframe": 16408, "InpStopATRMultiplier": 0.5}),
            ("daily-atr-075", {"InpStopMode": 1, "InpStopATRTimeframe": 16408, "InpStopATRMultiplier": 0.75}),
            ("daily-atr-100", {"InpStopMode": 1, "InpStopATRTimeframe": 16408, "InpStopATRMultiplier": 1.0}),
            ("daily-atr-150", {"InpStopMode": 1, "InpStopATRTimeframe": 16408, "InpStopATRMultiplier": 1.5}),
            ("daily-atr-200", {"InpStopMode": 1, "InpStopATRTimeframe": 16408, "InpStopATRMultiplier": 2.0}),
        ]), True),
        ("nights", variants([
            ("all-paper", {"InpTradeFridayNight": True, "InpTradeMondayNight": True, "InpTradeTuesdayNight": True}),
            ("friday-only", {"InpTradeFridayNight": True, "InpTradeMondayNight": False, "InpTradeTuesdayNight": False}),
            ("monday-only", {"InpTradeFridayNight": False, "InpTradeMondayNight": True, "InpTradeTuesdayNight": False}),
            ("tuesday-only", {"InpTradeFridayNight": False, "InpTradeMondayNight": False, "InpTradeTuesdayNight": True}),
            ("friday-monday", {"InpTradeFridayNight": True, "InpTradeMondayNight": True, "InpTradeTuesdayNight": False}),
            ("monday-tuesday", {"InpTradeFridayNight": False, "InpTradeMondayNight": True, "InpTradeTuesdayNight": True}),
            ("friday-tuesday", {"InpTradeFridayNight": True, "InpTradeMondayNight": False, "InpTradeTuesdayNight": True}),
        ]), False),
        ("lookback", variants([
            ("max-05", {"InpLookbackCalendarDays": 5}),
            ("max-10-paper", {"InpLookbackCalendarDays": 10}),
            ("max-15", {"InpLookbackCalendarDays": 15}),
            ("max-20", {"InpLookbackCalendarDays": 20}),
            ("max-30", {"InpLookbackCalendarDays": 30}),
            ("max-50", {"InpLookbackCalendarDays": 50}),
        ]), True),
        ("direction", variants([
            ("long-paper", {"InpDirectionMode": 0}),
            ("short-mirror", {"InpDirectionMode": 1}),
            ("both", {"InpDirectionMode": 2}),
        ]), False),
        ("exit-time", variants([
            ("ny-0930", {"InpExitNewYorkHour": 9, "InpExitNewYorkMinute": 30}),
            ("ny-1000-paper", {"InpExitNewYorkHour": 10, "InpExitNewYorkMinute": 0}),
            ("ny-1100", {"InpExitNewYorkHour": 11, "InpExitNewYorkMinute": 0}),
            ("ny-1200", {"InpExitNewYorkHour": 12, "InpExitNewYorkMinute": 0}),
            ("ny-1400", {"InpExitNewYorkHour": 14, "InpExitNewYorkMinute": 0}),
            ("ny-1600", {"InpExitNewYorkHour": 16, "InpExitNewYorkMinute": 0}),
        ]), True),
        ("target", variants([
            ("time-exit", {"InpTargetR": 0.0}),
            ("rr-050", {"InpTargetR": 0.5}),
            ("rr-075", {"InpTargetR": 0.75}),
            ("rr-100", {"InpTargetR": 1.0}),
            ("rr-150", {"InpTargetR": 1.5}),
            ("rr-200", {"InpTargetR": 2.0}),
            ("rr-300", {"InpTargetR": 3.0}),
            ("rr-400", {"InpTargetR": 4.0}),
        ]), True),
        ("management", variants([
            ("none", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 0.0}),
            ("be-050", {"InpBreakEvenAtR": 0.5, "InpTrailStartR": 0.0}),
            ("be-075", {"InpBreakEvenAtR": 0.75, "InpTrailStartR": 0.0}),
            ("be-100", {"InpBreakEvenAtR": 1.0, "InpTrailStartR": 0.0}),
            ("trail-050", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 0.5, "InpTrailATRMultiplier": 1.0}),
            ("trail-100", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 1.0, "InpTrailATRMultiplier": 1.0}),
            ("be100-trail100", {"InpBreakEvenAtR": 1.0, "InpTrailStartR": 1.0, "InpTrailATRMultiplier": 1.0}),
        ]), False),
        ("regime", variants([
            ("none", {"InpRegimeMode": 0}),
            ("daily-ema50", {"InpRegimeMode": 1}),
            ("daily-ema200", {"InpRegimeMode": 2}),
            ("ema50-slope", {"InpRegimeMode": 3}),
        ]), False),
        ("volatility", variants([
            ("none", {"InpMinimumDailyATRPercent": 0.0, "InpMaximumDailyATRPercent": 0.0}),
            ("atr-min-200", {"InpMinimumDailyATRPercent": 2.0, "InpMaximumDailyATRPercent": 0.0}),
            ("atr-max-500", {"InpMinimumDailyATRPercent": 0.0, "InpMaximumDailyATRPercent": 5.0}),
            ("atr-max-750", {"InpMinimumDailyATRPercent": 0.0, "InpMaximumDailyATRPercent": 7.5}),
            ("atr-band-2-75", {"InpMinimumDailyATRPercent": 2.0, "InpMaximumDailyATRPercent": 7.5}),
        ]), False),
    ]


def result_line(name: str, row: dict) -> dict:
    return {"version": name, **{key: row[key] for key in (
        "net_profit", "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct",
        "trades", "sharpe", "recovery_factor", "expected_payoff", "history_quality", "commission", "swap"
    )}}


def main() -> None:
    prepare()
    sequence = 0
    selected = base_config()
    selected_by_phase: dict[str, str] = {}
    development: dict[str, list[dict]] = {}

    for phase_name in [item[0] for item in phase_cases(selected)]:
        phase, candidates, numeric = next(item for item in phase_cases(selected) if item[0] == phase_name)
        rows = []
        for variant, config in candidates:
            sequence += 1
            rows.append(run_case(phase, variant, config, DEVELOPMENT_START, DEVELOPMENT_END, 1, sequence))
        winner = choose(rows, numeric=numeric)
        selected = deepcopy(winner["config"])
        selected_by_phase[phase] = winner["variant"]
        development[phase] = [compact(row) for row in rows]
        (ROOT / f"pipeline-{phase}-selection.json").write_text(
            json.dumps({"winner": compact(winner), "rows": development[phase]}, indent=2, default=str),
            encoding="utf-8",
        )
        print(
            f"SELECT {phase}: {winner['variant']} | {winner['return_pct']:+.2f}% "
            f"PF {winner['profit_factor']:.2f} WR {winner['win_rate_pct']:.2f}% "
            f"DD {winner['max_drawdown_pct']:.2f}% n={winner['trades']}",
            flush=True,
        )

    baseline = base_config()
    sequence += 1
    baseline_locked = run_case("locked", "baseline-risk1", baseline, LOCKED_START, LOCKED_END, 0, sequence)
    sequence += 1
    optimized_locked = run_case("locked", "optimized", selected, LOCKED_START, LOCKED_END, 0, sequence)
    sequence += 1
    optimized_latest = run_case("latest", "optimized", selected, LATEST_START, LOCKED_END, 0, sequence)
    sequence += 1
    optimized_full = run_case("full", "optimized", selected, FULL_START, LOCKED_END, 0, sequence)

    outcomes = ANALYZER.trade_outcomes(optimized_locked["deals"])
    monte_carlo = ANALYZER.monte_carlo(outcomes, optimized_locked["initial_balance"], 10_000) if outcomes else {}
    if (
        optimized_locked["return_pct"] > 0
        and optimized_locked["profit_factor"] >= 1.20
        and optimized_locked["trades"] >= 25
        and optimized_latest["profit_factor"] > 1.0
        and optimized_latest["return_pct"] > 0
        and monte_carlo.get("return_p5_pct", -1) > 0
    ):
        decision = "PASS FOR ISOLATED DEMO — not yet approved for the active portfolio."
    elif optimized_locked["return_pct"] > 0 and optimized_locked["profit_factor"] > 1.0:
        decision = "WATCH ONLY — some OOS edge remains, but robustness gates failed."
    else:
        decision = "REJECT — the untouched post-selection window failed."

    selected_set = SETS / "BTC Overnight MAX10 - pipeline selected - 1pct.set"
    selected_set.write_text(set_text(selected, 981009999), encoding="utf-8")
    raw = json.loads(RAW_AUDIT.read_text(encoding="utf-8"))
    audit = {
        "paper": {
            "title": "How To Profitably Trade Bitcoin's Overnight Sessions?",
            "authors": "Radovan Vojtko and Cyril Dujava",
            "ssrn": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=5021138",
        },
        "test_design": {
            "development": f"{DEVELOPMENT_START} to {DEVELOPMENT_END}, MT5 1-minute OHLC screening",
            "locked_oos": f"{LOCKED_START} to {LOCKED_END}, MT5 Every Tick",
            "latest": f"{LATEST_START} to {LOCKED_END}, MT5 Every Tick",
            "full": f"{FULL_START} to {LOCKED_END}, MT5 Every Tick",
            "risk_per_trade_pct": 1.0,
            "selection_rule": "Sequential development-only selection; locked window was untouched until all choices were frozen.",
        },
        "raw_reference": raw["rows"],
        "selected_by_phase": selected_by_phase,
        "selected_config": selected,
        "development": development,
        "final": {
            "baseline_locked": compact(baseline_locked),
            "optimized_locked": compact(optimized_locked),
            "optimized_latest": compact(optimized_latest),
            "optimized_full": compact(optimized_full),
        },
        "monte_carlo": monte_carlo,
        "decision": decision,
        "native_mt5_cases": sequence,
        "selected_set": str(selected_set),
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "system_changed": False,
    }
    (ROOT / "PIPELINE AUDIT.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    final_rows = [
        result_line("baseline-locked", baseline_locked),
        result_line("optimized-locked", optimized_locked),
        result_line("optimized-latest-1y", optimized_latest),
        result_line("optimized-full-5y", optimized_full),
    ]
    with (ROOT / "PIPELINE RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(final_rows[0]))
        writer.writeheader()
        writer.writerows(final_rows)

    lines = [
        "# Bitcoin Overnight MAX(10) - full Calyx pipeline",
        "",
        f"Decision: **{decision}**",
        "",
        "All pipeline configurations use a defined stop and dynamic 1% equity risk. Screening used only the development window; the locked window was opened after every setting was frozen.",
        "",
        "## Selected settings",
        "",
        *[f"- {phase}: `{variant}`" for phase, variant in selected_by_phase.items()],
        "",
        "## Final native MT5 results",
        "",
        "| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in final_rows:
        lines.append(
            f"| {row['version']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | "
            f"{row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
        )
    if monte_carlo:
        lines.extend([
            "",
            "## Locked-window Monte Carlo",
            "",
            f"- Probability profitable: {monte_carlo['probability_profitable_pct']:.2f}%",
            f"- Return P5 / median / P95: {monte_carlo['return_p5_pct']:+.2f}% / {monte_carlo['return_median_pct']:+.2f}% / {monte_carlo['return_p95_pct']:+.2f}%",
            f"- Max DD median / P95: {monte_carlo['max_dd_median_pct']:.2f}% / {monte_carlo['max_dd_p95_pct']:.2f}%",
        ])
    lines.extend([
        "",
        "No website, BAT, installer, recommended-system or active-portfolio file was changed. The selected SET remains research-only pending user review.",
    ])
    (ROOT / "PIPELINE REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"decision": decision, "selected": selected_by_phase, "final": final_rows,
                      "monte_carlo": {key: value for key, value in monte_carlo.items() if key != "fan"},
                      "cases": sequence}, indent=2), flush=True)


if __name__ == "__main__":
    main()
