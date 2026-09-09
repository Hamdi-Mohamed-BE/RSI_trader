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
SOURCE = ROOT / "EA" / "Calyx Value Area Reversion EA.mq5"
EXPERT_FOLDER = "AAA Research\\Value Area Reversion Pipeline"
EXPERT_NAME = "Calyx Value Area Reversion EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "Value Area Reversion Pipeline"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "value-area-reversion-pipeline-20260909"
TESTER_REPORTS = TESTER / "reports" / "value-area-reversion-pipeline-20260909"
REPORTS = ROOT / "Pipeline Backtest Reports"
SETS = ROOT / "Pipeline Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"

DEVELOPMENT_START = "2021.09.01"
DEVELOPMENT_END = "2024.03.01"
LOCKED_START = "2024.03.01"
LOCKED_END = "2026.09.01"
LATEST_START = "2025.09.01"
FULL_START = "2021.09.01"

ASSETS = [
    {"label": "XAU", "symbol": "XAUUSD", "slug": "xauusd"},
    {"label": "XAG", "symbol": "XAGUSD", "slug": "xagusd"},
    {"label": "BTC", "symbol": "BTCUSD", "slug": "btcusd"},
    {"label": "US100", "symbol": "USTEC", "slug": "ustec"},
]


def load_analyzer():
    spec = importlib.util.spec_from_file_location("value_area_pipeline_analyzer", ANALYZER_PATH)
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
        "InpSignalTimeframe": 15,
        "InpProfileTimeframe": 15,
        "InpProfileRows": 60,
        "InpValueAreaPercent": 70.0,
        "InpMaximumBarsAfterBreakout": 5,
        "InpMaximumBreakoutVolumeRatio": 1.0,
        "InpMinimumReclaimVolumeRatio": 1.0,
        "InpConfirmation": 0,
        "InpStopMode": 0,
        "InpStopBufferATR": 0.10,
        "InpStopATR": 1.0,
        "InpStopPercent": 0.50,
        "InpTargetMode": 0,
        "InpRewardRisk": 1.50,
        "InpBreakEvenAtR": 0.0,
        "InpBreakEvenLockR": 0.05,
        "InpTrailStartR": 0.0,
        "InpTrailATR": 1.50,
        "InpMaximumHoldingBars": 0,
        "InpSession": 0,
        "InpDirection": 0,
        "InpWeekdaysOnly": False,
        "InpAsiaStartUTC": 0,
        "InpAsiaEndUTC": 8,
        "InpLondonStartUTC": 7,
        "InpLondonEndUTC": 12,
        "InpNewYorkStartUTC": 13,
        "InpNewYorkEndUTC": 20,
        "InpOverlapStartUTC": 13,
        "InpOverlapEndUTC": 16,
        "InpTesterServerUTCOffsetHours": 0,
        "InpRegimeMode": 0,
        "InpRegimeTimeframe": 16385,
        "InpRegimeEMAPeriod": 50,
        "InpMinimumADX": 0.0,
        "InpMaximumADX": 0.0,
        "InpADXTimeframe": 30,
        "InpADXPeriod": 14,
        "InpMinimumDailyATRPercent": 0.0,
        "InpMaximumDailyATRPercent": 0.0,
        "InpMaximumSpreadATR": 0.25,
        "InpRiskPercent": 1.0,
        "InpMaximumTradesPerDay": 2,
        "InpMagic": 990909001,
        "InpMaximumDeviationPoints": 80,
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


