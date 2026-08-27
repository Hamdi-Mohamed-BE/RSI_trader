from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
ACTIVE = PACKAGE / "Active BAT Backtest 2026-08-12"
ACTIVE_REPORTS = ACTIVE / "MT5 Reports"
START = datetime(2025, 8, 11)
SPLIT = datetime(2026, 4, 11)
END = datetime(2026, 8, 11)

ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
CELL_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
TIME_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$")

SESSIONS: dict[str, tuple[int, int] | None] = {
    "All hours": None,
    "Asia 00-08 UTC": (0, 8),
    "London 07-16 UTC": (7, 16),
    "NY 13-21 UTC": (13, 21),
    "London+NY 07-21 UTC": (7, 21),
    "London/NY overlap 13-16 UTC": (13, 16),
    "Off-hours 21-07 UTC": (21, 7),
}
DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri")


def clean(value: str) -> str:
    return " ".join(unescape(TAG_RE.sub("", value)).replace("\xa0", " ").split())


def number(value: str) -> float:
    value = value.replace(" ", "").replace(",", "")
    return float(value) if value and value != "-" else 0.0


def read_html(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    return raw.decode("utf-8", errors="replace")


def report_paths() -> dict[str, Path]:
    data = json.loads((ACTIVE / "portfolio-results.json").read_text(encoding="utf-8-sig"))
    paths = {str(row["label"]): ACTIVE_REPORTS / str(row["file"]) for row in data["bots"]}
    paths |= {
        "US100 ORB 0.5R": PACKAGE / "US100 Selective ORB Research 2026-08-21" / "Backtest Reports" / "rr05-bat-one-year" / "Custom" / "one-year-2025-2026.htm",
        "US100 ORB 2R": PACKAGE / "US100 Selective ORB Research 2026-08-21" / "Backtest Reports" / "v3-time-direction" / "One Year" / "one-year-2025-2026.htm",
        "Nasdaq 5M Open EMA ATR": PACKAGE / "Nasdaq 5M Open EMA ATR Research 2026-08-20" / "Backtest Reports" / "Literal Hold" / "literal-hold-website-one-year.htm",
    }
    aliases = {
        "AAA Final Asia Breakout": "Asia Breakout",
        "AAA Final DmC": "DmC",
        "AAA Final EMA3": "EMA3",
        "AAA Final XAU Weakness": "XAU Weakness",
        "AAA Final US100 Weakness": "US100 Weakness",
        "AAA Final News Pulse — long only": "News Pulse",
    }
    return {aliases.get(label, label): path for label, path in paths.items()}


def parse_trades(label: str, path: Path) -> tuple[list[dict], dict]:
    html = read_html(path)
    text = " ".join(unescape(TAG_RE.sub(" ", html)).replace("\xa0", " ").split())
    summary_match = lambda pattern, default="0": (re.search(pattern, text).group(1).strip() if re.search(pattern, text) else default)
    report_summary = {
        "reported_trades": int(summary_match(r"Total Trades:\s*(\d+)")),
        "reported_net": number(summary_match(r"Total Net Profit:\s*([-\d .]+?)\s+Balance Drawdown Absolute:")),
        "reported_pf": float(summary_match(r"Profit Factor:\s*([\d.]+)")),
    }
    marker = html.lower().find("<b>deals</b>")
    deals = []
    for row_html in ROW_RE.findall(html[marker:] if marker >= 0 else ""):
        cells = [clean(cell) for cell in CELL_RE.findall(row_html)]
        if len(cells) != 13 or not TIME_RE.match(cells[0]) or cells[3].lower() == "balance":
            continue
        deals.append(
            {
                "time": datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S"),
                "type": cells[3].lower(),
                "direction": cells[4].lower(),
                "volume": number(cells[5]),
                "commission": number(cells[8]),
                "swap": number(cells[9]),
                "profit": number(cells[10]),
            }
        )

    open_trades: list[dict] = []
    trades: list[dict] = []
    for deal in deals:
        cash_flow = deal["commission"] + deal["swap"] + deal["profit"]
        if deal["direction"] == "in":
            open_trades.append(
                {
                    "ea": label,
                    "entry_time": deal["time"],
                    "exit_time": deal["time"],
                    "side": "Buy" if deal["type"] == "buy" else "Sell",
                    "remaining": deal["volume"],
                    "net": cash_flow,
                }
            )
            continue
        if deal["direction"] not in {"out", "out by"} or not open_trades:
            continue
        closing = deal["volume"]
        while closing > 1e-9 and open_trades:
            trade = open_trades[0]
            matched = min(closing, trade["remaining"])
            fraction = matched / deal["volume"] if deal["volume"] > 0 else 1.0
            trade["net"] += cash_flow * fraction
            trade["remaining"] -= matched
            trade["exit_time"] = deal["time"]
            closing -= matched
            if trade["remaining"] <= 1e-9:
                trade.pop("remaining", None)
                trades.append(trade)
                open_trades.pop(0)

    trades.sort(key=lambda trade: trade["exit_time"])
    report_summary["parsed_trades"] = len(trades)
    report_summary["parsed_net"] = round(sum(trade["net"] for trade in trades), 2)
    return trades, report_summary


def session_passes(when: datetime, bounds: tuple[int, int] | None) -> bool:
    if bounds is None:
        return True
    start, end = bounds
    value = when.hour + when.minute / 60.0
    return start <= value < end if start < end else value >= start or value < end


def day_passes(when: datetime, mask: int | None) -> bool:
    if mask is None:
        return True
    weekday = when.weekday()
    return weekday < 5 and bool(mask & (1 << weekday))


def mask_name(mask: int | None) -> str:
    if mask is None:
        return "All days"
    return "+".join(name for index, name in enumerate(DAY_NAMES) if mask & (1 << index))


def performance(trades: list[dict], predicate: Callable[[dict], bool] = lambda _trade: True) -> dict:
    selected = sorted((trade for trade in trades if predicate(trade)), key=lambda trade: trade["exit_time"])
    balance = 10_000.0
    peak = balance
    maximum_dd = 0.0
    wins = 0
    gross_profit = 0.0
    gross_loss = 0.0
    series = [{"time": START.isoformat(), "balance": balance}]
    for trade in selected:
        value = float(trade["net"])
        balance += value
        peak = max(peak, balance)
        maximum_dd = max(maximum_dd, peak - balance)
        if value > 0:
            wins += 1
            gross_profit += value
        elif value < 0:
            gross_loss += value
        series.append({"time": trade["exit_time"].isoformat(), "balance": round(balance, 2)})
    count = len(selected)
    return {
        "initial": 10_000.0,
        "final": round(balance, 2),
        "net": round(balance - 10_000.0, 2),
        "return_pct": round((balance - 10_000.0) / 100.0, 4),
        "profit_factor": round(gross_profit / abs(gross_loss), 4) if gross_loss else (999.0 if gross_profit else 0.0),
        "win_rate": round(wins / count * 100.0, 4) if count else 0.0,
        "max_dd_pct": round(maximum_dd / peak * 100.0, 4) if peak else 0.0,
        "trades": count,
        "wins": wins,
        "losses": count - wins,
        "series": series,
    }


def filter_predicate(session: tuple[int, int] | None, day_mask: int | None, start: datetime = START, end: datetime = END) -> Callable[[dict], bool]:
    return lambda trade: start <= trade["entry_time"] < end and session_passes(trade["entry_time"], session) and day_passes(trade["entry_time"], day_mask)


def candidate_rows(trades: list[dict], start: datetime, end: datetime) -> list[dict]:
    baseline_count = performance(trades, filter_predicate(None, None, start, end))["trades"]
    minimum = max(5, round(baseline_count * 0.15))
    rows = []
    for session_name, session in SESSIONS.items():
        for mask in (None, *range(1, 32)):
            stats = performance(trades, filter_predicate(session, mask, start, end))
            if stats["trades"] < minimum:
                continue
            score = stats["return_pct"] - 0.35 * stats["max_dd_pct"] + 2.0 * (stats["profit_factor"] - 1.0)
            rows.append({"session": session_name, "day_mask": mask, "days": mask_name(mask), "score": score, **stats})
    return sorted(rows, key=lambda row: row["score"], reverse=True)


def without_series(row: dict) -> dict:
    return {key: value for key, value in row.items() if key != "series"}


def main() -> None:
    paths = report_paths()
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing reports:\n" + "\n".join(missing))

    all_trades: list[dict] = []
    parsed = {}
    per_ea = []
    selection_by_ea: dict[str, tuple[tuple[int, int] | None, int]] = {}
    for label, path in paths.items():
        trades, audit = parse_trades(label, path)
        parsed[label] = audit
        all_trades.extend(trades)
        baseline = performance(trades, filter_predicate(None, None))
        training_candidates = candidate_rows(trades, START, SPLIT)
        best = training_candidates[0] if training_candidates else {"session": "All hours", "day_mask": 31, "days": mask_name(31)}
        session = SESSIONS[best["session"]]
        mask = best["day_mask"]
        selection_by_ea[label] = (session, mask)
        filtered_full = performance(trades, filter_predicate(session, mask))
        filtered_validation = performance(trades, filter_predicate(session, mask, SPLIT, END))
        validation_baseline = performance(trades, filter_predicate(None, None, SPLIT, END))

        full_candidates = candidate_rows(trades, START, END)
        baseline_candidate = {
            "session": "All hours",
            "day_mask": None,
            "days": "All days",
            "score": 0.0,
            **baseline,
        }
        session_only = max(
            (row for row in full_candidates if row["day_mask"] is None),
            key=lambda row: row["score"],
            default=baseline_candidate,
        )
        day_only = max(
            (row for row in full_candidates if row["session"] == "All hours"),
            key=lambda row: row["score"],
            default=baseline_candidate,
        )
        per_ea.append(
            {
                "ea": label,
                "baseline": without_series(baseline),
                "best_full_year_session_only": without_series(session_only),
                "best_full_year_days_only": without_series(day_only),
                "training_selected_filter": {"session": best["session"], "days": mask_name(mask), "day_mask": mask},
                "filtered_full_year": without_series(filtered_full),
                "validation_baseline": without_series(validation_baseline),
                "filtered_validation": without_series(filtered_validation),
                "report_audit": audit,
            }
        )

    all_trades.sort(key=lambda trade: trade["exit_time"])
    portfolio_baseline = performance(all_trades, filter_predicate(None, None))
    global_training = candidate_rows(all_trades, START, SPLIT)
    global_best = global_training[0]
    global_session = SESSIONS[global_best["session"]]
    global_mask = global_best["day_mask"]
    global_full = performance(all_trades, filter_predicate(global_session, global_mask))
    global_validation = performance(all_trades, filter_predicate(global_session, global_mask, SPLIT, END))
    baseline_validation = performance(all_trades, filter_predicate(None, None, SPLIT, END))

    per_ea_predicate = lambda trade: (
        session_passes(trade["entry_time"], selection_by_ea[trade["ea"]][0])
        and day_passes(trade["entry_time"], selection_by_ea[trade["ea"]][1])
    )
    per_ea_full = performance(all_trades, lambda trade: START <= trade["entry_time"] < END and per_ea_predicate(trade))
    per_ea_validation = performance(all_trades, lambda trade: SPLIT <= trade["entry_time"] < END and per_ea_predicate(trade))

    portfolio = {
        "baseline_full_year": without_series(portfolio_baseline),
        "baseline_validation": without_series(baseline_validation),
        "training_selected_global_filter": {
            "session": global_best["session"],
            "days": mask_name(global_mask),
            "day_mask": global_mask,
        },
        "global_filter_full_year": without_series(global_full),
        "global_filter_validation": without_series(global_validation),
        "per_ea_filters_full_year": without_series(per_ea_full),
        "per_ea_filters_validation": without_series(per_ea_validation),
    }

    payload = {
        "method": {
            "period": "2025-08-11 to 2026-08-10",
            "selection_period": "2025-08-11 to 2026-04-10",
            "locked_check_period": "2026-04-11 to 2026-08-10",
            "time_basis": "Exness MT5 tester timestamps treated as UTC",
            "sessions": {name: bounds for name, bounds in SESSIONS.items()},
            "warning": "Historical trade overlay. It preserves each native MT5 trade's realized cash result but does not rerun the EA or resize later positions after filtered trades are removed.",
        },
        "portfolio": portfolio,
        "per_ea": per_ea,
        "report_reconciliation": parsed,
        "series": {
            "portfolio_baseline": portfolio_baseline["series"],
            "global_filter": global_full["series"],
            "per_ea_filters": per_ea_full["series"],
        },
    }
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "session-day-filter-results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    rows = []
    for item in per_ea:
        rows.append(
            {
                "ea": item["ea"],
                "baseline_return": item["baseline"]["return_pct"],
                "baseline_pf": item["baseline"]["profit_factor"],
                "baseline_dd": item["baseline"]["max_dd_pct"],
                "baseline_trades": item["baseline"]["trades"],
                "best_session_full_year": item["best_full_year_session_only"]["session"],
                "best_days_full_year": item["best_full_year_days_only"]["days"],
                "selected_session": item["training_selected_filter"]["session"],
                "selected_days": item["training_selected_filter"]["days"],
                "filtered_return": item["filtered_full_year"]["return_pct"],
                "filtered_pf": item["filtered_full_year"]["profit_factor"],
                "filtered_dd": item["filtered_full_year"]["max_dd_pct"],
                "filtered_trades": item["filtered_full_year"]["trades"],
                "validation_baseline_return": item["validation_baseline"]["return_pct"],
                "validation_filtered_return": item["filtered_validation"]["return_pct"],
                "validation_filtered_pf": item["filtered_validation"]["profit_factor"],
                "validation_filtered_dd": item["filtered_validation"]["max_dd_pct"],
                "validation_filtered_trades": item["filtered_validation"]["trades"],
            }
        )
    with (ROOT / "per-ea-filter-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print("PORTFOLIO")
    for label, result in (
        ("Baseline full year", portfolio_baseline),
        ("Global filter full year", global_full),
        ("Per-EA filters full year", per_ea_full),
        ("Baseline locked check", baseline_validation),
        ("Global filter locked check", global_validation),
        ("Per-EA filters locked check", per_ea_validation),
    ):
        print(f"{label:29} return={result['return_pct']:8.2f}% PF={result['profit_factor']:5.2f} DD={result['max_dd_pct']:6.2f}% trades={result['trades']:4d}")
    print("Global selection:", global_best["session"], mask_name(global_mask))
    print("\nPER EA")
    for row in rows:
        print(
            f"{row['ea'][:28]:28} base={row['baseline_return']:7.2f}% -> filtered={row['filtered_return']:7.2f}% "
            f"locked={row['validation_filtered_return']:7.2f}% PF={row['validation_filtered_pf']:5.2f} "
            f"{row['selected_session']} {row['selected_days']}"
        )


if __name__ == "__main__":
    main()
