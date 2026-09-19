from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "EA store" / "data" / "evidence-cache" / "v1" / "products"
OUT = Path(__file__).resolve().parent
ACCOUNT = 100_000.0
START = date(2023, 9, 5)
END = date(2026, 9, 1)
MARGIN_LIMIT = ACCOUNT * 0.80

EAS = {
    "news-pulse-xau": ("News XAU", True),
    "news-pulse-xag": ("News XAG", True),
    "news-pulse-btc": ("News BTC", True),
    "orb-volume-profile-volume-confirmed": ("ORB VP Confirmed", False),
    "xau-trend-progression": ("XAU Trend Progression", False),
    "usdjpy-london-open-momentum": ("USDJPY London Momentum", False),
    "us100-orb-new-york-m30": ("US100 ORB NY M30", False),
    "us100-h1-orb-13utc": ("US100 H1 ORB", False),
}
LEVERAGE = {"XAUUSD": 9.0, "XAGUSD": 9.0, "BTCUSD": 1.0,
            "USTEC": 15.0, "USDJPY": 30.0}
CONTRACT = {"XAUUSD": 100.0, "XAGUSD": 5000.0, "BTCUSD": 1.0,
            "USTEC": 1.0, "USDJPY": 100_000.0}


def month_keys():
    keys = []
    year, month = START.year, START.month
    while (year, month) < (END.year, END.month):
        keys.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return keys


MONTHS = month_keys()


def canonical(value: str):
    value = value.upper().rstrip("R")
    return "USTEC" if value.startswith(("USTEC", "US100", "NAS")) else value


def required_margin(symbol: str, volume: float, price: float):
    symbol = canonical(symbol)
    notional = volume * CONTRACT[symbol] if symbol == "USDJPY" else volume * CONTRACT[symbol] * price
    return notional / LEVERAGE[symbol]


def blank():
    return {
        "signals": 0, "accepted": 0, "rejected": 0, "wins": 0, "losses": 0,
        "gross_profit": 0.0, "commission": 0.0, "swap": 0.0, "net_profit": 0.0,
        "stress_profit": 0.0, "exec_net_profit": 0.0, "exec_stress_profit": 0.0,
        "gross_wins": 0.0, "gross_losses": 0.0,
    }


def add(target: dict, source: dict):
    for key in target:
        target[key] += source[key]


def finalize(row: dict):
    result = dict(row)
    result["win_rate_pct"] = round(100 * row["wins"] / row["signals"], 2) if row["signals"] else None
    result["profit_factor"] = round(row["gross_wins"] / abs(row["gross_losses"]), 2) if row["gross_losses"] else None
    for key in ("gross_profit", "commission", "swap", "net_profit", "stress_profit",
                "exec_net_profit", "exec_stress_profit"):
        result[key] = round(row[key], 2)
    result["return_pct"] = round(100 * row["net_profit"] / ACCOUNT, 3)
    result["stressed_return_pct"] = round(100 * row["stress_profit"] / ACCOUNT, 3)
    result["swing_exec_return_pct"] = round(100 * row["exec_net_profit"] / ACCOUNT, 3)
    result["swing_exec_stressed_return_pct"] = round(100 * row["exec_stress_profit"] / ACCOUNT, 3)
    result.pop("gross_wins")
    result.pop("gross_losses")
    return result


