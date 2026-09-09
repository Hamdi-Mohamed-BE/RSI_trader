from __future__ import annotations

import csv
import importlib.util
import json
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
BASE_PIPELINE_PATH = PARENT / "run_pipeline.py"


def load_base_pipeline():
    spec = importlib.util.spec_from_file_location("sell_nasdaq_base_pipeline", BASE_PIPELINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the original Sell Nasdaq pipeline")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PIPELINE = load_base_pipeline()

# Run a separate EA and separate local evidence tree. The production EX5 and
# both approved production SET files remain untouched until user review.
PIPELINE.ROOT = ROOT
PIPELINE.SOURCE = ROOT / "EA" / "Sell Nasdaq 15min Dynamic Exit Research EA.mq5"
PIPELINE.EXPERT_FOLDER = "AAA Research\\Sell Nasdaq 15min Dynamic Exit"
PIPELINE.EXPERT_NAME = "Sell Nasdaq 15min Dynamic Exit Research EA"
PIPELINE.EXPERT_DIR = (
    PIPELINE.TESTER / "MQL5" / "Experts" / "AAA Research" / "Sell Nasdaq 15min Dynamic Exit"
)
PIPELINE.EXPERT = PIPELINE.EXPERT_DIR / f"{PIPELINE.EXPERT_NAME}.ex5"
PIPELINE.CONFIGS = PIPELINE.TESTER / "backtest-configs" / "sell-nasdaq-dynamic-exit-20260908"
PIPELINE.REPORTS = ROOT / "Backtest Reports"
PIPELINE.SETS = ROOT / "Sets"
PIPELINE.CHARTS = ROOT / "Charts"


def dynamic_defaults(config: dict[str, object]) -> dict[str, object]:
    result = deepcopy(config)
    result.update(
        {
            "InpStopMode": 0,
            "InpStopRangeMultiple": 1.0,
            "InpAtrPeriod": 14,
            "InpStopAtrMultiple": 1.5,
            "InpDynamicStopBufferPips": 0.0,
            "InpMinimumDynamicStopPips": 0.0,
            "InpMaximumDynamicStopPips": 0.0,
            "InpTargetMode": 0,
            "InpTargetRMultiple": 2.0,
            "InpTargetRangeMultiple": 2.0,
            "InpTargetAtrMultiple": 3.0,
            "InpBreakEvenAtR": 0.0,
            "InpTrailStartAtR": 0.0,
            "InpUseDynamic5020": False,
        }
    )
    return result


def clean(row: dict) -> dict:
    return PIPELINE.clean(row)


def compact(row: dict) -> dict:
    return {
        key: row[key]
        for key in (
            "return_pct",
            "profit_factor",
            "win_rate_pct",
            "max_drawdown_pct",
            "trades",
            "sharpe",
            "recovery_factor",
            "history_quality",
        )
    }


def choose(rows: list[dict], minimum_trades: int = 35) -> dict:
    for row in rows:
        row["selection_score"] = PIPELINE.selection_score(row, minimum_trades=minimum_trades)
    eligible = [
        row
        for row in rows
        if row["trades"] >= minimum_trades
        and row["return_pct"] > 0.0
        and row["profit_factor"] > 1.0
    ]
    return max(eligible or rows, key=lambda row: row["selection_score"])


def stop_candidates(base: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
    rows: list[tuple[str, dict[str, object]]] = []
    for buffer in (0, 25, 50, 100):
        rows.append(
            (
                f"setup-high-buffer-{buffer}",
                {
                    **deepcopy(base),
                    "InpStopMode": 1,
                    "InpDynamicStopBufferPips": float(buffer),
                    "InpTargetMode": 1,
                    "InpTargetRMultiple": 2.0,
                },
            )
        )
    for multiple in (0.75, 1.0, 1.25, 1.5):
        rows.append(
            (
                f"range-stop-{multiple:g}x",
                {
                    **deepcopy(base),
                    "InpStopMode": 2,
                    "InpStopRangeMultiple": multiple,
                    "InpDynamicStopBufferPips": 0.0,
                    "InpTargetMode": 1,
                    "InpTargetRMultiple": 2.0,
                },
            )
        )
    for multiple in (1.0, 1.25, 1.5, 2.0, 2.5):
        rows.append(
            (
                f"atr-stop-{multiple:g}x",
                {
                    **deepcopy(base),
                    "InpStopMode": 3,
                    "InpStopAtrMultiple": multiple,
                    "InpDynamicStopBufferPips": 0.0,
                    "InpTargetMode": 1,
                    "InpTargetRMultiple": 2.0,
                },
            )
        )
    for multiple in (1.0, 1.5, 2.0):
        rows.append(
            (
                f"max-range-atr-{multiple:g}x",
                {
                    **deepcopy(base),
                    "InpStopMode": 4,
                    "InpStopRangeMultiple": 1.0,
                    "InpStopAtrMultiple": multiple,
                    "InpDynamicStopBufferPips": 0.0,
                    "InpTargetMode": 1,
                    "InpTargetRMultiple": 2.0,
                },
            )
        )
    return rows


def target_candidates(selected_stop: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
    rows: list[tuple[str, dict[str, object]]] = []
    for multiple in (1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0):
        rows.append(
            (
                f"target-{multiple:g}r",
                {**deepcopy(selected_stop), "InpTargetMode": 1, "InpTargetRMultiple": multiple},
            )
        )
    for multiple in (1.0, 1.5, 2.0, 2.5, 3.0):
        rows.append(
            (
                f"target-range-{multiple:g}x",
                {**deepcopy(selected_stop), "InpTargetMode": 2, "InpTargetRangeMultiple": multiple},
            )
        )
    for multiple in (1.5, 2.0, 2.5, 3.0, 4.0):
        rows.append(
            (
                f"target-atr-{multiple:g}x",
                {**deepcopy(selected_stop), "InpTargetMode": 3, "InpTargetAtrMultiple": multiple},
            )
        )
    for pips in (600, 800, 1000, 1250, 1500):
        rows.append(
            (
                f"target-fixed-{pips}",
                {**deepcopy(selected_stop), "InpTargetMode": 0, "InpTargetPips": float(pips)},
            )
        )
    return rows


def joint_candidates(selected_target: dict[str, object]) -> list[tuple[str, dict[str, object]]]:
    stop_mode = int(selected_target["InpStopMode"])
    target_mode = int(selected_target["InpTargetMode"])
    stop_value = float(selected_target["InpStopAtrMultiple"])
    if stop_mode != 3:
        raise RuntimeError("The local robustness stage currently expects the selected ATR stop family")
    stop_values = sorted({round(stop_value * factor, 3) for factor in (0.8, 1.0, 1.2)})
    if target_mode == 1:
        target_key = "InpTargetRMultiple"
    elif target_mode == 2:
        target_key = "InpTargetRangeMultiple"
    elif target_mode == 3:
        target_key = "InpTargetAtrMultiple"
    else:
        raise RuntimeError("The local robustness stage expects an adaptive target family")
    target_value = float(selected_target[target_key])
    target_values = sorted({round(target_value * factor, 3) for factor in (0.8, 1.0, 1.2)})
    rows: list[tuple[str, dict[str, object]]] = []
    for atr_period in (10, 14, 20):
        for stop_multiple in stop_values:
            for target_multiple in target_values:
                rows.append(
                    (
                        f"atr{atr_period}-sl{stop_multiple:g}-{target_key.replace('InpTarget', '').replace('Multiple', '').lower()}{target_multiple:g}",
                        {
                            **deepcopy(selected_target),
                            "InpAtrPeriod": atr_period,
                            "InpStopAtrMultiple": stop_multiple,
                            target_key: target_multiple,
                        },
                    )
                )
    return rows


def run_branch(
    branch: str,
    base: dict[str, object],
    sequence: int,
) -> tuple[dict, int]:
    stop_rows: list[dict] = []
    for label, config in stop_candidates(base):
        sequence += 1
        stop_rows.append(
            PIPELINE.run_case(
                f"{branch}-dynamic-stop",
                label,
                config,
                "2023.09.01",
                "2025.09.01",
                1,
                sequence,
            )
        )
    selected_stop = choose(stop_rows)
    print(
        f"SELECT {branch} stop: {selected_stop['variant']} | "
        f"{selected_stop['return_pct']:+.2f}% PF {selected_stop['profit_factor']:.2f} "
        f"WR {selected_stop['win_rate_pct']:.2f}% DD {selected_stop['max_drawdown_pct']:.2f}%",
        flush=True,
    )

    target_rows: list[dict] = []
    for label, config in target_candidates(selected_stop["config"]):
        sequence += 1
        target_rows.append(
            PIPELINE.run_case(
                f"{branch}-dynamic-target",
                label,
                config,
                "2023.09.01",
                "2025.09.01",
                1,
                sequence,
            )
        )
    selected_target = choose(target_rows)
    print(
        f"SELECT {branch} target: {selected_target['variant']} | "
        f"{selected_target['return_pct']:+.2f}% PF {selected_target['profit_factor']:.2f} "
        f"WR {selected_target['win_rate_pct']:.2f}% DD {selected_target['max_drawdown_pct']:.2f}%",
        flush=True,
    )

    joint_rows: list[dict] = []
    for label, config in joint_candidates(selected_target["config"]):
        sequence += 1
        joint_rows.append(
            PIPELINE.run_case(
                f"{branch}-dynamic-joint",
                label,
                config,
                "2023.09.01",
                "2025.09.01",
                1,
                sequence,
            )
        )
    selected_joint = choose(joint_rows)
    print(
        f"SELECT {branch} joint: {selected_joint['variant']} | "
        f"{selected_joint['return_pct']:+.2f}% PF {selected_joint['profit_factor']:.2f} "
        f"WR {selected_joint['win_rate_pct']:.2f}% DD {selected_joint['max_drawdown_pct']:.2f}%",
        flush=True,
    )

    sequence += 1
    locked = PIPELINE.run_case(
        f"{branch}-dynamic-locked",
        "development-selected",
        selected_joint["config"],
        "2025.09.01",
        "2026.09.01",
        0,
        sequence,
    )
    sequence += 1
    full = PIPELINE.run_case(
        f"{branch}-dynamic-full",
        "development-selected",
        selected_joint["config"],
        "2023.09.01",
        "2026.09.01",
        0,
        sequence,
    )
    monte_carlo = PIPELINE.ANALYZER.monte_carlo(
        PIPELINE.ANALYZER.trade_outcomes(locked["deals"]),
        locked["initial_balance"],
        10_000,
    )
    selected_set = ROOT / "Sets" / f"Sell Nasdaq 15min - {branch} dynamic exit candidate - 1pct.set"
    selected_set.parent.mkdir(parents=True, exist_ok=True)
    selected_set.write_text(PIPELINE.set_text(selected_joint["config"], 981008001 if branch == "standard" else 981008002), encoding="utf-8")
    return (
        {
            "branch": branch,
            "selected_stop": selected_stop["variant"],
            "selected_target": selected_target["variant"],
            "selected_joint": selected_joint["variant"],
            "selected_config": selected_joint["config"],
            "development_stop_rows": [clean(row) for row in stop_rows],
            "development_target_rows": [clean(row) for row in target_rows],
            "development_joint_rows": [clean(row) for row in joint_rows],
            "development_selected": clean(selected_joint),
            "locked": clean(locked),
            "full": clean(full),
            "monte_carlo": monte_carlo,
            "candidate_set": str(selected_set),
        },
        sequence,
    )


def table_line(label: str, row: dict) -> str:
    return (
        f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
        f"{row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | "
        f"{row['sharpe']:.2f} | {row['recovery_factor']:.2f} |"
    )


def top_rows(rows: list[dict], count: int = 5) -> list[dict]:
    return sorted(rows, key=lambda row: row.get("selection_score", -10_000), reverse=True)[:count]


def main() -> None:
    PIPELINE.prepare()
    original_audit = json.loads((PARENT / "FINAL AUDIT.json").read_text(encoding="utf-8"))
    standard = dynamic_defaults(
        {**PIPELINE.base_config(require_london=False), **original_audit["selected_config"]}
    )
    london = dynamic_defaults(PIPELINE.base_config(require_london=True))

    sequence = sum(1 for _ in PIPELINE.REPORTS.rglob("*.htm"))
    standard_result, sequence = run_branch("standard", standard, sequence)
    london_result, sequence = run_branch("london-safe", london, sequence)

    baseline_standard_locked = original_audit["final"]["selected_locked"]
    baseline_standard_full = original_audit["final"]["selected_full"]
    baseline_london_locked = original_audit["final"]["raw_london"]
    baseline_london_full = original_audit["safe_audit"]["raw_london_standard_full"]

    result = {
        "scope": "Research only; active EA, BAT files, website and cached production evidence unchanged",
        "development_period": "2023-09-01 to 2025-09-01, native MT5 1-minute OHLC",
        "locked_period": "2025-09-01 to 2026-09-01, native MT5 Every Tick",
        "full_period": "2023-09-01 to 2026-09-01, native MT5 Every Tick",
        "native_mt5_report_count": sum(1 for _ in PIPELINE.REPORTS.rglob("*.htm")),
        "standard": standard_result,
        "london_safe": london_result,
        "baselines": {
            "standard_locked": baseline_standard_locked,
            "standard_full": baseline_standard_full,
            "london_safe_locked": baseline_london_locked,
            "london_safe_full": baseline_london_full,
        },
    }
    (ROOT / "DYNAMIC EXIT AUDIT.json").write_text(
        json.dumps(result, indent=2, default=str), encoding="utf-8"
    )

    csv_rows = []
    for branch_result in (standard_result, london_result):
        for phase_name in ("development_stop_rows", "development_target_rows", "development_joint_rows"):
            for row in branch_result[phase_name]:
                csv_rows.append(
                    {
                        "branch": branch_result["branch"],
                        "phase": row["phase"],
                        "variant": row["variant"],
                        **compact(row),
                        "selection_score": row.get("selection_score", ""),
                    }
                )
    with (ROOT / "DYNAMIC EXIT DEVELOPMENT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(csv_rows[0]))
        writer.writeheader()
        writer.writerows(csv_rows)

    report = [
        "# Sell Nasdaq 15min — dynamic SL/TP research",
        "",
        "Research-only audit. The deployed 450/1000 Standard and original London-confirmed 600/1000 Safe presets were not changed.",
        "",
        "## Test design",
        "",
        "- Development selection: 2023-09-01 to 2025-09-01, native MT5 one-minute OHLC.",
        "- Untouched validation: 2025-09-01 to 2026-09-01, native MT5 Every Tick with broker costs and random delay.",
        "- Full reference: 2023-09-01 to 2026-09-01, native MT5 Every Tick.",
        "- Dynamic SL families: setup-candle high plus buffer, opening-range multiple, ATR multiple, and max(opening range, ATR).",
        "- Dynamic TP families: original-risk multiple, opening-range multiple, ATR multiple, plus fixed-TP controls.",
        f"- Evidence inventory: {result['native_mt5_report_count']} native MT5 reports across discovery, local robustness and final validation.",
        "- Risk remains 1% of dynamic equity to the actual calculated stop.",
        "- Break-even, trailing and Dynamic 50/20 remain off so this audit isolates initial SL/TP behavior.",
        "",
        "## Untouched locked-year comparison",
        "",
        "| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        table_line("Current Standard 450/1000", baseline_standard_locked),
        table_line("Dynamic Standard candidate", standard_result["locked"]),
        table_line("Current London Safe 600/1000", baseline_london_locked),
        table_line("Dynamic London candidate", london_result["locked"]),
        "",
        "## Full three-year comparison",
        "",
        "| Version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
        table_line("Current Standard 450/1000", baseline_standard_full),
        table_line("Dynamic Standard candidate", standard_result["full"]),
        table_line("Current London Safe 600/1000", baseline_london_full),
        table_line("Dynamic London candidate", london_result["full"]),
        "",
    ]
    for branch_result in (standard_result, london_result):
        report.extend(
            [
                f"## {branch_result['branch'].replace('-', ' ').title()} selection",
                "",
                f"- Selected dynamic stop: `{branch_result['selected_stop']}`",
                f"- Selected target: `{branch_result['selected_target']}`",
                f"- Selected local robustness point: `{branch_result['selected_joint']}`",
                f"- Locked Monte Carlo return P5: {branch_result['monte_carlo']['return_p5_pct']:+.2f}%",
                f"- Locked Monte Carlo max-DD P95: {branch_result['monte_carlo']['max_dd_p95_pct']:.2f}%",
                "",
                "Top development candidates:",
                "",
                "| Candidate | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
                "|---|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in top_rows(branch_result["development_joint_rows"]):
            report.append(table_line(row["variant"], row))
        report.append("")
    report.extend(
        [
            "## Review recommendation",
            "",
            "- Keep the current fixed 450/1000 Standard preset. The adaptive Standard candidate raised return but materially worsened win rate, drawdown, Sharpe/recovery quality and Monte Carlo downside.",
            "- Do not replace London Safe automatically. The ATR(14) 2.5x stop with 3R target is a strong isolated demo candidate because its PF and return improved, but its untouched drawdown rose from 4.52% to 7.79% and its untouched Sharpe/recovery weakened.",
            "- If approved later, expose the adaptive London configuration as a separate selectable mode first; preserve the current fixed London Safe preset until forward evidence confirms the trade-off.",
            "",
            "## Deployment status",
            "",
            "Nothing from this experiment is deployed. Promotion requires explicit user review and approval after the untouched evidence is compared with the current presets.",
            "",
        ]
    )
    (ROOT / "DYNAMIC EXIT REPORT.md").write_text("\n".join(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "standard": {
                    "stop": standard_result["selected_stop"],
                    "target": standard_result["selected_target"],
                    "joint": standard_result["selected_joint"],
                    "locked": compact(standard_result["locked"]),
                    "full": compact(standard_result["full"]),
                    "mc_return_p5": standard_result["monte_carlo"]["return_p5_pct"],
                },
                "london_safe": {
                    "stop": london_result["selected_stop"],
                    "target": london_result["selected_target"],
                    "joint": london_result["selected_joint"],
                    "locked": compact(london_result["locked"]),
                    "full": compact(london_result["full"]),
                    "mc_return_p5": london_result["monte_carlo"]["return_p5_pct"],
                },
                "production_changed": False,
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