def run_case(asset: dict, phase: str, variant: str, config: dict[str, object],
             start: str, end: str, model: int, sequence: int) -> dict:
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    case_id = f"{asset['slug']}--{variant}--{phase}--{signature}"
    local_report = REPORTS / asset["slug"] / phase / f"{case_id}.htm"
    if local_report.is_file():
        parsed = {
            "asset": asset["label"], "symbol": asset["symbol"], "variant": variant,
            "phase": phase, "config": deepcopy(config), "path": str(local_report),
            **ANALYZER.parse_report(local_report),
        }
        print(f"CACHED {sequence:03d} {asset['label']:5s} {phase:15s} {variant}", flush=True)
        return parsed

    set_name = f"VAR-{case_id}.set"
    set_path = SETS / asset["slug"] / set_name
    set_path.parent.mkdir(parents=True, exist_ok=True)
    set_path.write_text(set_text(config, 990900000 + sequence), encoding="utf-8")
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
Symbol={asset['symbol']}
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
Report=reports\\value-area-reversion-pipeline-20260909\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {asset['label']:5s} {phase:15s} {variant}", flush=True)
    for attempt in range(1, 5):
        stop_isolated_terminal()
        subprocess.Popen(
            f'"{TERMINAL}" /portable /config:"{ini_path}"',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + (75 if model == 1 else 900)
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
    parsed = {
        "asset": asset["label"], "symbol": asset["symbol"], "variant": variant,
        "phase": phase, "config": deepcopy(config), "path": str(local_report),
        **ANALYZER.parse_report(local_report),
    }
    print(
        f"DONE  {asset['label']:5s} {phase:15s} {variant:24s} "
        f"return={parsed['return_pct']:+.2f}% PF={parsed['profit_factor']:.2f} "
        f"WR={parsed['win_rate_pct']:.2f}% DD={parsed['max_drawdown_pct']:.2f}% "
        f"n={parsed['trades']} Sharpe={parsed['sharpe']:.2f}",
        flush=True,
    )
    return parsed


def selection_score(row: dict, minimum_trades: int = 55) -> float:
    if row["trades"] < 12 or row["profit_factor"] <= 0:
        return -10000.0 + row["trades"]
    sample_penalty = max(0, minimum_trades - row["trades"]) * 0.15
    return (
        0.20 * row["return_pct"]
        + 34.0 * math.log(max(row["profit_factor"], 0.05))
        - 1.70 * row["max_drawdown_pct"]
        + 0.12 * row["win_rate_pct"]
        + 0.90 * row["sharpe"]
        + 2.75 * row["recovery_factor"]
        - sample_penalty
    )


def choose(rows: list[dict], numeric: bool = False) -> dict:
    for row in rows:
        row["selection_score"] = selection_score(row)
    if numeric and len(rows) >= 3:
        raw_scores = [row["selection_score"] for row in rows]
        for index, row in enumerate(rows):
            neighbors = raw_scores[max(0, index - 1):min(len(raw_scores), index + 2)]
            row["selection_score"] = 0.65 * raw_scores[index] + 0.35 * sorted(neighbors)[len(neighbors) // 2]
    sampled = [row for row in rows if row["trades"] >= 30]
    eligible = [row for row in sampled if row["return_pct"] > 0 and row["profit_factor"] > 1.0]
    return max(eligible or sampled or rows, key=lambda item: item["selection_score"])


def variants(selected: dict[str, object], items: list[tuple[str, dict[str, object]]]):
    return [(label, {**deepcopy(selected), **changes}) for label, changes in items]


def phase_cases(selected: dict[str, object]):
    return [
        ("timeframe", variants(selected, [
            ("m5", {"InpSignalTimeframe": 5, "InpProfileTimeframe": 5}),
            ("m15-raw", {"InpSignalTimeframe": 15, "InpProfileTimeframe": 15}),
            ("m30", {"InpSignalTimeframe": 30, "InpProfileTimeframe": 30}),
            ("h1", {"InpSignalTimeframe": 16385, "InpProfileTimeframe": 30}),
        ]), False),
        ("profile-rows", variants(selected, [
            ("rows-30", {"InpProfileRows": 30}),
            ("rows-45", {"InpProfileRows": 45}),
            ("rows-60-raw", {"InpProfileRows": 60}),
            ("rows-90", {"InpProfileRows": 90}),
            ("rows-120", {"InpProfileRows": 120}),
        ]), True),
        ("value-area", variants(selected, [
            ("va-60", {"InpValueAreaPercent": 60.0}),
            ("va-65", {"InpValueAreaPercent": 65.0}),
            ("va-70-raw", {"InpValueAreaPercent": 70.0}),
            ("va-75", {"InpValueAreaPercent": 75.0}),
            ("va-80", {"InpValueAreaPercent": 80.0}),
        ]), True),
        ("reclaim-window", variants(selected, [
            ("bars-1", {"InpMaximumBarsAfterBreakout": 1}),
            ("bars-2", {"InpMaximumBarsAfterBreakout": 2}),
            ("bars-3", {"InpMaximumBarsAfterBreakout": 3}),
            ("bars-5-raw", {"InpMaximumBarsAfterBreakout": 5}),
            ("bars-8", {"InpMaximumBarsAfterBreakout": 8}),
            ("bars-10", {"InpMaximumBarsAfterBreakout": 10}),
        ]), True),
        ("breakout-volume", variants(selected, [
            ("weak-060", {"InpMaximumBreakoutVolumeRatio": 0.60}),
            ("weak-075", {"InpMaximumBreakoutVolumeRatio": 0.75}),
            ("weak-090", {"InpMaximumBreakoutVolumeRatio": 0.90}),
            ("weak-100-raw", {"InpMaximumBreakoutVolumeRatio": 1.00}),
            ("weak-110", {"InpMaximumBreakoutVolumeRatio": 1.10}),
        ]), True),
        ("reclaim-volume", variants(selected, [
            ("expand-075", {"InpMinimumReclaimVolumeRatio": 0.75}),
            ("expand-100-raw", {"InpMinimumReclaimVolumeRatio": 1.00}),
            ("expand-115", {"InpMinimumReclaimVolumeRatio": 1.15}),
            ("expand-125", {"InpMinimumReclaimVolumeRatio": 1.25}),
            ("expand-150", {"InpMinimumReclaimVolumeRatio": 1.50}),
        ]), True),
        ("confirmation", variants(selected, [
            ("strict-engulf-raw", {"InpConfirmation": 0}),
            ("body-engulf", {"InpConfirmation": 1}),
            ("directional-reclaim", {"InpConfirmation": 2}),
            ("wick-rejection", {"InpConfirmation": 3}),
        ]), False),
        ("stop", variants(selected, [
            ("breakout-buffer-000", {"InpStopMode": 0, "InpStopBufferATR": 0.00}),
            ("breakout-buffer-005", {"InpStopMode": 0, "InpStopBufferATR": 0.05}),
            ("breakout-buffer-010-raw", {"InpStopMode": 0, "InpStopBufferATR": 0.10}),
            ("breakout-buffer-020", {"InpStopMode": 0, "InpStopBufferATR": 0.20}),
            ("breakout-buffer-030", {"InpStopMode": 0, "InpStopBufferATR": 0.30}),
            ("signal-buffer-010", {"InpStopMode": 1, "InpStopBufferATR": 0.10}),
            ("atr-050", {"InpStopMode": 2, "InpStopATR": 0.50}),
            ("atr-075", {"InpStopMode": 2, "InpStopATR": 0.75}),
            ("atr-100", {"InpStopMode": 2, "InpStopATR": 1.00}),
            ("atr-150", {"InpStopMode": 2, "InpStopATR": 1.50}),
            ("atr-200", {"InpStopMode": 2, "InpStopATR": 2.00}),
            ("percent-025", {"InpStopMode": 3, "InpStopPercent": 0.25}),
            ("percent-050", {"InpStopMode": 3, "InpStopPercent": 0.50}),
            ("percent-100", {"InpStopMode": 3, "InpStopPercent": 1.00}),
            ("percent-150", {"InpStopMode": 3, "InpStopPercent": 1.50}),
        ]), False),
        ("target", variants(selected, [
            ("poc-raw", {"InpTargetMode": 0}),
            ("opposite-edge", {"InpTargetMode": 1}),
            ("rr-050", {"InpTargetMode": 2, "InpRewardRisk": 0.50}),
            ("rr-075", {"InpTargetMode": 2, "InpRewardRisk": 0.75}),
            ("rr-100", {"InpTargetMode": 2, "InpRewardRisk": 1.00}),
            ("rr-150", {"InpTargetMode": 2, "InpRewardRisk": 1.50}),
            ("rr-200", {"InpTargetMode": 2, "InpRewardRisk": 2.00}),
            ("rr-250", {"InpTargetMode": 2, "InpRewardRisk": 2.50}),
            ("rr-300", {"InpTargetMode": 2, "InpRewardRisk": 3.00}),
            ("rr-400", {"InpTargetMode": 2, "InpRewardRisk": 4.00}),
        ]), False),
        ("session", variants(selected, [
            ("all-day-raw", {"InpSession": 0}),
            ("asia", {"InpSession": 1}),
            ("london", {"InpSession": 2}),
            ("new-york", {"InpSession": 3}),
            ("london-ny-overlap", {"InpSession": 4}),
        ]), False),
        ("direction", variants(selected, [
            ("both-raw", {"InpDirection": 0}),
            ("long-only", {"InpDirection": 1}),
            ("short-only", {"InpDirection": 2}),
        ]), False),
        ("trades-per-day", variants(selected, [
            ("max-1", {"InpMaximumTradesPerDay": 1}),
            ("max-2-raw", {"InpMaximumTradesPerDay": 2}),
            ("max-3", {"InpMaximumTradesPerDay": 3}),
            ("max-4", {"InpMaximumTradesPerDay": 4}),
        ]), True),
        ("management", variants(selected, [
            ("none-raw", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 0.0}),
            ("be-050", {"InpBreakEvenAtR": 0.50, "InpTrailStartR": 0.0}),
            ("be-075", {"InpBreakEvenAtR": 0.75, "InpTrailStartR": 0.0}),
            ("be-100", {"InpBreakEvenAtR": 1.00, "InpTrailStartR": 0.0}),
            ("trail-050-atr100", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 0.50, "InpTrailATR": 1.00}),
            ("trail-100-atr100", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 1.00, "InpTrailATR": 1.00}),
            ("trail-100-atr150", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 1.00, "InpTrailATR": 1.50}),
            ("trail-100-atr200", {"InpBreakEvenAtR": 0.0, "InpTrailStartR": 1.00, "InpTrailATR": 2.00}),
            ("be075-trail100", {"InpBreakEvenAtR": 0.75, "InpTrailStartR": 1.00, "InpTrailATR": 1.50}),
        ]), False),
        ("holding", variants(selected, [
            ("until-stop-target-raw", {"InpMaximumHoldingBars": 0}),
            ("bars-8", {"InpMaximumHoldingBars": 8}),
            ("bars-16", {"InpMaximumHoldingBars": 16}),
            ("bars-32", {"InpMaximumHoldingBars": 32}),
            ("bars-64", {"InpMaximumHoldingBars": 64}),
        ]), True),
        ("regime", variants(selected, [
            ("none-raw", {"InpRegimeMode": 0}),
            ("h1-ema50-aligned", {"InpRegimeMode": 1, "InpRegimeTimeframe": 16385, "InpRegimeEMAPeriod": 50}),
            ("h1-ema50-inverse", {"InpRegimeMode": 2, "InpRegimeTimeframe": 16385, "InpRegimeEMAPeriod": 50}),
            ("h1-ema50-slope", {"InpRegimeMode": 3, "InpRegimeTimeframe": 16385, "InpRegimeEMAPeriod": 50}),
            ("h1-ema200-aligned", {"InpRegimeMode": 1, "InpRegimeTimeframe": 16385, "InpRegimeEMAPeriod": 200}),
            ("h4-ema50-aligned", {"InpRegimeMode": 1, "InpRegimeTimeframe": 16388, "InpRegimeEMAPeriod": 50}),
            ("d1-ema50-aligned", {"InpRegimeMode": 1, "InpRegimeTimeframe": 16408, "InpRegimeEMAPeriod": 50}),
        ]), False),
        ("adx", variants(selected, [
            ("none-raw", {"InpMinimumADX": 0.0, "InpMaximumADX": 0.0}),
            ("max-20", {"InpMinimumADX": 0.0, "InpMaximumADX": 20.0}),
            ("max-25", {"InpMinimumADX": 0.0, "InpMaximumADX": 25.0}),
            ("max-30", {"InpMinimumADX": 0.0, "InpMaximumADX": 30.0}),
            ("min-15", {"InpMinimumADX": 15.0, "InpMaximumADX": 0.0}),
            ("min-20", {"InpMinimumADX": 20.0, "InpMaximumADX": 0.0}),
            ("min-25", {"InpMinimumADX": 25.0, "InpMaximumADX": 0.0}),
        ]), True),
        ("daily-volatility", variants(selected, [
            ("none-raw", {"InpMinimumDailyATRPercent": 0.0, "InpMaximumDailyATRPercent": 0.0}),
            ("min-050", {"InpMinimumDailyATRPercent": 0.5, "InpMaximumDailyATRPercent": 0.0}),
            ("min-100", {"InpMinimumDailyATRPercent": 1.0, "InpMaximumDailyATRPercent": 0.0}),
            ("min-150", {"InpMinimumDailyATRPercent": 1.5, "InpMaximumDailyATRPercent": 0.0}),
            ("min-200", {"InpMinimumDailyATRPercent": 2.0, "InpMaximumDailyATRPercent": 0.0}),
            ("max-200", {"InpMinimumDailyATRPercent": 0.0, "InpMaximumDailyATRPercent": 2.0}),
            ("max-300", {"InpMinimumDailyATRPercent": 0.0, "InpMaximumDailyATRPercent": 3.0}),
            ("max-500", {"InpMinimumDailyATRPercent": 0.0, "InpMaximumDailyATRPercent": 5.0}),
            ("band-1-3", {"InpMinimumDailyATRPercent": 1.0, "InpMaximumDailyATRPercent": 3.0}),
        ]), False),
        ("weekday", variants(selected, [
            ("all-days-raw", {"InpWeekdaysOnly": False}),
            ("weekdays-only", {"InpWeekdaysOnly": True}),
        ]), False),
    ]


