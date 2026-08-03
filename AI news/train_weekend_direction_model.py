from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import joblib
import MetaTrader5 as mt5
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    log_loss,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from weekend_direction_model import (
    CORE_FEATURES,
    FEATURE_NAMES,
    HISTORY_FEATURES,
    MarketSeries,
    build_weekend_dataset,
    choose_confidence_threshold,
    expanding_folds,
    records_to_arrays,
    wilson_interval,
)


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "weekend-direction"
MODEL_DIR = ROOT / "models"
CACHE_PATH = DATA_DIR / "market_5y.npz"
MODEL_PATH = MODEL_DIR / "gold_weekend_direction.joblib"
METADATA_PATH = MODEL_DIR / "gold_weekend_direction.metadata.json"
JSON_PATH = ROOT / "gold_weekend_direction_5y.json"
CSV_PATH = ROOT / "gold_weekend_direction_predictions.csv"
REPORT_PATH = ROOT / "GOLD_WEEKEND_DIRECTION_5Y.md"
CHART_DIR = ROOT / "charts" / "weekend-direction-5y"


def discover_symbol(canonical: str) -> str | None:
    aliases = {
        "XAUUSD": ("XAUUSD", "GOLD"),
        "XAGUSD": ("XAGUSD", "SILVER"),
        "US30": ("US30", "DJ30", "DOW30", "WS30"),
        "BTCUSD": ("BTCUSD",),
    }[canonical]
    candidates: list[tuple[int, str]] = []
    for symbol in mt5.symbols_get() or []:
        name = symbol.name.upper()
        description = (symbol.description or "").upper()
        score = 0
        for alias in aliases:
            if name == alias:
                score = max(score, 100)
            elif name.startswith(alias):
                score = max(score, 80)
            elif alias in name:
                score = max(score, 60)
            elif alias in description:
                score = max(score, 30)
        if canonical == "US30" and "DOW INC" in description:
            score = 0
        if score:
            candidates.append((score, symbol.name))
    return max(candidates)[1] if candidates else None


def _series_from_rates(symbol: str, point: float, timeframe_seconds: int, rates: np.ndarray) -> MarketSeries:
    return MarketSeries(
        symbol=symbol,
        point=point,
        timeframe_seconds=timeframe_seconds,
        time=np.asarray(rates["time"], dtype=np.int64),
        open=np.asarray(rates["open"], dtype=np.float64),
        high=np.asarray(rates["high"], dtype=np.float64),
        low=np.asarray(rates["low"], dtype=np.float64),
        close=np.asarray(rates["close"], dtype=np.float64),
        tick_volume=np.asarray(rates["tick_volume"], dtype=np.float64),
        spread=np.asarray(rates["spread"], dtype=np.float64),
    )


def _save_cache(series: dict[str, MarketSeries], metadata: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ndarray] = {"metadata": np.asarray(json.dumps(metadata))}
    for canonical, item in series.items():
        prefix = canonical.lower()
        for field in ("time", "open", "high", "low", "close", "tick_volume", "spread"):
            arrays[f"{prefix}_{field}"] = getattr(item, field)
    np.savez_compressed(CACHE_PATH, **arrays)


def _load_cache() -> tuple[dict[str, MarketSeries], dict]:
    with np.load(CACHE_PATH, allow_pickle=False) as data:
        metadata = json.loads(str(data["metadata"]))
        series: dict[str, MarketSeries] = {}
        for canonical, item in metadata["series"].items():
            prefix = canonical.lower()
            series[canonical] = MarketSeries(
                symbol=item["symbol"],
                point=float(item["point"]),
                timeframe_seconds=int(item["timeframe_seconds"]),
                time=np.array(data[f"{prefix}_time"]),
                open=np.array(data[f"{prefix}_open"]),
                high=np.array(data[f"{prefix}_high"]),
                low=np.array(data[f"{prefix}_low"]),
                close=np.array(data[f"{prefix}_close"]),
                tick_volume=np.array(data[f"{prefix}_tick_volume"]),
                spread=np.array(data[f"{prefix}_spread"]),
            )
    return series, metadata


