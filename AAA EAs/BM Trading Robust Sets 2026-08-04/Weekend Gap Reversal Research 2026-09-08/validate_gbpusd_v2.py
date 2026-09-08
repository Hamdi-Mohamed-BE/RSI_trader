"""Re-run the complete weekend-gap pipeline for GBPUSD after the timing audit."""
from __future__ import annotations

from datetime import datetime, timezone
import json

import full_pipeline as pipeline


def main() -> int:
    pipeline.prepare_weekly()
    base, weekly, meta = pipeline.load("GBPUSD")
    row = pipeline.select("GBPUSD", base, weekly, meta)
    row["monte_carlo"] = pipeline.monte_carlo(row["locked"]["trades_data"])
    row["promoted"], row["gate_failures"] = pipeline.gate(row)
    payload = {
        "strategy": "Weekend gap overreaction reversal - corrected causal confirmation timing",
        "model_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "risk_per_trade_pct": 1.0,
        "source": "https://irep.ntu.ac.uk/id/eprint/35555/",
        "results": [row],
    }
    pipeline.dump(pipeline.ROOT / "gbpusd-v2-results.json", payload)
    report = pipeline.report(payload).replace(
        "# Weekend Gap Reversal - Full Pipeline Report",
        "# Weekend Gap Reversal - GBPUSD Corrected Timing Audit",
    )
    (pipeline.ROOT / "GBPUSD V2 TIMING AUDIT.md").write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
