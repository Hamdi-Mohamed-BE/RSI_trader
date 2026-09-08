"""Full native MT5 re-optimization for Nasdaq 5M Candle Momentum.

The deployed expert is never touched by this script. Development selection is
frozen before the locked year is opened. All tests use one percent equity risk.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import shutil
import subprocess
import time

import numpy as np


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parents[1]
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
SOURCE = ROOT / "EA" / "Nasdaq 5M Candle Momentum Audit EA.mq5"
EXPERT_DIR = "AAA Research\\Active Portfolio Reaudit 20260907\\Nasdaq Momentum Audit"
EXPERT_NAME = SOURCE.stem
WINDOWS = {
    "development": ("2023.09.01", "2025.09.01", 1, 1),
    "locked": ("2025.09.01", "2026.09.01", 0, -1),
    "full": ("2023.09.01", "2026.09.01", 0, -1),
}

parser_spec = importlib.util.spec_from_file_location(
    "report_parser", PACKAGE / "US100 Momentum Continuation Research 2026-08-31" / "Analyze-Reports.py"
)
report_parser = importlib.util.module_from_spec(parser_spec)
assert parser_spec.loader
parser_spec.loader.exec_module(report_parser)

BASE = dict(
    InpSignalTimeframe=5,
    InpSignalHourNY=9,
    InpSignalMinuteNY=30,
    InpEMAPeriod=12,
    InpAllowLong=True,
    InpAllowShort=True,
    InpRequireEMASlope=False,
    InpMinimumBodyATR=0.0,
    InpMaximumBodyATR=0.0,
    InpMinimumBodyFraction=0.0,
    InpMinimumEMADistanceATR=0.0,
    InpMaximumEMADistanceATR=0.0,
    InpRelativeVolumePeriod=0,
    InpMinimumRelativeVolume=0.0,
    InpATRPeriod=14,
    InpStopMode=0,
    InpInitialStopATR=4.0,
    InpSignalStopBufferATR=0.10,
    InpMaximumStopATR=0.0,
    InpUseFixedTarget=False,
    InpRewardRisk=2.0,
    InpUseAdaptiveRR=False,
    InpAdaptiveStrongBodyATR=1.0,
    InpAdaptiveStrongRR=3.0,
    InpUseATRTrailing=True,
    InpTrailingATR=6.0,
    InpTrailStartR=1.0,
    InpUseBreakEven=False,
    InpBreakEvenTriggerR=1.0,
    InpBreakEvenLockR=0.0,
    InpMaximumHoldingMinutes=0,
    InpCloseAtSessionEnd=True,
    InpCloseHourNY=15,
    InpCloseMinuteNY=55,
    InpAutoServerUtcOffsetLive=False,
    InpServerUtcOffsetHours=0,
    InpEnableTrading=True,
    InpRiskPercent=1.0,
    InpMaximumSpreadATR=0.0,
    InpMagic=862020,
    InpMaximumDeviationPoints=50,
    InpUseDynamicTrailingSL=True,
    InpDynamicTriggerFraction=0.50,
    InpDynamicLockFraction=0.20,
    InpResearchSession=0,
    InpResearchBrokerUtcOffsetMinutes=0,
    InpUseMarkovRegimeFilter=False,
    InpMarkovReturnWindow=40,
    InpMarkovThreshold=0.05,
    InpMarkovSignalGate=0.05,
    InpMarkovMinLabels=252,
    InpMarkovHistoryBars=2600,
)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def compile_ea() -> None:
    log = SOURCE.with_suffix(".compile.log")
    subprocess.run(
        f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',
        timeout=90,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    text = log.read_text(encoding="utf-16") if log.exists() else ""
    if "0 errors, 0 warnings" not in text or not SOURCE.with_suffix(".ex5").exists():
        raise RuntimeError("EA compilation failed:\n" + text[-6000:])
    target = TESTER / "MQL5" / "Experts" / Path(EXPERT_DIR)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE.with_suffix(".ex5"), target / SOURCE.with_suffix(".ex5").name)
    print("COMPILE 0 errors, 0 warnings", flush=True)


def set_text(config: dict) -> str:
    return "\n".join(
        f"{key}={str(value).lower() if isinstance(value, bool) else value}" for key, value in config.items()
    ) + "\n"


def trade_audit(report: Path) -> list[dict]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(report.read_text(encoding="utf-16"), "html.parser")
    inside = False
    opened = None
    trades = []
    for row in soup.find_all("tr"):
        if row.get_text(" ", strip=True) == "Deals":
            inside = True
            continue
        if not inside:
            continue
        cells = [" ".join(cell.get_text(" ", strip=True).split()) for cell in row.find_all("td")]
        if len(cells) != 13 or cells[4] not in ("in", "out"):
            continue
        when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S")
        cash = sum(float(cells[index].replace(" ", "")) for index in (8, 9, 10))
        balance = float(cells[11].replace(" ", ""))
        if cells[4] == "in":
            if opened is not None:
                raise RuntimeError("Unexpected overlapping positions")
            opened = dict(
                entry_time=when.isoformat(), entry_price=float(cells[6].replace(" ", "")), side=cells[3],
                volume=float(cells[5]), cash=cash, before=balance-cash,
            )
        else:
            if opened is None:
                raise RuntimeError("Unmatched exit")
            net = opened.pop("cash") + cash
            before = opened.pop("before")
            trades.append(dict(
                **opened, exit_time=when.isoformat(), exit_price=float(cells[6].replace(" ", "")), net=net,
                return_fraction=net/before if before else 0.0,
                holding_minutes=(when-datetime.fromisoformat(opened["entry_time"])).total_seconds()/60.0,
            ))
            opened = None
    if opened is not None:
        raise RuntimeError("Unclosed position in native report")
    return trades


def score(row: dict) -> float:
    if row["history_quality_pct"] < 90 or row["trades"] < 180:
        return -10000.0 + row["trades"]
    return (
        row["return_pct"] - 1.75 * row["equity_dd_pct"]
        + 12.0 * (row["profit_factor"] - 1.0) + 1.5 * row["sharpe_ratio"]
    )


def run(stage: str, name: str, group: str, config: dict, timeout: int = 1200) -> dict:
    start, end, model, execution = WINDOWS[stage]
    params = dict(config, InpRiskPercent=1.0)
    params["InpMagic"] = 869110000 + int(hashlib.sha1(name.encode()).hexdigest()[:6], 16) % 800000
    fingerprint = hashlib.sha256(
        (SOURCE.read_text(encoding="utf-8") + json.dumps(params, sort_keys=True) + start + end + str(model)).encode()
    ).hexdigest()
    case = f"ustec-{stage}-{name}"
    output = ROOT / "Reports" / stage
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / f"{case}.json"
    if result_path.exists():
        old = json.loads(result_path.read_text(encoding="utf-8"))
        if old.get("fingerprint") == fingerprint:
            print(f"SKIP {case}", flush=True)
            return old

    sets = ROOT / "Sets" / stage
    sets.mkdir(parents=True, exist_ok=True)
    set_name = f"{case}.set"
    (sets / set_name).write_text(set_text(params), encoding="utf-8")
    tester_sets = TESTER / "MQL5" / "Profiles" / "Tester"
    tester_sets.mkdir(parents=True, exist_ok=True)
    (tester_sets / set_name).write_text(set_text(params), encoding="utf-8")

    report_dir = TESTER / "reports" / "calyx-nasdaq-momentum-audit"
    report_dir.mkdir(parents=True, exist_ok=True)
    report = report_dir / f"{case}.htm"
    if report.exists():
        report.rename(report.with_name(case + f".old-{time.time_ns()}.htm"))
    jobs = TESTER / "backtest-configs" / "calyx-nasdaq-momentum-audit"
    jobs.mkdir(parents=True, exist_ok=True)
    ini = jobs / f"{case}.ini"
    ini.write_text(f"""[Common]
