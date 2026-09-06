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
EXPERT_FOLDER = "AAA Research\\US100 Overnight 20260904"
EXPERT_NAME = "Nasdaq Overnight Negative Day EA"
EXPERT_TARGET = TESTER / "MQL5" / "Experts" / "AAA Research" / "US100 Overnight 20260904" / f"{EXPERT_NAME}.ex5"
SETS = ROOT / "Sets"
REPORTS = ROOT / "Backtest Reports"
CONFIGS = TESTER / "backtest-configs" / "overnight-20260904"
TESTER_REPORTS = TESTER / "reports" / "overnight-20260904"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("poc_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load shared MT5 report parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


def base_config() -> dict:
    return {
        "require_negative": True,
        "definition": 0,
        "threshold": 0.0,
        "friday": True,
        "entry_hour": 16,
        "entry_minute": 0,
        "exit_hour": 9,
        "exit_minute": 29,
        "stop_pct": 2.0,
        "rr": 0.0,
        "dynamic": False,
        "safe": False,
    }


def video_negative() -> dict:
    config = base_config()
    config.update(entry_hour=18, exit_hour=4, exit_minute=0)
    return config


def video_go_long() -> dict:
    config = video_negative()
    config["require_negative"] = False
    return config


def set_text(config: dict, magic: int) -> str:
    return f"""InpEnableTrading=true
InpRequireNegativeDay={str(config['require_negative']).lower()}
InpNegativeDayDefinition={config['definition']}
InpNegativeDayThresholdPercent={config['threshold']}
InpAllowFridayEntry={str(config['friday']).lower()}
InpCashOpenHour=9
InpCashOpenMinute=30
InpCashCloseHour=16
InpCashCloseMinute=0
InpEntryHour={config['entry_hour']}
InpEntryMinute={config['entry_minute']}
InpExitHour={config['exit_hour']}
InpExitMinute={config['exit_minute']}
InpEntryWindowMinutes=10
InpExitWindowMinutes=31
InpMinimumCashSessionBars=300
InpRiskPercent=1
InpEmergencyStopPercent={config['stop_pct']}
InpRewardRisk={config['rr']}
InpMaxSpreadPoints=0
InpMaxDeviationPoints=30
InpMagic={magic}
InpUseAutomaticLiveServerOffset=true
InpTesterServerUTCOffsetHours=0
InpManualLiveServerUTCOffsetHours=0
InpUseDynamicTrailingSL={str(config['dynamic']).lower()}
InpDynamicTriggerFraction=0.50
InpDynamicLockFraction=0.20
InpResearchSession=0
InpResearchBrokerUtcOffsetMinutes=0
InpUseMarkovRegimeFilter={str(config.get('safe', False)).lower()}
InpMarkovReturnWindow=40
InpMarkovThreshold=0.05
InpMarkovSignalGate=0.05
InpMarkovMinLabels=252
InpMarkovHistoryBars=2600
"""


def prepare() -> None:
    for path in (SETS, REPORTS, CONFIGS, TESTER_REPORTS, TESTER_SETS, EXPERT_TARGET.parent):
        path.mkdir(parents=True, exist_ok=True)
    if not TERMINAL.is_file() or not EXPERT_TARGET.is_file():
        raise FileNotFoundError("The isolated MT5 tester or compiled Overnight EA is missing")
    active = Path.home() / "AppData" / "Roaming" / "MetaQuotes" / "Terminal" / "D0E8209F77C8CF37AD8BF550E51FF075" / "config"
    isolated = TESTER / "Config"
    isolated.mkdir(parents=True, exist_ok=True)
    for name in ("accounts.dat", "servers.dat", "common.ini"):
        source = active / name
        if source.is_file():
            shutil.copy2(source, isolated / name)


def run_case(case_id: str, config: dict, start: str, end: str, model: int, sequence: int) -> dict:
    phase = case_id.split("--", 1)[0]
    out_dir = REPORTS / phase
    out_dir.mkdir(parents=True, exist_ok=True)
    set_name = f"Overnight-{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 940420000 + sequence), encoding="utf-8")
    shutil.copy2(set_path, TESTER_SETS / set_name)
    report_name = f"{case_id}.htm"
    tester_report = TESTER_REPORTS / report_name
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
Report=reports\\overnight-20260904\\{report_name}
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {case_id}", flush=True)
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
    for artifact in TESTER_REPORTS.glob(f"{case_id}*"):
        shutil.copy2(artifact, out_dir / artifact.name)
    parsed = ANALYZER.parse_report(tester_report)
    return {"case": case_id, "config": deepcopy(config), "path": str(out_dir / report_name), **parsed}


def selection_score(row: dict, minimum_trades: int = 30) -> float:
    if row["trades"] < 8 or row["profit_factor"] <= 0:
        return -10000 + row["trades"]
    penalty = max(0, minimum_trades - row["trades"]) * 0.4
    return (
        row["return_pct"]
        + 14 * math.log(max(row["profit_factor"], 0.05))
        - 0.9 * row["max_drawdown_pct"]
        + 0.6 * row["sharpe"]
        + 0.4 * row["recovery_factor"]
        - penalty
    )


def choose(rows: list[dict], phase: str, minimum_trades: int = 30) -> dict:
    for row in rows:
        row["selection_score"] = selection_score(row, minimum_trades)
    eligible = [row for row in rows if row["return_pct"] > 0 and row["profit_factor"] > 1 and row["trades"] >= minimum_trades]
    winner = max(eligible or rows, key=lambda row: row["selection_score"])
    serial = [{key: value for key, value in row.items() if key != "deals"} for row in rows]
    payload = {"phase": phase, "winner": {key: value for key, value in winner.items() if key != "deals"}, "rows": serial}
    (ROOT / f"{phase}-selection.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return winner


def plot_phase(rows: list[dict], phase: str, winner: dict) -> None:
    import matplotlib.pyplot as plt

    ordered = sorted(rows, key=lambda row: row["selection_score"], reverse=True)
    fig, ax = plt.subplots(figsize=(14, max(5, len(ordered) * 0.55)), constrained_layout=True)
    colors = ["#18b981" if row["case"] == winner["case"] else "#7395c9" for row in ordered]
    values = [row["return_pct"] for row in ordered]
    labels = [row["case"].split("--", 1)[1] for row in ordered]
    ax.barh(range(len(rows)), values, color=colors)
    ax.set_yticks(range(len(rows)), labels)
    ax.invert_yaxis()
    ax.axvline(0, color="#333", linewidth=0.8)
    ax.set_title(f"US100 Overnight — {phase} development comparison")
    ax.set_xlabel("Net return (%)")
    ax.grid(axis="x", alpha=0.2)
    for index, row in enumerate(ordered):
        ax.text(values[index], index, f" {values[index]:+.2f}% | PF {row['profit_factor']:.2f} | DD {row['max_drawdown_pct']:.2f}% | n={row['trades']}", va="center", fontsize=8)
    charts = ROOT / "Charts"
    charts.mkdir(exist_ok=True)
    fig.savefig(charts / f"{phase.upper()} COMPARISON.png", dpi=170, facecolor="white")
    plt.close(fig)


def run_phase(name: str, candidates: list[tuple[str, dict]], sequence: int) -> tuple[dict, int, list[dict]]:
    rows = []
    for variant, config in candidates:
        sequence += 1
        rows.append(run_case(f"{name}--{variant}", config, "2023.09.01", "2025.08.31", 1, sequence))
    winner = choose(rows, name)
    plot_phase(rows, name, winner)
    return winner, sequence, rows


def final_charts(rows: list[dict], mc: dict) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    charts = ROOT / "Charts"
    charts.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 7), constrained_layout=True)
    for row, color in zip(rows, ("#98a1ad", "#cc8b36", "#68a7ff", "#18b981")):
        dates, balances = ANALYZER.equity_points(row, datetime(2025, 9, 1))
        ax.step(dates, balances, where="post", label=row["case"].split("--", 1)[1], color=color, linewidth=1.7)
    ax.axhline(10000, color="#444", linestyle="--", linewidth=0.8)
    ax.set_title("US100 Overnight — untouched locked-year equity")
    ax.set_ylabel("Balance (USD)")
    ax.grid(alpha=0.2)
    ax.legend(loc="best")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.savefig(charts / "LOCKED YEAR EQUITY COMPARISON.png", dpi=180, facecolor="white")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(14, 7), constrained_layout=True)
    fan = mc["fan"]
    x = [point["trade"] for point in fan]
    ax.fill_between(x, [point["p5"] for point in fan], [point["p95"] for point in fan], color="#729cff", alpha=0.18, label="5–95%")
    ax.fill_between(x, [point["p25"] for point in fan], [point["p75"] for point in fan], color="#729cff", alpha=0.32, label="25–75%")
    ax.plot(x, [point["p50"] for point in fan], color="#18b981", linewidth=2, label="Median")
    ax.axhline(10000, color="#444", linestyle="--", linewidth=0.8)
    ax.set_title(f"US100 Overnight optimized — 10,000 paths | P5 {mc['return_p5_pct']:+.2f}% | DD95 {mc['max_dd_p95_pct']:.2f}%")
    ax.set_xlabel("Closed trades")
    ax.set_ylabel("Balance (USD)")
    ax.grid(alpha=0.2)
    ax.legend(loc="best")
    fig.savefig(charts / "LOCKED MONTE CARLO FAN.png", dpi=180, facecolor="white")
    plt.close(fig)


