from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
import argparse
import json
from pathlib import Path
import sys
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import REPORTS_DIR, load_config
from app.mt5_client import MT5Client
from app.risk_manager import DEFAULT_CONTRACT_SIZES
from app.strategy_engine import generate_signal


ACTIVE_SYMBOLS = ("XAUUSD", "XAGUSD", "BTCUSD", "US30", "US100")
DISABLED_FOREX_SYMBOLS = (
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCAD",
    "AUDUSD",
    "NZDUSD",
    "USDCHF",
)
OTHER_PREVIOUS_SYMBOLS: tuple[str, ...] = ()
DEFAULT_SYMBOLS = (*ACTIVE_SYMBOLS, *OTHER_PREVIOUS_SYMBOLS, *DISABLED_FOREX_SYMBOLS)
DEFAULT_TIMEFRAMES = ("M15", "M30", "H1")
PROFILE_LOOKBACK_BARS = {"M5": 5000, "M15": 2200, "M30": 1200, "H1": 700, "H4": 350, "D1": 180}
WARMUP_DAYS = {"M5": 45, "M15": 45, "M30": 60, "H1": 90, "H4": 180, "D1": 540}


@dataclass(frozen=True)
class Candidate:
    index: int
    signal: dict[str, Any]


@dataclass
class Trade:
    min_score: int
    rr: int
    symbol: str
    timeframe: str
    month: str
    opened_at: str
    closed_at: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    exit_price: float
    result: str
    max_stage: int
    exit_stop_r: float
    pnl: float
    r_multiple: float
    setup_score: int
    entry_model: str
    session: str
    profile_type: str
    key_level: str
    volume_source: str
    volume_regime: str
    volume_ratio: float
    spread_r: float


def parse_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(item.strip().upper() for item in value.split(",") if item.strip())


def date_bounds(start: date | None, end: date | None) -> tuple[datetime, datetime]:
    end_date = end or date.today()
    start_date = start or end_date - timedelta(days=31)
    return datetime.combine(start_date, time.min), datetime.combine(end_date, time.max)


def log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def target_for_rr(signal: dict[str, Any], rr: int) -> float:
    direction = str(signal["direction"]).upper()
    entry = float(signal["entry"])
    stop = float(signal["stop_loss"])
    risk = abs(entry - stop)
    return entry + risk * rr if direction == "BUY" else entry - risk * rr


def simulate_trade(
    candles: pd.DataFrame,
    start_index: int,
    signal: dict[str, Any],
    rr: int,
    max_holding_bars: int,
) -> tuple[int, float, str, datetime, int, float]:
    direction = str(signal["direction"]).upper()
    entry = float(signal["entry"])
    stop = float(signal["stop_loss"])
    risk = abs(entry - stop)
    target = target_for_rr(signal, rr)
    end_index = min(len(candles) - 1, start_index + max_holding_bars)
    current_stop_r = -1.0
    max_stage = 0

    for idx in range(start_index + 1, end_index + 1):
        row = candles.iloc[idx]
        high = float(row["high"])
        low = float(row["low"])
        current_stop = entry + risk * current_stop_r if direction == "BUY" else entry - risk * current_stop_r
        if direction == "BUY":
            hit_stop = low <= current_stop
            hit_target = high >= target
        else:
            hit_stop = high >= current_stop
            hit_target = low <= target

        # Conservative intrabar ordering: the stop active at candle open is checked first.
        if hit_stop:
            result = "loss" if current_stop_r < -0.05 else "break_even" if current_stop_r < 0.05 else "trail_stop"
            return idx, current_stop, result, pd.Timestamp(row["time"]).to_pydatetime(), max_stage, current_stop_r
        if hit_target:
            return idx, target, "win", pd.Timestamp(row["time"]).to_pydatetime(), max(max_stage, rr), float(rr)

        favorable_r = (high - entry) / risk if direction == "BUY" else (entry - low) / risk
        reached_stage = min(rr - 1, max(0, int(favorable_r)))
        if reached_stage > max_stage:
            max_stage = reached_stage
            current_stop_r = 0.0 if max_stage == 1 else float(max_stage - 1)

    row = candles.iloc[end_index]
    return (
        end_index,
        float(row["close"]),
        "timeout",
        pd.Timestamp(row["time"]).to_pydatetime(),
        max_stage,
        current_stop_r,
    )


