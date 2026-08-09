from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from pathlib import Path

import joblib

from news_core import ROOT
from news_v5 import CPI_POLICY, cpi_regime_prediction


V4_REPORT = ROOT / "news_v4_3m_results.json"
V4_MODEL = ROOT / "models" / "gold_news_v4.joblib"
OUTPUT_JSON = ROOT / "news_v5_3m_results.json"
OUTPUT_CSV = ROOT / "news_v5_3m_results.csv"
OUTPUT_MD = ROOT / "NEWS_V5_3M_RESULTS.md"
MODEL_PATH = ROOT / "models" / "gold_news_v5.joblib"
HISTORY_PATH = ROOT / "gold_direction_5y.json"


def _wilson(wins: int, calls: int) -> list[float]:
    if calls == 0:
        return [0.0, 0.0]
    z = 1.959963984540054
    p = wins / calls
    denominator = 1 + z * z / calls
    center = (p + z * z / (2 * calls)) / denominator
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * calls)) / calls) / denominator
    return [round(100 * (center - margin), 2), round(100 * (center + margin), 2)]


def _metrics(rows: list[dict], key: str) -> dict:
    called = [row for row in rows if row.get(key) not in {None, "NO CALL"}]
    wins = sum(row[key] == row["actual"] for row in called)
    return {
        "events": len(rows),
        "calls": len(called),
        "wins": wins,
        "losses": len(called) - wins,
        "accuracy_pct": round(100 * wins / len(called), 2) if called else 0.0,
        "coverage_pct": round(100 * len(called) / len(rows), 2) if rows else 0.0,
        "wilson_95_pct": _wilson(wins, len(called)),
    }


def _seed_history() -> dict[str, list[str]]:
    payload = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    history: dict[str, list[str]] = defaultdict(list)
    for row in payload["events"]:
        if row["release_utc"] >= "2026-05-08T00:00:00+00:00":
            continue
        history[row["event"]].append(
            "BUY" if row["actual_gold_impact"] == "POSITIVE" else "SELL"
        )
    return history


def _pre_holdout_evidence() -> dict:
    direction = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))["events"]
    cpi = [
        row
        for row in direction
        if row["event"] == "CPI"
        and row["release_utc"] < "2026-05-08T00:00:00+00:00"
    ]
    fomc_payload = json.loads(
        (ROOT / "fomc_frozen_holdout.json").read_text(encoding="utf-8")
    )
    fomc = [
        row
        for row in fomc_payload["events"]
        if row["release_utc"] < "2026-05-08T00:00:00+00:00"
        and row.get("agreement_prediction")
    ]
    cpi_wins = sum(row["actual_gold_impact"] == "POSITIVE" for row in cpi)
    fomc_wins = sum(
        row["agreement_prediction"] == row["actual_gold_impact"]
        for row in fomc
    )
    return {
        "cpi_positive_regime": {
            "calls": len(cpi),
            "wins": cpi_wins,
            "accuracy_pct": round(100 * cpi_wins / len(cpi), 2),
        },
        "fomc_agreement": {
            "calls": len(fomc),
            "wins": fomc_wins,
            "accuracy_pct": round(100 * fomc_wins / len(fomc), 2),
        },
        "combined": {
            "calls": len(cpi) + len(fomc),
            "wins": cpi_wins + fomc_wins,
            "accuracy_pct": round(
                100 * (cpi_wins + fomc_wins) / (len(cpi) + len(fomc)),
                2,
            ),
        },
    }


def _promote_artifact() -> None:
    artifact = joblib.load(V4_MODEL)
    artifact.update(
        {
            "artifact_version": 5,
            "cpi_regime_policy": dict(CPI_POLICY),
            "nfp_pre_release_calls_enabled": False,
            "policy_note": (
                "CPI positive-regime calls, selective FOMC agreement calls, "
                "and NFP shadow bias only. T-30 is preliminary only."
            ),
        }
    )
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, MODEL_PATH)