def main():
    detail = []
    per_ea = {}
    portfolio = {month: blank() for month in MONTHS}
    for slug, (label, news) in EAS.items():
        rows = json.loads((CACHE / slug / "standard" / "3y.trades.json").read_text(encoding="utf-8-sig"))
        monthly = {month: blank() for month in MONTHS}
        symbol = None
        margins = []
        for row in rows:
            opened = datetime.fromisoformat(row["open_time"])
            if not START <= opened.date() < END:
                continue
            month = opened.strftime("%Y-%m")
            if month not in monthly:
                continue
            symbol = canonical(row["symbol"])
            base_risk_pct = float(row.get("configured_risk_pct") or (0.75 if news else 1.0))
            source_risk = float(row.get("estimated_risk_cash") or (75.0 if news else 100.0))
            source_balance = source_risk / (base_risk_pct / 100.0)
            desired_risk_pct = 0.75 if news else 0.50
            scale = ACCOUNT / source_balance * desired_risk_pct / base_risk_pct
            net = float(row["net_profit"]) * scale
            gross = float(row.get("gross_profit") or row["net_profit"]) * scale
            commission = float(row.get("commission") or 0.0) * scale
            swap = float(row.get("swap") or 0.0) * scale
            source_stress = (float(row["net_profit"]) * (0.65 if net > 0 else 1.25) - 0.15 * source_risk) if news else (
                float(row["net_profit"]) * (0.90 if net > 0 else 1.10) - 0.02 * source_risk)
            stressed = source_stress * scale
            margin = required_margin(symbol, float(row.get("volume") or 0.0) * scale,
                                     float(row["open_price"]))
            margins.append(100 * margin / ACCOUNT)
            executable = margin <= MARGIN_LIMIT
            values = monthly[month]
            values["signals"] += 1
            values["wins"] += int(net > 0)
            values["losses"] += int(net < 0)
            values["gross_profit"] += gross
            values["commission"] += commission
            values["swap"] += swap
            values["net_profit"] += net
            values["stress_profit"] += stressed
            values["gross_wins"] += max(net, 0.0)
            values["gross_losses"] += min(net, 0.0)
            if executable:
                values["accepted"] += 1
                values["exec_net_profit"] += net
                values["exec_stress_profit"] += stressed
            else:
                values["rejected"] += 1
        finalized = []
        for month in MONTHS:
            item = {"month": month, "ea": label, "symbol": symbol,
                    "category": "news" if news else "regular", **finalize(monthly[month])}
            detail.append(item)
            finalized.append(item)
            add(portfolio[month], monthly[month])
        total = blank()
        for month in MONTHS:
            add(total, monthly[month])
        per_ea[label] = {
            "symbol": symbol,
            "category": "news" if news else "regular",
            "risk_pct": 0.75 if news else 0.50,
            "summary": finalize(total),
            "average_monthly_net_profit": round(total["net_profit"] / len(MONTHS), 2),
            "average_monthly_stressed_profit": round(total["stress_profit"] / len(MONTHS), 2),
            "average_monthly_swing_exec_profit": round(total["exec_net_profit"] / len(MONTHS), 2),
            "average_monthly_swing_exec_stressed_profit": round(total["exec_stress_profit"] / len(MONTHS), 2),
            "median_margin_pct": round(sorted(margins)[len(margins) // 2], 2) if margins else None,
            "max_margin_pct": round(max(margins), 2) if margins else None,
            "months": finalized,
        }

    portfolio_rows = [{"month": month, **finalize(portfolio[month])} for month in MONTHS]
    payload = {
        "account_reference": ACCOUNT,
        "window": [START.isoformat(), END.isoformat()],
        "risk": {"news_pct": 0.75, "regular_pct": 0.50},
        "swing_asset_leverage": LEVERAGE,
        "margin_acceptance_limit_pct": 80.0,
        "per_ea": per_ea,
        "portfolio_months": portfolio_rows,
        "notes": [
            "Constant $100,000 balance attribution; no compounding or shared adaptive overlay.",
            "Net profit and return include the recorded MT5 commission and swap.",
            "All-signals columns include BTC. Swing-executable columns reject trades requiring more than 80% of equity as margin.",
            "Pending-order margin and exact intratrade floating equity are not available in the closed-deal ledger.",
        ],
    }
    (OUT / "monthly-detail-3y-100k.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    fields = ["month", "ea", "symbol", "category", "signals", "accepted", "rejected", "wins", "losses",
              "win_rate_pct", "profit_factor", "gross_profit", "commission", "swap", "net_profit", "return_pct",
              "stress_profit", "stressed_return_pct", "exec_net_profit", "swing_exec_return_pct",
              "exec_stress_profit", "swing_exec_stressed_return_pct"]
    with (OUT / "monthly-detail-3y-100k.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in fields} for row in detail)
    with (OUT / "monthly-portfolio-3y-100k.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["month"] + fields[4:])
        writer.writeheader()
        writer.writerows({key: row.get(key) for key in ["month"] + fields[4:]} for row in portfolio_rows)

    abbreviations = {
        "News XAU": "NXAU", "News XAG": "NXAG", "News BTC": "NBTC",
        "ORB VP Confirmed": "OVP", "XAU Trend Progression": "XTP",
        "USDJPY London Momentum": "UJPY", "US100 ORB NY M30": "UNY",
        "US100 H1 ORB": "UH1",
    }
    lines = [
        "# Three-year monthly attribution — $100K FTMO Swing",
        "",
        f"Window: {START.isoformat()} through {(END.replace(day=1)).isoformat()} (September 2023 through August 2026).",
        "",
        "News risk is 0.75% per filled trade; regular-EA risk is 0.50%. Figures use a constant $100,000 reference balance, do not compound, and include recorded MT5 commission and swap. They are per-EA attribution, not a replay of the shared adaptive overlay.",
        "",
        "## Per-EA summary",
        "",
        "| EA | Signals | Avg trades/mo | Win rate | PF | 3Y net return | Avg monthly net | Avg stressed/mo | Swing accepted | Swing rejected | Swing stressed/mo |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, data in per_ea.items():
        s = data["summary"]
        lines.append(
            f"| {name} | {s['signals']} | {s['signals']/len(MONTHS):.2f} | {s['win_rate_pct']:.2f}% | "
            f"{s['profit_factor']:.2f} | {s['return_pct']:+.2f}% | ${data['average_monthly_net_profit']:,.2f} | "
            f"${data['average_monthly_stressed_profit']:,.2f} | {s['accepted']} | {s['rejected']} | "
            f"${data['average_monthly_swing_exec_stressed_profit']:,.2f} |"
        )
    lines.extend([
        "",
        "## Monthly trade counts and portfolio attribution",
        "",
        "Each EA column is the number of signals in that month. Return columns are the sum of independently normalized EA attribution; they are not the path-dependent adaptive portfolio result.",
        "",
        "| Month | NXAU | NXAG | NBTC | OVP | XTP | UJPY | UNY | UH1 | Total | All net | All stressed | Swing net | Swing stressed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    month_lookup = {name: {row["month"]: row for row in data["months"]} for name, data in per_ea.items()}
    portfolio_lookup = {row["month"]: row for row in portfolio_rows}
    for month in MONTHS:
        counts = [month_lookup[name][month]["signals"] for name in abbreviations]
        p = portfolio_lookup[month]
        lines.append(
            f"| {month} | " + " | ".join(str(value) for value in counts) +
            f" | {p['signals']} | {p['return_pct']:+.3f}% | {p['stressed_return_pct']:+.3f}% | "
            f"{p['swing_exec_return_pct']:+.3f}% | {p['swing_exec_stressed_return_pct']:+.3f}% |"
        )
    lines.extend([
        "",
        "## Monthly net P/L in USD by EA",
        "",
        "EA columns show every recorded signal, including BTC. `All total` is their sum. `Swing stressed` applies the execution stress and removes trades that exceed the 80% Swing margin ceiling.",
        "",
        "| Month | NXAU | NXAG | NBTC | OVP | XTP | UJPY | UNY | UH1 | All total | Swing stressed |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    usd_rows = []
    for month in MONTHS:
        values = [month_lookup[name][month]["net_profit"] for name in abbreviations]
        p = portfolio_lookup[month]
        usd_rows.append({"month": month, **{abbreviations[name]: value for name, value in zip(abbreviations, values)},
                         "all_total": p["net_profit"], "swing_stressed": p["exec_stress_profit"]})
        lines.append(
            f"| {month} | " + " | ".join(f"${value:+,.0f}" for value in values) +
            f" | ${p['net_profit']:+,.0f} | ${p['exec_stress_profit']:+,.0f} |"
        )
    lines.extend([
        "",
        "## Abbreviations and execution warning",
        "",
        "NXAU = News XAU; NXAG = News XAG; NBTC = News BTC; OVP = ORB Volume Profile Confirmed; XTP = XAU Trend Progression; UJPY = USDJPY London Momentum; UNY = US100 ORB New York M30; UH1 = US100 H1 ORB.",
        "",
        "FTMO's 1:30 Swing figure is the maximum/base leverage, not uniform leverage for every asset. FTMO's published asset-class breakdown is 1:30 forex, 1:15 indices, 1:9 metals and 1:1 crypto. At locked 0.75% risk, all 124 BTC signals required more than the model's 80% margin ceiling (median 613.56% of equity), so the Swing-executable BTC contribution is $0. This remains true when the account is reduced proportionally from $200K to $100K.",
        "",
        "Detailed per-EA monthly wins, losses, win rate, PF, gross P/L, commission, swap, net P/L, return, stress result and margin accept/reject status are in `monthly-detail-3y-100k.csv`.",
    ])
    (OUT / "MONTHLY 3Y 100K REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    with (OUT / "monthly-usd-3y-100k.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(usd_rows[0]))
        writer.writeheader()
        writer.writerows(usd_rows)
    print(json.dumps({"per_ea": {name: {
        "signals": data["summary"]["signals"],
        "average_monthly_net": data["average_monthly_net_profit"],
        "average_monthly_stressed": data["average_monthly_stressed_profit"],
        "average_monthly_swing_stressed": data["average_monthly_swing_exec_stressed_profit"],
        "accepted": data["summary"]["accepted"], "rejected": data["summary"]["rejected"],
    } for name, data in per_ea.items()}, "portfolio_months": portfolio_rows}, indent=2))


if __name__ == "__main__":
    main()
