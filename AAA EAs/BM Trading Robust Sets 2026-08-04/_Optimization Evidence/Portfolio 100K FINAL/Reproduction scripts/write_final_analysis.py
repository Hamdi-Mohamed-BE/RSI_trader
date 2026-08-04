from __future__ import annotations

import csv
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np


ROOT = Path(r"C:\Users\hama101\Downloads\BM Trading EAs 2026-08-04\portfolio optimization")
spec = importlib.util.spec_from_file_location("portfolio_analyzer", ROOT / "analyze_portfolio.py")
pa = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pa
spec.loader.exec_module(pa)

FILES = {
    "Range Breakout": "PORT_SCALED_RB.htm",
    "Go Long": "PORT_SCALED_GL.htm",
    "Turnaround Tuesday": "PORT_SCALED_TT.htm",
    "ATR Candle Breakout": "PORT_SCALED_ATR.htm",
}
SETTINGS = {
    "Range Breakout": {"chart": "USDJPY M5", "setting": "$245 fixed money risk", "nominal_stop_risk": 245.0},
    "Go Long": {"chart": "US30 D1", "setting": "0.50 fixed lot; stop loss disabled", "nominal_stop_risk": None},
    "Turnaround Tuesday": {"chart": "UT100 D1", "setting": "0.24 fixed lot; stop loss disabled", "nominal_stop_risk": None},
    "ATR Candle Breakout": {"chart": "XAUUSD H1", "setting": "$146 fixed money risk", "nominal_stop_risk": 146.0},
}


def main() -> None:
    output_dir = ROOT / "analysis" / "final"
    output_dir.mkdir(parents=True, exist_ok=True)
    parsed = {
        name: pa.parse_report(name, ROOT / "scaled validation reports" / filename)
        for name, filename in FILES.items()
    }
    names = list(parsed)
    timestamps = sorted({deal["timestamp"] for report in parsed.values() for deal in report.deals})
    event_index = {timestamp: index for index, timestamp in enumerate(timestamps)}
    matrix = np.zeros((len(timestamps), len(names)), dtype=float)
    for column, name in enumerate(names):
        for deal in parsed[name].deals:
            matrix[event_index[deal["timestamp"]], column] += deal["net"]
    months = [
        f"{year}-{month:02d}"
        for year in (2025, 2026)
        for month in range(1, 13)
        if f"{year}-{month:02d}" <= "2026-07"
    ]
    metrics = pa.period_metrics(np.ones(len(names)), timestamps, matrix, months)

    ea_results = {}
    for name, report in parsed.items():
        losses = [deal["net"] for deal in report.deals if deal["net"] < 0]
        ea_results[name] = {
            **SETTINGS[name],
            "net_profit": pa.parse_number(report.summary.get("Total Net Profit", "0")),
            "profit_factor": pa.parse_number(report.summary.get("Profit Factor", "0")),
            "total_trades": int(pa.parse_number(report.summary.get("Total Trades", "0"))),
            "largest_historical_deal_loss": min(losses) if losses else 0.0,
            "balance_drawdown_maximal_standalone": report.summary.get("Balance Drawdown Maximal", ""),
            "equity_drawdown_maximal_standalone": report.summary.get("Equity Drawdown Maximal", ""),
            "report": FILES[name],
        }

    summary = {
        "starting_balance": 100_000.0,
        "validation_start": "2025-01-01",
        "validation_end_exclusive": "2026-08-01",
        "completed_months": len(months),
        "model": "MT5 Every Tick (generated ticks, Model=0)",
        "total_net_profit": metrics["total_profit"],
        "average_monthly_profit": metrics["average_monthly_profit"],
        "annualized_average_profit": metrics["average_monthly_profit"] * 12.0,
        "profitable_months": metrics["profitable_months"],
        "worst_month_profit": metrics["worst_month_profit"],
        "best_month_profit": metrics["best_month_profit"],
        "max_monthly_closed_balance_drawdown": metrics["max_monthly_closed_balance_dd"],
        "stress_factor": 1.25,
        "stressed_max_monthly_drawdown": metrics["stressed_max_monthly_dd"],
        "stressed_max_monthly_drawdown_percent_of_100k": metrics["stressed_max_monthly_dd"] / 100_000.0 * 100.0,
        "global_closed_balance_drawdown": metrics["global_closed_balance_dd"],
        "drawdown_scope": "Merged closed-deal balance curve; not simultaneous floating-equity drawdown",
    }
    payload = {
        "portfolio": summary,
        "eas": ea_results,
        "monthly": {
            month: {
                "profit": metrics["monthly_profit"][month],
                "closed_balance_drawdown": metrics["monthly_drawdown"][month],
                "stressed_drawdown": metrics["monthly_drawdown"][month] * 1.25,
            }
            for month in months
        },
    }
    (output_dir / "FINAL 100K portfolio analysis.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with (output_dir / "FINAL 100K monthly results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Month", "Net profit", "Closed-balance DD", "Stressed DD x1.25", "Stressed DD % of $100k"])
        for month in months:
            dd = metrics["monthly_drawdown"][month]
            writer.writerow([
                month,
                round(metrics["monthly_profit"][month], 2),
                round(dd, 2),
                round(dd * 1.25, 2),
                round(dd * 1.25 / 100_000.0 * 100.0, 4),
            ])

    with (output_dir / "FINAL 100K EA results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["EA", "Chart", "Setting", "Net profit", "Profit factor", "Trades", "Largest historical deal loss", "Standalone equity DD"])
        for name, result in ea_results.items():
            writer.writerow([
                name, result["chart"], result["setting"], result["net_profit"],
                result["profit_factor"], result["total_trades"],
                round(result["largest_historical_deal_loss"], 2),
                result["equity_drawdown_maximal_standalone"],
            ])
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
