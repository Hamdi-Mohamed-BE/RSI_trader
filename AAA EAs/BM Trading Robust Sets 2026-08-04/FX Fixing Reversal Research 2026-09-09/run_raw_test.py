"""Raw, unoptimized transfer of Krohn-Mueller-Whelan FX fixing reversals."""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCHF", "USDCAD")
FOREIGN_PER_USD = {"USDJPY", "USDCHF", "USDCAD"}
NY = ZoneInfo("America/New_York")
TOKYO = ZoneInfo("Asia/Tokyo")
BERLIN = ZoneInfo("Europe/Berlin")
LONDON = ZoneInfo("Europe/London")
UTC = ZoneInfo("UTC")
COST_MODES = {"gross": 0.0, "half_spread": 0.5, "full_spread": 1.0}


def load_symbol(symbol: str, metadata: dict) -> pd.DataFrame:
    with np.load(ROOT / "Data" / f"{symbol}-M5.npz") as archive:
        rates = archive["rates"]
    frame = pd.DataFrame({name: rates[name] for name in rates.dtype.names})
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.set_index("time").sort_index()
    point = float(metadata["symbols"][symbol]["point"])
    spread = frame["spread"].to_numpy(dtype=float, copy=True)
    positive = spread > 0
    hourly = pd.Series(np.where(positive, spread, np.nan), index=frame.index).groupby(frame.index.hour).median()
    global_median = float(np.nanmedian(spread[positive])) if positive.any() else 0.0
    for hour in range(24):
        missing = (frame.index.hour == hour) & ~positive
        replacement = float(hourly.get(hour, global_median))
        if not math.isfinite(replacement):
            replacement = global_median
        spread[missing] = replacement
    frame["spread_price"] = spread * point
    return frame


def at_local(day: date, value: time, zone: ZoneInfo) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, value, tzinfo=zone).astimezone(UTC))


def raw_windows(day: date) -> list[dict]:
    """The four legs in paper Note 2, using local fixes and DST-aware boundaries."""
    previous = day - timedelta(days=1)
    return [
        {
            "group": "Tokyo",
            "leg": "Tokyo pre-fix",
            "usd_direction": 1,
            "entry": at_local(previous, time(17, 0), NY),
            "exit": at_local(day, time(9, 55), TOKYO),
        },
        {
            "group": "Tokyo",
            "leg": "Tokyo post-fix",
            "usd_direction": -1,
            "entry": at_local(day, time(9, 55), TOKYO),
            "exit": at_local(day, time(2, 0), NY),
        },
        {
            "group": "Europe",
            "leg": "ECB pre-fix",
            "usd_direction": 1,
            "entry": at_local(day, time(2, 0), NY),
            "exit": at_local(day, time(14, 15), BERLIN),
        },
        {
            "group": "Europe",
            "leg": "London post-fix",
            "usd_direction": -1,
            "entry": at_local(day, time(16, 0), LONDON),
            "exit": at_local(day, time(17, 0), NY),
        },
    ]


def quote_direction(symbol: str, usd_direction: int) -> int:
    """Return +1 for long MT5 symbol and -1 for short MT5 symbol."""
    return usd_direction if symbol in FOREIGN_PER_USD else -usd_direction


def trade_return(entry_bid: float, exit_bid: float, entry_spread: float, exit_spread: float, direction: int, spread_multiplier: float) -> float:
    entry_ask = entry_bid + spread_multiplier * entry_spread
    exit_ask = exit_bid + spread_multiplier * exit_spread
    if direction > 0:
        return exit_bid / entry_ask - 1.0
    return entry_bid / exit_ask - 1.0


