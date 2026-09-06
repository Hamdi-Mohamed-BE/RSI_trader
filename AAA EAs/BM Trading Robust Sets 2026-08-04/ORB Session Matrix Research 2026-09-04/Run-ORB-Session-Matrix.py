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
PRIOR_ROOT = PACKAGE / "Robust ORB Research 2026-09-04"
PRIOR_SCRIPT = PRIOR_ROOT / "Run-Robust-ORB-Pipeline.py"
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
TERMINAL = TESTER / "terminal64.exe"
EXPERT_FOLDER = "BM Trading\\ORB Volume Data EA"
EXPERT_NAME = "ORB Volume Data EA"
EXPERT = TESTER / "MQL5" / "Experts" / "BM Trading" / "ORB Volume Data EA" / f"{EXPERT_NAME}.ex5"
CONFIGS = TESTER / "backtest-configs" / "orb-session-matrix-20260904"
TESTER_REPORTS = TESTER / "reports" / "orb-session-matrix-20260904"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
CHARTS = ROOT / "Charts"

SYMBOLS = ("xauusd", "ustec")
BROKER_SYMBOLS = {"xauusd": "XAUUSD", "ustec": "USTEC"}
DISPLAY = {"xauusd": "Gold (XAUUSD)", "ustec": "US100 (USTEC CFD)"}
PERIOD_NAMES = {1: "M1", 5: "M5", 15: "M15", 30: "M30"}

# These are genuine standalone opening ranges, not filters pasted over a New
# York opening range. UTC anchors intentionally match the existing system's
# research-session definitions. New York uses the EA's DST-aware clock.
SESSIONS = {
    "asia": {
        "label": "Asia 00:00 UTC",
        "zone": 1,
        "hour": 0,
        "minute": 0,
        "filter": 1,
        "flat_hour": 8,
        "flat_minute": 0,
    },
    "london": {
        "label": "London 07:00 UTC",
        "zone": 1,
        "hour": 7,
        "minute": 0,
        "filter": 2,
        "flat_hour": 12,
        "flat_minute": 0,
    },
    "new-york": {
        "label": "New York 09:30 local",
        "zone": 0,
        "hour": 9,
        "minute": 30,
        "filter": 3,
        "flat_hour": 15,
        "flat_minute": 55,
    },
    "overlap": {
        "label": "London/New York overlap 13:00 UTC",
        "zone": 1,
        "hour": 13,
        "minute": 0,
        "filter": 4,
        "flat_hour": 16,
        "flat_minute": 0,
    },
}


