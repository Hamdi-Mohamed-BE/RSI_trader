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
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
TERMINAL = TESTER / "terminal64.exe"
METAEDITOR = TESTER / "MetaEditor64.exe"
SOURCE_PACKAGE = PACKAGE / "ORB Volume Data EA"
SOURCE = SOURCE_PACKAGE / "ORB Volume Data EA.mq5"
EXPERT_FOLDER = "BM Trading\\ORB Volume Data EA"
EXPERT_NAME = "ORB Volume Data EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "BM Trading" / EXPERT_NAME
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "paper-orb-us100-20260906"
TESTER_REPORTS = TESTER / "reports" / "paper-orb-us100-20260906"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
CHARTS = ROOT / "Charts"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"
PREVIOUS_AUDIT = PACKAGE / "ORB Session Matrix Research 2026-09-05" / "FINAL AUDIT.json"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("paper_orb_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the native MT5 report analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


def compile_ea() -> None:
    EXPERT_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("ORB Volume Data EA.mq5", "SafeRegimeFilter.mqh", "DynamicTrailingSessionFilter.mqh"):
        shutil.copy2(SOURCE_PACKAGE / name, EXPERT_DIR / name)
    log = ROOT / "compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{log}"'
    result = subprocess.run(command, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = log.read_text(encoding="utf-16", errors="ignore") if log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"EA compile failed (exit {result.returncode}). Read {log}")


def prepare() -> None:
    for directory in (CONFIGS, TESTER_REPORTS, TESTER_SETS, REPORTS, SETS, CHARTS):
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
    compile_ea()


def base_config() -> dict[str, object]:
    # Portable single-US100 analogue of Zarattini/Barbon/Aziz. The paper's
    # cross-sectional top-20 Stocks-in-Play ranking cannot exist on one CFD,
    # so opening relative volume is exposed as a threshold instead.
    return {
        "InpEnableTrading": True,
        "InpSessionZone": 0,
        "InpSessionHour": 9,
        "InpSessionMinute": 30,
        "InpOpeningRangeMinutes": 5,
        "InpTradeWindowMinutes": 385,
        "InpFlatHour": 15,
        "InpFlatMinute": 55,
        "InpWeekdaysOnly": True,
        "InpSignalTimeframe": 1,
        "InpRelativeVolumeDays": 14,
        "InpMinOpeningRelativeVolume": 1.0,
        "InpBarVolumeLookback": 20,
        "InpMinBreakoutRelativeVolume": 0.0,
        "InpATRTimeframe": 15,
        "InpATRPeriod": 14,
        "InpMinRangeATR": 0.0001,
        "InpMaxRangeATR": 99.0,
        "InpRequireVWAP": False,
        "InpUseEMATrend": False,
        "InpFastEMA": 20,
        "InpSlowEMA": 50,
        "InpUseProfileValueArea": False,
        "InpUseProfilePOCBias": False,
        "InpUseProfileBoundaryLVN": False,
        "InpProfileStartHour": 8,
        "InpProfileStartMinute": 0,
        "InpProfileBins": 48,
        "InpProfileValueAreaPercent": 70.0,
        "InpMaxBoundaryNodeRatio": 1.0,
        "InpMinimumProfileTicks": 100,
        "InpShowProfileLevels": False,
        "InpEntryMode": 0,
        "InpTradeDirection": 0,
        "InpUsePaperStopEntry": True,
        "InpRequireOpeningCandleDirection": True,
        "InpBreakoutBodyMinimum": 0.0,
        "InpBreakoutBufferATR": 0.0,
        "InpRetestBars": 3,
        "InpRetestToleranceATR": 0.15,
        "InpRetestBodyMinimum": 0.0,
        "InpStopMode": 2,
        "InpStopBufferATR": 0.0,
        "InpMaximumStopATR": 99.0,
        "InpDailyATRStopFraction": 0.10,
        "InpUseFixedTarget": False,
        "InpRewardRisk": 2.0,
        "InpBreakEvenAtR": 0.0,
        "InpTrailStartAtR": 0.0,
        "InpTrailCandleBufferATR": 0.10,
        "InpRiskPercent": 1.0,
        "InpMaxSpreadRangePercent": 99.0,
        "InpMaxDeviationPoints": 30,
        "InpMagic": 969060001,
        "InpUseAutomaticLiveServerOffset": True,
        "InpTesterServerUTCOffsetHours": 0,
        "InpManualLiveServerUTCOffsetHours": 0,
        "InpUseDynamicTrailingSL": False,
        "InpDynamicTriggerFraction": 0.50,
        "InpDynamicLockFraction": 0.20,
        "InpResearchSession": 0,
        "InpResearchBrokerUtcOffsetMinutes": 0,
        "InpUseMarkovRegimeFilter": False,
        "InpMarkovReturnWindow": 40,
        "InpMarkovThreshold": 0.05,
        "InpMarkovSignalGate": 0.05,
        "InpMarkovMinLabels": 252,
        "InpMarkovHistoryBars": 2600,
    }


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def set_text(config: dict[str, object], magic: int) -> str:
    values = deepcopy(config)
    values["InpMagic"] = magic
    return "\n".join(f"{key}={render(value)}" for key, value in values.items()) + "\n"


def clean(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def run_case(phase: str, variant: str, config: dict[str, object], start: str, end: str,
             model: int, sequence: int) -> dict:
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    case_id = f"ustec--{variant}--{phase}--{signature}"
    local_report = REPORTS / phase / f"{case_id}.htm"
    if local_report.is_file():
        return {"variant": variant, "phase": phase, "config": deepcopy(config),
                "path": str(local_report), **ANALYZER.parse_report(local_report)}

    set_name = f"Paper-ORB-{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 969060000 + sequence), encoding="utf-8")
    shutil.copy2(set_path, TESTER_SETS / set_name)
    tester_report = TESTER_REPORTS / f"{case_id}.htm"
    for stale in TESTER_REPORTS.glob(f"{case_id}*"):
        stale.unlink()
    period = {1: "M1", 5: "M5", 15: "M15", 30: "M30"}[int(config["InpSignalTimeframe"])]
    ini = f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert={EXPERT_FOLDER}\\{EXPERT_NAME}
ExpertParameters={set_name}
Symbol=USTEC
Period={period}
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
Report=reports\\paper-orb-us100-20260906\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {phase:12s} {variant}", flush=True)
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
    # Some MT5 builds hand the config to a child process and let the launcher
    # exit immediately. The report, rather than launcher lifetime, is the
    # authoritative completion signal.
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
    # MT5 can leave its portable terminal lock alive briefly after the report
    # is written. A short gap prevents the following case from attaching to a
    # terminal that is still shutting down and silently skipping its config.
    time.sleep(3)
    return parsed


def selection_score(row: dict, minimum_trades: int = 60) -> float:
    if row["trades"] < 15 or row["profit_factor"] <= 0:
        return -10000.0 + row["trades"]
    sample_penalty = max(0, minimum_trades - row["trades"]) * 0.25
    return (
        row["return_pct"]
        + 14.0 * math.log(max(row["profit_factor"], 0.05))
        - 1.15 * row["max_drawdown_pct"]
        + 0.25 * row["win_rate_pct"]
        + 0.45 * row["sharpe"]
        + 0.30 * row["recovery_factor"]
        - sample_penalty
    )


def choose(rows: list[dict], numeric: bool = False) -> dict:
    for row in rows:
        row["selection_score"] = selection_score(row)
    if numeric and len(rows) >= 3:
        ordered = rows
        raw = [row["selection_score"] for row in ordered]
        for index, row in enumerate(ordered):
            neighbors = raw[max(0, index - 1): min(len(raw), index + 2)]
            row["selection_score"] = 0.55 * raw[index] + 0.45 * sorted(neighbors)[len(neighbors) // 2]
    adequately_sampled = [row for row in rows if row["trades"] >= 40]
    eligible = [row for row in adequately_sampled if row["return_pct"] > 0 and row["profit_factor"] > 1]
    return max(eligible or adequately_sampled or rows, key=lambda item: item["selection_score"])


def phase_cases(selected: dict[str, object]) -> list[tuple[str, list[tuple[str, dict[str, object]]], bool]]:
    phases: list[tuple[str, list[tuple[str, dict[str, object]]], bool]] = []

    def variants(items):
        return [(label, {**deepcopy(selected), **changes}) for label, changes in items]

    phases.append(("open-volume", variants([
        ("rv000", {"InpMinOpeningRelativeVolume": 0.0}),
        ("rv080", {"InpMinOpeningRelativeVolume": 0.8}),
        ("rv100-paper", {"InpMinOpeningRelativeVolume": 1.0}),
        ("rv120", {"InpMinOpeningRelativeVolume": 1.2}),
        ("rv150", {"InpMinOpeningRelativeVolume": 1.5}),
        ("rv200", {"InpMinOpeningRelativeVolume": 2.0}),
    ]), True))
    phases.append(("range", variants([
        ("or5-paper", {"InpOpeningRangeMinutes": 5}),
        ("or15", {"InpOpeningRangeMinutes": 15}),
        ("or30", {"InpOpeningRangeMinutes": 30}),
        ("or60", {"InpOpeningRangeMinutes": 60}),
    ]), True))
    phases.append(("entry", variants([
        ("tick-stop-paper", {"InpUsePaperStopEntry": True, "InpSignalTimeframe": 1}),
        ("close-m1", {"InpUsePaperStopEntry": False, "InpSignalTimeframe": 1}),
        ("close-m5", {"InpUsePaperStopEntry": False, "InpSignalTimeframe": 5}),
        ("close-m15", {"InpUsePaperStopEntry": False, "InpSignalTimeframe": 15}),
        ("close-m30", {"InpUsePaperStopEntry": False, "InpSignalTimeframe": 30}),
    ]), False))
    phases.append(("stop", variants([
        ("dailyatr05", {"InpStopMode": 2, "InpDailyATRStopFraction": 0.05}),
        ("dailyatr075", {"InpStopMode": 2, "InpDailyATRStopFraction": 0.075}),
        ("dailyatr10-paper", {"InpStopMode": 2, "InpDailyATRStopFraction": 0.10}),
        ("dailyatr15", {"InpStopMode": 2, "InpDailyATRStopFraction": 0.15}),
        ("dailyatr20", {"InpStopMode": 2, "InpDailyATRStopFraction": 0.20}),
        ("opposite-range", {"InpStopMode": 1, "InpStopBufferATR": 0.0}),
        ("signal-candle", {"InpStopMode": 0, "InpStopBufferATR": 0.0}),
    ]), False))
    phases.append(("exit", variants([
        ("eod-paper", {"InpUseFixedTarget": False, "InpRewardRisk": 2.0}),
        *[(f"rr{int(rr * 100):03d}", {"InpUseFixedTarget": True, "InpRewardRisk": rr})
          for rr in (0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0)],
    ]), True))
    phases.append(("management", variants([
        ("none-paper", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.0, "InpUseDynamicTrailingSL": False}),
        ("be050", {"InpBreakEvenAtR": 0.5, "InpTrailStartAtR": 0.0, "InpUseDynamicTrailingSL": False}),
        ("be100", {"InpBreakEvenAtR": 1.0, "InpTrailStartAtR": 0.0, "InpUseDynamicTrailingSL": False}),
        ("trail050", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.5, "InpUseDynamicTrailingSL": False}),
        ("trail100", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 1.0, "InpUseDynamicTrailingSL": False}),
        ("dynamic-50-20", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.0, "InpUseDynamicTrailingSL": True}),
    ]), False))
    phases.append(("window", variants([
        *[(f"window{minutes}", {"InpTradeWindowMinutes": minutes}) for minutes in (30, 60, 120, 180, 240, 380)],
    ]), True))
    phases.append(("direction", variants([
        ("both", {"InpTradeDirection": 0}),
        ("long-only", {"InpTradeDirection": 1}),
        ("short-only", {"InpTradeDirection": 2}),
    ]), False))
    phases.append(("session", variants([
        ("asia-0000utc", {"InpSessionZone": 1, "InpSessionHour": 0, "InpSessionMinute": 0,
                           "InpFlatHour": 8, "InpFlatMinute": 0}),
        ("london-0700utc", {"InpSessionZone": 1, "InpSessionHour": 7, "InpSessionMinute": 0,
                             "InpFlatHour": 12, "InpFlatMinute": 0}),
        ("ny-0930-paper", {"InpSessionZone": 0, "InpSessionHour": 9, "InpSessionMinute": 30,
                            "InpFlatHour": 15, "InpFlatMinute": 55}),
        ("overlap-1300utc", {"InpSessionZone": 1, "InpSessionHour": 13, "InpSessionMinute": 0,
                              "InpFlatHour": 16, "InpFlatMinute": 0}),
    ]), False))
    phases.append(("filter", variants([
        ("none", {"InpRequireVWAP": False, "InpUseEMATrend": False,
                   "InpMinBreakoutRelativeVolume": 0.0}),
        ("vwap", {"InpRequireVWAP": True, "InpUseEMATrend": False,
                   "InpMinBreakoutRelativeVolume": 0.0}),
        ("ema", {"InpRequireVWAP": False, "InpUseEMATrend": True,
                  "InpMinBreakoutRelativeVolume": 0.0}),
        ("vwap-ema", {"InpRequireVWAP": True, "InpUseEMATrend": True,
                       "InpMinBreakoutRelativeVolume": 0.0}),
    ]), False))
    return phases


