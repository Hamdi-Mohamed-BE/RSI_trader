from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
FINAL = ROOT / "Backtest Reports" / "Final"
PARSER_PATH = PACKAGE / "BAT Portfolio Backtest 2026-08-09" / "Build-BAT-Portfolio-Report.py"
START = datetime(2025, 8, 11)
END = datetime(2026, 8, 10, 23, 59, 59)

TRAINING = {
    "xau": {"return_pct": 14.13, "pf": 2.44, "dd_pct": 4.32, "trades": 30},
    "xag": {"return_pct": 1.45, "pf": 1.25, "dd_pct": 3.78, "trades": 9},
    "us30": {"return_pct": 12.42, "pf": 1.87, "dd_pct": 4.53, "trades": 31},
    "us100": {"return_pct": 14.08, "pf": 1.67, "dd_pct": 5.26, "trades": 42},
}


def load_parser():
    spec = importlib.util.spec_from_file_location("portfolio_parser", PARSER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load report parser: {PARSER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verdict(row: dict) -> str:
    if row["return_pct"] > 0 and row["profit_factor"] >= 1.20 and row["trades"] >= 50:
        return "RESEARCH ONLY"
    if row["return_pct"] > 0 and row["profit_factor"] > 1.0:
        return "WEAK / WATCH"
    return "REJECT"


def main() -> None:
    parser = load_parser()
    manifest = json.loads((FINAL / "manifest.json").read_text(encoding="utf-8-sig"))
    selected = {
        item["Id"]: item
        for item in json.loads((ROOT / "selected-configs.json").read_text(encoding="utf-8-sig"))
    }
    rows = []
    curves = []
    for item in manifest:
        case = {
            "id": item["Id"],
            "label": item["Label"],
            "symbol": item["Symbol"],
            "period": item["Period"],
            "chart": f"{item['Id']}.png",
            "set_source": f"BEST - {item['Id']}.set",
        }
        row = parser.parse_report(FINAL / f"{item['Id']}.htm", case)
        deals = row.pop("deals")
        row["verdict"] = verdict(row)
        row["training"] = TRAINING[item["Id"]]
        row["selection_note"] = selected[item["Id"]]["Selection"]
        rows.append(row)

        balance = row["initial"]
        points = [{"date": START.date().isoformat(), "equity": round(balance, 2)}]
        for deal in deals:
            if abs(deal["cashflow"]) < 0.005:
                continue
            balance += deal["cashflow"]
            points.append({"date": deal["time"].date().isoformat(), "equity": round(balance, 2)})
        points.append({"date": END.date().isoformat(), "equity": round(row["final"], 2)})
        curves.append({
            "id": row["id"],
            "market": "US100" if row["id"] == "us100" else row["symbol"].replace("USD", ""),
            "symbol": row["symbol"],
            "timeframe": row["timeframe"],
            "returnPct": round(row["return_pct"], 2),
            "maxDdPct": round(row["equity_dd_pct"], 2),
            "pf": round(row["profit_factor"], 2),
            "trades": row["trades"],
            "points": points,
        })

    serializable = json.loads(json.dumps(rows, default=str))
    (ROOT / "final-results.json").write_text(json.dumps(serializable, indent=2), encoding="utf-8")
    (ROOT / "equity-curves.json").write_text(json.dumps(curves, indent=2), encoding="utf-8")

    columns = [
        "id", "label", "symbol", "timeframe", "initial", "final", "net", "return_pct",
        "equity_dd_amount", "equity_dd_pct", "balance_dd_amount", "balance_dd_pct",
        "profit_factor", "win_rate_pct", "wins", "losses", "trades", "expected_payoff",
        "recovery_factor", "sharpe", "gross_profit", "gross_loss", "largest_win",
        "largest_loss", "average_win", "average_loss", "history_quality", "verdict",
    ]
    with (ROOT / "final-results.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    report = [
        "# ICT + SNR Liquidity-Reversal Research — Final Report",
        "",
        "## Honest verdict",
        "",
        "The mechanical ICT + support/resistance combination did **not** pass out-of-sample validation for live deployment. XAG and US30 were marginally profitable, but neither produced enough return or profit-factor margin to survive realistic uncertainty. XAU and US100 lost money; US100 failed decisively.",
        "",
        "No active BAT, installation pipeline, or live MT5 portfolio was changed.",
        "",
        "## Untouched one-year validation",
        "",
        "- Period: 2025-08-11 through 2026-08-10",
        "- Starting balance: USD 10,000 per independent market test",
        "- Risk: 1% of current equity per trade; one position per symbol",
        "- Execution: Exness MT5, full Every Tick simulation from broker M1 history, random execution delay",
        "- History quality: 99–100%",
        "- Settings: selected only on 2023-08-11 through 2025-08-10, then frozen",
        "- Real-tick limitation: Exness-MT5Trial16 canceled historical real-tick downloads. Invalid zero-bar reports were rejected, not counted. Final validation therefore uses MT5-generated intrabar ticks from broker M1 data, not broker-recorded tick history.",
        "",
        "| Market | Chart | Final balance | Net / return | Max equity DD | PF | Win rate | Trades | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        market = "US100" if row["id"] == "us100" else row["symbol"].replace("USD", "")
        report.append(
            f"| {market} | {row['timeframe']} | ${row['final']:,.2f} | ${row['net']:,.2f} / {row['return_pct']:+.2f}% | "
            f"{row['equity_dd_pct']:.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['trades']} | {row['verdict']} |"
        )

    report += [
        "",
        "## Training-to-validation stability",
        "",
        "| Market | Training return / PF / trades | Validation return / PF / trades | Assessment |",
        "|---|---:|---:|---|",
    ]
    assessments = {
        "xau": "Edge reversed; reject.",
        "xag": "Positive but training and validation samples remain too weak.",
        "us30": "Best survivor, but PF 1.15 leaves little margin for costs or regime change.",
        "us100": "Severe regime failure; reject.",
    }
    for row in rows:
        train = row["training"]
        report.append(
            f"| {'US100' if row['id'] == 'us100' else row['symbol'].replace('USD', '')} | "
            f"{train['return_pct']:+.2f}% / {train['pf']:.2f} / {train['trades']} | "
            f"{row['return_pct']:+.2f}% / {row['profit_factor']:.2f} / {row['trades']} | {assessments[row['id']]} |"
        )

    report += [
        "",
        "## Mechanical strategy tested",
        "",
        "1. Build zones from the prior-day high/low, completed Asian range, previous week, and confirmed H1 swings.",
        "2. Increase a zone's score when independent levels cluster and recent closed candles reject it.",
        "3. During the configured London/New York window, require a liquidity sweep beyond the zone followed by a close back through it.",
        "4. Require a closed-bar market-structure shift through the pre-sweep internal swing, ATR-sized displacement, and a three-candle fair-value gap.",
        "5. Enter only on a later FVG retracement and directional close. Place the stop beyond the raid extreme with an ATR buffer; target a fixed R multiple, with optional break-even/trailing variants.",
        "",
        "## Why this was the defensible translation",
        "",
        "- ICT's own Episode 6 explicitly links fair-value gaps with market-structure shifts; the EA uses that sequence rather than trading every gap: https://www.youtube.com/watch?v=Bkt8B3kLATQ",
        "- Empirical S/R research finds local extrema are useful approximations, repeated bounces matter, and effects decay; the EA therefore uses confirmed swings, rejection counts, and ATR-normalized zones: https://arxiv.org/abs/2101.07410",
        "- Federal Reserve research found intraday S/R levels can help predict trend interruptions, but their strength varies; this supports treating S/R as a conditional filter, not certainty: https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf",
        "- Intraday volume and volatility have strong session seasonality, supporting explicit London/New York windows: https://arxiv.org/abs/1810.12099",
        "",
        "## Robustness and limitations",
        "",
        "- The EA is closed-bar and non-repainting: confirmed right-side swings only; no same-bar FVG retracement entry.",
        "- 173 training/refinement/neighborhood cases were screened. This creates selection bias even though the final year was untouched.",
        "- XAG's selected training sample had only nine trades, so it was weak before validation.",
        "- A one-year final window is useful but not enough to establish a durable edge across multiple regimes.",
        "- CFD spreads, swaps, and random delay were represented by MT5; broker-recorded historical tick data and external commissions were not available.",
        "- 'ICT' language is descriptive. This experiment tests these objective rules; it does not prove claims about institutional intent.",
        "",
        "## Decision",
        "",
        "Do not add this EA to the active portfolio. If research continues, use US30 only as the starting hypothesis and require a second broker plus a later forward test. Do not optimize the failed final year, because doing so would contaminate the holdout.",
    ]
    (ROOT / "FINAL REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