def load_prior_module():
    spec = importlib.util.spec_from_file_location("prior_orb_pipeline", PRIOR_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load prior ORB pipeline")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PRIOR = load_prior_module()
ANALYZER = PRIOR.ANALYZER


def prepare() -> None:
    for directory in (CONFIGS, TESTER_REPORTS, TESTER_SETS, REPORTS, SETS, CHARTS):
        directory.mkdir(parents=True, exist_ok=True)
    for required in (TERMINAL, EXPERT, PRIOR_ROOT / "FINAL AUDIT.json"):
        if not required.is_file():
            raise FileNotFoundError(required)
    active_config = (
        Path.home()
        / "AppData"
        / "Roaming"
        / "MetaQuotes"
        / "Terminal"
        / "D0E8209F77C8CF37AD8BF550E51FF075"
        / "config"
    )
    isolated_config = TESTER / "Config"
    isolated_config.mkdir(parents=True, exist_ok=True)
    for name in ("accounts.dat", "servers.dat", "common.ini"):
        source = active_config / name
        if source.is_file():
            shutil.copy2(source, isolated_config / name)


def base_config(session: str) -> dict[str, object]:
    values = PRIOR.base_config()
    spec = SESSIONS[session]
    values.update(
        InpSessionZone=spec["zone"],
        InpSessionHour=spec["hour"],
        InpSessionMinute=spec["minute"],
        InpFlatHour=spec["flat_hour"],
        InpFlatMinute=spec["flat_minute"],
        InpResearchSession=spec["filter"],
        InpResearchBrokerUtcOffsetMinutes=0,
        InpTradeWindowMinutes=180,
        InpOpeningRangeMinutes=15,
        InpSignalTimeframe=5,
        InpEntryMode=0,
        InpStopMode=1,
        InpStopBufferATR=0.10,
        InpMaximumStopATR=2.0,
        InpRewardRisk=1.5,
        InpBreakEvenAtR=0.0,
        InpTrailStartAtR=0.0,
        InpUseDynamicTrailingSL=False,
        InpRiskPercent=1.0,
        InpShowProfileLevels=False,
    )
    return values


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


def score(row: dict, minimum_trades: int = 30) -> float:
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


def choose(rows: list[dict], phase: str) -> dict:
    for row in rows:
        row["selection_score"] = score(row)
    if phase == "rr":
        ordered = sorted(rows, key=lambda item: float(item["config"]["InpRewardRisk"]))
        raw_scores = [item["selection_score"] for item in ordered]
        for index, row in enumerate(ordered):
            neighborhood = raw_scores[max(0, index - 1) : min(len(ordered), index + 2)]
            row["selection_score"] = 0.55 * row["selection_score"] + 0.45 * sorted(neighborhood)[len(neighborhood) // 2]
    eligible = [
        row
        for row in rows
        if row["return_pct"] > 0 and row["profit_factor"] > 1 and row["trades"] >= 30
    ]
    return max(eligible or rows, key=lambda item: item["selection_score"])


def run_case(
    symbol: str,
    session: str,
    phase: str,
    variant: str,
    config: dict[str, object],
    start: str,
    end: str,
    model: int,
    sequence: int,
) -> dict:
    case_id = f"{symbol}--{session}--{variant}--{phase}"
    local_report = REPORTS / phase / f"{case_id}.htm"
    if local_report.is_file():
        parsed = ANALYZER.parse_report(local_report)
        return {
            "symbol": symbol,
            "session": session,
            "variant": variant,
            "phase": phase,
            "config": deepcopy(config),
            "path": str(local_report),
            **parsed,
        }

    set_name = f"ORB-Session-{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 961000000 + sequence), encoding="utf-8")
    shutil.copy2(set_path, TESTER_SETS / set_name)

    tester_report = TESTER_REPORTS / f"{case_id}.htm"
    for stale in TESTER_REPORTS.glob(f"{case_id}*"):
        stale.unlink()
    signal_tf = int(config["InpSignalTimeframe"])
    period = PERIOD_NAMES[signal_tf]
    ini = f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert={EXPERT_FOLDER}\\{EXPERT_NAME}
ExpertParameters={set_name}
Symbol={BROKER_SYMBOLS[symbol]}
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
Report=reports\\orb-session-matrix-20260904\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {case_id}", flush=True)
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
    deadline = time.time() + 10
    while not tester_report.is_file() and time.time() < deadline:
        time.sleep(0.25)
    if not tester_report.is_file():
        raise FileNotFoundError(f"Missing MT5 report: {tester_report}")
    local_report.parent.mkdir(parents=True, exist_ok=True)
    for artifact in TESTER_REPORTS.glob(f"{case_id}*"):
        shutil.copy2(artifact, local_report.parent / artifact.name)
    parsed = ANALYZER.parse_report(local_report)
    return {
        "symbol": symbol,
        "session": session,
        "variant": variant,
        "phase": phase,
        "config": deepcopy(config),
        "path": str(local_report),
        **parsed,
    }


def run_stage(
    phase: str,
    candidates: dict[tuple[str, str], list[tuple[str, dict[str, object]]]],
    sequence: int,
) -> tuple[dict[tuple[str, str], dict], list[dict], int]:
    winners: dict[tuple[str, str], dict] = {}
    all_rows: list[dict] = []
    for symbol in SYMBOLS:
        for session in SESSIONS:
            rows: list[dict] = []
            for variant, config in candidates[(symbol, session)]:
                sequence += 1
                rows.append(
                    run_case(
                        symbol,
                        session,
                        phase,
                        variant,
                        config,
                        "2023.09.01",
                        "2025.08.31",
                        1,
                        sequence,
                    )
                )
            winner = choose(rows, phase)
            winners[(symbol, session)] = clean(winner)
            all_rows.extend(rows)
            print(
                f"WIN {phase} {symbol} {session}: {winner['variant']} "
                f"{winner['return_pct']:+.2f}% PF {winner['profit_factor']:.2f} "
                f"DD {winner['max_drawdown_pct']:.2f}% n={winner['trades']}",
                flush=True,
            )
    payload = {
        "phase": phase,
        "development_period": "2023-09-01 to 2025-08-31",
        "winners": {
            f"{symbol}::{session}": row for (symbol, session), row in winners.items()
        },
        "rows": [clean(row) for row in all_rows],
    }
    (ROOT / f"{phase}-selection.json").write_text(
        json.dumps(payload, indent=2, default=str), encoding="utf-8"
    )
    return winners, all_rows, sequence


def active_xau_config() -> dict[str, object]:
    path = (
        PACKAGE
        / "Selected Portfolio Settings 2026-09-01"
        / "05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set"
    )
    defaults = PRIOR.base_config()
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if "=" not in line:
            continue
        key, raw = line.split("=", 1)
        if key not in defaults:
            continue
        raw = raw.split("||", 1)[0].strip()
        exemplar = defaults[key]
        if isinstance(exemplar, bool):
            defaults[key] = raw.lower() == "true"
        elif isinstance(exemplar, int):
            defaults[key] = int(float(raw))
        elif isinstance(exemplar, float):
            defaults[key] = float(raw)
        else:
            defaults[key] = raw
    defaults["InpRiskPercent"] = 1.0
    defaults["InpResearchBrokerUtcOffsetMinutes"] = 0
    return defaults


def prior_us100_config() -> dict[str, object]:
    payload = json.loads((PRIOR_ROOT / "FINAL AUDIT.json").read_text(encoding="utf-8"))
    values = payload["symbols"]["ustec"]["selected_config"]
    values["InpRiskPercent"] = 1.0
    return values


def plot_development(phase_rows: dict[str, list[dict]], phase_winners: dict[str, dict]) -> None:
    import matplotlib.pyplot as plt

    # Timeframe/opening-range comparison: best result for each TF in each session.
    fig, axes = plt.subplots(2, 1, figsize=(16, 12), constrained_layout=True)
    fig.suptitle("ORB standalone sessions — development timeframe comparison", fontsize=18, fontweight="bold")
    for axis, symbol in zip(axes, SYMBOLS):
        rows = [row for row in phase_rows["structure"] if row["symbol"] == symbol]
        labels, values, annotations = [], [], []
        for session in SESSIONS:
            for timeframe in PERIOD_NAMES:
                subset = [
                    row
                    for row in rows
                    if row["session"] == session
                    and int(row["config"]["InpSignalTimeframe"]) == timeframe
                ]
                best = max(subset, key=score)
                labels.append(f"{session}\n{PERIOD_NAMES[timeframe]}")
                values.append(best["return_pct"])
                annotations.append(
                    f"OR{best['config']['InpOpeningRangeMinutes']}\nPF {best['profit_factor']:.2f}\nDD {best['max_drawdown_pct']:.1f}%"
                )
        colors = ["#18b981" if value > 0 else "#e35d6a" for value in values]
        bars = axis.bar(range(len(values)), values, color=colors)
        axis.set_xticks(range(len(labels)), labels, fontsize=8)
        axis.axhline(0, color="#333", linewidth=0.8)
        axis.set_ylabel("Return (%)")
        axis.set_title(DISPLAY[symbol])
        axis.grid(axis="y", alpha=0.2)
        for bar, text in zip(bars, annotations):
            y = bar.get_height()
            axis.text(bar.get_x() + bar.get_width() / 2, y, text, ha="center", va="bottom" if y >= 0 else "top", fontsize=7)
    fig.savefig(CHARTS / "DEVELOPMENT SESSION TIMEFRAME COMPARISON.png", dpi=180, facecolor="white")
    plt.close(fig)

    # RR response curves are deliberately shown per standalone session.
    fig, axes = plt.subplots(2, 2, figsize=(16, 11), constrained_layout=True)
    fig.suptitle("ORB standalone sessions — RR response on development data", fontsize=18, fontweight="bold")
    for row_index, symbol in enumerate(SYMBOLS):
        for session in SESSIONS:
            rows = sorted(
                [
                    row
                    for row in phase_rows["rr"]
                    if row["symbol"] == symbol and row["session"] == session
                ],
                key=lambda item: float(item["config"]["InpRewardRisk"]),
            )
            rr = [float(row["config"]["InpRewardRisk"]) for row in rows]
            axes[row_index, 0].plot(rr, [row["return_pct"] for row in rows], marker="o", label=session)
            axes[row_index, 1].plot(rr, [row["profit_factor"] for row in rows], marker="o", label=session)
        axes[row_index, 0].axhline(0, color="#333", linewidth=0.8)
        axes[row_index, 1].axhline(1, color="#333", linewidth=0.8)
        axes[row_index, 0].set_title(f"{DISPLAY[symbol]} — return")
        axes[row_index, 1].set_title(f"{DISPLAY[symbol]} — profit factor")
        for axis in axes[row_index]:
            axis.set_xlabel("Target RR")
            axis.grid(alpha=0.2)
            axis.legend()
    fig.savefig(CHARTS / "DEVELOPMENT RR BY SESSION.png", dpi=180, facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(16, 12), constrained_layout=True)
    fig.suptitle("ORB standalone sessions — stop placement comparison", fontsize=18, fontweight="bold")
    for axis, symbol in zip(axes, SYMBOLS):
        rows = [row for row in phase_rows["stop"] if row["symbol"] == symbol]
        ordered = sorted(rows, key=lambda item: (item["session"], item["variant"]))
        labels = [f"{row['session']}\n{row['variant']}" for row in ordered]
        values = [row["return_pct"] for row in ordered]
        colors = ["#18b981" if row["profit_factor"] > 1 else "#e35d6a" for row in ordered]
        axis.bar(range(len(values)), values, color=colors)
        axis.set_xticks(range(len(labels)), labels, rotation=50, ha="right", fontsize=7)
        axis.axhline(0, color="#333", linewidth=0.8)
        axis.set_ylabel("Return (%)")
        axis.set_title(DISPLAY[symbol])
        axis.grid(axis="y", alpha=0.2)
    fig.savefig(CHARTS / "DEVELOPMENT STOP BY SESSION.png", dpi=180, facecolor="white")
    plt.close(fig)


def plot_final(audit: dict, raw_locked: dict[tuple[str, str], dict]) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 1, figsize=(16, 12), constrained_layout=True)
    fig.suptitle("ORB standalone sessions — untouched locked-year equity", fontsize=18, fontweight="bold")
    colors = {"asia": "#7d74ff", "london": "#f4b942", "new-york": "#18b981", "overlap": "#4ca6ff"}
    for axis, symbol in zip(axes, SYMBOLS):
        for session in SESSIONS:
            row = raw_locked[(symbol, session)]
            dates, balances = ANALYZER.equity_points(row, datetime(2025, 9, 1))
            axis.step(dates, balances, where="post", label=session, color=colors[session], linewidth=1.5)
        axis.axhline(10000, color="#333", linestyle="--", linewidth=0.8)
        axis.set_title(DISPLAY[symbol])
        axis.set_ylabel("Balance (USD)")
        axis.grid(alpha=0.2)
        axis.legend()
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.savefig(CHARTS / "LOCKED EQUITY BY SESSION.png", dpi=180, facecolor="white")
    plt.close(fig)

    fig, axes = plt.subplots(2, 1, figsize=(16, 10), constrained_layout=True)
    fig.suptitle("ORB standalone sessions — locked-year return, PF and drawdown", fontsize=18, fontweight="bold")
    for axis, symbol in zip(axes, SYMBOLS):
        rows = [audit["symbols"][symbol]["sessions"][session]["locked"] for session in SESSIONS]
        x = list(range(len(SESSIONS)))
        returns = [row["return_pct"] for row in rows]
        axis.bar([value - 0.22 for value in x], returns, width=0.42, color="#18b981", label="Return %")
        axis.bar([value + 0.22 for value in x], [-row["max_drawdown_pct"] for row in rows], width=0.42, color="#e35d6a", label="-Max DD %")
        axis.axhline(0, color="#333", linewidth=0.8)
        axis.set_xticks(x, list(SESSIONS))
        axis.set_title(DISPLAY[symbol])
        axis.grid(axis="y", alpha=0.2)
        axis.legend(loc="best")
        for index, row in enumerate(rows):
            axis.text(index, max(returns[index], 0), f"PF {row['profit_factor']:.2f}\nn={row['trades']}", ha="center", va="bottom", fontsize=8)
    fig.savefig(CHARTS / "LOCKED SESSION METRICS.png", dpi=180, facecolor="white")
    plt.close(fig)


def verdict(row: dict, mc: dict) -> str:
    if (
        row["return_pct"] > 0
        and row["profit_factor"] >= 1.15
        and row["trades"] >= 30
        and row["max_drawdown_pct"] <= 12
        and mc["return_p5_pct"] > 0
    ):
        return "PASS / demo candidate"
    if row["return_pct"] > 0 and row["profit_factor"] > 1:
        return "WATCH / insufficient robustness"
    return "REJECT"


def write_report(audit: dict) -> None:
    lines = [
        "# Step 6 — ORB Session × RR × Stop × Timeframe Audit",
        "",
        "## Test design",
        "",
        "Each session is a genuine standalone opening range: Asia 00:00 UTC, London 07:00 UTC, New York 09:30 local (DST-aware), and London/New York overlap 13:00 UTC. Risk is fixed at 1% of current equity.",
        "",
        "Development selection used 2023-09-01 through 2025-08-31 with MT5 1-minute OHLC. The untouched locked test used 2025-09-01 through 2026-09-01 with Every Tick, broker spread, commission, swap and random delay. Three-year results are context because they include development data.",
        "",
    ]
    for symbol in SYMBOLS:
        item = audit["symbols"][symbol]
        lines += [
            f"## {DISPLAY[symbol]}",
            "",
            f"Development-selected session: **{item['development_selected_session']}** — locked verdict: **{item['development_selected_verdict']}**.",
            "",
            "| Session | Final configuration | Locked return | PF | Win | DD | Trades | Sharpe | Recovery | MC P5 | MC DD P95 | 3Y return | 3Y PF |",
            "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for session in SESSIONS:
            result = item["sessions"][session]
            row = result["locked"]
            full = result["full"]
            mc = result["monte_carlo"]
            config = result["selected_config"]
            setup = (
                f"{PERIOD_NAMES[int(config['InpSignalTimeframe'])]} / OR{config['InpOpeningRangeMinutes']} / "
                f"{config['InpRewardRisk']}R / {result['selected_by_phase']['stop']} / "
                f"{result['selected_by_phase']['management']} / {config['InpTradeWindowMinutes']}m"
            )
            lines.append(
                f"| {SESSIONS[session]['label']} | {setup} | {row['return_pct']:+.2f}% | "
                f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | "
                f"{row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} | "
                f"{mc['return_p5_pct']:+.2f}% | {mc['max_dd_p95_pct']:.2f}% | "
                f"{full['return_pct']:+.2f}% | {full['profit_factor']:.2f} |"
            )
        baseline = item["comparison_baseline"]
        lines += [
            "",
            f"Existing comparator: {baseline['label']} — {baseline['locked']['return_pct']:+.2f}% return, PF {baseline['locked']['profit_factor']:.2f}, win {baseline['locked']['win_rate_pct']:.2f}%, DD {baseline['locked']['max_drawdown_pct']:.2f}%, {baseline['locked']['trades']} trades.",
            "",
        ]
    lines += [
        "## Integrity",
        "",
        "- RR values tested separately inside every session: 0.5, 0.75, 1, 1.5, 2, 2.5, 3 and 4.",
        "- Signal timeframes tested separately inside every session: M1, M5, M15 and M30, with 5, 15 and 30-minute opening ranges.",
        "- Stop families tested separately inside every session: signal-candle and opposite-range stops with ATR buffers and 1.5–2.5 ATR caps.",
        "- Management tested separately inside every session: none, 0.5R/1R break-even, 0.5R/1R candle trail, and Dynamic 50/20.",
        "- Trade windows tested separately inside every session: 30, 60, 90, 120 and 180 minutes.",
        "- The best session was selected on development data before the locked period was read.",
        "- Exness USTEC is a CFD and its tick activity is not centralized CME NQ/MNQ volume.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    prepare()
    sequence = 0
    phase_rows: dict[str, list[dict]] = {}
    phase_winners: dict[str, dict] = {}

    structure_candidates: dict[tuple[str, str], list[tuple[str, dict[str, object]]]] = {}
    for symbol in SYMBOLS:
        for session in SESSIONS:
            candidates = []
            for timeframe in PERIOD_NAMES:
                for opening_range in (5, 15, 30):
                    config = base_config(session)
                    config.update(
                        InpSignalTimeframe=timeframe,
                        InpOpeningRangeMinutes=opening_range,
                    )
                    candidates.append((f"{PERIOD_NAMES[timeframe].lower()}-or{opening_range}", config))
            structure_candidates[(symbol, session)] = candidates
    winners, rows, sequence = run_stage("structure", structure_candidates, sequence)
    phase_winners["structure"] = {f"{s}::{q}": r for (s, q), r in winners.items()}
    phase_rows["structure"] = [clean(row) for row in rows]

    stop_candidates: dict[tuple[str, str], list[tuple[str, dict[str, object]]]] = {}
    stop_specs = (
        ("signal-b05-max1.5", 0, 0.05, 1.5),
        ("signal-b10-max2", 0, 0.10, 2.0),
        ("signal-b10-max2.5", 0, 0.10, 2.5),
        ("opposite-b05-max1.5", 1, 0.05, 1.5),
        ("opposite-b10-max2", 1, 0.10, 2.0),
        ("opposite-b10-max2.5", 1, 0.10, 2.5),
    )
    for key, selected in winners.items():
        candidates = []
        for label, mode, buffer, maximum in stop_specs:
            config = deepcopy(selected["config"])
            config.update(
                InpStopMode=mode,
                InpStopBufferATR=buffer,
                InpMaximumStopATR=maximum,
            )
            candidates.append((label, config))
        stop_candidates[key] = candidates
    winners, rows, sequence = run_stage("stop", stop_candidates, sequence)
    phase_winners["stop"] = {f"{s}::{q}": r for (s, q), r in winners.items()}
    phase_rows["stop"] = [clean(row) for row in rows]

    rr_candidates: dict[tuple[str, str], list[tuple[str, dict[str, object]]]] = {}
    for key, selected in winners.items():
        candidates = []
        for rr in (0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0):
            config = deepcopy(selected["config"])
            config["InpRewardRisk"] = rr
            candidates.append((f"rr{rr:g}", config))
        rr_candidates[key] = candidates
    winners, rows, sequence = run_stage("rr", rr_candidates, sequence)
    phase_winners["rr"] = {f"{s}::{q}": r for (s, q), r in winners.items()}
    phase_rows["rr"] = [clean(row) for row in rows]

    management_candidates: dict[tuple[str, str], list[tuple[str, dict[str, object]]]] = {}
    management_specs = (
        ("none", 0.0, 0.0, False),
        ("be05", 0.5, 0.0, False),
        ("be1", 1.0, 0.0, False),
        ("trail05", 0.0, 0.5, False),
        ("trail1", 0.0, 1.0, False),
        ("dynamic5020", 0.0, 0.0, True),
    )
    for key, selected in winners.items():
        candidates = []
        for label, break_even, trail, dynamic in management_specs:
            config = deepcopy(selected["config"])
            config.update(
                InpBreakEvenAtR=break_even,
                InpTrailStartAtR=trail,
                InpUseDynamicTrailingSL=dynamic,
            )
            candidates.append((label, config))
        management_candidates[key] = candidates
    winners, rows, sequence = run_stage("management", management_candidates, sequence)
    phase_winners["management"] = {f"{s}::{q}": r for (s, q), r in winners.items()}
    phase_rows["management"] = [clean(row) for row in rows]

    window_candidates: dict[tuple[str, str], list[tuple[str, dict[str, object]]]] = {}
    for key, selected in winners.items():
        candidates = []
        for minutes in (30, 60, 90, 120, 180):
            config = deepcopy(selected["config"])
            config["InpTradeWindowMinutes"] = minutes
            candidates.append((f"window{minutes}", config))
        window_candidates[key] = candidates
    winners, rows, sequence = run_stage("window", window_candidates, sequence)
    phase_winners["window"] = {f"{s}::{q}": r for (s, q), r in winners.items()}
    phase_rows["window"] = [clean(row) for row in rows]

    # Choose the session on development data only, before running locked tests.
    development_selected: dict[str, str] = {}
    for symbol in SYMBOLS:
        candidates = [winners[(symbol, session)] for session in SESSIONS]
        development_selected[symbol] = max(candidates, key=score)["session"]

    audit = {
        "test_design": {
            "development": "2023-09-01 to 2025-08-31",
            "locked": "2025-09-01 to 2026-09-01",
            "full": "2023-09-01 to 2026-09-01",
            "risk_per_trade_pct": 1.0,
            "sessions": {name: values["label"] for name, values in SESSIONS.items()},
            "timeframes": list(PERIOD_NAMES.values()),
            "opening_ranges_minutes": [5, 15, 30],
            "rr_values": [0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0],
            "final_model": "MT5 Every Tick with Exness costs and random delay",
            "selection_rule": "All selections made on development data before locked results were read",
        },
        "development": phase_rows,
        "symbols": {},
    }
    raw_locked: dict[tuple[str, str], dict] = {}
    final_csv: list[dict] = []
    for symbol in SYMBOLS:
        audit["symbols"][symbol] = {
            "development_selected_session": development_selected[symbol],
            "sessions": {},
        }
        for session in SESSIONS:
            config = deepcopy(winners[(symbol, session)]["config"])
            sequence += 1
            locked = run_case(
                symbol,
                session,
                "locked",
                "development-selected",
                config,
                "2025.09.01",
                "2026.09.01",
                0,
                sequence,
            )
            sequence += 1
            full = run_case(
                symbol,
                session,
                "full",
                "development-selected",
                config,
                "2023.09.01",
                "2026.09.01",
                0,
                sequence,
            )
            outcomes = ANALYZER.trade_outcomes(locked["deals"])
            mc = ANALYZER.monte_carlo(outcomes, locked["initial_balance"], 10_000)
            item = {
                "selected_by_phase": {
                    phase: phase_winners[phase][f"{symbol}::{session}"]["variant"]
                    for phase in phase_winners
                },
                "selected_config": config,
                "locked": clean(locked),
                "full": clean(full),
                "monte_carlo": mc,
                "verdict": verdict(locked, mc),
            }
            audit["symbols"][symbol]["sessions"][session] = item
            raw_locked[(symbol, session)] = locked
            set_name = f"{symbol.upper()} - {session} - ORB research - 1pct.set"
            (SETS / set_name).write_text(
                set_text(config, 961100000 + sequence), encoding="utf-8"
            )
            final_csv.append(
                {
                    "symbol": symbol,
                    "session": session,
                    "development_selected_for_symbol": session == development_selected[symbol],
                    "verdict": item["verdict"],
                    "timeframe": PERIOD_NAMES[int(config["InpSignalTimeframe"])],
                    "opening_range_minutes": config["InpOpeningRangeMinutes"],
                    "rr": config["InpRewardRisk"],
                    "stop": item["selected_by_phase"]["stop"],
                    "management": item["selected_by_phase"]["management"],
                    "trade_window_minutes": config["InpTradeWindowMinutes"],
                    "locked_return_pct": locked["return_pct"],
                    "locked_pf": locked["profit_factor"],
                    "locked_win_pct": locked["win_rate_pct"],
                    "locked_dd_pct": locked["max_drawdown_pct"],
                    "locked_trades": locked["trades"],
                    "locked_sharpe": locked["sharpe"],
                    "locked_recovery": locked["recovery_factor"],
                    "mc_return_p5_pct": mc["return_p5_pct"],
                    "mc_dd_p95_pct": mc["max_dd_p95_pct"],
                    "full_return_pct": full["return_pct"],
                    "full_pf": full["profit_factor"],
                }
            )

        selected_session = development_selected[symbol]
        selected_item = audit["symbols"][symbol]["sessions"][selected_session]
        audit["symbols"][symbol]["development_selected_verdict"] = selected_item["verdict"]

        baseline_config = active_xau_config() if symbol == "xauusd" else prior_us100_config()
        baseline_label = (
            "Current active XAU Dynamic 50/20 ORB"
            if symbol == "xauusd"
            else "Prior development-selected US100 ORB"
        )
        sequence += 1
        baseline = run_case(
            symbol,
            "comparison",
            "locked",
            "existing-comparator",
            baseline_config,
            "2025.09.01",
            "2026.09.01",
            0,
            sequence,
        )
        audit["symbols"][symbol]["comparison_baseline"] = {
            "label": baseline_label,
            "config": baseline_config,
            "locked": clean(baseline),
        }

    (ROOT / "FINAL AUDIT.json").write_text(
        json.dumps(audit, indent=2, default=str), encoding="utf-8"
    )
    with (ROOT / "FINAL AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(final_csv[0]))
        writer.writeheader()
        writer.writerows(final_csv)

    plot_development(phase_rows, phase_winners)
    plot_final(audit, raw_locked)
    write_report(audit)
    print(json.dumps(final_csv, indent=2), flush=True)
    print(f"COMPLETED {sequence} native MT5 cases", flush=True)


if __name__ == "__main__":
    main()
