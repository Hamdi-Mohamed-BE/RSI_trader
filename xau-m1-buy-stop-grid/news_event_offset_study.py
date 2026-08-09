from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from statistics import mean, median
from typing import Iterable


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "news-event-days"
CALENDAR_PATH = ROOT / "news_event_offset_calendar.csv"
OUTPUT_DIR = ROOT / "reports" / "news-offset-study"
EVENT_ORDER = ("NFP", "CPI", "PPI", "GDP", "FOMC")


@dataclass(frozen=True)
class Event:
    event: str
    release_utc: datetime
    title: str
    source: str


@dataclass(frozen=True)
class EventMove:
    event: str
    release_utc: str
    direction: str
    anchor_bid: float
    anchor_ask: float
    anchor_mid: float
    end_mid: float
    net_move: float
    fakeout_usd: float
    correct_move_usd: float
    correct_extreme_utc: str
    bars: int
    data_source: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conservative XAU news fakeout/offset study")
    parser.add_argument("--years", type=float, default=5.0)
    parser.add_argument("--horizon-minutes", type=int, default=30)
    parser.add_argument("--offset-step", type=float, default=0.5)
    parser.add_argument("--end", type=str, default="")
    return parser.parse_args()


def load_calendar() -> list[Event]:
    with CALENDAR_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        Event(
            event=row["event"],
            release_utc=datetime.fromisoformat(row["release_utc"]).astimezone(timezone.utc),
            title=row["title"],
            source=row["source"],
        )
        for row in rows
    ]


@lru_cache(maxsize=None)
def load_bars(day: str, side: str) -> dict[int, dict[str, float]]:
    path = DATA_DIR / f"xauusd-m1-{side}-{day}.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        int(row["timestamp"]): {
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
        }
        for row in raw
    }


