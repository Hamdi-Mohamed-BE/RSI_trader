from __future__ import annotations

import csv
import importlib.util
import json
import math
import shutil
from copy import deepcopy
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
SOURCE_SCRIPT = PACKAGE / "ORB Session Matrix Research 2026-09-05" / "Run-ORB-Session-Matrix.py"


def load_source():
    spec = importlib.util.spec_from_file_location("orb_session_pipeline", SOURCE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load the validated ORB runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ORB = load_source()
TESTER = PACKAGE / "_Backtests" / "MT5-DMC-20260811"
ORB.ROOT = ROOT
ORB.CONFIGS = TESTER / "backtest-configs" / "orb-h1-range-20260905"
# The validated inherited runner writes this tester-relative folder name into
# each INI. Case IDs are unique to the H1 audit, while final artifacts are
# still copied into this audit's own Backtest Reports directory below.
ORB.TESTER_REPORTS = TESTER / "reports" / "orb-session-matrix-20260905"
ORB.TESTER_SETS = TESTER / "MQL5" / "Profiles" / "Tester"
ORB.REPORTS = ROOT / "Backtest Reports"
ORB.SETS = ROOT / "Sets"
ORB.CHARTS = ROOT / "Charts"
ORB.SYMBOLS = ("xauusd", "xagusd", "ustec")
ORB.BROKER_SYMBOLS = {"xauusd": "XAUUSD", "xagusd": "XAGUSD", "ustec": "USTEC"}
ORB.DISPLAY = {"xauusd": "Gold (XAUUSD)", "xagusd": "Silver (XAGUSD)", "ustec": "US100 (USTEC CFD)"}
ORB.PERIOD_NAMES = {5: "M5", 15: "M15", 30: "M30", 16385: "H1"}

ANCHORS = {
    "asia-0000": {"label": "Asia 00:00 UTC", "zone": 1, "hour": 0, "minute": 0, "flat_hour": 8, "flat_minute": 0},
    "london-0700": {"label": "London 07:00 UTC", "zone": 1, "hour": 7, "minute": 0, "flat_hour": 16, "flat_minute": 0},
    "ny-metals-0820": {"label": "New York 08:20", "zone": 0, "hour": 8, "minute": 20, "flat_hour": 15, "flat_minute": 55},
    "ny-cash-0930": {"label": "New York 09:30", "zone": 0, "hour": 9, "minute": 30, "flat_hour": 15, "flat_minute": 55},
    "overlap-1300": {"label": "Overlap 13:00 UTC", "zone": 1, "hour": 13, "minute": 0, "flat_hour": 20, "flat_minute": 0},
    "futures-1800": {"label": "New York futures restart 18:00", "zone": 0, "hour": 18, "minute": 0, "flat_hour": 23, "flat_minute": 55},
}

DEVELOPMENT = ("2023.09.01", "2025.08.31", 1)
LOCKED = ("2025.09.01", "2026.09.01", 0)
FULL = ("2023.09.01", "2026.09.01", 0)
SYMBOLS = ORB.SYMBOLS
PERIOD_NAMES = ORB.PERIOD_NAMES


def prepare() -> None:
    for directory in (ORB.CONFIGS, ORB.TESTER_REPORTS, ORB.TESTER_SETS, ORB.REPORTS, ORB.SETS, ORB.CHARTS):
        directory.mkdir(parents=True, exist_ok=True)
    for required in (ORB.TERMINAL, ORB.EXPERT):
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


def base_config(anchor: str) -> dict[str, object]:
    spec = ANCHORS[anchor]
    values = ORB.PRIOR.base_config()
    values.update(
        InpSessionZone=spec["zone"],
        InpSessionHour=spec["hour"],
        InpSessionMinute=spec["minute"],
        InpOpeningRangeMinutes=60,
        InpTradeWindowMinutes=180,
        InpFlatHour=spec["flat_hour"],
        InpFlatMinute=spec["flat_minute"],
        InpSignalTimeframe=15,
        InpATRTimeframe=16385,
        InpMinRangeATR=0.50,
        InpMaxRangeATR=3.50,
        InpMinOpeningRelativeVolume=0.60,
        InpMinBreakoutRelativeVolume=0.80,
        InpRequireVWAP=False,
        InpUseEMATrend=False,
        InpUseProfileValueArea=False,
        InpUseProfilePOCBias=False,
        InpUseProfileBoundaryLVN=False,
        InpEntryMode=0,
        InpStopMode=1,
        InpStopBufferATR=0.10,
        InpMaximumStopATR=3.00,
        InpRewardRisk=1.50,
        InpBreakEvenAtR=0.0,
        InpTrailStartAtR=0.0,
        InpUseDynamicTrailingSL=False,
        InpResearchSession=0,
        InpResearchBrokerUtcOffsetMinutes=0,
        InpUseMarkovRegimeFilter=False,
        InpRiskPercent=1.0,
        InpShowProfileLevels=False,
    )
    return values


def clean(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "deals"}


def score(row: dict, minimum_trades: int = 35) -> float:
    trades = int(row.get("trades", 0))
    pf = float(row.get("profit_factor", 0.0))
    if trades < 8 or pf <= 0:
        return -10000.0 + trades
    penalty = max(0, minimum_trades - trades) * 0.55
    return (
        float(row["return_pct"])
        + 14.0 * math.log(max(pf, 0.05))
        - 1.0 * float(row["max_drawdown_pct"])
        + 0.55 * float(row["sharpe"])
        + 0.40 * float(row["recovery_factor"])
        - penalty
    )


def choose(rows: list[dict], phase: str) -> dict:
    for row in rows:
        row["selection_score"] = score(row)
    if phase == "rr":
        ordered = sorted(rows, key=lambda item: float(item["config"]["InpRewardRisk"]))
        raw = [item["selection_score"] for item in ordered]
        for index, row in enumerate(ordered):
            neighborhood = raw[max(0, index - 1): min(len(ordered), index + 2)]
            row["selection_score"] = 0.60 * row["selection_score"] + 0.40 * sorted(neighborhood)[len(neighborhood) // 2]
    eligible = [
        row for row in rows
        if row["return_pct"] > 0 and row["profit_factor"] > 1 and row["trades"] >= 25
    ]
    return max(eligible or rows, key=lambda item: item["selection_score"])


def run_case(symbol: str, anchor: str, phase: str, variant: str, config: dict[str, object], sequence: int,
             window: tuple[str, str, int] = DEVELOPMENT) -> dict:
    return ORB.run_case(symbol, anchor, phase, variant, config, window[0], window[1], window[2], sequence)


def run_variants(symbol: str, anchor: str, phase: str, variants: list[tuple[str, dict[str, object]]],
                 sequence: int) -> tuple[dict, list[dict], int]:
    rows = []
    for variant, config in variants:
        sequence += 1
        rows.append(run_case(symbol, anchor, phase, variant, config, sequence))
    winner = choose(rows, phase)
    print(
        f"WIN {phase} {symbol} {anchor}: {winner['variant']} {winner['return_pct']:+.2f}% "
        f"PF {winner['profit_factor']:.2f} DD {winner['max_drawdown_pct']:.2f}% n={winner['trades']}",
        flush=True,
    )
    return winner, rows, sequence


def save_phase(name: str, rows: list[dict], winners: dict[str, dict]) -> None:
    payload = {
        "phase": name,
        "period": "2023-09-01 to 2025-08-31",
        "rows": [clean(row) for row in rows],
        "winners": {key: clean(value) for key, value in winners.items()},
    }
    (ROOT / f"{name.upper()} RESULTS.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def phase_pipeline() -> tuple[dict[tuple[str, str], dict], dict[str, list[dict]], int, dict[str, list[str]]]:
    sequence = 0
    phases: dict[str, list[dict]] = {}

    anchor_rows = []
    anchor_winners: dict[str, dict] = {}
    selected_anchors: dict[str, list[str]] = {}
    for symbol in SYMBOLS:
        rows = []
        for anchor in ANCHORS:
            sequence += 1
            rows.append(run_case(symbol, anchor, "anchor", "or60-m15-base", base_config(anchor), sequence))
        ordered = sorted(rows, key=score, reverse=True)
        selected_anchors[symbol] = [row["session"] for row in ordered[:2]]
        anchor_winners[symbol] = ordered[0]
        anchor_rows.extend(rows)
        print(f"ANCHORS {symbol}: {', '.join(selected_anchors[symbol])}", flush=True)
    phases["anchor"] = anchor_rows
    save_phase("anchor", anchor_rows, anchor_winners)

    current: dict[tuple[str, str], dict] = {}
    all_pairs = [(symbol, anchor) for symbol in SYMBOLS for anchor in selected_anchors[symbol]]
    for symbol, anchor in all_pairs:
        current[(symbol, anchor)] = next(
            row for row in anchor_rows if row["symbol"] == symbol and row["session"] == anchor
        )

    phase_specs: list[tuple[str, object]] = [
        ("timeframe", [(f"{PERIOD_NAMES[tf].lower()}", {"InpSignalTimeframe": tf}) for tf in PERIOD_NAMES]),
        ("entry", [("direct", {"InpEntryMode": 0}), ("retest", {"InpEntryMode": 1})]),
        ("confirmation", [
            ("permissive", {"InpMinOpeningRelativeVolume": 0.50, "InpMinBreakoutRelativeVolume": 0.70, "InpRequireVWAP": False, "InpUseEMATrend": False, "InpMinRangeATR": 0.35, "InpMaxRangeATR": 4.0}),
            ("base-volume", {"InpMinOpeningRelativeVolume": 0.60, "InpMinBreakoutRelativeVolume": 0.80, "InpRequireVWAP": False, "InpUseEMATrend": False}),
            ("volume", {"InpMinOpeningRelativeVolume": 0.80, "InpMinBreakoutRelativeVolume": 1.10, "InpRequireVWAP": False, "InpUseEMATrend": False}),
            ("ema", {"InpUseEMATrend": True, "InpRequireVWAP": False}),
            ("vwap", {"InpUseEMATrend": False, "InpRequireVWAP": True}),
            ("strict", {"InpMinOpeningRelativeVolume": 0.80, "InpMinBreakoutRelativeVolume": 1.10, "InpUseEMATrend": True, "InpRequireVWAP": True}),
        ]),
        ("stop", [
            ("opposite-b05-max25", {"InpStopMode": 1, "InpStopBufferATR": 0.05, "InpMaximumStopATR": 2.5}),
            ("opposite-b10-max30", {"InpStopMode": 1, "InpStopBufferATR": 0.10, "InpMaximumStopATR": 3.0}),
            ("opposite-b20-max40", {"InpStopMode": 1, "InpStopBufferATR": 0.20, "InpMaximumStopATR": 4.0}),
            ("signal-b05-max20", {"InpStopMode": 0, "InpStopBufferATR": 0.05, "InpMaximumStopATR": 2.0}),
            ("signal-b10-max25", {"InpStopMode": 0, "InpStopBufferATR": 0.10, "InpMaximumStopATR": 2.5}),
            ("signal-b20-max30", {"InpStopMode": 0, "InpStopBufferATR": 0.20, "InpMaximumStopATR": 3.0}),
        ]),
        ("rr", [(f"rr{rr:g}", {"InpRewardRisk": rr}) for rr in (0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0)]),
        ("management", [
            ("none", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.0, "InpUseDynamicTrailingSL": False}),
            ("be05", {"InpBreakEvenAtR": 0.5, "InpTrailStartAtR": 0.0, "InpUseDynamicTrailingSL": False}),
            ("be1", {"InpBreakEvenAtR": 1.0, "InpTrailStartAtR": 0.0, "InpUseDynamicTrailingSL": False}),
            ("trail05", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.5, "InpUseDynamicTrailingSL": False}),
            ("trail1", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 1.0, "InpUseDynamicTrailingSL": False}),
            ("dynamic5020", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.0, "InpUseDynamicTrailingSL": True, "InpDynamicTriggerFraction": 0.50, "InpDynamicLockFraction": 0.20}),
            ("dynamic6020", {"InpBreakEvenAtR": 0.0, "InpTrailStartAtR": 0.0, "InpUseDynamicTrailingSL": True, "InpDynamicTriggerFraction": 0.60, "InpDynamicLockFraction": 0.20}),
        ]),
        ("window", [(f"window{minutes}", {"InpTradeWindowMinutes": minutes}) for minutes in (60, 120, 180, 240)]),
        ("safe", [("safe-off", {"InpUseMarkovRegimeFilter": False}), ("safe-on", {"InpUseMarkovRegimeFilter": True})]),
    ]

    for phase, specs in phase_specs:
        rows_all = []
        winners: dict[str, dict] = {}
        for symbol, anchor in all_pairs:
            base = deepcopy(current[(symbol, anchor)]["config"])
            variants = []
            for label, changes in specs:
                config = deepcopy(base)
                config.update(changes)
                config["InpRiskPercent"] = 1.0
                variants.append((label, config))
            winner, rows, sequence = run_variants(symbol, anchor, phase, variants, sequence)
            current[(symbol, anchor)] = winner
            winners[f"{symbol}::{anchor}"] = winner
            rows_all.extend(rows)
        phases[phase] = rows_all
        save_phase(phase, rows_all, winners)

    return current, phases, sequence, selected_anchors


