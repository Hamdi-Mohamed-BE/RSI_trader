from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RESULTS = ROOT / "Results"
MT5_REPORTS = PROJECT / "Active BAT Backtest 5Y 2026-08-12" / "MT5 Reports"
GLOBAL_AUCTION = PROJECT / "Global Macro Auction Market Research 2026-08-14"
STOCK_AUCTION = PROJECT / "Stock Auction Market Research Exness 2026-08-14"
TERMINAL = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")

STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01
DEVELOPMENT_END = pd.Timestamp("2025-01-01", tz="UTC")
LOCKED_START = pd.Timestamp("2025-08-11", tz="UTC")
TEST_END = pd.Timestamp("2026-08-11", tz="UTC")
WAIT_MINUTES = (5, 10, 15, 20, 30, 60)
MODES = ("entry", "exit", "both")
HARD_LOSS_CAP_R = (1.25, 1.50, 2.00)


@dataclass(frozen=True)
class Trade:
    ea: str
    group: str
    data_key: str
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: int
    entry: float
    stop: float
    target: float | None
    exit_price: float
    exit_reason: str
    base_r: float
    cost_r: float
    evidence: str
    source_file: str


NATIVE_REPORTS = {
    "01-lta-volume-profile.htm": ("LTA Volume Profile", "XAUUSD"),
    "02-orb-volume-profile.htm": ("ORB Volume Profile", "XAUUSD"),
    "03-atr-candle-breakout.htm": ("ATR Candle Breakout", "XAUUSD"),
    "04-aaa-final-asia-breakout.htm": ("Asia Breakout", "XAUUSD"),
    "05-aaa-final-dmc.htm": ("DmC", "XAUUSD"),
    "06-go-long.htm": ("Go Long", "US30"),
    "07-aaa-final-ema3.htm": ("EMA3", "XAUUSD"),
    "08-aaa-final-xau-weakness.htm": ("XAU Weakness", "XAUUSD"),
    "10-nasdaq-overnight.htm": ("Nasdaq Overnight", "USTEC"),
    "11-turnaround-tuesday.htm": ("Turnaround Tuesday", "USTEC"),
    "12-aaa-final-us100-weakness.htm": ("US100 Weakness", "USTEC"),
    "13-aaa-final-news-pulse.htm": ("News Pulse", "XAUUSD"),
}

GLOBAL_SOURCES = {
    "XAU": (PROJECT / "Apex Pulse and IVB Research 2026-08-10" / "Data", "MEXAtlantic-XAU-*-M1-*.csv.gz"),
    "XAG": (PROJECT / "FVG Volume Research 2026-08-14" / "Data", "MEXAtlantic-XAG-*-M1-*.csv.gz"),
    "US30": (PROJECT / "Apex Pulse and IVB Research 2026-08-10" / "Data", "MEXAtlantic-US30-*-M1-*.csv.gz"),
    "US100": (PROJECT / "Apex Pulse and IVB Research 2026-08-10" / "Data", "MEXAtlantic-US100-*-M1-*.csv.gz"),
    "BTC": (PROJECT / "Daily Bias AMD Validation 2026-08-10" / "Data", "MEXAtlantic-BTC-*-M1-*.csv.gz"),
    "ETH": (PROJECT / "FVG Volume Research 2026-08-14" / "Data", "MEXAtlantic-ETH-*-M1-*.csv.gz"),
}

ACTIVE_STOCKS = ("SP500", "NVDA", "MSFT", "AMZN", "GOOGL", "META", "AVGO", "INTC")


def number(value) -> float | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    try:
        return float(str(value).replace(" ", "").replace("\xa0", ""))
    except (TypeError, ValueError):
        return None


def utc(value) -> pd.Timestamp:
    result = pd.Timestamp(value)
    return result.tz_localize("UTC") if result.tzinfo is None else result.tz_convert("UTC")


def native_specs() -> dict[str, dict[str, float]]:
    fallback = {
        "XAUUSD": {"point": 0.001, "tick_size": 0.001, "tick_value": 0.1},
        "USTEC": {"point": 0.01, "tick_size": 0.01, "tick_value": 0.01},
        "US30": {"point": 0.1, "tick_size": 0.1, "tick_value": 0.1},
    }
    if not mt5.initialize(path=str(TERMINAL), timeout=60_000):
        return fallback
    try:
        output = {}
        for symbol, default in fallback.items():
            info = mt5.symbol_info(symbol)
            output[symbol] = default if info is None else {
                "point": float(info.point),
                "tick_size": float(info.trade_tick_size or info.point),
                "tick_value": float(info.trade_tick_value),
            }
        return output
    finally:
        mt5.shutdown()


