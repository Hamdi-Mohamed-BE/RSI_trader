from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path


def load_main(root: Path):
    spec = importlib.util.spec_from_file_location("crt_analysis", root / "Analyze-CRT.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    analysis = load_main(args.output)
    charts = args.output / "Charts"
    rows = []
    for path in sorted(args.reports.glob("*.htm")):
        match = re.match(r"^(xauusd|usdjpy)--(.+)--assetlocked\.htm$", path.name, re.I)
        if not match:
            continue
        slug, variant = match.group(1).lower(), match.group(2)
        label, group = analysis.SYMBOLS[slug]
        row = analysis.parse_report(path)
        row.update({"symbol": label, "group": group, "slug": slug, "variant": variant})
        row["verdict"] = analysis.verdict(row)
        analysis.plot_curve(row, charts / f"{slug}-asset-specific-locked-equity.png", f"{label} — asset-specific CRT locked 2025-08-29 to 2026-08-28")
        rows.append({key: value for key, value in row.items() if key != "deals"})
    (args.output / "ASSET SPECIFIC RESULTS.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    lines = [
        "# CRT asset-specific locked exceptions",
        "",
        "Only development-positive configurations not already represented by the universal locked test were retested here.",
        "",
        "| Verdict | Market | Variant | Return | PF | Win rate | Equity DD | Trades | Final |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['verdict']} | {row['symbol']} | {row['variant']} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | "
            f"{row['win_rate_pct']:.2f}% | {row['equity_dd_pct']:.2f}% | {row['trades']} | ${row['final']:,.2f} |"
        )
    (args.output / "ASSET SPECIFIC RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