def final_validation(current: dict[tuple[str, str], dict], phases: dict[str, list[dict]], sequence: int,
                     selected_anchors: dict[str, list[str]]) -> dict:
    audit = {
        "design": {
            "opening_range_minutes": 60,
            "development": "2023-09-01 to 2025-08-31",
            "locked": "2025-09-01 to 2026-09-01",
            "full": "2023-09-01 to 2026-09-01",
            "risk_percent": 1.0,
            "selection": "All parameters and primary anchor selected before locked-year results were read",
            "safe_filter": "Completed D1 Markov gate; no lookahead",
        },
        "development_phases": {name: [clean(row) for row in rows] for name, rows in phases.items()},
        "symbols": {},
    }
    final_rows = []
    raw_locked = {}
    for symbol in SYMBOLS:
        candidates = [current[(symbol, anchor)] for anchor in selected_anchors[symbol]]
        ordered = sorted(candidates, key=score, reverse=True)
        audit["symbols"][symbol] = {"development_order": [row["session"] for row in ordered], "anchors": {}}
        for rank, development_row in enumerate(ordered, start=1):
            anchor = development_row["session"]
            config = deepcopy(development_row["config"])
            sequence += 1
            locked = run_case(symbol, anchor, "locked", f"development-rank{rank}", config, sequence, LOCKED)
            sequence += 1
            full = run_case(symbol, anchor, "full", f"development-rank{rank}", config, sequence, FULL)
            outcomes = ORB.ANALYZER.trade_outcomes(locked["deals"])
            mc = ORB.ANALYZER.monte_carlo(outcomes, locked["initial_balance"], 10_000)
            verdict = "PASS / demo candidate" if (
                locked["return_pct"] > 0 and locked["profit_factor"] >= 1.20 and locked["trades"] >= 20
                and locked["max_drawdown_pct"] <= 12 and mc["return_p5_pct"] > 0
            ) else ("WATCH" if locked["return_pct"] > 0 and locked["profit_factor"] > 1 else "REJECT")
            audit["symbols"][symbol]["anchors"][anchor] = {
                "development_rank": rank,
                "selected_config": config,
                "development": clean(development_row),
                "locked": clean(locked),
                "full": clean(full),
                "monte_carlo": mc,
                "verdict": verdict,
            }
            raw_locked[(symbol, anchor)] = locked
            set_name = f"{symbol.upper()} - {anchor} - H1 opening range - 1pct.set"
            (ORB.SETS / set_name).write_text(ORB.set_text(config, 962000000 + sequence), encoding="utf-8")
            final_rows.append({
                "symbol": symbol,
                "anchor": anchor,
                "development_rank": rank,
                "verdict": verdict,
                "signal_timeframe": PERIOD_NAMES[int(config["InpSignalTimeframe"])],
                "entry_mode": "direct" if int(config["InpEntryMode"]) == 0 else "retest",
                "rr": config["InpRewardRisk"],
                "stop_mode": "signal" if int(config["InpStopMode"]) == 0 else "opposite",
                "stop_buffer_atr": config["InpStopBufferATR"],
                "max_stop_atr": config["InpMaximumStopATR"],
                "management": next((row["variant"] for row in phases["management"] if row["symbol"] == symbol and row["session"] == anchor and row["config"] == config), "selected pipeline"),
                "safe": config["InpUseMarkovRegimeFilter"],
                "locked_return_pct": locked["return_pct"],
                "locked_pf": locked["profit_factor"],
                "locked_win_pct": locked["win_rate_pct"],
                "locked_dd_pct": locked["max_drawdown_pct"],
                "locked_trades": locked["trades"],
                "locked_sharpe": locked["sharpe"],
                "locked_recovery": locked["recovery_factor"],
                "mc_return_p5_pct": mc["return_p5_pct"],
                "mc_return_median_pct": mc["return_median_pct"],
                "mc_dd_p95_pct": mc["max_dd_p95_pct"],
                "full_return_pct": full["return_pct"],
                "full_pf": full["profit_factor"],
                "full_win_pct": full["win_rate_pct"],
                "full_dd_pct": full["max_drawdown_pct"],
                "full_trades": full["trades"],
                "full_sharpe": full["sharpe"],
                "full_recovery": full["recovery_factor"],
            })
    audit["final_rows"] = final_rows
    audit["sequence_count"] = sequence
    (ROOT / "FINAL AUDIT.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    with (ROOT / "FINAL AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(final_rows[0]))
        writer.writeheader()
        writer.writerows(final_rows)
    plot_results(audit, raw_locked)
    write_report(audit)
    return audit


