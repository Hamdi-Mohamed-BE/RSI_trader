from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, timezone

import joblib

from fomc_pipeline import (
    FOMC_HISTORY_RULE,
    FOMC_AGREEMENT_CONFIDENCE,
    binary_gold_direction,
    combine_fomc_decision,
    fit_fomc_model,
    make_fomc_model,
    model_probability_positive,
    pricing_context,
)
from gold_direction_rules import rule_direction
from news_core import ROOT, build_samples


START = date(2021, 7, 30)
RECENT_START = date(2024, 7, 30)
END = date(2026, 7, 30)
OUTPUT_JSON = ROOT / "fomc_pipeline_backtest.json"
OUTPUT_CSV = ROOT / "fomc_pipeline_backtest.csv"
OUTPUT_MD = ROOT / "FOMC_PIPELINE_RESULTS.md"
MODEL_PATH = ROOT / "models" / "gold_news_direction.joblib"
PRICING_PATH = ROOT / "data" / "fomc_pricing_snapshots.csv"


def _date(row: dict) -> date:
    return date.fromisoformat(row["release_utc"][:10])


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
        row for row in rows
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


def _pricing_snapshots() -> dict[str, dict]:
    if not PRICING_PATH.exists():
        return {}
    output = {}
    with PRICING_PATH.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            release = datetime.fromisoformat(
                row["release_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            observed = datetime.fromisoformat(
                row["observed_at_utc"].replace("Z", "+00:00")
            ).astimezone(timezone.utc)
            if observed >= release:
                raise ValueError(
                    "FOMC pricing snapshots must be observed before release: "
                    f"{row['release_utc']}"
                )
            output[row["release_utc"]] = pricing_context(
                current_lower=float(row["current_lower_pct"]),
                current_upper=float(row["current_upper_pct"]),
                cut_25_probability=float(row["cut_25_probability_pct"]),
                hold_probability=float(row["hold_probability_pct"]),
                hike_25_probability=float(row["hike_25_probability_pct"]),
                cut_50_probability=float(
                    row.get("cut_50_probability_pct") or 0
                ),
                hike_50_probability=float(
                    row.get("hike_50_probability_pct") or 0
                ),
            )
    return output


def replay() -> tuple[list[dict], list[dict]]:
    samples, _ = build_samples(30)
    for row in samples:
        row["binary_target"] = binary_gold_direction(
            float(row["reaction"]["release_move"])
        )
    pricing_by_release = _pricing_snapshots()
    history: dict[str, list[str]] = defaultdict(list)
    output = []
    for row in samples:
        labels = history[row["event"]]
        if (
            row["event"] == "FOMC"
            and START <= _date(row) < END
        ):
            training = [
                item
                for item in samples
                if item["event"] == "FOMC"
                and item["release_utc"] < row["release_utc"]
            ]
            model = fit_fomc_model(training)
            model_probability = model_probability_positive(
                model,
                row["features"],
            )
            pricing = pricing_by_release.get(row["release_utc"])
            ensemble = combine_fomc_decision(
                history_labels=labels,
                model_probability_positive_value=model_probability,
                pricing=pricing,
            )
            history_direction = rule_direction(FOMC_HISTORY_RULE, labels)
            model_direction = (
                "POSITIVE"
                if model_probability >= 0.5
                else "NEGATIVE"
            )
            actual = row["binary_target"]
            output.append(
                {
                    "release_utc": row["release_utc"],
                    "history_prediction": history_direction,
                    "model_prediction": model_direction,
                    "model_probability_positive_pct": round(
                        100 * model_probability,
                        2,
                    ),
                    "components_agree": history_direction == model_direction,
                    "agreement_prediction": (
                        history_direction
                        if history_direction == model_direction
                        else None
                    ),
                    "production_prediction": ensemble["gold_impact"],
                    "confidence_tier": ensemble["confidence_tier"],
                    "confidence_pct": round(
                        100 * ensemble["confidence"],
                        2,
                    ),
                    "resolver": ensemble["resolver"],
                    "pricing_direction": (
                        pricing.get("gold_direction")
                        if pricing
                        else None
                    ),
                    "actual_gold_impact": actual,
                    "actual_move_usd": round(
                        float(row["reaction"]["release_move"]),
                        4,
                    ),
                    "history_correct": history_direction == actual,
                    "model_correct": model_direction == actual,
                    "agreement_correct": (
                        history_direction == actual
                        if history_direction == model_direction
                        else None
                    ),
                    "production_correct": ensemble["gold_impact"] == actual,
                }
            )
        labels.append(row["binary_target"])
    return output, samples


def _window(rows: list[dict], start: date, end: date) -> dict:
    selected = [row for row in rows if start <= _date(row) < end]
    return {
        "all_events": len(selected),
        "history_rule": _metrics(selected, "history_prediction"),
        "t30_model": _metrics(selected, "model_prediction"),
        "agreement_only": _metrics(selected, "agreement_prediction"),
        "full_coverage_production": _metrics(
            selected,
            "production_prediction",
        ),
    }


def _save_production_model(samples: list[dict], report: dict) -> None:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            "Run backtest_gold_direction.py before the FOMC pipeline."
        )
    artifact = joblib.load(MODEL_PATH)
    artifact["artifact_version"] = max(3, int(artifact.get("artifact_version", 1)))
    artifact["fomc_ensemble"] = {
        "version": 1,
        "model": fit_fomc_model(samples),
        "model_feature_count": 18,
        "history_rule": FOMC_HISTORY_RULE,
        "agreement_confidence_cap": FOMC_AGREEMENT_CONFIDENCE,
        "conflict_confidence": 0.52,
        "validated_agreement": report["combined"]["agreement_only"],
        "pricing_requirement": (
            "Optional point-in-time cut/hold/hike probabilities observed "
            "before release. Same-meeting post-release data is prohibited."
        ),
    }
    joblib.dump(artifact, MODEL_PATH)