def result_line(name: str, row: dict) -> dict:
    keys = (
        "net_profit", "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct",
        "trades", "sharpe", "recovery_factor", "expected_payoff", "history_quality",
        "commission", "swap",
    )
    return {"asset": row["asset"], "symbol": row["symbol"], "version": name,
            **{key: row[key] for key in keys}}


def process_asset(asset: dict, sequence: int) -> tuple[dict, int]:
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
            rows.append(run_case(asset, phase, variant, config, DEVELOPMENT_START, DEVELOPMENT_END, 1, sequence))
        winner = choose(rows, numeric=numeric)
        selected = deepcopy(winner["config"])
        selected_by_phase[phase] = winner["variant"]
        selected_phase_stats[phase] = compact(winner)
        development[phase] = [compact(row) for row in rows]
        selection_file = ROOT / f"pipeline-{asset['slug']}-{phase}-selection.json"
        selection_file.write_text(
            json.dumps({"winner": compact(winner), "rows": development[phase]}, indent=2, default=str),
            encoding="utf-8",
        )
        print(
            f"SELECT {asset['label']} {phase}: {winner['variant']} | {winner['return_pct']:+.2f}% "
            f"PF {winner['profit_factor']:.2f} WR {winner['win_rate_pct']:.2f}% "
            f"DD {winner['max_drawdown_pct']:.2f}% n={winner['trades']}", flush=True,
        )
        progress = {
            "asset": asset,
            "completed_phase": phase,
            "selected_by_phase": selected_by_phase,
            "selected_config": selected,
            "updated_utc": datetime.now(timezone.utc).isoformat(),
        }
        (ROOT / f"PIPELINE PROGRESS - {asset['label']}.json").write_text(
            json.dumps(progress, indent=2), encoding="utf-8"
        )

    baseline = base_config()
    sequence += 1
    baseline_locked = run_case(asset, "locked", "baseline-raw", baseline, LOCKED_START, LOCKED_END, 0, sequence)
    sequence += 1
    optimized_locked = run_case(asset, "locked", "optimized", selected, LOCKED_START, LOCKED_END, 0, sequence)
    sequence += 1
    optimized_latest = run_case(asset, "latest", "optimized", selected, LATEST_START, LOCKED_END, 0, sequence)
    sequence += 1
    optimized_full = run_case(asset, "full", "optimized", selected, FULL_START, LOCKED_END, 0, sequence)

    outcomes = ANALYZER.trade_outcomes(optimized_locked["deals"])
    monte_carlo = ANALYZER.monte_carlo(outcomes, optimized_locked["initial_balance"], 10_000) if outcomes else {}
    if (
        optimized_locked["return_pct"] > 0
        and optimized_locked["profit_factor"] >= 1.20
        and optimized_locked["trades"] >= 40
        and optimized_latest["profit_factor"] > 1.0
        and optimized_latest["return_pct"] > 0
        and monte_carlo.get("return_p5_pct", -1) > 0
    ):
        decision = "PASS FOR ISOLATED DEMO — not approved for the active portfolio."
    elif optimized_locked["return_pct"] > 0 and optimized_locked["profit_factor"] > 1.0:
        decision = "WATCH ONLY — some locked-window edge remains, but robustness gates failed."
    else:
        decision = "REJECT — the untouched post-selection window failed."

    selected_set = SETS / f"{asset['label']} Value Area Reversion - pipeline selected - 1pct.set"
    selected_set.write_text(set_text(selected, 990999000 + ASSETS.index(asset)), encoding="utf-8")
    return {
        "asset": asset,
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
        "selected_set": str(selected_set),
    }, sequence


