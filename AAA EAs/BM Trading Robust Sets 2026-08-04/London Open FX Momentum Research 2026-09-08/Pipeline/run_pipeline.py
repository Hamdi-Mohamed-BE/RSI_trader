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
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parents[1]
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
TERMINAL = TESTER / "terminal64.exe"
METAEDITOR = TESTER / "MetaEditor64.exe"
SOURCE = ROOT / "EA" / "Calyx London Open FX Momentum Pipeline EA.mq5"
EXPERT_FOLDER = "AAA Research\\London Open FX Momentum Pipeline"
EXPERT_NAME = "Calyx London Open FX Momentum Pipeline EA"
EXPERT_DIR = TESTER / "MQL5" / "Experts" / "AAA Research" / "London Open FX Momentum Pipeline"
EXPERT = EXPERT_DIR / f"{EXPERT_NAME}.ex5"
TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
CONFIGS = TESTER / "backtest-configs" / "london-open-fx-pipeline-20260908"
TESTER_REPORTS = TESTER / "reports" / "london-open-fx-pipeline-20260908"
REPORTS = ROOT / "Backtest Reports"
SETS = ROOT / "Sets"
ANALYZER_PATH = PACKAGE / "POC Fibonacci Volume Profile Research 2026-09-04" / "Analyze-POCFib.py"

DEV = ("2021.09.01", "2024.09.01")
VALIDATION = ("2024.09.01", "2025.09.01")
LATEST = ("2025.09.01", "2026.09.01")
FULL = ("2021.09.01", "2026.09.01")


