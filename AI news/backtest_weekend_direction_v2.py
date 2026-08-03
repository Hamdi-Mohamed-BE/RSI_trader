from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import joblib
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from train_weekend_direction_model import _load_cache
from weekend_direction_model import build_weekend_dataset, expanding_folds, wilson_interval
from weekend_direction_v2 import (
    COT_FEATURES,
    MACRO_FEATURES,
    MARKET_FEATURES,
    V2_FEATURE_NAMES,
    V2Sample,
    build_v2_samples,
    fetch_gold_cot,
    load_macro_context,
    samples_to_arrays,
)


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "models" / "gold_weekend_direction_v2.joblib"
JSON_PATH = ROOT / "gold_weekend_direction_v2_nested_oos.json"
CSV_PATH = ROOT / "gold_weekend_direction_v2_predictions.csv"
REPORT_PATH = ROOT / "GOLD_WEEKEND_DIRECTION_V2.md"
CHART_PATH = ROOT / "charts" / "weekend-direction-v2" / "oos-call-accuracy.svg"


@dataclass(frozen=True)
class ModelSpec:
    name: str
    feature_set: str
    indices: tuple[int, ...]
    c_value: float
    balanced: bool


def feature_sets() -> dict[str, tuple[int, ...]]:
    index = {name: position for position, name in enumerate(V2_FEATURE_NAMES)}
    return {
        "market": tuple(index[name] for name in MARKET_FEATURES),
        "market_macro": tuple(index[name] for name in MARKET_FEATURES + MACRO_FEATURES),
        "all_context": tuple(range(len(V2_FEATURE_NAMES))),
    }


def candidate_specs(*, stage: str) -> list[ModelSpec]:
    output: list[ModelSpec] = []
    for feature_set, indices in feature_sets().items():
        for c_value in (0.01, 0.05, 0.2, 1.0):
            balanced_values = (True,) if stage == "significant" else (False, True)
            for balanced in balanced_values:
                output.append(
                    ModelSpec(
                        name=f"{stage}_{feature_set}_c{c_value:g}_{'balanced' if balanced else 'plain'}",
                        feature_set=feature_set,
                        indices=indices,
                        c_value=c_value,
                        balanced=balanced,
                    )
                )
    return output


def make_model(spec: ModelSpec) -> Pipeline:
    selector = ColumnTransformer([("selected", "passthrough", list(spec.indices))], remainder="drop")
    return Pipeline(
        [
            ("select", selector),
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=spec.c_value,
                    class_weight="balanced" if spec.balanced else None,
                    max_iter=5_000,
                    random_state=42,
                ),
            ),
        ]
    )


def probability_metrics(y_true: np.ndarray, probability: np.ndarray) -> dict:
    prediction = (probability >= 0.5).astype(int)
    return {
        "samples": int(len(y_true)),
        "accuracy_pct": round(100.0 * float(accuracy_score(y_true, prediction)), 2),
        "roc_auc": round(float(roc_auc_score(y_true, probability)), 4) if len(np.unique(y_true)) > 1 else None,
        "brier": round(float(brier_score_loss(y_true, probability)), 5),
        "log_loss": round(float(log_loss(y_true, probability, labels=[0, 1])), 5),
    }


