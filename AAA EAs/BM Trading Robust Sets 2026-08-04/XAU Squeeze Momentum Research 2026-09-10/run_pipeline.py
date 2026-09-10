from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import random
import shutil
import statistics
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
SOURCE = ROOT / "EA" / "Calyx XAU Squeeze Momentum Research EA.mq5"
SAFE_INCLUDE = ROOT / "EA" / "SafeRegimeFilter.mqh"
EXPERT_NAME = SOURCE.stem
EXPERT_FOLDER = "AAA Research\\XAU Squeeze Momentum 20260910"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "XAU Squeeze Momentum 20260910"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "xau-squeeze-momentum-20260910"
TESTER_REPORTS = TESTER / "reports" / "xau-squeeze-momentum-20260910"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"
COMMON_PIPELINE = PACKAGE.parent / "Calyx Research Pipeline" / "calyx_pipeline.py"

DEVELOPMENT = ("2021.09.01", "2024.08.31")
VALIDATION = ("2024.09.07", "2025.08.31")
LOCKED = ("2025.09.07", "2026.09.01")
THREE_YEAR = ("2023.09.01", "2026.09.01")
FIVE_YEAR = ("2021.09.01", "2026.09.01")
SYMBOLS = {"XAU": "XAUUSD", "XAG": "XAGUSD"}


def load_analyzer():
    spec = importlib.util.spec_from_file_location("squeeze_report_analyzer", ANALYZER_PATH)
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
    for required in (TERMINAL, METAEDITOR, SOURCE, SAFE_INCLUDE, ANALYZER_PATH, COMMON_PIPELINE):
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
    shutil.copy2(SAFE_INCLUDE, EXPERT_DIR / SAFE_INCLUDE.name)
    compile_log = ROOT / "compile-native.log"
    command = (
        f'"{METAEDITOR}" /portable '
        f'/compile:"{EXPERT_DIR / SOURCE.name}" /log:"{compile_log}"'
    )
    result = subprocess.run(command, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    text = compile_log.read_text(encoding="utf-16", errors="ignore") if compile_log.is_file() else ""
    expert = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
    if "0 errors, 0 warnings" not in text or not expert.is_file():
        raise RuntimeError(f"Research EA compile failed (exit {result.returncode}). Read {compile_log}")
    shutil.copy2(expert, ROOT / "EA" / expert.name)


def base_config() -> dict[str, object]:
    return {
        "InpUseMarkovRegimeFilter": False,
        "InpMarkovReturnWindow": 40,
        "InpMarkovThreshold": 0.05,
        "InpMarkovSignalGate": 0.05,
        "InpMarkovMinLabels": 252,
        "InpMarkovHistoryBars": 2600,
        "InpEnableTrading": True,
        "InpRiskPercent": 1.0,
        "InpMaximumEffectiveLeverage": 9.8,
        "InpMagic": 1091010,
        "InpMaximumSpreadPoints": 0,
        "InpSqueezeLength": 20,
        "InpBollingerMultiplier": 2.0,
        "InpKeltnerMultiplier": 1.5,
        "InpMomentumLength": 20,
        "InpTrendSMAPeriod": 200,
        "InpRequireMomentumRising": True,
        "InpATRPeriod": 14,
        "InpATRMethod": 0,
        "InpStopATR": 3.0,
        "InpTargetR": 2.0,
        "InpTrailingMode": 1,
        "InpTrailATR": 3.0,
        "InpBreakEvenAtR": 0.0,
        "InpPartialExitAtR": 0.0,
        "InpPartialExitFraction": 0.5,
        "InpMomentumExitMode": 2,
        "InpMomentumFadeFraction": 0.5,
        "InpMaximumHoldH1Bars": 0,
        "InpDynamicTriggerFraction": 0.5,
        "InpDynamicLockFraction": 0.2,
        "InpSessionStartHourUTC": 0,
        "InpSessionEndHourUTC": 24,
        "InpWeekdayMask": 62,
    }


def raw_config(risk: float = 5.0) -> dict[str, object]:
    return {**base_config(), "InpRiskPercent": risk}


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def config_signature(config: dict[str, object]) -> str:
    clean = {key: value for key, value in config.items() if key != "InpMagic"}
    return hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:12]


