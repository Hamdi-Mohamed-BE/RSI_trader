"""Generate ONLY the Nasdaq 5M DI-filter ("dynamic" slot) website evidence cache (2026-09-25).

Uses the EA Store's own tools/precompute_evidence_cache.py functions (run_native -> isolated tester
_Backtests/MT5-DMC-20260811 via app.mt5_evidence_jobs; product_payload; write_json) for the DI mode only,
so the existing Standard/Safe caches are not regenerated as a side effect. Windows end on 2026-09-07, the same
end date as the current Nasdaq 5M Standard cache. The portfolio is NOT rebuilt here; run
`tools/precompute_evidence_cache.py --portfolio-only` afterwards.
Run with EA_STORE_DISABLE_MT5=1 so the live-monitor module never attaches to a terminal.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

assert os.getenv("EA_STORE_DISABLE_MT5") == "1", "Set EA_STORE_DISABLE_MT5=1"
STORE = Path(__file__).resolve().parents[2] / "EA store"
sys.path.insert(0, str(STORE))
sys.path.insert(0, str(STORE / "tools"))
import precompute_evidence_cache as P  # noqa: E402

END = date(2026, 9, 7)
product = next(p for p in P.get_sellable_catalog() if p.slug == "nasdaq-5m-candle-momentum")
assert product.dynamic_mode_supported and "DI EA" in str(product.dynamic_expert_source), product.dynamic_expert_source
print("DI expert:", product.dynamic_expert_source, "| set:", product.dynamic_set_source, flush=True)
for period, months in P.PERIOD_MONTHS.items():
    start = P.subtract_months(END, months)
    report = P.run_native(product, "dynamic", period, start, END, force=False)
    payload, trades = P.product_payload(product, "dynamic", period, start, END, report)
    P.write_json(P.product_cache_path(product.slug, "dynamic", period), payload)
    P.write_json(P.product_trades_path(product.slug, "dynamic", period), trades)
    s = payload["stats"]
    print(f"DONE dynamic {period} {payload['period']}: {s.get('return_pct')}% | PF {s.get('profit_factor')} | "
          f"WR {s.get('win_rate_pct')}% | DD {s.get('max_drawdown_pct')}% | {len(trades)} trades | HQ {s.get('history_quality')}", flush=True)