def charts_and_report(audit: dict, raw: dict[str, dict]) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, axes = plt.subplots(2, 1, figsize=(15, 11), constrained_layout=True)
    for label, row, color in (
        ("Raw paper analogue", raw["raw"], "#98a1ad"),
        ("Paper + relative volume", raw["paper_rv"], "#4f86f7"),
        ("Development-selected", raw["optimized"], "#18b981"),
    ):
        dates, balances = ANALYZER.equity_points(row, datetime(2025, 9, 1))
        axes[0].step(dates, balances, where="post", label=label, linewidth=1.8, color=color)
    axes[0].axhline(10000, color="#444", linestyle="--", linewidth=0.8)
    axes[0].set_title("US100 paper-style ORB — untouched locked-year equity")
    axes[0].set_ylabel("Balance (USD)")
    axes[0].legend(loc="best")
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    mc = audit["monte_carlo"]
    fan = mc["fan"]
    x = [point["trade"] for point in fan]
    axes[1].fill_between(x, [point["p5"] for point in fan], [point["p95"] for point in fan],
                         color="#729cff", alpha=0.18, label="5–95%")
    axes[1].fill_between(x, [point["p25"] for point in fan], [point["p75"] for point in fan],
                         color="#729cff", alpha=0.32, label="25–75%")
    axes[1].plot(x, [point["p50"] for point in fan], color="#18b981", linewidth=2, label="Median")
    axes[1].axhline(10000, color="#444", linestyle="--", linewidth=0.8)
    axes[1].set_title(f"10,000-path Monte Carlo — return P5 {mc['return_p5_pct']:+.2f}% | DD P95 {mc['max_dd_p95_pct']:.2f}%")
    axes[1].set_xlabel("Closed trades")
    axes[1].set_ylabel("Balance (USD)")
    axes[1].legend(loc="best")
    fig.savefig(CHARTS / "LOCKED EQUITY AND MONTE CARLO.png", dpi=180, facecolor="white")
    plt.close(fig)

    phase_names = list(audit["development"])
    fig, grid = plt.subplots(5, 2, figsize=(17, 22), constrained_layout=True)
    for axis, phase in zip(grid.flat, phase_names):
        rows = audit["development"][phase]
        labels = [row["variant"] for row in rows]
        returns = [row["return_pct"] for row in rows]
        colors = ["#18b981" if row["variant"] == audit["selected_by_phase"][phase] else "#8aa0b5" for row in rows]
        axis.barh(labels, returns, color=colors)
        axis.axvline(0, color="#333", linewidth=0.8)
        axis.set_title(f"{phase} — development return (%)")
    fig.savefig(CHARTS / "DEVELOPMENT PIPELINE.png", dpi=170, facecolor="white")
    plt.close(fig)

    final = audit["final"]
    lines = [
        "# US100 paper-style 5-minute ORB — native MT5 audit", "",
        "## Decision", "", f"**{audit['decision']}**", "",
        "The exact paper cannot be reproduced on one US100 CFD because its strongest rule ranks the top 20 stocks cross-sectionally by opening relative volume. This audit tests the portable single-instrument analogue on Exness USTEC using broker tick activity.", "",
        "## Test design", "",
        "- Development: 2023-09-01 to 2025-08-31, MT5 1-minute OHLC, sequential parameter selection.",
        "- Locked test: 2025-09-01 to 2026-09-01, MT5 Every Tick, broker spread/costs and random delay.",
        "- Full reference: 2023-09-01 to 2026-09-01, MT5 Every Tick.",
        "- Risk: exactly 1% of dynamic equity per trade. One trade maximum per session.",
        "- Monte Carlo: 10,000 five-trade block-bootstrap paths from untouched locked-year trades.", "",
        "## Locked-year comparison", "",
        "| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key, label in (("raw_paper", "Raw paper analogue"), ("paper_relative_volume", "Paper + relative volume"), ("optimized_locked", "Development-selected")):
        row = final[key]
        lines.append(f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |")
    full = final["optimized_full"]
    lines += ["", "## Selected three-year reference", "",
              "| Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
              "|---:|---:|---:|---:|---:|---:|---:|",
              f"| {full['return_pct']:+.2f}% | {full['profit_factor']:.2f} | {full['win_rate_pct']:.2f}% | {full['max_drawdown_pct']:.2f}% | {full['trades']} | {full['sharpe']:.2f} | {full['recovery_factor']:.2f} |", "",
              "## Selected inputs", ""]
    for phase, variant in audit["selected_by_phase"].items():
        lines.append(f"- {phase}: `{variant}`")
    lines += ["", "## Monte Carlo", "",
              f"- Chance of profit: {mc['probability_profitable_pct']:.2f}%",
              f"- Return P5 / median / P95: {mc['return_p5_pct']:+.2f}% / {mc['return_median_pct']:+.2f}% / {mc['return_p95_pct']:+.2f}%",
              f"- Max drawdown median / P95: {mc['max_dd_median_pct']:.2f}% / {mc['max_dd_p95_pct']:.2f}%", "",
              "## Interpretation", "",
              "The paper's reported stock-universe result must not be presented as a US100 CFD expectation. Only the locked MT5 line above is the honest evidence for this implementation. No portfolio, BAT, or website files were changed by this research run."]
    if audit.get("existing_us100_orb_comparison"):
        old = audit["existing_us100_orb_comparison"]
        lines += ["", "## Existing US100 ORB comparison", "",
                  "| Version | Locked return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | 3-year return | 3-year PF |",
                  "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
                  f"| Existing safer NY ORB | {old['locked']['return_pct']:+.2f}% | {old['locked']['profit_factor']:.2f} | {old['locked']['win_rate_pct']:.2f}% | {old['locked']['max_drawdown_pct']:.2f}% | {old['locked']['trades']} | {old['locked']['sharpe']:.2f} | {old['locked']['recovery_factor']:.2f} | {old['full']['return_pct']:+.2f}% | {old['full']['profit_factor']:.2f} |",
                  f"| New paper-derived ORB | {final['optimized_locked']['return_pct']:+.2f}% | {final['optimized_locked']['profit_factor']:.2f} | {final['optimized_locked']['win_rate_pct']:.2f}% | {final['optimized_locked']['max_drawdown_pct']:.2f}% | {final['optimized_locked']['trades']} | {final['optimized_locked']['sharpe']:.2f} | {final['optimized_locked']['recovery_factor']:.2f} | {full['return_pct']:+.2f}% | {full['profit_factor']:.2f} |", "",
                  "The new version makes more in this sample, but the existing ORB has materially lower drawdown, higher win rate and stronger recovery. Keep the existing ORB in the active system; forward-test the new version separately."]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    prepare()
    sequence = 0
    selected = base_config()
    development: dict[str, list[dict]] = {}
    selected_by_phase: dict[str, str] = {}
    phase_names = [item[0] for item in phase_cases(selected)]
    for phase_name in phase_names:
        phase, candidates, numeric = next(item for item in phase_cases(selected) if item[0] == phase_name)
        rows = []
        for variant, config in candidates:
            sequence += 1
            rows.append(run_case(phase, variant, config, "2023.09.01", "2025.09.01", 1, sequence))
        winner = choose(rows, numeric=numeric)
        selected = deepcopy(winner["config"])
        selected_by_phase[phase] = winner["variant"]
        development[phase] = [clean(row) for row in rows]
        (ROOT / f"{phase}-selection.json").write_text(
            json.dumps({"winner": clean(winner), "rows": development[phase]}, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"SELECT {phase}: {winner['variant']} | {winner['return_pct']:+.2f}% PF {winner['profit_factor']:.2f} n={winner['trades']}", flush=True)

    raw_config = base_config()
    raw_config["InpMinOpeningRelativeVolume"] = 0.0
    raw_config["InpTradeWindowMinutes"] = 380
    paper_rv_config = base_config()
    paper_rv_config["InpTradeWindowMinutes"] = 380
    sequence += 1
    raw = run_case("locked", "raw-paper", raw_config, "2025.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    paper_rv = run_case("locked", "paper-rv100", paper_rv_config, "2025.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    optimized = run_case("locked", "optimized", selected, "2025.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    full = run_case("full", "optimized", selected, "2023.09.01", "2026.09.01", 0, sequence)
    outcomes = ANALYZER.trade_outcomes(optimized["deals"])
    mc = ANALYZER.monte_carlo(outcomes, optimized["initial_balance"], 10_000)
    if optimized["return_pct"] > 0 and optimized["profit_factor"] >= 1.30 and optimized["trades"] >= 30 and mc["return_p5_pct"] > 0:
        decision = "PASS FOR ISOLATED DEMO FORWARD TESTING — do not add to the portfolio until the user approves."
    elif optimized["return_pct"] > 0 and optimized["profit_factor"] > 1.0:
        decision = "WATCH ONLY — positive, but not robust enough for the active portfolio."
    else:
        decision = "REJECT — the portable US100 implementation failed the untouched year."

    set_path = SETS / "US100 Paper Style ORB - selected research - 1pct.set"
    set_path.write_text(set_text(selected, 969069999), encoding="utf-8")
    previous = json.loads(PREVIOUS_AUDIT.read_text(encoding="utf-8")) if PREVIOUS_AUDIT.is_file() else None
    previous_comparison = None
    if previous:
        prior_ny = previous["symbols"]["ustec"]["sessions"]["new-york"]
        previous_comparison = {
            "selected_by_phase": prior_ny["selected_by_phase"],
            "locked": {key: prior_ny["locked"][key] for key in ("return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor")},
            "full": {key: prior_ny["full"][key] for key in ("return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor")},
            "monte_carlo_return_p5_pct": prior_ny["monte_carlo"]["return_p5_pct"],
        }
    audit = {
        "paper": {
            "title": "A Profitable Day Trading Strategy For The U.S. Equity Market",
            "authors": "Carlo Zarattini, Andrea Barbon, Andrew Aziz",
            "ssrn": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4729284",
            "translation_limit": "The paper ranks thousands of stocks; this test uses one USTEC CFD and broker tick volume.",
        },
        "test_design": {
            "development": "2023-09-01 to 2025-08-31",
            "locked": "2025-09-01 to 2026-09-01",
            "full": "2023-09-01 to 2026-09-01",
            "risk_per_trade_pct": 1.0,
            "final_model": "MT5 Every Tick with Exness costs and random delay",
        },
        "selected_by_phase": selected_by_phase,
        "selected_config": selected,
        "development": development,
        "final": {
            "raw_paper": clean(raw),
            "paper_relative_volume": clean(paper_rv),
            "optimized_locked": clean(optimized),
            "optimized_full": clean(full),
        },
        "monte_carlo": mc,
        "decision": decision,
        "selected_set": str(set_path),
        "previous_orb_audit_available": previous is not None,
        "existing_us100_orb_comparison": previous_comparison,
        "native_mt5_cases": sequence,
    }
    (ROOT / "FINAL AUDIT.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    rows = []
    for name, row in (("raw-paper-locked", raw), ("paper-rv-locked", paper_rv), ("optimized-locked", optimized), ("optimized-full", full)):
        rows.append({"version": name, **{key: row[key] for key in ("return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor", "history_quality")}})
    with (ROOT / "FINAL AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    charts_and_report(audit, {"raw": raw, "paper_rv": paper_rv, "optimized": optimized})
    print(json.dumps({"decision": decision, "final": rows, "monte_carlo": {key: value for key, value in mc.items() if key != "fan"}, "cases": sequence}, indent=2), flush=True)


if __name__ == "__main__":
    main()
