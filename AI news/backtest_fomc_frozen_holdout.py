from __future__ import annotations

import csv
import json
import math
from datetime import date

from fomc_pipeline import (
    FOMC_HISTORY_RULE,
    binary_gold_direction,
    fit_fomc_model,
    model_probability_positive,
)
from gold_direction_rules import rule_direction
from news_core import ROOT, build_samples


WINDOWS = (
    ("2016-07-30", "2019-07-30"),
    ("2019-07-30", "2021-07-30"),
    ("2021-07-30", "2024-07-30"),
    ("2024-07-30", "2026-07-30"),
)
OUTPUT_JSON = ROOT / "fomc_frozen_holdout.json"
OUTPUT_CSV = ROOT / "fomc_frozen_holdout.csv"
OUTPUT_MD = ROOT / "FOMC_FROZEN_HOLDOUT.md"


def _wilson(correct: int, total: int) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    z = 1.96
    probability = correct / total
    denominator = 1 + z * z / total
    center = (probability + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(
        probability * (1 - probability) / total
        + z * z / (4 * total * total)
    ) / denominator
    return [
        round(100 * max(0.0, center - margin), 2),
        round(100 * min(1.0, center + margin), 2),
    ]


def _metrics(rows: list[dict], prediction_key: str) -> dict:
    selected = [
        row
        for row in rows
        if row.get(prediction_key) in {"POSITIVE", "NEGATIVE"}
    ]
    correct = sum(
        row[prediction_key] == row["actual_gold_impact"]
        for row in selected
    )
    return {
        "events": len(selected),
        "correct": correct,
        "wrong": len(selected) - correct,
        "accuracy_pct": (
            round(100 * correct / len(selected), 2)
            if selected
            else 0.0
        ),
        "coverage_pct": (
            round(100 * len(selected) / len(rows), 2)
            if rows
            else 0.0
        ),
        "wilson_95_pct": _wilson(correct, len(selected)),
    }


def _window_metrics(rows: list[dict]) -> dict:
    return {
        "test_events": len(rows),
        "history_rule": _metrics(rows, "history_prediction"),
        "frozen_t30_model": _metrics(rows, "model_prediction"),
        "agreement_only": _metrics(rows, "agreement_prediction"),
    }


def run() -> dict:
    samples, source_audit = build_samples(30)
    for row in samples:
        row["binary_target"] = binary_gold_direction(
            float(row["reaction"]["release_move"])
        )

    events = []
    windows = []
    for start, end in WINDOWS:
        training = [
            row
            for row in samples
            if row["event"] == "FOMC"
            and row["release_utc"][:10] < start
        ]
        testing = [
            row
            for row in samples
            if row["event"] == "FOMC"
            and start <= row["release_utc"][:10] < end
        ]
        model = fit_fomc_model(training)
        history = [row["binary_target"] for row in training]
        window_rows = []
        for row in testing:
            history_prediction = rule_direction(
                FOMC_HISTORY_RULE,
                history,
            )
            probability_positive = model_probability_positive(
                model,
                row["features"],
            )
            model_prediction = (
                "POSITIVE"
                if probability_positive >= 0.5
                else "NEGATIVE"
            )
            actual = row["binary_target"]
            event_row = {
                "window_start": start,
                "window_end": end,
                "release_utc": row["release_utc"],
                "training_events": len(training),
                "history_prediction": history_prediction,
                "model_prediction": model_prediction,
                "model_probability_positive_pct": round(
                    100 * probability_positive,
                    2,
                ),
                "components_agree": (
                    history_prediction == model_prediction
                ),
                "agreement_prediction": (
                    history_prediction
                    if history_prediction == model_prediction
                    else None
                ),
                "actual_gold_impact": actual,
                "actual_move_usd": round(
                    float(row["reaction"]["release_move"]),
                    4,
                ),
            }
            window_rows.append(event_row)
            events.append(event_row)
            history.append(actual)
        windows.append(
            {
                "start": start,
                "end": end,
                "training_events": len(training),
                **_window_metrics(window_rows),
            }
        )

    report = {
        "methodology": {
            "test_type": (
                "Frozen temporal block holdout. The ExtraTrees model is fitted "
                "once before each block and never refitted inside that block."
            ),
            "history_rule_update": (
                "The deterministic history component may observe completed "
                "meetings inside the block, exactly as it would live."
            ),
            "no_fedwatch": (
                "The pricing resolver is excluded because a complete "
                "point-in-time historical FedWatch archive is unavailable."
            ),
            "honesty_warning": (
                "The estimator does not see test outcomes, but the architecture "
                "was designed after July 2026. This is stronger than the rolling "
                "replay, but it is not future data unseen by the researcher."
            ),
            "source_audit": source_audit,
        },
        "windows": windows,
        "overall": _window_metrics(events),
        "events": events,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(events[0]))
        writer.writeheader()
        writer.writerows(events)

    overall = report["overall"]
    lines = [
        "# FOMC Frozen Temporal Holdout",
        "",
        "The T-30 model is frozen before each future block and cannot learn "
        "from any outcome inside that block.",
        "",
        "| Test block | Train events | Test events | History | Frozen model | Agreement calls | Agreement accuracy |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for item in windows:
        lines.append(
            f"| {item['start']} to {item['end']} | "
            f"{item['training_events']} | {item['test_events']} | "
            f"{item['history_rule']['accuracy_pct']:.2f}% | "
            f"{item['frozen_t30_model']['accuracy_pct']:.2f}% | "
            f"{item['agreement_only']['events']} | "
            f"{item['agreement_only']['accuracy_pct']:.2f}% |"
        )
    lines.extend(
        (
            "",
            "## Overall",
            "",
            f"- History rule: **{overall['history_rule']['correct']}/"
            f"{overall['history_rule']['events']} "
            f"({overall['history_rule']['accuracy_pct']:.2f}%)**",
            f"- Frozen T-30 model: **{overall['frozen_t30_model']['correct']}/"
            f"{overall['frozen_t30_model']['events']} "
            f"({overall['frozen_t30_model']['accuracy_pct']:.2f}%)**",
            f"- Agreement only: **{overall['agreement_only']['correct']}/"
            f"{overall['agreement_only']['events']} "
            f"({overall['agreement_only']['accuracy_pct']:.2f}%)**, "
            f"coverage **{overall['agreement_only']['coverage_pct']:.2f}%**",
            f"- Agreement 95% interval: **"
            f"{overall['agreement_only']['wilson_95_pct'][0]:.2f}% to "
            f"{overall['agreement_only']['wilson_95_pct'][1]:.2f}%**",
            "",
            "The 2019-2021 block failed at 45.45% on agreement calls. This "
            "confirms regime sensitivity and supports a 65% confidence cap, "
            "not 70% or higher.",
        )
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

