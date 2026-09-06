from __future__ import annotations

import json
import sys
from pathlib import Path


STORE_ROOT = Path(__file__).resolve().parents[1]
if str(STORE_ROOT) not in sys.path:
    sys.path.insert(0, str(STORE_ROOT))

from app.catalog import get_sellable_catalog  # noqa: E402
from app.evidence_cache import PERIOD_OPTIONS, product_trades_path, write_json  # noqa: E402
from app.trade_metrics import enrich_trades  # noqa: E402


def main() -> int:
    updated = 0
    for product in get_sellable_catalog():
        modes = ["standard"] + (["safe"] if product.safe_filter_supported else [])
        for mode in modes:
            for option in PERIOD_OPTIONS:
                path = product_trades_path(product.slug, mode, option["value"])
                if not path.is_file():
                    continue
                trades = json.loads(path.read_text(encoding="utf-8-sig"))
                write_json(path, enrich_trades(trades, product.slug))
                updated += 1
                print(f"ENRICHED {product.label} | {mode} | {option['value']} | {len(trades)} trades")
    print(f"DONE {updated} cached trade ledgers enriched; no MT5 backtest was run.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
