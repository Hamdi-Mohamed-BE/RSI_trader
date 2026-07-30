from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, balanced_accuracy_score, brier_score_loss, log_loss
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from macro_regime import MacroRegimeStore, feature_names as macro_feature_names
from news_core import (
    EVENTS,
    FEATURE_NAMES,
    ROOT,
    build_samples,
    event_history_features,
)


BROAD_START = date(2024, 7, 30)
RECENT_START = date(2026, 5, 30)
SELECTION_START = date(2019, 7, 30)
OUTPUT_JSON = ROOT / "gold_direction_backtest.json"
OUTPUT_CSV = ROOT / "gold_direction_recent.csv"
OUTPUT_MD = ROOT / "GOLD_DIRECTION_RESULTS.md"
MODEL_PATH = ROOT / "models" / "gold_news_direction.joblib"


@dataclass(frozen=True)
class Candidate:
    name: str
    profile: str
    model: object


def _date(row: dict) -> date:
    return date.fromisoformat(row["release_utc"][:10])


def _direction(row: dict) -> str:
    return "POSITIVE" if row["reaction"]["release_move"] >= 0 else "NEGATIVE"


def paired_rows(store: MacroRegimeStore) -> list[dict]:
    rows_15, _ = build_samples(15)
    rows_30, _ = build_samples(30)
    by_15 = {row["release_utc"]: row for row in rows_15}
    by_30 = {row["release_utc"]: row for row in rows_30}
    output = []
    for release in sorted(set(by_15) & set(by_30)):
        row_15 = by_15[release]
        row_30 = by_30[release]
        features_15 = np.asarray(row_15["features"], dtype=float)
        features_30 = np.asarray(row_30["features"], dtype=float)
        output.append(
            {
                "release_utc": release,
                "event": row_15["event"],
                "target": _direction(row_15),
                "impulse_target": row_15["target"],
                "move_usd": float(row_15["reaction"]["release_move"]),
                "features_15": features_15,
                "features_30": features_30,
                "features_dual": np.concatenate(
                    (features_15, features_30, features_15 - features_30)
                ),
                "features_macro": np.asarray(store.features(release), dtype=float),
            }
        )
    return output


def profile_vector(row: dict, profile: str) -> np.ndarray:
    if profile == "t15":
        return row["features_15"]
    if profile == "t30":
        return row["features_30"]
    if profile == "dual":
        return row["features_dual"]
    if profile == "t30_macro":
        return np.concatenate((row["features_30"], row["features_macro"]))
    if profile == "dual_macro":
        return np.concatenate((row["features_dual"], row["features_macro"]))
    raise ValueError(f"Unknown feature profile: {profile}")


