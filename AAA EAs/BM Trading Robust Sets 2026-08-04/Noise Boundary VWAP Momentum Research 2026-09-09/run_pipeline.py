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
SOURCE = ROOT / "EA" / "Calyx Noise Boundary VWAP Momentum Raw EA.mq5"
EXPERT_FOLDER = "AAA Research\\Noise Boundary VWAP Momentum Pipeline"
EXPERT_NAME = "Calyx Noise Boundary VWAP Momentum Raw EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "Noise Boundary VWAP Momentum Pipeline"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "noise-boundary-vwap-pipeline-20260909"
TESTER_REPORTS = TESTER / "reports" / "noise-boundary-vwap-pipeline-20260909"
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
    spec = importlib.util.spec_from_file_location("noise_boundary_pipeline_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the native MT5 report analyzer")
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
    compile_log = ROOT / "pipeline-compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{compile_log}"'
    result = subprocess.run(command, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = compile_log.read_text(encoding="utf-16", errors="ignore") if compile_log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"EA compile failed (exit {result.returncode}). Read {compile_log}")
    shutil.copy2(EXPERT, ROOT / "EA" / EXPERT.name)


def base_config() -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpNoiseLookbackSessions": 14,
        "InpVolatilityMultiplier": 1.0,
        "InpDecisionFrequencyMinutes": 30,
        "InpTargetDailyVolatilityPercent": 2.0,
        "InpMaximumNotionalLeverage": 4.0,
        "InpRequireRegularNYSEDay": True,
        "InpUseCalyxRisk": True,
        "InpRiskPercent": 1.0,
        "InpDirectionMode": 0,
        "InpStopMode": 0,
        "InpStopPercent": 0.75,
        "InpStopATRTimeframe": 30,
        "InpStopATRPeriod": 14,
        "InpStopATRMultiplier": 1.0,
        "InpTargetR": 0.0,
        "InpExitMode": 0,
        "InpBreakEvenAtR": 0.0,
        "InpTrailStartR": 0.0,
        "InpTrailATRTimeframe": 30,
        "InpTrailATRPeriod": 14,
        "InpTrailATRMultiplier": 1.0,
        "InpSkipLunch": False,
        "InpLunchStartNewYorkHour": 12,
        "InpLunchStartNewYorkMinute": 0,
        "InpLunchEndNewYorkHour": 14,
        "InpLunchEndNewYorkMinute": 0,
        "InpRegimeMode": 0,
        "InpMinimumDailyATRPercent": 0.0,
        "InpMaximumDailyATRPercent": 0.0,
        "InpMinimumADX": 0.0,
        "InpADXTimeframe": 30,
        "InpADXPeriod": 14,
        "InpMinimumRelativeVolume": 0.0,
        "InpOpenNewYorkHour": 9,
        "InpOpenNewYorkMinute": 30,
        "InpFirstDecisionNewYorkHour": 10,
        "InpFirstDecisionNewYorkMinute": 0,
        "InpLastDecisionNewYorkHour": 15,
        "InpLastDecisionNewYorkMinute": 30,
        "InpCloseNewYorkHour": 15,
        "InpCloseNewYorkMinute": 59,
        "InpMaxDeviationBrokerPoints": 50,
        "InpMagic": 982009950,
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


