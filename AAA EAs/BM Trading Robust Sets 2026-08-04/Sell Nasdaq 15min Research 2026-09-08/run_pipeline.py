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
SOURCE = ROOT / "EA" / "Sell Nasdaq 15min EA.mq5"
EXPERT_FOLDER = "AAA Research\\Sell Nasdaq 15min"
EXPERT_NAME = "Sell Nasdaq 15min EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "Sell Nasdaq 15min"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "sell-nasdaq-15min-20260908"
TESTER_REPORTS = TESTER / "reports" / "sell-nasdaq-15min-20260908"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
CHARTS = ROOT / "Charts"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"


def load_analyzer():
    spec = importlib.util.spec_from_file_location("sell_nasdaq_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the native MT5 report analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


def compile_ea() -> None:
    EXPERT_DIR.mkdir(parents=True, exist_ok=True)
    for name in (SOURCE.name, "SafeRegimeFilter.mqh"):
        shutil.copy2(ROOT / "EA" / name, EXPERT_DIR / name)
    log = ROOT / "compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{log}"'
    result = subprocess.run(command, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = log.read_text(encoding="utf-16", errors="ignore") if log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"EA compile failed (exit {result.returncode}). Read {log}")
    shutil.copy2(EXPERT, ROOT / "EA" / EXPERT.name)


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


def base_config(require_london: bool) -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpNewYorkOpenHour": 9.5,
        "InpOpeningRangeMinutes": 15,
        "InpRequirePriorLondonBearish": require_london,
        "InpMinimumBodyFraction": 0.0,
        "InpMinimumSetupRangePips": 0.0,
        "InpMaximumSetupRangePips": 0.0,
        "InpEntryBufferPips": 0.0,
        "InpEntryWindowMinutes": 60,
        "InpCancelIfSetupHighBreaks": False,
        "InpTradeMonday": True,
        "InpTradeTuesday": True,
        "InpTradeWednesday": True,
        "InpTradeThursday": True,
        "InpTradeFriday": True,
        "InpRiskPercent": 1.0,
        "InpStopPips": 600.0,
        "InpTargetPips": 1000.0,
        "InpHardExitNyHour": 15.9166667,
        "InpBreakEvenAtR": 0.0,
        "InpTrailStartAtR": 0.0,
        "InpTrailDistanceR": 0.5,
        "InpUseDynamic5020": False,
        "InpMaxSpreadBrokerPoints": 0,
        "InpMaxDeviationBrokerPoints": 30,
        "InpMagic": 980908150,
        "InpUseAutomaticLiveServerOffset": True,
        "InpTesterServerClock": 0,
        "InpTesterManualUTCOffsetHours": 0,
        "InpManualLiveServerUTCOffsetHours": 0,
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


def run_case(
    phase: str,
    variant: str,
    config: dict[str, object],
    start: str,
    end: str,
    model: int,
    sequence: int,
) -> dict:
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode("utf-8")).hexdigest()[:8]
    case_id = f"ustec--{variant}--{phase}--{signature}"
    local_report = REPORTS / phase / f"{case_id}.htm"
    if local_report.is_file():
        return {
            "variant": variant,
            "phase": phase,
            "config": deepcopy(config),
            "path": str(local_report),
            **ANALYZER.parse_report(local_report),
        }

    set_name = f"Sell-Nasdaq-15min--{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(config, 980908000 + sequence), encoding="utf-8")
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
Period=M15
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
Report=reports\\sell-nasdaq-15min-20260908\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {phase:16s} {variant}", flush=True)
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
    parsed = {
        "variant": variant,
        "phase": phase,
        "config": deepcopy(config),
        "path": str(local_report),
        **ANALYZER.parse_report(local_report),
    }
    time.sleep(3)
    return parsed


def selection_score(row: dict, minimum_trades: int = 55) -> float:
    if row["trades"] < 15 or row["profit_factor"] <= 0:
        return -10000.0 + row["trades"]
    sample_penalty = max(0, minimum_trades - row["trades"]) * 0.28
    return (
        row["return_pct"]
        + 15.0 * math.log(max(row["profit_factor"], 0.05))
        - 1.30 * row["max_drawdown_pct"]
        + 0.22 * row["win_rate_pct"]
        + 0.40 * row["sharpe"]
        + 0.35 * row["recovery_factor"]
        - sample_penalty
    )