def run() -> dict:
    rows, samples = replay()
    broad = _window(rows, START, RECENT_START)
    recent = _window(rows, RECENT_START, END)
    combined = _window(rows, START, END)
    pricing_rows = [
        row for row in rows if row["pricing_direction"] is not None
    ]
    report = {
        "methodology": {
            "target": "Sign of the XAUUSD release-minute midpoint move.",
            "history_component": FOMC_HISTORY_RULE,
            "model_component": (
                "Expanding walk-forward FOMC-only ExtraTrees using the first "
                "18 canonical T-30 features. Each event is fitted using only "
                "earlier meetings."
            ),
            "confidence_policy": (
                "History/model agreement is HIGH confidence capped at 65%. "
                "Conflicts are LOW confidence. Point-in-time FedWatch pricing "
                "may resolve direction but cannot lift confidence above 60%."
            ),
            "statement_and_press": (
                "The statement reaction and the press conference 30 minutes "
                "later are separate shocks."
            ),
            "selection_warning": (
                "Every row is generated without future-event leakage, but this "
                "ensemble design was created after reviewing the July 29 miss. "
                "The replay is retrospective, not a pristine untouched test."
            ),
        },
        "broad_2021_2024": broad,
        "recent_2024_2026": recent,
        "combined": combined,
        "pricing_resolver_audit": {
            "historical_rows_available": len(pricing_rows),
            "warning": (
                "The local archive does not contain a complete point-in-time "
                "FedWatch history. Pricing-resolved rows are forensic examples, "
                "not a validated resolver backtest."
            ),
            "rows": pricing_rows,
        },
        "events": rows,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    combined_agreement = combined["agreement_only"]
    recent_agreement = recent["agreement_only"]
    july = next(
        (
            row for row in rows
            if row["release_utc"].startswith("2026-07-29")
        ),
        None,
    )
    lines = [
        "# FOMC Gold Direction Pipeline",
        "",
        "This is a prediction-only, leakage-safe FOMC direction layer.",
        "Each event is replayed using only earlier data. The design itself was "
        "created after the July 29 miss, so these are retrospective results, "
        "not a pristine untouched test.",
        "",
        "## Honest replay",
        "",
        "| Window | FOMC events | History | T-30 model | Agreement calls | Agreement accuracy |",
        "|---|---:|---:|---:|---:|---:|",
        (
            f"| 2021-2024 broad | {broad['all_events']} | "
            f"{broad['history_rule']['accuracy_pct']:.2f}% | "
            f"{broad['t30_model']['accuracy_pct']:.2f}% | "
            f"{broad['agreement_only']['events']} | "
            f"{broad['agreement_only']['accuracy_pct']:.2f}% |"
        ),
        (
            f"| 2024-2026 recent | {recent['all_events']} | "
            f"{recent['history_rule']['accuracy_pct']:.2f}% | "
            f"{recent['t30_model']['accuracy_pct']:.2f}% | "
            f"{recent_agreement['events']} | "
            f"{recent_agreement['accuracy_pct']:.2f}% |"
        ),
        (
            f"| Combined | {combined['all_events']} | "
            f"{combined['history_rule']['accuracy_pct']:.2f}% | "
            f"{combined['t30_model']['accuracy_pct']:.2f}% | "
            f"{combined_agreement['events']} | "
            f"{combined_agreement['accuracy_pct']:.2f}% |"
        ),
        "",
        (
            "Agreement coverage is intentionally selective. Its combined 95% "
            f"interval is {combined_agreement['wilson_95_pct'][0]:.2f}% to "
            f"{combined_agreement['wilson_95_pct'][1]:.2f}%."
        ),
        "",
        "## July 29, 2026 forensic check",
        "",
    ]
    if july:
        lines.extend(
            (
                f"- History component: **{july['history_prediction']}**",
                f"- T-30 model: **{july['model_prediction']}**",
                f"- FedWatch resolver: **{july['pricing_direction'] or 'not available'}**",
                f"- Final low-confidence output: **{july['production_prediction']}**",
                f"- Actual release-minute gold impact: **{july['actual_gold_impact']}** "
                f"({july['actual_move_usd']:+.3f} USD)",
                "",
                "The single pricing-resolved example is not counted as proof. "
                "A licensed or user-supplied point-in-time FedWatch history is "
                "still required to validate that resolver.",
            )
        )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _save_production_model(samples, report)
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
