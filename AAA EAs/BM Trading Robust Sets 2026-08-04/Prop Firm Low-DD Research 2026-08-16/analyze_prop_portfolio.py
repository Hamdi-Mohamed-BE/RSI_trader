from __future__ import annotations

import csv
import importlib.util
import json
import math
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
SOURCE = PACKAGE / "Active BAT Backtest 5Y 2026-08-12"
PARSER_PATH = PACKAGE / "BAT Portfolio Backtest 2026-08-09" / "Build-BAT-Portfolio-Report.py"
STARTING_BALANCE = 10_000.0
START = datetime(2021, 8, 11)
END = datetime(2026, 8, 10)
SEED = 20260816

SELECTED_IDS = [
    "02-orb-volume-profile",
    "07-aaa-final-ema3",
    "10-nasdaq-overnight",
]

SCENARIOS = {
    "high_win_core_1pct": {
        "07-aaa-final-ema3": 1.0,
        "10-nasdaq-overnight": 1.0,
    },
    "balanced_035pct": {key: 0.35 for key in SELECTED_IDS},
    "balanced_050pct": {key: 0.50 for key in SELECTED_IDS},
    "balanced_075pct": {key: 0.75 for key in SELECTED_IDS},
    "balanced_100pct": {key: 1.00 for key in SELECTED_IDS},
    "ftmo_eligible_035pct": {
        "02-orb-volume-profile": 0.35,
        "07-aaa-final-ema3": 0.35,
    },
    "ftmo_eligible_050pct": {
        "02-orb-volume-profile": 0.50,
        "07-aaa-final-ema3": 0.50,
    },
    "ftmo_eligible_075pct": {
        "02-orb-volume-profile": 0.75,
        "07-aaa-final-ema3": 0.75,
    },
}


