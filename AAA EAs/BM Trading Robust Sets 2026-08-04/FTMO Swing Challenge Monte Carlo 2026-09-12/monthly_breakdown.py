from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from statistics import median


ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "EA store" / "data" / "evidence-cache" / "v1" / "products"
OUT = Path(__file__).resolve().parent / "monthly-breakdown-100k.json"
ACCOUNT = 100_000.0
MARGIN_LIMIT = ACCOUNT * 0.80
START = date(2021, 9, 5)
END = date(2026, 9, 1)

NEWS = {
    "news-pulse-xau": "News Pulse XAU",
    "news-pulse-xag": "News Pulse XAG",
    "news-pulse-btc": "News Pulse BTC",
}
REGULAR = {
    "orb-volume-profile-volume-confirmed": "ORB Volume Profile Volume Confirmed",
    "xau-trend-progression": "XAU Trend Progression",
    "usdjpy-london-open-momentum": "USDJPY London Open Momentum",
    "us100-orb-new-york-m30": "US100 ORB New York M30",
    "us100-h1-orb-13utc": "US100 H1 ORB 13UTC",
}
ALL = {**NEWS, **REGULAR}
LEVERAGE = {"XAUUSD": 9.0, "XAGUSD": 9.0, "BTCUSD": 1.0,
            "USTEC": 15.0, "USDJPY": 30.0}
CONTRACT = {"XAUUSD": 100.0, "XAGUSD": 5000.0, "BTCUSD": 1.0,
            "USTEC": 1.0, "USDJPY": 100_000.0}


def months():
    values = []
    year, month = START.year, START.month
    while (year, month) < (END.year, END.month):
        values.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return values


MONTHS = months()


def canonical(symbol: str):
    value = symbol.upper().rstrip("R")
    return "USTEC" if value.startswith(("USTEC", "US100", "NAS")) else value


def margin(symbol: str, volume: float, price: float):
    symbol = canonical(symbol)
    notional = volume * CONTRACT[symbol] if symbol == "USDJPY" else volume * CONTRACT[symbol] * price
    return notional / LEVERAGE[symbol]


def stress_pnl(row: dict, risk_cash: float, news: bool):
    pnl = float(row["net_profit"])
    if news:
        return pnl * (0.65 if pnl > 0 else 1.25) - 0.15 * risk_cash
    return pnl * (0.90 if pnl > 0 else 1.10) - 0.02 * risk_cash


def stats(values: dict[str, float]):
    series = [round(values.get(month, 0.0), 2) for month in MONTHS]
    return {
        "total_net_profit": round(sum(series), 2),
        "average_monthly_net_profit": round(sum(series) / len(series), 2),
        "median_monthly_net_profit": round(median(series), 2),
        "profitable_months": sum(value > 0 for value in series),
        "losing_months": sum(value < 0 for value in series),
        "flat_months": sum(value == 0 for value in series),
        "profitable_month_pct": round(100 * sum(value > 0 for value in series) / len(series), 2),
        "best_month": round(max(series), 2),
        "worst_month": round(min(series), 2),
        "monthly_values": dict(zip(MONTHS, series)),
    }


def main():
    rows_out = []
    for slug, label in ALL.items():
        rows = json.loads((CACHE / slug / "standard" / "5y.trades.json").read_text(encoding="utf-8-sig"))
        historical = defaultdict(float)
        stressed = defaultdict(float)
        executable_historical = defaultdict(float)
        executable_stressed = defaultdict(float)
        trade_counts = defaultdict(int)
        margins = []
        accepted = rejected = 0
        news = slug in NEWS
        symbol = None
        for row in rows:
            opened = datetime.fromisoformat(row["open_time"])
            if not START <= opened.date() < END:
                continue
            symbol = row["symbol"]
            month = opened.strftime("%Y-%m")
            base_risk_pct = float(row.get("configured_risk_pct") or (0.75 if news else 1.0))
            source_risk_cash = float(row.get("estimated_risk_cash") or (100.0 if not news else 75.0))
            source_balance = source_risk_cash / (base_risk_pct / 100.0)
            desired_risk_pct = 0.75 if news else 0.50
            risk_multiplier = desired_risk_pct / base_risk_pct
            account_multiplier = ACCOUNT / source_balance
            scale = account_multiplier * risk_multiplier
            normalized_risk = source_risk_cash * scale
            historical_pnl = float(row["net_profit"]) * scale
            stressed_value = stress_pnl(row, source_risk_cash, news) * scale
            required_margin = margin(symbol, float(row.get("volume") or 0.0) * scale,
                                     float(row["open_price"]))
            margin_pct = 100 * required_margin / ACCOUNT
            margins.append(margin_pct)
            historical[month] += historical_pnl
            stressed[month] += stressed_value
            trade_counts[month] += 1
            if required_margin <= MARGIN_LIMIT:
                accepted += 1
                executable_historical[month] += historical_pnl
                executable_stressed[month] += stressed_value
            else:
                rejected += 1
        row_out = {
            "ea": label,
            "slug": slug,
            "symbol": canonical(symbol or ""),
            "category": "news" if news else "regular",
            "risk_pct": 0.75 if news else 0.50,
            "source_trades": accepted + rejected,
            "average_trades_per_month": round((accepted + rejected) / len(MONTHS), 2),
            "historical_all_signals": stats(historical),
            "stressed_all_signals": stats(stressed),
            "swing_margin": {
                "leverage": LEVERAGE[canonical(symbol or "")],
                "accepted_trades": accepted,
                "rejected_trades": rejected,
                "accepted_pct": round(100 * accepted / (accepted + rejected), 2),
                "median_required_margin_pct": round(median(margins), 2),
                "maximum_required_margin_pct": round(max(margins), 2),
                "historical_executable": stats(executable_historical),
                "stressed_executable": stats(executable_stressed),
            },
        }
        rows_out.append(row_out)
    payload = {
        "account_reference": ACCOUNT,
        "window": [START.isoformat(), END.isoformat()],
        "months": len(MONTHS),
        "non_news_risk_pct": 0.50,
        "news_risk_pct": 0.75,
        "swing_margin_limit_pct": 80.0,
        "method": "Constant $100K reference balance; no compounding; net MT5 P/L includes recorded commission and swap.",
        "eas": rows_out,
    }
    OUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps([{ 
        "ea": row["ea"],
        "symbol": row["symbol"],
        "risk_pct": row["risk_pct"],
        "historical_monthly": row["historical_all_signals"]["average_monthly_net_profit"],
        "stressed_monthly": row["stressed_all_signals"]["average_monthly_net_profit"],
        "swing_stressed_monthly": row["swing_margin"]["stressed_executable"]["average_monthly_net_profit"],
        "margin_accept_pct": row["swing_margin"]["accepted_pct"],
        "median_margin_pct": row["swing_margin"]["median_required_margin_pct"],
        "max_margin_pct": row["swing_margin"]["maximum_required_margin_pct"],
    } for row in rows_out], indent=2))


if __name__ == "__main__":
    main()