def clean_row(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def main() -> None:
    prepare()
    sequence = 0
    phase_rows: dict[str, list[dict]] = {}

    model_candidates: list[tuple[str, dict]] = []
    variants = [
        ("negative-cc-close-open", True, 0, 16, 9, 29),
        ("negative-oc-close-open", True, 1, 16, 9, 29),
        ("all-close-open", False, 0, 16, 9, 29),
        ("negative-cc-reopen-eu1", True, 0, 18, 2, 0),
        ("negative-cc-reopen-eu2", True, 0, 18, 3, 0),
        ("negative-cc-reopen-eu3", True, 0, 18, 4, 0),
        ("negative-cc-reopen-open", True, 0, 18, 9, 29),
        ("all-reopen-eu1", False, 0, 18, 2, 0),
        ("all-reopen-eu2", False, 0, 18, 3, 0),
        ("all-reopen-eu3", False, 0, 18, 4, 0),
        ("all-reopen-open", False, 0, 18, 9, 29),
    ]
    for label, require_negative, definition, entry_hour, exit_hour, exit_minute in variants:
        config = base_config()
        config.update(require_negative=require_negative, definition=definition, entry_hour=entry_hour, exit_hour=exit_hour, exit_minute=exit_minute)
        model_candidates.append((label, config))
    winner, sequence, phase_rows["model"] = run_phase("model", model_candidates, sequence)
    selected = deepcopy(winner["config"])

    stop_candidates = []
    for value in (0.5, 1.0, 1.5, 2.0, 3.0, 4.0):
        config = deepcopy(selected); config["stop_pct"] = value
        stop_candidates.append((f"stop-{value:g}pct", config))
    winner, sequence, phase_rows["stop"] = run_phase("stop", stop_candidates, sequence)
    selected = deepcopy(winner["config"])

    rr_candidates = []
    for value in (0.0, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0):
        config = deepcopy(selected); config["rr"] = value
        label = "calendar-exit" if value == 0 else f"rr-{value:g}"
        rr_candidates.append((label, config))
    winner, sequence, phase_rows["rr"] = run_phase("rr", rr_candidates, sequence)
    selected = deepcopy(winner["config"])

    if selected["require_negative"]:
        threshold_candidates = []
        for value in (0.0, 0.1, 0.25, 0.5, 1.0):
            config = deepcopy(selected); config["threshold"] = value
            threshold_candidates.append((f"threshold-{value:g}pct", config))
    else:
        threshold_candidates = [("not-applicable-unconditional", deepcopy(selected))]
    winner, sequence, phase_rows["threshold"] = run_phase("threshold", threshold_candidates, sequence)
    selected = deepcopy(winner["config"])

    trailing_candidates = []
    for label, value in (("none", False), ("dynamic-50-20", True)):
        config = deepcopy(selected); config["dynamic"] = value
        trailing_candidates.append((label, config))
    winner, sequence, phase_rows["trailing"] = run_phase("trailing", trailing_candidates, sequence)
    selected = deepcopy(winner["config"])

    friday_candidates = []
    for label, value in (("friday-on", True), ("friday-off", False)):
        config = deepcopy(selected); config["friday"] = value
        friday_candidates.append((label, config))
    winner, sequence, phase_rows["friday"] = run_phase("friday", friday_candidates, sequence)
    selected = deepcopy(winner["config"])

    locked_configs = [
        ("current-negative-close-open", base_config()),
        ("video-negative-reopen-eu3", video_negative()),
        ("video-go-long-reopen-eu3", video_go_long()),
        ("optimized", selected),
    ]
    locked_rows = []
    for label, config in locked_configs:
        sequence += 1
        locked_rows.append(run_case(f"locked--{label}", config, "2025.09.01", "2026.09.01", 0, sequence))
    sequence += 1
    full_row = run_case("full--optimized", selected, "2023.09.01", "2026.09.01", 0, sequence)
    optimized = next(row for row in locked_rows if row["case"].endswith("--optimized"))
    mc = ANALYZER.monte_carlo(ANALYZER.trade_outcomes(optimized["deals"]), optimized["initial_balance"], 10000)
    final_charts(locked_rows, mc)

    final = {
        "test_design": {
            "development": "2023-09-01 to 2025-08-31",
            "locked": "2025-09-01 to 2026-09-01",
            "full": "2023-09-01 to 2026-09-01",
            "risk_per_trade_pct": 1.0,
            "development_model": "MT5 1-minute OHLC",
            "final_model": "MT5 Every Tick with broker costs and random delay",
            "monte_carlo": "10,000 five-trade block-bootstrap paths",
        },
        "selected_config": selected,
        "development_phases": {phase: [clean_row(row) for row in rows] for phase, rows in phase_rows.items()},
        "locked": {row["case"].split("--", 1)[1]: clean_row(row) for row in locked_rows},
        "full_optimized": clean_row(full_row),
        "monte_carlo": mc,
    }
    (ROOT / "FINAL AUDIT.json").write_text(json.dumps(final, indent=2, default=str), encoding="utf-8")
    fields = ["case", "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor", "history_quality"]
    with (ROOT / "FINAL AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in [*locked_rows, full_row]:
            writer.writerow({key: row.get(key, "") for key in fields})

    report = [
        "# Step 4 — US100 Overnight + Go Long Optimization",
        "",
        "## Goal",
        "",
        "Compare the current negative-day close-to-open implementation with the video's futures-reopen/calendar alternatives, then select timing, stop, reward/risk, trailing and Friday handling on development data only. Risk stayed at 1% in every test.",
        "",
        "## Untouched locked-year results",
        "",
        "| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in locked_rows:
        label = row["case"].split("--", 1)[1]
        report.append(f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |")
    report += [
        "",
        "## Selected development configuration",
        "",
        f"`{json.dumps(selected, sort_keys=True)}`",
        "",
        "## Three-year result",
        "",
        f"Optimized: {full_row['return_pct']:+.2f}% return, PF {full_row['profit_factor']:.2f}, {full_row['win_rate_pct']:.2f}% wins, {full_row['max_drawdown_pct']:.2f}% max DD, {full_row['trades']} trades, Sharpe {full_row['sharpe']:.2f}, recovery {full_row['recovery_factor']:.2f}.",
        "",
        "## Monte Carlo",
        "",
        f"10,000 paths: profitable {mc['probability_profitable_pct']:.1f}%, return P5 {mc['return_p5_pct']:+.2f}%, median {mc['return_median_pct']:+.2f}%, P95 {mc['return_p95_pct']:+.2f}%, max-DD P95 {mc['max_dd_p95_pct']:.2f}%, ruin {mc['ruin_probability_pct']:.2f}%.",
        "",
        "## Integrity notes",
        "",
        "- The selected rules were chosen only on 2023-09-01 through 2025-08-31. The final year was not used for selection.",
        "- Final comparisons use native MT5 Every Tick data, broker spread, commission, swap and random execution delay.",
        "- The older Go Long binary is input-audited only and was not used for rule selection. The unconditional Go Long idea was implemented in the readable Overnight source so the timing and risk logic could be verified.",
        "- A fixed-R target is optional; calendar exit remains in force if the target is not reached.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    (SETS / "Overnight-optimized-locked.set").write_text(set_text(selected, 940429999), encoding="utf-8")
    print(f"Completed {sequence} native MT5 tests. Selected: {selected}")


if __name__ == "__main__":
    main()