def aggregate_ticks_to_m1(ticks) -> tuple[dict[int, dict[str, float]], dict[int, dict[str, float]]]:
    sides: dict[str, dict[int, dict[str, float]]] = {"bid": {}, "ask": {}}
    for tick in ticks:
        stamp = int(tick["time_msc"] // 60_000 * 60_000)
        for side in ("bid", "ask"):
            value = float(tick[side])
            if value <= 0:
                continue
            row = sides[side].get(stamp)
            if row is None:
                sides[side][stamp] = {"open": value, "high": value, "low": value, "close": value}
            else:
                row["high"] = max(row["high"], value)
                row["low"] = min(row["low"], value)
                row["close"] = value
    return sides["bid"], sides["ask"]


def mt5_tick_window(event: Event, horizon_minutes: int):
    try:
        import MetaTrader5 as mt5
    except ImportError:
        return {}, {}
    if not mt5.initialize():
        return {}, {}
    try:
        symbols = mt5.symbols_get() or []
        candidates = []
        for info in symbols:
            clean = "".join(ch for ch in info.name.upper() if ch.isalnum())
            if "XAUUSD" in clean or clean.startswith("GOLD"):
                score = 0 if clean.startswith("XAUUSD") else 10
                score += len(info.name)
                candidates.append((score, info.name))
        if not candidates:
            return {}, {}
        symbol = min(candidates)[1]
        mt5.symbol_select(symbol, True)
        start = event.release_utc - timedelta(minutes=5)
        end = event.release_utc + timedelta(minutes=horizon_minutes + 1)
        ticks = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
        if ticks is None or len(ticks) == 0:
            return {}, {}
        return aggregate_ticks_to_m1(ticks)
    finally:
        mt5.shutdown()


def shifted_bars(bars: dict[int, dict[str, float]], amount: float) -> dict[int, dict[str, float]]:
    return {
        stamp: {field: value + amount for field, value in row.items()}
        for stamp, row in bars.items()
    }


def annual_spreads(calendar: list[Event]) -> dict[int, float]:
    samples: dict[int, list[float]] = {}
    for day in sorted({event.release_utc.date().isoformat() for event in calendar}):
        bid = load_bars(day, "bid")
        ask = load_bars(day, "ask")
        common = sorted(set(bid).intersection(ask))
        if not common:
            continue
        year = int(day[:4])
        # A sparse intraday sample is sufficient and avoids overweighting any day.
        for stamp in common[::60]:
            spread = ask[stamp]["close"] - bid[stamp]["close"]
            if 0.0 < spread < 10.0:
                samples.setdefault(year, []).append(spread)
    all_values = [value for values in samples.values() for value in values]
    global_median = median(all_values) if all_values else 0.10
    return {year: median(values) if values else global_median for year, values in samples.items()} | {
        year: global_median for year in range(2020, 2028) if year not in samples
    }


def latest_at_or_before(bars: dict[int, dict[str, float]], target_ms: int, tolerance_minutes: int = 5):
    candidates = [stamp for stamp in bars if target_ms - tolerance_minutes * 60_000 <= stamp <= target_ms]
    if not candidates:
        return None
    stamp = max(candidates)
    return stamp, bars[stamp]


def analyze_event(event: Event, horizon_minutes: int, spread_by_year: dict[int, float]) -> EventMove | None:
    day = event.release_utc.date().isoformat()
    bid = load_bars(day, "bid")
    ask = load_bars(day, "ask")
    data_source = "archived bid/ask M1"
    if not bid and not ask:
        bid, ask = mt5_tick_window(event, horizon_minutes)
        data_source = "MT5 bid/ask ticks"
    spread = spread_by_year[event.release_utc.year]
    if not bid and ask:
        bid = shifted_bars(ask, -spread)
    elif not ask and bid:
        ask = shifted_bars(bid, spread)
    release_ms = int(event.release_utc.timestamp() * 1000)
    pre_bid = latest_at_or_before(bid, release_ms - 60_000)
    pre_ask = latest_at_or_before(ask, release_ms - 60_000)
    if pre_bid is None or pre_ask is None:
        return None

    anchor_bid = pre_bid[1]["close"]
    anchor_ask = pre_ask[1]["close"]
    anchor_mid = (anchor_bid + anchor_ask) / 2.0
    end_ms = release_ms + horizon_minutes * 60_000
    stamps = sorted(stamp for stamp in set(bid).intersection(ask) if release_ms <= stamp < end_ms)
    if len(stamps) < max(3, horizon_minutes // 2):
        return None

    end_mid = (bid[stamps[-1]]["close"] + ask[stamps[-1]]["close"]) / 2.0
    net_move = end_mid - anchor_mid
    if abs(net_move) < 1e-9:
        up_peak = max(ask[stamp]["high"] - anchor_ask for stamp in stamps)
        down_peak = max(anchor_bid - bid[stamp]["low"] for stamp in stamps)
        direction = "UP" if up_peak >= down_peak else "DOWN"
    else:
        direction = "UP" if net_move > 0 else "DOWN"

    if direction == "UP":
        correct_by_stamp = {stamp: max(0.0, ask[stamp]["high"] - anchor_ask) for stamp in stamps}
        correct_stamp = max(stamps, key=lambda stamp: correct_by_stamp[stamp])
        # Include the correct-extreme M1 bar. M1 OHLC cannot prove high/low ordering,
        # so treating its wrong-way low as first is deliberately conservative.
        fakeout = max(max(0.0, anchor_bid - bid[stamp]["low"]) for stamp in stamps if stamp <= correct_stamp)
    else:
        correct_by_stamp = {stamp: max(0.0, anchor_bid - bid[stamp]["low"]) for stamp in stamps}
        correct_stamp = max(stamps, key=lambda stamp: correct_by_stamp[stamp])
        fakeout = max(max(0.0, ask[stamp]["high"] - anchor_ask) for stamp in stamps if stamp <= correct_stamp)

    return EventMove(
        event=event.event,
        release_utc=event.release_utc.isoformat(),
        direction=direction,
        anchor_bid=round(anchor_bid, 5),
        anchor_ask=round(anchor_ask, 5),
        anchor_mid=round(anchor_mid, 5),
        end_mid=round(end_mid, 5),
        net_move=round(net_move, 5),
        fakeout_usd=round(fakeout, 5),
        correct_move_usd=round(correct_by_stamp[correct_stamp], 5),
        correct_extreme_utc=datetime.fromtimestamp(correct_stamp / 1000, tz=timezone.utc).isoformat(),
        bars=len(stamps),
        data_source=data_source,
    )


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def strictly_above(value: float, step: float) -> float:
    return round((math.floor(value / step + 1e-12) + 1) * step, 8)


def offset_metrics(rows: list[EventMove], offset: float) -> dict[str, float]:
    total = len(rows)
    correct = sum(row.correct_move_usd >= offset for row in rows)
    false_first = sum(row.fakeout_usd >= offset for row in rows)
    clean = sum(row.correct_move_usd >= offset and row.fakeout_usd < offset for row in rows)
    both = sum(row.correct_move_usd >= offset and row.fakeout_usd >= offset for row in rows)
    return {
        "capture_rate_pct": round(100 * correct / total, 2) if total else 0.0,
        "false_first_rate_pct": round(100 * false_first / total, 2) if total else 0.0,
        "clean_capture_rate_pct": round(100 * clean / total, 2) if total else 0.0,
        "both_sides_rate_pct": round(100 * both / total, 2) if total else 0.0,
    }


def summarize(group: str, rows: list[EventMove], step: float) -> dict[str, object]:
    fake = [row.fakeout_usd for row in rows]
    correct = [row.correct_move_usd for row in rows]
    robust_offset = strictly_above(percentile(fake, 0.95), step)
    sample_safe_offset = strictly_above(max(fake), step)
    robust = offset_metrics(rows, robust_offset)
    sample_safe = offset_metrics(rows, sample_safe_offset)
    return {
        "event": group,
        "events": len(rows),
        "fakeout_min_usd": round(min(fake), 2),
        "fakeout_avg_usd": round(mean(fake), 2),
        "fakeout_p95_usd": round(percentile(fake, 0.95), 2),
        "fakeout_max_usd": round(max(fake), 2),
        "correct_min_usd": round(min(correct), 2),
        "correct_avg_usd": round(mean(correct), 2),
        "correct_p50_usd": round(percentile(correct, 0.50), 2),
        "correct_max_usd": round(max(correct), 2),
        "best_robust_offset_usd": robust_offset,
        "robust_capture_pct": robust["capture_rate_pct"],
        "robust_false_first_pct": robust["false_first_rate_pct"],
        "robust_clean_capture_pct": robust["clean_capture_rate_pct"],
        "sample_safe_offset_usd": sample_safe_offset,
        "sample_safe_capture_pct": sample_safe["capture_rate_pct"],
        "sample_safe_false_first_pct": sample_safe["false_first_rate_pct"],
    }


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    records = list(rows)
    if not records:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def markdown_report(start: datetime, end: datetime, horizon_minutes: int, summaries: list[dict[str, object]], skipped: list[str]) -> str:
    lines = [
        "# XAU news-event stop-offset study", "",
        f"Study range: **{start.date()} through {end.date()}**. Main-move horizon: **{horizon_minutes} minutes**.", "",
        "## Method", "",
        "- Anchor: last available bid/ask close immediately before the official release.",
        "- Direction: sign of the bid/ask midpoint at the end of the horizon versus the anchor midpoint.",
        "- Correct move: maximum executable stop-trigger excursion in that final direction.",
        "- Fakeout: maximum opposite executable stop-trigger excursion before or during the M1 bar containing the correct extreme.",
        "- Same-bar ordering is conservative: the wrong side is assumed to occur first.",
        "- Best robust offset: first $0.50 increment strictly above the historical 95th-percentile fakeout.",
        "- Sample-safe offset: first $0.50 increment strictly above the largest fakeout in this sample; not a future guarantee.", "",
        "## Results", "",
        "| Event | N | Fake min | Fake avg | Fake p95 | Fake max | Correct min | Correct avg | Correct max | Robust offset | Capture | False-first | Sample-safe | Safe capture |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summaries:
        lines.append(
            f"| {row['event']} | {row['events']} | ${row['fakeout_min_usd']:.2f} | ${row['fakeout_avg_usd']:.2f} | "
            f"${row['fakeout_p95_usd']:.2f} | ${row['fakeout_max_usd']:.2f} | ${row['correct_min_usd']:.2f} | "
            f"${row['correct_avg_usd']:.2f} | ${row['correct_max_usd']:.2f} | ${row['best_robust_offset_usd']:.2f} | "
            f"{row['robust_capture_pct']:.2f}% | {row['robust_false_first_pct']:.2f}% | "
            f"${row['sample_safe_offset_usd']:.2f} | {row['sample_safe_capture_pct']:.2f}% |"
        )
    if skipped:
        lines.extend(["", f"Skipped events: {len(skipped)}", "", *[f"- {item}" for item in skipped]])
    lines.extend(["", "## Interpretation", "", "The robust offset is the practical research choice, not a promise of safety. The sample-safe offset avoids every measured pre-main-move fakeout in this dataset but can miss many correct moves. Gaps, slippage, spread expansion, and sub-minute path ordering remain live risks.", ""])
    return "\n".join(lines)


def run() -> dict[str, object]:
    args = parse_args()
    calendar = load_calendar()
    spread_by_year = annual_spreads(calendar)
    available_end = max(event.release_utc for event in calendar)
    requested_end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc) if args.end else available_end
    end = min(requested_end, available_end)
    start = end - timedelta(days=365.2425 * args.years)
    events = [event for event in calendar if start <= event.release_utc <= end]
    rows: list[EventMove] = []
    skipped: list[str] = []
    for event in events:
        try:
            move = analyze_event(event, args.horizon_minutes, spread_by_year)
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            skipped.append(f"{event.release_utc.isoformat()} {event.event}: {exc}")
            continue
        if move is None:
            skipped.append(f"{event.release_utc.isoformat()} {event.event}: insufficient bars")
        else:
            rows.append(move)
    if not rows:
        raise RuntimeError("No usable event records were produced.")

    summaries = []
    for event_name in EVENT_ORDER:
        subset = [row for row in rows if row.event == event_name]
        if subset:
            summaries.append(summarize(event_name, subset, args.offset_step))
    summaries.append(summarize("ALL", rows, args.offset_step))

    max_offset = strictly_above(max(row.correct_move_usd for row in rows), args.offset_step)
    sweep_rows = []
    for group in (*EVENT_ORDER, "ALL"):
        subset = rows if group == "ALL" else [row for row in rows if row.event == group]
        if not subset:
            continue
        for index in range(1, int(max_offset / args.offset_step) + 1):
            offset = round(index * args.offset_step, 8)
            sweep_rows.append({"event": group, "offset_usd": offset, **offset_metrics(subset, offset)})

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    event_cases = []
    for row in rows:
        record = asdict(row)
        case_safe_offset = strictly_above(row.fakeout_usd, args.offset_step)
        record["minimum_observed_safe_offset_usd"] = case_safe_offset
        record["correct_move_reached_case_safe_offset"] = row.correct_move_usd >= case_safe_offset
        event_cases.append(record)
    write_csv(OUTPUT_DIR / "event_cases.csv", event_cases)
    write_csv(OUTPUT_DIR / "event_summary.csv", summaries)
    write_csv(OUTPUT_DIR / "offset_sweep.csv", sweep_rows)
    report_text = markdown_report(start, end, args.horizon_minutes, summaries, skipped)
    (OUTPUT_DIR / "REPORT.md").write_text(report_text, encoding="utf-8")
    report = {"range": {"start": start.isoformat(), "end": end.isoformat()}, "horizon_minutes": args.horizon_minutes, "usable_events": len(rows), "skipped": skipped, "annual_median_spread_for_side_reconstruction": spread_by_year, "summary": summaries}
    (OUTPUT_DIR / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(report_text)
    return report


if __name__ == "__main__":
    run()