def stop_isolated_terminal() -> None:
    escaped = str(TERMINAL).replace("'", "''")
    script = (
        f"$target='{escaped}'; "
        "$until=(Get-Date).AddSeconds(3); "
        "do { Get-Process terminal64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -eq $target } | Stop-Process -Force; "
        "Start-Sleep -Milliseconds 200 } while ((Get-Date) -lt $until)"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=30,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def run_case(phase: str, variant: str, config: dict[str, object], start: str, end: str,
             model: int, sequence: int) -> dict:
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    case_id = f"ustec--{variant}--{phase}--{signature}"
    local_report = REPORTS / phase / f"{case_id}.htm"
    if local_report.is_file():
        parsed = {"variant": variant, "phase": phase, "config": deepcopy(config),
                  "path": str(local_report), **ANALYZER.parse_report(local_report)}
        print(f"CACHED {sequence:03d} {phase:14s} {variant}", flush=True)
        return parsed

    set_name = f"Noise-Boundary-{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 982009950 + sequence), encoding="utf-8")
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
Symbol=USTEC
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
Report=reports\\noise-boundary-vwap-pipeline-20260909\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {phase:14s} {variant}", flush=True)
    for attempt in range(1, 5):
        stop_isolated_terminal()
        subprocess.Popen(
            f'"{TERMINAL}" /portable /config:"{ini_path}"',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + (45 if model == 1 else 600)
        while not tester_report.is_file() and time.time() < deadline:
            time.sleep(0.25)
        if tester_report.is_file():
            break
        print(f"RETRY {sequence:03d} attempt {attempt + 1} after MT5 startup lock", flush=True)
    if not tester_report.is_file():
        stop_isolated_terminal()
        raise FileNotFoundError(f"Missing MT5 report: {tester_report}")
    local_report.parent.mkdir(parents=True, exist_ok=True)
    for artifact in TESTER_REPORTS.glob(f"{case_id}*"):
        shutil.copy2(artifact, local_report.parent / artifact.name)
    stop_isolated_terminal()
    parsed = {"variant": variant, "phase": phase, "config": deepcopy(config),
              "path": str(local_report), **ANALYZER.parse_report(local_report)}
    print(
        f"DONE  {phase:14s} {variant:22s} return={parsed['return_pct']:+.2f}% "
        f"PF={parsed['profit_factor']:.2f} WR={parsed['win_rate_pct']:.2f}% "
        f"DD={parsed['max_drawdown_pct']:.2f}% n={parsed['trades']} Sharpe={parsed['sharpe']:.2f}",
        flush=True,
    )
    return parsed


def selection_score(row: dict, minimum_trades: int = 120) -> float:
    if row["trades"] < 20 or row["profit_factor"] <= 0:
        return -10000.0 + row["trades"]
    sample_penalty = max(0, minimum_trades - row["trades"]) * 0.08
    return (
        0.25 * row["return_pct"]
        + 30.0 * math.log(max(row["profit_factor"], 0.05))
        - 1.50 * row["max_drawdown_pct"]
        + 0.15 * row["win_rate_pct"]
        + 0.80 * row["sharpe"]
        + 2.50 * row["recovery_factor"]
        - sample_penalty
    )


def choose(rows: list[dict], numeric: bool = False) -> dict:
    for row in rows:
        row["selection_score"] = selection_score(row)
    if numeric and len(rows) >= 3:
        raw = [row["selection_score"] for row in rows]
        for index, row in enumerate(rows):
            neighbors = raw[max(0, index - 1):min(len(raw), index + 2)]
            row["selection_score"] = 0.60 * raw[index] + 0.40 * sorted(neighbors)[len(neighbors) // 2]
    sampled = [row for row in rows if row["trades"] >= 80]
    eligible = [row for row in sampled if row["return_pct"] > 0 and row["profit_factor"] > 1.0]
    return max(eligible or sampled or rows, key=lambda item: item["selection_score"])


def phase_cases(selected: dict[str, object]) -> list[tuple[str, list[tuple[str, dict[str, object]]], bool]]:
    def variants(items):
        return [(label, {**deepcopy(selected), **changes}) for label, changes in items]

    return [
        ("stop", variants([
            ("structural-dynamic", {"InpStopMode": 0}),
            ("percent-025", {"InpStopMode": 1, "InpStopPercent": 0.25}),
            ("percent-050", {"InpStopMode": 1, "InpStopPercent": 0.50}),
            ("percent-075", {"InpStopMode": 1, "InpStopPercent": 0.75}),
            ("percent-100", {"InpStopMode": 1, "InpStopPercent": 1.00}),
            ("percent-150", {"InpStopMode": 1, "InpStopPercent": 1.50}),
            ("m15-atr-050", {"InpStopMode": 2, "InpStopATRTimeframe": 15, "InpStopATRMultiplier": 0.50}),
            ("m15-atr-100", {"InpStopMode": 2, "InpStopATRTimeframe": 15, "InpStopATRMultiplier": 1.00}),
            ("m15-atr-150", {"InpStopMode": 2, "InpStopATRTimeframe": 15, "InpStopATRMultiplier": 1.50}),
            ("m30-atr-050", {"InpStopMode": 2, "InpStopATRTimeframe": 30, "InpStopATRMultiplier": 0.50}),
            ("m30-atr-100", {"InpStopMode": 2, "InpStopATRTimeframe": 30, "InpStopATRMultiplier": 1.00}),
            ("m30-atr-150", {"InpStopMode": 2, "InpStopATRTimeframe": 30, "InpStopATRMultiplier": 1.50}),
            ("h1-atr-050", {"InpStopMode": 2, "InpStopATRTimeframe": 16385, "InpStopATRMultiplier": 0.50}),
            ("h1-atr-100", {"InpStopMode": 2, "InpStopATRTimeframe": 16385, "InpStopATRMultiplier": 1.00}),
            ("h1-atr-150", {"InpStopMode": 2, "InpStopATRTimeframe": 16385, "InpStopATRMultiplier": 1.50}),
        ]), False),
        ("lookback", variants([
            ("sessions-05", {"InpNoiseLookbackSessions": 5}),
            ("sessions-10", {"InpNoiseLookbackSessions": 10}),
            ("sessions-14-paper", {"InpNoiseLookbackSessions": 14}),
            ("sessions-20", {"InpNoiseLookbackSessions": 20}),
            ("sessions-28", {"InpNoiseLookbackSessions": 28}),
            ("sessions-45", {"InpNoiseLookbackSessions": 45, "InpMagic": 982009951}),
        ]), True),
        ("band", variants([
            ("mult-050", {"InpVolatilityMultiplier": 0.50}),
            ("mult-075", {"InpVolatilityMultiplier": 0.75}),
            ("mult-100-paper", {"InpVolatilityMultiplier": 1.00}),
            ("mult-125", {"InpVolatilityMultiplier": 1.25}),
            ("mult-150", {"InpVolatilityMultiplier": 1.50}),
            ("mult-200", {"InpVolatilityMultiplier": 2.00}),
        ]), True),
        ("decision", variants([
            ("every-15m", {"InpDecisionFrequencyMinutes": 15}),
            ("every-30m-paper", {"InpDecisionFrequencyMinutes": 30}),
            ("every-60m", {"InpDecisionFrequencyMinutes": 60}),
        ]), True),
        ("session", variants([
            ("full-1000-1530", {"InpFirstDecisionNewYorkHour": 10, "InpFirstDecisionNewYorkMinute": 0,
                                  "InpLastDecisionNewYorkHour": 15, "InpLastDecisionNewYorkMinute": 30,
                                  "InpCloseNewYorkHour": 15, "InpCloseNewYorkMinute": 59, "InpSkipLunch": False}),
            ("morning-1000-1130", {"InpFirstDecisionNewYorkHour": 10, "InpFirstDecisionNewYorkMinute": 0,
                                     "InpLastDecisionNewYorkHour": 11, "InpLastDecisionNewYorkMinute": 30,
                                     "InpCloseNewYorkHour": 12, "InpCloseNewYorkMinute": 0, "InpSkipLunch": False}),
            ("afternoon-1330-1530", {"InpFirstDecisionNewYorkHour": 13, "InpFirstDecisionNewYorkMinute": 30,
                                      "InpLastDecisionNewYorkHour": 15, "InpLastDecisionNewYorkMinute": 30,
                                      "InpCloseNewYorkHour": 15, "InpCloseNewYorkMinute": 59, "InpSkipLunch": False}),
            ("no-lunch-1200-1400", {"InpFirstDecisionNewYorkHour": 10, "InpFirstDecisionNewYorkMinute": 0,
                                      "InpLastDecisionNewYorkHour": 15, "InpLastDecisionNewYorkMinute": 30,
                                      "InpCloseNewYorkHour": 15, "InpCloseNewYorkMinute": 59, "InpSkipLunch": True}),
            ("late-1400-1530", {"InpFirstDecisionNewYorkHour": 14, "InpFirstDecisionNewYorkMinute": 0,
                                  "InpLastDecisionNewYorkHour": 15, "InpLastDecisionNewYorkMinute": 30,
                                  "InpCloseNewYorkHour": 15, "InpCloseNewYorkMinute": 59, "InpSkipLunch": False}),
        ]), False),
        ("direction", variants([
            ("both-paper", {"InpDirectionMode": 0}),
            ("long-only", {"InpDirectionMode": 1}),
            ("short-only", {"InpDirectionMode": 2}),
        ]), False),
        ("exit", variants([
            ("band-vwap-paper", {"InpExitMode": 0}),
            ("band-only", {"InpExitMode": 1}),
            ("vwap-only", {"InpExitMode": 2}),
            ("opposite-band", {"InpExitMode": 3}),
            ("time-only", {"InpExitMode": 4}),
        ]), False),
        ("target", variants([
            ("dynamic-indicator-exit", {"InpTargetR": 0.0}),
            ("rr-050", {"InpTargetR": 0.50}),
            ("rr-075", {"InpTargetR": 0.75}),
            ("rr-100", {"InpTargetR": 1.00}),
            ("rr-150", {"InpTargetR": 1.50}),
            ("rr-200", {"InpTargetR": 2.00}),
            ("rr-300", {"InpTargetR": 3.00}),
            ("rr-400", {"InpTargetR": 4.00}),
        ]), True),
        ("management", variants([
            ("none", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 0.0}),
            ("be-050", {"InpBreakEvenAtR": 0.50, "InpTrailStartR": 0.0}),
            ("be-075", {"InpBreakEvenAtR": 0.75, "InpTrailStartR": 0.0}),
            ("be-100", {"InpBreakEvenAtR": 1.00, "InpTrailStartR": 0.0}),
            ("trail-m15-050", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 0.50,
                                "InpTrailATRTimeframe": 15, "InpTrailATRMultiplier": 1.0}),
            ("trail-m30-100", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 1.00,
                                "InpTrailATRTimeframe": 30, "InpTrailATRMultiplier": 1.0}),
            ("trail-h1-100", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 1.00,
                               "InpTrailATRTimeframe": 16385, "InpTrailATRMultiplier": 1.0}),
            ("be100-trail-m30", {"InpBreakEvenAtR": 1.00, "InpTrailStartR": 1.00,
                                  "InpTrailATRTimeframe": 30, "InpTrailATRMultiplier": 1.0}),
        ]), False),
        ("regime", variants([
            ("none", {"InpRegimeMode": 0}),
            ("daily-ema50", {"InpRegimeMode": 1}),
            ("daily-ema200", {"InpRegimeMode": 2}),
            ("daily-ema50-slope", {"InpRegimeMode": 3}),
        ]), False),
        ("adx", variants([
            ("none", {"InpMinimumADX": 0.0}),
            ("m30-adx-15", {"InpMinimumADX": 15.0, "InpADXTimeframe": 30}),
            ("m30-adx-20", {"InpMinimumADX": 20.0, "InpADXTimeframe": 30}),
            ("m30-adx-25", {"InpMinimumADX": 25.0, "InpADXTimeframe": 30}),
            ("h1-adx-20", {"InpMinimumADX": 20.0, "InpADXTimeframe": 16385}),
        ]), True),
        ("relative-volume", variants([
            ("none", {"InpMinimumRelativeVolume": 0.0}),
            ("relvol-075", {"InpMinimumRelativeVolume": 0.75}),
            ("relvol-100", {"InpMinimumRelativeVolume": 1.00}),
            ("relvol-125", {"InpMinimumRelativeVolume": 1.25}),
            ("relvol-150", {"InpMinimumRelativeVolume": 1.50}),
        ]), True),
        ("daily-volatility", variants([
            ("none", {"InpMinimumDailyATRPercent": 0.0, "InpMaximumDailyATRPercent": 0.0}),
            ("atr-min-100", {"InpMinimumDailyATRPercent": 1.0, "InpMaximumDailyATRPercent": 0.0}),
            ("atr-min-150", {"InpMinimumDailyATRPercent": 1.5, "InpMaximumDailyATRPercent": 0.0}),
            ("atr-min-200", {"InpMinimumDailyATRPercent": 2.0, "InpMaximumDailyATRPercent": 0.0}),
            ("atr-max-300", {"InpMinimumDailyATRPercent": 0.0, "InpMaximumDailyATRPercent": 3.0}),
            ("atr-band-1-3", {"InpMinimumDailyATRPercent": 1.0, "InpMaximumDailyATRPercent": 3.0}),
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
    selected_phase_stats: dict[str, dict] = {}
    development: dict[str, list[dict]] = {}

    phase_names = [item[0] for item in phase_cases(selected)]
    for phase_name in phase_names:
        phase, candidates, numeric = next(item for item in phase_cases(selected) if item[0] == phase_name)
        rows = []
        for variant, config in candidates:
            sequence += 1
            rows.append(run_case(phase, variant, config, DEVELOPMENT_START, DEVELOPMENT_END, 1, sequence))
        winner = choose(rows, numeric=numeric)
        selected = deepcopy(winner["config"])
        selected_by_phase[phase] = winner["variant"]
        selected_phase_stats[phase] = compact(winner)
        development[phase] = [compact(row) for row in rows]
        (ROOT / f"pipeline-{phase}-selection.json").write_text(
            json.dumps({"winner": compact(winner), "rows": development[phase]}, indent=2, default=str),
            encoding="utf-8",
        )
        print(
            f"SELECT {phase}: {winner['variant']} | {winner['return_pct']:+.2f}% "
            f"PF {winner['profit_factor']:.2f} WR {winner['win_rate_pct']:.2f}% "
            f"DD {winner['max_drawdown_pct']:.2f}% n={winner['trades']}", flush=True,
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
        and optimized_locked["trades"] >= 80
        and optimized_latest["profit_factor"] > 1.0
        and optimized_latest["return_pct"] > 0
        and monte_carlo.get("return_p5_pct", -1) > 0
    ):
        decision = "PASS FOR ISOLATED DEMO — not yet approved for the active portfolio."
    elif optimized_locked["return_pct"] > 0 and optimized_locked["profit_factor"] > 1.0:
        decision = "WATCH ONLY — some locked-window edge remains, but one or more robustness gates failed."
    else:
        decision = "REJECT — the untouched post-selection window failed."

    selected_set = SETS / "USTEC Noise Boundary VWAP Momentum - pipeline selected - 1pct.set"
    selected_set.write_text(set_text(selected, 982009999), encoding="utf-8")
    raw = json.loads(RAW_AUDIT.read_text(encoding="utf-8"))
    audit = {
        "paper": {
            "title": "Beat the Market: An Effective Intraday Momentum Strategy for S&P500 ETF (SPY)",
            "authors": "Carlo Zarattini, Andrew Aziz and Andrea Barbon",
            "ssrn": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172",
        },
        "instrument": "USTEC transfer test only; US500 failed the raw screen.",
        "test_design": {
            "development": f"{DEVELOPMENT_START} to {DEVELOPMENT_END}, MT5 1-minute OHLC screening",
            "locked_oos": f"{LOCKED_START} to {LOCKED_END}, MT5 Every Tick",
            "latest": f"{LATEST_START} to {LOCKED_END}, MT5 Every Tick",
            "full": f"{FULL_START} to {LOCKED_END}, MT5 Every Tick",
            "risk_per_trade_pct": 1.0,
            "selection_rule": "Sequential development-only selection; locked OOS was not read until every setting was frozen.",
            "costs": "Broker spread, commission, swap and random execution delay.",
        },
        "raw_reference": [row for row in raw["rows"] if row["symbol"] == "USTEC"],
        "selected_by_phase": selected_by_phase,
        "selected_phase_stats": selected_phase_stats,
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
        "# USTEC Noise Boundary VWAP Momentum - full Calyx pipeline",
        "",
        f"Decision: **{decision}**",
        "",
        "Every pipeline case uses a defined stop and dynamic 1% equity risk. Selection used only the development window; the locked Every-Tick window remained untouched until all settings were frozen.",
        "",
        "## Selected development settings",
        "",
        "| Phase | Winner | Return | PF | Win rate | Max DD | Trades |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for phase, variant in selected_by_phase.items():
        row = selected_phase_stats[phase]
        lines.append(
            f"| {phase} | {variant} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} |"
        )
    lines.extend([
        "",
        "## Final native MT5 results",
        "",
        "| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for row in final_rows:
        lines.append(
            f"| {row['version']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | "
            f"{row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
        )
    if monte_carlo:
        lines.extend([
            "",
            "## Locked-window Monte Carlo — 10,000 resamples",
            "",
            f"- Probability profitable: {monte_carlo['probability_profitable_pct']:.2f}%",
            f"- Return P5 / median / P95: {monte_carlo['return_p5_pct']:+.2f}% / {monte_carlo['return_median_pct']:+.2f}% / {monte_carlo['return_p95_pct']:+.2f}%",
            f"- Max DD median / P95: {monte_carlo['max_dd_median_pct']:.2f}% / {monte_carlo['max_dd_p95_pct']:.2f}%",
        ])
    lines.extend([
        "",
        "The MT5 CFD VWAP uses Exness tick volume rather than consolidated exchange volume, so this remains an adapted transfer test.",
        "",
        "No website, BAT, installer, recommended-system or active-portfolio file was changed. The selected SET is research-only pending user review.",
    ])
    (ROOT / "PIPELINE REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": decision,
        "selected": selected_by_phase,
        "final": final_rows,
        "monte_carlo": {key: value for key, value in monte_carlo.items() if key != "fan"},
        "cases": sequence,
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
