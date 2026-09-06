from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
STORE = ROOT.parents[2] / "EA store"
sys.path.insert(0, str(STORE))

from app.evidence_series import analyse_equity_series, parse_mt5_balance_series  # noqa: E402
from app.mt5_evidence_jobs import _native_metrics  # noqa: E402


def analyse(stage: str) -> list[dict]:
    folder = ROOT / "Backtest Reports" / stage
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8-sig"))
    if isinstance(manifest, dict):
        manifest = [manifest]
    rows: list[dict] = []
    for item in manifest:
        report = Path(item["report"])
        native = _native_metrics(report)
        points = [dict(point) for point in parse_mt5_balance_series(report)]
        analysed = analyse_equity_series(points, expected_trades=int(native["trades"]), label=item["case"])
        analysed_stats = (analysed or {}).get("stats") or {}
        row = {**item, **native}
        row["analysed_sharpe"] = analysed_stats.get("sharpe_ratio", 0.0)
        row["analysed_recovery"] = analysed_stats.get("recovery_factor", 0.0)
        row["series"] = points
        rows.append(row)
    (folder / "results.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
    fields = [key for key in rows[0] if key not in {"series", "settings"}]
    with (folder / "results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{key: row[key] for key in fields} for row in rows])
    return rows


def chart(stage: str, rows: list[dict]) -> Path:
    groups = sorted({str(row["group"]) for row in rows})
    columns = 2
    row_count = (len(groups) + columns - 1) // columns
    fig, axes = plt.subplots(row_count, columns, figsize=(15, 4.5 * row_count), dpi=160, squeeze=False)
    for axis, group in zip(axes.flat, groups):
        for row in [item for item in rows if item["group"] == group]:
            series = row["series"]
            if not series:
                continue
            base = float(series[0]["balance"])
            values = [(float(point["balance"]) / base - 1.0) * 100.0 for point in series]
            axis.plot(range(len(values)), values, linewidth=1.2, label=f'{row["case"]} ({row["symbol"]})')
        axis.axhline(0.0, color="#64748b", linewidth=0.8)
        axis.set_title(group.replace("-", " ").title())
        axis.set_ylabel("Return (%)")
        axis.set_xlabel("Balance events")
        axis.grid(alpha=0.2)
        axis.legend(fontsize=6, ncol=2)
    for axis in axes.flat[len(groups):]:
        axis.axis("off")
    fig.suptitle(f"EMA3 — {stage} focused pipeline")
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    output = ROOT / f"EMA3 - {stage.upper()} CONFIG COMPARISON.png"
    fig.savefig(output, bbox_inches="tight")
    plt.close(fig)
    return output


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "Development"
    data = analyse(stage)
    output = chart(stage, data)
    simple = [{
        "case": row["case"], "group": row["group"], "symbol": row["symbol"],
        "return_pct": row["return_pct"], "pf": row["profit_factor"],
        "win_rate": row["win_rate_pct"], "dd": row["max_drawdown_pct"],
        "trades": row["trades"], "sharpe": row["sharpe_ratio"],
        "recovery": row["recovery_factor"],
    } for row in data]
    print(json.dumps({"chart": str(output), "results": simple}, indent=2))
