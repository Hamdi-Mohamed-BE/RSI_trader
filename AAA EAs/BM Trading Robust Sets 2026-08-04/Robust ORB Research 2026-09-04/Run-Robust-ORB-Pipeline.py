from __future__ import annotations

import csv
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
EXPERT_FOLDER = "BM Trading\\ORB Volume Data EA"
EXPERT_NAME = "ORB Volume Data EA"
EXPERT = TESTER / "MQL5" / "Experts" / "BM Trading" / "ORB Volume Data EA" / f"{EXPERT_NAME}.ex5"
ACTIVE_SET = PACKAGE / "Selected Portfolio Settings 2026-09-01" / "05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "robust-orb-20260904"
TESTER_REPORTS = TESTER / "reports" / "robust-orb-20260904"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
CHARTS = ROOT / "Charts"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"

SYMBOLS = ("xauusd", "xagusd", "btcusd", "us30", "ustec", "gbpjpy")
BROKER_SYMBOLS = {
    "xauusd": "XAUUSD",
    "xagusd": "XAGUSD",
    "btcusd": "BTCUSD",
    "us30": "US30",
    "ustec": "USTEC",
    "gbpjpy": "GBPJPY",
}
DISPLAY = {
    "xauusd": "Gold",
    "xagusd": "Silver",
    "btcusd": "Bitcoin",
    "us30": "US30",
    "ustec": "US100",
    "gbpjpy": "GBPJPY",
}
ANCHORS = {
    "xauusd": ((0, 9, 15, "0915ny"), (0, 9, 30, "0930ny")),
    "xagusd": ((0, 9, 15, "0915ny"), (0, 9, 30, "0930ny")),
    "btcusd": ((0, 9, 15, "0915ny"), (0, 9, 30, "0930ny")),
    "us30": ((0, 9, 15, "0915ny"), (0, 9, 30, "0930ny")),
    "ustec": ((0, 9, 15, "0915ny"), (0, 9, 30, "0930ny")),
    # 03:00 New York follows the London open for most of the year; 08:00 UTC
    # is the fixed-clock alternative. Both are tested instead of assuming one.
    "gbpjpy": ((0, 3, 0, "0300ny"), (1, 8, 0, "0800utc")),
}


