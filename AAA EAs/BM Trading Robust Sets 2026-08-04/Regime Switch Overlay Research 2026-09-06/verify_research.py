"""Independent invariants for the regime overlay research."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np

import research


ROOT = Path(__file__).resolve().parent


def main() -> int:
    results = json.loads((ROOT / "results.json").read_text(encoding="utf-8"))
    checks = []
    checks.append((set(results) == set(research.SYMBOLS), "all four required symbols, including XAGUSD"))
    checks.append((len(__import__("pandas").read_csv(ROOT / "all-screen-results.csv")) == 5380, "all 5,380 configuration rows saved"))
    for symbol in research.SYMBOLS:
        config = research.Config(**results[symbol]["selected"])
        close = research.load_prices(symbol)
        full = research.forecasts(close, config)
        prefix_close = close.loc[:"2025-01-15"]
        prefix = research.forecasts(prefix_close, config)
        common = prefix.index[-1]
        causal = np.allclose(prefix.loc[common].to_numpy(float), full.loc[common].to_numpy(float), atol=1e-12)
        checks.append((causal, f"{symbol} forecast unchanged when future prices are removed"))
        momentum, snapback = research.ledgers(symbol, "locked")
        selected = research.select_non_overlapping(research.attach_forecast(momentum + snapback, full), config, research.LOCKED)
        recomputed = research.metrics(selected)
        saved = results[symbol]["selected_locked"]
        checks.append((recomputed["trades"] == saved["trades"] and abs(recomputed["return_pct"] - saved["return_pct"]) < 1e-10, f"{symbol} locked ledger reproduces saved count and return"))
        checks.append((all(research.LOCKED[0] <= x["entry"] < research.LOCKED[1] for x in selected), f"{symbol} locked trades remain inside untouched interval"))
    checks.append((all(not results[s]["promotion_pass"] for s in research.SYMBOLS), "no production auto-promotion"))
    failed = [name for passed, name in checks if not passed]
    lines = [("PASS " if passed else "FAIL ") + name for passed, name in checks]
    lines.append(f"SUMMARY {len(checks)-len(failed)}/{len(checks)} checks passed")
    (ROOT / "VERIFICATION.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

