from __future__ import annotations

import json
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BOOKMAPER = PACKAGE.parent / "BookMaper" / "artifacts"
INITIAL = 10_000.0
SOURCE_FILTERED = {
    "LTA Volume Profile",
    "BTC Top Down FVG Liquidity",
    "ETH Top Down FVG Liquidity",
    "ORB Volume Profile",
    "US100 Fabio ORB 1R",
    "Asia Breakout",
    "DmC",
    "EMA3",
    "XAU Weakness",
    "Nasdaq Overnight",
    "Nasdaq 5M Candle Momentum",
    "News Pulse",
}
VENDOR_UNCHANGED: set[str] = set()
NATIVE_SAFE_LABEL = "Nasdaq 5M Candle Momentum"
NATIVE_SAFE_REPORT = PACKAGE / "Nasdaq 5M Open EMA ATR Research 2026-08-20" / "Backtest Reports" / "982 Claim Recheck" / "Portfolio Window" / "portfolio-full-safe.htm"
PARSER_PATH = PACKAGE / "BAT Portfolio Backtest 2026-08-09" / "Build-BAT-Portfolio-Report.py"

spec = importlib.util.spec_from_file_location("deployment_mode_mt5_parser", PARSER_PATH)
mt5_parser = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mt5_parser)


def max_drawdown(series: list[dict]) -> tuple[float, float]:
    peak = float(series[0]["balance"])
    worst_amount = worst_pct = 0.0
    for point in series:
        balance = float(point["balance"])
        peak = max(peak, balance)
        amount = peak - balance
        pct = amount / peak * 100.0 if peak else 0.0
        if pct > worst_pct:
            worst_amount, worst_pct = amount, pct
    return worst_amount, worst_pct


def main() -> None:
    current = json.loads((ROOT / "portfolio-results.json").read_text(encoding="utf-8-sig"))
    filter_data = json.loads((BOOKMAPER / "active-ea-regime-filter.json").read_text(encoding="utf-8-sig"))
    standalone = json.loads((BOOKMAPER / "standalone-results.json").read_text(encoding="utf-8-sig"))
    by_ea = {row["ea"]: row for row in filter_data["by_ea"]}

    safe_case = {
        "id": "nasdaq-5m-candle-momentum-safe",
        "label": NATIVE_SAFE_LABEL,
        "symbol": "USTEC",
        "period": "M5",
        "chart": "USTEC M5",
        "set_source": "native Full Safe replacement preset",
    }
    native_safe = mt5_parser.parse_report(NATIVE_SAFE_REPORT, safe_case)

    events: list[dict] = []
    for decision in filter_data["decisions"]:
        bot = decision["bot"]
        if bot not in SOURCE_FILTERED | VENDOR_UNCHANGED:
            continue
        if bot in SOURCE_FILTERED and not decision["accepted"]:
            continue
        events.append(
            {
                "time": decision["close_time"],
                "open_time": decision["open_time"],
                "bot": bot,
                "net": float(decision["base_net"]),
            }
        )
    for deal in native_safe["deals"]:
        events.append(
            {
                "time": deal["time"].isoformat(),
                "open_time": deal["time"].isoformat(),
                "bot": NATIVE_SAFE_LABEL,
                "net": float(deal["cashflow"]),
            }
        )

    xau = standalone["xau"]["optimized"]
    for trade in xau["trades"]:
        events.append(
            {
                "time": trade["close_time"],
                "open_time": trade["open_time"],
                "bot": "XAU Markov Regime",
                "net": float(trade["net"]),
            }
        )
    events.sort(key=lambda item: (item["time"], item["open_time"], item["bot"]))

    balance = INITIAL
    series = [{"time": "2025-08-11T00:00:00", "balance": INITIAL}]
    for event in events:
        balance += event["net"]
        series.append({"time": event["time"], "balance": round(balance, 2)})

    metric_rows = [by_ea[label]["filtered"] for label in SOURCE_FILTERED if label != NATIVE_SAFE_LABEL]
    metric_rows += [by_ea[label]["baseline"] for label in VENDOR_UNCHANGED]
    metric_rows.append(
        {
            "gross_profit": native_safe["gross_profit"],
            "gross_loss": native_safe["gross_loss"],
            "trades": native_safe["trades"],
            "wins": native_safe["wins"],
            "losses": native_safe["losses"],
        }
    )
    metric_rows.append(xau["metrics"])
    gross_profit = sum(float(row["gross_profit"]) for row in metric_rows)
    gross_loss = sum(float(row["gross_loss"]) for row in metric_rows)
    trades = sum(int(row["trades"]) for row in metric_rows)
    wins = sum(int(row["wins"]) for row in metric_rows)
    losses = sum(int(row["losses"]) for row in metric_rows)
    dd_amount, dd_pct = max_drawdown(series)
    safe = {
        "label": "Full Safe per-EA deployment",
        "period": "2025-08-11 to 2026-08-21",
        "tested_eas": 13,
        "individually_filtered_eas": len(SOURCE_FILTERED),
        "safe_by_design_eas": 1,
        "vendor_unchanged_eas": len(VENDOR_UNCHANGED),
        "initial": INITIAL,
        "final": round(balance, 2),
        "net": round(balance - INITIAL, 2),
        "return_pct": round((balance / INITIAL - 1.0) * 100.0, 4),
        "profit_factor": round(gross_profit / abs(gross_loss), 4) if gross_loss else 0.0,
        "win_rate_pct": round(wins / trades * 100.0, 4) if trades else 0.0,
        "realized_balance_dd_amount": round(dd_amount, 2),
        "realized_balance_dd_pct": round(dd_pct, 4),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "series": series,
        "caution": "Every active non-standalone strategy in this mode uses its own embedded completed-D1 filter.",
    }
    standard = dict(current["combined"])
    standard["label"] = "Standard current selective configuration"
    standard["individually_filtered_eas"] = 3
    standard["safe_by_design_eas"] = 1
    standard["vendor_unchanged_eas"] = 0
    output = {"standard": standard, "safe": safe}
    (ROOT / "deployment-mode-results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({key: {k: v for k, v in value.items() if k != "series"} for key, value in output.items()}, indent=2))


if __name__ == "__main__":
    main()