def choose(rows: list[dict], numeric: bool = False) -> dict:
    for row in rows:
        row["selection_score"] = selection_score(row)
    if numeric and len(rows) >= 3:
        raw_scores = [row["selection_score"] for row in rows]
        for index, row in enumerate(rows):
            neighbors = raw_scores[max(0, index - 1): min(len(rows), index + 2)]
            row["selection_score"] = 0.60 * raw_scores[index] + 0.40 * sorted(neighbors)[len(neighbors) // 2]
    adequately_sampled = [row for row in rows if row["trades"] >= 40]
    eligible = [row for row in adequately_sampled if row["return_pct"] > 0 and row["profit_factor"] > 1]
    return max(eligible or adequately_sampled or rows, key=lambda item: item["selection_score"])


def phase_cases(selected: dict[str, object]) -> list[tuple[str, list[tuple[str, dict[str, object]]], bool]]:
    phases: list[tuple[str, list[tuple[str, dict[str, object]]], bool]] = []

    def variants(items):
        return [(label, {**deepcopy(selected), **changes}) for label, changes in items]

    phases.append(("london-condition", variants([
        ("without-london", {"InpRequirePriorLondonBearish": False}),
        ("with-london", {"InpRequirePriorLondonBearish": True}),
    ]), False))
    phases.append(("stop", variants([
        (f"sl{value}", {"InpStopPips": float(value)})
        for value in (300, 450, 600, 750, 900, 1200)
    ]), True))
    phases.append(("target", variants([
        (f"tp{value}", {"InpTargetPips": float(value)})
        for value in (400, 600, 800, 1000, 1250, 1500, 2000)
    ]), True))
    phases.append(("entry-buffer", variants([
        (f"buffer{value}", {"InpEntryBufferPips": float(value)})
        for value in (0, 25, 50, 100, 150)
    ]), True))
    phases.append(("entry-window", variants([
        (f"window{value}", {"InpEntryWindowMinutes": value})
        for value in (15, 30, 60, 90, 120, 240, 360)
    ]), True))
    phases.append(("body", variants([
        (f"body{int(value * 100):02d}", {"InpMinimumBodyFraction": value})
        for value in (0.0, 0.2, 0.4, 0.6, 0.8)
    ]), True))
    phases.append(("minimum-range", variants([
        (f"minrange{value}", {"InpMinimumSetupRangePips": float(value)})
        for value in (0, 200, 400, 600)
    ]), True))
    minimum_range = float(selected["InpMinimumSetupRangePips"])
    max_items = [("maxrange-off", {"InpMaximumSetupRangePips": 0.0})]
    max_items += [
        (f"maxrange{value}", {"InpMaximumSetupRangePips": float(value)})
        for value in (800, 1200, 1600, 2400)
        if value > minimum_range
    ]
    phases.append(("maximum-range", variants(max_items), True))
    phases.append(("invalidation", variants([
        ("keep-after-high-break", {"InpCancelIfSetupHighBreaks": False}),
        ("cancel-on-high-break", {"InpCancelIfSetupHighBreaks": True}),
    ]), False))
    phases.append(("management", variants([
        ("none", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.0, "InpUseDynamic5020": False}),
        ("be050", {"InpBreakEvenAtR": 0.5, "InpTrailStartAtR": 0.0, "InpUseDynamic5020": False}),
        ("be075", {"InpBreakEvenAtR": 0.75, "InpTrailStartAtR": 0.0, "InpUseDynamic5020": False}),
        ("be100", {"InpBreakEvenAtR": 1.0, "InpTrailStartAtR": 0.0, "InpUseDynamic5020": False}),
        ("trail100-050", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 1.0, "InpTrailDistanceR": 0.5, "InpUseDynamic5020": False}),
        ("dynamic-50-20", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.0, "InpUseDynamic5020": True}),
    ]), False))
    phases.append(("weekdays", variants([
        ("mon-fri", {}),
        ("mon-thu", {"InpTradeFriday": False}),
        ("tue-fri", {"InpTradeMonday": False}),
        ("tue-thu", {"InpTradeMonday": False, "InpTradeFriday": False}),
        ("mon-wed", {"InpTradeThursday": False, "InpTradeFriday": False}),
        ("wed-fri", {"InpTradeMonday": False, "InpTradeTuesday": False}),
    ]), False))
    return phases