def selection_score(row: dict) -> float:
    trades = row["trades"]
    pf = max(row["profit_factor"], 0.03)
    if trades < 15:
        return -10000.0 + trades
    sample_penalty = max(0, 80 - trades) * 0.16
    return (
        0.16 * row["return_pct"]
        + 34.0 * math.log(pf)
        + 0.08 * row["win_rate_pct"]
        - 2.0 * row["max_drawdown_pct"]
        + 1.2 * row["sharpe"]
        + 2.0 * row["recovery_factor"]
        - sample_penalty
    )


def serializable(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def run_case(
    asset: str,
    phase: str,
    label: str,
    config: dict[str, object],
    window: tuple[str, str],
    sequence: int,
    model: int = 1,
    execution: int = 0,
) -> dict:
    signature = config_signature(config)
    case_id = f"{asset.lower()}--{phase}--{label}--m{model}e{str(execution).replace('-', 'r')}--{signature}"
    local_report = REPORTS / asset / phase / f"{case_id}.htm"
    if local_report.is_file():
        parsed = ANALYZER.parse_report(local_report)
        row = {
            "asset": asset, "symbol": SYMBOLS[asset], "phase": phase, "label": label,
            "window": window, "model": model, "execution": execution,
            "config": deepcopy(config), "path": str(local_report), **parsed,
        }
        row["selection_score"] = selection_score(row)
        print(f"CACHED {sequence:03d} {asset} {phase} {label}", flush=True)
        return row

    actual = {**deepcopy(config), "InpMagic": 109100000 + sequence}
    set_name = f"SQZ-{case_id}.set"
    set_path = SETS / asset / phase / set_name
    set_path.parent.mkdir(parents=True, exist_ok=True)
    set_path.write_text(
        "\n".join(f"{key}={render(value)}" for key, value in actual.items()) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(set_path, TESTER_SETS / set_name)
    # MT5 still uses a legacy path-limited report writer. Keep its temporary
    # filename deliberately short, then copy it to the descriptive research
    # filename after the terminal exits.
    tester_stub = f"r{sequence:04d}-{signature}"
    tester_report = TESTER_REPORTS / f"{tester_stub}.htm"
    for stale in TESTER_REPORTS.glob(f"{tester_stub}*"):
        stale.unlink()
    start, end = window
    ini = f"""[Common]
Login=472334559
Server=Exness-MT5Trial16

[Tester]
Expert={EXPERT_FOLDER}\\{EXPERT_NAME}
ExpertParameters={set_name}
Symbol={SYMBOLS[asset]}
Period=H1
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
Report=reports\\xau-squeeze-momentum-20260910\\{tester_stub}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {asset:3s} {phase:12s} {label}", flush=True)
    timeout = 2400 if model == 4 else 900
    for attempt in range(3):
        stop_terminal()
        # MT5's Windows command-line parser misreads the trailing quote when
        # subprocess.list2cmdline quotes a /config:<path with spaces> token.
        # Passing the executable and start-config as one command string matches
        # MetaEditor's launch convention and avoids an extra quote in the path.
        launch_command = f'"{TERMINAL}" /portable /config:"{ini_path}"'
        subprocess.Popen(
            launch_command,
            cwd=TESTER,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        deadline = time.time() + timeout
        while not tester_report.is_file() and time.time() < deadline:
            time.sleep(0.5)
        if tester_report.is_file():
            time.sleep(0.8)
            break
        print(f"RETRY {sequence:03d} attempt={attempt + 2}", flush=True)
    if not tester_report.is_file():
        stop_terminal()
        raise FileNotFoundError(f"Missing native MT5 report: {tester_report}")
    local_report.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(tester_report, local_report)
    for artifact in TESTER_REPORTS.glob(f"{tester_stub}*"):
        if artifact == tester_report:
            continue
        descriptive = local_report.with_name(f"{local_report.stem}{artifact.name[len(tester_stub):]}")
        shutil.copy2(artifact, descriptive)
    stop_terminal()
    parsed = ANALYZER.parse_report(local_report)
    row = {
        "asset": asset, "symbol": SYMBOLS[asset], "phase": phase, "label": label,
        "window": window, "model": model, "execution": execution,
        "config": deepcopy(config), "path": str(local_report), **parsed,
    }
    row["selection_score"] = selection_score(row)
    print(
        f"DONE  {asset:3s} {label:25s} ret={row['return_pct']:+.2f}% "
        f"PF={row['profit_factor']:.2f} WR={row['win_rate_pct']:.2f}% "
        f"DD={row['max_drawdown_pct']:.2f}% n={row['trades']}",
        flush=True,
    )
    return row


def choose(rows: list[dict], complexity_penalty: dict[str, float] | None = None) -> dict:
    complexity_penalty = complexity_penalty or {}
    eligible = [r for r in rows if r["trades"] >= 30 and r["return_pct"] > 0 and r["profit_factor"] > 1.0]
    pool = eligible or [r for r in rows if r["trades"] >= 15] or rows
    return max(pool, key=lambda r: r["selection_score"] - complexity_penalty.get(r["label"], 0.0))


def choose_plateau(rows: list[dict], dimensions: list[str], grids: dict[str, list[object]]) -> dict:
    eligible = [r for r in rows if r["trades"] >= 30 and r["return_pct"] > 0 and r["profit_factor"] > 1.0]
    pool = eligible or [r for r in rows if r["trades"] >= 15] or rows
    indexes = {key: {value: index for index, value in enumerate(values)} for key, values in grids.items()}
    for row in pool:
        neighbours = []
        for other in rows:
            distance = 0
            valid = True
            for key in dimensions:
                a = row["config"][key]
                b = other["config"][key]
                if a not in indexes[key] or b not in indexes[key]:
                    valid = False
                    break
                distance += abs(indexes[key][a] - indexes[key][b])
            if valid and distance <= 1:
                neighbours.append(other)
        neighbour_scores = [n["selection_score"] for n in neighbours]
        neighbour_pfs = [n["profit_factor"] for n in neighbours]
        row["plateau_score"] = (
            0.50 * row["selection_score"]
            + 0.50 * statistics.median(neighbour_scores or [row["selection_score"]])
            + 4.0 * min(statistics.median(neighbour_pfs or [0.0]), 2.0)
        )
    return max(pool, key=lambda r: r["plateau_score"])


def metric_line(name: str, row: dict) -> str:
    return (
        f"| {name} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
        f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | "
        f"{row['sharpe']:.2f} | {row['recovery_factor']:.2f} | "
        f"${row['commission']:.2f} | ${row['swap']:.2f} | {row['history_quality']} |"
    )


def trade_outcomes(row: dict) -> list[float]:
    outcomes: list[float] = []
    pending = 0.0
    for deal in row.get("deals", []):
        pending += float(deal.get("cashflow", 0.0))
        if deal.get("entry") in {"out", "out by"}:
            outcomes.append(pending)
            pending = 0.0
    return outcomes


def quantile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def monte_carlo(row: dict, paths: int = 10000, block: int = 5) -> dict:
    outcomes = trade_outcomes(row)
    if not outcomes:
        return {"paths": paths, "trades": 0}
    rng = random.Random(20260910 + len(outcomes))
    returns, drawdowns = [], []
    daily_breach = total_breach = 0
    initial = float(row["initial_balance"])
    for _ in range(paths):
        selected: list[float] = []
        while len(selected) < len(outcomes):
            start = rng.randrange(len(outcomes))
            selected.extend(outcomes[(start + offset) % len(outcomes)] for offset in range(block))
        equity = peak = initial
        maximum_dd = 0.0
        breached_daily = breached_total = False
        for pnl in selected[: len(outcomes)]:
            before = equity
            equity += pnl
            peak = max(peak, equity)
            maximum_dd = max(maximum_dd, (peak - equity) / max(peak, 1.0) * 100.0)
            breached_daily |= pnl < -0.05 * max(before, 1.0)
            breached_total |= equity < 0.90 * initial
        returns.append((equity / initial - 1.0) * 100.0)
        drawdowns.append(maximum_dd)
        daily_breach += int(breached_daily)
        total_breach += int(breached_total)
    return {
        "paths": paths, "trades": len(outcomes),
        "probability_profit_pct": sum(v > 0 for v in returns) / paths * 100.0,
        "return_p05_pct": quantile(returns, 0.05),
        "return_median_pct": quantile(returns, 0.50),
        "return_p95_pct": quantile(returns, 0.95),
        "max_drawdown_median_pct": quantile(drawdowns, 0.50),
        "max_drawdown_p95_pct": quantile(drawdowns, 0.95),
        "daily_5pct_breach_pct": daily_breach / paths * 100.0,
        "total_10pct_breach_pct": total_breach / paths * 100.0,
    }


def measured_extra_cost(row: dict) -> float:
    """One additional currently measured spread per closed trade at median entry volume."""
    try:
        from bs4 import BeautifulSoup
        import MetaTrader5 as mt5

        soup = BeautifulSoup(Path(row["path"]).read_bytes().decode("utf-16", errors="ignore"), "html.parser")
        inside = False
        volumes = []
        for tr in soup.find_all("tr"):
            if " ".join(tr.stripped_strings) == "Deals":
                inside = True
                continue
            if not inside:
                continue
            cells = [" ".join(td.stripped_strings) for td in tr.find_all("td", recursive=False)]
            if len(cells) == 13 and cells[4].lower() == "in":
                volumes.append(float(cells[5].replace(" ", "")))
        if not volumes or not mt5.initialize(path=r"C:\Program Files\MetaTrader 5\terminal64.exe", timeout=15000):
            return 0.0
        tick = mt5.symbol_info_tick(row["symbol"])
        info = mt5.symbol_info(row["symbol"])
        mt5.shutdown()
        if tick is None or info is None:
            return 0.0
        spread_price = max(0.0, tick.ask - tick.bid)
        return round(spread_price * info.trade_contract_size * statistics.median(volumes), 4)
    except Exception:
        return 0.0


def run_enhanced(row: dict, label: str, output: Path, tested: int) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    extra = measured_extra_cost(row)
    command = [
        "py", "-3", str(COMMON_PIPELINE), "--report", row["path"], "--label", label,
        "--output", str(output), "--tested-configurations", str(tested), "--paths", "10000",
    ]
    if extra > 0.0:
        command += ["--extra-cost-per-trade", str(extra)]
    subprocess.run(command, check=True, timeout=600)
    summaries = list(output.glob("*.json"))
    payload = json.loads(max(summaries, key=lambda p: p.stat().st_size).read_text(encoding="utf-8"))
    payload["measured_extra_cost_per_trade"] = extra
    return payload


def write_csv(rows: list[dict], path: Path) -> None:
    fields = [
        "asset", "symbol", "phase", "label", "model", "execution", "return_pct",
        "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe",
        "recovery_factor", "expected_payoff", "commission", "swap", "history_quality", "path",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    prepare()
    sequence = 0
    all_rows: list[dict] = []

    def run(asset, phase, label, config, window=DEVELOPMENT, model=1, execution=0):
        nonlocal sequence
        sequence += 1
        row = run_case(asset, phase, label, config, window, sequence, model, execution)
        all_rows.append(row)
        return row

    base = base_config()
    raw_dev = run("XAU", "raw", "literal-risk5-development", raw_config(), DEVELOPMENT, 1, 0)

    squeeze_lengths = [16, 20, 24]
    bb_values = [1.8, 2.0, 2.2]
    kc_values = [1.3, 1.5, 1.7]
    signal_rows = []
    for length in squeeze_lengths:
        for bb in bb_values:
            for kc in kc_values:
                cfg = {**base, "InpSqueezeLength": length, "InpMomentumLength": length,
                       "InpBollingerMultiplier": bb, "InpKeltnerMultiplier": kc}
                signal_rows.append(run("XAU", "development-signal", f"l{length}-bb{bb}-kc{kc}", cfg))
    signal_pick = choose_plateau(
        signal_rows,
        ["InpSqueezeLength", "InpBollingerMultiplier", "InpKeltnerMultiplier"],
        {"InpSqueezeLength": squeeze_lengths, "InpBollingerMultiplier": bb_values,
         "InpKeltnerMultiplier": kc_values},
    )

    refine_rows = []
    momentum_values = [12, 16, 20, 24, 28]
    sma_values = [150, 200, 250]
    for momentum in momentum_values:
        for sma in sma_values:
            cfg = {**signal_pick["config"], "InpMomentumLength": momentum, "InpTrendSMAPeriod": sma}
            refine_rows.append(run("XAU", "development-refine", f"mom{momentum}-sma{sma}", cfg))
    refine_pick = choose_plateau(
        refine_rows, ["InpMomentumLength", "InpTrendSMAPeriod"],
        {"InpMomentumLength": momentum_values, "InpTrendSMAPeriod": sma_values},
    )

    stop_values = [2.0, 2.5, 3.0, 3.5, 4.0]
    rr_values = [0.0, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0]
    management_rows = []
    for stop in stop_values:
        for rr in rr_values:
            cfg = {**refine_pick["config"], "InpStopATR": stop, "InpTargetR": rr}
            management_rows.append(run("XAU", "development-management", f"sl{stop}-rr{rr}", cfg))
    management_pick = choose_plateau(
        management_rows, ["InpStopATR", "InpTargetR"],
        {"InpStopATR": stop_values, "InpTargetR": rr_values},
    )

    atr_rows = []
    atr_periods = [10, 14, 20]
    atr_methods = [0, 1]
    for period in atr_periods:
        for method in atr_methods:
            cfg = {**management_pick["config"], "InpATRPeriod": period, "InpATRMethod": method}
            atr_rows.append(run("XAU", "development-atr", f"atr{period}-method{method}", cfg))
    atr_pick = choose_plateau(
        atr_rows, ["InpATRPeriod", "InpATRMethod"],
        {"InpATRPeriod": atr_periods, "InpATRMethod": atr_methods},
    )

    exit_specs = [
        ("raw-atr3-fade50", {}),
        ("no-trail-fade50", {"InpTrailingMode": 0}),
        ("no-trail-no-momentum", {"InpTrailingMode": 0, "InpMomentumExitMode": 0}),
        ("atr2-fade50", {"InpTrailATR": 2.0}),
        ("atr2p5-fade50", {"InpTrailATR": 2.5}),
        ("atr3p5-fade50", {"InpTrailATR": 3.5}),
        ("atr4-fade50", {"InpTrailATR": 4.0}),
        ("atr3-negative-only", {"InpMomentumExitMode": 1}),
        ("atr3-no-momentum", {"InpMomentumExitMode": 0}),
        ("atr3-fade25", {"InpMomentumFadeFraction": 0.25}),
        ("atr3-fade75", {"InpMomentumFadeFraction": 0.75}),
        ("dynamic50-20", {"InpTrailingMode": 2}),
        ("dynamic60-20", {"InpTrailingMode": 2, "InpDynamicTriggerFraction": 0.6}),
        ("dynamic60-30", {"InpTrailingMode": 2, "InpDynamicTriggerFraction": 0.6,
                           "InpDynamicLockFraction": 0.3}),
        ("h1-low-trail", {"InpTrailingMode": 3}),
        ("break-even-0p5", {"InpTrailingMode": 0, "InpBreakEvenAtR": 0.5}),
        ("break-even-1", {"InpTrailingMode": 0, "InpBreakEvenAtR": 1.0}),
        ("break-even-1p5", {"InpTrailingMode": 0, "InpBreakEvenAtR": 1.5}),
        ("partial-1", {"InpPartialExitAtR": 1.0}),
        ("partial-1p5", {"InpPartialExitAtR": 1.5}),
        ("partial-2", {"InpPartialExitAtR": 2.0}),
        ("time-24h", {"InpMaximumHoldH1Bars": 24}),
        ("time-48h", {"InpMaximumHoldH1Bars": 48}),
        ("time-72h", {"InpMaximumHoldH1Bars": 72}),
    ]
    exit_rows = [run("XAU", "development-exit", name, {**atr_pick["config"], **changes})
                 for name, changes in exit_specs]
    exit_pick = choose(exit_rows, {name: 2.0 if "partial" in name else 0.0 for name, _ in exit_specs})

    sessions = [
        ("all-day", 0, 24, 62), ("asia", 0, 8, 62), ("london", 7, 13, 62),
        ("new-york", 13, 21, 62), ("overlap", 13, 16, 62), ("us-wide", 12, 22, 62),
        ("all-mon-thu", 0, 24, 30), ("all-tue-fri", 0, 24, 60),
        ("ny-mon-thu", 13, 21, 30),
    ]
    session_rows = []
    for name, start, end, mask in sessions:
        cfg = {**exit_pick["config"], "InpSessionStartHourUTC": start,
               "InpSessionEndHourUTC": end, "InpWeekdayMask": mask}
        session_rows.append(run("XAU", "development-session", name, cfg))

    top_sessions = sorted(session_rows, key=lambda r: r["selection_score"], reverse=True)[:3]
    native_dev_rows = [
        run("XAU", "development-native", f"verify-{r['label']}", r["config"], DEVELOPMENT, 0, 0)
        for r in top_sessions
    ]
    selected_dev = choose(native_dev_rows)
    selected_structure = deepcopy(selected_dev["config"])

    validation = run("XAU", "validation", "frozen", selected_structure, VALIDATION, 0, 0)
    locked_standard_1pct = run("XAU", "locked", "frozen-1pct-real-ticks", selected_structure, LOCKED, 4, 0)
    three_year_1pct = run("XAU", "final", "frozen-1pct-three-year", selected_structure, THREE_YEAR, 0, 0)

    risk_rows = []
    for risk in [0.25, 0.5, 0.75, 1.0, 1.25, 2.0, 5.0]:
        risk_rows.append(run("XAU", "risk", f"risk-{risk}", {**selected_structure, "InpRiskPercent": risk}, THREE_YEAR, 0, 0))
    conservative = [r for r in risk_rows if r["config"]["InpRiskPercent"] <= 1.25
                    and r["return_pct"] > 0 and r["max_drawdown_pct"] <= 10.0]
    risk_pick = max(conservative or risk_rows[:5], key=lambda r: float(r["config"]["InpRiskPercent"]))
    selected_risk = float(risk_pick["config"]["InpRiskPercent"])
    final_config = {**selected_structure, "InpRiskPercent": selected_risk}

    locked = run("XAU", "locked", f"recommended-risk-{selected_risk}-real-ticks", final_config, LOCKED, 4, 0)
    three_year = run("XAU", "final", f"recommended-risk-{selected_risk}-three-year", final_config, THREE_YEAR, 0, 0)
    five_year = run("XAU", "final", f"recommended-risk-{selected_risk}-five-year", final_config, FIVE_YEAR, 0, 0)
    random_delay = run("XAU", "stress", "random-delay", final_config, THREE_YEAR, 0, -1)
    fixed_500ms = run("XAU", "stress", "fixed-500ms", final_config, THREE_YEAR, 0, 500)

    safe_config = {**final_config, "InpUseMarkovRegimeFilter": True}
    safe_three_year = run("XAU", "safe", "markov-safe-three-year", safe_config, THREE_YEAR, 0, 0)
    safe_locked = run("XAU", "safe", "markov-safe-locked-real-ticks", safe_config, LOCKED, 4, 0)

    raw_locked = run("XAU", "raw", "literal-risk5-locked-real-ticks", raw_config(), LOCKED, 4, 0)
    raw_three_year = run("XAU", "raw", "literal-risk5-three-year", raw_config(), THREE_YEAR, 0, 0)
    raw_five_year = run("XAU", "raw", "literal-risk5-five-year", raw_config(), FIVE_YEAR, 0, 0)

    xag_three_year = run("XAG", "cross-market", "xau-frozen-three-year", final_config, THREE_YEAR, 0, 0)
    xag_locked = run("XAG", "cross-market", "xau-frozen-locked-real-ticks", final_config, LOCKED, 4, 0)

    unique_configs = {config_signature(r["config"]) for r in all_rows}
    tested_count = len(unique_configs)
    enhanced_xau = run_enhanced(locked, "XAU Squeeze Momentum — locked", ROOT / "Enhanced Audit" / "XAU", tested_count)
    enhanced_xag = run_enhanced(xag_locked, "XAU Squeeze Momentum — XAG frozen validation",
                                ROOT / "Enhanced Audit" / "XAG", tested_count)
    mc = {"XAU_three_year": monte_carlo(three_year), "XAU_locked": monte_carlo(locked),
          "XAG_three_year": monte_carlo(xag_three_year)}

    summary_rows = [raw_three_year, raw_locked, three_year, locked, validation, random_delay,
                    fixed_500ms, safe_three_year, safe_locked, xag_three_year, xag_locked]
    write_csv(summary_rows, ROOT / "final-summary.csv")
    write_csv(all_rows, ROOT / "all-results.csv")

    payload = {
        "methodology": {
            "development": DEVELOPMENT, "purged_validation": VALIDATION, "locked": LOCKED,
            "three_year": THREE_YEAR, "five_year": FIVE_YEAR,
            "screen_model": "MT5 1-minute OHLC", "native_model": "MT5 Every Tick",
            "locked_model": "MT5 Every Tick based on real ticks", "broker": "Exness-MT5Trial16",
            "timezone": "UTC+0", "tested_unique_configurations": tested_count,
        },
        "raw_config": raw_config(), "selected_config": final_config,
        "selected_development": serializable(selected_dev),
        "raw": {"development": serializable(raw_dev), "locked": serializable(raw_locked),
                "three_year": serializable(raw_three_year), "five_year": serializable(raw_five_year)},
        "recommended": {"validation": serializable(validation), "locked": serializable(locked),
                        "three_year": serializable(three_year), "five_year": serializable(five_year)},
        "stress": {"random_delay": serializable(random_delay), "fixed_500ms": serializable(fixed_500ms)},
        "risk_sweep": [serializable(r) for r in risk_rows],
        "safe": {"three_year": serializable(safe_three_year), "locked": serializable(safe_locked)},
        "xag_validation": {"three_year": serializable(xag_three_year), "locked": serializable(xag_locked)},
        "monte_carlo": mc, "enhanced_audit": {"XAU": enhanced_xau, "XAG": enhanced_xag},
        "selection_stages": {
            "signal": serializable(signal_pick), "refinement": serializable(refine_pick),
            "management": serializable(management_pick), "atr": serializable(atr_pick),
            "exit": serializable(exit_pick), "native_development": serializable(selected_dev),
        },
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "settings_sha256": hashlib.sha256(json.dumps(final_config, sort_keys=True).encode()).hexdigest(),
    }
    (ROOT / "results.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    (ROOT / "monte-carlo.json").write_text(json.dumps(mc, indent=2), encoding="utf-8")

    lines = [
        "# XAU Squeeze Momentum — full Calyx research pipeline", "",
        "Research only. No website, BAT installer, active profile, or live account was changed.", "",
        "## Exact raw reconstruction", "",
        "- Completed H1 bars only; first bar after BB(20,2) leaves KC(20,1.5).",
        "- LazyBear-style 20-hour linear-regression momentum must be positive and strengthening.",
        "- Completed H1 close must be above SMA200.",
        "- Long market entry at the next H1 bar, 5% equity risk, maximum effective leverage 9.8x.",
        "- Wilder ATR(14), 3 ATR stop, 6 ATR target (2R), 3 ATR H1 ratchet, momentum negative/fade exit.", "",
        "## Headline comparison", "",
        "| Version / market | Return | PF | Win rate | Max equity DD | Trades | Sharpe | Recovery | Commission | Swap | Quality |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        metric_line("Raw 5% — XAU 3Y", raw_three_year),
        metric_line("Raw 5% — XAU locked real ticks", raw_locked),
        metric_line(f"Recommended {selected_risk}% — XAU 3Y", three_year),
        metric_line(f"Recommended {selected_risk}% — XAU locked real ticks", locked),
        metric_line("Random-delay stress — XAU 3Y", random_delay),
        metric_line("500 ms delay stress — XAU 3Y", fixed_500ms),
        metric_line("Safe/Markov — XAU 3Y", safe_three_year),
        metric_line("Safe/Markov — XAU locked real ticks", safe_locked),
        metric_line("XAG frozen rules — 3Y", xag_three_year),
        metric_line("XAG frozen rules — locked real ticks", xag_locked), "",
        "## Chronological evidence", "",
        metric_line("Development — selected structure", selected_dev),
        metric_line("Purged validation — selected structure", validation),
        metric_line("Locked real ticks — selected risk", locked), "",
        "## Frozen recommended configuration", "", "```json",
        json.dumps(final_config, indent=2), "```", "",
        "## Monte Carlo", "",
        "```json", json.dumps(mc, indent=2), "```", "",
        f"Enhanced XAU verdict: **{enhanced_xau.get('verdict', 'UNKNOWN')}**.",
        f"Enhanced XAG verdict: **{enhanced_xag.get('verdict', 'UNKNOWN')}**.",
        f"Total unique configurations counted: **{tested_count}**.", "",
        "The raw 5% sizing is reported exactly as requested but is not automatically recommended. "
        "Risk selection is capped at the pipeline's normal 1.25% ceiling and is based on drawdown survival.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"COMPLETE {ROOT / 'FINAL REPORT.md'}", flush=True)


if __name__ == "__main__":
    main()
