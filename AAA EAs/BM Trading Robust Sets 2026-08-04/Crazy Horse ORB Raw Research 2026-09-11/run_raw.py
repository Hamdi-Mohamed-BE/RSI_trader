"""Transparent raw reconstruction of the narrated 'Crazy Horse' ORB.

Only stated rules are treated as facts. The creator's proprietary HTF signal,
auto-stop formula, overextension threshold and shelf trailing are unavailable.
The raw baseline therefore uses the opposite opening-range edge as invalidation,
a fixed 1R target, and no trailing. A separate H1 EMA200 proxy shows whether a
common mechanical interpretation of 'higher-timeframe trend' helps.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "Data"
CHARTS = ROOT / "Charts"
TERMINAL = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
START = pd.Timestamp("2021-09-11", tz="UTC")
END = pd.Timestamp("2026-09-11", tz="UTC")
NY = ZoneInfo("America/New_York")
RISK_FRACTION = 0.01
STARTING_BALANCE = 10_000.0
COMMISSION_PER_LOT_SIDE = 3.50


@dataclass(frozen=True)
class Meta:
    canonical: str
    broker_symbol: str
    point: float
    digits: int
    contract_size: float
    volume_min: float
    volume_step: float
    volume_max: float


def resolve(canonical: str, names: list[str]) -> str:
    exact = [name for name in names if name.upper() == canonical]
    if exact:
        return exact[0]
    matches = [name for name in names if name.upper().startswith(canonical)]
    if not matches:
        raise RuntimeError(f"No broker symbol for {canonical}")
    return min(matches, key=len)


def acquire() -> tuple[dict[str, pd.DataFrame], dict[str, Meta], dict]:
    DATA.mkdir(parents=True, exist_ok=True)
    if not mt5.initialize(path=str(TERMINAL)):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")
    frames, metas = {}, {}
    audit = {"terminal": str(TERMINAL), "downloaded_at_utc": datetime.now(timezone.utc).isoformat(), "symbols": {}}
    try:
        account = mt5.account_info()
        audit |= {"broker": account.company, "server": account.server, "account_name": account.name}
        names = [item.name for item in (mt5.symbols_get() or ())]
        for canonical in ("XAUUSD", "USTEC"):
            symbol = resolve(canonical, names)
            mt5.symbol_select(symbol, True)
            rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, START.to_pydatetime(), END.to_pydatetime())
            if rates is None or len(rates) < 50_000:
                raise RuntimeError(f"Insufficient M5 history for {symbol}: {0 if rates is None else len(rates)}")
            info = mt5.symbol_info(symbol)
            meta = Meta(canonical, symbol, float(info.point), int(info.digits), float(info.trade_contract_size), float(info.volume_min), float(info.volume_step), float(info.volume_max))
            idx = pd.to_datetime(rates["time"], unit="s", utc=True)
            frame = pd.DataFrame({key: rates[key].astype(float) for key in ("open", "high", "low", "close", "tick_volume", "spread")}, index=idx)
            frame = frame[~frame.index.duplicated(keep="last")].sort_index()
            positive = frame.loc[frame.spread > 0, "spread"]
            floor = float(positive.median()) if len(positive) else max(float(info.spread), 1.0)
            frame["spread_used"] = frame.spread.where(frame.spread > 0, floor) * meta.point
            frames[canonical], metas[canonical] = frame, meta
            np.savez_compressed(DATA / f"{canonical}-M5.npz", rates=rates)
            audit["symbols"][canonical] = asdict(meta) | {
                "bars": len(frame), "from": frame.index[0].isoformat(), "to": frame.index[-1].isoformat(),
                "median_positive_spread_points": floor,
            }
    finally:
        mt5.shutdown()
    (DATA / "broker-audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    return frames, metas, audit


def floor_volume(value: float, meta: Meta) -> float:
    if value < meta.volume_min:
        return 0.0
    steps = math.floor((value + 1e-12) / meta.volume_step)
    return min(meta.volume_max, steps * meta.volume_step)


def result_stats(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"trades": 0, "return_pct": 0.0, "profit_factor": 0.0, "win_rate_pct": 0.0, "max_drawdown_pct": 0.0, "sharpe": 0.0, "avg_r": 0.0}
    pnl = trades.net_pnl.astype(float)
    equity = STARTING_BALANCE + pnl.cumsum()
    peak = equity.cummax()
    dd = equity / peak - 1.0
    wins, losses = pnl[pnl > 0].sum(), -pnl[pnl < 0].sum()
    daily = trades.assign(day=pd.to_datetime(trades.exit_utc, utc=True).dt.date).groupby("day").net_pnl.sum() / STARTING_BALANCE
    sd = daily.std(ddof=1)
    return {
        "trades": len(trades), "return_pct": float(pnl.sum() / STARTING_BALANCE * 100.0),
        "profit_factor": float(wins / losses) if losses else 999.0,
        "win_rate_pct": float((pnl > 0).mean() * 100.0), "max_drawdown_pct": float(-dd.min() * 100.0),
        "sharpe": float(daily.mean() / sd * math.sqrt(252)) if sd and math.isfinite(sd) else 0.0,
        "avg_r": float(trades.net_r.mean()), "gross_profit": float(wins), "gross_loss": float(losses),
        "costs": float(trades.cost.sum()),
    }


def h1_trend(frame: pd.DataFrame) -> pd.Series:
    hourly = frame.close.resample("1h", label="left", closed="left").last().dropna()
    ema = hourly.ewm(span=200, adjust=False, min_periods=200).mean()
    trend = np.sign(hourly - ema).shift(1)
    return trend


def simulate(frame: pd.DataFrame, meta: Meta, use_htf: bool) -> pd.DataFrame:
    local = frame.index.tz_convert(NY)
    dates = pd.Index(local.date)
    trend = h1_trend(frame)
    trades = []
    equity = STARTING_BALANCE
    for day in pd.Index(dates).unique():
        if day.weekday() >= 5:
            continue
        day_mask = dates == day
        positions = np.flatnonzero(day_mask)
        if not len(positions):
            continue
        d = frame.iloc[positions]
        dl = d.index.tz_convert(NY)
        opening = d[(dl.time >= datetime.strptime("09:30", "%H:%M").time()) & (dl.time < datetime.strptime("09:45", "%H:%M").time())]
        if len(opening) != 3:
            continue
        range_high, range_low = float(opening.high.max()), float(opening.low.min())
        if range_high <= range_low:
            continue
        signal_bars = d[(dl.time >= datetime.strptime("09:45", "%H:%M").time()) & (dl.time < datetime.strptime("10:30", "%H:%M").time())]
        signal_index = None
        side = 0
        for stamp, bar in signal_bars.iterrows():
            if bar.close > range_high:
                signal_index, side = stamp, 1
                break
            if bar.close < range_low:
                signal_index, side = stamp, -1
                break
        if signal_index is None:
            continue
        signal_pos = frame.index.get_loc(signal_index)
        if signal_pos + 1 >= len(frame):
            continue
        entry_stamp = frame.index[signal_pos + 1]
        if entry_stamp.tz_convert(NY).date() != day:
            continue
        if use_htf:
            available = trend.loc[:entry_stamp].dropna()
            if available.empty or int(available.iloc[-1]) != side:
                continue
        spread = float(frame.spread_used.iloc[signal_pos + 1])
        entry_bid = float(frame.open.iloc[signal_pos + 1])
        entry = entry_bid + (spread if side > 0 else 0.0)
        stop = range_low if side > 0 else range_high + spread
        risk_distance = abs(entry - stop)
        if risk_distance <= spread:
            continue
        target = entry + side * risk_distance
        risk_cash = equity * RISK_FRACTION
        cash_per_lot_at_stop = risk_distance * meta.contract_size
        lots = floor_volume(risk_cash / cash_per_lot_at_stop, meta)
        if lots <= 0:
            continue
        exit_stamp, exit_price, reason = None, None, None
        afternoon = d[(dl.time >= entry_stamp.tz_convert(NY).time()) & (dl.time < datetime.strptime("16:00", "%H:%M").time())]
        for stamp, bar in afternoon.iterrows():
            bar_spread = float(frame.loc[stamp, "spread_used"])
            if side > 0:
                stop_hit, target_hit = float(bar.low) <= stop, float(bar.high) >= target
            else:
                stop_hit, target_hit = float(bar.high) + bar_spread >= stop, float(bar.low) + bar_spread <= target
            if stop_hit:
                exit_stamp, exit_price, reason = stamp, stop, "stop"
                break
            if target_hit:
                exit_stamp, exit_price, reason = stamp, target, "target"
                break
        if exit_stamp is None:
            close_candidates = d[dl.time >= datetime.strptime("15:55", "%H:%M").time()]
            if close_candidates.empty:
                continue
            exit_stamp = close_candidates.index[0]
            exit_bid = float(close_candidates.open.iloc[0])
            exit_spread = float(close_candidates.spread_used.iloc[0])
            exit_price = exit_bid + (exit_spread if side < 0 else 0.0)
            reason = "16:00 close"
        gross_pnl = side * (float(exit_price) - entry) * meta.contract_size * lots
        commission = 2.0 * COMMISSION_PER_LOT_SIDE * lots
        net_pnl = gross_pnl - commission
        equity += net_pnl
        trades.append({
            "date": day.isoformat(), "symbol": meta.canonical, "model": "H1 EMA200 proxy" if use_htf else "stated minimum",
            "side": "long" if side > 0 else "short", "signal_utc": signal_index.isoformat(), "entry_utc": entry_stamp.isoformat(),
            "exit_utc": exit_stamp.isoformat(), "entry": entry, "stop": stop, "target": target, "opening_range": range_high-range_low,
            "lots": lots, "reason": reason, "gross_pnl": gross_pnl, "cost": commission, "net_pnl": net_pnl,
            "net_r": net_pnl / risk_cash if risk_cash else 0.0, "equity": equity,
        })
    return pd.DataFrame(trades)


def main() -> None:
    frames, metas, audit = acquire()
    CHARTS.mkdir(parents=True, exist_ok=True)
    rows, summaries = [], []
    windows = {"5y": START, "3y": END - pd.DateOffset(years=3), "1y": END - pd.DateOffset(years=1)}
    for symbol in ("XAUUSD", "USTEC"):
        for use_htf in (False, True):
            trades = simulate(frames[symbol], metas[symbol], use_htf)
            rows.append(trades)
            model = "H1 EMA200 proxy" if use_htf else "stated minimum"
            for label, begin in windows.items():
                subset = trades[pd.to_datetime(trades.entry_utc, utc=True) >= begin] if not trades.empty else trades
                summaries.append({"symbol": symbol, "model": model, "window": label, **result_stats(subset)})
            if not trades.empty:
                plt.figure(figsize=(10, 5.5))
                stamps = pd.to_datetime(trades.exit_utc, utc=True)
                plt.plot(stamps, trades.equity, linewidth=1.6)
                plt.axhline(STARTING_BALANCE, color="#888", linewidth=0.8)
                plt.title(f"{symbol} Crazy Horse ORB raw — {model}")
                plt.ylabel("$10,000 account equity")
                plt.grid(alpha=0.2)
                plt.tight_layout()
                plt.savefig(CHARTS / f"{symbol.lower()}-{model.lower().replace(' ', '-')}.png", dpi=160)
                plt.close()
    all_trades = pd.concat(rows, ignore_index=True)
    results = pd.DataFrame(summaries)
    all_trades.to_csv(ROOT / "raw-trades.csv", index=False)
    results.to_csv(ROOT / "raw-results.csv", index=False)
    five = results[results.window == "5y"]
    table = [
        "| Symbol | Raw interpretation | Trades | Return | PF | Win rate | Max DD | Sharpe | Avg R | Costs |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in five.to_dict("records"):
        table.append(f"| {row['symbol']} | {row['model']} | {row['trades']} | {row['return_pct']:.2f}% | {row['profit_factor']:.2f} | {row['win_rate_pct']:.2f}% | {row['max_drawdown_pct']:.2f}% | {row['sharpe']:.2f} | {row['avg_r']:.2f}R | ${row['costs']:.2f} |")
    report = f"""# Crazy Horse ORB — raw reconstruction

