from __future__ import annotations

import argparse
from datetime import datetime
import heapq
from itertools import combinations
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd


SESSIONS = ("Asia", "London", "New York")


def parse_clock(value: str) -> int:
    hour, minute = (int(part) for part in value.split(":", 1))
    return hour * 60 + minute


def apply_live_entry_guards(
    frame: pd.DataFrame,
    max_spread_r: float,
    strict_start: str,
    strict_end: str,
    strict_min_score: int,
    strict_require_internal: bool,
    session_timezone: str,
) -> tuple[pd.DataFrame, dict[str, int]]:
    guarded = frame.copy()
    spread = pd.to_numeric(guarded["spread_r"], errors="coerce").fillna(0.0)
    spread_ok = spread <= max_spread_r if max_spread_r > 0 else pd.Series(True, index=guarded.index)

    timestamps = pd.to_datetime(guarded["opened_at"], errors="coerce", utc=True).dt.tz_convert(ZoneInfo(session_timezone))
    minutes = timestamps.dt.hour * 60 + timestamps.dt.minute
    start = parse_clock(strict_start)
    end = parse_clock(strict_end)
    if start == end:
        in_strict = pd.Series(False, index=guarded.index)
    elif start < end:
        in_strict = (minutes >= start) & (minutes < end)
    else:
        in_strict = (minutes >= start) | (minutes < end)
    strict_score_ok = pd.to_numeric(guarded["setup_score"], errors="coerce").fillna(0) >= strict_min_score
    if strict_require_internal:
        strict_model_ok = guarded["entry_model"].astype(str).str.contains("Internal Structure", case=False, regex=False)
    else:
        strict_model_ok = pd.Series(True, index=guarded.index)
    strict_ok = ~in_strict | (strict_score_ok & strict_model_ok)
    kept = guarded[spread_ok & strict_ok].copy()
    return kept, {
        "input_rows": int(len(guarded)),
        "blocked_spread": int((~spread_ok).sum()),
        "blocked_strict_window": int((spread_ok & ~strict_ok).sum()),
        "kept_rows": int(len(kept)),
    }


def settle(
    pending: list[tuple[datetime, int, dict[str, Any]]],
    balance: float,
    peak: float,
    max_drawdown: float,
    until: datetime | None = None,
) -> tuple[float, float, float, list[dict[str, Any]]]:
    closed: list[dict[str, Any]] = []
    while pending and (until is None or pending[0][0] <= until):
        _closed_at, _sequence, item = heapq.heappop(pending)
        balance += float(item["pnl"])
        peak = max(peak, balance)
        max_drawdown = max(max_drawdown, (peak - balance) / peak if peak > 0 else 0.0)
        item["balance_after"] = round(balance, 2)
        closed.append(item)
    return balance, peak, max_drawdown, closed


