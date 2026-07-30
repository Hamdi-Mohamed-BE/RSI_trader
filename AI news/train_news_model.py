from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from statistics import mean

import joblib
import numpy as np
from sklearn.base import clone
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder, StandardScaler

from news_core import (
    EVENTS,
    FEATURE_NAMES,
    LABELS,
    LEADS,
    ROOT,
    build_samples,
    history_snapshot,
)


MODEL_DIR = ROOT / "models"
REPORT_PATH = ROOT / "backtest_report.json"
DETAIL_PATH = ROOT / "backtest_validation_predictions.csv"
TEST_START = date(2024, 7, 30)
THRESHOLDS = (0.45, 0.50, 0.55, 0.60, 0.65)
LEGACY_FEATURE_COUNT = 18
DEPLOYMENT_PROFILE = {15: "enhanced", 30: "legacy"}


def candidates() -> dict[str, object]:
    return {
        "logistic": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=0.08,
                        class_weight="balanced",
                        max_iter=3_000,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=500,
            min_samples_leaf=8,
            max_features=0.75,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "extra_trees_regularized": ExtraTreesClassifier(
            n_estimators=900,
            min_samples_leaf=12,
            max_depth=9,
            max_features=0.55,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=700,
            min_samples_leaf=10,
            max_depth=8,
            max_features=0.55,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=150,
            learning_rate=0.035,
            max_depth=2,
            min_samples_leaf=12,
            subsample=0.8,
            random_state=42,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            learning_rate=0.04,
            max_iter=180,
            max_leaf_nodes=11,
            min_samples_leaf=18,
            l2_regularization=1.5,
            random_state=42,
        ),
    }


def apply_threshold(probabilities: np.ndarray, classes: list[str], threshold: float) -> np.ndarray:
    class_index = {name: index for index, name in enumerate(classes)}
    outputs = []
    for row in probabilities:
        buy = row[class_index["BUY"]]
        sell = row[class_index["SELL"]]
        uncertain = row[class_index["UNCERTAIN"]] if "UNCERTAIN" in class_index else 0.0
        directional = "BUY" if buy >= sell else "SELL"
        directional_probability = max(buy, sell)
        outputs.append(
            directional
            if directional_probability >= threshold and directional_probability > uncertain
            else "UNCERTAIN"
        )
    return np.asarray(outputs)


def multiclass_brier(y_true: np.ndarray, probabilities: np.ndarray, classes: list[str]) -> float:
    encoded = np.zeros_like(probabilities)
    mapping = {label: index for index, label in enumerate(classes)}
    for row, label in enumerate(y_true):
        encoded[row, mapping[label]] = 1.0
    return float(np.mean(np.sum((probabilities - encoded) ** 2, axis=1)))


def metrics(y_true: np.ndarray, predicted: np.ndarray, probabilities: np.ndarray, classes: list[str]) -> dict:
    called = predicted != "UNCERTAIN"
    clear_actual = y_true != "UNCERTAIN"
    directional_mask = called & clear_actual
    coverage = float(np.mean(called)) if len(called) else 0.0
    directional_accuracy = (
        float(np.mean(predicted[directional_mask] == y_true[directional_mask]))
        if directional_mask.any()
        else 0.0
    )
    return {
        "samples": int(len(y_true)),
        "overall_accuracy_pct": round(100 * accuracy_score(y_true, predicted), 2),
        "directional_call_accuracy_pct": round(100 * directional_accuracy, 2),
        "coverage_pct": round(100 * coverage, 2),
        "called_predictions": int(called.sum()),
        "macro_precision": round(
            precision_score(y_true, predicted, labels=list(LABELS), average="macro", zero_division=0),
            4,
        ),
        "macro_recall": round(
            recall_score(y_true, predicted, labels=list(LABELS), average="macro", zero_division=0),
            4,
        ),
        "macro_f1": round(
            f1_score(y_true, predicted, labels=list(LABELS), average="macro", zero_division=0),
            4,
        ),
        "brier_multiclass": round(multiclass_brier(y_true, probabilities, classes), 5),
        "confusion_labels": list(LABELS),
        "confusion_matrix": confusion_matrix(y_true, predicted, labels=list(LABELS)).tolist(),
    }