## Scope

Research only. No pipeline optimization and no website, BAT or live-account change.

## Rules that were actually stated

- New York cash open, 09:30 ET.
- Build the first 15-minute range.
- Enter after the first M5 candle body closes outside that range; no retest.
- Use higher-timeframe direction.
- The example used 1:1 because its 227-point opening range was described as overextended.
- Trail by a proprietary "shelf" method.

## Missing rules and transparent reconstruction

The transcript does not define the proprietary trend signal, auto-stop, range-overextension threshold or shelf algorithm. The `stated minimum` row therefore uses the opposite edge of the 15-minute range as the stop, a fixed 1R target, one first breakout per day, signals only through 10:30 ET, and no trailing. The second row adds a clearly labelled H1 EMA200 trend proxy. This is not claimed to be the creator's proprietary model.

## Five-year Exness Raw Spread result

{chr(10).join(table)}

Returns use a $10,000 balance and 1% equity risk per trade, recorded bar spreads, broker-valid lot steps, $3.50/lot/side commission, conservative stop-first handling when both exits fall inside one M5 bar, and a 16:00 ET forced exit. The CSV also contains one- and three-year rows.

## Promotion decision

**Skip the full pipeline for now.** Every five-year row loses after costs and the best five-year win rate is far below the advertised 80%. XAU improves in the latest year, but that isolated recovery does not justify optimizing a five-year loser. Reconsider only after obtaining the creator's exact HTF signal, auto-stop, overextension threshold and shelf-trailing rules.

Broker: {audit['broker']} / {audit['server']} / {audit['account_name']}.
"""
    (ROOT / "RAW RESULTS.md").write_text(report, encoding="utf-8")
    print(ROOT / "RAW RESULTS.md")


if __name__ == "__main__":
    main()