def execute_all(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    earliest = max(frame.index.min() for frame in frames.values())
    latest = min(frame.index.max() for frame in frames.values())
    start_day = earliest.date()
    end_day = latest.date()
    rows = []
    for day_value in pd.date_range(start_day, end_day, freq="D"):
        business_day = day_value.date()
        if business_day.weekday() >= 5:
            continue
        for window in raw_windows(business_day):
            if window["entry"] >= window["exit"]:
                raise RuntimeError(f"Invalid time ordering: {window}")
            for symbol, frame in frames.items():
                if window["entry"] not in frame.index or window["exit"] not in frame.index:
                    continue
                entry = frame.loc[window["entry"]]
                exit_row = frame.loc[window["exit"]]
                direction = quote_direction(symbol, window["usd_direction"])
                base = {
                    "business_date": business_day.isoformat(),
                    "symbol": symbol,
                    "group": window["group"],
                    "leg": window["leg"],
                    "usd_direction": "long USD" if window["usd_direction"] > 0 else "short USD",
                    "quote_direction": "long" if direction > 0 else "short",
                    "entry_utc": window["entry"].isoformat(),
                    "exit_utc": window["exit"].isoformat(),
                    "entry_bid": float(entry["open"]),
                    "exit_bid": float(exit_row["open"]),
                    "entry_spread_price": float(entry["spread_price"]),
                    "exit_spread_price": float(exit_row["spread_price"]),
                }
                for mode, multiplier in COST_MODES.items():
                    rows.append({
                        **base,
                        "cost_mode": mode,
                        "return_pct": trade_return(
                            base["entry_bid"],
                            base["exit_bid"],
                            base["entry_spread_price"],
                            base["exit_spread_price"],
                            direction,
                            multiplier,
                        ) * 100.0,
                    })
    trades = pd.DataFrame(rows)
    if trades.empty:
        raise RuntimeError("No paper windows were executable")
    return trades


def metric_block(trades: pd.DataFrame, group: str) -> dict:
    selected = trades if group == "All" else trades[trades["group"] == group]
    values = selected["return_pct"].to_numpy(dtype=float) / 100.0
    by_day = selected.assign(log_return=np.log1p(values)).groupby("business_date")["log_return"].sum().sort_index()
    daily = np.expm1(by_day.to_numpy(dtype=float))
    total = math.expm1(float(by_day.sum()))
    equity = np.exp(np.cumsum(by_day.to_numpy(dtype=float)))
    full_equity = np.r_[1.0, equity]
    drawdown = float(np.min(full_equity / np.maximum.accumulate(full_equity) - 1.0))
    std = float(np.std(daily, ddof=1)) if len(daily) > 1 else 0.0
    sharpe = float(np.mean(daily) / std * math.sqrt(252.0)) if std > 0 else 0.0
    wins = values[values > 0]
    losses = values[values < 0]
    years = len(by_day) / 252.0
    annualized = math.expm1(math.log1p(total) / years) if years > 0 and total > -1 else -1.0
    return {
        "return_pct": total * 100.0,
        "annualized_return_pct": annualized * 100.0,
        "profit_factor": float(wins.sum() / abs(losses.sum())) if len(losses) else None,
        "win_rate_pct": float((values > 0).mean() * 100.0) if len(values) else 0.0,
        "max_drawdown_pct": abs(drawdown) * 100.0,
        "sharpe": sharpe,
        "recovery_factor": total / abs(drawdown) if drawdown < 0 else None,
        "trades": int(len(values)),
        "average_trade_bps": float(values.mean() * 10_000.0) if len(values) else 0.0,
        "days": int(len(by_day)),
    }


def sliced(trades: pd.DataFrame, period: str) -> pd.DataFrame:
    end = pd.to_datetime(trades["business_date"]).max()
    if period == "5y":
        start = pd.Timestamp("2021-09-01")
    elif period == "3y":
        start = pd.Timestamp("2023-09-01")
    elif period == "1y":
        start = pd.Timestamp("2025-09-01")
    else:
        raise ValueError(period)
    dates = pd.to_datetime(trades["business_date"])
    return trades[(dates >= start) & (dates <= end)]


def equal_weight_portfolio(trades: pd.DataFrame, group: str) -> tuple[pd.Series, pd.DataFrame]:
    selected = trades if group == "All" else trades[trades["group"] == group]
    legs = selected.assign(log_return=np.log1p(selected["return_pct"] / 100.0))
    pair_day = legs.groupby(["business_date", "symbol"])["log_return"].sum().unstack()
    simple_pair = np.expm1(pair_day)
    simple_portfolio = simple_pair.mean(axis=1, skipna=True)
    portfolio_log = np.log1p(simple_portfolio)
    return portfolio_log.sort_index(), selected


def portfolio_metrics(trades: pd.DataFrame, group: str) -> dict:
    logs, selected = equal_weight_portfolio(trades, group)
    daily = np.expm1(logs.to_numpy(dtype=float))
    total = math.expm1(float(logs.sum()))
    equity = np.exp(np.cumsum(logs.to_numpy(dtype=float)))
    full = np.r_[1.0, equity]
    drawdown = float(np.min(full / np.maximum.accumulate(full) - 1.0))
    std = float(np.std(daily, ddof=1)) if len(daily) > 1 else 0.0
    trade_values = selected["return_pct"].to_numpy(dtype=float) / 100.0
    wins = trade_values[trade_values > 0]
    losses = trade_values[trade_values < 0]
    years = len(logs) / 252.0
    annualized = math.expm1(math.log1p(total) / years) if years > 0 and total > -1 else -1.0
    return {
        "return_pct": total * 100.0,
        "annualized_return_pct": annualized * 100.0,
        "profit_factor": float(wins.sum() / abs(losses.sum())) if len(losses) else None,
        "win_rate_pct": float((trade_values > 0).mean() * 100.0),
        "max_drawdown_pct": abs(drawdown) * 100.0,
        "sharpe": float(np.mean(daily) / std * math.sqrt(252.0)) if std > 0 else 0.0,
        "recovery_factor": total / abs(drawdown) if drawdown < 0 else None,
        "trades": int(len(trade_values)),
        "average_trade_bps": float(trade_values.mean() * 10_000.0),
        "days": int(len(logs)),
    }


def make_chart(trades: pd.DataFrame) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = {"Tokyo": "#5ba6ff", "Europe": "#65f6c1", "All": "#f6c65b"}
    for group in ("Tokyo", "Europe", "All"):
        logs, _ = equal_weight_portfolio(trades, group)
        equity = 10_000.0 * np.exp(np.cumsum(logs.to_numpy(dtype=float)))
        ax.plot(pd.to_datetime(logs.index), equity, label=f"{group} fix portfolio", color=colors[group], linewidth=1.4)
    ax.set_title("FX Fixing Reversal - raw paper windows, full Exness spread")
    ax.set_ylabel("Growth of $10,000 at 1x notional")
    ax.grid(alpha=0.15)
    ax.legend(frameon=False)
    fig.tight_layout()
    fig.savefig(ROOT / "raw-equity.png", dpi=180)
    plt.close(fig)


def clean(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def main() -> None:
    metadata = json.loads((ROOT / "Data" / "metadata.json").read_text(encoding="utf-8"))
    frames = {symbol: load_symbol(symbol, metadata) for symbol in SYMBOLS}
    trades = execute_all(frames)
    trades.to_csv(ROOT / "raw-trades.csv", index=False)

    summary_rows = []
    portfolio_rows = []
    for period in ("5y", "3y", "1y"):
        period_trades = sliced(trades, period)
        for mode in COST_MODES:
            mode_trades = period_trades[period_trades["cost_mode"] == mode]
            for symbol in SYMBOLS:
                symbol_trades = mode_trades[mode_trades["symbol"] == symbol]
                for group in ("Tokyo", "Europe", "All"):
                    summary_rows.append({
                        "period": period,
                        "cost_mode": mode,
                        "symbol": symbol,
                        "strategy": group,
                        **metric_block(symbol_trades, group),
                    })
            for group in ("Tokyo", "Europe", "All"):
                portfolio_rows.append({
                    "period": period,
                    "cost_mode": mode,
                    "strategy": group,
                    **portfolio_metrics(mode_trades, group),
                })

    summary = pd.DataFrame(summary_rows)
    portfolios = pd.DataFrame(portfolio_rows)
    summary.to_csv(ROOT / "raw-summary-by-pair.csv", index=False)
    portfolios.to_csv(ROOT / "raw-portfolio-summary.csv", index=False)

    leg_rows = []
    full = sliced(trades, "5y")
    for mode in COST_MODES:
        mode_trades = full[full["cost_mode"] == mode]
        for symbol in SYMBOLS:
            for leg in ("Tokyo pre-fix", "Tokyo post-fix", "ECB pre-fix", "London post-fix"):
                leg_trade = mode_trades[(mode_trades["symbol"] == symbol) & (mode_trades["leg"] == leg)]
                leg_rows.append({"cost_mode": mode, "symbol": symbol, "leg": leg, **metric_block(leg_trade, "All")})
    pd.DataFrame(leg_rows).to_csv(ROOT / "raw-summary-by-leg.csv", index=False)

    yearly_rows = []
    full_cost = trades[trades["cost_mode"] == "full_spread"]
    years = sorted(pd.to_datetime(full_cost["business_date"]).dt.year.unique())
    for year in years:
        year_trades = full_cost[pd.to_datetime(full_cost["business_date"]).dt.year == year]
        for group in ("Tokyo", "Europe", "All"):
            yearly_rows.append({"year": int(year), "strategy": group, **portfolio_metrics(year_trades, group)})
    yearly = pd.DataFrame(yearly_rows)
    yearly.to_csv(ROOT / "yearly-stability.csv", index=False)

    make_chart(full_cost)
    output = {
        "paper": {
            "title": "Foreign Exchange Fixings and Returns around the Clock",
            "authors": "Ingomar Krohn, Philippe Mueller and Paul Whelan",
            "journal": "Journal of Finance 79(1)",
            "year": 2024,
            "doi": "10.1111/jofi.13306",
        },
        "method": {
            "windows": {
                "tokyo_pre": "17:00 New York previous day to 09:55 Tokyo; long USD",
                "tokyo_post": "09:55 Tokyo to 02:00 New York; short USD",
                "europe_pre": "02:00 New York to 14:15 Frankfurt; long USD",
                "london_post": "16:00 London to 17:00 New York; short USD",
            },
            "dst": "IANA local time zones; no fixed UTC offsets",
            "entry_exit": "M5 bar open, exact endpoint required",
            "risk": "paper-style 1x notional; no stop or take-profit",
            "costs": list(COST_MODES),
            "production_action": "none",
        },
        "portfolio_summary": [
            {key: clean(value) for key, value in row.items()} for row in portfolio_rows
        ],
        "pair_summary": [
            {key: clean(value) for key, value in row.items()} for row in summary_rows
        ],
        "yearly_stability": [
            {key: clean(value) for key, value in row.items()} for row in yearly_rows
        ],
    }
    (ROOT / "raw-results.json").write_text(json.dumps(output, indent=2), encoding="utf-8")

    print("PORTFOLIO - FULL OBSERVED SPREAD", flush=True)
    print(portfolios[(portfolios["cost_mode"] == "full_spread")].to_string(index=False), flush=True)
    print("\nFIVE-YEAR PAIR RESULTS - FULL OBSERVED SPREAD", flush=True)
    print(summary[(summary["period"] == "5y") & (summary["cost_mode"] == "full_spread")].to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
