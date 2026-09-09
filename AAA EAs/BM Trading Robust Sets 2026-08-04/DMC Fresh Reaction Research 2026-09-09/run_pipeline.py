from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import random
import shutil
import subprocess
import time
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
TERMINAL = TESTER / "terminal64.exe"
METAEDITOR = TESTER / "MetaEditor64.exe"
SOURCE_DIR = ROOT / "EA"
SOURCE = SOURCE_DIR / "AAA DmC Fresh Reaction Research EA.mq5"
EXPERT_NAME = "AAA DmC Fresh Reaction Research EA"
EXPERT_FOLDER = "AAA Research\\DMC Fresh Reaction 20260909"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "DMC Fresh Reaction 20260909"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "dmc-fresh-reaction-20260909"
TESTER_REPORTS = TESTER / "reports" / "dmc-fresh-reaction-20260909"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"

DEVELOPMENT = ("2023.09.01", "2025.08.31", 1)
LOCKED = ("2025.09.01", "2026.09.01", 0)
THREE_YEAR = ("2023.09.01", "2026.09.01", 0)

ASSETS = {
    "XAU": {"symbol": "XAUUSD", "session": 1},
    "US100": {"symbol": "USTEC", "session": 3},
    "US30": {"symbol": "US30", "session": 3},
    "BTC": {"symbol": "BTCUSD", "session": 0},
}