def parse_native_report(path: Path, ea: str, symbol_key: str, specs: dict[str, dict[str, float]]) -> list[Trade]:
    table = pd.read_html(path, encoding="utf-16")[1]
    orders_marker = next(index for index, row in table.iterrows() if str(row.iloc[0]).strip() == "Orders")
    deals_marker = next(index for index, row in table.iterrows() if str(row.iloc[0]).strip() == "Deals")
    orders = {}
    for _, row in table.iloc[orders_marker + 2:deals_marker - 1].iterrows():
        if pd.isna(row.iloc[1]):
            continue
        orders[str(row.iloc[1]).strip()] = {
            "sl": number(row.iloc[7]), "tp": number(row.iloc[8]), "comment": str(row.iloc[12]),
        }

    open_positions: list[dict] = []
    output: list[Trade] = []
    spec = specs[symbol_key]
    value_per_price_per_lot = spec["tick_value"] / spec["tick_size"]
    for _, row in table.iloc[deals_marker + 2:].iterrows():
        deal_direction = str(row.iloc[4]).strip().lower()
        deal_type = str(row.iloc[3]).strip().lower()
        volume = number(row.iloc[5])
        if deal_direction not in {"in", "out"} or volume is None:
            continue
        detail = {
            "time": utc(str(row.iloc[0]).replace(".", "-")),
            "type": deal_type,
            "volume": volume,
            "price": float(number(row.iloc[6]) or 0.0),
            "commission": float(number(row.iloc[8]) or 0.0),
            "swap": float(number(row.iloc[9]) or 0.0),
            "profit": float(number(row.iloc[10]) or 0.0),
            "comment": "" if pd.isna(row.iloc[12]) else str(row.iloc[12]),
            "order": str(row.iloc[7]).strip(),
        }
        if deal_direction == "in":
            detail.update(orders.get(detail["order"], {}))
            open_positions.append(detail)
            continue

        candidates = [
            (index, entry) for index, entry in enumerate(open_positions)
            if entry["type"] != deal_type and abs(entry["volume"] - volume) < 1e-9
        ]
        if not candidates:
            raise RuntimeError(f"Unmatched exit in {path.name}: {detail}")
        stop_target = re.search(r"\b(sl|tp)\s+([0-9.]+)", detail["comment"], flags=re.I)
        if stop_target:
            field = stop_target.group(1).lower()
            level = float(stop_target.group(2))
            candidates.sort(key=lambda pair: abs((pair[1].get(field) or 1e100) - level))
        position_index, entry = candidates[0]
        open_positions.pop(position_index)
        stop = entry.get("sl")
        if stop is None:
            continue
        direction = 1 if entry["type"] == "buy" else -1
        distance = direction * (entry["price"] - stop)
        if distance <= 0:
            continue
        risk_cash = distance * value_per_price_per_lot * volume
        if risk_cash <= 0:
            continue
        gross_r = direction * (detail["price"] - entry["price"]) / distance
        cash_cost = entry["commission"] + detail["commission"] + entry["swap"] + detail["swap"]
        cost_r = cash_cost / risk_cash
        base_r = gross_r + cost_r
        comment = detail["comment"].lower()
        reason = "stop" if comment.startswith("sl ") else "target" if comment.startswith("tp ") else "other"
        output.append(Trade(
            ea=ea, group="Native MT5", data_key=f"native:{symbol_key}",
            entry_time=entry["time"], exit_time=detail["time"], direction=direction,
            entry=entry["price"], stop=float(stop), target=entry.get("tp"), exit_price=detail["price"],
            exit_reason=reason, base_r=base_r, cost_r=cost_r,
            evidence="MT5 every-tick report; random delay; Exness", source_file=str(path),
        ))
    if open_positions:
        raise RuntimeError(f"Unclosed native positions in {path.name}: {len(open_positions)}")
    return output


def load_native_trades() -> list[Trade]:
    specs = native_specs()
    trades = []
    for filename, (ea, symbol) in NATIVE_REPORTS.items():
        trades.extend(parse_native_report(MT5_REPORTS / filename, ea, symbol, specs))
    return trades


def load_global_auction_trades() -> list[Trade]:
    output = []
    for label in GLOBAL_SOURCES:
        path = GLOBAL_AUCTION / "Results" / f"{label}-selected-trades.csv"
        frame = pd.read_csv(path)
        for row in frame.itertuples(index=False):
            direction = 1 if str(row.direction).lower() == "long" else -1
            entry = float(row.entry)
            stop = float(row.initial_stop)
            distance = direction * (entry - stop)
            base_r = float(row.r_multiple)
            if distance <= 0:
                continue
            exit_price = entry + direction * base_r * distance
            output.append(Trade(
                ea=f"Auction Market {label}", group="Auction market", data_key=f"global:{label}",
                entry_time=utc(row.entry_time_utc), exit_time=utc(row.exit_time_utc), direction=direction,
                entry=entry, stop=stop, target=float(row.target), exit_price=exit_price,
                exit_reason=str(row.exit_reason).lower(), base_r=base_r, cost_r=0.0,
                evidence="Local M1 replay; modeled spread and slippage", source_file=str(path),
            ))
    return output


def load_stock_trades() -> list[Trade]:
    output = []
    base = STOCK_AUCTION / "Results Net Costs 2026-08-14"
    for label in ACTIVE_STOCKS:
        path = base / f"{label}-net-cost-trades.csv"
        frame = pd.read_csv(path)
        for row in frame.itertuples(index=False):
            direction = 1 if str(row.direction).lower() == "long" else -1
            entry = float(row.entry)
            stop = float(row.initial_stop)
            distance = direction * (entry - stop)
            if distance <= 0:
                continue
            base_r = float(row.r_multiple)
            gross_r = float(row.r_before_all_costs)
            exit_price = entry + direction * gross_r * distance
            output.append(Trade(
                ea=f"Auction Stock {label}", group="Auction stock", data_key=f"stock:{label}",
                entry_time=utc(row.entry_time_utc), exit_time=utc(row.exit_time_utc), direction=direction,
                entry=entry, stop=stop, target=float(row.target), exit_price=exit_price,
                exit_reason=str(row.exit_reason).lower(), base_r=base_r, cost_r=base_r - gross_r,
                evidence="Exness M1 replay; spread, slippage, commission, swap", source_file=str(path),
            ))
    return output


def m5_from_m1(frame: pd.DataFrame, point: float) -> pd.DataFrame:
    indexed = frame.set_index("time")
    bars = indexed.resample("5min", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
        spread=("spread", "first"),
    ).dropna().reset_index()
    bars["time"] = pd.to_datetime(bars.time, utc=True)
    bars["end_time"] = bars.time + pd.Timedelta(minutes=5)
    spread_price = bars.spread.to_numpy(float) * point
    positive = spread_price[spread_price > 0]
    bars.attrs["point"] = point
    bars.attrs["median_spread"] = float(np.median(positive)) if len(positive) else 0.0
    return bars


def load_native_m5(symbol: str) -> pd.DataFrame:
    if not mt5.initialize(path=str(TERMINAL), timeout=60_000):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        info = mt5.symbol_info(symbol)
        if info is None or not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"MT5 symbol unavailable: {symbol}")
        chunks = []
        for year in range(2021, 2027):
            start = datetime(year, 1, 1, tzinfo=timezone.utc)
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
            rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start, end)
            if rates is not None and len(rates):
                chunks.append(pd.DataFrame(rates))
        if not chunks:
            raise RuntimeError(f"No MT5 M5 data for {symbol}: {mt5.last_error()}")
        frame = pd.concat(chunks, ignore_index=True)
        frame["time"] = pd.to_datetime(frame.time, unit="s", utc=True)
        frame = frame.sort_values("time").drop_duplicates("time", keep="last")
        frame["end_time"] = frame.time + pd.Timedelta(minutes=5)
        spread_price = frame.spread.to_numpy(float) * float(info.point)
        positive = spread_price[spread_price > 0]
        frame.attrs["point"] = float(info.point)
        frame.attrs["median_spread"] = float(np.median(positive)) if len(positive) else 0.0
        return frame.reset_index(drop=True)
    finally:
        mt5.shutdown()