def pnl_for(symbol: str, direction: str, lot: float, contract_size: float, entry: float, exit_price: float) -> float:
    if direction == "BUY":
        return (exit_price - entry) * contract_size * lot
    return (entry - exit_price) * contract_size * lot


def collect_candidates(
    candles: pd.DataFrame,
    symbol: str,
    timeframe: str,
    min_score: int,
    stride: int,
    signal_lookback_bars: int,
    signal_start: datetime,
    signal_end: datetime,
) -> list[Candidate]:
    candidates: list[Candidate] = []
    eligible = candles.index[pd.to_datetime(candles["time"]) >= signal_start].tolist()
    i = max(120, eligible[0] if eligible else len(candles))
    checked = 0
    while i < len(candles) - 2:
        start_index = max(0, i + 1 - signal_lookback_bars)
        signal = generate_signal(
            candles.iloc[start_index : i + 1],
            symbol=symbol,
            timeframe=timeframe,
            min_score=min_score,
            min_rr=1.0,
        )
        signal_time = pd.Timestamp(candles.iloc[i]["time"]).to_pydatetime()
        if signal_time > signal_end:
            break
        if signal and signal.get("status") == "allowed" and int(signal.get("setup_score") or 0) >= min_score:
            if signal.get("entry") is not None and signal.get("stop_loss") is not None:
                candidates.append(Candidate(index=i, signal=signal))
        i += stride
        checked += 1
        if checked % 1000 == 0:
            log(f"{symbol} {timeframe}: checked {checked} points, candidates={len(candidates)}")
    return candidates


def candidates_from_rows(
    candles: pd.DataFrame,
    rows: pd.DataFrame,
    symbol: str,
    timeframe: str,
    min_score: int,
) -> list[Candidate]:
    if rows.empty:
        return []
    selected = rows[
        (rows["symbol"].astype(str).str.upper() == symbol.upper())
        & (rows["timeframe"].astype(str).str.upper() == timeframe.upper())
        & (pd.to_numeric(rows["setup_score"], errors="coerce").fillna(0) >= min_score)
    ].copy()
    if "min_score" in selected.columns:
        selected = selected[pd.to_numeric(selected["min_score"], errors="coerce").fillna(0) == min_score]
    if "rr" in selected.columns:
        selected = selected[pd.to_numeric(selected["rr"], errors="coerce").fillna(0) == 1]
    selected = selected.drop_duplicates(
        subset=["opened_at", "direction", "entry", "stop_loss", "setup_score"],
        keep="last",
    ).sort_values("opened_at")

    candle_times = pd.to_datetime(candles["time"]).reset_index(drop=True)
    out: list[Candidate] = []
    for row in selected.to_dict(orient="records"):
        opened_at = pd.Timestamp(row["opened_at"])
        index = int(candle_times.searchsorted(opened_at, side="left"))
        if index >= len(candles):
            continue
        signal = {
            "timestamp": opened_at.to_pydatetime(),
            "direction": str(row.get("direction") or "").upper(),
            "entry": float(row.get("entry") or 0.0),
            "stop_loss": float(row.get("stop_loss") or 0.0),
            "setup_score": int(row.get("setup_score") or 0),
            "entry_model": str(row.get("entry_model") or ""),
            "session": str(row.get("session") or ""),
            "profile_type": str(row.get("profile_type") or ""),
            "key_level": str(row.get("key_level") or ""),
            "volume_source": str(row.get("volume_source") or ""),
            "volume_regime": str(row.get("volume_regime") or ""),
            "volume_ratio": float(row.get("volume_ratio") or 1.0),
        }
        if signal["direction"] in {"BUY", "SELL"} and signal["entry"] > 0 and signal["stop_loss"] > 0:
            out.append(Candidate(index=index, signal=signal))
    return out


