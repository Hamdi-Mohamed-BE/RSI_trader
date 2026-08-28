from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
PARSER_PATH = PACKAGE / "BAT Portfolio Backtest 2026-08-09" / "Build-BAT-Portfolio-Report.py"
REPORT_ROOT = PACKAGE / "_Backtests" / "MT5-DMC-20260811" / "reports" / "selected-regime-20260828"

spec = importlib.util.spec_from_file_location("mt5_report_parser", PARSER_PATH)
parser = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(parser)

CASES = [
    {"id": "asia", "label": "Asia Breakout", "symbol": "XAUUSD", "period": "H1", "chart": "XAUUSD H1", "set_source": "embedded Markov filter"},
    {"id": "dmc", "label": "DmC", "symbol": "XAUUSD", "period": "H1", "chart": "XAUUSD H1", "set_source": "embedded Markov filter"},
    {"id": "xau-weakness", "label": "XAU Weakness", "symbol": "XAUUSD", "period": "M15", "chart": "XAUUSD M15", "set_source": "embedded Markov filter"},
]


def main() -> None:
    rows = []
    for case in CASES:
        parsed = parser.parse_report(REPORT_ROOT / f"{case['id']}.htm", case)
        parsed.pop("deals", None)
        rows.append(parsed)
    (ROOT / "native-filter-validation.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = [
        "# Native MT5 validation — individually embedded Markov filters",
        "",
        "| EA | Return | PF | Win rate | Equity DD | Trades | Quality |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['label']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | {row['history_quality']} |"
        )
    (ROOT / "NATIVE FILTER VALIDATION.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
