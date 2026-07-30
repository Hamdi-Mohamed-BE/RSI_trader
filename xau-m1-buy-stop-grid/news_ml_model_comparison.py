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
from sklearn.metrics import accuracy_score, log_loss, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import fifteen_year_news_backtest as research


ROOT = Path(__file__).resolve().parent
REPORT_PATH = ROOT / "news_ml_comparison_report.json"
HOLDOUT_PATH = ROOT / "news_ml_last_2_months.csv"
MODEL_PATH = ROOT / "news_direction_model.joblib"
TRAIN_END = date(2024, 7, 30)
HOLDOUT_START = date(2026, 5, 30)


def model_candidates() -> dict:
    return {
        "regularized_logistic": Pipeline(
            [
                ("scale", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=0.03,
                        class_weight="balanced",
                        max_iter=2_000,
                        random_state=42,
                    ),
                ),
            ]
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=500,
            max_depth=4,
            min_samples_leaf=15,
            max_features=0.7,
            class_weight="balanced_subsample",
            random_state=42,
            n_jobs=-1,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=500,
            max_depth=4,
            min_samples_leaf=15,
            max_features=0.7,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        ),
        "hist_gradient_boosting": HistGradientBoostingClassifier(
            max_iter=150,
            learning_rate=0.035,
            max_leaf_nodes=7,
            min_samples_leaf=25,
            l2_regularization=3,
            random_state=42,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=120,
            learning_rate=0.03,
            max_depth=2,
            min_samples_leaf=20,
            subsample=0.8,
            random_state=42,
        ),
    }


def load_samples() -> list[dict]:
    events = research.build_calendar()
    days = sorted({event.release_utc.date().isoformat() for event in events})
    spreads = research.annual_spreads(days)
    cache = {}
    samples = []
    for event in events:
        day = event.release_utc.date().isoformat()
        for side in ("bid", "ask"):
            cache.setdefault((day, side), research.load_day(day, side))
        bid, ask, _ = research.complete_sides(
            cache[(day, "bid")],
            cache[(day, "ask")],
            spreads[event.release_utc.year],
        )
        sample = research.feature_row(event, bid, ask)
        if sample:
            samples.append(sample)
    return samples


def evaluate(model, samples: list[dict]) -> tuple[dict, list[dict]]:
    x_values = np.asarray([sample["features"] for sample in samples])
    targets = np.asarray([sample["target"] for sample in samples])
    probabilities = model.predict_proba(x_values)[:, 1]
    predictions = probabilities >= 0.5
    rows = []
    for sample, probability, prediction in zip(samples, probabilities, predictions):
        price_pnl = sample["buy_pnl"] if prediction else sample["sell_pnl"]
        usd_pnl = max(-100.0, price_pnl * 8)
        rows.append(
            {
                "release_utc": sample["release_utc"],
                "event": sample["event"],
                "prediction": "UP" if prediction else "DOWN",
                "up_probability": round(float(probability), 5),
                "actual": sample["actual_direction"],
                "correct": int(prediction == sample["target"]),
                "pnl_pips": round(price_pnl / 0.01, 1),
                "pnl_usd": round(usd_pnl, 2),
            }
        )
    pnl = [row["pnl_usd"] for row in rows]
    gains = sum(value for value in pnl if value > 0)
    losses = -sum(value for value in pnl if value < 0)
    metrics = {
        "events": len(rows),
        "accuracy_pct": round(100 * accuracy_score(targets, predictions), 2),
        "roc_auc": round(float(roc_auc_score(targets, probabilities)), 4),
        "execution_win_rate_pct": round(100 * sum(value > 0 for value in pnl) / len(pnl), 2),
        "net_usd_fresh_100_each": round(sum(pnl), 2),
        "profit_factor": round(gains / losses, 3) if losses else None,
    }
    return metrics, rows


def run() -> dict:
    samples = load_samples()
    train = [sample for sample in samples if date.fromisoformat(sample["release_utc"][:10]) < TRAIN_END]
    validation = [
        sample
        for sample in samples
        if TRAIN_END <= date.fromisoformat(sample["release_utc"][:10]) < HOLDOUT_START
    ]
    holdout = [
        sample for sample in samples if date.fromisoformat(sample["release_utc"][:10]) >= HOLDOUT_START
    ]
    x_train = np.asarray([sample["features"] for sample in train])
    y_train = np.asarray([sample["target"] for sample in train])
    candidates = model_candidates()
    splitter = TimeSeriesSplit(n_splits=5)
    comparison = {}

    for name, candidate in candidates.items():
        fold_probabilities = np.zeros(len(train))
        tested = np.zeros(len(train), dtype=bool)
        for fit_indices, test_indices in splitter.split(x_train):
            fold_model = clone(candidate)
            fold_model.fit(x_train[fit_indices], y_train[fit_indices])
            fold_probabilities[test_indices] = fold_model.predict_proba(x_train[test_indices])[:, 1]
            tested[test_indices] = True
        cv_targets = y_train[tested]
        cv_probabilities = fold_probabilities[tested]
        fitted = clone(candidate).fit(x_train, y_train)
        validation_metrics, _ = evaluate(fitted, validation)
        holdout_metrics, _ = evaluate(fitted, holdout)
        comparison[name] = {
            "train_expanding_cv_log_loss": round(log_loss(cv_targets, cv_probabilities), 5),
            "train_expanding_cv_accuracy_pct": round(
                100 * accuracy_score(cv_targets, cv_probabilities >= 0.5),
                2,
            ),
            "train_expanding_cv_roc_auc": round(float(roc_auc_score(cv_targets, cv_probabilities)), 4),
            "validation_22_months": validation_metrics,
            "final_holdout_2_months": holdout_metrics,
        }

    selected_name = min(
        comparison,
        key=lambda name: comparison[name]["train_expanding_cv_log_loss"],
    )
    selected_model = clone(candidates[selected_name]).fit(x_train, y_train)
    holdout_metrics, holdout_rows = evaluate(selected_model, holdout)
    joblib.dump(
        {
            "model": selected_model,
            "model_name": selected_name,
            "feature_names": research.FEATURE_NAMES,
            "trained_through": str(TRAIN_END),
            "watchlist": research.EVENT_ORDER,
        },
        MODEL_PATH,
    )
    with HOLDOUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(holdout_rows[0]))
        writer.writeheader()
        writer.writerows(holdout_rows)

    report = {
        "split": {
            "training": f"{research.START_DATE} through {TRAIN_END.replace(day=29)}",
            "model_comparison_validation": f"{TRAIN_END} through {HOLDOUT_START.replace(day=29)}",
            "final_holdout": f"{HOLDOUT_START} through {research.END_DATE}",
            "counts": {
                "train": len(train),
                "validation_22_months": len(validation),
                "final_holdout_2_months": len(holdout),
            },
        },
        "selection_rule": "Lowest expanding-window cross-validation log loss on the 13-year training sample only",
        "selected_model": selected_name,
        "comparison": comparison,
        "selected_model_final_holdout": holdout_metrics,
        "sentiment_status": (
            "Not included. A valid historical sentiment feature requires timestamped text available before "
            "the trade decision; released statements cannot be used for pre-release predictions."
        ),
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    run()