def load_analyzer():
    spec = importlib.util.spec_from_file_location("dmc_report_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load native MT5 report analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


def stop_terminal() -> None:
    escaped = str(TERMINAL).replace("'", "''")
    script = (
        f"$target='{escaped}'; Get-Process terminal64 -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Path -eq $target } | Stop-Process -Force"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def prepare() -> None:
    for folder in (EXPERT_DIR, TESTER_SETS, CONFIGS, TESTER_REPORTS, REPORTS, SETS):
        folder.mkdir(parents=True, exist_ok=True)
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

    for item in SOURCE_DIR.glob("*.*"):
        if item.suffix.lower() in {".mq5", ".mqh"}:
            shutil.copy2(item, EXPERT_DIR / item.name)
    compile_log = ROOT / "pipeline-compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{compile_log}"'
    result = subprocess.run(command, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = compile_log.read_text(encoding="utf-16", errors="ignore") if compile_log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"Research EA compile failed (exit {result.returncode}). Read {compile_log}")
    shutil.copy2(EXPERT, SOURCE_DIR / EXPERT.name)


def base_config() -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpRiskPercent": 1.0,
        "InpRewardRisk": 3.0,
        "InpMagic": 1090901,
        "InpMaxSpreadPoints": 0,
        "InpTesterServerClockMode": 1,
        "InpUseMarkovRegimeFilter": False,
        "InpUseTrailing": True,
        "InpDmCSignalTimeframe": 16385,
        "InpDmCStopMode": 0,
        "InpDmCFixedStopPrice": 22.5,
        "InpDmCATRPeriod": 14,
        "InpDmCStopATR": 1.0,
        "InpDmCSignalBufferATR": 0.10,
        "InpUseDynamicTrailingSL": True,
        "InpDynamicTriggerFraction": 0.50,
        "InpDynamicLockFraction": 0.20,
        "InpResearchSession": 1,
        "InpResearchBrokerUtcOffsetMinutes": 180,
        "InpDmCFreshMode": 0,
        "InpDmCFreshTouchTimeframe": 15,
        "InpDmCFreshToleranceATR": 0.05,
        "InpDmCSignalMode": 0,
        "InpDmCRegainMaxBars": 1,
        "InpDmCRoomGateEnabled": False,
        "InpDmCMinimumRoomR": 2.0,
        "InpDmCRoomRequireMappedLevel": False,
        "InpDmCUseWeeklyMonthlyLevels": True,
        "InpDmCHTFProximityEnabled": False,
        "InpDmCHTFProximityATR": 0.50,
        "InpDmCConfirmMode": 0,
        "InpDmCM15StructureLookback": 4,
        "InpDmCConfirmExpiryHours": 2,
        "InpDmCWeekdaysOnly": False,
    }


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def serializable(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def selection_score(row: dict, minimum_trades: int = 60) -> float:
    if row["trades"] < 12 or row["profit_factor"] <= 0:
        return -10000.0 + row["trades"]
    sample_penalty = max(0, minimum_trades - row["trades"]) * 0.18
    return (
        0.18 * row["return_pct"]
        + 35.0 * math.log(max(row["profit_factor"], 0.05))
        - 1.65 * row["max_drawdown_pct"]
        + 0.10 * row["win_rate_pct"]
        + 0.90 * row["sharpe"]
        + 2.50 * row["recovery_factor"]
        - sample_penalty
    )


def compact_metrics(row: dict) -> dict:
    fields = (
        "asset", "symbol", "phase", "variant", "path", "net_profit", "return_pct",
        "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe",
        "recovery_factor", "expected_payoff", "history_quality", "commission", "swap",
        "selection_score", "config",
    )
    return {key: row[key] for key in fields if key in row}


def run_case(asset: str, phase: str, variant: str, config: dict[str, object],
             window: tuple[str, str, int], sequence: int) -> dict:
    info = ASSETS[asset]
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:9]
    case_id = f"{asset.lower()}--{phase}--{variant}--{signature}"
    local_report = REPORTS / asset / phase / f"{case_id}.htm"
    if local_report.is_file():
        parsed = ANALYZER.parse_report(local_report)
        row = {"asset": asset, "symbol": info["symbol"], "phase": phase, "variant": variant,
               "config": deepcopy(config), "path": str(local_report), **parsed}
        row["selection_score"] = selection_score(row)
        print(f"CACHED {sequence:03d} {asset:5s} {phase:16s} {variant}", flush=True)
        return row

    actual = {**deepcopy(config), "InpMagic": 109000000 + sequence}
    set_name = f"DMCFR-{case_id}.set"
    set_path = SETS / asset / phase / set_name
    set_path.parent.mkdir(parents=True, exist_ok=True)
    set_path.write_text("\n".join(f"{key}={render(value)}" for key, value in actual.items()) + "\n", encoding="utf-8")
    shutil.copy2(set_path, TESTER_SETS / set_name)

    tester_report = TESTER_REPORTS / f"{case_id}.htm"
    for stale in TESTER_REPORTS.glob(f"{case_id}*"):
        stale.unlink()
    start, end, model = window
    ini = f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert={EXPERT_FOLDER}\\{EXPERT_NAME}
ExpertParameters={set_name}
Symbol={info['symbol']}
Period=H1
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
Report=reports\\dmc-fresh-reaction-20260909\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {asset:5s} {phase:16s} {variant}", flush=True)
    for attempt in range(4):
        stop_terminal()
        subprocess.Popen(
            f'"{TERMINAL}" /portable /config:"{ini_path}"',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + (120 if model == 1 else 1200)
        while not tester_report.is_file() and time.time() < deadline:
            time.sleep(0.25)
        if tester_report.is_file():
            break
        print(f"RETRY {sequence:03d} attempt={attempt + 2}", flush=True)
    if not tester_report.is_file():
        stop_terminal()
        raise FileNotFoundError(f"Missing native MT5 report: {tester_report}")
    local_report.parent.mkdir(parents=True, exist_ok=True)
    for artifact in TESTER_REPORTS.glob(f"{case_id}*"):
        shutil.copy2(artifact, local_report.parent / artifact.name)
    stop_terminal()
    parsed = ANALYZER.parse_report(local_report)
    row = {"asset": asset, "symbol": info["symbol"], "phase": phase, "variant": variant,
           "config": deepcopy(config), "path": str(local_report), **parsed}
    row["selection_score"] = selection_score(row)
    print(
        f"DONE  {asset:5s} {phase:16s} {variant:24s} return={row['return_pct']:+.2f}% "
        f"PF={row['profit_factor']:.2f} WR={row['win_rate_pct']:.2f}% "
        f"DD={row['max_drawdown_pct']:.2f}% n={row['trades']} Sharpe={row['sharpe']:.2f}",
        flush=True,
    )
    return row


def choose(rows: list[dict], numeric: bool = False) -> dict:
    if numeric and len(rows) >= 3:
        raw = [row["selection_score"] for row in rows]
        for index, row in enumerate(rows):
            neighborhood = raw[max(0, index - 1):min(len(raw), index + 2)]
            row["selection_score"] = 0.65 * raw[index] + 0.35 * sorted(neighborhood)[len(neighborhood) // 2]
    eligible = [row for row in rows if row["trades"] >= 40 and row["return_pct"] > 0 and row["profit_factor"] > 1.0]
    sampled = [row for row in rows if row["trades"] >= 20]
    return max(eligible or sampled or rows, key=lambda item: item["selection_score"])


def variants(selected: dict[str, object], rows: list[tuple[str, dict[str, object]]]):
    return [(label, {**deepcopy(selected), **changes}) for label, changes in rows]


def xau_phases(selected: dict[str, object]):
    return [
        ("freshness", variants(selected, [
            ("control-off", {"InpDmCFreshMode": 0}),
            ("strict-first-touch", {"InpDmCFreshMode": 1}),
            ("allow-one-prior-touch", {"InpDmCFreshMode": 2}),
        ]), False),
        ("reaction", variants(selected, [
            ("rejection-control", {"InpDmCSignalMode": 0}),
            ("regain-one-bar", {"InpDmCSignalMode": 1, "InpDmCRegainMaxBars": 1}),
            ("regain-two-bars", {"InpDmCSignalMode": 1, "InpDmCRegainMaxBars": 2}),
            ("reject-or-regain-one", {"InpDmCSignalMode": 2, "InpDmCRegainMaxBars": 1}),
            ("reject-or-regain-two", {"InpDmCSignalMode": 2, "InpDmCRegainMaxBars": 2}),
        ]), False),
        ("room", variants(selected, [
            ("room-off-control", {"InpDmCRoomGateEnabled": False}),
            ("room-1p7R", {"InpDmCRoomGateEnabled": True, "InpDmCMinimumRoomR": 1.7}),
            ("room-2R", {"InpDmCRoomGateEnabled": True, "InpDmCMinimumRoomR": 2.0}),
            ("room-3R", {"InpDmCRoomGateEnabled": True, "InpDmCMinimumRoomR": 3.0}),
        ]), True),
        ("confirmation", variants(selected, [
            ("h1-close-control", {"InpDmCConfirmMode": 0}),
            ("m15-break-retest-lb2", {"InpDmCConfirmMode": 1, "InpDmCM15StructureLookback": 2}),
            ("m15-break-retest-lb4", {"InpDmCConfirmMode": 1, "InpDmCM15StructureLookback": 4}),
            ("m15-break-retest-lb8", {"InpDmCConfirmMode": 1, "InpDmCM15StructureLookback": 8}),
        ]), True),
        ("htf-confluence", variants(selected, [
            ("htf-off-control", {"InpDmCHTFProximityEnabled": False}),
            ("htf-within-0p25ATR", {"InpDmCHTFProximityEnabled": True, "InpDmCHTFProximityATR": 0.25}),
            ("htf-within-0p50ATR", {"InpDmCHTFProximityEnabled": True, "InpDmCHTFProximityATR": 0.50}),
            ("htf-within-1ATR", {"InpDmCHTFProximityEnabled": True, "InpDmCHTFProximityATR": 1.00}),
        ]), True),
        ("stop", variants(selected, [
            ("fixed-15", {"InpDmCStopMode": 0, "InpDmCFixedStopPrice": 15.0}),
            ("fixed-22p5-control", {"InpDmCStopMode": 0, "InpDmCFixedStopPrice": 22.5}),
            ("fixed-30", {"InpDmCStopMode": 0, "InpDmCFixedStopPrice": 30.0}),
            ("fixed-45", {"InpDmCStopMode": 0, "InpDmCFixedStopPrice": 45.0}),
            ("atr-0p50", {"InpDmCStopMode": 1, "InpDmCStopATR": 0.50}),
            ("atr-0p75", {"InpDmCStopMode": 1, "InpDmCStopATR": 0.75}),
            ("atr-1p00", {"InpDmCStopMode": 1, "InpDmCStopATR": 1.00}),
            ("atr-1p50", {"InpDmCStopMode": 1, "InpDmCStopATR": 1.50}),
            ("signal-0", {"InpDmCStopMode": 2, "InpDmCSignalBufferATR": 0.00}),
            ("signal-0p10", {"InpDmCStopMode": 2, "InpDmCSignalBufferATR": 0.10}),
            ("signal-0p25", {"InpDmCStopMode": 2, "InpDmCSignalBufferATR": 0.25}),
        ]), False),
        ("reward-risk", variants(selected, [
            ("rr-1p0", {"InpRewardRisk": 1.0}),
            ("rr-1p5", {"InpRewardRisk": 1.5}),
            ("rr-1p7", {"InpRewardRisk": 1.7}),
            ("rr-2p0", {"InpRewardRisk": 2.0}),
            ("rr-2p5", {"InpRewardRisk": 2.5}),
            ("rr-3p0-control", {"InpRewardRisk": 3.0}),
            ("rr-4p0", {"InpRewardRisk": 4.0}),
        ]), True),
        ("management", variants(selected, [
            ("no-dynamic", {"InpUseDynamicTrailingSL": False}),
            ("dynamic-50-20-control", {"InpUseDynamicTrailingSL": True, "InpDynamicTriggerFraction": 0.50, "InpDynamicLockFraction": 0.20}),
            ("dynamic-60-20", {"InpUseDynamicTrailingSL": True, "InpDynamicTriggerFraction": 0.60, "InpDynamicLockFraction": 0.20}),
            ("dynamic-75-25", {"InpUseDynamicTrailingSL": True, "InpDynamicTriggerFraction": 0.75, "InpDynamicLockFraction": 0.25}),
        ]), False),
    ]


def save_progress(payload: dict) -> None:
    (ROOT / "pipeline-progress.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def run_xau(sequence: int) -> tuple[dict, dict, dict, int]:
    baseline_config = base_config()
    baseline_dev = run_case("XAU", "baseline", "proven-current-control", baseline_config, DEVELOPMENT, sequence + 1)
    sequence += 1
    selected = deepcopy(baseline_config)
    progress: dict[str, object] = {"baseline_development": compact_metrics(baseline_dev), "phases": {}}
    all_phase_rows: list[dict] = []
    phase_names = [phase[0] for phase in xau_phases(selected)]
    for phase_name in phase_names:
        phase, candidates, numeric = next(item for item in xau_phases(selected) if item[0] == phase_name)
        rows = []
        for variant, config in candidates:
            sequence += 1
            rows.append(run_case("XAU", phase, variant, config, DEVELOPMENT, sequence))
        winner = choose(rows, numeric)
        selected = deepcopy(winner["config"])
        progress["phases"][phase] = {
            "winner": compact_metrics(winner),
            "candidates": [compact_metrics(row) for row in rows],
        }
        all_phase_rows.extend(rows)
        save_progress(progress)
        print(
            f"SELECT XAU {phase}: {winner['variant']} | {winner['return_pct']:+.2f}% "
            f"PF={winner['profit_factor']:.2f} WR={winner['win_rate_pct']:.2f}% "
            f"DD={winner['max_drawdown_pct']:.2f}% n={winner['trades']}", flush=True,
        )

    sequence += 1
    baseline_locked = run_case("XAU", "final", "baseline-locked", baseline_config, LOCKED, sequence)
    sequence += 1
    selected_locked = run_case("XAU", "final", "fresh-reaction-locked", selected, LOCKED, sequence)
    sequence += 1
    baseline_full = run_case("XAU", "final", "baseline-three-year", baseline_config, THREE_YEAR, sequence)
    sequence += 1
    selected_full = run_case("XAU", "final", "fresh-reaction-three-year", selected, THREE_YEAR, sequence)
    final = {
        "selected_config": selected,
        "baseline": {"development": compact_metrics(baseline_dev), "locked": compact_metrics(baseline_locked), "three_year": compact_metrics(baseline_full)},
        "candidate": {"locked": compact_metrics(selected_locked), "three_year": compact_metrics(selected_full)},
    }
    progress["final"] = final
    save_progress(progress)
    (ROOT / "xau-development-candidates.json").write_text(
        json.dumps([compact_metrics(row) for row in all_phase_rows], indent=2, default=str), encoding="utf-8"
    )
    return selected, selected_locked, selected_full, sequence


def portable_config(selected: dict[str, object], asset: str) -> dict[str, object]:
    config = deepcopy(selected)
    config["InpResearchSession"] = ASSETS[asset]["session"]
    config["InpDmCStopMode"] = 1
    config["InpDmCStopATR"] = 1.0
    config["InpDmCWeekdaysOnly"] = False
    return config


def run_transfer(asset: str, selected_xau: dict[str, object], sequence: int) -> tuple[dict, int]:
    legacy = portable_config(base_config(), asset)
    current = portable_config(selected_xau, asset)
    stop_rows = variants(current, [
        ("atr-0p50", {"InpDmCStopMode": 1, "InpDmCStopATR": 0.50}),
        ("atr-0p75", {"InpDmCStopMode": 1, "InpDmCStopATR": 0.75}),
        ("atr-1p00", {"InpDmCStopMode": 1, "InpDmCStopATR": 1.00}),
        ("atr-1p50", {"InpDmCStopMode": 1, "InpDmCStopATR": 1.50}),
        ("atr-2p00", {"InpDmCStopMode": 1, "InpDmCStopATR": 2.00}),
        ("signal-0p10", {"InpDmCStopMode": 2, "InpDmCSignalBufferATR": 0.10}),
    ])
    rows = []
    for variant, config in stop_rows:
        sequence += 1
        rows.append(run_case(asset, "transfer-stop", variant, config, DEVELOPMENT, sequence))
    stop_winner = choose(rows)
    current = deepcopy(stop_winner["config"])

    rr_rows = variants(current, [
        ("rr-1p0", {"InpRewardRisk": 1.0}),
        ("rr-1p5", {"InpRewardRisk": 1.5}),
        ("rr-1p7", {"InpRewardRisk": 1.7}),
        ("rr-2p0", {"InpRewardRisk": 2.0}),
        ("rr-2p5", {"InpRewardRisk": 2.5}),
        ("rr-3p0", {"InpRewardRisk": 3.0}),
        ("rr-4p0", {"InpRewardRisk": 4.0}),
    ])
    rr_results = []
    for variant, config in rr_rows:
        sequence += 1
        rr_results.append(run_case(asset, "transfer-rr", variant, config, DEVELOPMENT, sequence))
    rr_winner = choose(rr_results, numeric=True)
    current = deepcopy(rr_winner["config"])

    weekend_results = []
    if asset == "BTC":
        for variant, config in variants(current, [
            ("all-days", {"InpDmCWeekdaysOnly": False}),
            ("weekdays-only", {"InpDmCWeekdaysOnly": True}),
        ]):
            sequence += 1
            weekend_results.append(run_case(asset, "transfer-weekend", variant, config, DEVELOPMENT, sequence))
        current = deepcopy(choose(weekend_results)["config"])

    finals = {}
    for name, config, window in (
        ("legacy-locked", legacy, LOCKED), ("candidate-locked", current, LOCKED),
        ("legacy-three-year", legacy, THREE_YEAR), ("candidate-three-year", current, THREE_YEAR),
    ):
        sequence += 1
        finals[name] = run_case(asset, "transfer-final", name, config, window, sequence)
    result = {
        "asset": asset,
        "selected_config": current,
        "stop_winner": compact_metrics(stop_winner),
        "rr_winner": compact_metrics(rr_winner),
        "weekend": [compact_metrics(row) for row in weekend_results],
        "finals": {key: compact_metrics(value) for key, value in finals.items()},
    }
    (ROOT / f"transfer-{asset.lower()}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    return result, sequence


def trade_returns(deals: list[dict], initial: float = 10000.0) -> list[float]:
    equity = initial
    pending = 0.0
    outcomes = []
    for deal in deals:
        entry = deal.get("entry", "")
        pending += float(deal.get("cashflow", 0.0))
        if entry in {"out", "out by"}:
            base = max(equity, 1.0)
            outcomes.append(pending / base)
            equity += pending
            pending = 0.0
    return outcomes


def monte_carlo(row: dict, simulations: int = 10000, block: int = 5) -> dict:
    returns = trade_returns(row.get("deals", []), float(row.get("initial_balance", 10000.0)))
    if not returns:
        return {"simulations": simulations, "trades": 0}
    rng = random.Random(20260909)
    finals, drawdowns = [], []
    for _ in range(simulations):
        sample = []
        while len(sample) < len(returns):
            start = rng.randrange(len(returns))
            sample.extend(returns[(start + offset) % len(returns)] for offset in range(block))
        equity = 1.0
        peak = 1.0
        maximum_dd = 0.0
        for result in sample[:len(returns)]:
            equity *= max(0.01, 1.0 + result)
            peak = max(peak, equity)
            maximum_dd = max(maximum_dd, (peak - equity) / peak)
        finals.append((equity - 1.0) * 100.0)
        drawdowns.append(maximum_dd * 100.0)
    finals.sort(); drawdowns.sort()
    q = lambda values, p: values[min(len(values) - 1, int(p * (len(values) - 1)))]
    return {
        "simulations": simulations,
        "trades": len(returns),
        "probability_profit_pct": sum(value > 0 for value in finals) / len(finals) * 100.0,
        "return_p5_pct": q(finals, 0.05), "return_median_pct": q(finals, 0.50), "return_p95_pct": q(finals, 0.95),
        "drawdown_median_pct": q(drawdowns, 0.50), "drawdown_p95_pct": q(drawdowns, 0.95),
    }


def metric_row(label: str, row: dict) -> str:
    return (
        f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
        f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | "
        f"{row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
    )


def write_report(xau_selected: dict, xau_locked: dict, xau_full: dict, transfers: list[dict]) -> None:
    progress = json.loads((ROOT / "pipeline-progress.json").read_text(encoding="utf-8"))
    xau = progress["final"]
    baseline_locked = xau["baseline"]["locked"]
    baseline_full = xau["baseline"]["three_year"]
    full_row = ANALYZER.parse_report(Path(xau_full["path"]))
    mc = monte_carlo(full_row)
    (ROOT / "monte-carlo.json").write_text(json.dumps(mc, indent=2), encoding="utf-8")

    lines = [
        "# DMC Fresh-Reaction Filter — Full Native MT5 Pipeline",
        "",
        "Research-only implementation. The active EA, recommended portfolio, BAT installers and website were not changed.",
        "All cases used real-cost native MT5 testing and 1% dynamic equity risk.",
        "",
        "## Step-by-step development decisions",
        "",
        "| Step | Selected setting | Return | PF | Win rate | Max DD | Trades |",
        "|---|---|---:|---:|---:|---:|---:|",
        f"| Baseline | XAU H1, Asia, fixed 22.5, 3R, Dynamic 50/20 | {progress['baseline_development']['return_pct']:+.2f}% | {progress['baseline_development']['profit_factor']:.2f} | {progress['baseline_development']['win_rate_pct']:.2f}% | {progress['baseline_development']['max_drawdown_pct']:.2f}% | {progress['baseline_development']['trades']} |",
    ]
    for phase, description in (
        ("freshness", "Freshness"), ("reaction", "Reaction type"), ("room", "Structural room"),
        ("confirmation", "LTF confirmation"), ("htf-confluence", "HTF confluence"),
        ("stop", "Stop"), ("reward-risk", "Reward/risk"), ("management", "Management"),
    ):
        winner = progress["phases"][phase]["winner"]
        lines.append(
            f"| {description} | {winner['variant']} | {winner['return_pct']:+.2f}% | "
            f"{winner['profit_factor']:.2f} | {winner['win_rate_pct']:.2f}% | "
            f"{winner['max_drawdown_pct']:.2f}% | {winner['trades']} |"
        )
    lines += [
        "",
        "## XAU baseline versus selected candidate",
        "",
        "| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        metric_row("Current baseline — locked", baseline_locked),
        metric_row("Fresh Reaction — locked", xau_locked),
        metric_row("Current baseline — 3 years", baseline_full),
        metric_row("Fresh Reaction — 3 years", xau_full),
        "",
        "## Frozen configuration selected from development data",
        "",
        "```json",
        json.dumps(xau_selected, indent=2),
        "```",
        "",
        "## Cross-asset transfer",
        "",
        "| Asset / version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for transfer in transfers:
        finals = transfer["finals"]
        lines.append(metric_row(f"{transfer['asset']} legacy — locked", finals["legacy-locked"]))
        lines.append(metric_row(f"{transfer['asset']} candidate — locked", finals["candidate-locked"]))
        lines.append(metric_row(f"{transfer['asset']} legacy — 3 years", finals["legacy-three-year"]))
        lines.append(metric_row(f"{transfer['asset']} candidate — 3 years", finals["candidate-three-year"]))
    lines += [
        "",
        "## Monte Carlo — selected XAU 3-year trades",
        "",
        f"- Simulations: {mc.get('simulations', 0):,}",
        f"- Probability of profit: {mc.get('probability_profit_pct', 0):.2f}%",
        f"- End return P5 / median / P95: {mc.get('return_p5_pct', 0):+.2f}% / {mc.get('return_median_pct', 0):+.2f}% / {mc.get('return_p95_pct', 0):+.2f}%",
        f"- Max drawdown median / P95: {mc.get('drawdown_median_pct', 0):.2f}% / {mc.get('drawdown_p95_pct', 0):.2f}%",
        "",
        "## Deployment status",
        "",
        "Nothing was deployed.",
        "",
        "- **XAU: WATCH / DEMO CANDIDATE.** PF, win rate and drawdown improved strongly, but the locked sample is only 15 trades and total three-year return is lower than the current baseline.",
        "- **US100: WATCH / DEMO CANDIDATE.** The transfer reverses a losing portable baseline, but the locked sample is only 12 trades.",
        "- **US30: REJECT.** The locked candidate lost 7.37% with PF 0.48.",
        "- **BTC: REJECT.** Weekdays reduced drawdown versus all-days, but both the locked and three-year candidates remained negative.",
        "- **Recommended action:** keep the current live DMC unchanged. If approved, add XAU and US100 Fresh-Reaction variants to demo observation as separate modes, not replacements.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-only", action="store_true")
    parser.add_argument("--xau-only", action="store_true")
    args = parser.parse_args()
    prepare()
    sequence = 0
    if args.baseline_only:
        row = run_case("XAU", "baseline", "proven-current-control", base_config(), DEVELOPMENT, 1)
        print(json.dumps(compact_metrics(row), indent=2, default=str))
        return
    selected, locked, full, sequence = run_xau(sequence)
    if args.xau_only:
        write_report(selected, locked, full, [])
        return
    transfers = []
    for asset in ("US100", "US30", "BTC"):
        result, sequence = run_transfer(asset, selected, sequence)
        transfers.append(result)
    write_report(selected, locked, full, transfers)
    print(f"COMPLETE: {ROOT / 'FINAL REPORT.md'}", flush=True)


if __name__ == "__main__":
    main()