def cross_validate(rows: list[dict], model: object, feature_indices: list[int]) -> dict:
    x = np.asarray(
        [[row["features"][index] for index in feature_indices] for row in rows],
        dtype=float,
    )
    y = np.asarray([row["target"] for row in rows])
    splitter = TimeSeriesSplit(n_splits=5)
    out_of_fold: list[tuple[int, str, dict[str, float]]] = []
    for fit_indices, validation_indices in splitter.split(x):
        fitted = clone(model)
        fitted.fit(x[fit_indices], y[fit_indices])
        probabilities = fitted.predict_proba(x[validation_indices])
        classes = list(fitted.classes_)
        for sample_index, row_probabilities in zip(validation_indices, probabilities):
            out_of_fold.append(
                (
                    int(sample_index),
                    y[sample_index],
                    {label: float(value) for label, value in zip(classes, row_probabilities)},
                )
            )
    out_of_fold.sort(key=lambda item: item[0])
    y_true = np.asarray([item[1] for item in out_of_fold])
    classes = list(LABELS)
    probabilities = np.asarray(
        [[item[2].get(label, 0.0) for label in classes] for item in out_of_fold],
        dtype=float,
    )
    threshold_results = []
    for threshold in THRESHOLDS:
        predicted = apply_threshold(probabilities, classes, threshold)
        result = metrics(y_true, predicted, probabilities, classes)
        result["threshold"] = threshold
        edge = max(0.0, result["directional_call_accuracy_pct"] / 100 - 0.5)
        result["selection_score"] = round(edge * np.sqrt(result["coverage_pct"] / 100), 6)
        threshold_results.append(result)
    eligible = [row for row in threshold_results if row["coverage_pct"] >= 15]
    selected = max(
        eligible or threshold_results,
        key=lambda row: (row["selection_score"], -row["brier_multiclass"], row["coverage_pct"]),
    )
    return {
        "selected_threshold": selected["threshold"],
        "selected_metrics": selected,
        "thresholds": threshold_results,
    }


def baseline_metrics(train: list[dict], test: list[dict]) -> dict:
    event_majority = {}
    for event in EVENTS:
        labels = [row["target"] for row in train if row["event"] == event]
        event_majority[event] = max(LABELS, key=labels.count) if labels else "UNCERTAIN"
    actual = np.asarray([row["target"] for row in test])
    majority_predictions = np.asarray([event_majority[row["event"]] for row in test])
    momentum_predictions = np.asarray(
        [
            "BUY" if row["features"][1] > 0.15 else "SELL" if row["features"][1] < -0.15 else "UNCERTAIN"
            for row in test
        ]
    )
    return {
        "event_majority": {
            "mapping": event_majority,
            "accuracy_pct": round(100 * accuracy_score(actual, majority_predictions), 2),
            "macro_f1": round(f1_score(actual, majority_predictions, labels=list(LABELS), average="macro", zero_division=0), 4),
        },
        "pre_news_momentum": {
            "accuracy_pct": round(100 * accuracy_score(actual, momentum_predictions), 2),
            "macro_f1": round(f1_score(actual, momentum_predictions, labels=list(LABELS), average="macro", zero_division=0), 4),
        },
    }