def main() -> None:
    prepare()
    sequence = 0
    results = []
    for asset in ASSETS:
        print(f"\n===== {asset['label']} / {asset['symbol']} FULL PIPELINE =====", flush=True)
        result, sequence = process_asset(asset, sequence)
        results.append(result)

    audit = {
        "source": {
            "video_title": "Stupid Simple Order Flow Strategy",
            "video": "https://www.youtube.com/shorts/-j5xykuSD3I",
            "indicator": "https://www.luxalgo.com/library/indicator/value-area-reversion-signals/",
            "raw_rule": "Previous-day 60-row 70% value area; weak-volume breach; reclaim within five bars using an engulfing candle and expanding activity; stop beyond the failed-breakout extreme; target POC.",
            "data_limit": "All MT5 tests use broker tick activity. They are not centralized futures order-flow tests.",
        },
        "test_design": {
            "development": f"{DEVELOPMENT_START} to {DEVELOPMENT_END}, native MT5 1-minute OHLC screening",
            "locked_oos": f"{LOCKED_START} to {LOCKED_END}, native MT5 Every Tick",
            "latest": f"{LATEST_START} to {LOCKED_END}, native MT5 Every Tick",
            "full": f"{FULL_START} to {LOCKED_END}, native MT5 Every Tick",
            "risk_per_trade_pct": 1.0,
            "selection": "Sequential development-only optimization. The locked window was unopened until each asset's complete rule set was frozen.",
            "costs": "Broker spread, commission, swap and random execution delay.",
        },
        "assets": results,
        "native_mt5_cases": sequence,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "system_changed": False,
    }
    (ROOT / "PIPELINE AUDIT.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")

    final_rows = []
    for result in results:
        final_rows.extend([
            result_line("baseline-raw-locked", result["final"]["baseline_locked"]),
            result_line("optimized-locked", result["final"]["optimized_locked"]),
            result_line("optimized-latest-1y", result["final"]["optimized_latest"]),
            result_line("optimized-full-5y", result["final"]["optimized_full"]),
        ])
    with (ROOT / "PIPELINE RESULTS.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(final_rows[0]))
        writer.writeheader()
        writer.writerows(final_rows)

    lines = [
        "# Value Area Reversion — full Calyx pipeline",
        "",
        "Source: LuxAlgo's *Stupid Simple Order Flow Strategy* video and official Value Area Reversion Signals specification.",
        "",
        "All configurations risk 1% of current equity. Development-only sequential selection was followed by an untouched Every-Tick locked window. Broker costs and random execution delay are included.",
        "",
        "## Final native MT5 results",
        "",
        "| Asset | Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in final_rows:
        lines.append(
            f"| {row['asset']} | {row['version']} | {row['return_pct']:+.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | "
            f"{row['max_drawdown_pct']:.2f}% | {row['trades']} | "
            f"{row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
        )
    lines.extend(["", "## Decisions", ""])
    for result in results:
        lines.append(f"- **{result['asset']['label']}:** {result['decision']}")
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        "The source itself warns that this TradingView-style reconstruction is not Fabio Valentini's real order flow. The MT5 implementation is one step further removed because CFD/spot symbols expose broker tick activity rather than centralized exchange volume. Results therefore test a reproducible value-area proxy, not a genuine order-book edge.",
        "",
        "No website, BAT, installer, recommended-system or active-portfolio file was changed. All SET files are research-only pending user review.",
    ])
    (ROOT / "PIPELINE REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({
        "cases": sequence,
        "decisions": {result["asset"]["label"]: result["decision"] for result in results},
        "final": final_rows,
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()

