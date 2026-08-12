from __future__ import annotations

import importlib.util
import csv
import json
import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BUILDER = PACKAGE / "Active BAT Backtest 2026-08-12" / "Build-Active-BAT-Report.py"

spec = importlib.util.spec_from_file_location("active_bat_builder", BUILDER)
builder = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(builder)

builder.ROOT = ROOT
builder.REPORTS = ROOT / "MT5 Reports"
builder.CHARTS = ROOT / "Charts"
builder.MANIFEST = ROOT / "manifest.json"
builder.START_DATE = datetime(2021, 8, 11)
builder.FINISH_DATE = datetime(2026, 8, 10)


def main() -> None:
    builder.main()
    results_path = ROOT / "portfolio-results.json"
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    rows = []
    for result in payload["bots"]:
        final = float(result["final"])
        initial = float(result["initial"])
        cagr = ((final / initial) ** (1.0 / 5.0) - 1.0) * 100.0 if final > 0 and initial > 0 else -100.0
        result["cagr_pct"] = cagr
        rows.append({
            "label": result["label"],
            "chart": result["chart"],
            "return_pct": result["return_pct"],
            "cagr_pct": cagr,
            "equity_dd_pct": result["equity_dd_pct"],
            "profit_factor": result["profit_factor"],
            "win_rate_pct": result["win_rate_pct"],
            "trades": result["trades"],
        })
    combined = payload["combined"]
    combined["cagr_pct"] = (
        (float(combined["final"]) / float(combined["initial"])) ** (1.0 / 5.0) - 1.0
    ) * 100.0
    results_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    annualized_path = ROOT / "five-year-annualized-summary.csv"
    with annualized_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    with (ROOT / "combined-realized-balance.csv").open("r", newline="", encoding="utf-8-sig") as handle:
        minimum_combined_balance = min(float(row["balance"]) for row in csv.DictReader(handle))
    minimum_combined_text = (
        f"-${abs(minimum_combined_balance):,.2f}"
        if minimum_combined_balance < 0
        else f"${minimum_combined_balance:,.2f}"
    )

    execution_rows = []
    tester_log = PACKAGE / "_Backtests" / "MT5-DMC-20260811" / "Tester" / "logs" / "20260812.log"
    current = None
    if tester_log.exists():
        for line in tester_log.read_text(encoding="utf-16", errors="ignore").splitlines():
            start = re.search(
                r"testing of Experts\\BM Trading\\Active BAT 5Y 2026-08-12\\(.+?\.ex5) from .* started with inputs:",
                line,
            )
            if start:
                current = {"ea_file": start.group(1), "failed": 0, "invalid_price": 0, "market_closed": 0, "other": 0}
                continue
            if current is not None and re.search(r"\sfailed (market|buy stop|sell stop|modify)", line):
                current["failed"] += 1
                if "[Invalid price]" in line:
                    current["invalid_price"] += 1
                elif "[Market closed]" in line:
                    current["market_closed"] += 1
                else:
                    current["other"] += 1
                continue
            if current is not None and re.search(r"final balance [0-9.]+ USD", line):
                execution_rows.append(current)
                current = None
    with (ROOT / "execution-rejection-audit.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        fields = ["ea_file", "failed", "invalid_price", "market_closed", "other"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(execution_rows)

    report_path = ROOT / "FULL REPORT.md"
    text = report_path.read_text(encoding="utf-8-sig")
    text = text.replace(
        "# Current active BAT — complete one-year Exness backtest",
        "# Current active BAT — complete five-year Exness backtest",
    )
    text = text.replace("## Invalid active BAT entry\n\n\n", "")
    text = text.replace("## Invalid active BAT entry\n\n", "")
    text = text.replace(
        "- Period: 2025-08-11 through 2026-08-10, the latest complete one-year window.",
        "- Period: 2021-08-11 through 2026-08-10, the latest complete five-year window.",
    )
    text = text.replace(
        "| $10,000.00 | $29,552.64 | $19,552.64 / +195.53% | $17,424.02 / 154.57% | 1.06 | 36.39% | 2663 / 4654 | 7317 |\n",
        "| $10,000.00 | $29,552.64* | $19,552.64* / +195.53%* | $17,424.02 / 154.57% | 1.06 | 36.39% | 2663 / 4654 | 7317 |\n\n"
        f"**Portfolio verdict: FAIL.** The merged curve fell to **{minimum_combined_text}**. A real USD 10,000 account "
        "would have reached ruin/margin stop-out, so the starred final balance and return are only a later arithmetic recovery and are not achievable live.\n",
    )
    text = text.replace(
        "- Model: MT5 Every Tick generated from synchronized broker M1 history; reported quality 99–100% for valid tests.",
        "- Model: MT5 Every Tick generated from synchronized broker M1 history; reported history quality 98% for all 12 valid tests.",
    )
    annualized_lines = [
        "## Five-year annualized view",
        "",
        f"Arithmetic-overlay CAGR: **{combined['cagr_pct']:+.2f}% per year**. This is not tradable because the combined curve crossed below zero.",
        "",
        "| EA | Symbol / TF | 5Y return | CAGR | Max equity DD | PF | Win rate | Trades |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in sorted(rows, key=lambda item: item["return_pct"], reverse=True):
        annualized_lines.append(
            f"| {row['label']} | {row['chart']} | {row['return_pct']:+.2f}% | {row['cagr_pct']:+.2f}% | "
            f"{row['equity_dd_pct']:.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['trades']} |"
        )
    annualized_lines.extend(["", ""])
    execution_lines = [
        "## Execution-rejection audit",
        "",
        "All 12 tests initialized and completed, but MT5 rejected some attempted operations. Invalid-price rejections are a material strategy/broker-compatibility warning; market-closed rejections mean signals or stop updates were skipped.",
        "",
        "| EA binary | Total rejected | Invalid price | Market closed | Other |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in execution_rows:
        execution_lines.append(
            f"| {row['ea_file']} | {row['failed']} | {row['invalid_price']} | {row['market_closed']} | {row['other']} |"
        )
    execution_lines.extend([
        "",
        "XAU Weakness and US100 Weakness are especially unreliable on this Exness symbol setup because thousands/hundreds of their pending-order requests were rejected as invalid prices. Their reported returns should not be used for deployment decisions until the entry-price logic is repaired and retested.",
        "",
        "",
    ])
    marker = "## Test conditions"
    if marker in text:
        text = text.replace(marker, "\n".join(annualized_lines + execution_lines) + marker, 1)
    else:
        text += "\n" + "\n".join(annualized_lines)
    report_path.write_text(text, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
