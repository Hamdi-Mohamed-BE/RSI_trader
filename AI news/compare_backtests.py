from __future__ import annotations

import csv
import json
from pathlib import Path

from news_core import ROOT


BASELINE_REPORT = ROOT / "backtest_report_baseline_v1.json"
BASELINE_DETAILS = ROOT / "backtest_validation_predictions_baseline_v1.csv"
CURRENT_REPORT = ROOT / "backtest_report.json"
CURRENT_DETAILS = ROOT / "backtest_validation_predictions.csv"
OUTPUT_JSON = ROOT / "backtest_comparison.json"
OUTPUT_MD = ROOT / "BACKTEST_COMPARISON.md"
OFFICIAL_TEXT_REPORT = ROOT.parent / "news AI" / "news_official_text_hybrid_report.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_details(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def pooled(rows: list[dict]) -> dict:
    called = [row for row in rows if row["prediction"] != "UNCERTAIN"]
    correct = sum(row["prediction"] == row["actual_impulse"] for row in called)
    return {
        "calls": len(called),
        "correct": correct,
        "directional_accuracy_pct": round(100 * correct / len(called), 2) if called else 0.0,
    }


def model_rows(report: dict) -> list[dict]:
    rows = []
    for model in report["models"]:
        validation = model["selected_validation"]
        rows.append(
            {
                "lead_minutes": model["lead_minutes"],
                "model": model["selected_model"],
                "feature_profile": model.get("selected_feature_profile", "legacy"),
                "threshold": model["selected_threshold"],
                "calls": validation["called_predictions"],
                "coverage_pct": validation["coverage_pct"],
                "directional_accuracy_pct": validation["directional_call_accuracy_pct"],
                "brier_multiclass": validation["brier_multiclass"],
            }
        )
    return rows


def run() -> dict:
    baseline = load_json(BASELINE_REPORT)
    current = load_json(CURRENT_REPORT)
    baseline_models = model_rows(baseline)
    current_models = model_rows(current)
    comparisons = []
    for old, new in zip(baseline_models, current_models):
        comparisons.append(
            {
                "lead_minutes": new["lead_minutes"],
                "baseline": old,
                "improved": new,
                "accuracy_change_points": round(
                    new["directional_accuracy_pct"] - old["directional_accuracy_pct"],
                    2,
                ),
                "coverage_change_points": round(new["coverage_pct"] - old["coverage_pct"], 2),
                "call_change": new["calls"] - old["calls"],
                "brier_change": round(new["brier_multiclass"] - old["brier_multiclass"], 5),
            }
        )

    baseline_pooled = pooled(load_details(BASELINE_DETAILS))
    improved_pooled = pooled(load_details(CURRENT_DETAILS))
    statement_validation = None
    if OFFICIAL_TEXT_REPORT.exists():
        text_report = load_json(OFFICIAL_TEXT_REPORT)
        statement_validation = {
            "selected_model": text_report.get("selected_model"),
            "validation": text_report.get("selected_validation"),
            "deployment_recommendation": text_report.get("deployment_recommendation"),
            "timing": "Entry one minute after release; not a pre-release forecast.",
        }

    result = {
        "methodology": {
            "same_data": True,
            "calendar_releases": current["models"][0]["audit"]["calendar_events"],
            "usable_releases": current["models"][0]["audit"]["usable_samples"],
            "train_samples": current["models"][0]["train_samples"],
            "final_holdout_samples": current["models"][0]["validation_samples"],
            "holdout_start": current["models"][0]["test_start"],
            "leakage_rule": (
                "Every pre-release feature is timestamped before release. Actual, forecast surprise, "
                "revisions, and statement text are excluded from this backtest."
            ),
        },
        "per_lead": comparisons,
        "pooled": {
            "baseline": baseline_pooled,
            "improved": improved_pooled,
            "accuracy_change_points": round(
                improved_pooled["directional_accuracy_pct"]
                - baseline_pooled["directional_accuracy_pct"],
                2,
            ),
            "call_change": improved_pooled["calls"] - baseline_pooled["calls"],
        },
        "post_release_statement_research": statement_validation,
        "conclusion": (
            "Use the enhanced profile at T-15 and retain the legacy profile at T-30. "
            "The official-statement layer remains post-release confirmation only."
        ),
    }
    OUTPUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")

    lines = [
        "# Backtest Comparison",
        "",
        "Same 716-release archive, same chronological training period, and same final holdout.",
        "",
        "| Lead | Version | Profile | Calls | Coverage | Accuracy | Brier |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for comparison in comparisons:
        for label, key in (("Baseline", "baseline"), ("Improved", "improved")):
            row = comparison[key]
            lines.append(
                f"| {row['lead_minutes']}m | {label} | {row['feature_profile']} | "
                f"{row['calls']} | {row['coverage_pct']:.2f}% | "
                f"{row['directional_accuracy_pct']:.2f}% | {row['brier_multiclass']:.5f} |"
            )
    lines.extend(
        [
            "",
            f"Pooled called accuracy: **{baseline_pooled['directional_accuracy_pct']:.2f}% "
            f"({baseline_pooled['correct']}/{baseline_pooled['calls']})** to "
            f"**{improved_pooled['directional_accuracy_pct']:.2f}% "
            f"({improved_pooled['correct']}/{improved_pooled['calls']})**.",
            "",
            "The T-15 gain comes with lower coverage. T-30 keeps the stable legacy feature profile. "
            "Official release text is analyzed only after publication and is not credited to the "
            "pre-release result.",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