def load_local_m5(data_directory: Path, pattern: str, point: float) -> pd.DataFrame:
    columns = ["time", "open", "high", "low", "close", "spread"]
    frames = []
    for path in sorted(data_directory.glob(pattern)):
        match = re.search(r"M1-(\d{4})\.csv\.gz$", path.name)
        if match and 2021 <= int(match.group(1)) <= 2026:
            frames.append(pd.read_csv(path, compression="gzip", usecols=columns, parse_dates=["time"]))
    if not frames:
        raise FileNotFoundError(f"No data for {pattern}")
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame.time, utc=True)
    frame = frame.sort_values("time").drop_duplicates("time", keep="last")
    return m5_from_m1(frame, point)


def point_from_manifest(directory: Path, key: str) -> float:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    return float(manifest["instruments"][key]["point"])


def load_all_m5(trades: list[Trade]) -> dict[str, pd.DataFrame]:
    needed = sorted({trade.data_key for trade in trades})
    output = {}
    for key in needed:
        print(f"Loading M5 confirmation data: {key}", flush=True)
        kind, label = key.split(":", 1)
        if kind == "native":
            output[key] = load_native_m5(label)
        elif kind == "global":
            directory, pattern = GLOBAL_SOURCES[label]
            manifest_key = "US100" if label == "US100" else label
            output[key] = load_local_m5(directory, pattern, point_from_manifest(directory, manifest_key))
        elif kind == "stock":
            directory = STOCK_AUCTION / "Data"
            manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))["instruments"][label]
            pattern = f"Exness-{label}-*-M1-*.csv.gz"
            output[key] = load_local_m5(directory, pattern, float(manifest["point"]))
    return output


def bar_arrays(bars: pd.DataFrame) -> dict[str, np.ndarray | float]:
    return {
        "time": bars.time.to_numpy(dtype="datetime64[ns]"),
        "end": bars.end_time.to_numpy(dtype="datetime64[ns]"),
        "open": bars.open.to_numpy(float), "high": bars.high.to_numpy(float),
        "low": bars.low.to_numpy(float), "close": bars.close.to_numpy(float),
        "spread": bars.spread.to_numpy(float) * float(bars.attrs["point"]),
        "median_spread": float(bars.attrs["median_spread"]),
    }


def execution_price(data: dict, timestamp: pd.Timestamp, direction: int, is_entry: bool) -> tuple[pd.Timestamp, float] | None:
    times = data["time"]
    index = int(np.searchsorted(times, timestamp.to_datetime64(), side="left"))
    if index >= len(times):
        return None
    actual = pd.Timestamp(times[index], tz="UTC")
    if actual - timestamp > pd.Timedelta(minutes=15):
        return None
    bid = float(data["open"][index])
    spread = float(data["spread"][index])
    if spread <= 0:
        spread = float(data["median_spread"])
    slippage = 0.25 * float(data["median_spread"])
    if is_entry:
        price = bid + spread + slippage if direction > 0 else bid - slippage
    else:
        price = bid - slippage if direction > 0 else bid + spread + slippage
    return actual, price


