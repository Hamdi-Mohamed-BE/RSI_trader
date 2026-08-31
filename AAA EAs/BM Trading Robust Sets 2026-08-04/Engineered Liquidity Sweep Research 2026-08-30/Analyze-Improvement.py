from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPORTS = ROOT / "Improvement Reports"
OUTPUT = ROOT / "IMPROVEMENT RESULTS.json"
BASE_ANALYZER = ROOT / "Analyze-Engineered-Liquidity.py"

spec = importlib.util.spec_from_file_location("els_analyzer", BASE_ANALYZER)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def score(row: dict) -> float:
    if row["trades"] < 25 or row["profit_factor"] <= 0:
        return -10_000 + row["trades"]
    return row["return_pct"] + 12 * (min(row["profit_factor"], 3) - 1) - 0.55 * row["equity_dd_pct"]


rows: list[dict] = []
for path in sorted(REPORTS.glob("*.htm")):
    parts = path.stem.split("--")
    if len(parts) != 3:
        continue
    slug, case, phase = parts
    parsed = module.parse_report(path)
    chart = path.with_suffix(".png")
    row = {
        "symbol": {"xauusd": "XAUUSD", "btcusd": "BTCUSD"}[slug],
        "case": case,
        "phase": phase,
        "from_date": "2024-08-29" if phase == "development" else "2025-08-29",
        "to_date": "2025-08-28" if phase == "development" else "2026-08-28",
        "return_pct": parsed["return_pct"],
        "profit_factor": parsed["profit_factor"],
        "win_rate_pct": parsed["win_rate_pct"],
        "equity_dd_pct": parsed["equity_dd_pct"],
        "trades": parsed["trades"],
        "final": parsed["final"],
        "net": parsed["net"],
        "history_quality": parsed["history_quality"],
        "report_path": str(path),
        "chart_path": str(chart),
    }
    rows.append(row)
    module.plot_curve(parsed, chart, f"{row['symbol']} {case} — {phase}")

for symbol in ("XAUUSD", "BTCUSD"):
    development = [
        row
        for row in rows
        if row["symbol"] == symbol
        and row["phase"] == "development"
        and not row["case"].startswith("safe-")
    ]
    winner = max(development, key=score)
    for row in rows:
        if row["symbol"] == symbol:
            row["development_selected"] = row["case"] == winner["case"]
            row["production_applied"] = row["case"] == (
                "rr2" if symbol == "XAUUSD" else "displacement"
            ) or row["case"] == (
                "safe-rr2" if symbol == "XAUUSD" else "safe-displacement"
            )

OUTPUT.write_text(json.dumps(rows, indent=2), encoding="utf-8")
print(json.dumps([
    {key: row[key] for key in ("symbol", "case", "phase", "return_pct", "profit_factor", "win_rate_pct", "equity_dd_pct", "trades", "development_selected")}
    for row in rows
], indent=2))
