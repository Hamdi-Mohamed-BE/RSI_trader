from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
BOOKMAPER = PACKAGE.parent / "BookMaper" / "artifacts"
ACTIVE_PATH = BOOKMAPER / "active-ea-regime-filter.json"
STANDALONE_PATH = BOOKMAPER / "standalone-results.json"
PARSER_PATH = PACKAGE / "BAT Portfolio Backtest 2026-08-09" / "Build-BAT-Portfolio-Report.py"
NATIVE_REPORT_ROOT = PACKAGE / "_Backtests" / "MT5-DMC-20260811" / "reports" / "selected-regime-20260828"
INITIAL_BALANCE = 10_000.0
PERIOD = "2025-08-11 to 2026-08-21"

# Keep an EA when either version returned at least +5%. Use the filter only when
# both return and profit factor improved. This is the exact user-approved rule.
VARIANTS = {
    "ATR Candle Breakout": "base",
    "Asia Breakout": "filtered",
    "BTC Top Down FVG Liquidity": "base",
    "DmC": "filtered",
    "EMA3": "base",
    "ETH Top Down FVG Liquidity": "base",
    "Go Long": "base",
    "LTA Volume Profile": "base",
    "Nasdaq 5M Open EMA ATR": "base",
    "Nasdaq Overnight": "base",
    "News Pulse": "base",
    "ORB Volume Profile": "base",
    "US100 Fabio ORB 1R": "base",
    "XAU Weakness": "filtered",
}

NATIVE_CASES = {
    "Asia Breakout": {"id": "asia", "label": "Asia Breakout", "symbol": "XAUUSD", "period": "H1", "chart": "XAUUSD H1", "set_source": "embedded Markov filter"},
    "DmC": {"id": "dmc", "label": "DmC", "symbol": "XAUUSD", "period": "H1", "chart": "XAUUSD H1", "set_source": "embedded Markov filter"},
    "XAU Weakness": {"id": "xau-weakness", "label": "XAU Weakness", "symbol": "XAUUSD", "period": "M15", "chart": "XAUUSD M15", "set_source": "embedded Markov filter"},
}

spec = importlib.util.spec_from_file_location("selected_portfolio_mt5_parser", PARSER_PATH)
mt5_parser = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mt5_parser)


def max_drawdown(series: list[dict[str, float | str]]) -> tuple[float, float]:
    peak = float(series[0]["balance"])
    worst_amount = 0.0
    worst_pct = 0.0
    for point in series:
        balance = float(point["balance"])
        peak = max(peak, balance)
        amount = peak - balance
        pct = amount / peak * 100.0 if peak else 0.0
        if pct > worst_pct:
            worst_amount, worst_pct = amount, pct
    return worst_amount, worst_pct