def load_analyzer():
    spec = importlib.util.spec_from_file_location("mt5_report_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared MT5 report parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


def prepare() -> None:
    for directory in (CONFIGS, TESTER_REPORTS, REPORTS, SETS, CHARTS, TESTER_SETS):
        directory.mkdir(parents=True, exist_ok=True)
    if not TERMINAL.is_file() or not EXPERT.is_file() or not ACTIVE_SET.is_file():
        raise FileNotFoundError("The isolated MT5 tester, ORB EA, or active ORB SET is missing")
    active_config = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "D0E8209F77C8CF37AD8BF550E51FF075" / "config"
    isolated_config = TESTER / "Config"
    isolated_config.mkdir(parents=True, exist_ok=True)
    for name in ("accounts.dat", "servers.dat", "common.ini"):
        source = active_config / name
        if source.is_file():
            shutil.copy2(source, isolated_config / name)


def base_config() -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpSessionZone": 0,
        "InpSessionHour": 9,
        "InpSessionMinute": 30,
        "InpOpeningRangeMinutes": 15,
        "InpTradeWindowMinutes": 120,
        "InpFlatHour": 15,
        "InpFlatMinute": 55,
        "InpWeekdaysOnly": True,
        "InpSignalTimeframe": 5,
        "InpRelativeVolumeDays": 20,
        "InpMinOpeningRelativeVolume": 0.6,
        "InpBarVolumeLookback": 20,
        "InpMinBreakoutRelativeVolume": 0.8,
        "InpATRTimeframe": 15,
        "InpATRPeriod": 14,
        "InpMinRangeATR": 0.2,
        "InpMaxRangeATR": 1.8,
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
        "InpBreakoutBodyMinimum": 0.55,
        "InpBreakoutBufferATR": 0.03,
        "InpRetestBars": 3,
        "InpRetestToleranceATR": 0.15,
        "InpRetestBodyMinimum": 0.30,
        "InpStopMode": 1,
        "InpStopBufferATR": 0.10,
        "InpMaximumStopATR": 2.0,
        "InpRewardRisk": 1.5,
        "InpBreakEvenAtR": 0.0,
        "InpTrailStartAtR": 0.0,
        "InpTrailCandleBufferATR": 0.10,
        "InpRiskPercent": 1.0,
        "InpMaxSpreadRangePercent": 12.0,
        "InpMaxDeviationPoints": 30,
        "InpMagic": 960904001,
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


def baseline_config(symbol: str) -> dict[str, object]:
    config = base_config()
    config.update(
        InpSessionZone=0,
        InpSessionHour=9,
        InpSessionMinute=30,
        InpOpeningRangeMinutes=15,
        InpEntryMode=0,
        InpStopMode=1,
        InpRewardRisk=2.5,
        InpBreakEvenAtR=1.0,
        InpUseDynamicTrailingSL=True,
    )
    if symbol == "gbpjpy":
        config.update(InpSessionHour=3, InpSessionMinute=0, InpRewardRisk=1.5)
    return config


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def set_text(config: dict[str, object], magic: int) -> str:
    values = deepcopy(config)
    values["InpMagic"] = magic
    return "\n".join(f"{name}={render(value)}" for name, value in values.items()) + "\n"


def run_case(
    symbol: str,
    phase: str,
    variant: str,
    config: dict[str, object],
    start: str,
    end: str,
    model: int,
    sequence: int,
) -> dict:
    case_id = f"{symbol}--{variant}--{phase}"
    local_report = REPORTS / phase / f"{case_id}.htm"
    if local_report.is_file():
        return {"symbol": symbol, "variant": variant, "phase": phase, "config": deepcopy(config), "path": str(local_report), **ANALYZER.parse_report(local_report)}

    set_name = f"Robust-ORB-{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 960904000 + sequence), encoding="utf-8")
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
Symbol={BROKER_SYMBOLS[symbol]}
Period=M5
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
Report=reports\\robust-orb-20260904\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {case_id}", flush=True)
    command = f'"{TERMINAL}" /portable /config:"{ini_path}"'
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        process.wait(timeout=1200)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f"MT5 timed out: {case_id}")
    deadline = time.time() + 10
    while not tester_report.is_file() and time.time() < deadline:
        time.sleep(0.25)
    if not tester_report.is_file():
        raise FileNotFoundError(f"Missing MT5 report: {tester_report}")
    local_report.parent.mkdir(parents=True, exist_ok=True)
    for artifact in TESTER_REPORTS.glob(f"{case_id}*"):
        shutil.copy2(artifact, local_report.parent / artifact.name)
    return {"symbol": symbol, "variant": variant, "phase": phase, "config": deepcopy(config), "path": str(local_report), **ANALYZER.parse_report(local_report)}


def selection_score(row: dict, minimum_trades: int = 30) -> float:
    if row["trades"] < 8 or row["profit_factor"] <= 0:
        return -10000.0 + row["trades"]
    sample_penalty = max(0, minimum_trades - row["trades"]) * 0.45
    return (
        row["return_pct"]
        + 13.0 * math.log(max(row["profit_factor"], 0.05))
        - 0.90 * row["max_drawdown_pct"]
        + 0.60 * row["sharpe"]
        + 0.35 * row["recovery_factor"]
        - sample_penalty
    )


