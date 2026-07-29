from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
import csv
import json
import math
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5
import pandas as pd

from .config import ROOT


NY = ZoneInfo("America/New_York")
DEFAULT_TERMINAL = r"C:\Program Files\JustMarkets MetaTrader 5\terminal64.exe"


def _clock(name: str, default: str) -> time:
    return datetime.strptime(os.getenv(name, default), "%H:%M").time()


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass
class MidpointTrade:
    session_date: str
    rr: float
    signal_time: str
    entry_time: str
    exit_time: str
    london_high: float
    london_low: float
    london_midpoint: float
    signal_open: float
    signal_close: float
    entry: float
    stop: float
    target: float
    outcome: str
    r_multiple: float
    risk_amount: float
    pnl: float
    balance_after: float
    spread_points: int


def _initialize() -> None:
    path = os.getenv("LONDON_ORB_MT5_PATH", DEFAULT_TERMINAL).strip()
    if not mt5.initialize(path=path):
        raise RuntimeError(f"MT5 initialization failed: {mt5.last_error()}")


def _resolve_us100() -> str:
    preferred = os.getenv("LONDON_ORB_SYMBOL", "US100").upper()
    aliases = ("US100", "NAS100", "USTEC", "NDX100", "NASDAQ100")
    ranked = []
    for symbol in mt5.symbols_get() or []:
        normalized = "".join(character for character in symbol.name.upper() if character.isalnum())
        score = -1
        if normalized == preferred:
            score = 100
        elif normalized.startswith(preferred):
            score = 95
        else:
            for index, alias in enumerate(aliases):
                if normalized == alias:
                    score = max(score, 90 - index)
                elif normalized.startswith(alias):
                    score = max(score, 85 - index)
                elif alias in normalized:
                    score = max(score, 70 - index)
        if score >= 0:
            ranked.append((score, int(symbol.visible), symbol.name))
    if not ranked:
        raise RuntimeError("Could not discover a US100/NAS100 broker symbol.")
    ranked.sort(reverse=True)
    resolved = ranked[0][2]
    if not mt5.symbol_select(resolved, True):
        raise RuntimeError(f"Could not select broker symbol {resolved}.")
    return resolved


def _rates(symbol: str, start: datetime, end: datetime) -> pd.DataFrame:
    raw = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M15, start, end)
    if raw is None:
        raise RuntimeError(f"MT5 history request failed: {mt5.last_error()}")
    frame = pd.DataFrame(raw)
    if frame.empty:
        raise RuntimeError("MT5 returned no M15 history.")
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    return frame.set_index("time").sort_index()


def _local_stamp(day: date, clock: time) -> pd.Timestamp:
    return pd.Timestamp(datetime.combine(day, clock), tz=NY)


def _simulate(
    frame: pd.DataFrame,
    session_date: date,
    rr: float,
    balance: float,
    risk_percent: float,
    point: float,
    london_start: time,
    ny_open: time,
    flat_time: time,
    slippage_points: int,
) -> tuple[MidpointTrade | None, str]:
    local = frame.tz_convert(NY)
    day = local[local.index.date == session_date]
    if day.empty:
        return None, "no_data"

    london_start_stamp = _local_stamp(session_date, london_start)
    ny_open_stamp = _local_stamp(session_date, ny_open)
    signal_end = ny_open_stamp + pd.Timedelta(minutes=15)
    flat_stamp = _local_stamp(session_date, flat_time)
    london = day[
        (day.index >= london_start_stamp) & (day.index < ny_open_stamp)
    ]
    if len(london) < 20:
        return None, "london_range_incomplete"

    signal_rows = day[day.index == ny_open_stamp]
    if signal_rows.empty:
        return None, "opening_candle_missing"
    signal = signal_rows.iloc[0]
    if float(signal["close"]) <= float(signal["open"]):
        return None, "opening_candle_not_green"

    next_rows = day[day.index >= signal_end]
    if next_rows.empty:
        return None, "entry_bar_missing"
    entry_stamp = next_rows.index[0]
    entry_row = next_rows.iloc[0]
    spread_points = int(entry_row.get("spread", 0) or 0)
    entry = (
        float(entry_row["open"])
        + spread_points * point
        + slippage_points * point
    )
    london_high = float(london["high"].max())
    london_low = float(london["low"].min())
    midpoint = (london_high + london_low) / 2.0
    reward_distance = midpoint - entry
    if reward_distance <= point:
        return None, "entry_not_below_london_midpoint"

    risk_distance = reward_distance / rr
    stop = entry - risk_distance
    target = midpoint
    management = day[
        (day.index >= entry_stamp) & (day.index <= flat_stamp)
    ]
    if management.empty:
        return None, "management_window_missing"

    outcome = "session_close"
    exit_stamp = management.index[-1]
    r_multiple = 0.0
    for stamp, row in management.iterrows():
        stop_hit = float(row["low"]) <= stop
        target_hit = float(row["high"]) >= target
        if stop_hit:
            outcome = "stop"
            r_multiple = -1.0
            exit_stamp = stamp
            break
        if target_hit:
            outcome = "target"
            r_multiple = rr
            exit_stamp = stamp
            break
    else:
        exit_row = management.iloc[-1]
        exit_price = float(exit_row["close"])
        r_multiple = (exit_price - entry) / risk_distance

    risk_amount = balance * risk_percent / 100.0
    pnl = risk_amount * r_multiple
    trade = MidpointTrade(
        session_date=session_date.isoformat(),
        rr=rr,
        signal_time=ny_open_stamp.isoformat(),
        entry_time=entry_stamp.isoformat(),
        exit_time=exit_stamp.isoformat(),
        london_high=london_high,
        london_low=london_low,
        london_midpoint=midpoint,
        signal_open=float(signal["open"]),
        signal_close=float(signal["close"]),
        entry=entry,
        stop=stop,
        target=target,
        outcome=outcome,
        r_multiple=r_multiple,
        risk_amount=risk_amount,
        pnl=pnl,
        balance_after=balance + pnl,
        spread_points=spread_points,
    )
    return trade, "trade"


