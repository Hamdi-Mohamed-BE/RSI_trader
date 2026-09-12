from __future__ import annotations

import importlib.util
import hashlib
import json
import shutil
import subprocess
import time
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
PRIOR = PACKAGE / "DMC Fresh Reaction Research 2026-09-09"
PIPELINE_PATH = PRIOR / "run_pipeline.py"


def load_pipeline():
    spec = importlib.util.spec_from_file_location("dmc_fresh_pipeline", PIPELINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {PIPELINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = ROOT
    module.REPORTS = ROOT / "Backtest Reports"
    module.SETS = ROOT / "Sets"
    module.CONFIGS = module.TESTER / "backtest-configs" / "dmc-cheat-sheet-regime-20260912"
    module.TESTER_REPORTS = module.TESTER / "reports" / "dmc-cheat-sheet-regime-20260912"
    return module


P = load_pipeline()
DEVELOPMENT = ("2023.09.01", "2025.08.31", 1)
LOCKED = ("2025.09.01", "2026.09.01", 0)
THREE_YEAR = ("2023.09.01", "2026.09.01", 0)
LOGIN = 474572294
SERVER = "Exness-MT5Trial15"
P.ASSETS["XAU"]["symbol"] = "XAUUSDr"
P.ASSETS["US100"]["symbol"] = "USTECr"


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def run_case(asset: str, phase: str, variant: str, config: dict[str, object],
             window: tuple[str, str, int], sequence: int) -> dict:
    info = P.ASSETS[asset]
    signature = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:9]
    case_id = f"{asset.lower()}--{phase}--{variant}--{signature}"
    local_report = P.REPORTS / asset / phase / f"{case_id}.htm"
    if local_report.is_file():
        parsed = P.ANALYZER.parse_report(local_report)
        row = {
            "asset": asset,
            "symbol": info["symbol"],
            "phase": phase,
            "variant": variant,
            "config": deepcopy(config),
            "path": str(local_report),
            **parsed,
        }
        row["selection_score"] = P.selection_score(row)
        print(f"CACHED {sequence:03d} {asset:5s} {phase:16s} {variant}", flush=True)
        return row

    actual = {**deepcopy(config), "InpMagic": 112090000 + sequence}
    set_name = f"DMCCS-{case_id}.set"
    set_path = P.SETS / asset / phase / set_name
    set_path.parent.mkdir(parents=True, exist_ok=True)
    set_path.write_text(
        "\n".join(f"{key}={render(value)}" for key, value in actual.items()) + "\n",
        encoding="utf-8",
    )
    shutil.copy2(set_path, P.TESTER_SETS / set_name)

    tester_report = P.TESTER_REPORTS / f"{case_id}.htm"
    start, end, model = window
    ini = f"""[Common]
Login={LOGIN}
Server={SERVER}

[Tester]
Expert={P.EXPERT_FOLDER}\\{P.EXPERT_NAME}
ExpertParameters={set_name}
Symbol={info['symbol']}
Period=H1
Login={LOGIN}
Deposit=10000
Currency=USD
Leverage=1:2000
Model={model}
ExecutionMode=1
Optimization=0
FromDate={start}
ToDate={end}
ForwardMode=0
Report=reports\\dmc-cheat-sheet-regime-20260912\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = P.CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {asset:5s} {phase:16s} {variant}", flush=True)
    for attempt in range(4):
        P.stop_terminal()
        subprocess.Popen(
            f'"{P.TERMINAL}" /portable /config:"{ini_path}"',
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        deadline = time.time() + (180 if model == 1 else 1500)
        while not tester_report.is_file() and time.time() < deadline:
            time.sleep(0.25)
        if tester_report.is_file():
            break
        print(f"RETRY {sequence:03d} attempt={attempt + 2}", flush=True)
    if not tester_report.is_file():
        P.stop_terminal()
        raise FileNotFoundError(f"Missing native MT5 report: {tester_report}")
    local_report.parent.mkdir(parents=True, exist_ok=True)
    for artifact in P.TESTER_REPORTS.glob(f"{case_id}*"):
        shutil.copy2(artifact, local_report.parent / artifact.name)
    P.stop_terminal()
    parsed = P.ANALYZER.parse_report(local_report)
    row = {
        "asset": asset,
        "symbol": info["symbol"],
        "phase": phase,
        "variant": variant,
        "config": deepcopy(config),
        "path": str(local_report),
        **parsed,
    }
    row["selection_score"] = P.selection_score(row)
    print(
        f"DONE  {asset:5s} {phase:16s} {variant:24s} return={row['return_pct']:+.2f}% "
        f"PF={row['profit_factor']:.2f} WR={row['win_rate_pct']:.2f}% "
        f"DD={row['max_drawdown_pct']:.2f}% n={row['trades']}",
        flush=True,
    )
    return row


def prior_results() -> tuple[dict, dict]:
    xau = json.loads((PRIOR / "pipeline-progress.json").read_text(encoding="utf-8"))["final"]
    us100 = json.loads((PRIOR / "transfer-us100.json").read_text(encoding="utf-8"))
    return xau, us100


def metric(label: str, row: dict) -> str:
    return (
        f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
        f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | "
        f"{row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
    )


def regime_variants(base: dict) -> list[tuple[str, dict]]:
    rows = []
    for window in (20, 40, 60):
        config = deepcopy(base)
        config.update(
            {
                "InpUseMarkovRegimeFilter": True,
                "InpMarkovReturnWindow": window,
                "InpMarkovThreshold": 0.05,
                "InpMarkovSignalGate": 0.05,
                "InpMarkovMinLabels": 252,
                "InpMarkovHistoryBars": 2600,
            }
        )
        rows.append((f"markov-{window}d-5pct", config))
    return rows


def choose_markov(rows: list[dict]) -> dict:
    eligible = [
        row
        for row in rows
        if row["trades"] >= 20 and row["return_pct"] > 0 and row["profit_factor"] > 1.0
    ]
    sampled = [row for row in rows if row["trades"] >= 12]
    return max(eligible or sampled or rows, key=lambda row: row["selection_score"])


def run_asset(asset: str, base: dict, sequence: int) -> tuple[dict, int]:
    development = []
    for name, config in regime_variants(base):
        sequence += 1
        development.append(run_case(asset, "regime-screen", name, config, DEVELOPMENT, sequence))
    winner = choose_markov(development)
    frozen = deepcopy(winner["config"])
    sequence += 1
    locked = run_case(asset, "regime-final", "origin-held-locked", frozen, LOCKED, sequence)
    sequence += 1
    full = run_case(asset, "regime-final", "origin-held-three-year", frozen, THREE_YEAR, sequence)
    return {
        "asset": asset,
        "development": [P.compact_metrics(row) for row in development],
        "winner": P.compact_metrics(winner),
        "locked": P.compact_metrics(locked),
        "three_year": P.compact_metrics(full),
        "monte_carlo": P.monte_carlo(full),
    }, sequence


def run_reference(asset: str, label: str, config: dict, sequence: int) -> tuple[dict, int]:
    sequence += 1
    locked = run_case(asset, "matched-reference", f"{label}-locked", config, LOCKED, sequence)
    sequence += 1
    full = run_case(asset, "matched-reference", f"{label}-three-year", config, THREE_YEAR, sequence)
    return {"locked": P.compact_metrics(locked), "three_year": P.compact_metrics(full)}, sequence


def write_report(references: dict, xau: dict, us100: dict) -> None:
    lines = [
        "# DMC Cheat-Sheet Rules — Regime/Origin-Held Research",
        "",
        "## Decision",
        "",
        "**Do not replace either current DMC with the screenshot-enhanced regime gate.** On XAU it produced an attractive 80% locked win rate, but that came from only five trades. Across the nominal three-year window it reduced Fresh Reaction from 55 to 19 trades, lowered return from +35.84% to +10.92%, lowered PF from 2.46 to 2.28, and increased drawdown from 4.22% to 5.56%. On the currently connected US100 symbol the gate produced no trades, and that symbol has insufficient backfill for a valid three-year conclusion.",
        "",
        "Nothing in the active EAs, BAT installers or website was changed.",
        "",
        "## Mechanical translation of the screenshot",
        "",
        "- **Buy a level once / pass-throughs weaken it:** retained the already-validated fresh-reaction gate (maximum one prior M15 touch). Strict first-touch was previously weaker on XAU development data.",
        "- **Higher-timeframe levels win:** retained the validated W1/MN1 body-level proximity filter within 0.25 D1 ATR.",
        "- **Origin-to-distal level must hold / know trend and range:** tested a no-lookahead D1 Markov regime proxy. It only permits a long or short when transitions learned strictly from earlier completed D1 states support that direction. The screenshot does not define a mechanical origin-picking rule, so this is explicitly a proxy rather than a claim to reproduce the author's discretionary chart marking.",
        "- **Each level has an attached target:** not re-enabled. The prior 1.7R–3R structural-room tests collapsed the trade sample and were rejected.",
        "",
        "## Matched side-by-side — untouched locked year",
        "",
        "| Asset / version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        metric("XAU current DMC control", references["xau_control"]["locked"]),
        metric("XAU Fresh Reaction currently saved", references["xau_fresh"]["locked"]),
        metric("XAU screenshot regime proxy", xau["locked"]),
        metric("US100 Fresh Reaction currently saved", references["us100_fresh"]["locked"]),
        metric("US100 screenshot regime proxy", us100["locked"]),
        "",
        "## Matched side-by-side — full three years",
        "",
        "| Asset / version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        metric("XAU current DMC control", references["xau_control"]["three_year"]),
        metric("XAU Fresh Reaction currently saved", references["xau_fresh"]["three_year"]),
        metric("XAU screenshot regime proxy", xau["three_year"]),
        metric("US100 Fresh Reaction currently saved", references["us100_fresh"]["three_year"]),
        metric("US100 screenshot regime proxy", us100["three_year"]),
        "",
        "## Development-only regime screen",
        "",
        "| Asset | Variant | Return | PF | Win rate | Max DD | Trades |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for result in (xau, us100):
        for row in result["development"]:
            lines.append(
                f"| {result['asset']} | {row['variant']} | {row['return_pct']:+.2f}% | "
                f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | "
                f"{row['max_drawdown_pct']:.2f}% | {row['trades']} |"
            )
    lines += [
        "",
        "## Frozen candidates",
        "",
        f"- XAU: {xau['winner']['variant']}",
        "- US100: no viable candidate; all three regime windows produced zero trades on the available history.",
        "",
        "## Monte Carlo — three-year frozen candidates",
        "",
        "| Asset | P(profit) | Return P5 / median / P95 | DD median / P95 | Trades |",
        "|---|---:|---:|---:|---:|",
    ]
    for result in (xau, us100):
        mc = result["monte_carlo"]
        lines.append(
            f"| {result['asset']} | {mc.get('probability_profit_pct', 0):.2f}% | "
            f"{mc.get('return_p5_pct', 0):+.2f}% / {mc.get('return_median_pct', 0):+.2f}% / {mc.get('return_p95_pct', 0):+.2f}% | "
            f"{mc.get('drawdown_median_pct', 0):.2f}% / {mc.get('drawdown_p95_pct', 0):.2f}% | "
            f"{mc.get('trades', 0)} |"
        )
    lines += [
        "",
        "## Test conditions",
        "",
        "Current connected Exness Trial15 account, native MT5, `XAUUSDr` / `USTECr`, USD 10,000, 1% dynamic equity risk, H1, matched symbols and sessions, development 2023-09-01 through 2025-08-31, untouched lock 2025-09-01 through 2026-09-01, and exact three-year reference 2023-09-01 through 2026-09-01. Locked and three-year runs use Every Tick with random execution delay and recorded broker costs.",
        "",
        "## Data-quality limitation",
        "",
        "The locked XAU reports have 99% history quality and are the cleanest new evidence. The nominal three-year XAU reports show 34% history quality on the current account, while the development screens show 3%; those longer figures are useful only as directional references. The current `USTECr` report contains 6,936 H1 bars (roughly one year of market history), so its row must not be represented as genuine three-year coverage.",
        "",
        "Historical results are not guaranteed future profitability.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    P.prepare()
    xau_prior, us100_prior = prior_results()
    xau_base = deepcopy(xau_prior["candidate"]["three_year"]["config"])
    us100_base = deepcopy(us100_prior["selected_config"])
    sequence = 200
    xau, sequence = run_asset("XAU", xau_base, sequence)
    us100, sequence = run_asset("US100", us100_base, sequence)
    references = {}
    references["xau_control"], sequence = run_reference("XAU", "current-control", P.base_config(), sequence)
    references["xau_fresh"], sequence = run_reference("XAU", "fresh-current", xau_base, sequence)
    references["us100_fresh"], sequence = run_reference("US100", "fresh-current", us100_base, sequence)
    payload = {"xau": xau, "us100": us100, "references": references}
    (ROOT / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_report(references, xau, us100)
    print(f"COMPLETE: {ROOT / 'FINAL REPORT.md'}", flush=True)


if __name__ == "__main__":
    main()
