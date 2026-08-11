from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd

import research_optimize as base
import research_optimize_v2 as v2


DESTINATION = base.RESEARCH / "reports-exact-20-points"


def mixed_values(
    sessions: list[v2.Session],
    signal: v2.Signal,
    long_matrix: np.ndarray,
    short_matrix: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    include, directions = v2.signal_arrays(sessions, signal)
    matrix = np.where(directions[:, None] > 0, long_matrix, short_matrix)
    return include, directions, matrix


def choose_execution(
    sessions: list[v2.Session],
    signal: v2.Signal,
    long_matrix: np.ndarray,
    short_matrix: np.ndarray,
) -> tuple[v2.Outcome, pd.DataFrame]:
    outcome_list = v2.outcomes()
    dates = np.asarray([np.datetime64(session.session_date) for session in sessions])
    include, _, matrix = mixed_values(sessions, signal, long_matrix, short_matrix)
    train_mask = include & (dates < np.datetime64("2024-01-01"))
    validation_mask = include & (dates >= np.datetime64("2024-01-01")) & (dates < np.datetime64("2025-01-01"))
    train = v2.nan_vector_metrics(matrix[train_mask])
    validation = v2.nan_vector_metrics(matrix[validation_mask])
    rows = []
    for col, outcome in enumerate(outcome_list):
        if train["count"][col] < 20 or validation["count"][col] < 5:
            continue
        rows.append(
            {
                **asdict(outcome),
                "outcome_index": col,
                "score": float(min(train["lcb"][col], validation["lcb"][col])),
                "train_trades": int(train["count"][col]),
                "train_pf": float(train["pf"][col]),
                "train_mean_r": float(train["mean"][col]),
                "validation_trades": int(validation["count"][col]),
                "validation_pf": float(validation["pf"][col]),
                "validation_mean_r": float(validation["mean"][col]),
            }
        )
    table = pd.DataFrame(rows).sort_values(["score", "validation_pf", "train_pf"], ascending=False)
    if table.empty:
        raise RuntimeError("The exact 20-point signal has too few trades to choose an execution configuration")
    winner = table.iloc[0]
    outcome = v2.Outcome(
        str(winner.entry_mode),
        int(winner.entry_cutoff_minute),
        float(winner.stop_range_multiple),
        float(winner.minimum_stop_points),
        float(winner.reward_risk),
        str(winner.trailing_mode),
        int(winner.exit_minute),
    )
    return outcome, table


def trade_frame(sessions: list[v2.Session], signal: v2.Signal, outcome: v2.Outcome) -> pd.DataFrame:
    include, directions = v2.signal_arrays(sessions, signal)
    rows = []
    for session, use, direction in zip(sessions, include, directions):
        if not use:
            continue
        detail = v2.simulate(session, int(direction), outcome, detail=True)
        if detail is not None:
            rows.append(detail)
    return pd.DataFrame(rows)


def period_metrics(trades: pd.DataFrame) -> dict:
    dates = pd.to_datetime(trades.date)
    masks = {
        "training_2019_2023": dates < pd.Timestamp("2024-01-01"),
        "validation_2024": (dates >= pd.Timestamp("2024-01-01")) & (dates < pd.Timestamp("2025-01-01")),
        "holdout_2025_2026": dates >= pd.Timestamp("2025-01-01"),
        "full": np.ones(len(trades), dtype=bool),
    }
    return {name: base.scalar_metrics(trades.loc[mask, "result_r"]) for name, mask in masks.items()}


def main() -> int:
    DESTINATION.mkdir(parents=True, exist_ok=True)
    raw, manifest = base.download_history()
    sessions, quality = v2.build_sessions(raw, manifest["median_positive_spread_points"])
    cache = np.load(base.RESEARCH / "reports-v2-aligned-breakout" / "outcome-cache.npz")
    long_matrix = cache["long"]
    short_matrix = cache["short"]

    # Locked wording: Asia and London both point the same way; matching Asia/New York
    # extremes are within 20 index points; trade both directions.
    signal = v2.Signal(
        proximity_threshold=20.0,
        minimum_trend=0.0,
        trend_definition="asia_and_london_aligned",
        proximity_relation="absolute",
        direction_mode="both",
        maximum_opening_range=400.0,
    )
    outcome, ranking = choose_execution(sessions, signal, long_matrix, short_matrix)
    trades = trade_frame(sessions, signal, outcome)
    metrics = period_metrics(trades)
    result = {
        "signal": asdict(signal),
        "selected_execution": asdict(outcome),
        "quality": quality,
        "metrics": metrics,
        "selection_note": "Only execution parameters were selected on 2019-2024. The 20-point signal was locked before evaluation.",
    }
    (DESTINATION / "results.json").write_text(json.dumps(base.json_safe(result), indent=2), encoding="utf-8")
    ranking.to_csv(DESTINATION / "execution-ranking.csv", index=False)
    trades.to_csv(DESTINATION / "trades.csv", index=False)
    lines = [
        "# Exact 20-Point US100 Signal",
        "",
        "Locked signal: both Asia and London sessions point in the same direction, and the matching first-New-York-15-minute extreme is within 20 index points of the Asia extreme.",
        "",
        "## Selected execution (chosen without 2025–2026)",
        "",
        *[f"- {key}: `{value}`" for key, value in asdict(outcome).items()],
        "",
    ]
    for period, values in metrics.items():
        lines.extend(
            [
                f"## {period}",
                "",
                f"- Trades: {values['trades']}",
                f"- Return: {values['return_pct']:.2f}%",
                f"- PF: {values['profit_factor']:.2f}",
                f"- Win rate: {values['win_rate_pct']:.2f}%",
                f"- Closed-balance DD: {values['max_closed_balance_dd_pct']:.2f}%",
                "",
            ]
        )
    (DESTINATION / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(base.json_safe(result), indent=2))
    print(f"Exact-20 report: {DESTINATION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
