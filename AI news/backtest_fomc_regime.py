from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler

from fomc_pipeline import (
    FOMC_HISTORY_RULE,
    binary_gold_direction,
    fit_fomc_model,
    model_probability_positive,
)
from fomc_regime import FomcRegimeStore, regime_feature_names
from gold_direction_rules import rule_direction
from news_core import FEATURE_NAMES, ROOT, build_samples


WINDOWS = (
    ("2016-07-30", "2019-07-30"),
    ("2019-07-30", "2021-07-30"),
    ("2021-07-30", "2024-07-30"),
    ("2024-07-30", "2026-07-30"),
)
OUTPUT_JSON = ROOT / "fomc_regime_backtest.json"
OUTPUT_CSV = ROOT / "fomc_regime_backtest.csv"
OUTPUT_MD = ROOT / "FOMC_REGIME_BACKTEST.md"


def _extra_trees() -> ExtraTreesClassifier:
    return ExtraTreesClassifier(
        n_estimators=800,
        min_samples_leaf=7,
        max_features=0.65,
        class_weight="balanced",
        random_state=20260731,
        n_jobs=-1,
    )


def _logistic():
    return make_pipeline(
        RobustScaler(),
        LogisticRegression(
            C=0.35,
            class_weight="balanced",
            max_iter=4000,
            random_state=20260731,
        ),
    )


def _probability_positive(model, vector: list[float]) -> float:
    probabilities = model.predict_proba(
        np.asarray(vector, dtype=float).reshape(1, -1)
    )[0]
    return {
        str(label): float(probability)
        for label, probability in zip(model.classes_, probabilities)
    }["POSITIVE"]


def _prediction(probability: float) -> str:
    return "POSITIVE" if probability >= 0.5 else "NEGATIVE"


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


def _metrics(rows: list[dict], key: str) -> dict:
    selected = [
        row for row in rows if row.get(key) in {"POSITIVE", "NEGATIVE"}
    ]
    correct = sum(row[key] == row["actual"] for row in selected)
    return {
        "calls": len(selected),
        "correct": correct,
        "wrong": len(selected) - correct,
        "accuracy_pct": (
            round(100 * correct / len(selected), 2) if selected else 0.0
        ),
        "coverage_pct": (
            round(100 * len(selected) / len(rows), 2) if rows else 0.0
        ),
        "wilson_95_pct": _wilson(correct, len(selected)),
    }


def _fit(model, rows: list[dict], vector_key: str, target_key: str):
    selected = [
        row for row in rows if row.get(target_key) in {"POSITIVE", "NEGATIVE"}
    ]
    x = np.asarray([row[vector_key] for row in selected], dtype=float)
    y = np.asarray([row[target_key] for row in selected])
    return model.fit(x, y)


def _agreement(*predictions: str) -> str | None:
    return predictions[0] if len(set(predictions)) == 1 else None


def _majority(*predictions: str) -> str:
    positives = predictions.count("POSITIVE")
    return "POSITIVE" if positives >= math.ceil(len(predictions) / 2) else "NEGATIVE"


def _prepare_rows() -> tuple[list[dict], dict, FomcRegimeStore]:
    samples, source_audit = build_samples(30)
    store = FomcRegimeStore()
    rows = []
    for sample in samples:
        if sample["event"] != "FOMC":
            continue
        released = sample["release_utc"]
        market = list(sample["features"])
        regime = store.features(released)
        rows.append(
            {
                **sample,
                "actual": binary_gold_direction(
                    float(sample["reaction"]["release_move"])
                ),
                "policy_target": store.statement_gold_label(released),
                "market18": market[:18],
                "enhanced": [*market[:18], *regime],
                "policy_vector": regime,
            }
        )
    return rows, source_audit, store