def main() -> None:
    active = json.loads(ACTIVE_PATH.read_text(encoding="utf-8-sig"))
    standalone = json.loads(STANDALONE_PATH.read_text(encoding="utf-8-sig"))
    rows = {row["ea"]: row for row in active["by_ea"]}

    selected: list[dict] = []
    events: list[dict] = []
    for label, variant in VARIANTS.items():
        row = rows[label]
        native = None
        if variant == "filtered":
            case = NATIVE_CASES[label]
            native = mt5_parser.parse_report(NATIVE_REPORT_ROOT / f"{case['id']}.htm", case)
            metrics = {
                "return_pct": native["return_pct"],
                "profit_factor": native["profit_factor"],
                "win_rate_pct": native["win_rate_pct"],
                "max_equity_dd_pct": native["balance_dd_pct"],
                "trades": native["trades"],
                "final_balance": native["final"],
                "net_profit": native["net"],
                "gross_profit": native["gross_profit"],
                "gross_loss": native["gross_loss"],
                "wins": native["wins"],
                "losses": native["losses"],
            }
        else:
            metrics = row["baseline"]
        selected.append(
            {
                "label": label,
                "symbol": row["symbol"],
                "variant": "filtered-native" if native else variant,
                "return_pct": float(metrics["return_pct"]),
                "profit_factor": float(metrics["profit_factor"]),
                "win_rate_pct": float(metrics["win_rate_pct"]),
                "realized_balance_dd_pct": float(metrics["max_equity_dd_pct"]),
                "trades": int(metrics["trades"]),
                "final": float(metrics["final_balance"]),
                "net": float(metrics["net_profit"]),
                "gross_profit": float(metrics["gross_profit"]),
                "gross_loss": float(metrics["gross_loss"]),
                "wins": int(metrics["wins"]),
                "losses": int(metrics["losses"]),
                "history_quality": str(native["history_quality"]) if native else "Saved net MT5 trades",
            }
        )
        if native:
            for deal in native["deals"]:
                events.append({"time": deal["time"].isoformat(), "open_time": deal["time"].isoformat(), "bot": label, "net": float(deal["cashflow"])})
        else:
            for decision in active["decisions"]:
                if decision["bot"] == label:
                    events.append({"time": decision["close_time"], "open_time": decision["open_time"], "bot": label, "net": float(decision["base_net"])})

    xau = standalone["xau"]["optimized"]
    metrics = xau["metrics"]
    selected.append(
        {
            "label": "XAU Markov Regime",
            "symbol": "XAUUSD",
            "variant": "standalone",
            "return_pct": float(metrics["return_pct"]),
            "profit_factor": float(metrics["profit_factor"]),
            "win_rate_pct": float(metrics["win_rate_pct"]),
            "realized_balance_dd_pct": float(metrics["max_equity_dd_pct"]),
            "trades": int(metrics["trades"]),
            "final": float(metrics["final_balance"]),
            "net": float(metrics["net_profit"]),
            "gross_profit": float(metrics["gross_profit"]),
            "gross_loss": float(metrics["gross_loss"]),
            "wins": int(metrics["wins"]),
            "losses": int(metrics["losses"]),
            "history_quality": "GC=F daily proxy; conservative costs",
        }
    )
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
    series: list[dict[str, float | str]] = [
        {"time": "2025-08-11T00:00:00", "balance": INITIAL_BALANCE}
    ]
    balance = INITIAL_BALANCE
    for event in events:
        net = event["net"]
        balance += net
        series.append({"time": event["time"], "balance": round(balance, 2)})
    dd_amount, dd_pct = max_drawdown(series)
    gross_profit = sum(float(row["gross_profit"]) for row in selected)
    gross_loss = sum(float(row["gross_loss"]) for row in selected)
    trades = sum(int(row["trades"]) for row in selected)
    wins = sum(int(row["wins"]) for row in selected)
    losses = sum(int(row["losses"]) for row in selected)
    combined = {
        "period": PERIOD,
        "tested_eas": len(selected),
        "initial": INITIAL_BALANCE,
        "final": round(balance, 2),
        "net": round(balance - INITIAL_BALANCE, 2),
        "return_pct": round((balance / INITIAL_BALANCE - 1.0) * 100.0, 4),
        "realized_balance_dd_amount": round(dd_amount, 2),
        "realized_balance_dd_pct": round(dd_pct, 4),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "profit_factor": round(gross_profit / abs(gross_loss), 4) if gross_loss else 0.0,
        "trades": trades,
        "wins": wins,
        "losses": losses,
        "win_rate_pct": round(wins / trades * 100.0, 4) if trades else 0.0,
        "series": series,
    }
    payload = {
        "method": "Selected cash-flow overlay: filter only when both return and PF improve; retain any EA with at least +5% in either version.",
        "combined": combined,
        "bots": sorted(selected, key=lambda item: item["return_pct"], reverse=True),
    }
    (ROOT / "portfolio-results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    with (ROOT / "individual-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(selected[0]))
        writer.writeheader()
        writer.writerows(payload["bots"])
    with (ROOT / "combined-equity.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time", "balance"])
        writer.writeheader()
        writer.writerows(series)

    figure, axis = plt.subplots(figsize=(13, 6), dpi=170)
    dates = [datetime.fromisoformat(str(point["time"])) for point in series]
    balances = [float(point["balance"]) for point in series]
    axis.plot(dates, balances, color="#0b8f78", linewidth=1.4)
    axis.axhline(INITIAL_BALANCE, color="gray", linestyle="--", linewidth=0.9)
    axis.set_title("Selected active BAT — one-year realized-balance overlay")
    axis.set_xlabel("Date")
    axis.set_ylabel("Balance (USD)")
    axis.grid(True, alpha=0.25)
    figure.tight_layout()
    figure.savefig(ROOT / "selected-portfolio-equity.png")
    plt.close(figure)

    lines = [
        "# Selected active BAT — final one-year audit",
        "",
        f"- Active EAs: **{combined['tested_eas']}**",
        f"- Initial / final: **${combined['initial']:,.2f} / ${combined['final']:,.2f}**",
        f"- Net return: **{combined['return_pct']:+.2f}%**",
        f"- Profit factor: **{combined['profit_factor']:.2f}**",
        f"- Win rate: **{combined['win_rate_pct']:.2f}%**",
        f"- Realized balance DD: **{combined['realized_balance_dd_pct']:.2f}%**",
        f"- Trades: **{combined['trades']}**",
        "",
        "The combined result is a chronological cash-flow overlay, not a simultaneous multi-EA MT5 test. It includes saved net MT5 trade cash flows for the existing EAs. The standalone XAU Markov row is a GC=F daily proxy and is labelled separately.",
        "",
        "| EA | Symbol | Version | Return | PF | Win rate | Realized DD | Trades |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in payload["bots"]:
        lines.append(
            f"| {row['label']} | {row['symbol']} | {row['variant']} | {row['return_pct']:+.2f}% | "
            f"{row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | "
            f"{row['realized_balance_dd_pct']:.2f}% | {row['trades']} |"
        )
    (ROOT / "FULL REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(json.dumps({key: value for key, value in combined.items() if key != "series"}, indent=2))


if __name__ == "__main__":
    main()