def inner_model_selection(x: np.ndarray, y: np.ndarray, *, stage: str) -> tuple[ModelSpec, np.ndarray, list[dict]]:
    initial = max(52, len(y) // 2)
    folds = expanding_folds(len(y), initial_train=initial, splits=3, embargo=1)
    ranking: list[dict] = []
    for spec in candidate_specs(stage=stage):
        probability = np.full(len(y), np.nan)
        for train, test in folds:
            model = make_model(spec)
            model.fit(x[train], y[train])
            probability[test] = model.predict_proba(x[test])[:, 1]
        mask = np.isfinite(probability)
        metrics = probability_metrics(y[mask], probability[mask])
        ranking.append({"spec": spec, "probability": probability, "metrics": metrics})
    ranking.sort(key=lambda item: (item["metrics"]["brier"], item["metrics"]["log_loss"], item["spec"].name))
    selected = ranking[0]
    public = [{"spec": asdict(item["spec"]), "metrics": item["metrics"]} for item in ranking[:5]]
    return selected["spec"], selected["probability"], public


def choose_policy(
    significant: np.ndarray,
    direction: np.ndarray,
    significant_probability: np.ndarray,
    direction_probability: np.ndarray,
) -> dict:
    available = np.isfinite(significant_probability) & np.isfinite(direction_probability)
    candidates: list[dict] = []
    for significant_threshold in (0.40, 0.45, 0.50, 0.55, 0.60, 0.65):
        for direction_threshold in (0.50, 0.525, 0.55, 0.575, 0.60, 0.625, 0.65):
            confidence = np.maximum(direction_probability, 1.0 - direction_probability)
            calls = available & (significant_probability >= significant_threshold) & (confidence >= direction_threshold)
            count = int(np.sum(calls))
            available_count = int(np.sum(available))
            if count < max(8, int(available_count * 0.10)) or count > int(available_count * 0.50):
                continue
            predicted = (direction_probability >= 0.5).astype(int)
            correct = int(np.sum(calls & (significant == 1) & (predicted == direction)))
            meaningful_calls = int(np.sum(calls & (significant == 1)))
            low, high = wilson_interval(correct, count)
            candidates.append(
                {
                    "significant_threshold": significant_threshold,
                    "direction_threshold": direction_threshold,
                    "calls": count,
                    "coverage_pct": round(100.0 * count / available_count, 2),
                    "correct_call_precision_pct": round(100.0 * correct / count, 2),
                    "meaningful_precision_pct": round(100.0 * meaningful_calls / count, 2),
                    "direction_accuracy_on_meaningful_pct": round(100.0 * correct / meaningful_calls, 2) if meaningful_calls else None,
                    "wilson_low_pct": round(100.0 * low, 2),
                    "wilson_high_pct": round(100.0 * high, 2),
                }
            )
    if not candidates:
        return {"significant_threshold": 0.55, "direction_threshold": 0.60, "calls": 0}
    return max(
        candidates,
        key=lambda item: (
            item["wilson_low_pct"],
            item["correct_call_precision_pct"],
            item["coverage_pct"],
            -item["significant_threshold"],
            -item["direction_threshold"],
        ),
    )


def summarize_calls(samples: Sequence[V2Sample], call: np.ndarray, predicted_up: np.ndarray) -> dict:
    meaningful = np.asarray([sample.meaningful_gap for sample in samples], dtype=bool)
    actual_up = np.asarray([sample.direction_up for sample in samples], dtype=bool)
    count = int(np.sum(call))
    meaningful_calls = int(np.sum(call & meaningful))
    correct_mask = call & meaningful & (predicted_up == actual_up)
    correct = int(np.sum(correct_mask))
    wrong_direction = int(np.sum(call & meaningful & (predicted_up != actual_up)))
    no_gap_calls = int(np.sum(call & ~meaningful))
    low, high = wilson_interval(correct, count)
    signed_gap_usd = 0.0
    absolute_gap_usd = 0.0
    for index, sample in enumerate(samples):
        if not call[index]:
            continue
        sign = 1.0 if predicted_up[index] else -1.0
        signed_gap_usd += sign * sample.record.gap_usd
        absolute_gap_usd += abs(sample.record.gap_usd)
    return {
        "samples": len(samples),
        "calls": count,
        "coverage_pct": round(100.0 * count / len(samples), 2) if samples else 0.0,
        "correct_calls": correct,
        "wrong_direction_calls": wrong_direction,
        "no_meaningful_gap_calls": no_gap_calls,
        "correct_call_precision_pct": round(100.0 * correct / count, 2) if count else None,
        "correct_call_ci95_pct": [round(100.0 * low, 2), round(100.0 * high, 2)] if count else None,
        "meaningful_precision_pct": round(100.0 * meaningful_calls / count, 2) if count else None,
        "direction_accuracy_on_meaningful_pct": round(100.0 * correct / meaningful_calls, 2) if meaningful_calls else None,
        "signed_gap_usd_per_one_unit": round(signed_gap_usd, 4),
        "absolute_called_gap_usd": round(absolute_gap_usd, 4),
    }


def nested_outer_predictions(samples: Sequence[V2Sample], x: np.ndarray, significant: np.ndarray, direction: np.ndarray) -> tuple[list[dict], list[dict]]:
    output: list[dict] = []
    folds: list[dict] = []
    initial_train = 104
    block_size = 26
    for test_start in range(initial_train, len(samples), block_size):
        test_end = min(len(samples), test_start + block_size)
        train_end = test_start - 1
        train = np.arange(train_end)
        test = np.arange(test_start, test_end)
        sig_spec, sig_oof, sig_ranking = inner_model_selection(x[train], significant[train], stage="significant")
        dir_spec, dir_oof, dir_ranking = inner_model_selection(x[train], direction[train], stage="direction")
        policy = choose_policy(significant[train], direction[train], sig_oof, dir_oof)

        sig_model = make_model(sig_spec)
        dir_model = make_model(dir_spec)
        sig_model.fit(x[train], significant[train])
        dir_model.fit(x[train], direction[train])
        sig_probability = sig_model.predict_proba(x[test])[:, 1]
        dir_probability = dir_model.predict_proba(x[test])[:, 1]
        confidence = np.maximum(dir_probability, 1.0 - dir_probability)
        call = (sig_probability >= policy["significant_threshold"]) & (confidence >= policy["direction_threshold"])
        predicted_up = dir_probability >= 0.5

        momentum_index = V2_FEATURE_NAMES.index("xau_ret_1440m")
        momentum_cutoff = float(np.quantile(np.abs(x[train, momentum_index]), 0.70))
        momentum_call = np.abs(x[test, momentum_index]) >= momentum_cutoff
        momentum_up = x[test, momentum_index] >= 0

        fold_samples = [samples[index] for index in test]
        folds.append(
            {
                "train_samples": len(train),
                "test_start_utc": fold_samples[0].record.reopen_utc,
                "test_end_utc": fold_samples[-1].record.reopen_utc,
                "test_samples": len(test),
                "significant_model": asdict(sig_spec),
                "direction_model": asdict(dir_spec),
                "policy": policy,
                "model_result": summarize_calls(fold_samples, call, predicted_up),
                "momentum_result": summarize_calls(fold_samples, momentum_call, momentum_up),
                "top_significant_candidates": sig_ranking,
                "top_direction_candidates": dir_ranking,
            }
        )
        for local, index in enumerate(test):
            sample = samples[index]
            output.append(
                {
                    "sample_index": int(index),
                    "feature_time_utc": sample.record.feature_time_utc,
                    "reopen_utc": sample.record.reopen_utc,
                    "gap_usd": sample.record.gap_usd,
                    "gap_pct": sample.record.gap_pct,
                    "meaningful_threshold_pct": sample.meaningful_threshold_pct,
                    "actual_state": "UP" if sample.meaningful_gap and sample.direction_up else "DOWN" if sample.meaningful_gap else "NO_GAP",
                    "significant_probability": round(float(sig_probability[local]), 6),
                    "direction_probability_up": round(float(dir_probability[local]), 6),
                    "decision": "UP" if call[local] and predicted_up[local] else "DOWN" if call[local] else "NO_TRADE",
                    "called": bool(call[local]),
                    "predicted_up": bool(predicted_up[local]),
                    "momentum_decision": "UP" if momentum_call[local] and momentum_up[local] else "DOWN" if momentum_call[local] else "NO_TRADE",
                    "momentum_called": bool(momentum_call[local]),
                    "momentum_up": bool(momentum_up[local]),
                }
            )
    return output, folds


def _rows_to_metrics(samples: Sequence[V2Sample], rows: Sequence[dict], prefix: str = "") -> dict:
    indices = [row["sample_index"] for row in rows]
    subset = [samples[index] for index in indices]
    call_key = f"{prefix}called" if prefix else "called"
    up_key = f"{prefix}up" if prefix else "predicted_up"
    call = np.asarray([row[call_key] for row in rows], dtype=bool)
    predicted = np.asarray([row[up_key] for row in rows], dtype=bool)
    return summarize_calls(subset, call, predicted)


def _chart(path: Path, yearly: Sequence[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height, margin = 900, 420, 70
    rows = [row for row in yearly if row["model"]["calls"]]
    plot_w, plot_h = width - 2 * margin, height - 2 * margin
    pieces = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#08111f"/>',
        '<text x="70" y="36" fill="#f5f7fb" font-family="Arial" font-size="22" font-weight="700">V2 nested OOS call accuracy</text>',
    ]
    for value in (0, 25, 50, 75, 100):
        y = margin + plot_h * (1.0 - value / 100.0)
        pieces.append(f'<line x1="{margin}" y1="{y:.1f}" x2="{width-margin}" y2="{y:.1f}" stroke="#25334a"/>')
        pieces.append(f'<text x="{margin-10}" y="{y+4:.1f}" text-anchor="end" fill="#91a0b8" font-family="Arial" font-size="12">{value}%</text>')
    if rows:
        bar_w = plot_w / len(rows) * 0.5
        for position, row in enumerate(rows):
            centre = margin + plot_w * (position + 0.5) / len(rows)
            value = row["model"]["correct_call_precision_pct"]
            top = margin + plot_h * (1.0 - value / 100.0)
            color = "#20d6a7" if value >= 55 else "#ff6577"
            pieces.append(f'<rect x="{centre-bar_w/2:.1f}" y="{top:.1f}" width="{bar_w:.1f}" height="{margin+plot_h-top:.1f}" rx="4" fill="{color}"/>')
            pieces.append(f'<text x="{centre:.1f}" y="{top-8:.1f}" text-anchor="middle" fill="#f5f7fb" font-family="Arial" font-size="13">{value:.1f}%</text>')
            pieces.append(f'<text x="{centre:.1f}" y="{height-margin+24:.1f}" text-anchor="middle" fill="#b5c0d2" font-family="Arial" font-size="13">{row["year"]}</text>')
    pieces.append("</svg>")
    path.write_text("\n".join(pieces), encoding="utf-8")


def write_report(payload: dict) -> None:
    result = payload["nested_oos"]["model"]
    momentum = payload["nested_oos"]["momentum_baseline"]
    status = payload["deployment_status"].upper()
    accuracy = "N/A" if result["correct_call_precision_pct"] is None else f"{result['correct_call_precision_pct']:.2f}%"
    direction = "N/A" if result["direction_accuracy_on_meaningful_pct"] is None else f"{result['direction_accuracy_on_meaningful_pct']:.2f}%"
    interval = "N/A" if not result["correct_call_ci95_pct"] else f"{result['correct_call_ci95_pct'][0]:.2f}%-{result['correct_call_ci95_pct'][1]:.2f}%"
    lines = [
        "# Gold Weekend Direction V2",
        "",
        f"**Deployment verdict: {status}.** Rejected models are forced to `NO TRADE` by the predictor.",
        "",
        "V2 predicts whether the weekly reopen gap will be meaningful, then predicts direction. The meaningful threshold is the rolling 70th percentile of the previous 26 absolute weekend gaps, so it adapts to gold's price and volatility without future data.",
        "",
        "## Nested chronological out-of-sample result",
        "",
        "| OOS weeks | Calls | Coverage | Fully correct calls | Call precision | 95% interval | Direction accuracy when meaningful | Signed gap per one unit |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
        f"| {result['samples']} | {result['calls']} | {result['coverage_pct']:.2f}% | {result['correct_calls']} | {accuracy} | {interval} | {direction} | ${result['signed_gap_usd_per_one_unit']:+.2f} |",
        "",
        "A fully correct call must both identify a meaningful gap and predict its direction. A direction call on a small/noisy gap counts as incorrect.",
        "",
        "## Momentum baseline",
        "",
        "| Calls | Coverage | Call precision | Direction accuracy when meaningful | Signed gap per one unit |",
        "|---:|---:|---:|---:|---:|",
        f"| {momentum['calls']} | {momentum['coverage_pct']:.2f}% | {momentum['correct_call_precision_pct']}% | {momentum['direction_accuracy_on_meaningful_pct']}% | ${momentum['signed_gap_usd_per_one_unit']:+.2f} |",
        "",
        "## Year breakdown",
        "",
        "| Year | OOS weeks | Calls | Call precision | Meaningful precision | Direction accuracy | Signed gap |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in payload["yearly"]:
        item = row["model"]
        call_accuracy = "N/A" if item["correct_call_precision_pct"] is None else f"{item['correct_call_precision_pct']:.2f}%"
        meaningful = "N/A" if item["meaningful_precision_pct"] is None else f"{item['meaningful_precision_pct']:.2f}%"
        direction_accuracy = "N/A" if item["direction_accuracy_on_meaningful_pct"] is None else f"{item['direction_accuracy_on_meaningful_pct']:.2f}%"
        lines.append(f"| {row['year']} | {item['samples']} | {item['calls']} | {call_accuracy} | {meaningful} | {direction_accuracy} | ${item['signed_gap_usd_per_one_unit']:+.2f} |")
    lines.extend(
        [
            "",
            "![Nested OOS call accuracy](charts/weekend-direction-v2/oos-call-accuracy.svg)",
            "",
            "## Inputs",
            "",
            f"- {len(MARKET_FEATURES)} compact MT5 market and lagged weekend-history features from completed bars.",
            "- Nine lagged FRED macro features: broad USD, real yields, nominal yields, VIX, and breakevens.",
            "- Four CFTC gold-positioning features, conservatively lagged one full week to avoid holiday publication leakage.",
            "- No CVOL/options-skew history was available locally, so no options values were invented.",
            "",
            "## Validation design",
            "",
            "- The outer replay starts after 104 weeks and advances in 26-week unseen blocks.",
            "- Each outer block independently selects regularization, feature set, and confidence gates using only nested training folds.",
            "- Every inner and outer boundary uses a one-week embargo.",
            "- V1's old final year was not used to choose a single global V2 configuration.",
            "- Because V2 was designed after seeing V1 fail, this is rigorous nested OOS evidence but not a pristine future trial. New weekends remain the final confirmation.",
            "",
            "Promotion requires at least 20 calls, at least 60% fully correct call precision, at least 60% direction accuracy on meaningful gaps, positive signed gap capture, and positive results in all but at most one tested calendar year. More tuning on these same OOS weeks would invalidate them as independent evidence.",
            "",
            "This remains an informational direction model, not an executable P&L backtest. Signed-gap dollars show the midpoint direction captured by one unit and do not include order slippage, margin, or weekend execution constraints.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(refresh_context: bool = False) -> dict:
    market, market_metadata = _load_cache()
    base_records = build_weekend_dataset(market["XAUUSD"], {key: value for key, value in market.items() if key != "XAUUSD"})
    macro = load_macro_context(refresh=refresh_context)
    cot = fetch_gold_cot(refresh=refresh_context)
    samples = build_v2_samples(base_records, macro, cot)
    x, significant, direction = samples_to_arrays(samples)

    predictions, folds = nested_outer_predictions(samples, x, significant, direction)
    model_result = _rows_to_metrics(samples, predictions)
    momentum_result = _rows_to_metrics(samples, predictions, prefix="momentum_")
    sig_prob = np.asarray([row["significant_probability"] for row in predictions], dtype=float)
    dir_prob = np.asarray([row["direction_probability_up"] for row in predictions], dtype=float)
    indices = np.asarray([row["sample_index"] for row in predictions], dtype=int)

    years = sorted({datetime.fromisoformat(row["reopen_utc"]).year for row in predictions})
    yearly = []
    for year in years:
        year_rows = [row for row in predictions if datetime.fromisoformat(row["reopen_utc"]).year == year]
        yearly.append(
            {
                "year": year,
                "model": _rows_to_metrics(samples, year_rows),
                "momentum": _rows_to_metrics(samples, year_rows, prefix="momentum_"),
            }
        )

    positive_years = sum(row["model"]["signed_gap_usd_per_one_unit"] > 0 for row in yearly)
    validated = bool(
        model_result["calls"] >= 20
        and model_result["correct_call_precision_pct"] is not None
        and model_result["correct_call_precision_pct"] >= 60.0
        and model_result["direction_accuracy_on_meaningful_pct"] is not None
        and model_result["direction_accuracy_on_meaningful_pct"] >= 60.0
        and model_result["signed_gap_usd_per_one_unit"] > 0
        and positive_years >= max(2, len(yearly) - 1)
    )

    sig_spec, sig_oof, sig_ranking = inner_model_selection(x, significant, stage="significant")
    dir_spec, dir_oof, dir_ranking = inner_model_selection(x, direction, stage="direction")
    final_policy = choose_policy(significant, direction, sig_oof, dir_oof)
    sig_model = make_model(sig_spec).fit(x, significant)
    dir_model = make_model(dir_spec).fit(x, direction)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "significant_model": sig_model,
            "direction_model": dir_model,
            "significant_spec": asdict(sig_spec),
            "direction_spec": asdict(dir_spec),
            "policy": final_policy,
            "feature_names": list(V2_FEATURE_NAMES),
            "meaningful_quantile": 0.70,
            "threshold_history": 26,
            "validated": validated,
            "purpose": "Prediction only; never sends orders",
            "trained_through_utc": samples[-1].record.feature_time_utc,
        },
        MODEL_PATH,
    )

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "deployment_status": "validated" if validated else "rejected",
        "sample": {
            "first_utc": samples[0].record.reopen_utc,
            "last_utc": samples[-1].record.reopen_utc,
            "samples": len(samples),
            "outer_warmup": 104,
            "nested_oos_samples": len(predictions),
            "meaningful_gap_rate_pct": round(100.0 * float(np.mean(significant)), 2),
        },
        "data": {
            "broker": market_metadata,
            "fred_series": list(MACRO_FEATURES),
            "cftc_gold_rows": len(cot),
            "cftc_safe_lag_days": 7,
            "options_skew": "unavailable; excluded",
        },
        "nested_oos": {
            "model": model_result,
            "momentum_baseline": momentum_result,
            "significant_detector": probability_metrics(significant[indices], sig_prob),
            "direction_model": probability_metrics(direction[indices], dir_prob),
        },
        "yearly": yearly,
        "outer_folds": folds,
        "final_refit": {
            "significant_spec": asdict(sig_spec),
            "direction_spec": asdict(dir_spec),
            "policy": final_policy,
            "top_significant_candidates": sig_ranking,
            "top_direction_candidates": dir_ranking,
        },
        "predictions": predictions,
    }
    JSON_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0].keys()))
        writer.writeheader()
        writer.writerows(predictions)
    _chart(CHART_PATH, yearly)
    write_report(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Nested walk-forward XAUUSD weekend-direction V2 research")
    parser.add_argument("--refresh-context", action="store_true")
    args = parser.parse_args()
    payload = run(refresh_context=args.refresh_context)
    result = payload["nested_oos"]["model"]
    print(f"Deployment status: {payload['deployment_status'].upper()}")
    print(f"Nested OOS: {result['calls']} calls, {result['correct_call_precision_pct']}% fully correct")
    print(f"Direction accuracy on meaningful calls: {result['direction_accuracy_on_meaningful_pct']}%")
    print(f"Signed midpoint gap per one unit: ${result['signed_gap_usd_per_one_unit']:+.2f}")
    print(f"Report: {REPORT_PATH}")


if __name__ == "__main__":
    main()