def validation_breakdowns(
    test: list[dict],
    predicted: np.ndarray,
    probabilities: np.ndarray,
    classes: list[str],
) -> tuple[dict, list[dict]]:
    actual = np.asarray([row["target"] for row in test])
    confidence = np.max(probabilities, axis=1)
    by_event = {}
    for event in EVENTS:
        mask = np.asarray([row["event"] == event for row in test])
        called = mask & (predicted != "UNCERTAIN")
        by_event[event] = {
            "samples": int(mask.sum()),
            "calls": int(called.sum()),
            "coverage_pct": round(100 * float(called.sum()) / max(int(mask.sum()), 1), 2),
            "directional_accuracy_pct": (
                round(100 * float(np.mean(predicted[called] == actual[called])), 2)
                if called.any()
                else None
            ),
        }

    bins = []
    edges = (0.50, 0.55, 0.60, 0.65, 0.70, 0.80, 1.01)
    raw_direction = np.asarray(
        [classes[int(np.argmax(row))] for row in probabilities]
    )
    for low, high in zip(edges, edges[1:]):
        mask = (confidence >= low) & (confidence < high)
        if not mask.any():
            continue
        bins.append(
            {
                "confidence_from": low,
                "confidence_to": round(high if high <= 1 else 1.0, 2),
                "samples": int(mask.sum()),
                "mean_confidence_pct": round(100 * float(np.mean(confidence[mask])), 2),
                "observed_accuracy_pct": round(
                    100 * float(np.mean(raw_direction[mask] == actual[mask])),
                    2,
                ),
            }
        )
    return by_event, bins