def load_market_data(start: datetime, end: datetime, refresh: bool) -> tuple[dict[str, MarketSeries], dict]:
    if CACHE_PATH.exists() and not refresh:
        series, metadata = _load_cache()
        cached_start = datetime.fromisoformat(metadata["requested_start_utc"])
        cached_end = datetime.fromisoformat(metadata["requested_end_utc"])
        if cached_start <= start and cached_end >= end - timedelta(days=2):
            return series, metadata

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    try:
        account = mt5.account_info()
        loaded: dict[str, MarketSeries] = {}
        meta_series: dict[str, dict] = {}
        definitions = {
            "XAUUSD": (mt5.TIMEFRAME_M1, 60),
            "XAGUSD": (mt5.TIMEFRAME_H1, 3600),
            "US30": (mt5.TIMEFRAME_H1, 3600),
            "BTCUSD": (mt5.TIMEFRAME_H1, 3600),
        }
        for canonical, (timeframe, seconds) in definitions.items():
            symbol = discover_symbol(canonical)
            if not symbol:
                if canonical == "XAUUSD":
                    raise RuntimeError("No broker XAUUSD symbol was found")
                continue
            if not mt5.symbol_select(symbol, True):
                raise RuntimeError(f"Could not select {symbol}: {mt5.last_error()}")
            info = mt5.symbol_info(symbol)
            rates = mt5.copy_rates_range(symbol, timeframe, start, end)
            minimum = 500_000 if canonical == "XAUUSD" else 5_000
            if rates is None or len(rates) < minimum:
                if canonical == "XAUUSD":
                    raise RuntimeError(f"Incomplete XAUUSD M1 history: {mt5.last_error()}")
                continue
            loaded[canonical] = _series_from_rates(symbol, float(info.point), seconds, rates)
            meta_series[canonical] = {
                "symbol": symbol,
                "description": info.description,
                "point": float(info.point),
                "timeframe_seconds": seconds,
                "bars": len(rates),
                "first_utc": datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc).isoformat(),
                "last_utc": datetime.fromtimestamp(int(rates[-1]["time"]), timezone.utc).isoformat(),
            }
        metadata = {
            "server": getattr(account, "server", None),
            "requested_start_utc": start.isoformat(),
            "requested_end_utc": end.isoformat(),
            "series": meta_series,
        }
        _save_cache(loaded, metadata)
        return loaded, metadata
    finally:
        mt5.shutdown()


def make_logistic(indices: list[int], c_value: float, balanced: bool) -> Pipeline:
    selector = ColumnTransformer([("selected", "passthrough", indices)], remainder="drop")
    return Pipeline(
        [
            ("select", selector),
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=c_value,
                    class_weight="balanced" if balanced else None,
                    max_iter=5_000,
                    random_state=42,
                ),
            ),
        ]
    )