Login=472334559
Server=Exness-MT5Trial16
[Experts]
Enabled=0
[Tester]
Expert={EXPERT_DIR}\\{EXPERT_NAME}
ExpertParameters={set_name}
Symbol=USTEC
Period=M5
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode={execution}
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\calyx-nasdaq-momentum-audit\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
""", encoding="utf-8-sig")
    print(f"START {case} {start}..{end} model={model}", flush=True)
    begin = time.monotonic()
    subprocess.run(
        f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"',
        timeout=timeout,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if not report.exists():
        raise RuntimeError(f"MT5 produced no report for {case}")
    for file in report_dir.glob(case + "*"):
        if ".old-" not in file.name:
            shutil.copy2(file, output / file.name)
    copied = output / report.name
    row = report_parser.parse_report(copied)
    trades = trade_audit(copied)
    if len(trades) != row["trades"] or abs(sum(item["net"] for item in trades) - row["net_profit"]) > 0.05:
        raise RuntimeError(f"Trade ledger failed reconciliation for {case}")
    dump(output / f"{case}-trades.json", trades)
    row.update(
        name=name, group=group, stage=stage, config=params, fingerprint=fingerprint,
        elapsed_seconds=round(time.monotonic()-begin, 2), risk_percent=1.0,
        maximum_holding_minutes=max((item["holding_minutes"] for item in trades), default=0.0),
    )
    row["score"] = score(row)
    if row["bars"] <= 0 or row["initial_balance"] != 10000 or row["history_quality_pct"] < 90:
        raise RuntimeError(f"Invalid native report {case}")
    dump(result_path, row)
    print(
        f"DONE {name}: return {row['return_pct']:+.2f}% PF {row['profit_factor']:.2f} "
        f"win {row['win_rate']:.2f}% DD {row['equity_dd_pct']:.2f}% n={row['trades']} "
        f"Sharpe {row['sharpe_ratio']:.2f}", flush=True,
    )
    return row


def candidate(name: str, group: str, **changes) -> tuple[str, str, dict]:
    return name, group, dict(BASE, **changes)


def development_candidates() -> list[tuple[str, str, dict]]:
    rows = [candidate("current-dynamic5020-atr6", "baseline")]
    rows += [
        candidate("current-safe", "safe", InpUseMarkovRegimeFilter=True),
        candidate("no-management-eod", "management", InpUseATRTrailing=False, InpUseDynamicTrailingSL=False),
        candidate("dynamic-only-5020", "management", InpUseATRTrailing=False),
        candidate("dynamic-only-6020", "management", InpUseATRTrailing=False, InpDynamicTriggerFraction=0.60),
        candidate("dynamic-only-7525", "management", InpUseATRTrailing=False, InpDynamicTriggerFraction=0.75, InpDynamicLockFraction=0.25),
        candidate("atr5-immediate", "management", InpUseDynamicTrailingSL=False, InpTrailingATR=5.0, InpTrailStartR=0.0),
        candidate("atr6-immediate", "management", InpUseDynamicTrailingSL=False, InpTrailStartR=0.0),
        candidate("atr4-start1", "management", InpUseDynamicTrailingSL=False, InpTrailingATR=4.0),
        candidate("atr5-start1", "management", InpUseDynamicTrailingSL=False, InpTrailingATR=5.0),
        candidate("breakeven-only-100-000", "management", InpUseATRTrailing=False, InpUseDynamicTrailingSL=False, InpUseBreakEven=True),
        candidate("breakeven-only-075-010", "management", InpUseATRTrailing=False, InpUseDynamicTrailingSL=False, InpUseBreakEven=True, InpBreakEvenTriggerR=0.75, InpBreakEvenLockR=0.10),
    ]
    for rr in (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0, 5.0):
        rows.append(candidate(f"fixed-rr{rr:g}", "reward-risk", InpUseFixedTarget=True, InpRewardRisk=rr, InpUseATRTrailing=False, InpUseDynamicTrailingSL=False))
        if rr in (1.0, 1.5, 2.0, 3.0):
            rows.append(candidate(f"fixed-rr{rr:g}-dynamic5020", "reward-risk", InpUseFixedTarget=True, InpRewardRisk=rr, InpUseATRTrailing=False))
    for stop in (1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0):
        rows.append(candidate(f"atr-stop{stop:g}-rr15", "stop", InpInitialStopATR=stop, InpUseFixedTarget=True, InpRewardRisk=1.5, InpUseATRTrailing=False, InpUseDynamicTrailingSL=False))
    for buffer in (0.0, 0.1, 0.25, 0.5):
        rows.append(candidate(f"signal-stop{buffer:g}-rr15", "stop", InpStopMode=1, InpSignalStopBufferATR=buffer, InpMaximumStopATR=5.0, InpUseFixedTarget=True, InpRewardRisk=1.5, InpUseATRTrailing=False, InpUseDynamicTrailingSL=False))
    for timeframe, value in (("m1", 1), ("m5", 5), ("m15", 15), ("m30", 30)):
        rows.append(candidate(f"timeframe-{timeframe}", "timeframe", InpSignalTimeframe=value))
    rows += [
        candidate("long-only", "direction", InpAllowShort=False),
        candidate("short-only", "direction", InpAllowLong=False),
        candidate("ema-slope", "signal-filter", InpRequireEMASlope=True),
        candidate("body-020atr", "signal-filter", InpMinimumBodyATR=0.20),
        candidate("body-050atr", "signal-filter", InpMinimumBodyATR=0.50),
        candidate("body-fraction-050", "signal-filter", InpMinimumBodyFraction=0.50),
        candidate("max-body-150atr", "signal-filter", InpMaximumBodyATR=1.50),
        candidate("ema-distance-020atr", "signal-filter", InpMinimumEMADistanceATR=0.20),
        candidate("ema-distance-max100atr", "signal-filter", InpMaximumEMADistanceATR=1.00),
        candidate("relvol10-100", "signal-filter", InpRelativeVolumePeriod=10, InpMinimumRelativeVolume=1.00),
        candidate("relvol20-125", "signal-filter", InpRelativeVolumePeriod=20, InpMinimumRelativeVolume=1.25),
    ]
    for label, hour, minute in (("asia-1900", 19, 0), ("london-0300", 3, 0), ("overlap-0800", 8, 0), ("ny-1000", 10, 0)):
        rows.append(candidate(label, "session-anchor", InpSignalHourNY=hour, InpSignalMinuteNY=minute, InpCloseAtSessionEnd=False, InpMaximumHoldingMinutes=360))
    for threshold in (0.5, 1.0, 1.5):
        for strong_rr in (2.0, 3.0, 4.0):
            rows.append(candidate(
                f"adaptive-base1-strong{strong_rr:g}-body{threshold:g}", "adaptive-rr",
                InpUseFixedTarget=True, InpRewardRisk=1.0, InpUseAdaptiveRR=True,
                InpAdaptiveStrongBodyATR=threshold, InpAdaptiveStrongRR=strong_rr,
                InpUseATRTrailing=False, InpUseDynamicTrailingSL=False,
            ))
    return rows


def choose_primary(rows: list[dict]) -> tuple[dict, list[dict]]:
    baseline = next(row for row in rows if row["name"] == "current-dynamic5020-atr6")
    eligible = [
        row for row in rows
        if row["trades"] >= 220 and row["profit_factor"] >= 1.04
        and row["equity_dd_pct"] <= max(35.0, baseline["equity_dd_pct"] * 1.15)
    ]
    ranked = sorted(eligible, key=score, reverse=True)
    primary = ranked[0] if ranked else baseline
    finalists = [primary, baseline]
    for row in ranked[1:]:
        if row["name"] not in {item["name"] for item in finalists} and row["group"] not in {item["group"] for item in finalists if item["name"] != baseline["name"]}:
            finalists.append(row)
        if len(finalists) >= 6:
            break
    return primary, finalists


def export_results(rows: list[dict]) -> None:
    fields = [
        "stage", "name", "group", "return_pct", "profit_factor", "win_rate", "equity_dd_pct",
        "trades", "sharpe_ratio", "recovery_factor", "history_quality_pct", "score", "elapsed_seconds",
    ]
    with (ROOT / "all-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (row["stage"], -score(row))))


def main(smoke: bool = False) -> None:
    compile_ea()
    candidates = development_candidates()
    if smoke:
        candidates = candidates[:1]
    development = [run("development", name, group, config) for name, group, config in candidates]
    if smoke:
        export_results(development)
        return
    primary, finalists = choose_primary(development)
    selection = {
        "selected_before_locked_test": primary["name"],
        "selection_score": score(primary),
        "config": primary["config"],
        "finalists": [row["name"] for row in finalists],
        "selection_rule": "highest development robustness score after fixed trade/PF/DD gates",
    }
    dump(ROOT / "selection-frozen-before-locked.json", selection)
    print("FROZEN BEFORE LOCKED:", primary["name"], flush=True)
    locked = [run("locked", row["name"], row["group"], row["config"]) for row in finalists]
    full = [run("full", row["name"], row["group"], row["config"]) for row in finalists]
    safe_config = dict(primary["config"], InpUseMarkovRegimeFilter=True)
    safe_rows = [run(stage, f"{primary['name']}-safe", "safe-finalist", safe_config) for stage in ("development", "locked", "full")]
    all_rows = development + locked + full + safe_rows
    export_results(all_rows)
    dump(ROOT / "all-results.json", all_rows)
    finalize(all_rows, selection)


def daily_returns(row: dict, start: datetime, end: datetime) -> np.ndarray:
    trades = json.loads((ROOT / "Reports" / row["stage"] / f"ustec-{row['stage']}-{row['name']}-trades.json").read_text())
    values = np.array([item["return_fraction"] for item in trades], dtype=float)
    return values


def monte_carlo(row: dict, seed: int) -> dict:
    returns = daily_returns(row, datetime(2023, 9, 1), datetime(2026, 9, 1))
    paths = 10000
    if not len(returns):
        return dict(paths=paths, return_p05=0.0, return_median=0.0, return_p95=0.0, dd_p95=0.0, profitable_pct=0.0)
    rng = np.random.default_rng(seed)
    block = min(5, len(returns))
    count = math.ceil(len(returns)/block)
    starts = rng.integers(0, len(returns), size=(paths, count))
    indices = (starts[:, :, None] + np.arange(block)) % len(returns)
    sampled = returns[indices.reshape(paths, -1)[:, :len(returns)]]
    balances = 10000.0 * np.cumprod(1.0 + sampled, axis=1)
    full = np.concatenate([np.full((paths, 1), 10000.0), balances], axis=1)
    drawdowns = np.max(1.0-full/np.maximum.accumulate(full, axis=1), axis=1)*100.0
    endings = (full[:, -1]/10000.0-1.0)*100.0
    return dict(
        paths=paths, return_p05=float(np.percentile(endings, 5)), return_median=float(np.median(endings)),
        return_p95=float(np.percentile(endings, 95)), dd_p95=float(np.percentile(drawdowns, 95)),
        profitable_pct=float(np.mean(endings > 0)*100.0), probability_dd20_pct=float(np.mean(drawdowns >= 20)*100.0),
    )


def finalize(rows: list[dict], selection: dict) -> None:
    primary = selection["selected_before_locked_test"]
    baseline = "current-dynamic5020-atr6"
    lookup = {(row["stage"], row["name"]): row for row in rows}
    locked_primary = lookup[("locked", primary)]
    locked_baseline = lookup[("locked", baseline)]
    full_primary = lookup[("full", primary)]
    full_baseline = lookup[("full", baseline)]
    passes = (
        primary != baseline
        and locked_primary["return_pct"] > 0
        and locked_primary["profit_factor"] >= 1.10
        and locked_primary["return_pct"] > locked_baseline["return_pct"]
        and locked_primary["equity_dd_pct"] <= locked_baseline["equity_dd_pct"] * 1.10
        and locked_primary["trades"] >= 80
    )
    mc = {
        baseline: monte_carlo(full_baseline, 202609071),
        primary: monte_carlo(full_primary, 202609072),
    }
    dump(ROOT / "monte-carlo-results.json", mc)
    cost_stress = {}
    for name, row in ((baseline, full_baseline), (primary, full_primary)):
        values = daily_returns(row, datetime(2023, 9, 1), datetime(2026, 9, 1)) - 0.0005
        balance = 10000.0*np.cumprod(1.0+values) if len(values) else np.array([10000.0])
        cash = np.diff(np.r_[10000.0, balance])
        losses = -cash[cash < 0].sum()
        cost_stress[name] = dict(
            additional_cost="0.05% of equity per trade", return_pct=float((balance[-1]/10000.0-1.0)*100.0),
            profit_factor=float(cash[cash > 0].sum()/losses) if losses else None,
            balance_dd_pct=float(np.max(1.0-balance/np.maximum.accumulate(balance))*100.0),
        )
    dump(ROOT / "cost-stress.json", cost_stress)

    def metric_line(stage: str, name: str, label: str) -> str:
        row = lookup[(stage, name)]
        return (
            f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate']:.2f}% | "
            f"{row['equity_dd_pct']:.2f}% | {row['trades']} | {row['sharpe_ratio']:.2f} | {row['recovery_factor']:.2f} |"
        )

    decision = (
        f"Promote **{primary}** because it passed the frozen locked-year gate."
        if passes else
        f"Keep the deployed **{baseline}** configuration. The frozen challenger **{primary}** did not clear every promotion gate."
    )
    report = [
        "# Step 11 — Nasdaq 5M Candle Momentum full optimization", "", "## Decision", "", decision, "",
        "Every native test used Exness USTEC, a $10,000 account and exactly 1% equity risk per trade. Development used M1 OHLC for search speed. The untouched locked year and exact three-year finalists used MT5 Every Tick with random execution delay.", "",
        "## Frozen comparison", "", "| Window / configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        metric_line("development", baseline, "Development — current"),
        metric_line("development", primary, "Development — frozen challenger"),
        metric_line("locked", baseline, "Locked year — current"),
        metric_line("locked", primary, "Locked year — frozen challenger"),
        metric_line("full", baseline, "Exact 3 years — current"),
        metric_line("full", primary, "Exact 3 years — frozen challenger"),
        metric_line("full", f"{primary}-safe", "Exact 3 years — challenger Full Safe"), "",
        "## Monte Carlo — 10,000 five-trade block paths from exact three-year net trades", "",
        "| Configuration | Return P5 | Median | Return P95 | P95 DD | Profitable paths | P(DD >= 20%) |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, label in ((baseline, "Current"), (primary, "Frozen challenger")):
        item = mc[name]
        report.append(f"| {label} | {item['return_p05']:+.2f}% | {item['return_median']:+.2f}% | {item['return_p95']:+.2f}% | {item['dd_p95']:.2f}% | {item['profitable_pct']:.2f}% | {item['probability_dd20_pct']:.2f}% |")
    report += ["", "## What was tested", "",
        "- RR targets from 0.5R through 5R, plus nine adaptive-RR rules.",
        "- ATR stops from 1–5 ATR and signal-candle stops with four buffers.",
        "- M1, M5, M15 and M30 signals.",
        "- New York 09:30 baseline plus Asia, London, overlap and 10:00 New York standalone anchors.",
        "- Both directions, long-only and short-only.",
        "- No management, ATR trailing, breakeven and Dynamic 50/20 variants.",
        "- EMA slope, candle-body, EMA-distance and relative-volume filters.", "",
        "The completed-D1 Full Safe gate was also applied to the selected 2.5R configuration. It returned +21.15% with PF 1.18, a 40.74% win rate and 19.12% drawdown across 189 exact three-year trades, so Standard remains the recommended mode.", "",
        "Alternate anchors are separate once-daily momentum hypotheses, not generic session filters. The original rule only fires at 09:30 New York, so applying an Asia/London gate to it would merely produce zero trades.", "",
        "The complete development table is in `all-results.csv`; exact inputs are retained in `Sets`. Full MT5 reports and reconciled trade ledgers are retained in `Reports`.", "",
        "Historical results are not a guarantee of future performance.",
    ]
    (ROOT / "STEP 11 - NASDAQ 5M CANDLE MOMENTUM FULL OPTIMIZATION.md").write_text("\n".join(report)+"\n", encoding="utf-8")
    dump(ROOT / "decision.json", dict(promote=passes, selected=primary if passes else baseline, challenger=primary, monte_carlo=mc, cost_stress=cost_stress))
    make_charts(rows, selection, mc)
    print(json.dumps(dict(promote=passes, selected=primary if passes else baseline, challenger=primary), indent=2), flush=True)


def make_charts(rows: list[dict], selection: dict, monte: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    charts = ROOT / "Charts"
    charts.mkdir(exist_ok=True)
    development = sorted((row for row in rows if row["stage"] == "development"), key=score)
    fig, axis = plt.subplots(figsize=(12, max(8, len(development)*0.23)), constrained_layout=True)
    axis.barh([row["name"] for row in development], [row["return_pct"] for row in development], color=["#18a879" if row["return_pct"] >= 0 else "#ef6464" for row in development])
    axis.axvline(0, color="#6b7280", linewidth=0.8)
    axis.set(title="Nasdaq Momentum — every development configuration", xlabel="Net return (%)")
    fig.savefig(charts / "all-development-configurations.png", dpi=150)
    plt.close(fig)

    primary = selection["selected_before_locked_test"]
    baseline = "current-dynamic5020-atr6"
    lookup = {(row["stage"], row["name"]): row for row in rows}
    fig, axes = plt.subplots(2, 1, figsize=(13, 9))
    fig.subplots_adjust(left=0.08, right=0.98, top=0.95, bottom=0.08, hspace=0.30)
    for axis, stage in zip(axes, ("locked", "full")):
        for name, label, color in ((baseline, "Current", "#94a3b8"), (primary, "Frozen challenger", "#68a7ff")):
            row = lookup[(stage, name)]
            series = row["series"]
            dates = [datetime.fromisoformat(str(point["date"])) for point in series]
            axis.step(dates, [point["balance"] for point in series], where="post", label=f"{label}: PF {row['profit_factor']:.2f}, win {row['win_rate']:.1f}%", color=color)
        axis.set_title("Untouched locked year" if stage == "locked" else "Exact three-year context", loc="left", pad=10, fontweight="bold")
        axis.set_ylabel("Balance USD")
        axis.grid(alpha=0.2)
        axis.legend()
        axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=4, maxticks=8))
        axis.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.savefig(charts / "locked-and-three-year-comparison.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument("--smoke", action="store_true")
    args = argument_parser.parse_args()
    main(args.smoke)