def load_parser():
    spec = importlib.util.spec_from_file_location("mt5_report_parser", PARSER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load parser: {PARSER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def max_drawdown(points: list[tuple[datetime, float]]) -> tuple[float, float]:
    peak = points[0][1]
    worst_amount = 0.0
    worst_pct = 0.0
    for _, value in points:
        peak = max(peak, value)
        amount = peak - value
        pct = amount / peak * 100.0 if peak else 0.0
        if pct > worst_pct:
            worst_amount = amount
            worst_pct = pct
    return worst_amount, worst_pct


def cagr(final: float, years: float) -> float:
    return ((final / STARTING_BALANCE) ** (1.0 / years) - 1.0) * 100.0 if final > 0 else -100.0


def scenario_metrics(name: str, weights: dict[str, float], rows: dict[str, dict]) -> tuple[dict, list[tuple[datetime, float]], np.ndarray]:
    events = []
    daily = defaultdict(float)
    for order, bot_id in enumerate(SELECTED_IDS):
        if bot_id not in weights:
            continue
        weight = weights[bot_id]
        for deal in rows[bot_id]["deals"]:
            cashflow = deal["cashflow"] * weight
            events.append((deal["time"], order, cashflow))
            daily[deal["time"].date()] += cashflow
    events.sort(key=lambda item: (item[0], item[1]))

    balance = STARTING_BALANCE
    curve = [(START, balance)]
    for when, _, cashflow in events:
        balance += cashflow
        curve.append((when, balance))
    curve.append((END, balance))
    dd_amount, dd_pct = max_drawdown(curve)

    gross_profit = sum(rows[key]["gross_profit"] * weight for key, weight in weights.items())
    gross_loss = sum(rows[key]["gross_loss"] * weight for key, weight in weights.items())
    trades = sum(rows[key]["trades"] for key in weights)
    wins = sum(rows[key]["wins"] for key in weights)
    years = (END - START).days / 365.2425

    weekdays = np.busday_offset(
        np.datetime64(START.date()),
        np.arange(np.busday_count(START.date(), END.date()) + 1),
        roll="forward",
    )
    daily_returns = np.array(
        [daily.get(datetime.fromisoformat(str(day)).date(), 0.0) / STARTING_BALANCE for day in weekdays],
        dtype=float,
    )
    nonzero = daily_returns[np.abs(daily_returns) > 1e-12]
    max_daily_loss_pct = abs(min(float(daily_returns.min()), 0.0)) * 100.0
    worst_sum_equity_dd = sum(rows[key]["equity_dd_pct"] * weight for key, weight in weights.items())

    result = {
        "scenario": name,
        "weights_pct_per_trade": weights,
        "initial": STARTING_BALANCE,
        "final": balance,
        "net": balance - STARTING_BALANCE,
        "return_pct": (balance / STARTING_BALANCE - 1.0) * 100.0,
        "cagr_pct": cagr(balance, years),
        "realized_max_dd_amount": dd_amount,
        "realized_max_dd_pct": dd_pct,
        "conservative_sum_of_individual_equity_dd_pct": worst_sum_equity_dd,
        "profit_factor": gross_profit / abs(gross_loss) if gross_loss else 0.0,
        "win_rate_pct": wins / trades * 100.0 if trades else 0.0,
        "wins": wins,
        "trades": trades,
        "active_days": int(nonzero.size),
        "max_realized_daily_loss_pct": max_daily_loss_pct,
    }
    return result, curve, daily_returns


def block_bootstrap_paths(daily_returns: np.ndarray, paths: int, days: int, block: int, rng: np.random.Generator) -> np.ndarray:
    blocks = math.ceil(days / block)
    max_start = len(daily_returns) - block
    starts = rng.integers(0, max_start + 1, size=(paths, blocks))
    offsets = np.arange(block)
    indices = (starts[:, :, None] + offsets[None, None, :]).reshape(paths, -1)[:, :days]
    return daily_returns[indices]


def prop_simulation(daily_returns: np.ndarray, stressed: bool, paths: int = 20_000, days: int = 756) -> dict:
    rng = np.random.default_rng(SEED + (1 if stressed else 0))
    sampled = block_bootstrap_paths(daily_returns, paths, days, 20, rng)
    if stressed:
        sampled = np.where(sampled >= 0.0, sampled * 0.90, sampled * 1.10)

    # 0=phase 1, 1=verification, 2=funded, 3=first payout, -1=failed.
    stage = np.zeros(paths, dtype=np.int8)
    balance = np.ones(paths, dtype=float)
    trade_days = np.zeros(paths, dtype=np.int16)
    funded_days = np.zeros(paths, dtype=np.int16)
    payout_day = np.full(paths, -1, dtype=np.int16)
    payout_gross_pct = np.zeros(paths, dtype=float)

    checkpoints = {252: {}, 504: {}, 756: {}}
    for day in range(days):
        live = (stage >= 0) & (stage < 3)
        today = sampled[:, day]
        balance[live] *= 1.0 + today[live]
        trade_days[live & (np.abs(today) > 1e-12)] += 1
        funded_days[stage == 2] += 1

        failed = live & ((today <= -0.05) | (balance <= 0.90))
        stage[failed] = -1

        p1 = (stage == 0) & (balance >= 1.10) & (trade_days >= 4)
        stage[p1] = 1
        balance[p1] = 1.0
        trade_days[p1] = 0

        p2 = (stage == 1) & (balance >= 1.05) & (trade_days >= 4)
        stage[p2] = 2
        balance[p2] = 1.0
        funded_days[p2] = 0

        payout = (stage == 2) & (funded_days >= 10) & (balance >= 1.02)
        payout_gross_pct[payout] = (balance[payout] - 1.0) * 100.0
        payout_day[payout] = day + 1
        stage[payout] = 3

        checkpoint_day = day + 1
        if checkpoint_day in checkpoints:
            checkpoints[checkpoint_day] = {
                "phase1_passed_or_better_pct": float(np.mean(stage >= 1) * 100.0),
                "phase2_passed_or_better_pct": float(np.mean(stage >= 2) * 100.0),
                "first_payout_pct": float(np.mean(stage == 3) * 100.0),
                "failed_pct": float(np.mean(stage == -1) * 100.0),
            }

    paid = payout_day > 0
    return {
        "model": "20-day block bootstrap; phase targets 10% then 5%; static 10% loss; 5% daily loss; 4 trading-day minimum; first funded payout modelled at +2% after 10 trading days; 80% trader split",
        "stressed": stressed,
        "paths": paths,
        "checkpoints": {f"{day // 252}_year": values for day, values in checkpoints.items()},
        "median_trading_days_to_first_payout_if_paid": float(np.median(payout_day[paid])) if paid.any() else None,
        "p10_p90_trading_days_to_first_payout_if_paid": [
            float(np.percentile(payout_day[paid], 10)),
            float(np.percentile(payout_day[paid], 90)),
        ] if paid.any() else None,
        "median_gross_first_payout_pct_if_paid": float(np.median(payout_gross_pct[paid])) if paid.any() else None,
        "median_net_first_payout_pct_at_80_split_if_paid": float(np.median(payout_gross_pct[paid]) * 0.80) if paid.any() else None,
    }


def main() -> None:
    parser = load_parser()
    manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8-sig"))
    cases = {case["id"]: case for case in manifest if case["id"] in SELECTED_IDS}
    rows = {key: parser.parse_report(Path(case["report"]), case) for key, case in cases.items()}

    individual = []
    for key in SELECTED_IDS:
        row = rows[key]
        individual.append({
            "id": key,
            "strategy": row["label"],
            "chart": row["chart"],
            "return_pct": row["return_pct"],
            "equity_dd_pct": row["equity_dd_pct"],
            "profit_factor": row["profit_factor"],
            "win_rate_pct": row["win_rate_pct"],
            "trades": row["trades"],
        })

    scenario_rows = []
    curves = {}
    daily_by_scenario = {}
    for name, weights in SCENARIOS.items():
        result, curve, daily_returns = scenario_metrics(name, weights, rows)
        scenario_rows.append(result)
        curves[name] = curve
        daily_by_scenario[name] = daily_returns

    recommended_name = "ftmo_eligible_050pct"
    monte_carlo = {}
    for scenario_name in ["ftmo_eligible_035pct", "ftmo_eligible_050pct", "ftmo_eligible_075pct"]:
        monte_carlo[scenario_name] = {
            "nominal": prop_simulation(daily_by_scenario[scenario_name], stressed=False),
            "execution_stress": prop_simulation(daily_by_scenario[scenario_name], stressed=True),
        }

    output = {
        "individual_mt5_5y": individual,
        "portfolio_scenarios": scenario_rows,
        "monte_carlo": monte_carlo,
        "ftmo_eligibility_note": "Nasdaq Overnight is excluded from the FTMO portfolio because its close-to-open holding logic may conflict with FTMO's current gap-trading prohibition.",
    }
    (ROOT / "results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")

    fields = [
        "scenario", "initial", "final", "net", "return_pct", "cagr_pct", "realized_max_dd_amount",
        "realized_max_dd_pct", "conservative_sum_of_individual_equity_dd_pct", "profit_factor",
        "win_rate_pct", "wins", "trades", "active_days", "max_realized_daily_loss_pct",
    ]
    with (ROOT / "portfolio-scenarios.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(scenario_rows)

    fig, ax = plt.subplots(figsize=(13, 6.2), dpi=170)
    colors = {
        "high_win_core_1pct": "#845EC2",
        "balanced_035pct": "#0081CF",
        "balanced_050pct": "#00A36C",
        "balanced_075pct": "#E09600",
        "balanced_100pct": "#C43C3C",
        "ftmo_eligible_035pct": "#2D9CDB",
        "ftmo_eligible_050pct": "#27AE60",
        "ftmo_eligible_075pct": "#F2994A",
    }
    for name, curve in curves.items():
        ax.plot([p[0] for p in curve], [p[1] for p in curve], label=name.replace("_", " "), linewidth=1.4, color=colors[name])
    ax.axhline(STARTING_BALANCE, color="#777", linestyle="--", linewidth=0.8)
    ax.set_title("Prop-strategy candidates — realized MT5 balance curves")
    ax.set_ylabel("Balance (USD), starting at $10,000")
    ax.grid(alpha=0.18)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "portfolio-risk-comparison.png")
    plt.close(fig)

    rec_curve = curves[recommended_name]
    fig, ax = plt.subplots(figsize=(13, 6.2), dpi=170)
    ax.plot([p[0] for p in rec_curve], [p[1] for p in rec_curve], color="#00A36C", linewidth=1.7)
    ax.axhline(STARTING_BALANCE, color="#777", linestyle="--", linewidth=0.8)
    ax.set_title("FTMO-eligible research portfolio — 0.50% per trade")
    ax.set_ylabel("Realized balance (USD), starting at $10,000")
    ax.grid(alpha=0.18)
    fig.tight_layout()
    fig.savefig(ROOT / "recommended-equity.png")
    plt.close(fig)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