def simulate_account(
    frame: pd.DataFrame,
    starting_balance: float,
    risk_pct: float,
    max_trades_per_day: int,
) -> tuple[dict[str, Any], pd.DataFrame]:
    balance = float(starting_balance)
    peak = balance
    max_drawdown = 0.0
    pending: list[tuple[datetime, int, dict[str, Any]]] = []
    daily_trades: dict[str, int] = {}
    symbol_open_until: dict[str, datetime] = {}
    applied: list[dict[str, Any]] = []
    skipped_daily = 0
    skipped_overlap = 0
    sequence = 0

    rows = frame.sort_values(["opened_at", "setup_score", "symbol"], ascending=[True, False, True])
    for raw in rows.to_dict(orient="records"):
        opened_at = datetime.fromisoformat(str(raw["opened_at"]))
        closed_at = datetime.fromisoformat(str(raw["closed_at"]))
        balance, peak, max_drawdown, closed = settle(pending, balance, peak, max_drawdown, opened_at)
        applied.extend(closed)
        symbol = str(raw["symbol"])
        day_key = opened_at.date().isoformat()
        if symbol_open_until.get(symbol, datetime.min) > opened_at:
            skipped_overlap += 1
            continue
        if max_trades_per_day > 0 and daily_trades.get(day_key, 0) >= max_trades_per_day:
            skipped_daily += 1
            continue

        risk_amount = balance * risk_pct / 100.0
        item = dict(raw)
        item["balance_at_entry"] = round(balance, 2)
        item["risk_amount"] = round(risk_amount, 2)
        item["pnl"] = round(risk_amount * float(raw["r_multiple"]), 2)
        daily_trades[day_key] = daily_trades.get(day_key, 0) + 1
        symbol_open_until[symbol] = closed_at
        sequence += 1
        heapq.heappush(pending, (closed_at, sequence, item))

    balance, peak, max_drawdown, closed = settle(pending, balance, peak, max_drawdown)
    applied.extend(closed)
    wins = sum(float(item["r_multiple"]) > 0 for item in applied)
    losses = sum(float(item["r_multiple"]) < 0 for item in applied)
    summary = {
        "starting_balance": round(starting_balance, 2),
        "ending_balance": round(balance, 2),
        "net_profit": round(balance - starting_balance, 2),
        "return_pct": round((balance / starting_balance - 1) * 100, 2) if starting_balance else 0.0,
        "trades": len(applied),
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / len(applied) * 100, 2) if applied else 0.0,
        "net_r": round(sum(float(item["r_multiple"]) for item in applied), 2),
        "max_drawdown_pct": round(max_drawdown * 100, 2),
        "skipped_daily_cap": skipped_daily,
        "skipped_same_symbol_overlap": skipped_overlap,
    }
    return summary, pd.DataFrame(applied)