def entry_confirmation(trade: Trade, data: dict, wait: int) -> pd.Timestamp | None:
    starts = data["time"]
    begin = int(np.searchsorted(starts, trade.entry_time.to_datetime64(), side="left"))
    deadline = trade.entry_time + pd.Timedelta(minutes=wait)
    for index in range(begin, min(len(starts), begin + wait // 5 + 3)):
        bar_end = pd.Timestamp(data["end"][index], tz="UTC")
        if bar_end > deadline:
            break
        opposite = data["close"][index] < data["open"][index] if trade.direction > 0 else data["close"][index] > data["open"][index]
        if opposite:
            return bar_end
    return None


def stop_confirmation(
    trade: Trade,
    data: dict,
    wait: int,
    entry_price: float,
    risk_distance: float,
    hard_loss_cap_r: float,
) -> tuple[pd.Timestamp, float, str] | None:
    starts = data["time"]
    begin = int(np.searchsorted(starts, trade.exit_time.to_datetime64(), side="left"))
    deadline = trade.exit_time + pd.Timedelta(minutes=wait)
    last_bar_end = None
    for index in range(begin, min(len(starts), begin + wait // 5 + 4)):
        bar_end = pd.Timestamp(data["end"][index], tz="UTC")
        if bar_end > deadline:
            break
        last_bar_end = bar_end
        spread = float(data["spread"][index])
        if spread <= 0:
            spread = float(data["median_spread"])
        slip = 0.25 * float(data["median_spread"])
        hard_exit = entry_price - trade.direction * hard_loss_cap_r * risk_distance
        if trade.direction > 0 and data["low"][index] <= hard_exit:
            price = min(hard_exit, float(data["open"][index])) - slip
            return bar_end, price, "emergency-loss-cap"
        if trade.direction < 0 and data["high"][index] + spread >= hard_exit:
            price = max(hard_exit, float(data["open"][index]) + spread) + slip
            return bar_end, price, "emergency-loss-cap"
        if trade.target is not None:
            target_hit = data["high"][index] >= trade.target if trade.direction > 0 else data["low"][index] <= trade.target
            if target_hit:
                price = trade.target - slip if trade.direction > 0 else trade.target + spread + slip
                return bar_end, price, "target-during-delay"
        favourable = data["close"][index] > data["open"][index] if trade.direction > 0 else data["close"][index] < data["open"][index]
        if favourable:
            fill = execution_price(data, bar_end, trade.direction, is_entry=False)
            if fill is not None:
                return fill[0], fill[1], "fast-stop-confirmation"
    # This is deliberately mandatory. Reverting to the original stop after looking ahead
    # and finding no confirmation would be impossible in live trading.
    if last_bar_end is not None:
        fill = execution_price(data, last_bar_end, trade.direction, is_entry=False)
        if fill is not None:
            return fill[0], fill[1], "maximum-wait-exit"
    fill = execution_price(data, deadline, trade.direction, is_entry=False)
    if fill is not None:
        return fill[0], fill[1], "maximum-wait-exit"
    return None


def apply_overlay(trade: Trade, arrays: dict, mode: str, wait: int, hard_loss_cap_r: float) -> dict:
    entry_time = trade.entry_time
    entry_price = trade.entry
    entry_delay = 0.0
    if mode in {"entry", "both"}:
        confirmation = entry_confirmation(trade, arrays, wait)
        if confirmation is None:
            return {"skipped": True, "reason": "no-opposite-M5"}
        fill = execution_price(arrays, confirmation, trade.direction, is_entry=True)
        if fill is None or fill[0] >= trade.exit_time:
            return {"skipped": True, "reason": "confirmation-after-exit"}
        entry_time, entry_price = fill
        entry_delay = (entry_time - trade.entry_time).total_seconds() / 60.0
    distance = trade.direction * (entry_price - trade.stop)
    if distance <= 0:
        return {"skipped": True, "reason": "structural-stop-invalid-after-wait"}

    exit_time = trade.exit_time
    exit_price = trade.exit_price
    exit_reason = trade.exit_reason
    stop_delay = 0.0
    if mode in {"exit", "both"} and trade.exit_reason == "stop":
        confirmation = stop_confirmation(trade, arrays, wait, entry_price, distance, hard_loss_cap_r)
        if confirmation is not None:
            exit_time, exit_price, exit_reason = confirmation
            stop_delay = (exit_time - trade.exit_time).total_seconds() / 60.0
    original_distance = trade.direction * (trade.entry - trade.stop)
    scaled_cost_r = trade.cost_r * original_distance / distance
    result_r = trade.direction * (exit_price - entry_price) / distance + scaled_cost_r
    return {
        "skipped": False, "r": float(result_r), "entry_time": entry_time, "exit_time": exit_time,
        "entry_delay": entry_delay, "stop_delay": stop_delay, "exit_reason": exit_reason,
    }


def overlay_records(trades: list[Trade], arrays_by_key: dict[str, dict], mode: str, wait: int, hard_loss_cap_r: float) -> list[dict]:
    output = []
    for trade in trades:
        result = apply_overlay(trade, arrays_by_key[trade.data_key], mode, wait, hard_loss_cap_r)
        if result["skipped"]:
            continue
        output.append({
            "ea": trade.ea, "group": trade.group, "entry_time": result["entry_time"],
            "exit_time": result["exit_time"], "r": result["r"], "base_r": trade.base_r,
            "entry_delay": result["entry_delay"], "stop_delay": result["stop_delay"],
        })
    return output


def baseline_records(trades: list[Trade]) -> list[dict]:
    return [{
        "ea": trade.ea, "group": trade.group, "entry_time": trade.entry_time,
        "exit_time": trade.exit_time, "r": trade.base_r, "base_r": trade.base_r,
        "entry_delay": 0.0, "stop_delay": 0.0,
    } for trade in trades]


def stats(records: list[dict], start: pd.Timestamp | None = None, end: pd.Timestamp | None = None) -> dict:
    selected = [row for row in records if (start is None or row["entry_time"] >= start) and (end is None or row["entry_time"] < end)]
    selected.sort(key=lambda row: (row["exit_time"], row["entry_time"], row["ea"]))
    balance = STARTING_BALANCE
    peak = balance
    max_dd = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    equity = []
    for row in selected:
        pnl = balance * RISK_FRACTION * row["r"]
        balance += pnl
        if pnl > 0:
            gross_profit += pnl
            wins += 1
        elif pnl < 0:
            gross_loss += pnl
        peak = max(peak, balance)
        max_dd = max(max_dd, (peak - balance) / peak * 100.0 if peak > 0 else 100.0)
        equity.append((row["exit_time"], balance))
    trades_count = len(selected)
    pf = gross_profit / abs(gross_loss) if gross_loss < 0 else (999.0 if gross_profit > 0 else 0.0)
    return {
        "initial": STARTING_BALANCE, "final": balance, "return_pct": (balance / STARTING_BALANCE - 1.0) * 100.0,
        "closed_equity_max_dd_pct": max_dd, "profit_factor": pf,
        "win_rate_pct": wins / trades_count * 100.0 if trades_count else 0.0,
        "wins": wins, "losses": trades_count - wins, "trades": trades_count,
        "net_r": float(sum(row["r"] for row in selected)),
        "average_r": float(np.mean([row["r"] for row in selected])) if selected else 0.0,
        "median_entry_delay_minutes": float(np.median([row["entry_delay"] for row in selected])) if selected else 0.0,
        "median_stop_delay_minutes": float(np.median([row["stop_delay"] for row in selected if row["stop_delay"] > 0])) if any(row["stop_delay"] > 0 for row in selected) else 0.0,
        "equity": equity,
    }


def candidate_rows(trades: list[Trade], arrays: dict[str, dict]) -> tuple[pd.DataFrame, dict[tuple[str, int, float], list[dict]]]:
    baseline = baseline_records(trades)
    all_records: dict[tuple[str, int, float], list[dict]] = {}
    rows = []
    baseline_dev = stats(baseline, end=DEVELOPMENT_END)
    baseline_val = stats(baseline, start=DEVELOPMENT_END, end=LOCKED_START)
    rows.append({"mode": "baseline", "wait_minutes": 0, "hard_loss_cap_r": 1.0, **{f"dev_{k}": v for k, v in baseline_dev.items() if k != "equity"}, **{f"validation_{k}": v for k, v in baseline_val.items() if k != "equity"}})
    for mode in MODES:
        for wait in WAIT_MINUTES:
            caps = (1.0,) if mode == "entry" else HARD_LOSS_CAP_R
            for cap in caps:
                records = overlay_records(trades, arrays, mode, wait, cap)
                all_records[(mode, wait, cap)] = records
                dev = stats(records, end=DEVELOPMENT_END)
                validation = stats(records, start=DEVELOPMENT_END, end=LOCKED_START)
                rows.append({"mode": mode, "wait_minutes": wait, "hard_loss_cap_r": cap, **{f"dev_{k}": v for k, v in dev.items() if k != "equity"}, **{f"validation_{k}": v for k, v in validation.items() if k != "equity"}})
    frame = pd.DataFrame(rows)
    return frame, all_records


def select_candidate(frame: pd.DataFrame) -> tuple[str, int, float, str, str]:
    baseline = frame.loc[frame["mode"] == "baseline"].iloc[0]
    candidates = frame.loc[frame["mode"] != "baseline"].copy()
    # A candidate must be positive in both pre-lock windows, retain at least 80% of signals,
    # and not materially degrade development PF. The final score is based only on validation.
    candidates = candidates.loc[
        (candidates.dev_net_r > 0) & (candidates.validation_net_r > 0)
        & (candidates.dev_trades >= 0.80 * baseline.dev_trades)
        & (candidates.validation_trades >= 0.80 * baseline.validation_trades)
        & (candidates.dev_profit_factor >= 0.95 * baseline.dev_profit_factor)
    ].copy()
    if candidates.empty:
        return "baseline", 0, 1.0, "No Fast Alpha candidate passed the pre-lock robustness gates.", "REJECT"
    candidates["selection_score"] = (
        candidates.validation_net_r
        + 20.0 * (candidates.validation_profit_factor - 1.0)
        - 0.5 * candidates.validation_closed_equity_max_dd_pct
    )
    best = candidates.sort_values(["selection_score", "dev_profit_factor"], ascending=False).iloc[0]
    baseline_score = (
        baseline.validation_net_r
        + 20.0 * (baseline.validation_profit_factor - 1.0)
        - 0.5 * baseline.validation_closed_equity_max_dd_pct
    )
    improved = (
        best.selection_score > baseline_score
        and best.validation_net_r > baseline.validation_net_r
        and best.validation_profit_factor >= baseline.validation_profit_factor
    )
    status = "PASS" if improved else "REJECT"
    rationale = (
        "Chosen solely on 2025-01-01 to 2025-08-10 validation after development robustness gates."
        if improved else
        "This was the strongest Fast Alpha candidate that passed the development gates, but it did not beat the unchanged baseline in validation, so it is rejected."
    )
    return str(best["mode"]), int(best["wait_minutes"]), float(best["hard_loss_cap_r"]), rationale, status


def comparison_rows(trades: list[Trade], baseline: list[dict], optimized: list[dict]) -> pd.DataFrame:
    rows = []
    eas = sorted({trade.ea for trade in trades})
    periods = {"full": (None, TEST_END), "locked": (LOCKED_START, TEST_END)}
    for ea in eas:
        base_ea = [row for row in baseline if row["ea"] == ea]
        fast_ea = [row for row in optimized if row["ea"] == ea]
        source_trades = [trade for trade in trades if trade.ea == ea]
        for period, (start, end) in periods.items():
            base = stats(base_ea, start, end)
            fast = stats(fast_ea, start, end)
            rows.append({
                "ea": ea, "group": source_trades[0].group, "period": period,
                "baseline_return_pct": base["return_pct"], "fast_return_pct": fast["return_pct"],
                "return_delta_pp": fast["return_pct"] - base["return_pct"],
                "baseline_pf": base["profit_factor"], "fast_pf": fast["profit_factor"],
                "baseline_win_rate_pct": base["win_rate_pct"], "fast_win_rate_pct": fast["win_rate_pct"],
                "baseline_dd_pct": base["closed_equity_max_dd_pct"], "fast_dd_pct": fast["closed_equity_max_dd_pct"],
                "baseline_trades": base["trades"], "fast_trades": fast["trades"],
                "signal_retention_pct": fast["trades"] / base["trades"] * 100.0 if base["trades"] else 0.0,
                "decision": "IMPROVED" if fast["return_pct"] > base["return_pct"] and fast["profit_factor"] >= base["profit_factor"] else "NOT IMPROVED",
            })
    return pd.DataFrame(rows)


def select_per_ea_candidates(
    trades: list[Trade],
    baseline: list[dict],
    records_by_candidate: dict[tuple[str, int, float], list[dict]],
) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    selections = []
    grid_rows = []
    selective_records: list[dict] = []
    for ea in sorted({trade.ea for trade in trades}):
        base_records = [row for row in baseline if row["ea"] == ea]
        base_dev = stats(base_records, end=DEVELOPMENT_END)
        base_val = stats(base_records, DEVELOPMENT_END, LOCKED_START)
        base_locked = stats(base_records, LOCKED_START, TEST_END)
        usable_sample = base_dev["trades"] >= 40 and base_val["trades"] >= 10
        qualifying = []
        for (mode, wait, cap), records in records_by_candidate.items():
            ea_records = [row for row in records if row["ea"] == ea]
            dev = stats(ea_records, end=DEVELOPMENT_END)
            val = stats(ea_records, DEVELOPMENT_END, LOCKED_START)
            locked = stats(ea_records, LOCKED_START, TEST_END)
            dev_retention = dev["trades"] / base_dev["trades"] if base_dev["trades"] else 0.0
            val_retention = val["trades"] / base_val["trades"] if base_val["trades"] else 0.0
            row = {
                "ea": ea, "mode": mode, "wait_minutes": wait, "hard_loss_cap_r": cap,
                "base_dev_return_pct": base_dev["return_pct"], "fast_dev_return_pct": dev["return_pct"],
                "base_dev_pf": base_dev["profit_factor"], "fast_dev_pf": dev["profit_factor"],
                "base_validation_return_pct": base_val["return_pct"], "fast_validation_return_pct": val["return_pct"],
                "base_validation_pf": base_val["profit_factor"], "fast_validation_pf": val["profit_factor"],
                "base_validation_dd_pct": base_val["closed_equity_max_dd_pct"], "fast_validation_dd_pct": val["closed_equity_max_dd_pct"],
                "dev_trades": dev["trades"], "validation_trades": val["trades"],
                "dev_retention_pct": 100.0 * dev_retention, "validation_retention_pct": 100.0 * val_retention,
                "base_locked_return_pct": base_locked["return_pct"], "fast_locked_return_pct": locked["return_pct"],
                "base_locked_pf": base_locked["profit_factor"], "fast_locked_pf": locked["profit_factor"],
                "base_locked_dd_pct": base_locked["closed_equity_max_dd_pct"], "fast_locked_dd_pct": locked["closed_equity_max_dd_pct"],
                "base_locked_trades": base_locked["trades"], "fast_locked_trades": locked["trades"],
            }
            grid_rows.append(row)
            development_floor = 0.90 * base_dev["net_r"] if base_dev["net_r"] > 0 else base_dev["net_r"]
            dd_limit = max(base_val["closed_equity_max_dd_pct"] + 2.0, 1.20 * base_val["closed_equity_max_dd_pct"])
            passes = (
                usable_sample and dev_retention >= 0.80 and val_retention >= 0.80
                and dev["net_r"] >= development_floor
                and dev["profit_factor"] >= 0.95 * base_dev["profit_factor"]
                and val["net_r"] > base_val["net_r"]
                and val["profit_factor"] >= base_val["profit_factor"]
                and val["closed_equity_max_dd_pct"] <= dd_limit
            )
            if passes:
                row["selection_score"] = (
                    val["net_r"] - base_val["net_r"]
                    + 10.0 * (val["profit_factor"] - base_val["profit_factor"])
                    - 0.25 * max(0.0, val["closed_equity_max_dd_pct"] - base_val["closed_equity_max_dd_pct"])
                )
                row["records"] = ea_records
                qualifying.append(row)

        if qualifying:
            chosen = max(qualifying, key=lambda row: row["selection_score"])
            oos_confirmed = (
                chosen["fast_locked_return_pct"] >= chosen["base_locked_return_pct"] + 1.0
                and chosen["fast_locked_pf"] >= chosen["base_locked_pf"]
                and chosen["fast_locked_dd_pct"] <= max(chosen["base_locked_dd_pct"] + 1.0, 1.15 * chosen["base_locked_dd_pct"])
            )
            selections.append({
                **{key: value for key, value in chosen.items() if key not in {"records", "selection_score"}},
                "prelock_decision": "PASS", "locked_oos": "CONFIRMED" if oos_confirmed else "FAILED",
            })
            selective_records.extend(chosen["records"])
        else:
            selections.append({
                "ea": ea, "mode": "baseline", "wait_minutes": 0, "hard_loss_cap_r": 1.0,
                "base_dev_return_pct": base_dev["return_pct"], "fast_dev_return_pct": base_dev["return_pct"],
                "base_dev_pf": base_dev["profit_factor"], "fast_dev_pf": base_dev["profit_factor"],
                "base_validation_return_pct": base_val["return_pct"], "fast_validation_return_pct": base_val["return_pct"],
                "base_validation_pf": base_val["profit_factor"], "fast_validation_pf": base_val["profit_factor"],
                "base_validation_dd_pct": base_val["closed_equity_max_dd_pct"], "fast_validation_dd_pct": base_val["closed_equity_max_dd_pct"],
                "dev_trades": base_dev["trades"], "validation_trades": base_val["trades"],
                "dev_retention_pct": 100.0, "validation_retention_pct": 100.0,
                "base_locked_return_pct": base_locked["return_pct"], "fast_locked_return_pct": base_locked["return_pct"],
                "base_locked_pf": base_locked["profit_factor"], "fast_locked_pf": base_locked["profit_factor"],
                "base_locked_dd_pct": base_locked["closed_equity_max_dd_pct"], "fast_locked_dd_pct": base_locked["closed_equity_max_dd_pct"],
                "base_locked_trades": base_locked["trades"], "fast_locked_trades": base_locked["trades"],
                "prelock_decision": "INSUFFICIENT" if not usable_sample else "REJECT",
                "locked_oos": "NOT TESTED",
            })
            selective_records.extend(base_records)
    return pd.DataFrame(selections), pd.DataFrame(grid_rows), selective_records


def plot_equity(baseline: list[dict], optimized: list[dict], path: Path, start=None, end=None, title="") -> None:
    fig, ax = plt.subplots(figsize=(13, 6.5))
    for records, label, color in [(baseline, "Current BAT baseline", "#7f8c8d"), (optimized, "Best Fast Alpha candidate", "#00a878")]:
        selected = [row for row in records if (start is None or row["entry_time"] >= start) and (end is None or row["entry_time"] < end)]
        selected.sort(key=lambda row: (row["exit_time"], row["entry_time"], row["ea"]))
        if selected:
            curve = STARTING_BALANCE + STARTING_BALANCE * RISK_FRACTION * np.cumsum([row["r"] for row in selected])
            ax.plot([row["exit_time"] for row in selected], curve, label=label, color=color, linewidth=1.6)
    ax.axhline(STARTING_BALANCE, color="#444", linewidth=0.8, linestyle="--")
    ax.set_title(title)
    ax.set_ylabel("Risk-normalized closed equity (USD; fixed $100 = 1R)")
    ax.grid(alpha=0.2)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def plot_per_ea(frame: pd.DataFrame, path: Path) -> None:
    locked = frame.loc[frame["period"] == "locked"].sort_values("return_delta_pp")
    colors = ["#00a878" if value > 0 else "#c44536" for value in locked.return_delta_pp]
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.barh(locked.ea, locked.return_delta_pp, color=colors)
    ax.axvline(0, color="#222", linewidth=0.8)
    ax.set_xlabel("Locked-year return change (percentage points)")
    ax.set_title("Fast Alpha impact by active EA — locked final year")
    ax.grid(axis="x", alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=170)
    plt.close(fig)


def markdown_table(frame: pd.DataFrame, period: str) -> str:
    rows = frame.loc[frame["period"] == period].sort_values("fast_return_pct", ascending=False)
    lines = [
        "| EA | Base return | Fast return | Delta | Base/Fast PF | Base/Fast win | Base/Fast DD* | Trades retained | Verdict |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for row in rows.itertuples(index=False):
        lines.append(
            f"| {row.ea} | {row.baseline_return_pct:+.2f}% | {row.fast_return_pct:+.2f}% | {row.return_delta_pp:+.2f} pp | "
            f"{row.baseline_pf:.2f}/{row.fast_pf:.2f} | {row.baseline_win_rate_pct:.1f}%/{row.fast_win_rate_pct:.1f}% | "
            f"{row.baseline_dd_pct:.2f}%/{row.fast_dd_pct:.2f}% | {row.fast_trades}/{row.baseline_trades} ({row.signal_retention_pct:.1f}%) | {row.decision} |"
        )
    return "\n".join(lines)


def write_report(
    trades: list[Trade], candidates: pd.DataFrame, mode: str, wait: int, hard_loss_cap_r: float,
    rationale: str, status: str, baseline: list[dict], optimized: list[dict], comparison: pd.DataFrame,
    per_ea_selection: pd.DataFrame, selective_records: list[dict], selective_comparison: pd.DataFrame,
) -> None:
    full_base = stats(baseline, end=TEST_END)
    full_fast = stats(optimized, end=TEST_END)
    locked_base = stats(baseline, LOCKED_START, TEST_END)
    locked_fast = stats(optimized, LOCKED_START, TEST_END)
    selective_full = stats(selective_records, end=TEST_END)
    selective_locked = stats(selective_records, LOCKED_START, TEST_END)
    source_counts = pd.DataFrame([asdict(trade) for trade in trades]).groupby(["group", "ea"]).size().reset_index(name="trades")
    candidate_view = candidates.loc[:, [
        "mode", "wait_minutes", "hard_loss_cap_r", "dev_return_pct", "dev_profit_factor", "dev_closed_equity_max_dd_pct", "dev_trades",
        "validation_return_pct", "validation_profit_factor", "validation_closed_equity_max_dd_pct", "validation_trades",
    ]].sort_values(["validation_return_pct", "dev_return_pct"], ascending=False)
    candidate_lines = [
        "| Mode | Wait | Emergency cap | Dev return | Dev PF | Dev DD* | Dev trades | Validation return | Validation PF | Validation DD* | Validation trades |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in candidate_view.itertuples(index=False):
        candidate_lines.append(
            f"| {row.mode} | {row.wait_minutes}m | {row.hard_loss_cap_r:.2f}R | {row.dev_return_pct:+.2f}% | {row.dev_profit_factor:.2f} | {row.dev_closed_equity_max_dd_pct:.2f}% | {row.dev_trades} | "
            f"{row.validation_return_pct:+.2f}% | {row.validation_profit_factor:.2f} | {row.validation_closed_equity_max_dd_pct:.2f}% | {row.validation_trades} |"
        )

    per_ea_lines = [
        "| EA | Pre-lock | Rule | Validation base/fast | Locked base/fast | Locked PF base/fast | Locked DD* base/fast | Locked trades | OOS |",
        "|---|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in per_ea_selection.sort_values(["prelock_decision", "ea"]).itertuples(index=False):
        rule = "unchanged" if row.mode == "baseline" else f"{row.mode} / {row.wait_minutes}m / {row.hard_loss_cap_r:.2f}R"
        per_ea_lines.append(
            f"| {row.ea} | {row.prelock_decision} | {rule} | {row.base_validation_return_pct:+.2f}%/{row.fast_validation_return_pct:+.2f}% | "
            f"{row.base_locked_return_pct:+.2f}%/{row.fast_locked_return_pct:+.2f}% | {row.base_locked_pf:.2f}/{row.fast_locked_pf:.2f} | "
            f"{row.base_locked_dd_pct:.2f}%/{row.fast_locked_dd_pct:.2f}% | {row.fast_locked_trades}/{row.base_locked_trades} | {row.locked_oos} |"
        )

    def summary_line(name: str, base: dict, fast: dict) -> str:
        return (
            f"| {name} | {base['return_pct']:+.2f}% | {fast['return_pct']:+.2f}% | {fast['return_pct']-base['return_pct']:+.2f} pp | {base['net_r']:+.2f}R | {fast['net_r']:+.2f}R | "
            f"{base['profit_factor']:.2f} | {fast['profit_factor']:.2f} | {base['win_rate_pct']:.2f}% | {fast['win_rate_pct']:.2f}% | "
            f"{base['closed_equity_max_dd_pct']:.2f}% | {fast['closed_equity_max_dd_pct']:.2f}% | {base['trades']} | {fast['trades']} |"
        )

    report = f"""# Fast Alpha optimization — currently configured BAT portfolio

Generated: {datetime.now(timezone.utc).isoformat()}

## Decision: {status}

The strongest pre-lock candidate was **{mode.upper()} with a {wait}-minute maximum wait and a {hard_loss_cap_r:.2f}R emergency loss cap**. {rationale}

This is a research overlay only. **The live BAT and EA files were not changed.** The rule follows the paper: the slow EA still decides direction, stop and target; a long waits for one red M5 candle and a short waits for one green M5 candle; a stop exit may wait for one M5 candle favorable to the open position. If no entry confirmation appears inside the time cap, the signal is skipped. A delayed stop exits at the first favorable M5 close, the original target, the emergency loss cap, or the maximum-wait market exit—whichever occurs first. This removes look-ahead and prevents an unlimited delayed-stop loss.

## Portfolio result

All figures below normalize every retained trade to **1% equity risk at its unchanged structural stop**, starting from **$10,000**. Costs already present in each source test are retained. `DD*` is closed-equity drawdown; it is not tick-level floating drawdown.

The compounded percentages below are a serial 1%-risk normalization, **not a realistic shared-account forecast**. The `net R` columns and fixed-$100-risk graphs are the safer combined comparison because the active EAs can overlap.

| Period | Base serial return | Fast serial return | Delta | Base net R | Fast net R | Base PF | Fast PF | Base win | Fast win | Base DD* | Fast DD* | Base trades | Fast trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{summary_line('Full available history', full_base, full_fast)}
{summary_line('Locked final year (2025-08-11 to 2026-08-10)', locked_base, locked_fast)}

![Full-history combined equity](Results/fast-alpha-combined-full.png)

![Locked-year combined equity](Results/fast-alpha-combined-locked.png)

![Locked-year EA impact](Results/fast-alpha-locked-impact-by-ea.png)

## Locked final year by EA

{markdown_table(comparison, 'locked')}

## Per-EA walk-forward optimization

This second pass allowed a different Fast Alpha timing rule per EA, but still chose every rule before the locked year. EAs with fewer than 40 development trades or 10 validation trades were marked insufficient instead of optimized.

| Portfolio construction | Base net R | Candidate net R | Base PF | Candidate PF | Base DD* | Candidate DD* | Base trades | Candidate trades |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Full available history | {full_base['net_r']:+.2f}R | {selective_full['net_r']:+.2f}R | {full_base['profit_factor']:.2f} | {selective_full['profit_factor']:.2f} | {full_base['closed_equity_max_dd_pct']:.2f}% | {selective_full['closed_equity_max_dd_pct']:.2f}% | {full_base['trades']} | {selective_full['trades']} |
| Locked final year | {locked_base['net_r']:+.2f}R | {selective_locked['net_r']:+.2f}R | {locked_base['profit_factor']:.2f} | {selective_locked['profit_factor']:.2f} | {locked_base['closed_equity_max_dd_pct']:.2f}% | {selective_locked['closed_equity_max_dd_pct']:.2f}% | {locked_base['trades']} | {selective_locked['trades']} |

![Per-EA selective full-history equity](Results/fast-alpha-selective-full.png)

![Per-EA selective locked-year equity](Results/fast-alpha-selective-locked.png)

{chr(10).join(per_ea_lines)}

## Full available history by EA

{markdown_table(comparison, 'full')}

## Pre-lock optimization grid

Development ends 2024-12-31. Validation is 2025-01-01 through 2025-08-10. The locked year was not used to choose the setting.

{chr(10).join(candidate_lines)}

## Evidence and limits

- Native group: twelve real MT5 Strategy Tester reports, Exness, every tick, random execution delay, 2021-08-11 to 2026-08-10.
- Auction-market group: six local M1 replays with spread and slippage, beginning in 2022.
- Auction-stock group: eight active PF>=2 stock/index selections on Exness M1 data, with spread, 25% spread slippage, commission and swap estimates, beginning in 2022.
- This is an **execution-overlay replay**, not a newly compiled tick-by-tick MT5 test of modified EAs. It changes only entry/stop-exit timing and keeps each original slow signal and structural levels.
- The combined curve serializes closed trades. It does not reconstruct simultaneous floating P/L, margin pressure, cross-EA correlation or gaps, so true account-level maximum drawdown can be higher.
- A delayed stop can lose more than 1R. Position size is normalized at the actual delayed entry so the structural stop starts at 1% planned risk; gaps and delayed exits can exceed it.
- Small samples (especially News Pulse and several stock EAs) are not sufficient to claim a durable edge.
- Three active binaries (ATR Candle Breakout, Go Long, Turnaround Tuesday) have no editable source in this package. Their result is research-only unless source code is obtained or a separate execution wrapper is built.

## Source coverage

{source_counts.to_markdown(index=False)}
"""
    (ROOT / "FAST ALPHA APPLIED EAS REPORT.md").write_text(report, encoding="utf-8")


def main() -> int:
    RESULTS.mkdir(parents=True, exist_ok=True)
    print("Parsing current BAT evidence...", flush=True)
    trades = load_native_trades() + load_global_auction_trades() + load_stock_trades()
    expected = 12 + 6 + len(ACTIVE_STOCKS)
    eas = sorted({trade.ea for trade in trades})
    if len(eas) != expected:
        raise RuntimeError(f"Expected {expected} active EAs, found {len(eas)}: {eas}")
    bars = load_all_m5(trades)
    arrays = {key: bar_arrays(value) for key, value in bars.items()}
    print("Running pre-lock optimization grid...", flush=True)
    candidates, records_by_candidate = candidate_rows(trades, arrays)
    mode, wait, hard_loss_cap_r, rationale, status = select_candidate(candidates)
    baseline = baseline_records(trades)
    optimized = baseline if mode == "baseline" else records_by_candidate[(mode, wait, hard_loss_cap_r)]
    comparison = comparison_rows(trades, baseline, optimized)
    per_ea_selection, per_ea_grid, selective_records = select_per_ea_candidates(trades, baseline, records_by_candidate)
    selective_comparison = comparison_rows(trades, baseline, selective_records)

    candidates.to_csv(RESULTS / "optimization-grid.csv", index=False)
    comparison.to_csv(RESULTS / "per-ea-comparison.csv", index=False)
    per_ea_selection.to_csv(RESULTS / "per-ea-selected-configs.csv", index=False)
    per_ea_grid.to_csv(RESULTS / "per-ea-optimization-grid.csv", index=False)
    selective_comparison.to_csv(RESULTS / "per-ea-selective-comparison.csv", index=False)
    pd.DataFrame(optimized).to_csv(RESULTS / "selected-overlay-trades.csv", index=False)
    pd.DataFrame(selective_records).to_csv(RESULTS / "selective-overlay-trades.csv", index=False)
    selection = {"decision": status, "mode": mode, "wait_minutes": wait, "hard_loss_cap_r": hard_loss_cap_r, "rationale": rationale, "locked_start": str(LOCKED_START), "test_end": str(TEST_END)}
    (RESULTS / "selected-config.json").write_text(json.dumps(selection, indent=2), encoding="utf-8")
    plot_equity(baseline, optimized, RESULTS / "fast-alpha-combined-full.png", end=TEST_END, title="Current BAT portfolio: baseline vs Fast Alpha — full available history")
    plot_equity(baseline, optimized, RESULTS / "fast-alpha-combined-locked.png", LOCKED_START, TEST_END, "Current BAT portfolio: locked final year")
    plot_per_ea(comparison, RESULTS / "fast-alpha-locked-impact-by-ea.png")
    plot_equity(baseline, selective_records, RESULTS / "fast-alpha-selective-full.png", end=TEST_END, title="Per-EA walk-forward Fast Alpha: full available history")
    plot_equity(baseline, selective_records, RESULTS / "fast-alpha-selective-locked.png", LOCKED_START, TEST_END, "Per-EA walk-forward Fast Alpha: locked final year")
    write_report(trades, candidates, mode, wait, hard_loss_cap_r, rationale, status, baseline, optimized, comparison, per_ea_selection, selective_records, selective_comparison)
    print(json.dumps({
        "active_eas": len(eas), "source_trades": len(trades), "selected": selection,
        "full_baseline": {k: v for k, v in stats(baseline, end=TEST_END).items() if k != "equity"},
        "full_fast": {k: v for k, v in stats(optimized, end=TEST_END).items() if k != "equity"},
        "locked_baseline": {k: v for k, v in stats(baseline, LOCKED_START, TEST_END).items() if k != "equity"},
        "locked_fast": {k: v for k, v in stats(optimized, LOCKED_START, TEST_END).items() if k != "equity"},
    }, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