def candidates(final: bool) -> list[Candidate]:
    profiles = ("t15", "dual", "dual_macro") if final else ("t30", "t30_macro")
    output = []
    for profile in profiles:
        output.extend(
            (
                Candidate(
                    "logistic",
                    profile,
                    Pipeline(
                        (
                            ("scale", StandardScaler()),
                            (
                                "model",
                                LogisticRegression(
                                    C=0.2,
                                    class_weight="balanced",
                                    max_iter=4_000,
                                    random_state=42,
                                ),
                            ),
                        )
                    ),
                ),
                Candidate(
                    "extra_trees",
                    profile,
                    ExtraTreesClassifier(
                        n_estimators=500,
                        min_samples_leaf=6,
                        max_features=0.5,
                        class_weight="balanced",
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
                Candidate(
                    "hist_gradient_boosting",
                    profile,
                    HistGradientBoostingClassifier(
                        max_iter=220,
                        max_leaf_nodes=7,
                        learning_rate=0.04,
                        l2_regularization=4.0,
                        random_state=42,
                    ),
                ),
            )
        )
    return output


def _positive_probability(model: object, values: np.ndarray) -> np.ndarray:
    classes = list(model.classes_)
    return model.predict_proba(values)[:, classes.index("POSITIVE")]


def _metrics(targets: list[str], probabilities: list[float]) -> dict:
    y = np.asarray(targets)
    p = np.asarray(probabilities, dtype=float)
    predicted = np.where(p >= 0.5, "POSITIVE", "NEGATIVE")
    encoded = (y == "POSITIVE").astype(int)
    correct = predicted == y
    return {
        "events": len(y),
        "correct": int(np.sum(correct)),
        "wrong": int(np.sum(~correct)),
        "accuracy_pct": round(100 * accuracy_score(y, predicted), 2),
        "balanced_accuracy_pct": round(100 * balanced_accuracy_score(y, predicted), 2),
        "brier": round(float(brier_score_loss(encoded, p)), 5),
        "log_loss": round(float(log_loss(encoded, np.column_stack((1 - p, p)))), 5),
    }


def oof(candidate: Candidate, rows: list[dict]) -> tuple[list[dict], dict]:
    x = np.asarray([profile_vector(row, candidate.profile) for row in rows])
    y = np.asarray([row["target"] for row in rows])
    output: list[dict] = []
    split = TimeSeriesSplit(n_splits=6)
    for train_indices, validation_indices in split.split(x):
        model = clone(candidate.model).fit(x[train_indices], y[train_indices])
        probabilities = _positive_probability(model, x[validation_indices])
        for index, probability in zip(validation_indices, probabilities):
            if _date(rows[index]) < SELECTION_START:
                continue
            output.append(
                {
                    "release_utc": rows[index]["release_utc"],
                    "event": rows[index]["event"],
                    "target": rows[index]["target"],
                    "probability_positive": float(probability),
                }
            )
    metrics = _metrics(
        [row["target"] for row in output],
        [row["probability_positive"] for row in output],
    )
    return output, metrics


def _selection_key(metrics: dict) -> tuple[float, float, float, float]:
    return (
        metrics["accuracy_pct"],
        metrics["balanced_accuracy_pct"],
        -metrics["log_loss"],
        -metrics["brier"],
    )


def prior_probability(history: list[dict], event: str) -> float:
    labels = [row["target"] for row in history if row["event"] == event]
    positives = sum(label == "POSITIVE" for label in labels)
    # A small symmetric prior prevents an early event streak from becoming
    # unjustifiably certain.
    return float((positives + 2) / (len(labels) + 4))


def select_blend(
    oof_rows: list[dict],
    development: list[dict],
) -> tuple[float, list[dict], list[dict]]:
    source_by_release = {row["release_utc"]: row for row in development}
    comparisons = []
    best: tuple[tuple[float, ...], float, list[dict]] | None = None
    for weight in (0.0, 0.25, 0.5, 0.75, 1.0):
        blended = blend_oof(oof_rows, development, weight, source_by_release)
        metrics = _metrics(
            [row["target"] for row in blended],
            [row["probability_positive"] for row in blended],
        )
        comparisons.append({"model_weight": weight, **metrics})
        # Prefer the simpler historical anchor when accuracy is tied.
        key = (*_selection_key(metrics), -weight)
        item = (key, weight, blended)
        if best is None or item[0] > best[0]:
            best = item
    if best is None:
        raise RuntimeError("No historical/model blend was evaluated.")
    return best[1], best[2], comparisons


def blend_oof(
    oof_rows: list[dict],
    development: list[dict],
    weight: float,
    source_by_release: dict[str, dict] | None = None,
) -> list[dict]:
    sources = source_by_release or {
        row["release_utc"]: row for row in development
    }
    blended = []
    for row in oof_rows:
        source = sources[row["release_utc"]]
        history = [
            item for item in development if _date(item) < _date(source)
        ]
        prior = prior_probability(history, source["event"])
        probability = weight * row["probability_positive"] + (1 - weight) * prior
        blended.append({**row, "probability_positive": probability})
    return blended


def select_candidate(rows: list[dict], final: bool) -> tuple[Candidate, list[dict], list[dict]]:
    comparisons = []
    best: tuple[tuple[float, ...], Candidate, list[dict]] | None = None
    for candidate in candidates(final):
        predictions, metrics = oof(candidate, rows)
        record = {"model": candidate.name, "profile": candidate.profile, **metrics}
        comparisons.append(record)
        item = (_selection_key(metrics), candidate, predictions)
        if best is None or item[0] > best[0]:
            best = item
    if best is None:
        raise RuntimeError("No direction model candidate was evaluated.")
    return best[1], best[2], comparisons


def fit_confidence_calibrator(oof_rows: list[dict]) -> IsotonicRegression:
    raw_confidence = []
    correct = []
    for row in oof_rows:
        probability = row["probability_positive"]
        prediction = "POSITIVE" if probability >= 0.5 else "NEGATIVE"
        raw_confidence.append(max(probability, 1 - probability))
        correct.append(float(prediction == row["target"]))
    return IsotonicRegression(
        y_min=0.0,
        y_max=1.0,
        increasing=True,
        out_of_bounds="clip",
    ).fit(raw_confidence, correct)


def fit(candidate: Candidate, rows: list[dict]) -> object:
    x = np.asarray([profile_vector(row, candidate.profile) for row in rows])
    y = np.asarray([row["target"] for row in rows])
    return clone(candidate.model).fit(x, y)


def predict(
    model: object,
    candidate: Candidate,
    calibrator: IsotonicRegression,
    model_weight: float,
    prior_history: list[dict],
    rows: list[dict],
) -> list[dict]:
    if not rows:
        return []
    x = np.asarray([profile_vector(row, candidate.profile) for row in rows])
    probabilities = _positive_probability(model, x)
    output = []
    history = list(prior_history)
    for row, model_probability in zip(rows, probabilities):
        prior = prior_probability(history, row["event"])
        probability = model_weight * model_probability + (1 - model_weight) * prior
        direction = "POSITIVE" if probability >= 0.5 else "NEGATIVE"
        raw_confidence = max(probability, 1 - probability)
        calibrated_confidence = float(calibrator.predict([raw_confidence])[0])
        output.append(
            {
                "release_utc": row["release_utc"],
                "event": row["event"],
                "predicted_gold_impact": direction,
                "confidence_pct": round(100 * calibrated_confidence, 2),
                "raw_probability_positive_pct": round(100 * probability, 2),
                "historical_probability_positive_pct": round(100 * prior, 2),
                "market_model_probability_positive_pct": round(
                    100 * model_probability,
                    2,
                ),
                "actual_gold_impact": row["target"],
                "actual_move_usd": round(row["move_usd"], 3),
                "actual_move_pips": round(100 * row["move_usd"], 1),
                "correct": direction == row["target"],
            }
        )
        history.append(row)
    return output


def metrics_from_predictions(rows: list[dict]) -> dict:
    return _metrics(
        [row["actual_gold_impact"] for row in rows],
        [row["raw_probability_positive_pct"] / 100 for row in rows],
    )


def event_breakdown(rows: list[dict]) -> dict[str, dict]:
    output = {}
    for event in EVENTS:
        selected = [row for row in rows if row["event"] == event]
        if selected:
            output[event] = {
                "events": len(selected),
                "correct": sum(row["correct"] for row in selected),
                "accuracy_pct": round(
                    100 * sum(row["correct"] for row in selected) / len(selected),
                    2,
                ),
            }
    return output


def majority_baseline(training: list[dict], test: list[dict]) -> dict:
    mapping = {}
    for event in EVENTS:
        labels = [row["target"] for row in training if row["event"] == event]
        mapping[event] = max(set(labels), key=labels.count)
    predicted = [mapping[row["event"]] for row in test]
    actual = [row["target"] for row in test]
    return {
        "mapping": mapping,
        "events": len(test),
        "correct": sum(left == right for left, right in zip(predicted, actual)),
        "accuracy_pct": round(100 * accuracy_score(actual, predicted), 2),
    }


def momentum_baseline(test: list[dict]) -> dict:
    predicted = [
        "POSITIVE" if row["features_15"][1] >= 0 else "NEGATIVE"
        for row in test
    ]
    actual = [row["target"] for row in test]
    return {
        "events": len(test),
        "correct": sum(left == right for left, right in zip(predicted, actual)),
        "accuracy_pct": round(100 * accuracy_score(actual, predicted), 2),
    }


def _feature_names(profile: str) -> list[str]:
    base = list(FEATURE_NAMES)
    macro = list(macro_feature_names())
    if profile == "t15" or profile == "t30":
        return base
    if profile == "dual":
        return [*(f"t15_{name}" for name in base), *(f"t30_{name}" for name in base), *(f"delta_{name}" for name in base)]
    if profile == "t30_macro":
        return [*(f"t30_{name}" for name in base), *macro]
    if profile == "dual_macro":
        return [*_feature_names("dual"), *macro]
    raise ValueError(profile)


def _wilson(correct: int, total: int) -> list[float]:
    if total == 0:
        return [0.0, 0.0]
    z = 1.96
    p = correct / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [round(100 * (center - margin), 2), round(100 * (center + margin), 2)]


def run(refresh_macro: bool = False) -> dict:
    store = MacroRegimeStore(refresh=refresh_macro)
    rows = paired_rows(store)
    development = [row for row in rows if _date(row) < BROAD_START]
    broad = [row for row in rows if BROAD_START <= _date(row) < RECENT_START]
    before_recent = [row for row in rows if _date(row) < RECENT_START]
    recent = [row for row in rows if _date(row) >= RECENT_START]

    early_candidate, early_oof, early_comparisons = select_candidate(development, final=False)
    final_candidate, final_oof, final_comparisons = select_candidate(development, final=True)
    early_weight, early_blended_oof, early_blends = select_blend(
        early_oof,
        development,
    )
    final_weight, final_blended_oof, final_blends = select_blend(
        final_oof,
        development,
    )
    early_calibrator = fit_confidence_calibrator(early_blended_oof)
    final_calibrator = fit_confidence_calibrator(final_blended_oof)

    broad_model = fit(final_candidate, development)
    broad_predictions = predict(
        broad_model,
        final_candidate,
        final_calibrator,
        final_weight,
        development,
        broad,
    )
    recent_model = fit(final_candidate, before_recent)
    recent_predictions = predict(
        recent_model,
        final_candidate,
        final_calibrator,
        final_weight,
        before_recent,
        recent,
    )
    early_broad_model = fit(early_candidate, development)
    early_broad_predictions = predict(
        early_broad_model,
        early_candidate,
        early_calibrator,
        early_weight,
        development,
        broad,
    )
    broad_metrics = metrics_from_predictions(broad_predictions)
    recent_metrics = metrics_from_predictions(recent_predictions)
    early_broad_metrics = metrics_from_predictions(early_broad_predictions)
    broad_prior = majority_baseline(development, broad)
    early_deployment_guard = "pre-holdout selection retained"
    if early_broad_metrics["accuracy_pct"] <= broad_prior["accuracy_pct"]:
        early_weight = 0.0
        early_blended_oof = blend_oof(early_oof, development, early_weight)
        early_calibrator = fit_confidence_calibrator(early_blended_oof)
        early_broad_predictions = predict(
            early_broad_model,
            early_candidate,
            early_calibrator,
            early_weight,
            development,
            broad,
        )
        early_broad_metrics = metrics_from_predictions(early_broad_predictions)
        early_deployment_guard = (
            "market model rejected after the broad holdout failed to beat "
            "the event-history baseline; recent holdout remained untouched"
        )
    early_recent_model = fit(early_candidate, before_recent)
    early_recent_predictions = predict(
        early_recent_model,
        early_candidate,
        early_calibrator,
        early_weight,
        before_recent,
        recent,
    )
    early_recent_metrics = metrics_from_predictions(early_recent_predictions)
    broad_metrics["wilson_95_pct"] = _wilson(broad_metrics["correct"], broad_metrics["events"])
    recent_metrics["wilson_95_pct"] = _wilson(recent_metrics["correct"], recent_metrics["events"])

    production_early = fit(early_candidate, rows)
    production_final = fit(final_candidate, rows)
    artifact = {
        "artifact_version": 1,
        "prediction_only": True,
        "execution_capability": False,
        "target": "Immediate release-minute gold impact: POSITIVE or NEGATIVE.",
        "event_prior_probability_positive": {
            event: prior_probability(rows, event) for event in EVENTS
        },
        "history_features": {
            event: event_history_features(
                event,
                {
                    name: [
                        row["impulse_target"]
                        for row in rows
                        if row["event"] == name
                    ]
                    for name in EVENTS
                },
                [row["impulse_target"] for row in rows],
            )
            for event in EVENTS
        },
        "expected_release_range_by_event": {
            event: {
                "median_usd": round(
                    float(
                        np.median(
                            [
                                abs(row["move_usd"])
                                for row in rows
                                if row["event"] == event
                            ]
                        )
                    ),
                    3,
                ),
                "samples": sum(row["event"] == event for row in rows),
            }
            for event in EVENTS
        },
        "early": {
            "candidate": {"name": early_candidate.name, "profile": early_candidate.profile},
            "model_weight": early_weight,
            "model": production_early,
            "confidence_calibrator": early_calibrator,
            "feature_names": _feature_names(early_candidate.profile),
        },
        "final": {
            "candidate": {"name": final_candidate.name, "profile": final_candidate.profile},
            "model_weight": final_weight,
            "model": production_final,
            "confidence_calibrator": final_calibrator,
            "feature_names": _feature_names(final_candidate.profile),
        },
        "trained_through": rows[-1]["release_utc"],
    }
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)

    report = {
        "scope": {
            "target": "Binary immediate XAUUSD effect; every release is POSITIVE or NEGATIVE.",
            "no_trade_outputs": False,
            "trade_execution": False,
            "selection_rule": (
                "Model and features selected only with expanding chronological validation "
                f"from {SELECTION_START.isoformat()} through {BROAD_START.isoformat()} exclusive."
            ),
            "deployment_guard": (
                "The broad holdout may reject a complex model in favor of the historical "
                "anchor. The recent holdout is never used for that decision."
            ),
            "broad_holdout": (
                f"{BROAD_START.isoformat()} through {RECENT_START.isoformat()} exclusive"
            ),
            "recent_holdout": f"{RECENT_START.isoformat()} onward",
        },
        "selected": {
            "early_30m": {
                "model": early_candidate.name,
                "profile": early_candidate.profile,
                "market_model_weight": early_weight,
                "historical_event_weight": 1 - early_weight,
            },
            "final_15m": {
                "model": final_candidate.name,
                "profile": final_candidate.profile,
                "market_model_weight": final_weight,
                "historical_event_weight": 1 - final_weight,
            },
        },
        "candidate_validation": {
            "early_30m": early_comparisons,
            "final_15m": final_comparisons,
            "early_30m_blends": early_blends,
            "final_15m_blends": final_blends,
        },
        "broad_holdout": {
            **broad_metrics,
            "by_event": event_breakdown(broad_predictions),
            "event_majority_baseline": majority_baseline(development, broad),
            "momentum_baseline": momentum_baseline(broad),
        },
        "recent_holdout": {
            **recent_metrics,
            "by_event": event_breakdown(recent_predictions),
            "event_majority_baseline": majority_baseline(before_recent, recent),
            "momentum_baseline": momentum_baseline(recent),
        },
        "early_30m_holdout": {
            "deployment_guard": early_deployment_guard,
            "broad": early_broad_metrics,
            "recent": early_recent_metrics,
        },
        "recent_events": recent_predictions,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(recent_predictions[0]))
        writer.writeheader()
        writer.writerows(recent_predictions)

    broad_summary = report["broad_holdout"]
    recent_summary = report["recent_holdout"]
    lines = [
        "# Gold Direction Prediction Results",
        "",
        "The system predicts information only: **POSITIVE for gold** or "
        "**NEGATIVE for gold**. It does not issue trade calls.",
        "",
        "## Selected configuration",
        "",
        f"- T-30 early view: `{100 * (1 - early_weight):.0f}%` event history and "
        f"`{100 * early_weight:.0f}%` `{early_candidate.name}` / `{early_candidate.profile}`.",
        f"- T-15 final view: `{100 * (1 - final_weight):.0f}%` event history and "
        f"`{100 * final_weight:.0f}%` `{final_candidate.name}` / `{final_candidate.profile}`.",
        "",
        "## Frozen results",
        "",
        "| Window | Events | Correct | Accuracy | 95% interval | Majority baseline | Momentum baseline |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Broad holdout | {broad_summary['events']} | {broad_summary['correct']} | "
        f"{broad_summary['accuracy_pct']:.2f}% | "
        f"{broad_summary['wilson_95_pct'][0]:.2f}-{broad_summary['wilson_95_pct'][1]:.2f}% | "
        f"{broad_summary['event_majority_baseline']['accuracy_pct']:.2f}% | "
        f"{broad_summary['momentum_baseline']['accuracy_pct']:.2f}% |",
        f"| Recent holdout | {recent_summary['events']} | {recent_summary['correct']} | "
        f"{recent_summary['accuracy_pct']:.2f}% | "
        f"{recent_summary['wilson_95_pct'][0]:.2f}-{recent_summary['wilson_95_pct'][1]:.2f}% | "
        f"{recent_summary['event_majority_baseline']['accuracy_pct']:.2f}% | "
        f"{recent_summary['momentum_baseline']['accuracy_pct']:.2f}% |",
        "",
        "## Recent releases",
        "",
        "| Date | Event | Forecast | Confidence | Actual | Gold move | Correct |",
        "|---|---|---|---:|---|---:|---|",
    ]
    for row in recent_predictions:
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | "
            f"{row['predicted_gold_impact']} | {row['confidence_pct']:.1f}% | "
            f"{row['actual_gold_impact']} | {row['actual_move_usd']:+.3f} | "
            f"{'YES' if row['correct'] else 'NO'} |"
        )
    lines.extend(
        (
            "",
            "Confidence is calibrated from chronological out-of-fold correctness. "
            "It is uncertainty information, not a trade instruction.",
        )
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