def train_lead(lead: int) -> tuple[dict, list[dict]]:
    all_rows, audit = build_samples(lead)
    unclear = [row for row in all_rows if row["target"] == "UNCERTAIN"]
    rows = [row for row in all_rows if row["target"] != "UNCERTAIN"]
    train = [row for row in rows if date.fromisoformat(row["release_utc"][:10]) < TEST_START]
    test = [row for row in rows if date.fromisoformat(row["release_utc"][:10]) >= TEST_START]
    y_train = np.asarray([row["target"] for row in train])
    y_test = np.asarray([row["target"] for row in test])

    comparisons = []
    profiles = {
        "legacy": list(range(LEGACY_FEATURE_COUNT)),
        "enhanced": list(range(len(FEATURE_NAMES))),
    }
    for profile, feature_indices in profiles.items():
        x_train = np.asarray(
            [[row["features"][index] for index in feature_indices] for row in train],
            dtype=float,
        )
        x_test = np.asarray(
            [[row["features"][index] for index in feature_indices] for row in test],
            dtype=float,
        )
        models = candidates()
        if profile == "legacy":
            models = {key: models[key] for key in ("logistic", "extra_trees")}
        for name, model in models.items():
            cv = cross_validate(train, model, feature_indices)
            selected_threshold = cv["selected_threshold"]
            fitted = clone(model)
            fitted.fit(x_train, y_train)
            probabilities = fitted.predict_proba(x_test)
            classes = list(fitted.classes_)
            predicted = apply_threshold(probabilities, classes, selected_threshold)
            comparisons.append(
                {
                    "name": name,
                    "profile": profile,
                    "feature_indices": feature_indices,
                    "cv": cv,
                    "validation": metrics(y_test, predicted, probabilities, classes),
                    "model": fitted,
                    "classes": classes,
                    "threshold": selected_threshold,
                    "probabilities": probabilities,
                    "predicted": predicted,
                }
            )
    deployment_candidates = [
        item for item in comparisons
        if item["profile"] == DEPLOYMENT_PROFILE[lead]
    ]
    selected = max(
        deployment_candidates,
        key=lambda item: (
            item["cv"]["selected_metrics"]["selection_score"],
            -item["cv"]["selected_metrics"]["brier_multiclass"],
        ),
    )

    expected_ranges = {}
    for event in EVENTS:
        values = [
            row["reaction"]["range"]
            for row in all_rows
            if row["event"] == event and date.fromisoformat(row["release_utc"][:10]) < TEST_START
        ]
        expected_ranges[event] = {
            "median_usd": round(float(np.median(values)), 3) if values else None,
            "p75_usd": round(float(np.percentile(values, 75)), 3) if values else None,
            "samples": len(values),
        }

    MODEL_DIR.mkdir(exist_ok=True)
    selected_indices = selected["feature_indices"]
    production = clone(candidates()[selected["name"]])
    production.fit(
        np.asarray(
            [[row["features"][index] for index in selected_indices] for row in rows],
            dtype=float,
        ),
        np.asarray([row["target"] for row in rows]),
    )
    artifact = {
        "model": production,
        "model_name": selected["name"],
        "lead_minutes": lead,
        "classes": list(production.classes_),
        "threshold": selected["threshold"],
        "events": list(EVENTS),
        "feature_names": [FEATURE_NAMES[index] for index in selected_indices],
        "feature_indices": selected_indices,
        "feature_profile": selected["profile"],
        "trained_through": rows[-1]["release_utc"],
        "expected_ranges": expected_ranges,
        "event_history_features": {
            event: history_snapshot(all_rows, event)
            for event in EVENTS
        },
        "feature_version": 2,
        "execution_capability": False,
    }
    model_path = MODEL_DIR / f"gold_news_impulse_{lead}m.joblib"
    joblib.dump(artifact, model_path)

    details = []
    for row, prediction, probability in zip(test, selected["predicted"], selected["probabilities"]):
        probability_map = {label: float(value) for label, value in zip(selected["classes"], probability)}
        details.append(
            {
                "lead_minutes": lead,
                "release_utc": row["release_utc"],
                "event": row["event"],
                "actual_impulse": row["target"],
                "prediction": prediction,
                "confidence": round(max(probability_map.get("BUY", 0), probability_map.get("SELL", 0)), 5),
                "prob_buy": round(probability_map.get("BUY", 0), 5),
                "prob_sell": round(probability_map.get("SELL", 0), 5),
                "prob_uncertain": round(probability_map.get("UNCERTAIN", 0), 5),
                "release_range_usd": round(row["reaction"]["range"], 3),
                "release_close_move_usd": round(row["reaction"]["release_move"], 3),
                "up_excursion_usd": round(row["reaction"]["up_excursion"], 3),
                "down_excursion_usd": round(row["reaction"]["down_excursion"], 3),
                "direction_1m": row["reaction"]["sustained"].get("1"),
                "direction_5m": row["reaction"]["sustained"].get("5"),
                "direction_15m": row["reaction"]["sustained"].get("15"),
            }
        )

    report_comparisons = [
        {
            key: value
            for key, value in comparison.items()
            if key not in {"model", "classes", "probabilities", "predicted", "feature_indices"}
        }
        for comparison in comparisons
    ]
    by_event, calibration = validation_breakdowns(
        test,
        selected["predicted"],
        selected["probabilities"],
        selected["classes"],
    )
    report = {
        "lead_minutes": lead,
        "audit": audit,
        "unclear_release_minutes_excluded": len(unclear),
        "train_samples": len(train),
        "validation_samples": len(test),
        "test_start": TEST_START.isoformat(),
        "target": (
            "Release-minute sustained direction from the T-1 midpoint to the release M1 close. "
            "Moves below an ATR/spread threshold are excluded as unclear."
        ),
        "comparisons": report_comparisons,
        "selected_model": selected["name"],
        "selected_feature_profile": selected["profile"],
        "selected_threshold": selected["threshold"],
        "selected_validation": selected["validation"],
        "validation_by_event": by_event,
        "confidence_calibration": calibration,
        "baselines": baseline_metrics(train, test),
        "expected_release_range_by_event": expected_ranges,
        "model_path": str(model_path.relative_to(ROOT)),
    }
    return report, details


def run() -> dict:
    reports = []
    details = []
    for lead in LEADS:
        print(f"Training and validating the {lead}-minute prediction model...")
        report, lead_details = train_lead(lead)
        reports.append(report)
        details.extend(lead_details)

    with DETAIL_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(details[0]))
        writer.writeheader()
        writer.writerows(details)

    final = {
        "scope": {
            "prediction_only": True,
            "trade_execution": False,
            "supported_events": list(EVENTS),
            "unsupported_inputs": (
                "Point-in-time consensus/actual/revision, DXY, Treasury yields, and sub-minute ticks are not "
                "present in the local archive and are not fabricated."
            ),
            "price_resolution": "XAUUSD M1 bid/ask; 30-second metrics unavailable",
            "train_validation": "Chronological expanding-window CV plus untouched final two years",
        },
        "models": reports,
    }
    REPORT_PATH.write_text(json.dumps(final, indent=2), encoding="utf-8")
    print(json.dumps(final, indent=2))
    return final


if __name__ == "__main__":
    run()
