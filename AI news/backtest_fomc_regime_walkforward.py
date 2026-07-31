from __future__ import annotations

import json
import math

from backtest_fomc_regime import (
    WINDOWS,
    _agreement,
    _fit,
    _logistic,
    _metrics,
    _prediction,
    _prepare_rows,
    _probability_positive,
)
from fomc_pipeline import (
    fit_fomc_model,
    model_probability_positive,
)
from gold_direction_rules import rule_direction
from fomc_pipeline import FOMC_HISTORY_RULE
from news_core import ROOT


OUTPUT_JSON = ROOT / "fomc_regime_walkforward.json"
OUTPUT_MD = ROOT / "FOMC_REGIME_WALKFORWARD.md"


def _union(old: str | None, regime: str | None) -> str | None:
    if old and regime and old != regime:
        return None
    return old or regime


def run() -> dict:
    rows, source_audit, _ = _prepare_rows()
    events = []
    for row in rows:
        if row["release_utc"][:10] < WINDOWS[0][0]:
            continue
        training = [
            previous
            for previous in rows
            if previous["release_utc"] < row["release_utc"]
        ]
        if len(training) < 20:
            continue
        history = [previous["actual"] for previous in training]
        history_prediction = rule_direction(FOMC_HISTORY_RULE, history)

        v1 = fit_fomc_model(training)
        v1_probability = model_probability_positive(v1, row["features"])
        v1_prediction = _prediction(v1_probability)

        direct_lr = _fit(
            _logistic(), training, "enhanced", "actual"
        )
        regime_probability = _probability_positive(
            direct_lr, row["enhanced"]
        )
        regime_prediction = _prediction(regime_probability)

        old_agreement = _agreement(
            history_prediction, v1_prediction
        )
        regime_agreement = _agreement(
            history_prediction, regime_prediction
        )
        selective_regime = (
            regime_agreement
            if abs(regime_probability - 0.5) >= 0.10
            else None
        )
        events.append(
            {
                "release_utc": row["release_utc"],
                "actual": row["actual"],
                "move_usd": round(
                    float(row["reaction"]["release_move"]), 4
                ),
                "history": history_prediction,
                "v1_model": v1_prediction,
                "regime_model": regime_prediction,
                "v1_history_agreement": old_agreement,
                "regime_history_agreement": regime_agreement,
                "regime_history_conf60": selective_regime,
                "dual_model_history_union": _union(
                    old_agreement, selective_regime
                ),
                "v1_probability": round(v1_probability, 6),
                "regime_probability": round(regime_probability, 6),
            }
        )

    prediction_keys = (
        "history",
        "v1_model",
        "regime_model",
        "v1_history_agreement",
        "regime_history_agreement",
        "regime_history_conf60",
        "dual_model_history_union",
    )
    overall = {
        key: _metrics(events, key) for key in prediction_keys
    }
    windows = []
    for start, end in WINDOWS:
        selected = [
            row
            for row in events
            if start <= row["release_utc"][:10] < end
        ]
        windows.append(
            {
                "start": start,
                "end": end,
                "events": len(selected),
                "metrics": {
                    key: _metrics(selected, key)
                    for key in prediction_keys
                },
            }
        )

    report = {
        "methodology": {
            "test_type": (
                "Expanding one-event-at-a-time walk-forward. Every prediction "
                "uses only prior completed meetings."
            ),
            "research_warning": (
                "The architecture was selected after observing this historical "
                "archive, so frozen blocks and a future locked test remain the "
                "primary robustness checks."
            ),
            "source_audit": source_audit,
        },
        "overall": overall,
        "windows": windows,
        "events": events,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# FOMC Regime Walk-Forward",
        "",
        "Each prediction is generated before its meeting and models are refit "
        "only after that meeting is complete.",
        "",
        "| Policy | Calls | Correct | Accuracy | Coverage | 95% interval |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for key in prediction_keys:
        metrics = overall[key]
        lines.append(
            f"| {key} | {metrics['calls']} | {metrics['correct']} | "
            f"{metrics['accuracy_pct']:.2f}% | "
            f"{metrics['coverage_pct']:.2f}% | "
            f"{metrics['wilson_95_pct'][0]:.2f}-"
            f"{metrics['wilson_95_pct'][1]:.2f}% |"
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    report = run()
    print(json.dumps(report["overall"], indent=2))