def _metrics(trades: list[MidpointTrade], starting_balance: float) -> dict:
    wins = [trade for trade in trades if trade.pnl > 0]
    losses = [trade for trade in trades if trade.pnl < 0]
    gross_profit = sum(trade.pnl for trade in wins)
    gross_loss = abs(sum(trade.pnl for trade in losses))
    ending = trades[-1].balance_after if trades else starting_balance
    equity = [starting_balance] + [trade.balance_after for trade in trades]
    peak = starting_balance
    max_drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        if peak > 0:
            max_drawdown = max(max_drawdown, (peak - value) / peak * 100.0)
    factor = gross_profit / gross_loss if gross_loss else (
        math.inf if gross_profit else 0.0
    )
    return {
        "starting_balance": round(starting_balance, 2),
        "ending_balance": round(ending, 2),
        "net_profit": round(ending - starting_balance, 2),
        "return_percent": round((ending / starting_balance - 1.0) * 100.0, 2),
        "trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100.0, 2) if trades else 0.0,
        "profit_factor": round(factor, 3) if math.isfinite(factor) else "inf",
        "average_r": round(
            sum(trade.r_multiple for trade in trades) / len(trades), 3
        )
        if trades
        else 0.0,
        "max_drawdown_percent": round(max_drawdown, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
    }


def run() -> dict:
    london_start = _clock("LONDON_ORB_LONDON_START", "03:00")
    ny_open = _clock("LONDON_ORB_NY_OPEN", "09:30")
    flat_time = _clock("LONDON_ORB_FLAT_TIME", "16:00")
    starting_balance = _float("LONDON_ORB_START_BALANCE", 300.0)
    risk_percent = _float("LONDON_ORB_RISK_PERCENT", 0.5)
    slippage_points = int(_float("LONDON_ORB_SLIPPAGE_POINTS", 5))
    end_date = datetime.now(NY).date() - timedelta(days=1)
    start_date = end_date - timedelta(days=92)
    start_utc = datetime.combine(
        start_date - timedelta(days=2), time.min, tzinfo=timezone.utc
    )
    end_utc = datetime.combine(
        end_date + timedelta(days=1), time.min, tzinfo=timezone.utc
    )

    _initialize()
    try:
        symbol = _resolve_us100()
        info = mt5.symbol_info(symbol)
        frame = _rates(symbol, start_utc, end_utc)
    finally:
        mt5.shutdown()

    local_dates = sorted(
        day
        for day in set(frame.index.tz_convert(NY).date)
        if start_date <= day <= end_date and day.weekday() < 5
    )
    results = {}
    all_trades = {}
    screening = {}
    for rr in (1.0, 2.0):
        balance = starting_balance
        trades: list[MidpointTrade] = []
        reasons = Counter()
        for session_date in local_dates:
            trade, reason = _simulate(
                frame,
                session_date,
                rr,
                balance,
                risk_percent,
                info.point,
                london_start,
                ny_open,
                flat_time,
                slippage_points,
            )
            reasons[reason] += 1
            if trade is not None:
                balance = trade.balance_after
                trades.append(trade)
        key = f"1:{int(rr)}"
        results[key] = _metrics(trades, starting_balance)
        all_trades[key] = [asdict(trade) for trade in trades]
        screening[key] = dict(reasons)

    report = {
        "strategy": (
            "US100 long-only: green 09:30 M15 candle, enter next M15 open, "
            "target pre-NY London midpoint"
        ),
        "definition": {
            "timezone": "America/New_York",
            "london_range": f"{london_start:%H:%M}-{ny_open:%H:%M}",
            "ny_signal_candle": f"{ny_open:%H:%M}-"
            f"{(datetime.combine(date.min, ny_open) + timedelta(minutes=15)).time():%H:%M}",
            "entry": "next M15 open plus historical spread and slippage",
            "target": "(London high + London low) / 2",
            "stop_1_1": "entry minus target distance",
            "stop_1_2": "entry minus half the target distance",
            "flat_time": f"{flat_time:%H:%M}",
            "risk_percent": risk_percent,
        },
        "symbol": symbol,
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "results": results,
        "screening": screening,
        "trades": all_trades,
        "warnings": [
            "The target interpretation is the midpoint of the pre-NY London range.",
            "A setup is skipped when the post-signal entry is already above that midpoint.",
            "Same-bar stop/target ambiguity is handled conservatively: stop first.",
            "Broker M15 spread and configured slippage are included; commissions and swaps are not.",
        ],
    }

    report_dir = ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    json_path = report_dir / (
        f"london_midpoint_{symbol}_{start_date}_{end_date}_{stamp}.json"
    )
    csv_path = report_dir / (
        f"london_midpoint_{symbol}_{start_date}_{end_date}_{stamp}.csv"
    )
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fields = list(asdict(next(iter(
            trade
            for key in ("1:1", "1:2")
            for trade in [
                MidpointTrade(**item) for item in all_trades[key]
            ]
        )))) if any(all_trades.values()) else [
            field.name for field in MidpointTrade.__dataclass_fields__.values()
        ]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key in ("1:1", "1:2"):
            writer.writerows(all_trades[key])
    report["report_files"] = {"json": str(json_path), "csv": str(csv_path)}
    return report


def main() -> None:
    report = run()
    print(
        json.dumps(
            {
                "symbol": report["symbol"],
                "period": report["period"],
                "results": report["results"],
                "screening": report["screening"],
                "report_files": report["report_files"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