def joint_neighborhood(selected: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
    stop = float(selected["InpStopPips"])
    target = float(selected["InpTargetPips"])
    rows = []
    for stop_factor in (0.8, 1.0, 1.2):
        for target_factor in (0.8, 1.0, 1.2):
            sl = round(stop * stop_factor / 25.0) * 25.0
            tp = round(target * target_factor / 25.0) * 25.0
            rows.append((
                f"sl{int(sl)}-tp{int(tp)}",
                {**deepcopy(selected), "InpStopPips": sl, "InpTargetPips": tp},
            ))
    return rows


def table_line(label: str, row: dict) -> str:
    return (
        f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
        f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | "
        f"{row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
    )


def charts_and_report(audit: dict, final_rows: dict[str, dict]) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    plt.style.use("seaborn-v0_8-darkgrid")
    fig, axes = plt.subplots(2, 1, figsize=(15, 11), constrained_layout=True)
    for label, row, color in (
        ("Raw: no London condition", final_rows["raw_no_london"], "#8aa0b5"),
        ("Raw: bearish London condition", final_rows["raw_london"], "#4f86f7"),
        ("Pipeline selected", final_rows["selected"], "#18b981"),
    ):
        dates, balances = ANALYZER.equity_points(row, datetime(2025, 9, 1))
        axes[0].step(dates, balances, where="post", label=label, linewidth=1.8, color=color)
    axes[0].axhline(10000, color="#444", linestyle="--", linewidth=0.8)
    axes[0].set_title("Sell Nasdaq 15min — untouched locked-year equity")
    axes[0].set_ylabel("Balance (USD)")
    axes[0].legend(loc="best")
    axes[0].xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

    mc = audit["monte_carlo"]
    fan = mc["fan"]
    x = [point["trade"] for point in fan]
    axes[1].fill_between(x, [point["p5"] for point in fan], [point["p95"] for point in fan], color="#729cff", alpha=0.18, label="5–95%")
    axes[1].fill_between(x, [point["p25"] for point in fan], [point["p75"] for point in fan], color="#729cff", alpha=0.32, label="25–75%")
    axes[1].plot(x, [point["p50"] for point in fan], color="#18b981", linewidth=2, label="Median")
    axes[1].axhline(10000, color="#444", linestyle="--", linewidth=0.8)
    axes[1].set_title(f"10,000-path block-bootstrap — return P5 {mc['return_p5_pct']:+.2f}% | DD P95 {mc['max_dd_p95_pct']:.2f}%")
    axes[1].set_xlabel("Closed trades")
    axes[1].set_ylabel("Balance (USD)")
    axes[1].legend(loc="best")
    fig.savefig(CHARTS / "LOCKED EQUITY AND MONTE CARLO.png", dpi=180, facecolor="white")
    plt.close(fig)

    phases = list(audit["development"])
    fig, grid = plt.subplots(6, 2, figsize=(17, 25), constrained_layout=True)
    for axis, phase in zip(grid.flat, phases):
        rows = audit["development"][phase]
        labels = [row["variant"] for row in rows]
        returns = [row["return_pct"] for row in rows]
        colors = ["#18b981" if row["variant"] == audit["selected_by_phase"][phase] else "#8aa0b5" for row in rows]
        axis.barh(labels, returns, color=colors)
        axis.axvline(0, color="#333", linewidth=0.8)
        axis.set_title(f"{phase} — development return (%)")
    for axis in grid.flat[len(phases):]:
        axis.set_visible(False)
    fig.savefig(CHARTS / "DEVELOPMENT PIPELINE.png", dpi=170, facecolor="white")
    plt.close(fig)

    locked = audit["final"]
    full = locked["selected_full"]
    lines = [
        "# Sell Nasdaq 15min — full native MT5 pipeline", "",
        "## Decision", "", f"**{audit['decision']}**", "",
        "## Exact strategy interpretation", "",
        "- Instrument: Exness USTEC only.",
        "- 09:30–09:45 New York candle must close bearish.",
        "- Optional London condition: the immediately preceding 09:15–09:30 New York M15 candle must also close bearish.",
        "- Entry: sell stop at the first New York candle low, plus any selected downside buffer.",
        "- User baseline: 600-pip SL and 1,000-pip TP. Under the requested display convention, 1 pip = 10 broker points, or roughly 60/100 USTEC index points on this feed.",
        "- One attempted setup per New York day; automatic U.S. daylight-saving conversion.", "",
        "## Test design", "",
        "- Development: 2023-09-01 to 2025-09-01, native MT5 1-minute OHLC for sequential search.",
        "- Untouched locked year: 2025-09-01 to 2026-09-01, native MT5 Every Tick with broker costs and random delay.",
        "- Full reference: 2023-09-01 to 2026-09-01, native MT5 Every Tick.",
        "- Starting balance: $10,000; risk: exactly 1% of dynamic equity per filled trade.",
        "- Monte Carlo: 10,000 five-trade block-bootstrap paths from the untouched selected-version trades.",
        "- The New York 09:30 anchor, M15 setup candle and short-only direction were kept fixed so optimization could not rewrite the hypothesis.", "",
        "## Untouched locked-year results", "",
        "| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        table_line("Raw 600/1000 — without London", locked["raw_no_london"]),
        table_line("Raw 600/1000 — with London", locked["raw_london"]),
        table_line("Development-selected", locked["selected_locked"]), "",
        "## Selected three-year Every Tick reference", "",
        "| Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---:|---:|---:|---:|---:|---:|---:|",
        f"| {full['return_pct']:+.2f}% | {full['profit_factor']:.2f} | {full['win_rate_pct']:.2f}% | {full['max_drawdown_pct']:.2f}% | {full['trades']} | {full['sharpe']:.2f} | {full['recovery_factor']:.2f} |", "",
        "## Development selections", "",
    ]
    for phase, winner in audit["selected_by_phase"].items():
        lines.append(f"- {phase}: `{winner}`")
    selected = audit["selected_config"]
    lines += [
        "", "## Final selected inputs", "",
        f"- London condition: `{selected['InpRequirePriorLondonBearish']}`",
        f"- Stop / target: `{selected['InpStopPips']:.0f}` / `{selected['InpTargetPips']:.0f}` pips (nominal RR {selected['InpTargetPips']/selected['InpStopPips']:.2f})",
        f"- Entry buffer / expiry: `{selected['InpEntryBufferPips']:.0f}` pips / `{selected['InpEntryWindowMinutes']}` minutes",
        f"- Minimum body fraction: `{selected['InpMinimumBodyFraction']:.2f}`",
        f"- Setup range bounds: `{selected['InpMinimumSetupRangePips']:.0f}` to `{selected['InpMaximumSetupRangePips']:.0f}` pips (0 = disabled)",
        f"- Cancel if setup high breaks: `{selected['InpCancelIfSetupHighBreaks']}`",
        f"- Break-even / trailing / Dynamic 50-20: `{selected['InpBreakEvenAtR']}` / `{selected['InpTrailStartAtR']}` / `{selected['InpUseDynamic5020']}`", "",
        "## Monte Carlo", "",
        f"- Probability profitable: {mc['probability_profitable_pct']:.2f}%",
        f"- Return P5 / median / P95: {mc['return_p5_pct']:+.2f}% / {mc['return_median_pct']:+.2f}% / {mc['return_p95_pct']:+.2f}%",
        f"- Max drawdown median / P95: {mc['max_dd_median_pct']:.2f}% / {mc['max_dd_p95_pct']:.2f}%", "",
        "## Scope", "",
        "This is research evidence, not a guarantee. The active portfolio, recommended installer, BAT files and website were deliberately left unchanged pending user review.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    prepare()
    sequence = 0
    selected = base_config(require_london=False)
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
        print(f"SELECT {phase}: {winner['variant']} | {winner['return_pct']:+.2f}% PF {winner['profit_factor']:.2f} WR {winner['win_rate_pct']:.2f}% n={winner['trades']}", flush=True)

    neighborhood_rows = []
    for variant, config in joint_neighborhood(selected):
        sequence += 1
        neighborhood_rows.append(run_case("joint-neighborhood", variant, config, "2023.09.01", "2025.09.01", 1, sequence))
    winner = choose(neighborhood_rows)
    selected = deepcopy(winner["config"])
    selected_by_phase["joint-neighborhood"] = winner["variant"]
    development["joint-neighborhood"] = [clean(row) for row in neighborhood_rows]
    (ROOT / "joint-neighborhood-selection.json").write_text(
        json.dumps({"winner": clean(winner), "rows": development["joint-neighborhood"]}, indent=2, default=str),
        encoding="utf-8",
    )
    print(f"SELECT joint-neighborhood: {winner['variant']} | {winner['return_pct']:+.2f}% PF {winner['profit_factor']:.2f} WR {winner['win_rate_pct']:.2f}% n={winner['trades']}", flush=True)

    raw_no_london_config = base_config(require_london=False)
    raw_london_config = base_config(require_london=True)
    sequence += 1
    raw_no_london = run_case("locked", "raw-no-london", raw_no_london_config, "2025.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    raw_london = run_case("locked", "raw-with-london", raw_london_config, "2025.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    optimized = run_case("locked", "pipeline-selected", selected, "2025.09.01", "2026.09.01", 0, sequence)
    sequence += 1
    full = run_case("full", "pipeline-selected", selected, "2023.09.01", "2026.09.01", 0, sequence)

    outcomes = ANALYZER.trade_outcomes(optimized["deals"])
    mc = ANALYZER.monte_carlo(outcomes, optimized["initial_balance"], 10_000)
    if optimized["return_pct"] > 0 and optimized["profit_factor"] >= 1.30 and optimized["trades"] >= 30 and mc["return_p5_pct"] > 0:
        decision = "PASS FOR ISOLATED DEMO FORWARD TESTING — do not add to the portfolio until the user approves."
    elif optimized["return_pct"] > 0 and optimized["profit_factor"] > 1.0:
        decision = "WATCH ONLY — positive, but the untouched evidence is not strong enough for the active portfolio."
    else:
        decision = "REJECT — the selected configuration failed the untouched year."

    selected_set = SETS / "Sell Nasdaq 15min - selected research - 1pct.set"
    selected_set.write_text(set_text(selected, 980908999), encoding="utf-8")
    audit = {
        "strategy": "Sell Nasdaq 15min",
        "interpretation": {
            "prior_london_candle_ny": "09:15-09:30",
            "setup_candle_ny": "09:30-09:45",
            "setup_direction": "bearish",
            "entry": "sell stop at setup low",
            "pip_convention": "1 pip = 10 broker points",
        },
        "test_design": {
            "development": "2023-09-01 to 2025-09-01",
            "locked": "2025-09-01 to 2026-09-01",
            "full": "2023-09-01 to 2026-09-01",
            "risk_per_trade_pct": 1.0,
            "final_model": "MT5 Every Tick with Exness recorded costs and random delay",
        },
        "selected_by_phase": selected_by_phase,
        "selected_config": selected,
        "development": development,
        "final": {
            "raw_no_london": clean(raw_no_london),
            "raw_london": clean(raw_london),
            "selected_locked": clean(optimized),
            "selected_full": clean(full),
        },
        "monte_carlo": mc,
        "decision": decision,
        "selected_set": str(selected_set),
        "native_mt5_cases": sequence,
        "active_system_changed": False,
    }
    (ROOT / "FINAL AUDIT.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    rows = []
    for name, row in (
        ("raw-no-london-locked", raw_no_london),
        ("raw-with-london-locked", raw_london),
        ("pipeline-selected-locked", optimized),
        ("pipeline-selected-full", full),
    ):
        rows.append({
            "version": name,
            **{key: row[key] for key in ("return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor", "history_quality")},
        })
    with (ROOT / "FINAL AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    charts_and_report(audit, {"raw_no_london": raw_no_london, "raw_london": raw_london, "selected": optimized})
    print(json.dumps({
        "decision": decision,
        "selected": selected,
        "final": rows,
        "monte_carlo": {key: value for key, value in mc.items() if key != "fan"},
        "cases": sequence,
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
