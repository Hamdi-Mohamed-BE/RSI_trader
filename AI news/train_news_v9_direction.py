from __future__ import annotations

import json

import joblib

from news_core import ROOT, build_samples
from news_v4 import SelectivePolicy
from news_v9_direction import fit_live_artifact


V4_MODEL = ROOT / "models" / "gold_news_v4.joblib"
OUTPUT_MODEL = ROOT / "models" / "gold_news_v9_direction.joblib"


def run() -> dict:
    frozen = joblib.load(V4_MODEL)
    policies = {
        int(lead): {
            event: SelectivePolicy(**values)
            for event, values in event_policies.items()
        }
        for lead, event_policies in frozen["policies_by_lead"].items()
    }
    rows_by_lead = {lead: build_samples(lead)[0] for lead in (15, 30)}
    artifact = fit_live_artifact(rows_by_lead, policies)
    OUTPUT_MODEL.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, OUTPUT_MODEL)
    return {
        "status": "ok",
        "artifact_version": artifact["artifact_version"],
        "trained_through": artifact["trained_through"],
        "output": str(OUTPUT_MODEL),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