def make_forest(indices: list[int], depth: int, leaf: int) -> Pipeline:
    selector = ColumnTransformer([("selected", "passthrough", indices)], remainder="drop")
    return Pipeline(
        [
            ("select", selector),
            ("impute", SimpleImputer(strategy="median")),
            (
                "model",
                RandomForestClassifier(
                    n_estimators=500,
                    max_depth=depth,
                    min_samples_leaf=leaf,
                    max_features=0.6,
                    class_weight="balanced",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def candidate_factories() -> list[tuple[str, str, Callable[[], Pipeline]]]:
    index = {name: position for position, name in enumerate(FEATURE_NAMES)}
    feature_sets = {
        "gold": [index[name] for name in CORE_FEATURES],
        "gold_history": [index[name] for name in CORE_FEATURES + HISTORY_FEATURES],
        "gold_cross_history": list(range(len(FEATURE_NAMES))),
    }
    candidates: list[tuple[str, str, Callable[[], Pipeline]]] = []
    for feature_set, indices in feature_sets.items():
        for c_value in (0.01, 0.05, 0.2, 1.0):
            for balanced in (False, True):
                name = f"logistic_{feature_set}_c{c_value:g}_{'balanced' if balanced else 'plain'}"
                candidates.append((name, feature_set, lambda i=indices, c=c_value, b=balanced: make_logistic(i, c, b)))
        for depth, leaf in ((2, 12), (3, 15)):
            name = f"forest_{feature_set}_d{depth}_leaf{leaf}"
            candidates.append((name, feature_set, lambda i=indices, d=depth, l=leaf: make_forest(i, d, l)))
    return candidates


def metric_bundle(y_true: np.ndarray, probabilities: np.ndarray) -> dict:
    predicted = (probabilities >= 0.5).astype(int)
    correct = int(np.sum(predicted == y_true))
    low, high = wilson_interval(correct, len(y_true))
    matrix = confusion_matrix(y_true, predicted, labels=[0, 1])
    return {
        "samples": len(y_true),
        "up_rate_pct": round(100.0 * float(np.mean(y_true)), 2),
        "accuracy_pct": round(100.0 * accuracy_score(y_true, predicted), 2),
        "accuracy_ci95_pct": [round(100.0 * low, 2), round(100.0 * high, 2)],
        "balanced_accuracy_pct": round(100.0 * balanced_accuracy_score(y_true, predicted), 2),
        "roc_auc": round(float(roc_auc_score(y_true, probabilities)), 4) if len(np.unique(y_true)) > 1 else None,
        "brier_score": round(float(brier_score_loss(y_true, probabilities)), 5),
        "log_loss": round(float(log_loss(y_true, probabilities, labels=[0, 1])), 5),
        "confusion_matrix_down_up": matrix.tolist(),
    }


def action_bundle(y_true: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict:
    predicted = (probabilities >= 0.5).astype(int)
    confidence = np.maximum(probabilities, 1.0 - probabilities)
    mask = confidence >= threshold
    count = int(np.sum(mask))
    correct = int(np.sum(predicted[mask] == y_true[mask])) if count else 0
    low, high = wilson_interval(correct, count)
    return {
        "threshold": threshold,
        "actions": count,
        "no_trade": int(len(y_true) - count),
        "coverage_pct": round(100.0 * count / len(y_true), 2) if len(y_true) else 0.0,
        "accuracy_pct": round(100.0 * correct / count, 2) if count else None,
        "accuracy_ci95_pct": [round(100.0 * low, 2), round(100.0 * high, 2)] if count else None,
    }


def evaluate_candidates(x_dev: np.ndarray, y_dev: np.ndarray) -> tuple[dict, list[dict], list[tuple[np.ndarray, np.ndarray]]]:
    initial_train = max(80, len(y_dev) // 2)
    folds = expanding_folds(len(y_dev), initial_train=initial_train, splits=4, embargo=1)
    ranking: list[dict] = []
    for name, feature_set, factory in candidate_factories():
        probabilities = np.full(len(y_dev), np.nan)
        for train, test in folds:
            estimator = factory()
            estimator.fit(x_dev[train], y_dev[train])
            probabilities[test] = estimator.predict_proba(x_dev[test])[:, 1]
        mask = np.isfinite(probabilities)
        metrics = metric_bundle(y_dev[mask], probabilities[mask])
        selection_score = metrics["brier_score"] + 0.0001 * (100.0 - metrics["balanced_accuracy_pct"])
        ranking.append(
            {
                "name": name,
                "feature_set": feature_set,
                "selection_score": round(selection_score, 6),
                "metrics": metrics,
                "probabilities": probabilities,
                "factory": factory,
            }
        )
    ranking.sort(key=lambda item: (item["selection_score"], item["metrics"]["log_loss"], item["name"]))
    return ranking[0], ranking, folds


def rolling_predictions(factory: Callable[[], Pipeline], x: np.ndarray, y: np.ndarray, warmup: int = 104) -> np.ndarray:
    probabilities = np.full(len(y), np.nan)
    for index in range(warmup, len(y)):
        train_end = index - 1
        estimator = factory()
        estimator.fit(x[:train_end], y[:train_end])
        probabilities[index] = estimator.predict_proba(x[index : index + 1])[:, 1][0]
    return probabilities


def _svg_accuracy(path: Path, rows: list[dict]) -> None:
    width, height, margin = 920, 420, 70
    plot_w, plot_h = width - 2 * margin, height - 2 * margin
    bars = [row for row in rows if row["samples"]]
    bar_w = plot_w / max(1, len(bars)) * 0.55
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#08111f"/>',
        '<text x="70" y="36" fill="#f5f7fb" font-family="Arial" font-size="22" font-weight="700">Chronological out-of-sample accuracy</text>',
    ]
    for value in (0, 25, 50, 75, 100):
        y = margin + plot_h * (1.0 - value / 100.0)
        pieces.append(f'<line x1="{margin}" y1="{y:.1f}" x2="{width-margin}" y2="{y:.1f}" stroke="#25334a"/>')
        pieces.append(f'<text x="{margin-12}" y="{y+5:.1f}" text-anchor="end" fill="#91a0b8" font-family="Arial" font-size="12">{value}%</text>')
    for index, row in enumerate(bars):
        centre = margin + plot_w * (index + 0.5) / len(bars)
        value = row["accuracy_pct"]
        top = margin + plot_h * (1.0 - value / 100.0)
        color = "#20d6a7" if value >= 50 else "#ff6577"
        pieces.append(f'<rect x="{centre-bar_w/2:.1f}" y="{top:.1f}" width="{bar_w:.1f}" height="{margin+plot_h-top:.1f}" rx="4" fill="{color}"/>')
        pieces.append(f'<text x="{centre:.1f}" y="{top-8:.1f}" text-anchor="middle" fill="#f5f7fb" font-family="Arial" font-size="13">{value:.1f}%</text>')
        pieces.append(f'<text x="{centre:.1f}" y="{height-margin+24:.1f}" text-anchor="middle" fill="#b5c0d2" font-family="Arial" font-size="13">{row["year"]}</text>')
    pieces.append("</svg>")
    path.write_text("\n".join(pieces), encoding="utf-8")


def _data_hash(records) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(record.reopen_utc.encode("ascii"))
        digest.update(np.asarray(record.feature_values, dtype=np.float64).tobytes())
        digest.update(str(record.label_up).encode("ascii"))
    return digest.hexdigest()


def train_and_report(series: dict[str, MarketSeries], data_metadata: dict, start: datetime, end: datetime) -> dict:
    records = [
        record
        for record in build_weekend_dataset(series["XAUUSD"], {key: value for key, value in series.items() if key != "XAUUSD"})
        if start <= datetime.fromisoformat(record.reopen_utc) < end
    ]
    if len(records) < 200:
        raise RuntimeError(f"Only {len(records)} usable weekends were found; at least 200 are required")
    x, y = records_to_arrays(records)
    holdout_size = 52
    split = len(records) - holdout_size
    x_dev, y_dev = x[:split], y[:split]
    x_holdout, y_holdout = x[split:], y[split:]

    selected, ranking, folds = evaluate_candidates(x_dev, y_dev)
    oof_mask = np.isfinite(selected["probabilities"])
    threshold_choice = choose_confidence_threshold(y_dev[oof_mask], selected["probabilities"][oof_mask])
    threshold = float(threshold_choice["threshold"])

    validation_model = selected["factory"]()
    validation_model.fit(x_dev, y_dev)
    holdout_probabilities = validation_model.predict_proba(x_holdout)[:, 1]
    holdout_metrics = metric_bundle(y_holdout, holdout_probabilities)
    holdout_actions = action_bundle(y_holdout, holdout_probabilities, threshold)

    majority_probability = float(np.mean(y_dev))
    majority_metrics = metric_bundle(y_holdout, np.full(len(y_holdout), majority_probability))
    momentum_index = FEATURE_NAMES.index("xau_ret_1440m")
    momentum_predictions = (x_holdout[:, momentum_index] >= 0).astype(int)
    momentum_accuracy = round(100.0 * float(np.mean(momentum_predictions == y_holdout)), 2)
    validated = bool(
        holdout_metrics["accuracy_pct"] > majority_metrics["accuracy_pct"]
        and holdout_metrics["roc_auc"] is not None
        and holdout_metrics["roc_auc"] > 0.5
    )

    rolling = rolling_predictions(selected["factory"], x, y)
    rolling_rows: list[dict] = []
    years = sorted({datetime.fromisoformat(record.reopen_utc).year for record in records})
    for year in years:
        mask = np.asarray([
            datetime.fromisoformat(record.reopen_utc).year == year and np.isfinite(rolling[index])
            for index, record in enumerate(records)
        ])
        if np.any(mask):
            metrics = metric_bundle(y[mask], rolling[mask])
            metrics.update({"year": year, "action": action_bundle(y[mask], rolling[mask], threshold)})
        else:
            metrics = {"year": year, "samples": 0, "accuracy_pct": None, "action": None}
        rolling_rows.append(metrics)

    final_model = selected["factory"]()
    final_model.fit(x, y)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": final_model,
            "feature_names": list(FEATURE_NAMES),
            "confidence_threshold": threshold,
            "placement_lead_minutes": 5,
            "trained_through_utc": records[-1].feature_time_utc,
            "purpose": "Prediction only; never sends orders",
            "validated": validated,
        },
        MODEL_PATH,
    )

    candidates_public = [
        {key: value for key, value in item.items() if key not in ("factory", "probabilities")}
        for item in ranking[:10]
    ]
    output = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "Predict UP/DOWN direction of the XAUUSD weekly reopen; prediction only",
        "data": data_metadata,
        "sample": {
            "start_reopen_utc": records[0].reopen_utc,
            "end_reopen_utc": records[-1].reopen_utc,
            "weekends": len(records),
            "development_weekends": len(y_dev),
            "frozen_holdout_weekends": len(y_holdout),
            "frozen_holdout_start_utc": records[split].reopen_utc,
            "up_weekends": int(np.sum(y)),
            "down_weekends": int(len(y) - np.sum(y)),
            "data_hash_sha256": _data_hash(records),
        },
        "anti_overfit_protocol": {
            "development": "All model, feature-set, regularization, and confidence-threshold selection used only the first four years",
            "validation": "Four expanding chronological folds with a one-week embargo",
            "final_test": "The final 52 weekends were frozen and evaluated once after selection",
            "live_refit": "After recording the holdout result, the saved prediction model was refit on all five years",
        },
        "selected_model": {
            "name": selected["name"],
            "feature_set": selected["feature_set"],
            "development_oof": selected["metrics"],
            "confidence_selection": threshold_choice,
            "deployment_status": "validated" if validated else "rejected",
        },
        "frozen_holdout": {
            "model": holdout_metrics,
            "high_confidence": holdout_actions,
            "majority_baseline": majority_metrics,
            "friday_24h_momentum_baseline_accuracy_pct": momentum_accuracy,
        },
        "rolling_oos_by_year": rolling_rows,
        "top_development_candidates": candidates_public,
        "folds": [
            {"train_samples": len(train), "test_samples": len(test), "train_end": int(train[-1]), "test_start": int(test[0]), "test_end": int(test[-1])}
            for train, test in folds
        ],
    }
    JSON_PATH.write_text(json.dumps(output, indent=2), encoding="utf-8")
    METADATA_PATH.write_text(json.dumps({key: value for key, value in output.items() if key != "top_development_candidates"}, indent=2), encoding="utf-8")

    selected_probabilities = np.full(len(records), np.nan)
    selected_probabilities[:split] = selected["probabilities"]
    selected_probabilities[split:] = holdout_probabilities
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "feature_time_utc", "friday_close_utc", "reopen_utc", "friday_mid_close", "reopen_mid_open",
            "gap_usd", "gap_pct", "actual", "split", "probability_up", "prediction", "decision", "correct",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index, record in enumerate(records):
            probability = selected_probabilities[index]
            prediction = "" if not np.isfinite(probability) else ("UP" if probability >= 0.5 else "DOWN")
            confidence = max(probability, 1.0 - probability) if np.isfinite(probability) else float("nan")
            decision = "" if not np.isfinite(probability) else (prediction if confidence >= threshold else "NO_TRADE")
            writer.writerow(
                {
                    "feature_time_utc": record.feature_time_utc,
                    "friday_close_utc": record.friday_close_utc,
                    "reopen_utc": record.reopen_utc,
                    "friday_mid_close": record.friday_mid_close,
                    "reopen_mid_open": record.reopen_mid_open,
                    "gap_usd": record.gap_usd,
                    "gap_pct": record.gap_pct,
                    "actual": "UP" if record.label_up else "DOWN",
                    "split": "frozen_holdout" if index >= split else "development",
                    "probability_up": "" if not np.isfinite(probability) else round(float(probability), 6),
                    "prediction": prediction,
                    "decision": decision,
                    "correct": "" if not prediction else int(prediction == ("UP" if record.label_up else "DOWN")),
                }
            )

    CHART_DIR.mkdir(parents=True, exist_ok=True)
    _svg_accuracy(CHART_DIR / "accuracy-by-year.svg", rolling_rows)
    write_report(output)
    return output


def write_report(output: dict) -> None:
    sample = output["sample"]
    selected = output["selected_model"]
    holdout = output["frozen_holdout"]
    model = holdout["model"]
    action = holdout["high_confidence"]
    majority = holdout["majority_baseline"]
    action_accuracy = "N/A" if action["accuracy_pct"] is None else f"{action['accuracy_pct']:.2f}%"
    action_interval = "N/A" if not action["accuracy_ci95_pct"] else f"{action['accuracy_ci95_pct'][0]:.2f}%-{action['accuracy_ci95_pct'][1]:.2f}%"
    lines = [
        "# Gold Weekend-Direction Model: Five-Year Validation",
        "",
        f"Data: `{sample['start_reopen_utc'][:10]}` through `{sample['end_reopen_utc'][:10]}` ({sample['weekends']} completed weekends)  ",
        f"Broker feed: `{output['data']['server']}` / `{output['data']['series']['XAUUSD']['symbol']}`  ",
        "Target: direction of the executable-midpoint change from the final Friday M1 close to the first weekly-reopen M1 open  ",
        "Decision time: five completed M1 bars before the broker's Friday close",
        "",
        f"**Deployment verdict: {selected['deployment_status'].upper()}.** The saved artifact remains available for reproducible research, but a rejected model is forced to `NO TRADE` in the predictor.",
        "",
        "## Frozen unseen final year",
        "",
        "| Measure | Selected model | Majority baseline |",
        "|---|---:|---:|",
        f"| Samples | {model['samples']} | {majority['samples']} |",
        f"| Direction accuracy | **{model['accuracy_pct']:.2f}%** | {majority['accuracy_pct']:.2f}% |",
        f"| 95% accuracy interval | {model['accuracy_ci95_pct'][0]:.2f}%-{model['accuracy_ci95_pct'][1]:.2f}% | {majority['accuracy_ci95_pct'][0]:.2f}%-{majority['accuracy_ci95_pct'][1]:.2f}% |",
        f"| Balanced accuracy | {model['balanced_accuracy_pct']:.2f}% | {majority['balanced_accuracy_pct']:.2f}% |",
        f"| ROC AUC | {model['roc_auc']:.3f} | {majority['roc_auc']:.3f} |",
        f"| Brier score (lower is better) | {model['brier_score']:.4f} | {majority['brier_score']:.4f} |",
        f"| Friday 24h-momentum baseline | {holdout['friday_24h_momentum_baseline_accuracy_pct']:.2f}% | - |",
        "",
        "## Confidence-gated result",
        "",
        f"The confidence threshold `{action['threshold']:.3f}` was selected only from development walk-forward predictions.",
        "",
        "| Actions | No trade | Coverage | Accuracy | 95% interval |",
        "|---:|---:|---:|---:|---:|",
        f"| {action['actions']} | {action['no_trade']} | {action['coverage_pct']:.2f}% | {action_accuracy} | {action_interval} |",
        "",
        "## Anti-overfit protocol",
        "",
        f"- Development: first `{sample['development_weekends']}` weekends (approximately four years).",
        "- Selection: four expanding chronological folds with a one-week embargo.",
        "- Compared only regularized logistic models and deliberately shallow random forests.",
        "- Hyperparameters, feature set, and confidence threshold were fixed before opening the final year.",
        f"- Frozen test: final `{sample['frozen_holdout_weekends']}` weekends beginning `{sample['frozen_holdout_start_utc'][:10]}`.",
        "- The saved live model was refit on all data only after the frozen score was recorded.",
        "",
        "## Selected model",
        "",
        f"- `{selected['name']}` using `{selected['feature_set']}` features",
        f"- Development walk-forward accuracy: `{selected['development_oof']['accuracy_pct']:.2f}%`",
        f"- Development walk-forward ROC AUC: `{selected['development_oof']['roc_auc']:.3f}`",
        f"- Development walk-forward Brier: `{selected['development_oof']['brier_score']:.4f}`",
        "",
        "## Rolling chronological diagnostic",
        "",
        "This weekly retraining view begins after a 104-week warm-up. It is useful for stability checks, but only the frozen final year is a completely untouched test.",
        "",
        "| Year | OOS weeks | Accuracy | AUC | High-confidence actions | Action accuracy |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    for row in output["rolling_oos_by_year"]:
        if not row["samples"]:
            lines.append(f"| {row['year']} | warm-up | - | - | - | - |")
            continue
        action_row = row["action"]
        auc = "N/A" if row["roc_auc"] is None else f"{row['roc_auc']:.3f}"
        year_action_accuracy = "N/A" if action_row["accuracy_pct"] is None else f"{action_row['accuracy_pct']:.2f}%"
        lines.append(f"| {row['year']} | {row['samples']} | {row['accuracy_pct']:.2f}% | {auc} | {action_row['actions']} | {year_action_accuracy} |")
    lines.extend(
        [
            "",
            "![Chronological accuracy](charts/weekend-direction-5y/accuracy-by-year.svg)",
            "",
            "## Interpretation",
            "",
            "Accuracy must be compared with the majority baseline and its confidence interval. A score near 50%, an AUC near 0.50, or a Brier score no better than the baseline means the model has not demonstrated a dependable edge. In that case its correct operational output is `NO TRADE`, not forced certainty.",
            "",
            "This is a direction classifier, not a trading backtest. It does not claim that a correct direction can be executed profitably after spread, slippage, gaps, or broker margin constraints.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train and validate the XAUUSD weekend-direction classifier")
    parser.add_argument("--years", type=float, default=5.0)
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=365.2425 * args.years)
    series, metadata = load_market_data(start, end, args.refresh)
    output = train_and_report(series, metadata, start, end)
    frozen = output["frozen_holdout"]
    print(f"Model: {output['selected_model']['name']}")
    print(f"Frozen final-year accuracy: {frozen['model']['accuracy_pct']:.2f}% ({frozen['model']['samples']} weekends)")
    print(f"Majority baseline: {frozen['majority_baseline']['accuracy_pct']:.2f}%")
    print(f"High-confidence: {frozen['high_confidence']['accuracy_pct']}% on {frozen['high_confidence']['actions']} decisions")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