def clean(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def choose(rows: list[dict], phase: str, minimum_trades: int = 30) -> dict:
    for row in rows:
        row["selection_score"] = selection_score(row, minimum_trades)
    if phase == "rr":
        by_rr = sorted(rows, key=lambda row: float(row["config"]["InpRewardRisk"]))
        for index, row in enumerate(by_rr):
            neighborhood = by_rr[max(index - 1, 0): min(index + 2, len(by_rr))]
            neighbor_scores = sorted(item["selection_score"] for item in neighborhood)
            row["selection_score"] = 0.55 * row["selection_score"] + 0.45 * neighbor_scores[len(neighbor_scores) // 2]
    eligible = [row for row in rows if row["return_pct"] > 0 and row["profit_factor"] > 1 and row["trades"] >= minimum_trades]
    return max(eligible or rows, key=lambda row: row["selection_score"])


def structures(symbol: str) -> list[tuple[str, dict[str, object]]]:
    templates = (
        ("or5-direct", 5, 0, 0.6, 0.8, 0.55, False, False),
        ("or15-direct", 15, 0, 0.6, 0.8, 0.55, False, False),
        ("or30-direct", 30, 0, 0.6, 0.8, 0.55, False, False),
        ("or15-retest", 15, 1, 0.6, 0.8, 0.55, False, False),
        ("or15-rvol", 15, 0, 0.8, 1.2, 0.70, False, False),
        ("or15-trend", 15, 0, 0.6, 0.8, 0.55, True, True),
    )
    candidates = []
    for zone, hour, minute, anchor_label in ANCHORS[symbol]:
        for label, opening_range, entry_mode, open_rv, bar_rv, body, vwap, ema in templates:
            config = base_config()
            config.update(
                InpSessionZone=zone,
                InpSessionHour=hour,
                InpSessionMinute=minute,
                InpOpeningRangeMinutes=opening_range,
                InpEntryMode=entry_mode,
                InpMinOpeningRelativeVolume=open_rv,
                InpMinBreakoutRelativeVolume=bar_rv,
                InpBreakoutBodyMinimum=body,
                InpRequireVWAP=vwap,
                InpUseEMATrend=ema,
            )
            candidates.append((f"{anchor_label}-{label}", config))
    return candidates


def plot_phase(all_rows: list[dict], winners: dict[str, dict], phase: str) -> None:
    import matplotlib.pyplot as plt

    fig, grid = plt.subplots(3, 2, figsize=(17, 16), constrained_layout=True)
    fig.suptitle(f"Robust ORB — {phase} development comparison", fontsize=18, fontweight="bold")
    for axis, symbol in zip(grid.flat, SYMBOLS):
        rows = sorted((row for row in all_rows if row["symbol"] == symbol), key=lambda row: row["selection_score"], reverse=True)
        labels = [row["variant"] for row in rows]
        returns = [row["return_pct"] for row in rows]
        colors = ["#18b981" if row["variant"] == winners[symbol]["variant"] else "#7395c9" for row in rows]
        axis.barh(range(len(rows)), returns, color=colors)
        axis.set_yticks(range(len(rows)), labels, fontsize=7)
        axis.invert_yaxis()
        axis.axvline(0, color="#333", linewidth=0.8)
        axis.set_title(DISPLAY[symbol])
        axis.set_xlabel("Return (%)")
        axis.grid(axis="x", alpha=0.2)
        for index, row in enumerate(rows):
            axis.text(returns[index], index, f" {returns[index]:+.1f}% | PF {row['profit_factor']:.2f} | DD {row['max_drawdown_pct']:.1f}% | n={row['trades']}", va="center", fontsize=6.4)
    fig.savefig(CHARTS / f"{phase.upper()} DEVELOPMENT COMPARISON.png", dpi=170, facecolor="white")
    plt.close(fig)


def run_phase(
    phase: str,
    candidates_by_symbol: dict[str, list[tuple[str, dict[str, object]]]],
    sequence: int,
) -> tuple[dict[str, dict], list[dict], int]:
    all_rows: list[dict] = []
    winners: dict[str, dict] = {}
    for symbol in SYMBOLS:
        rows = []
        for variant, config in candidates_by_symbol[symbol]:
            sequence += 1
            rows.append(run_case(symbol, phase, variant, config, "2023.09.01", "2025.08.31", 1, sequence))
        winner = choose(rows, phase)
        winners[symbol] = clean(winner)
        all_rows.extend(rows)
    payload = {
        "phase": phase,
        "development_period": "2023-09-01 to 2025-08-31",
        "selection_policy": "Positive PF/return and at least 30 trades preferred; score penalizes drawdown and small samples. RR selection also rewards neighboring-setting stability.",
        "winners": winners,
        "rows": [clean(row) for row in all_rows],
    }
    (ROOT / f"{phase}-selection.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    plot_phase(all_rows, winners, phase)
    return winners, all_rows, sequence


def decision(row: dict, mc: dict) -> str:
    if row["return_pct"] > 0 and row["profit_factor"] >= 1.15 and row["trades"] >= 30 and row["max_drawdown_pct"] <= 12 and mc["return_p5_pct"] > 0:
        return "PASS / demo candidate"
    if row["return_pct"] > 0 and row["profit_factor"] > 1:
        return "WATCH / insufficient robustness"
    return "REJECT"


def final_charts(results: dict[str, dict]) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    equity_fig, equity_grid = plt.subplots(3, 2, figsize=(17, 16), constrained_layout=True)
    equity_fig.suptitle("Robust ORB — untouched locked-year baseline vs optimized", fontsize=18, fontweight="bold")
    mc_fig, mc_grid = plt.subplots(3, 2, figsize=(17, 16), constrained_layout=True)
    mc_fig.suptitle("Robust ORB — 10,000-path block-bootstrap Monte Carlo", fontsize=18, fontweight="bold")
    for equity_axis, mc_axis, symbol in zip(equity_grid.flat, mc_grid.flat, SYMBOLS):
        item = results[symbol]
        for label, row, color in (("Universal baseline", item["baseline_locked_raw"], "#98a1ad"), ("Development-selected", item["optimized_locked_raw"], "#18b981")):
            dates, balances = ANALYZER.equity_points(row, datetime(2025, 9, 1))
            equity_axis.step(dates, balances, where="post", label=label, color=color, linewidth=1.6)
        optimized = item["optimized_locked_raw"]
        equity_axis.axhline(10000, color="#444", linestyle="--", linewidth=0.8)
        equity_axis.set_title(f"{DISPLAY[symbol]} — {item['decision']} | {optimized['return_pct']:+.2f}% | PF {optimized['profit_factor']:.2f} | DD {optimized['max_drawdown_pct']:.2f}% | n={optimized['trades']}")
        equity_axis.set_ylabel("Balance (USD)")
        equity_axis.grid(alpha=0.2)
        equity_axis.legend(loc="best")
        equity_axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

        mc = item["monte_carlo"]
        fan = mc["fan"]
        x = [point["trade"] for point in fan]
        mc_axis.fill_between(x, [point["p5"] for point in fan], [point["p95"] for point in fan], color="#729cff", alpha=0.18, label="5–95%")
        mc_axis.fill_between(x, [point["p25"] for point in fan], [point["p75"] for point in fan], color="#729cff", alpha=0.32, label="25–75%")
        mc_axis.plot(x, [point["p50"] for point in fan], color="#18b981", linewidth=2, label="Median")
        mc_axis.axhline(10000, color="#444", linestyle="--", linewidth=0.8)
        mc_axis.set_title(f"{DISPLAY[symbol]} — return P5 {mc['return_p5_pct']:+.1f}% | DD P95 {mc['max_dd_p95_pct']:.1f}%")
        mc_axis.set_xlabel("Closed trades")
        mc_axis.set_ylabel("Balance (USD)")
        mc_axis.grid(alpha=0.2)
        mc_axis.legend(loc="best")
    equity_fig.savefig(CHARTS / "LOCKED BASELINE VS OPTIMIZED EQUITY.png", dpi=180, facecolor="white")
    mc_fig.savefig(CHARTS / "LOCKED MONTE CARLO FAN.png", dpi=180, facecolor="white")
    plt.close(equity_fig)
    plt.close(mc_fig)


def write_report(audit: dict) -> None:
    lines = [
        "# Step 5 — Robust ORB Research",
        "",
        "## Goal",
        "",
        "Test the claimed 09:15–09:30 pre-open range against the official 09:30 New York opening range, then select range length, entry confirmation, relative-volume/trend filters, stop placement, RR, trade window and trailing behavior on development data only.",
        "",
        "## Untouched locked-year results",
        "",
        "| Decision | Market | Best configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery | MC return P5 | MC DD P95 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol in SYMBOLS:
        item = audit["symbols"][symbol]
        row = item["optimized_locked"]
        selected = item["selected_config"]
        anchor = f"{int(selected['InpSessionHour']):02d}:{int(selected['InpSessionMinute']):02d} {'NY' if int(selected['InpSessionZone']) == 0 else 'UTC'}"
        config = f"{anchor}, OR{selected['InpOpeningRangeMinutes']}, {selected['InpRewardRisk']}R"
        mc = item["monte_carlo"]
        lines.append(f"| {item['decision']} | {DISPLAY[symbol]} | {config} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} | {mc['return_p5_pct']:+.2f}% | {mc['max_dd_p95_pct']:.2f}% |")
    lines += [
        "",
        "## Three-year context",
        "",
        "| Market | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol in SYMBOLS:
        row = audit["symbols"][symbol]["optimized_full"]
        lines.append(f"| {DISPLAY[symbol]} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |")
    lines += [
        "",
        "## Timing verdict",
        "",
        "09:15 New York is a pre-open range, not the official cash-market opening range. It was tested because of the supplied claim; the selected timing above is determined by development data and judged only by untouched locked-year performance.",
        "",
        "## Integrity and execution",
        "",
        "- Parameter selection used only 2023-09-01 through 2025-08-31 with MT5 1-minute OHLC.",
        "- The untouched test is 2025-09-01 through 2026-09-01 and uses native MT5 Every Tick, Exness spread, commission, swap and random execution delay.",
        "- The three-year run is context, not an independent validation because it includes development and locked data.",
        "- All tests risk 1% of current equity, as required. One position maximum per session and the configured intraday flat time remain enforced.",
        "- Exness volume is broker tick activity, not centralized futures/exchange volume. Relative-volume filters are therefore broker-specific.",
        "",
        "## Research basis",
        "",
        "- NYSE states that its opening auction process begins at 09:30 Eastern: https://www.nyse.com/trade/auctions",
        "- Tsai et al. align index-futures ORB timing with the underlying stock-market open and report that shorter probing windows worked better in US markets: https://doi.org/10.1109/ACCESS.2019.2899177",
        "- Mesfin's 2026 MNQ falsification study found no OHLCV signal family, including ORB, passed all cost-aware out-of-sample criteria. This is the reason for strict locked testing and rejection labels: https://arxiv.org/abs/2605.04004",
        "",
        "Charts are under `Charts`, exact native reports under `Backtest Reports`, and the chosen 1% presets under `Sets`.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    prepare()
    sequence = 0
    selections: dict[str, dict[str, dict]] = {}
    development: dict[str, list[dict]] = {}

    structure_candidates = {symbol: structures(symbol) for symbol in SYMBOLS}
    winners, rows, sequence = run_phase("structure", structure_candidates, sequence)
    selections["structure"] = winners
    development["structure"] = [clean(row) for row in rows]

    stop_candidates: dict[str, list[tuple[str, dict[str, object]]]] = {}
    for symbol in SYMBOLS:
        selected = deepcopy(winners[symbol]["config"])
        stop_candidates[symbol] = []
        for stop_mode in (0, 1):
            for buffer in (0.05, 0.10):
                for maximum in (1.5, 2.5):
                    config = deepcopy(selected)
                    config.update(InpStopMode=stop_mode, InpStopBufferATR=buffer, InpMaximumStopATR=maximum)
                    stop_candidates[symbol].append((f"{'signal' if stop_mode == 0 else 'opposite'}-b{int(buffer*100):02d}-max{maximum:g}", config))
    winners, rows, sequence = run_phase("stop", stop_candidates, sequence)
    selections["stop"] = winners
    development["stop"] = [clean(row) for row in rows]

    rr_candidates: dict[str, list[tuple[str, dict[str, object]]]] = {}
    for symbol in SYMBOLS:
        selected = deepcopy(winners[symbol]["config"])
        rr_candidates[symbol] = []
        for rr in (0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
            config = deepcopy(selected)
            config["InpRewardRisk"] = rr
            rr_candidates[symbol].append((f"rr{rr:g}", config))
    winners, rows, sequence = run_phase("rr", rr_candidates, sequence)
    selections["rr"] = winners
    development["rr"] = [clean(row) for row in rows]

    management_variants = (
        ("none", 0.0, 0.0, False),
        ("be05", 0.5, 0.0, False),
        ("be1", 1.0, 0.0, False),
        ("trail05", 0.0, 0.5, False),
        ("trail1", 0.0, 1.0, False),
        ("dynamic5020", 0.0, 0.0, True),
        ("be1-dynamic5020", 1.0, 0.0, True),
    )
    management_candidates: dict[str, list[tuple[str, dict[str, object]]]] = {}
    for symbol in SYMBOLS:
        selected = deepcopy(winners[symbol]["config"])
        management_candidates[symbol] = []
        for label, break_even, trail, dynamic in management_variants:
            config = deepcopy(selected)
            config.update(InpBreakEvenAtR=break_even, InpTrailStartAtR=trail, InpUseDynamicTrailingSL=dynamic)
            management_candidates[symbol].append((label, config))
    winners, rows, sequence = run_phase("management", management_candidates, sequence)
    selections["management"] = winners
    development["management"] = [clean(row) for row in rows]

    window_candidates: dict[str, list[tuple[str, dict[str, object]]]] = {}
    for symbol in SYMBOLS:
        selected = deepcopy(winners[symbol]["config"])
        window_candidates[symbol] = []
        for minutes in (30, 60, 90, 120, 180):
            config = deepcopy(selected)
            config["InpTradeWindowMinutes"] = minutes
            window_candidates[symbol].append((f"window{minutes}", config))
    winners, rows, sequence = run_phase("window", window_candidates, sequence)
    selections["window"] = winners
    development["window"] = [clean(row) for row in rows]

    audit = {
        "test_design": {
            "development": "2023-09-01 to 2025-08-31",
            "locked": "2025-09-01 to 2026-09-01",
            "full": "2023-09-01 to 2026-09-01",
            "risk_per_trade_pct": 1.0,
            "development_model": "MT5 1-minute OHLC",
            "final_model": "MT5 Every Tick with Exness costs and random delay",
            "monte_carlo": "10,000 five-trade block-bootstrap paths",
        },
        "development": development,
        "symbols": {},
    }
    final_rows = []
    raw_results: dict[str, dict] = {}
    for symbol in SYMBOLS:
        optimized_config = deepcopy(winners[symbol]["config"])
        sequence += 1
        baseline = run_case(symbol, "locked", "universal-baseline", baseline_config(symbol), "2025.09.01", "2026.09.01", 0, sequence)
        sequence += 1
        optimized = run_case(symbol, "locked", "optimized", optimized_config, "2025.09.01", "2026.09.01", 0, sequence)
        sequence += 1
        full = run_case(symbol, "full", "optimized", optimized_config, "2023.09.01", "2026.09.01", 0, sequence)
        outcomes = ANALYZER.trade_outcomes(optimized["deals"])
        mc = ANALYZER.monte_carlo(outcomes, optimized["initial_balance"], 10_000)
        verdict = decision(optimized, mc)
        set_name = f"{symbol.upper()} - {verdict.split(' /', 1)[0]} - Robust ORB M5 - 1pct.set"
        (SETS / set_name).write_text(set_text(optimized_config, 960909000 + SYMBOLS.index(symbol)), encoding="utf-8")
        audit["symbols"][symbol] = {
            "selected_by_phase": {phase: selections[phase][symbol]["variant"] for phase in selections},
            "selected_config": optimized_config,
            "baseline_locked": clean(baseline),
            "optimized_locked": clean(optimized),
            "optimized_full": clean(full),
            "monte_carlo": mc,
            "decision": verdict,
            "set": str(SETS / set_name),
        }
        raw_results[symbol] = {
            "baseline_locked_raw": baseline,
            "optimized_locked_raw": optimized,
            "decision": verdict,
            "monte_carlo": mc,
        }
        final_rows.append({"symbol": symbol, "decision": verdict, **{key: optimized[key] for key in ("return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor", "history_quality")}, "mc_return_p5_pct": mc["return_p5_pct"], "mc_dd_p95_pct": mc["max_dd_p95_pct"]})

    (ROOT / "FINAL AUDIT.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    with (ROOT / "FINAL AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(final_rows[0]))
        writer.writeheader()
        writer.writerows(final_rows)
    final_charts(raw_results)
    write_report(audit)
    print(json.dumps(final_rows, indent=2), flush=True)
    print(f"COMPLETED {sequence} native MT5 cases", flush=True)


if __name__ == "__main__":
    main()