def replay_rr(
    candles: pd.DataFrame,
    candidates: list[Candidate],
    symbol: str,
    timeframe: str,
    rr: int,
    lot: float,
    contract_size: float,
    stride: int,
    max_holding_bars: int,
    min_score: int,
    point_size: float,
) -> list[Trade]:
    trades: list[Trade] = []
    next_allowed_index = 0
    for candidate in candidates:
        if int(candidate.signal.get("setup_score") or 0) < min_score:
            continue
        if candidate.index < next_allowed_index:
            continue
        signal = candidate.signal
        entry = float(signal["entry"])
        stop = float(signal["stop_loss"])
        if entry <= 0 or stop <= 0 or entry == stop:
            continue
        exit_index, exit_price, result, closed_at, max_stage, exit_stop_r = simulate_trade(
            candles,
            candidate.index,
            signal,
            rr,
            max_holding_bars,
        )
        direction = str(signal["direction"]).upper()
        risk_amount = max(abs(entry - stop) * contract_size * lot, 1e-9)
        raw_pnl = pnl_for(symbol, direction, lot, contract_size, entry, exit_price)
        try:
            spread_points = max(0.0, float(candles.iloc[candidate.index].get("spread") or 0.0))
        except (TypeError, ValueError):
            spread_points = 0.0
        spread_price = spread_points * max(point_size, 0.0)
        spread_r = spread_price / max(abs(entry - stop), 1e-9)
        r_multiple = raw_pnl / risk_amount - spread_r
        pnl = risk_amount * r_multiple
        opened_at = pd.Timestamp(signal["timestamp"]).to_pydatetime()
        trades.append(
            Trade(
                min_score=min_score,
                rr=rr,
                symbol=symbol,
                timeframe=timeframe,
                month=opened_at.strftime("%Y-%m"),
                opened_at=opened_at.isoformat(sep=" ", timespec="seconds"),
                closed_at=closed_at.isoformat(sep=" ", timespec="seconds"),
                direction=direction,
                entry=round(entry, 6),
                stop_loss=round(stop, 6),
                take_profit=round(target_for_rr(signal, rr), 6),
                exit_price=round(float(exit_price), 6),
                result=result,
                max_stage=int(max_stage),
                exit_stop_r=round(float(exit_stop_r), 3),
                pnl=round(float(pnl), 2),
                r_multiple=round(float(r_multiple), 4),
                setup_score=int(signal.get("setup_score") or 0),
                entry_model=str(signal.get("entry_model") or ""),
                session=str(signal.get("session") or ""),
                profile_type=str(signal.get("profile_type") or ""),
                key_level=str(signal.get("key_level") or ""),
                volume_source=str(signal.get("volume_source") or ""),
                volume_regime=str(signal.get("volume_regime") or ""),
                volume_ratio=round(float(signal.get("volume_ratio") or 1.0), 4),
                spread_r=round(float(spread_r), 4),
            )
        )
        next_allowed_index = max(exit_index + 1, candidate.index + stride)
    return trades