def load_analyzer():
    spec = importlib.util.spec_from_file_location("london_pipeline_analyzer", ANALYZER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the native MT5 report analyzer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ANALYZER = load_analyzer()


def prepare() -> None:
    for directory in (EXPERT_DIR, TESTER_SETS, CONFIGS, TESTER_REPORTS, REPORTS, SETS):
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

    shutil.copy2(SOURCE, EXPERT_DIR / SOURCE.name)
    log = ROOT / "compile.log"
    command = f'"{METAEDITOR}" /portable /compile:"{EXPERT_DIR / SOURCE.name}" /log:"{log}"'
    result = subprocess.run(command, timeout=90, creationflags=subprocess.CREATE_NO_WINDOW)
    text = log.read_text(encoding="utf-16", errors="ignore") if log.is_file() else ""
    if "0 errors, 0 warnings" not in text or not EXPERT.is_file():
        raise RuntimeError(f"EA compile failed (exit {result.returncode}). Read {log}")
    shutil.copy2(EXPERT, ROOT / "EA" / EXPERT.name)


def render(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def base_config() -> dict[str, object]:
    return {
        "InpEnableTrading": True,
        "InpLondonOpenHour": 8.0,
        "InpFormationMinutes": 30,
        "InpExitLondonHour": 16.0,
        "InpReverseSignal": False,
        "InpDirection": 0,
        "InpTradeMonday": True,
        "InpTradeTuesday": True,
        "InpTradeWednesday": True,
        "InpTradeThursday": True,
        "InpTradeFriday": True,
        "InpMinimumSignalAtr": 0.0,
        "InpMaximumSignalAtr": 0.0,
        "InpMinimumVolumePctMedian": 0.0,
        "InpVolumeLookbackDays": 20,
        "InpMaximumSpreadAtrPct": 0.0,
        "InpRiskPercent": 1.0,
        "InpAtrPeriod": 14,
        "InpStopMode": 0,
        "InpStopAtrMultiple": 10.0,
        "InpFormationRangeStopMultiple": 1.0,
        "InpTargetMode": 0,
        "InpTargetR": 1.0,
        "InpAdaptiveBaseR": 0.5,
        "InpAdaptiveSignalWeight": 1.0,
        "InpAdaptiveMinimumR": 0.5,
        "InpAdaptiveMaximumR": 3.0,
        "InpBreakEvenAtR": 0.0,
        "InpTrailStartAtR": 0.0,
        "InpTrailDistanceR": 0.5,
        "InpExitSecondsEarly": 30,
        "InpMaxDeviationBrokerPoints": 20,
        "InpMagic": 980908501,
        "InpUseAutomaticLiveServerOffset": True,
        "InpTesterServerClock": 0,
        "InpTesterManualUTCOffsetHours": 0,
        "InpManualLiveServerUTCOffsetHours": 0,
    }


def set_text(values: dict[str, object], magic: int) -> str:
    actual = {**values, "InpMagic": magic}
    return "\n".join(f"{key}={render(value)}" for key, value in actual.items()) + "\n"


def run_case(
    symbol: str,
    phase: str,
    variant: str,
    values: dict[str, object],
    start: str,
    end: str,
    model: int,
    sequence: int,
) -> dict:
    signature_payload = json.dumps(values, sort_keys=True).encode() + SOURCE.read_bytes()
    signature = hashlib.sha256(signature_payload).hexdigest()[:10]
    case_id = f"{symbol.lower()}--{phase}--{variant}--m{model}--{start.replace('.', '')}-{end.replace('.', '')}--{signature}"
    local_report = REPORTS / symbol / phase / f"{case_id}.htm"
    if local_report.is_file():
        return {
            "symbol": symbol,
            "phase": phase,
            "variant": variant,
            "model": model,
            "config": deepcopy(values),
            "path": str(local_report),
            **ANALYZER.parse_report(local_report),
        }

    set_name = f"Calyx-LondonPipeline--{case_id}.set"
    set_path = SETS / set_name
    set_path.write_text(set_text(values, 980908500 + sequence), encoding="utf-8")
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
Symbol={symbol}
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
Report=reports\\london-open-fx-pipeline-20260908\\{case_id}.htm
ReplaceReport=1
ShutdownTerminal=1
UseCloud=0
Visual=0
"""
    ini_path = CONFIGS / f"{case_id}.ini"
    ini_path.write_text(ini, encoding="utf-8-sig")
    print(f"START {sequence:03d} {symbol:6s} {phase:18s} {variant}", flush=True)
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
        "symbol": symbol,
        "phase": phase,
        "variant": variant,
        "model": model,
        "config": deepcopy(values),
        "path": str(local_report),
        **ANALYZER.parse_report(local_report),
    }
    print(
        f"DONE  {symbol:6s} {phase:18s} {variant:22s} "
        f"ret={parsed['return_pct']:+.2f}% PF={parsed['profit_factor']:.2f} "
        f"WR={parsed['win_rate_pct']:.2f}% DD={parsed['max_drawdown_pct']:.2f}% n={parsed['trades']}",
        flush=True,
    )
    time.sleep(1)
    return parsed


def score(row: dict, minimum_trades: int = 250) -> float:
    if row["trades"] < 30 or row["profit_factor"] <= 0:
        return -10000.0 + row["trades"]
    sample_penalty = max(0, minimum_trades - row["trades"]) * 0.04
    return (
        row["return_pct"]
        + 18.0 * math.log(max(row["profit_factor"], 0.05))
        - 1.35 * row["max_drawdown_pct"]
        + 0.12 * row["win_rate_pct"]
        + 0.75 * row["sharpe"]
        + 0.55 * row["recovery_factor"]
        - sample_penalty
    )


def choose(rows: list[dict]) -> dict:
    for row in rows:
        row["selection_score"] = score(row)
    sampled = [row for row in rows if row["trades"] >= 150]
    robust = [row for row in sampled if row["max_drawdown_pct"] <= 20.0]
    profitable = [row for row in robust if row["return_pct"] > 0 and row["profit_factor"] > 1]
    return max(profitable or robust or sampled or rows, key=lambda row: row["selection_score"])


def variants(selected: dict[str, object], changes: list[tuple[str, dict[str, object]]]):
    return [(name, {**deepcopy(selected), **delta}) for name, delta in changes]


def phase_cases(selected: dict[str, object]):
    phases = []
    phases.append(("formation", variants(selected, [
        (f"{minutes}m", {"InpFormationMinutes": minutes}) for minutes in (15, 30, 45, 60)
    ])))
    phases.append(("exit", variants(selected, [
        (str(hour).replace(".", "-"), {"InpExitLondonHour": hour})
        for hour in (13.0, 14.0, 15.0, 16.0, 16.5, 17.0)
        if hour * 60 > float(selected["InpLondonOpenHour"]) * 60 + int(selected["InpFormationMinutes"])
    ])))
    phases.append(("direction", variants(selected, [
        ("both", {"InpDirection": 0}),
        ("long-only", {"InpDirection": 1}),
        ("short-only", {"InpDirection": 2}),
    ])))
    phases.append(("dynamic-stop", variants(selected, [
        (f"atr-{multiple}", {"InpStopMode": 0, "InpStopAtrMultiple": multiple})
        for multiple in (0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0)
    ] + [
        (f"formation-{multiple}", {"InpStopMode": 1, "InpFormationRangeStopMultiple": multiple})
        for multiple in (1.0, 1.5, 2.0)
    ])))
    phases.append(("fixed-rr", variants(selected, [
        ("time-exit", {"InpTargetMode": 0}),
    ] + [
        (f"{target}R", {"InpTargetMode": 1, "InpTargetR": target})
        for target in (0.5, 0.75, 1.0, 1.5, 2.0, 3.0)
    ])))
    phases.append(("adaptive-rr", variants(selected, [
        ("keep-current", {}),
        ("adaptive-soft", {"InpTargetMode": 2, "InpAdaptiveBaseR": 0.25, "InpAdaptiveSignalWeight": 0.75, "InpAdaptiveMinimumR": 0.5, "InpAdaptiveMaximumR": 2.0}),
        ("adaptive-balanced", {"InpTargetMode": 2, "InpAdaptiveBaseR": 0.5, "InpAdaptiveSignalWeight": 1.0, "InpAdaptiveMinimumR": 0.5, "InpAdaptiveMaximumR": 3.0}),
        ("adaptive-wide", {"InpTargetMode": 2, "InpAdaptiveBaseR": 0.75, "InpAdaptiveSignalWeight": 1.5, "InpAdaptiveMinimumR": 0.75, "InpAdaptiveMaximumR": 4.0}),
    ])))
    phases.append(("signal-strength", variants(selected, [
        (f"min-{value}", {"InpMinimumSignalAtr": value})
        for value in (0.0, 0.1, 0.2, 0.35, 0.5, 0.75)
    ])))
    phases.append(("volume", variants(selected, [
        (f"median-{value}", {"InpMinimumVolumePctMedian": float(value)})
        for value in (0, 25, 50, 75, 100)
    ])))
    phases.append(("spread", variants(selected, [
        ("off", {"InpMaximumSpreadAtrPct": 0.0}),
        ("max-2-5pct-atr", {"InpMaximumSpreadAtrPct": 2.5}),
        ("max-5pct-atr", {"InpMaximumSpreadAtrPct": 5.0}),
        ("max-10pct-atr", {"InpMaximumSpreadAtrPct": 10.0}),
    ])))
    phases.append(("management", variants(selected, [
        ("none", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.0}),
        ("be-0-5", {"InpBreakEvenAtR": 0.5, "InpTrailStartAtR": 0.0}),
        ("be-0-75", {"InpBreakEvenAtR": 0.75, "InpTrailStartAtR": 0.0}),
        ("be-1-0", {"InpBreakEvenAtR": 1.0, "InpTrailStartAtR": 0.0}),
        ("trail-1-0-0-5", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 1.0, "InpTrailDistanceR": 0.5}),
        ("be-0-75-trail-1-5", {"InpBreakEvenAtR": 0.75, "InpTrailStartAtR": 1.5, "InpTrailDistanceR": 0.75}),
    ])))
    phases.append(("weekdays", variants(selected, [
        ("mon-fri", {}),
        ("mon-thu", {"InpTradeFriday": False}),
        ("tue-fri", {"InpTradeMonday": False}),
        ("tue-thu", {"InpTradeMonday": False, "InpTradeFriday": False}),
        ("mon-wed", {"InpTradeThursday": False, "InpTradeFriday": False}),
        ("wed-fri", {"InpTradeMonday": False, "InpTradeTuesday": False}),
    ])))
    phases.append(("london-anchor", variants(selected, [
        (str(hour).replace(".", "-"), {"InpLondonOpenHour": hour})
        for hour in (7.0, 7.5, 8.0, 8.5, 9.0)
        if hour * 60 + int(selected["InpFormationMinutes"]) < float(selected["InpExitLondonHour"]) * 60
    ])))
    return phases


def compact(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def table_line(label: str, row: dict) -> str:
    return (
        f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
        f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | "
        f"{row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
    )


def run_symbol(symbol: str, sequence: int) -> tuple[dict, int]:
    selected = base_config()
    development: dict[str, list[dict]] = {}
    winners: dict[str, str] = {}
    phase_names = [phase for phase, _ in phase_cases(selected)]
    for phase_name in phase_names:
        phase, candidates = next(
            item for item in phase_cases(selected) if item[0] == phase_name
        )
        rows = []
        for variant, values in candidates:
            sequence += 1
            rows.append(run_case(symbol, phase, variant, values, *DEV, 1, sequence))
        winner = choose(rows)
        selected = deepcopy(winner["config"])
        winners[phase] = winner["variant"]
        development[phase] = [compact(row) for row in rows]
        print(
            f"SELECT {symbol} {phase}: {winner['variant']} | {winner['return_pct']:+.2f}% "
            f"PF {winner['profit_factor']:.2f} WR {winner['win_rate_pct']:.2f}% n={winner['trades']}",
            flush=True,
        )
        (ROOT / f"{symbol.lower()}--{phase}.json").write_text(
            json.dumps({"winner": compact(winner), "rows": development[phase]}, indent=2),
            encoding="utf-8",
        )

    raw = base_config()
    finals = {}
    for label, values, dates, model in (
        ("raw-validation", raw, VALIDATION, 0),
        ("selected-validation", selected, VALIDATION, 0),
        ("raw-latest", raw, LATEST, 0),
        ("selected-latest", selected, LATEST, 0),
        ("raw-full", raw, FULL, 0),
        ("selected-full", selected, FULL, 0),
    ):
        sequence += 1
        finals[label] = run_case(symbol, "final", label, values, *dates, model, sequence)

    outcomes = ANALYZER.trade_outcomes(finals["selected-latest"]["deals"])
    monte_carlo = ANALYZER.monte_carlo(outcomes, finals["selected-latest"]["initial_balance"], 10_000)
    val = finals["selected-validation"]
    latest = finals["selected-latest"]
    if (
        val["return_pct"] > 0 and val["profit_factor"] >= 1.20 and val["trades"] >= 40
        and latest["return_pct"] > 0 and latest["profit_factor"] >= 1.15
        and monte_carlo["return_p5_pct"] > 0
    ):
        decision = "PASS FOR ISOLATED DEMO FORWARD TESTING - portfolio inclusion still requires user approval."
    elif val["return_pct"] > 0 and latest["return_pct"] > 0 and val["profit_factor"] > 1 and latest["profit_factor"] > 1:
        decision = "WATCH ONLY - positive validation, but not strong enough for the recommended portfolio."
    else:
        decision = "REJECT - the development-selected configuration did not survive both later windows."

    selected_set = SETS / f"London Open FX Momentum - {symbol} - pipeline selected - 1pct.set"
    selected_set.write_text(set_text(selected, 980908900 + (1 if symbol == "USDJPY" else 2)), encoding="utf-8")
    return {
        "symbol": symbol,
        "selected_config": selected,
        "selected_by_phase": winners,
        "development": development,
        "final": {key: compact(value) for key, value in finals.items()},
        "monte_carlo": monte_carlo,
        "decision": decision,
        "selected_set": str(selected_set),
    }, sequence


def write_outputs(audits: list[dict], sequence: int) -> None:
    audit = {
        "strategy": "London Open FX Momentum - full pipeline",
        "paper": "Seeck (2026), SSRN 7008318",
        "method": {
            "development": f"{DEV[0]} to {DEV[1]}, MT5 1-minute OHLC",
            "validation": f"{VALIDATION[0]} to {VALIDATION[1]}, MT5 Every Tick",
            "latest": f"{LATEST[0]} to {LATEST[1]}, MT5 Every Tick",
            "full": f"{FULL[0]} to {FULL[1]}, MT5 Every Tick",
            "risk": "1% dynamic equity per trade",
            "monte_carlo": "10,000 five-trade block-bootstrap paths from latest-year selected trades",
        },
        "symbols": audits,
        "native_mt5_cases": sequence,
        "active_system_changed": False,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
    }
    (ROOT / "FINAL AUDIT.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")

    csv_rows = []
    for item in audits:
        for label, row in item["final"].items():
            csv_rows.append({
                "symbol": item["symbol"],
                "version": label,
                **{key: row[key] for key in (
                    "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct",
                    "trades", "sharpe", "recovery_factor", "history_quality",
                )},
            })
    with (ROOT / "FINAL AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)

    lines = [
        "# London Open FX Momentum - full pipeline report",
        "",
        "## Test design",
        "",
        f"- Development: {DEV[0]} to {DEV[1]}, MT5 1-minute OHLC.",
        f"- Validation: {VALIDATION[0]} to {VALIDATION[1]}, MT5 Every Tick.",
        f"- Latest: {LATEST[0]} to {LATEST[1]}, MT5 Every Tick.",
        f"- Full reference: {FULL[0]} to {FULL[1]}, MT5 Every Tick.",
        "- Starting balance: $10,000; dynamic-equity risk: 1% per filled trade.",
        "- The original 08:00/30-minute paper rule remains the raw comparator.",
        "- No active portfolio, website, installer, or BAT file was changed.",
        "",
    ]
    for item in audits:
        lines += [
            f"## {item['symbol']}",
            "",
            f"**Decision: {item['decision']}**",
            "",
            "| Window/version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for label in (
            "raw-validation", "selected-validation", "raw-latest", "selected-latest",
            "raw-full", "selected-full",
        ):
            lines.append(table_line(label, item["final"][label]))
        lines += ["", "Selected development choices:", ""]
        for phase, winner in item["selected_by_phase"].items():
            lines.append(f"- {phase}: `{winner}`")
        mc = item["monte_carlo"]
        lines += [
            "",
            f"Monte Carlo latest-year P(profit): {mc['probability_profitable_pct']:.2f}%; "
            f"return P5/median/P95: {mc['return_p5_pct']:+.2f}% / "
            f"{mc['return_median_pct']:+.2f}% / {mc['return_p95_pct']:+.2f}%; "
            f"DD median/P95: {mc['max_dd_median_pct']:.2f}% / {mc['max_dd_p95_pct']:.2f}%.",
            "",
        ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    prepare()
    sequence = 0
    audits = []
    for symbol in ("USDJPY", "EURUSD"):
        symbol_audit, sequence = run_symbol(symbol, sequence)
        audits.append(symbol_audit)
    write_outputs(audits, sequence)
    print(json.dumps({
        "cases": sequence,
        "results": [
            {"symbol": item["symbol"], "decision": item["decision"], "final": item["final"]}
            for item in audits
        ],
    }, indent=2), flush=True)


if __name__ == "__main__":
    main()