def run() -> dict:
    if not V4_REPORT.exists() or not V4_MODEL.exists():
        raise FileNotFoundError(
            "Run backtest_news_v4.py once before building the V5 comparison."
        )
    base = json.loads(V4_REPORT.read_text(encoding="utf-8"))
    history = _seed_history()
    events = []
    for source in base["events"]:
        row = dict(source)
        event = row["event"]
        if event == "CPI":
            decision = cpi_regime_prediction(history[event])
            prediction = (
                "POSITIVE" if decision["prediction"] == "BUY" else "NO CALL"
            )
            row.update(
                {
                    "v5_prediction": prediction,
                    "v5_bias": "POSITIVE",
                    "v5_confidence_pct": round(100 * decision["confidence"], 2),
                    "v5_strategy": decision["strategy"],
                    "v5_failed_gates": decision["failed_gates"],
                }
            )
        elif event == "FOMC":
            row.update(
                {
                    "v5_prediction": row["t15_prediction"],
                    "v5_bias": row["t15_bias"],
                    "v5_confidence_pct": row["t15_confidence_pct"],
                    "v5_strategy": "fomc_history_model_agreement",
                    "v5_failed_gates": row["t15_failed_gates"],
                }
            )
        else:
            row.update(
                {
                    "v5_prediction": "NO CALL",
                    "v5_bias": row["t15_bias"],
                    "v5_confidence_pct": row["t15_confidence_pct"],
                    "v5_strategy": "nfp_shadow_bias_only",
                    "v5_failed_gates": ["nfp_pre_release_edge"],
                }
            )
        events.append(row)
        history[event].append("BUY" if row["actual"] == "POSITIVE" else "SELL")

    evidence = _pre_holdout_evidence()
    report = {
        "status": "promoted_for_forward_validation",
        "methodology": {
            "window": "2026-05-08 through 2026-08-07",
            "events": ["NFP", "CPI", "FOMC"],
            "target": "Sign of the XAUUSD release-minute bid/ask midpoint move.",
            "v5_policy": (
                "CPI calls POSITIVE only while preselected long-run and recent "
                "positive-regime gates pass. FOMC retains V4 history/model agreement. "
                "NFP is shadow-bias only."
            ),
            "researcher_warning": (
                "V5 was designed after the May-August outcomes were available. The "
                "event replay is retrospective, not a pristine unseen holdout. Its "
                "next releases are the true forward test."
            ),
        },
        "pre_holdout_evidence": evidence,
        "metrics": {
            "v4_final": _metrics(events, "t15_prediction"),
            "v5_final": _metrics(events, "v5_prediction"),
        },
        "events": events,
    }
    OUTPUT_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        fields = [
            "release_utc", "event", "v5_prediction", "v5_bias",
            "v5_confidence_pct", "v5_strategy", "actual", "release_move_usd",
            "v5_failed_gates",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(events)

    metrics = report["metrics"]
    lines = [
        "# Gold News Direction V5 - Three-Month Retrospective",
        "",
        "> V5 was designed after this period. These results are retrospective; the next releases are the true forward test.",
        "",
        "| Policy | Calls | Wins | Accuracy | Coverage |",
        "|---|---:|---:|---:|---:|",
        f"| V4 final | {metrics['v4_final']['calls']} | {metrics['v4_final']['wins']} | {metrics['v4_final']['accuracy_pct']:.2f}% | {metrics['v4_final']['coverage_pct']:.2f}% |",
        f"| V5 final | {metrics['v5_final']['calls']} | {metrics['v5_final']['wins']} | {metrics['v5_final']['accuracy_pct']:.2f}% | {metrics['v5_final']['coverage_pct']:.2f}% |",
        "",
        "| Date | Event | V5 final | Actual | Move |",
        "|---|---|---|---|---:|",
    ]
    for row in events:
        lines.append(
            f"| {row['release_utc'][:10]} | {row['event']} | {row['v5_prediction']} | "
            f"{row['actual']} | {row['release_move_usd']:+.3f} USD |"
        )
    lines.extend(
        [
            "",
            "## Pre-holdout evidence",
            "",
            f"- CPI positive regime: {evidence['cpi_positive_regime']['wins']}/{evidence['cpi_positive_regime']['calls']} ({evidence['cpi_positive_regime']['accuracy_pct']:.2f}%).",
            f"- FOMC agreement: {evidence['fomc_agreement']['wins']}/{evidence['fomc_agreement']['calls']} ({evidence['fomc_agreement']['accuracy_pct']:.2f}%).",
            f"- Combined: {evidence['combined']['wins']}/{evidence['combined']['calls']} ({evidence['combined']['accuracy_pct']:.2f}%).",
            "- NFP remains no-call before publication because no stable pre-release directional edge survived validation.",
        ]
    )
    OUTPUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    _promote_artifact()
    return report


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