def summarize_trades(trades: list[dict[str, Any]], group_cols: list[str]) -> pd.DataFrame:
    columns = [
        *group_cols,
        "trades",
        "wins",
        "losses",
        "trail_stops",
        "break_evens",
        "timeouts",
        "win_rate",
        "net_r",
        "avg_r",
        "gross_r",
        "loss_r",
        "profit_factor",
        "net_pnl",
        "avg_pnl",
    ]
    if not trades:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(trades)
    rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(group_cols, dropna=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        r_values = group["r_multiple"].astype(float)
        pnl_values = group["pnl"].astype(float)
        gross_r = float(r_values[r_values > 0].sum())
        loss_r = abs(float(r_values[r_values < 0].sum()))
        wins = int((group["result"] == "win").sum())
        losses = int((group["result"] == "loss").sum())
        trail_stops = int((group["result"] == "trail_stop").sum())
        break_evens = int((group["result"] == "break_even").sum())
        timeouts = int((group["result"] == "timeout").sum())
        total = int(len(group))
        row = dict(zip(group_cols, keys))
        row.update(
            {
                "trades": total,
                "wins": wins,
                "losses": losses,
                "trail_stops": trail_stops,
                "break_evens": break_evens,
                "timeouts": timeouts,
                "win_rate": round(wins / total * 100, 2) if total else 0.0,
                "net_r": round(float(r_values.sum()), 2),
                "avg_r": round(float(r_values.mean()), 3) if total else 0.0,
                "gross_r": round(gross_r, 2),
                "loss_r": round(loss_r, 2),
                "profit_factor": round(gross_r / loss_r, 2) if loss_r else round(gross_r, 2),
                "net_pnl": round(float(pnl_values.sum()), 2),
                "avg_pnl": round(float(pnl_values.mean()), 2) if total else 0.0,
            }
        )
        rows.append(row)
    return pd.DataFrame(rows, columns=columns).sort_values(group_cols).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep book-aligned LTA volume-profile entries over MT5 history.")
    parser.add_argument("--symbols", default=None, help="Comma-separated symbols. Defaults to active plus disabled forex.")
    parser.add_argument("--timeframes", default=None, help="Comma-separated timeframes. Defaults to AUTO_SCAN style set.")
    parser.add_argument("--start", default=None, help="Start date in YYYY-MM-DD. Defaults to end minus 31 days.")
    parser.add_argument("--end", default=None, help="End date in YYYY-MM-DD. Defaults to today.")
    parser.add_argument("--rrs", default="1,2,3,4,5,6,8", help="Comma-separated forced RR targets.")
    parser.add_argument("--score-thresholds", default="80,85,90,95", help="Comma-separated setup-score thresholds.")
    parser.add_argument("--stride", type=int, default=None, help="Signal scan step. Defaults to BACKTEST_SIGNAL_STRIDE.")
    parser.add_argument("--min-score", type=int, default=None, help="A+ minimum score. Defaults to MIN_SETUP_SCORE.")
    parser.add_argument("--max-holding-bars", type=int, default=96)
    parser.add_argument(
        "--candidate-csv",
        action="append",
        default=[],
        help="Reuse saved trades_all_rr.csv candidates. May be passed more than once.",
    )
    parser.add_argument(
        "--signal-lookback-bars",
        type=int,
        default=0,
        help="Candles fed into each signal check. Zero uses a timeframe-aware multiweek profile window.",
    )
    args = parser.parse_args()

    config = load_config()
    symbols = parse_csv(args.symbols, DEFAULT_SYMBOLS)
    timeframes = parse_csv(args.timeframes, DEFAULT_TIMEFRAMES)
    stride = max(1, int(args.stride if args.stride is not None else config.backtest_signal_stride))
    min_score = max(1, int(args.min_score if args.min_score is not None else config.min_setup_score))
    score_thresholds = tuple(sorted({int(item) for item in args.score_thresholds.split(",") if item.strip()}))
    candidate_min_score = min(min_score, min(score_thresholds))
    rrs = tuple(sorted({int(item) for item in args.rrs.split(",") if item.strip()}))
    end_date = date.fromisoformat(args.end) if args.end else date.today()
    start_date = date.fromisoformat(args.start) if args.start else None
    start, end = date_bounds(start_date, end_date)
    candidate_frames: list[pd.DataFrame] = []
    for raw_path in args.candidate_csv:
        candidate_path = Path(raw_path).expanduser().resolve()
        if not candidate_path.exists():
            parser.error(f"Candidate CSV does not exist: {candidate_path}")
        candidate_frames.append(pd.read_csv(candidate_path))
    saved_candidate_rows = pd.concat(candidate_frames, ignore_index=True) if candidate_frames else pd.DataFrame()

    symbol_lots: dict[str, float] = {
        "XAUUSD": 0.05,
        "XAGUSD": 0.05,
        "BTCUSD": 0.08,
        "US30": 1.0,
        "US100": 1.0,
        **{symbol: 1.0 for symbol in DISABLED_FOREX_SYMBOLS},
    }
    symbol_lots.update({key: float(value) for key, value in config.symbol_lots.items() if key in symbol_lots})

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = REPORTS_DIR / "rr_sweep" / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    client = MT5Client()
    status = client.terminal_status()
    log(f"MT5 status: {status.get('message')}")
    log(
        f"Window: {start.date()} to {end.date()} | stride={stride} | "
        f"candidate_score={candidate_min_score} | thresholds={score_thresholds} | RRs={rrs}"
    )
    log(f"Symbols: {', '.join(symbols)}")
    log(f"Timeframes: {', '.join(timeframes)}")
    if candidate_frames:
        log(f"Replaying candidates from {len(candidate_frames)} saved CSV file(s)")

    trades: list[dict[str, Any]] = []
    availability: list[dict[str, Any]] = []

    for symbol in symbols:
        resolved = client.resolve_symbol(symbol)
        if not resolved:
            availability.append({"symbol": symbol, "broker_symbol": None, "timeframe": None, "candles": 0, "status": "unavailable"})
            log(f"{symbol}: unavailable in MT5")
            continue
        lot = float(symbol_lots.get(symbol, 1.0))
        contract_size = client.contract_size(symbol) or DEFAULT_CONTRACT_SIZES.get(symbol, 1.0)
        info = client.symbol_info(symbol) or {}
        point_size = float(info.get("point") or 0.0)
        for timeframe in timeframes:
            fetch_start = start - timedelta(days=WARMUP_DAYS.get(timeframe, 90))
            candles = client.fetch_candles(symbol, timeframe, fetch_start, end, max_bars=200000)
            candle_count = 0 if candles is None else len(candles)
            if candles is None or candle_count < 120:
                availability.append(
                    {
                        "symbol": symbol,
                        "broker_symbol": resolved,
                        "timeframe": timeframe,
                        "candles": candle_count,
                        "status": "skipped_not_enough_candles",
                    }
                )
                log(f"{symbol} {timeframe}: skipped ({candle_count} candles)")
                continue

            availability.append(
                {
                    "symbol": symbol,
                    "broker_symbol": resolved,
                    "timeframe": timeframe,
                    "candles": candle_count,
                    "status": "ok",
                }
            )
            if candidate_frames:
                candidates = candidates_from_rows(
                    candles,
                    saved_candidate_rows,
                    symbol,
                    timeframe,
                    candidate_min_score,
                )
                log(f"{symbol} {timeframe}: replaying {len(candidates)} saved A+ candidates")
            else:
                log(f"{symbol} {timeframe}: generating candidates from {candle_count} candles")
                profile_lookback = (
                    max(120, int(args.signal_lookback_bars))
                    if int(args.signal_lookback_bars) > 0
                    else PROFILE_LOOKBACK_BARS.get(timeframe, 1000)
                )
                candidates = collect_candidates(
                    candles,
                    symbol,
                    timeframe,
                    candidate_min_score,
                    stride,
                    profile_lookback,
                    start,
                    end,
                )
                log(f"{symbol} {timeframe}: {len(candidates)} A+ candidates")
            for threshold in score_thresholds:
                for rr in rrs:
                    rr_trades = replay_rr(
                        candles,
                        candidates,
                        symbol,
                        timeframe,
                        rr,
                        lot,
                        float(contract_size),
                        stride,
                        int(args.max_holding_bars),
                        threshold,
                        point_size,
                    )
                    trades.extend(asdict(item) for item in rr_trades)

    client.shutdown()

    trades_frame = pd.DataFrame(trades)
    trade_path = out_dir / "trades_all_rr.csv"
    trades_frame.to_csv(trade_path, index=False)

    availability_frame = pd.DataFrame(availability)
    availability_path = out_dir / "availability.csv"
    availability_frame.to_csv(availability_path, index=False)

    rr_summary = summarize_trades(trades, ["min_score", "rr"])
    symbol_summary = summarize_trades(trades, ["min_score", "rr", "symbol"])
    timeframe_summary = summarize_trades(trades, ["min_score", "rr", "symbol", "timeframe"])
    session_summary = summarize_trades(trades, ["min_score", "rr", "symbol", "session"])
    monthly_symbol = summarize_trades(trades, ["min_score", "rr", "symbol", "month"])
    monthly_timeframe = summarize_trades(trades, ["min_score", "rr", "symbol", "timeframe", "month"])

    rr_summary_path = out_dir / "rr_summary.csv"
    symbol_summary_path = out_dir / "symbol_summary_by_rr.csv"
    timeframe_summary_path = out_dir / "symbol_timeframe_summary_by_rr.csv"
    session_summary_path = out_dir / "symbol_session_summary_by_rr.csv"
    monthly_symbol_path = out_dir / "monthly_symbol_breakdown_by_rr.csv"
    monthly_timeframe_path = out_dir / "monthly_symbol_timeframe_breakdown_by_rr.csv"
    rr_summary.to_csv(rr_summary_path, index=False)
    symbol_summary.to_csv(symbol_summary_path, index=False)
    timeframe_summary.to_csv(timeframe_summary_path, index=False)
    session_summary.to_csv(session_summary_path, index=False)
    monthly_symbol.to_csv(monthly_symbol_path, index=False)
    monthly_timeframe.to_csv(monthly_timeframe_path, index=False)

    best_rr = None
    best_score = None
    if not rr_summary.empty:
        best_row = rr_summary.sort_values(["net_r", "profit_factor", "trades"], ascending=[False, False, False]).iloc[0]
        best_rr = int(best_row["rr"])
        best_score = int(best_row["min_score"])
        best_monthly = monthly_symbol[
            (monthly_symbol["rr"] == best_rr) & (monthly_symbol["min_score"] == best_score)
        ]
        pivot = best_monthly.pivot(index="symbol", columns="month", values="net_r").fillna(0.0).reset_index()
        pivot_path = out_dir / f"monthly_symbol_net_r_best_rr_{best_rr}.csv"
        pivot.to_csv(pivot_path, index=False)
    else:
        pivot_path = out_dir / "monthly_symbol_net_r_best_rr_none.csv"
        pd.DataFrame().to_csv(pivot_path, index=False)

    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "window_start": start.isoformat(sep=" ", timespec="seconds"),
        "window_end": end.isoformat(sep=" ", timespec="seconds"),
        "symbols": list(symbols),
        "active_symbols": list(ACTIVE_SYMBOLS),
        "disabled_forex_symbols_counted": list(DISABLED_FOREX_SYMBOLS),
        "other_previous_symbols": list(OTHER_PREVIOUS_SYMBOLS),
        "timeframes_requested": list(timeframes),
        "timeframes_used": sorted(availability_frame[availability_frame["status"] == "ok"]["timeframe"].dropna().unique().tolist())
        if not availability_frame.empty
        else [],
        "stride": stride,
        "candidate_min_score": candidate_min_score,
        "score_thresholds": list(score_thresholds),
        "rrs": list(rrs),
        "max_holding_bars": int(args.max_holding_bars),
        "signal_lookback_bars": int(args.signal_lookback_bars),
        "candidate_csvs": [str(Path(item).expanduser().resolve()) for item in args.candidate_csv],
        "lot_assumptions": symbol_lots,
        "best_rr_by_net_r": best_rr,
        "best_score_by_net_r": best_score,
        "paths": {
            "trades": str(trade_path),
            "availability": str(availability_path),
            "rr_summary": str(rr_summary_path),
            "symbol_summary_by_rr": str(symbol_summary_path),
            "symbol_timeframe_summary_by_rr": str(timeframe_summary_path),
            "symbol_session_summary_by_rr": str(session_summary_path),
            "monthly_symbol_breakdown_by_rr": str(monthly_symbol_path),
            "monthly_symbol_timeframe_breakdown_by_rr": str(monthly_timeframe_path),
            "best_rr_monthly_pivot": str(pivot_path),
        },
        "rr_summary": rr_summary.to_dict(orient="records"),
        "best_rr_symbol_summary": symbol_summary[
            (symbol_summary["rr"] == best_rr) & (symbol_summary["min_score"] == best_score)
        ]
        .sort_values(["net_r", "profit_factor"], ascending=[False, False])
        .to_dict(orient="records")
        if best_rr is not None
        else [],
        "availability": availability,
    }
    report_path = out_dir / "rr_sweep_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    log(f"Done. Report: {report_path}")
    print(
        json.dumps(
            {
                "best_rr": best_rr,
                "best_score": best_score,
                "report": str(report_path),
                "rr_summary": report["rr_summary"],
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
