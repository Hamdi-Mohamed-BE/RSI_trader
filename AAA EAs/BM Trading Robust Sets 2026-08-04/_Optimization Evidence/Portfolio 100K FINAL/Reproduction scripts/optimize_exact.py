from __future__ import annotations

import importlib.util
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy.optimize import differential_evolution


ROOT = Path(r"C:\Users\hama101\Downloads\BM Trading EAs 2026-08-04\portfolio optimization")
ANALYZER = ROOT / "analyze_portfolio.py"
spec = importlib.util.spec_from_file_location("portfolio_analyzer", ANALYZER)
pa = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pa
spec.loader.exec_module(pa)

ALL_CODES = list(pa.REPORTS)
SELECTED = ["RB", "GL", "TT", "ATR"]
STRESS_FACTOR = 1.25
RAW_MONTHLY_DD_LIMIT = 4_000.0 / STRESS_FACTOR


def main() -> None:
    parsed = {
        code: pa.parse_report(code, pa.REPORT_DIR / filename)
        for code, filename in pa.REPORTS.items()
    }
    timestamps = sorted({deal["timestamp"] for report in parsed.values() for deal in report.deals})
    event_index = {timestamp: index for index, timestamp in enumerate(timestamps)}
    full_matrix = np.zeros((len(timestamps), len(ALL_CODES)), dtype=float)
    for column, code in enumerate(ALL_CODES):
        for deal in parsed[code].deals:
            full_matrix[event_index[deal["timestamp"]], column] += deal["net"]
    columns = [ALL_CODES.index(code) for code in SELECTED]
    matrix = full_matrix[:, columns]

    months = [f"{year}-{month:02d}" for year in (2023, 2024, 2025, 2026) for month in range(1, 13)]
    months = [month for month in months if month <= "2026-07"]
    train_count = 24
    month_profit_matrix = []
    month_curves = []
    for month in months:
        mask = np.asarray([timestamp.strftime("%Y-%m") == month for timestamp in timestamps])
        event_values = matrix[mask]
        month_profit_matrix.append(event_values.sum(axis=0))
        curve = np.vstack((np.zeros((1, len(SELECTED))), np.cumsum(event_values, axis=0)))
        month_curves.append(curve)
    month_profit_matrix = np.asarray(month_profit_matrix)

    def raw_metrics(weights: np.ndarray) -> tuple[float, float, float, float]:
        profits = month_profit_matrix @ weights
        train_avg = float(profits[:train_count].mean())
        valid_avg = float(profits[train_count:].mean())
        drawdowns = []
        for curve_matrix in month_curves:
            curve = curve_matrix @ weights
            drawdowns.append(float(np.max(np.maximum.accumulate(curve) - curve)))
        return train_avg, valid_avg, max(drawdowns[:train_count]), max(drawdowns[train_count:])

    def objective(weights: np.ndarray) -> float:
        train_avg, valid_avg, train_dd, valid_dd = raw_metrics(weights)
        robust_return = min(train_avg, valid_avg) + 0.20 * ((train_avg + valid_avg) / 2.0)
        excess = max(0.0, train_dd - RAW_MONTHLY_DD_LIMIT) + max(0.0, valid_dd - RAW_MONTHLY_DD_LIMIT)
        return -robust_return + 25.0 * excess + 0.002 * float(np.sum(weights * weights))

    bounds = [(0.0, 15.0), (0.0, 25.0), (0.0, 25.0), (0.0, 15.0)]
    continuous_results = []
    for seed in (20260804, 417, 99173):
        result = differential_evolution(
            objective,
            bounds=bounds,
            seed=seed,
            maxiter=220,
            popsize=18,
            tol=1e-8,
            polish=True,
            workers=1,
            updating="immediate",
        )
        continuous_results.append(result.x)

    # Quantize to quarter-step multipliers so the delivered settings are simple and reproducible.
    grid_candidates = []
    for result in continuous_results:
        center = np.round(result * 4.0) / 4.0
        axes = []
        for value, (_, upper) in zip(center, bounds, strict=True):
            axes.append(sorted({max(0.0, min(upper, value + step * 0.25)) for step in range(-6, 7)}))
        grid_candidates.extend(np.asarray(candidate) for candidate in itertools.product(*axes))

    best = None
    feasible = []
    seen = set()
    for weights in grid_candidates:
        key = tuple(float(value) for value in weights)
        if key in seen:
            continue
        seen.add(key)
        train_avg, valid_avg, train_dd, valid_dd = raw_metrics(weights)
        if train_dd > RAW_MONTHLY_DD_LIMIT + 1e-9 or valid_dd > RAW_MONTHLY_DD_LIMIT + 1e-9:
            continue
        robust_return = min(train_avg, valid_avg) + 0.20 * ((train_avg + valid_avg) / 2.0)
        item = {
            "weights_selected": {code: float(weights[index]) for index, code in enumerate(SELECTED)},
            "weights_all": {
                code: float(weights[SELECTED.index(code)]) if code in SELECTED else 0.0
                for code in ALL_CODES
            },
            "train_average_monthly": train_avg,
            "validation_average_monthly": valid_avg,
            "train_max_monthly_closed_dd": train_dd,
            "validation_max_monthly_closed_dd": valid_dd,
            "train_stressed_monthly_dd": train_dd * STRESS_FACTOR,
            "validation_stressed_monthly_dd": valid_dd * STRESS_FACTOR,
            "robust_score": robust_return,
        }
        feasible.append(item)
        if best is None or item["robust_score"] > best["robust_score"]:
            best = item

    if best is None:
        raise RuntimeError("No quantized exact candidate passed the drawdown constraint")

    all_weights = np.asarray([best["weights_all"][code] for code in ALL_CODES])
    train_mask = np.asarray([timestamp.year < 2025 for timestamp in timestamps])
    valid_mask = ~train_mask
    train_months = months[:train_count]
    valid_months = months[train_count:]
    best["train"] = pa.period_metrics(
        all_weights,
        [timestamp for timestamp, keep in zip(timestamps, train_mask, strict=True) if keep],
        full_matrix[train_mask],
        train_months,
    )
    best["validation"] = pa.period_metrics(
        all_weights,
        [timestamp for timestamp, keep in zip(timestamps, valid_mask, strict=True) if keep],
        full_matrix[valid_mask],
        valid_months,
    )
    best["combined"] = pa.period_metrics(all_weights, timestamps, full_matrix, months)

    feasible.sort(key=lambda item: item["robust_score"], reverse=True)
    payload = {
        "purpose": "Maximum robust return under stressed 4% monthly closed-balance drawdown proxy",
        "excluded": {
            "Ninja": "Negative 2025-2026 validation profit",
            "Fisher": "Negative 2025-2026 validation profit",
        },
        "stress_factor": STRESS_FACTOR,
        "raw_monthly_dd_limit": RAW_MONTHLY_DD_LIMIT,
        "continuous_solutions": [list(map(float, result)) for result in continuous_results],
        "quantized_candidates_checked": len(seen),
        "feasible_candidates": len(feasible),
        "best": best,
        "top_20": feasible[:20],
    }
    output = ROOT / "analysis" / "exact-portfolio-analysis.json"
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(best, indent=2))


if __name__ == "__main__":
    main()