def best_symbol_configs(frame: pd.DataFrame, minimum_trades: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for keys, group in frame.groupby(["symbol", "timeframe", "rr"], dropna=False):
        r_values = group["r_multiple"].astype(float)
        if len(group) < minimum_trades:
            continue
        rows.append(
            {
                "symbol": keys[0],
                "timeframe": keys[1],
                "rr": int(keys[2]),
                "trades": len(group),
                "net_r": float(r_values.sum()),
                "avg_r": float(r_values.mean()),
                "timeouts": int((group["result"] == "timeout").sum()),
            }
        )
    if not rows:
        return pd.DataFrame()
    summary = pd.DataFrame(rows).sort_values(
        ["symbol", "net_r", "avg_r", "trades"],
        ascending=[True, False, False, False],
    )
    return summary.groupby("symbol", as_index=False).head(1).reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize a managed LTA portfolio from an RR sweep trade file.")
    parser.add_argument("trade_csv")
    parser.add_argument("--balance", type=float, default=300.0)
    parser.add_argument("--risk-pct", type=float, default=5.0)
    parser.add_argument("--min-score", type=int, default=90)
    parser.add_argument("--minimum-trades", type=int, default=3)
    parser.add_argument("--max-symbols", type=int, default=5)
    parser.add_argument("--max-spread-r", type=float, default=0.10)
    parser.add_argument("--strict-start", default="10:00")
    parser.add_argument("--strict-end", default="13:00")
    parser.add_argument("--strict-min-score", type=int, default=96)
    parser.add_argument("--strict-require-internal", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--session-timezone", default="America/New_York")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    source = Path(args.trade_csv).expanduser().resolve()
    frame = pd.read_csv(source)
    frame = frame[pd.to_numeric(frame["min_score"], errors="coerce") == int(args.min_score)].copy()
    frame["rr"] = pd.to_numeric(frame["rr"], errors="coerce").astype(int)
    frame["r_multiple"] = pd.to_numeric(frame["r_multiple"], errors="coerce")
    frame = frame.dropna(subset=["r_multiple", "opened_at", "closed_at"])
    frame, guard_summary = apply_live_entry_guards(
        frame,
        max(0.0, float(args.max_spread_r)),
        args.strict_start,
        args.strict_end,
        int(args.strict_min_score),
        bool(args.strict_require_internal),
        args.session_timezone,
    )

    session_sets = [combo for size in range(1, len(SESSIONS) + 1) for combo in combinations(SESSIONS, size)]
    optimization_rows: list[dict[str, Any]] = []
    selected_frames: dict[str, pd.DataFrame] = {}
    for sessions in session_sets:
        session_frame = frame[frame["session"].isin(sessions)].copy()
        configs = best_symbol_configs(session_frame, max(1, int(args.minimum_trades)))
        if configs.empty:
            continue
        configs = configs[configs["net_r"] > 0].copy()
        symbols = sorted(configs["symbol"].astype(str).unique())
        for symbol_count in range(1, min(max(1, args.max_symbols), len(symbols)) + 1):
            for subset in combinations(symbols, symbol_count):
                chosen = configs[configs["symbol"].isin(subset)]
                parts: list[pd.DataFrame] = []
                config_labels: list[str] = []
                for config in chosen.to_dict(orient="records"):
                    rows = session_frame[
                        (session_frame["symbol"] == config["symbol"])
                        & (session_frame["timeframe"] == config["timeframe"])
                        & (session_frame["rr"] == config["rr"])
                    ]
                    parts.append(rows)
                    config_labels.append(f'{config["symbol"]}:{config["timeframe"]}:R{int(config["rr"])}')
                portfolio = pd.concat(parts, ignore_index=True)
                for daily_cap in range(1, 6):
                    summary, applied = simulate_account(portfolio, args.balance, args.risk_pct, daily_cap)
                    key = f'{"+".join(config_labels)}|{"+".join(sessions)}|D{daily_cap}'
                    result = {
                        **summary,
                        "symbols": ",".join(subset),
                        "symbol_count": symbol_count,
                        "sessions": ",".join(sessions),
                        "max_trades_per_day": daily_cap,
                        "configs": ",".join(config_labels),
                        "quality_score": round(summary["return_pct"] / max(1.0, summary["max_drawdown_pct"]), 4),
                        "key": key,
                    }
                    optimization_rows.append(result)
                    selected_frames[key] = applied

    results = pd.DataFrame(optimization_rows).sort_values(
        ["ending_balance", "max_drawdown_pct", "trades"],
        ascending=[False, True, False],
    )
    balanced = results[results["trades"] >= 5].sort_values(
        ["quality_score", "ending_balance"], ascending=[False, False]
    )
    best_growth = results.iloc[0].to_dict() if not results.empty else None
    best_balanced = balanced.iloc[0].to_dict() if not balanced.empty else None

    output_dir = Path(args.output_dir).resolve() if args.output_dir else source.parent / "portfolio_optimization"
    output_dir.mkdir(parents=True, exist_ok=True)
    results.head(500).to_csv(output_dir / "portfolio_rankings.csv", index=False)
    if best_growth:
        selected_frames[str(best_growth["key"])].to_csv(output_dir / "best_growth_trades.csv", index=False)
    if best_balanced:
        selected_frames[str(best_balanced["key"])].to_csv(output_dir / "best_balanced_trades.csv", index=False)
    config_table = best_symbol_configs(frame, max(1, int(args.minimum_trades)))
    config_table.to_csv(output_dir / "best_config_per_symbol.csv", index=False)
    report = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "starting_balance": args.balance,
        "risk_pct": args.risk_pct,
        "min_score": args.min_score,
        "minimum_trades_per_config": args.minimum_trades,
        "entry_guards": {
            **guard_summary,
            "max_spread_r": args.max_spread_r,
            "strict_window": f"{args.strict_start}-{args.strict_end}",
            "strict_min_score": args.strict_min_score,
            "strict_require_internal": args.strict_require_internal,
            "session_timezone": args.session_timezone,
        },
        "best_growth": best_growth,
        "best_balanced": best_balanced,
        "best_config_per_symbol": config_table.to_dict(orient="records"),
        "notes": [
            "Balance changes are settled at trade close, never credited at entry.",
            "The daily cap is global across the LTA bot.",
            "This is an in-sample one-month optimization and should be validated out of sample before live use.",
        ],
    }
    report_path = output_dir / "portfolio_optimization_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"report": str(report_path), "best_growth": best_growth, "best_balanced": best_balanced}, indent=2))


if __name__ == "__main__":
    main()