def run() -> dict:
    rows, source_audit, store = _prepare_rows()
    events: list[dict] = []
    window_reports: list[dict] = []

    for start, end in WINDOWS:
        training = [row for row in rows if row["release_utc"][:10] < start]
        testing = [
            row for row in rows if start <= row["release_utc"][:10] < end
        ]
        history = [row["actual"] for row in training]
        v1_model = fit_fomc_model(training)
        direct_et = _fit(_extra_trees(), training, "enhanced", "actual")
        direct_lr = _fit(_logistic(), training, "enhanced", "actual")
        shock_et = _fit(
            _extra_trees(), training, "enhanced", "policy_target"
        )
        shock_lr = _fit(
            _logistic(), training, "enhanced", "policy_target"
        )
        window_rows = []

        for row in testing:
            history_prediction = rule_direction(FOMC_HISTORY_RULE, history)
            v1_probability = model_probability_positive(
                v1_model, row["features"]
            )
            direct_et_probability = _probability_positive(
                direct_et, row["enhanced"]
            )
            direct_lr_probability = _probability_positive(
                direct_lr, row["enhanced"]
            )
            shock_et_probability = _probability_positive(
                shock_et, row["enhanced"]
            )
            shock_lr_probability = _probability_positive(
                shock_lr, row["enhanced"]
            )
            predictions = {
                "history": history_prediction,
                "v1_model": _prediction(v1_probability),
                "direct_et": _prediction(direct_et_probability),
                "direct_lr": _prediction(direct_lr_probability),
                "shock_et": _prediction(shock_et_probability),
                "shock_lr": _prediction(shock_lr_probability),
            }
            event = {
                "window": f"{start}/{end}",
                "release_utc": row["release_utc"],
                "actual": row["actual"],
                "move_usd": round(
                    float(row["reaction"]["release_move"]), 4
                ),
                "actual_statement_gold_label": row["policy_target"],
                **predictions,
                "v1_history_agreement": _agreement(
                    predictions["v1_model"], predictions["history"]
                ),
                "direct_et_history_agreement": _agreement(
                    predictions["direct_et"], predictions["history"]
                ),
                "direct_lr_history_agreement": _agreement(
                    predictions["direct_lr"], predictions["history"]
                ),
                "direct_lr_history_conf55": (
                    _agreement(
                        predictions["direct_lr"],
                        predictions["history"],
                    )
                    if abs(direct_lr_probability - 0.5) >= 0.05
                    else None
                ),
                "direct_lr_history_conf60": (
                    _agreement(
                        predictions["direct_lr"],
                        predictions["history"],
                    )
                    if abs(direct_lr_probability - 0.5) >= 0.10
                    else None
                ),
                "direct_et_shock_et_agreement": _agreement(
                    predictions["direct_et"], predictions["shock_et"]
                ),
                "direct_lr_shock_lr_agreement": _agreement(
                    predictions["direct_lr"], predictions["shock_lr"]
                ),
                "triple_et_consensus": _agreement(
                    predictions["direct_et"],
                    predictions["shock_et"],
                    predictions["history"],
                ),
                "triple_lr_consensus": _agreement(
                    predictions["direct_lr"],
                    predictions["shock_lr"],
                    predictions["history"],
                ),
                "majority_et": _majority(
                    predictions["direct_et"],
                    predictions["shock_et"],
                    predictions["history"],
                ),
                "majority_lr": _majority(
                    predictions["direct_lr"],
                    predictions["shock_lr"],
                    predictions["history"],
                ),
                "direct_et_probability": round(direct_et_probability, 6),
                "direct_lr_probability": round(direct_lr_probability, 6),
                "shock_et_probability": round(shock_et_probability, 6),
                "shock_lr_probability": round(shock_lr_probability, 6),
                "v1_probability": round(v1_probability, 6),
            }
            events.append(event)
            window_rows.append(event)
            history.append(row["actual"])

        keys = [
            key
            for key in window_rows[0]
            if key
            not in {
                "window",
                "release_utc",
                "actual",
                "move_usd",
                "actual_statement_gold_label",
                "direct_et_probability",
                "direct_lr_probability",
                "shock_et_probability",
                "shock_lr_probability",
                "v1_probability",
            }
        ]
        window_reports.append(
            {
                "start": start,
                "end": end,
                "training_events": len(training),
                "test_events": len(testing),
                "metrics": {
                    key: _metrics(window_rows, key) for key in keys
                },
            }
        )

    prediction_keys = [
        key
        for key in events[0]
        if key
        not in {
            "window",
            "release_utc",
            "actual",
            "move_usd",
            "actual_statement_gold_label",
            "direct_et_probability",
            "direct_lr_probability",
            "shock_et_probability",
            "shock_lr_probability",
            "v1_probability",
        }
    ]
    overall = {key: _metrics(events, key) for key in prediction_keys}
    ranked = sorted(
        (
            {"name": name, **metrics}
            for name, metrics in overall.items()
            if metrics["coverage_pct"] >= 25
        ),
        key=lambda item: (
            item["accuracy_pct"],
            item["coverage_pct"],
            item["calls"],
        ),
        reverse=True,
    )

    statement_rows = [
        row
        for row in events
        if row["actual_statement_gold_label"] in {"POSITIVE", "NEGATIVE"}
    ]
    statement_correct = sum(
        row["actual_statement_gold_label"] == row["actual"]
        for row in statement_rows
    )
    report = {
        "methodology": {
            "test_type": "Frozen temporal blocks; every fitted model is frozen for the full test block.",
            "target": "Immediate XAUUSD release-minute close direction.",
            "policy_target": "SF Fed USMPD statement surprise sign, mapped hawkish to gold-negative.",
            "leakage_control": "Current-meeting USMPD values are outcomes only. Features use strictly earlier meetings and market/macro observations before release.",
            "feature_count": len(rows[0]["enhanced"]),
            "feature_names": [
                *FEATURE_NAMES[:18],
                *regime_feature_names(),
            ],
            "source_audit": source_audit,
        },
        "official_statement_mapping": {
            "events": len(statement_rows),
            "correct": statement_correct,
            "accuracy_pct": round(
                100 * statement_correct / len(statement_rows), 2
            ),
        },
        "windows": window_reports,
        "overall": overall,
        "ranking_min_25pct_coverage": ranked,
        "events": events,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(events[0]))
        writer.writeheader()
        writer.writerows(events)

    best = ranked[0]
    lines = [
        "# FOMC Regime Research",
        "",
        "Every machine-learning model is frozen before its future test block. "
        "The current meeting's official surprise is never an input.",
        "",
        "## Overall candidates",
        "",
        "| Candidate | Calls | Accuracy | Coverage | 95% interval |",
        "|---|---:|---:|---:|---:|",
    ]
    for item in ranked:
        lines.append(
            f"| {item['name']} | {item['calls']} | "
            f"{item['accuracy_pct']:.2f}% | "
            f"{item['coverage_pct']:.2f}% | "
            f"{item['wilson_95_pct'][0]:.2f}-"
            f"{item['wilson_95_pct'][1]:.2f}% |"
        )
    lines.extend(
        (
            "",
            "## Best candidate",
            "",
            f"**{best['name']}**: {best['correct']}/{best['calls']} "
            f"correct ({best['accuracy_pct']:.2f}%), "
            f"{best['coverage_pct']:.2f}% coverage.",
            "",
            "The official statement surprise itself is an ex-post diagnostic, "
            f"not a tradable input: {statement_correct}/{len(statement_rows)} "
            f"({report['official_statement_mapping']['accuracy_pct']:.2f}%) "
            "matched the immediate gold direction.",
        )
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    result = run()
    print(json.dumps(result["ranking_min_25pct_coverage"], indent=2))
