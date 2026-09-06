from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUNNER_PATH = ROOT / "Run-Overnight-Optimization.py"


def load_runner():
    spec = importlib.util.spec_from_file_location("overnight_runner", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load Overnight runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R = load_runner()


def report_inputs(path: Path) -> dict[str, str]:
    soup = R.ANALYZER.read_report(path)
    values: dict[str, str] = {}
    for cell in soup.find_all("td"):
        text = " ".join(cell.get_text(" ", strip=True).split())
        if text.startswith("Inp") and "=" in text:
            key, value = text.split("=", 1)
            values[key] = value
    return values


def verify_case(row: dict) -> dict:
    expected = {}
    for line in R.set_text(row["config"], 0).splitlines():
        if "=" not in line or line.startswith("InpMagic="):
            continue
        key, value = line.split("=", 1)
        expected[key] = value
    actual = report_inputs(Path(row["path"]))
    mismatches = {
        key: {"expected": value, "actual": actual.get(key)}
        for key, value in expected.items()
        if actual.get(key, "").lower() != value.lower()
    }
    return {"checked": len(expected), "mismatches": mismatches}


def main() -> None:
    R.prepare()
    final_path = ROOT / "FINAL AUDIT.json"
    data = json.loads(final_path.read_text(encoding="utf-8"))
    configs = [
        ("current-negative-close-open", R.base_config()),
        ("video-negative-reopen-eu3", R.video_negative()),
        ("video-go-long-reopen-eu3", R.video_go_long()),
    ]
    full_rows = []
    for index, (label, config) in enumerate(configs, 201):
        full_rows.append(R.run_case(f"full--{label}", config, "2023.09.01", "2026.09.01", 0, index))
    existing = data["full_optimized"]
    optimized_report = Path(existing["path"])
    optimized = {**existing, "deals": R.ANALYZER.parse_report(optimized_report)["deals"]}
    full_rows.append(optimized)
    data["full"] = {
        row["case"].split("--", 1)[1]: R.clean_row(row)
        for row in full_rows
    }

    locked_rows = []
    for label, row in data["locked"].items():
        parsed = R.ANALYZER.parse_report(Path(row["path"]))
        locked_rows.append({**row, **parsed, "case": f"locked--{label}", "config": row["config"]})
    verification = {
        "locked": {row["case"]: verify_case(row) for row in locked_rows},
        "full": {row["case"]: verify_case(row) for row in full_rows},
    }
    mismatches = sum(len(item["mismatches"]) for group in verification.values() for item in group.values())
    data["input_verification"] = {"cases": verification, "mismatch_count": mismatches}
    final_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(14, 7), constrained_layout=True)
    for row, color in zip(full_rows, ("#98a1ad", "#cc8b36", "#68a7ff", "#18b981")):
        dates, balances = R.ANALYZER.equity_points(row, datetime(2023, 9, 1))
        label = row["case"].split("--", 1)[1]
        ax.step(dates, balances, where="post", label=label, color=color, linewidth=1.7)
    ax.axhline(10000, color="#444", linestyle="--", linewidth=0.8)
    ax.set_title("US100 Overnight — three-year Every Tick comparison")
    ax.set_ylabel("Balance (USD)")
    ax.grid(alpha=0.2)
    ax.legend(loc="best")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    fig.savefig(ROOT / "Charts" / "THREE YEAR EQUITY COMPARISON.png", dpi=180, facecolor="white")
    plt.close(fig)

    fields = ["case", "return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades", "sharpe", "recovery_factor", "history_quality"]
    with (ROOT / "FINAL AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in [*locked_rows, *full_rows]:
            writer.writerow({key: row.get(key, "") for key in fields})

    lines = [
        "# Step 4 — US100 Overnight + Go Long Optimization",
        "",
        "## Goal",
        "",
        "Compare the current negative-day close-to-open implementation with the video's futures-reopen/calendar alternatives, then select timing, stop, reward/risk, trailing and Friday handling on development data only. Risk stayed at 1% in every test.",
        "",
        "## Recommendation",
        "",
        "**Keep the current negative-day close-to-open preset as the active portfolio configuration.** It produced the strongest untouched-year return with a much larger sample than the optimized alternative. The optimized 1% negative-day threshold is safer but too selective to replace it; retain it as a conservative demo preset. Reject the video's futures-reopen timing and unconditional Go Long version on this CFD feed.",
        "",
        "## Untouched locked-year results",
        "",
        "| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in locked_rows:
        label = row["case"].split("--", 1)[1]
        lines.append(f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |")
    lines += [
        "",
        "## Three-year Every Tick results",
        "",
        "| Configuration | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in full_rows:
        label = row["case"].split("--", 1)[1]
        lines.append(f"| {label} | {row['return_pct']:+.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['trades']} | {row['sharpe']:.2f} | {row['recovery_factor']:.2f} |")
    mc = data["monte_carlo"]
    lines += [
        "",
        "## Development-selected conservative preset",
        "",
        f"`{json.dumps(data['selected_config'], sort_keys=True)}`",
        "",
        "This setup requires a close-to-close cash-session decline of at least 1%, enters at 16:00 New York, uses a 3% emergency stop, a 0.75R target, Dynamic 50/20 and allows Fridays. It returned less than current in the locked year because it took only 26 trades.",
        "",
        "## Monte Carlo — conservative preset",
        "",
        f"10,000 paths: profitable {mc['probability_profitable_pct']:.1f}%, return P5 {mc['return_p5_pct']:+.2f}%, median {mc['return_median_pct']:+.2f}%, P95 {mc['return_p95_pct']:+.2f}%, max-DD P95 {mc['max_dd_p95_pct']:.2f}%, ruin {mc['ruin_probability_pct']:.2f}%.",
        "",
        "## Integrity notes",
        "",
        "- Parameter selection used only 2023-09-01 through 2025-08-31. The final year was not used for selection.",
        "- Headline one-year and three-year comparisons use native MT5 Every Tick data, broker spread, commission, swap and random execution delay.",
        "- Forty-three native MT5 tests were completed. Report/set verification found " + str(mismatches) + " input mismatches.",
        "- The older Go Long binary is input-audited only and was not used for rule selection. The unconditional idea was implemented in readable source so its timing and risk could be verified.",
        "- The futures-reopen thesis may behave differently on exchange-traded NQ futures. These results apply to the tested Exness USTEC CFD history.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Completed three additional full-history tests; input mismatches: {mismatches}")


if __name__ == "__main__":
    main()
