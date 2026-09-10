from __future__ import annotations

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
SOURCE = ROOT / "EA" / "Calyx DMC H4 Fresh Ladder Research EA.mq5"
EXPERT_NAME = SOURCE.stem
EXPERT_FOLDER = "AAA Research\\DMC H4 Fresh Ladder 20260910"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "DMC H4 Fresh Ladder 20260910"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "dmc-h4-fresh-ladder-20260910"
TESTER_REPORTS = TESTER / "reports" / "dmc-h4-fresh-ladder-20260910"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"

DEVELOPMENT = ("2023.09.01", "2025.08.31")
LOCKED = ("2025.09.01", "2026.09.01")
THREE_YEAR = ("2023.09.01", "2026.09.01")

ASSETS = {
    "XAU": {"symbol": "XAUUSD"},
    "US100": {"symbol": "USTEC"},
}


def load_analyzer():
    spec = importlib.util.spec_from_file_location("h4_ladder_report_analyzer", ANALYZER_PATH)
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

    shutil.copy2(SOURCE, EXPERT_DIR / SOURCE.name)
    compile_log = ROOT / "compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{compile_log}"'
    result = subprocess.run(command, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    text = compile_log.read_text(encoding="utf-16", errors="ignore") if compile_log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"Research EA compile failed (exit {result.returncode}). Read {compile_log}")
    shutil.copy2(EXPERT, ROOT / "EA" / EXPERT.name)


def base_config() -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpRiskPercent": 1.0,
        "InpMagic": 1091001,
        "InpMaxTradesPerDay": 2,
        "InpMaxSpreadPoints": 0,
        "InpH4LookbackBars": 360,
        "InpATRPeriod": 14,
        "InpDuplicateLevelH4ATR": 0.10,
        "InpTouchToleranceM15ATR": 0.05,
        "InpMaximumPriorM15Touches": 0,
        "InpEntryMode": 0,
        "InpStopMode": 0,
        "InpStopM15ATR": 1.0,
        "InpStopBufferM15ATR": 0.02,
        "InpConfirmedRequireOpenOnApproachSide": True,
        "InpTargetFrontRunM15ATR": 0.0,
        "InpMinimumRR": 0.0,
        "InpMaximumRR": 20.0,
        "InpMaximumStopM15ATR": 8.0,
        "InpUseUTCSession": False,
        "InpSessionStartHourUTC": 0,
        "InpSessionEndHourUTC": 24,
    }


RAW_VARIANTS = [
    ("touch-atr-0p75", {"InpEntryMode": 0, "InpStopMode": 0, "InpStopM15ATR": 0.75}),
    ("touch-atr-1p00", {"InpEntryMode": 0, "InpStopMode": 0, "InpStopM15ATR": 1.00}),
    ("touch-prior-m15", {"InpEntryMode": 0, "InpStopMode": 1}),
    ("confirmed-touchbar", {"InpEntryMode": 1, "InpStopMode": 2}),
]


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def selection_score(row: dict) -> float:
    if row["trades"] < 12 or row["profit_factor"] <= 0:
        return -10000.0 + row["trades"]
    sample_penalty = max(0, 80 - row["trades"]) * 0.15
    return (
        0.20 * row["return_pct"]
        + 38.0 * math.log(max(row["profit_factor"], 0.05))
        + 0.12 * row["win_rate_pct"]
        - 1.75 * row["max_drawdown_pct"]
        + 1.00 * row["sharpe"]
        + 2.50 * row["recovery_factor"]
        - sample_penalty
    )


def compact(row: dict) -> dict:
    keys = (
        "asset",
        "symbol",
        "phase",
        "variant",
        "path",
        "initial_balance",
        "net_profit",
        "return_pct",
        "profit_factor",
        "win_rate_pct",
        "max_drawdown_pct",
        "trades",
        "sharpe",
        "recovery_factor",
        "expected_payoff",
        "history_quality",
        "commission",
        "swap",
        "selection_score",
        "config",
    )
    return {key: row[key] for key in keys if key in row}