def plot_results(audit: dict, raw_locked: dict) -> None:
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    plt.style.use("dark_background")
    fig, axes = plt.subplots(3, 2, figsize=(16, 15), dpi=170)
    fig.patch.set_facecolor("#07110f")
    colors = ["#6ee7b7", "#38bdf8"]
    for axis in axes.flat:
        axis.set_facecolor("#0b1714")
        axis.grid(color="#94a3b8", alpha=0.15)
        axis.spines[["top", "right"]].set_visible(False)
    for row_index, symbol in enumerate(SYMBOLS):
        item = audit["symbols"][symbol]
        anchors = item["development_order"]
        ax = axes[row_index, 0]
        for color, anchor in zip(colors, anchors):
            raw = raw_locked[(symbol, anchor)]
            dates, balances = ORB.ANALYZER.equity_points(raw, datetime(2025, 9, 1))
            ax.step(dates, balances, where="post", color=color, linewidth=1.5, label=ANCHORS[anchor]["label"])
        ax.axhline(10000, color="#94a3b8", linestyle="--", linewidth=0.8)
        ax.set_title(f"{ORB.DISPLAY[symbol]} — locked-year equity", loc="left", fontweight="bold")
        ax.set_ylabel("USD")
        ax.legend(frameon=False, fontsize=8)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))

        ax = axes[row_index, 1]
        rows = [item["anchors"][anchor]["locked"] for anchor in anchors]
        x = list(range(len(rows)))
        ax.bar([v - 0.2 for v in x], [row["return_pct"] for row in rows], width=0.4, color=colors, label="Return")
        ax.bar([v + 0.2 for v in x], [row["max_drawdown_pct"] for row in rows], width=0.4, color="#ef4444", alpha=0.8, label="DD")
        ax.set_xticks(x, [ANCHORS[a]["label"] for a in anchors], rotation=10, ha="right")
        ax.set_title(f"{ORB.DISPLAY[symbol]} — return vs DD", loc="left", fontweight="bold")
        ax.set_ylabel("Percent")
        ax.legend(frameon=False)
        for i, row in enumerate(rows):
            ax.text(i, max(row["return_pct"], 0), f"PF {row['profit_factor']:.2f}\nn={row['trades']}", ha="center", va="bottom", fontsize=8)
    fig.suptitle("One-hour Opening Range Breakout — locked validation", fontsize=20, fontweight="bold", y=0.995)
    fig.text(0.5, 0.975, "XAUUSD · XAGUSD · USTEC · MT5 Every Tick · broker costs + random delay · fixed 1% risk",
             ha="center", color="#94a3b8", fontsize=9)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(ORB.CHARTS / "H1 ORB LOCKED RESULTS.png", bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def write_report(audit: dict) -> None:
    lines = [
        "# One-Hour Opening Range Breakout — XAU, XAG and US100",
        "",
        "## Test design",
        "",
        "The opening range is exactly 60 minutes. Anchor, signal timeframe, direct versus retest entry, confirmation, stop placement, RR, management, trade window and the optional completed-D1 Safe gate were selected only on 2023-09-01 through 2025-08-31. The untouched year is 2025-09-01 through 2026-09-01. Final context is exact three-year Every Tick history. Every run uses $10,000 and fixed 1% equity risk with broker costs and random delay.",
        "",
        "## Finalists",
        "",
        "| Market | Anchor | Dev rank | Verdict | Config | Locked return | PF | Win | DD | Trades | Sharpe | Recovery | MC P5 | MC DD P95 | 3Y return | 3Y PF |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol in SYMBOLS:
        item = audit["symbols"][symbol]
        for anchor in item["development_order"]:
            result = item["anchors"][anchor]
            config = result["selected_config"]
            locked = result["locked"]
            full = result["full"]
            mc = result["monte_carlo"]
            setup = (
                f"{PERIOD_NAMES[int(config['InpSignalTimeframe'])]}, "
                f"{'direct' if int(config['InpEntryMode']) == 0 else 'retest'}, {config['InpRewardRisk']}R, "
                f"{'signal' if int(config['InpStopMode']) == 0 else 'opposite'} stop, "
                f"{config['InpTradeWindowMinutes']}m, Safe {'on' if config['InpUseMarkovRegimeFilter'] else 'off'}"
            )
            lines.append(
                f"| {ORB.DISPLAY[symbol]} | {ANCHORS[anchor]['label']} | {result['development_rank']} | {result['verdict']} | {setup} | "
                f"{locked['return_pct']:+.2f}% | {locked['profit_factor']:.2f} | {locked['win_rate_pct']:.2f}% | "
                f"{locked['max_drawdown_pct']:.2f}% | {locked['trades']} | {locked['sharpe']:.2f} | "
                f"{locked['recovery_factor']:.2f} | {mc['return_p5_pct']:+.2f}% | {mc['max_dd_p95_pct']:.2f}% | "
                f"{full['return_pct']:+.2f}% | {full['profit_factor']:.2f} |"
            )
    lines += [
        "",
        "## Integrity notes",
        "",
        "- No one-hour ORB was added to a BAT, selected portfolio preset or the website during research.",
        "- Safe mode is the existing completed-D1, no-lookahead Markov gate and remains independent per EA.",
        "- Exness USTEC, XAUUSD and XAGUSD are CFDs. Tick volume is broker activity, not centralized CME volume.",
        "- Monte Carlo resamples the locked-year trade outcomes 10,000 times; it is a robustness estimate, not a forecast.",
        "- Stepwise optimization can still overfit. Only candidates that survive the untouched year should move to demo testing.",
        "",
        "## Artifacts",
        "",
        "- `FINAL AUDIT.csv` and `FINAL AUDIT.json`",
        "- `Charts/H1 ORB LOCKED RESULTS.png`",
        "- Phase-level JSON files for anchor, timeframe, entry, confirmation, stop, RR, management, window and Safe mode",
        "- Reproducible `.set` files in `Sets/`",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    prepare()
    current, phases, sequence, selected_anchors = phase_pipeline()
    audit = final_validation(current, phases, sequence, selected_anchors)
    print(json.dumps(audit["final_rows"], indent=2), flush=True)
    print(f"COMPLETED {audit['sequence_count']} native MT5 cases", flush=True)


if __name__ == "__main__":
    main()