def run_case(
    asset: str,
    phase: str,
    variant: str,
    config: dict[str, object],
    window: tuple[str, str],
    sequence: int,
) -> dict:
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:10]
    case_id = f"{asset.lower()}--{phase}--{variant}--{signature}"
    local_report = REPORTS / asset / phase / f"{case_id}.htm"
    if local_report.is_file():
        parsed = ANALYZER.parse_report(local_report)
        row = {
            "asset": asset,
            "symbol": ASSETS[asset]["symbol"],
            "phase": phase,
            "variant": variant,
            "config": deepcopy(config),
            "path": str(local_report),
            **parsed,
        }
        row["selection_score"] = selection_score(row)
        print(f"CACHED {sequence:03d} {asset:5s} {phase:12s} {variant}", flush=True)
        return row

    actual = {**deepcopy(config), "InpMagic": 109100000 + sequence}
    set_name = f"H4L-{case_id}.set"
    set_path = SETS / asset / phase / set_name
    set_path.parent.mkdir(parents=True, exist_ok=True)
    set_path.write_text(
        "\n".join(f"{key}={render(value)}" for key, value in actual.items()) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(set_path, TESTER_SETS / set_name)

    tester_report = TESTER_REPORTS / f"{case_id}.htm"
    for stale in TESTER_REPORTS.glob(f"{case_id}*"):
        stale.unlink()
    start, end = window
    ini = f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert={EXPERT_FOLDER}\\{EXPERT_NAME}
ExpertParameters={set_name}
Symbol={ASSETS[asset]['symbol']}
Period=M15
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:2000
Model=0
ExecutionMode=1
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\dmc-h4-fresh-ladder-20260910\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {asset:5s} {phase:12s} {variant}", flush=True)
    timeout = 1800 if window == THREE_YEAR else 1200
    for attempt in range(3):
        stop_terminal()
        subprocess.Popen(
            f'"{TERMINAL}" /portable /config:"{ini_path}"',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + timeout
        while not tester_report.is_file() and time.time() < deadline:
            time.sleep(0.5)
        if tester_report.is_file():
            time.sleep(1.0)
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
    row = {
        "asset": asset,
        "symbol": ASSETS[asset]["symbol"],
        "phase": phase,
        "variant": variant,
        "config": deepcopy(config),
        "path": str(local_report),
        **parsed,
    }
    row["selection_score"] = selection_score(row)
    print(
        f"DONE  {asset:5s} {phase:12s} {variant:24s} "
        f"return={row['return_pct']:+.2f}% PF={row['profit_factor']:.2f} "
        f"WR={row['win_rate_pct']:.2f}% DD={row['max_drawdown_pct']:.2f}% "
        f"n={row['trades']} Sharpe={row['sharpe']:.2f}",
        flush=True,
    )
    return row


def choose_xau(rows: list[dict]) -> dict:
    eligible = [
        row
        for row in rows
        if row["trades"] >= 30 and row["return_pct"] > 0 and row["profit_factor"] > 1.0
    ]
    sampled = [row for row in rows if row["trades"] >= 12]
    return max(eligible or sampled or rows, key=lambda row: row["selection_score"])


def trade_returns(deals: list[dict], initial: float = 10000.0) -> list[float]:
    equity = initial
    pending = 0.0
    outcomes: list[float] = []
    for deal in deals:
        pending += float(deal.get("cashflow", 0.0))
        if deal.get("entry", "") in {"out", "out by"}:
            base = max(equity, 1.0)
            outcomes.append(pending / base)
            equity += pending
            pending = 0.0
    return outcomes


def monte_carlo(row: dict, simulations: int = 10000, block: int = 5) -> dict:
    returns = trade_returns(row.get("deals", []), float(row.get("initial_balance", 10000.0)))
    if not returns:
        return {"simulations": simulations, "trades": 0}
    rng = random.Random(20260910)
    finals: list[float] = []
    drawdowns: list[float] = []
    for _ in range(simulations):
        sample: list[float] = []
        while len(sample) < len(returns):
            start = rng.randrange(len(returns))
            sample.extend(returns[(start + offset) % len(returns)] for offset in range(block))
        equity = 1.0
        peak = 1.0
        maximum_dd = 0.0
        for result in sample[: len(returns)]:
            equity *= max(0.01, 1.0 + result)
            peak = max(peak, equity)
            maximum_dd = max(maximum_dd, (peak - equity) / peak)
        finals.append((equity - 1.0) * 100.0)
        drawdowns.append(maximum_dd * 100.0)
    finals.sort()
    drawdowns.sort()

    def q(values: list[float], probability: float) -> float:
        return values[min(len(values) - 1, int(probability * (len(values) - 1)))]

    return {
        "simulations": simulations,
        "trades": len(returns),
        "probability_profit_pct": sum(value > 0 for value in finals) / len(finals) * 100.0,
        "return_p5_pct": q(finals, 0.05),
        "return_median_pct": q(finals, 0.50),
        "return_p95_pct": q(finals, 0.95),
        "drawdown_median_pct": q(drawdowns, 0.50),
        "drawdown_p95_pct": q(drawdowns, 0.95),
    }


def metric_row(label: str, row: dict) -> str:
    return (
        f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
        f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | "
        f"{row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
    )


def write_report(payload: dict, selected_full_raw: dict, us100_full_raw: dict) -> None:
    xau_mc = monte_carlo(selected_full_raw)
    us100_mc = monte_carlo(us100_full_raw)
    (ROOT / "monte-carlo.json").write_text(
        json.dumps({"XAU": xau_mc, "US100": us100_mc}, indent=2), encoding="utf-8"
    )
    lines = [
        "# DMC H4 Fresh-Ladder — Native MT5 XAU and US100 Research",
        "",
        "Research only. No active EA, recommended installer, website data or live terminal was changed.",
        "All results use Exness native MT5 real ticks, modeled costs and 1% dynamic equity risk.",
        "",
        "## Rule definition",
        "",
        "- Levels: completed H4 candle-body highs and lows, clustered within 0.10 H4 ATR.",
        "- Freshness: strict first M15 touch after the H4 level becomes available.",
        "- Target: next rail on the same H4 ladder.",
        "- Maximum frequency: two trades per UTC day.",
        "- No-lookahead stop variants: immediate touch with a known ATR/prior-bar stop, or entry after the M15 touch bar closes with its now-known extreme.",
        "",
        "## XAU development screen — 2023-09-01 to 2025-08-31",
        "",
        "| Variant | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["xau_development"]:
        lines.append(metric_row(row["variant"], row))
    selected = payload["selected_config"]
    lines += [
        "",
        f"Frozen XAU selection: **{payload['selected_variant']}**.",
        "",
        "## Frozen version validation",
        "",
        "| Market / period | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        metric_row("XAU locked — 2025-09-01 to 2026-09-01", payload["xau_locked"]),
        metric_row("XAU full — 2023-09-01 to 2026-09-01", payload["xau_full"]),
        metric_row("US100 development — frozen XAU rules", payload["us100_development"]),
        metric_row("US100 locked — frozen XAU rules", payload["us100_locked"]),
        metric_row("US100 full — frozen XAU rules", payload["us100_full"]),
        "",
        "## Monte Carlo — frozen three-year trades",
        "",
        "| Market | Trades | P(profit) | Return P5 / median / P95 | DD median / P95 |",
        "|---|---:|---:|---:|---:|",
        f"| XAU | {xau_mc.get('trades', 0)} | {xau_mc.get('probability_profit_pct', 0):.2f}% | "
        f"{xau_mc.get('return_p5_pct', 0):+.2f}% / {xau_mc.get('return_median_pct', 0):+.2f}% / "
        f"{xau_mc.get('return_p95_pct', 0):+.2f}% | {xau_mc.get('drawdown_median_pct', 0):.2f}% / "
        f"{xau_mc.get('drawdown_p95_pct', 0):.2f}% |",
        f"| US100 | {us100_mc.get('trades', 0)} | {us100_mc.get('probability_profit_pct', 0):.2f}% | "
        f"{us100_mc.get('return_p5_pct', 0):+.2f}% / {us100_mc.get('return_median_pct', 0):+.2f}% / "
        f"{us100_mc.get('return_p95_pct', 0):+.2f}% | {us100_mc.get('drawdown_median_pct', 0):.2f}% / "
        f"{us100_mc.get('drawdown_p95_pct', 0):.2f}% |",
        "",
        "## Frozen configuration",
        "",
        "```json",
        json.dumps(selected, indent=2),
        "```",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    prepare()
    sequence = 0
    xau_development: list[dict] = []
    base = base_config()
    for name, changes in RAW_VARIANTS:
        sequence += 1
        xau_development.append(
            run_case("XAU", "development", name, {**deepcopy(base), **changes}, DEVELOPMENT, sequence)
        )
    selected_row = choose_xau(xau_development)
    selected_config = deepcopy(selected_row["config"])
    print(
        f"SELECT XAU {selected_row['variant']} return={selected_row['return_pct']:+.2f}% "
        f"PF={selected_row['profit_factor']:.2f} WR={selected_row['win_rate_pct']:.2f}% "
        f"DD={selected_row['max_drawdown_pct']:.2f}% n={selected_row['trades']}",
        flush=True,
    )

    sequence += 1
    xau_locked_raw = run_case("XAU", "validation", "frozen-locked", selected_config, LOCKED, sequence)
    sequence += 1
    xau_full_raw = run_case("XAU", "validation", "frozen-three-year", selected_config, THREE_YEAR, sequence)

    sequence += 1
    us100_development_raw = run_case(
        "US100", "transfer", "xau-frozen-development", selected_config, DEVELOPMENT, sequence
    )
    sequence += 1
    us100_locked_raw = run_case(
        "US100", "transfer", "xau-frozen-locked", selected_config, LOCKED, sequence
    )
    sequence += 1
    us100_full_raw = run_case(
        "US100", "transfer", "xau-frozen-three-year", selected_config, THREE_YEAR, sequence
    )

    payload = {
        "methodology": {
            "development": DEVELOPMENT,
            "locked": LOCKED,
            "three_year": THREE_YEAR,
            "model": "MT5 every tick",
            "selection_market": "XAU",
            "transfer_market": "US100 with XAU-frozen rules",
        },
        "selected_variant": selected_row["variant"],
        "selected_config": selected_config,
        "xau_development": [compact(row) for row in xau_development],
        "xau_locked": compact(xau_locked_raw),
        "xau_full": compact(xau_full_raw),
        "us100_development": compact(us100_development_raw),
        "us100_locked": compact(us100_locked_raw),
        "us100_full": compact(us100_full_raw),
    }
    (ROOT / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(payload, xau_full_raw, us100_full_raw)
    print(f"COMPLETE: {ROOT / 'FINAL REPORT.md'}", flush=True)


if __name__ == "__main__":
    main()
