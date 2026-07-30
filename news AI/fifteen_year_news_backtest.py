from __future__ import annotations

import csv
import json
import math
import re
import subprocess
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, pstdev
from zoneinfo import ZoneInfo

import numpy as np
import requests
from bs4 import BeautifulSoup
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, log_loss, roc_auc_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "news-event-days"
CALENDAR_PATH = ROOT / "news_15y_calendar.csv"
EVENT_DATES_PATH = ROOT / "news_15y_event_dates.json"
DETAIL_PATH = ROOT / "news_15y_validation_events.csv"
SUMMARY_PATH = ROOT / "news_15y_event_summary.csv"
REPORT_PATH = ROOT / "news_15y_report.json"

END_DATE = date(2026, 7, 29)
START_DATE = date(2011, 7, 30)
TEST_START = date(2024, 7, 30)
NY = ZoneInfo("America/New_York")
USER_AGENT = "Mozilla/5.0 (compatible; XAU-event-research/1.0; contact=research@example.com)"
EVENT_ORDER = ["NFP", "GDP", "CPI", "PPI", "FOMC"]
FEATURE_NAMES = [
    "ret_5",
    "ret_15",
    "ret_30",
    "ret_60",
    "range_15_atr",
    "range_30_atr",
    "body_15_atr",
    "volume_z",
    "distance_2h_open_atr",
    "pre_spread_atr",
    *[f"event_{name}" for name in EVENT_ORDER],
]


@dataclass(frozen=True)
class Event:
    event: str
    release_utc: datetime
    title: str
    source: str


def get_soup(url: str) -> BeautifulSoup:
    last_error = None
    for attempt in range(4):
        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=45)
            response.raise_for_status()
            return BeautifulSoup(response.text, "html.parser")
        except requests.RequestException as error:
            last_error = error
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to fetch official calendar page after retries: {url}") from last_error


def bls_events(name: str, archive_slug: str) -> list[Event]:
    soup = get_soup(f"https://www.bls.gov/bls/news-release/{archive_slug}.htm")
    found: dict[date, Event] = {}
    pattern = re.compile(rf"/{archive_slug}_(\d{{8}})\.(?:htm|pdf)$", re.I)
    for link in soup.select("a[href]"):
        match = pattern.search(link.get("href", ""))
        if not match:
            continue
        released = datetime.strptime(match.group(1), "%m%d%Y").date()
        if START_DATE <= released <= END_DATE:
            local = datetime.combine(released, datetime.min.time(), NY).replace(hour=8, minute=30)
            found[released] = Event(name, local.astimezone(timezone.utc), link.get_text(" ", strip=True), "BLS")
    return sorted(found.values(), key=lambda event: event.release_utc)


def gdp_events() -> list[Event]:
    found: dict[date, Event] = {}
    for page in range(18):
        soup = get_soup(
            "https://www.bea.gov/news/archive"
            f"?field_related_product_target_id=451&created_1=All&title=&page={page}"
        )
        for row in soup.select("table tbody tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            title = cells[0].get_text(" ", strip=True)
            normalized = title.lower()
            if "gdp" not in normalized and "gross domestic product" not in normalized:
                continue
            if "advance estimate" not in normalized and "initial estimate" not in normalized:
                continue
            try:
                released = datetime.strptime(cells[1].get_text(" ", strip=True), "%B %d, %Y").date()
            except ValueError:
                continue
            if START_DATE <= released <= END_DATE:
                local = datetime.combine(released, datetime.min.time(), NY).replace(hour=8, minute=30)
                found[released] = Event("GDP", local.astimezone(timezone.utc), title, "BEA")
    return sorted(found.values(), key=lambda event: event.release_utc)


FOMC_DATES = """
2011-08-09,2011-09-21,2011-11-02,2011-12-13,
2012-01-25,2012-03-13,2012-04-25,2012-06-20,2012-08-01,2012-09-13,2012-10-24,2012-12-12,
2013-01-30,2013-03-20,2013-05-01,2013-06-19,2013-07-31,2013-09-18,2013-10-30,2013-12-18,
2014-01-29,2014-03-19,2014-04-30,2014-06-18,2014-07-30,2014-09-17,2014-10-29,2014-12-17,
2015-01-28,2015-03-18,2015-04-29,2015-06-17,2015-07-29,2015-09-17,2015-10-28,2015-12-16,
2016-01-27,2016-03-16,2016-04-27,2016-06-15,2016-07-27,2016-09-21,2016-11-02,2016-12-14,
2017-02-01,2017-03-15,2017-05-03,2017-06-14,2017-07-26,2017-09-20,2017-11-01,2017-12-13,
2018-01-31,2018-03-21,2018-05-02,2018-06-13,2018-08-01,2018-09-26,2018-11-08,2018-12-19,
2019-01-30,2019-03-20,2019-05-01,2019-06-19,2019-07-31,2019-09-18,2019-10-30,2019-12-11,
2020-01-29,2020-04-29,2020-06-10,2020-07-29,2020-09-16,2020-11-05,2020-12-16,
2021-01-27,2021-03-17,2021-04-28,2021-06-16,2021-07-28,2021-09-22,2021-11-03,2021-12-15,
2022-01-26,2022-03-16,2022-05-04,2022-06-15,2022-07-27,2022-09-21,2022-11-02,2022-12-14,
2023-02-01,2023-03-22,2023-05-03,2023-06-14,2023-07-26,2023-09-20,2023-11-01,2023-12-13,
2024-01-31,2024-03-20,2024-05-01,2024-06-12,2024-07-31,2024-09-18,2024-11-07,2024-12-18,
2025-01-29,2025-03-19,2025-05-07,2025-06-18,2025-07-30,2025-09-17,2025-10-29,2025-12-10,
2026-01-28,2026-03-18,2026-04-29,2026-06-17,2026-07-29
"""


def fomc_events() -> list[Event]:
    events = []
    for raw in FOMC_DATES.replace("\n", "").split(","):
        if not raw.strip():
            continue
        released = date.fromisoformat(raw.strip())
        if START_DATE <= released <= END_DATE:
            local = datetime.combine(released, datetime.min.time(), NY).replace(hour=14)
            events.append(Event("FOMC", local.astimezone(timezone.utc), "Federal Reserve FOMC statement", "FRB"))
    return events


def build_calendar(refresh: bool = False) -> list[Event]:
    if CALENDAR_PATH.exists() and not refresh:
        with CALENDAR_PATH.open(newline="", encoding="utf-8") as handle:
            cached = [
                Event(
                    row["event"],
                    datetime.fromisoformat(row["release_utc"]),
                    row["title"],
                    row["source"],
                )
                for row in csv.DictReader(handle)
            ]
        if len(cached) >= 700:
            EVENT_DATES_PATH.write_text(
                json.dumps(sorted({event.release_utc.date().isoformat() for event in cached}), indent=2),
                encoding="utf-8",
            )
            return cached
    events = [
        *bls_events("NFP", "empsit"),
        *bls_events("CPI", "cpi"),
        *bls_events("PPI", "ppi"),
        *gdp_events(),
        *fomc_events(),
    ]
    events.sort(key=lambda event: event.release_utc)
    with CALENDAR_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["event", "release_utc", "title", "source"])
        writer.writeheader()
        for event in events:
            writer.writerow({**asdict(event), "release_utc": event.release_utc.isoformat()})
    dates = sorted({event.release_utc.date().isoformat() for event in events})
    EVENT_DATES_PATH.write_text(json.dumps(dates, indent=2), encoding="utf-8")
    return events


def ensure_market_data() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    dates = json.loads(EVENT_DATES_PATH.read_text(encoding="utf-8"))
    available = 0
    for day in dates:
        sizes = [
            (DATA_DIR / f"xauusd-m1-{price_type}-{day}.json").stat().st_size
            if (DATA_DIR / f"xauusd-m1-{price_type}-{day}.json").exists()
            else 0
            for price_type in ("bid", "ask")
        ]
        available += int(max(sizes) > 100)
    if available >= len(dates) - 20:
        return
    command = [
        "node",
        str(ROOT / "download_event_data.js"),
        str(EVENT_DATES_PATH),
        str(DATA_DIR),
        "10",
    ]
    result = subprocess.run(command, cwd=ROOT, check=False)
    if result.returncode:
        raise RuntimeError(f"Market-data downloader failed with exit code {result.returncode}")


def normalize_rows(raw: object) -> list[dict[str, float]]:
    if isinstance(raw, dict):
        for key in ("data", "rates", "items"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
    if not isinstance(raw, list):
        return []
    rows = []
    for item in raw:
        if isinstance(item, list) and len(item) >= 5:
            timestamp, open_, high, low, close = item[:5]
            volume = item[5] if len(item) > 5 else 0.0
        elif isinstance(item, dict):
            timestamp = item.get("timestamp") or item.get("time")
            open_, high, low, close = (item.get(key) for key in ("open", "high", "low", "close"))
            volume = item.get("volume", 0.0)
        else:
            continue
        if timestamp is None or close is None:
            continue
        stamp = float(timestamp)
        if stamp < 10_000_000_000:
            stamp *= 1000
        rows.append(
            {
                "timestamp": stamp,
                "open": float(open_),
                "high": float(high),
                "low": float(low),
                "close": float(close),
                "volume": float(volume or 0),
            }
        )
    return rows


def load_day(day: str, price_type: str) -> dict[int, dict[str, float]]:
    path = DATA_DIR / f"xauusd-m1-{price_type}-{day}.json"
    rows = normalize_rows(json.loads(path.read_text(encoding="utf-8")))
    return {round(row["timestamp"] / 60_000) * 60_000: row for row in rows}


def annual_spreads(days: list[str]) -> dict[int, float]:
    by_year: dict[int, list[float]] = defaultdict(list)
    for day in days:
        bid = load_day(day, "bid")
        ask = load_day(day, "ask")
        common = sorted(set(bid) & set(ask))
        for stamp in common[::60]:
            spread = ask[stamp]["close"] - bid[stamp]["close"]
            if 0 < spread < 20:
                by_year[int(day[:4])].append(spread)
    populated = {year: float(np.median(values)) for year, values in by_year.items() if values}
    global_median = float(np.median([value for values in by_year.values() for value in values]))
    return {year: populated.get(year, global_median) for year in range(START_DATE.year, END_DATE.year + 1)}


def complete_sides(
    bid: dict[int, dict[str, float]],
    ask: dict[int, dict[str, float]],
    spread: float,
) -> tuple[dict[int, dict[str, float]], dict[int, dict[str, float]], str | None]:
    if bid and ask:
        return bid, ask, None
    if not bid and not ask:
        return bid, ask, None
    source = ask if ask else bid
    direction = -1 if ask else 1
    synthetic = {}
    for stamp, row in source.items():
        synthetic[stamp] = {
            **row,
            **{key: row[key] + direction * spread for key in ("open", "high", "low", "close")},
        }
    if ask:
        return synthetic, ask, "bid"
    return bid, synthetic, "ask"


def nearest(data: dict[int, dict[str, float]], stamp: int, tolerance: int = 2) -> dict[str, float] | None:
    for offset in range(tolerance + 1):
        for candidate in (stamp - offset * 60_000, stamp + offset * 60_000):
            if candidate in data:
                return data[candidate]
    return None


def feature_row(event: Event, bid: dict[int, dict[str, float]], ask: dict[int, dict[str, float]]) -> dict | None:
    release_ms = int(event.release_utc.timestamp() * 1000)
    cutoff_ms = release_ms - 30 * 60_000
    release_bid = nearest(bid, release_ms)
    release_ask = nearest(ask, release_ms)
    pre_bid = nearest(bid, release_ms - 60_000)
    pre_ask = nearest(ask, release_ms - 60_000)
    cutoff = nearest(bid, cutoff_ms)
    if not all((release_bid, release_ask, pre_bid, pre_ask, cutoff)):
        return None

    history = []
    for minutes in range(121, -1, -1):
        row = nearest(bid, cutoff_ms - minutes * 60_000, tolerance=0)
        if row:
            history.append(row)
    if len(history) < 100:
        return None

    closes = np.array([row["close"] for row in history], dtype=float)
    highs = np.array([row["high"] for row in history], dtype=float)
    lows = np.array([row["low"] for row in history], dtype=float)
    opens = np.array([row["open"] for row in history], dtype=float)
    volumes = np.array([row["volume"] for row in history], dtype=float)
    true_ranges = np.maximum(highs[1:] - lows[1:], np.maximum(abs(highs[1:] - closes[:-1]), abs(lows[1:] - closes[:-1])))
    atr = float(np.mean(true_ranges[-30:]))
    if atr <= 0:
        return None

    def ret(minutes: int) -> float:
        return (closes[-1] - closes[-1 - minutes]) / atr

    day_open = opens[0]
    volume_std = float(np.std(volumes[-60:]))
    features = [
        ret(5),
        ret(15),
        ret(30),
        ret(60),
        (float(np.max(highs[-15:])) - float(np.min(lows[-15:]))) / atr,
        (float(np.max(highs[-30:])) - float(np.min(lows[-30:]))) / atr,
        (closes[-1] - opens[-15]) / atr,
        0.0 if volume_std == 0 else (float(np.mean(volumes[-5:])) - float(np.mean(volumes[-60:]))) / volume_std,
        (closes[-1] - day_open) / atr,
        (pre_ask["close"] - pre_bid["close"]) / atr,
        *[1.0 if event.event == name else 0.0 for name in EVENT_ORDER],
    ]

    pre_mid = (pre_bid["close"] + pre_ask["close"]) / 2
    release_mid = (release_bid["close"] + release_ask["close"]) / 2
    target = 1 if release_mid > pre_mid else 0
    return {
        "event": event.event,
        "release_utc": event.release_utc.isoformat(),
        "features": features,
        "target": target,
        "actual_direction": "UP" if target else "DOWN",
        "buy_pnl": release_bid["close"] - pre_ask["close"],
        "sell_pnl": pre_bid["close"] - release_ask["close"],
        "entry_bid": pre_bid["close"],
        "entry_ask": pre_ask["close"],
        "exit_bid": release_bid["close"],
        "exit_ask": release_ask["close"],
        "spread": pre_ask["close"] - pre_bid["close"],
        "title": event.title,
    }


def profit_factor(values: list[float]) -> float | None:
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    return None if losses == 0 else gains / losses


def max_drawdown(values: list[float]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return drawdown


def summarize(rows: list[dict]) -> dict:
    pnl = [row["pnl_usd"] for row in rows]
    return {
        "events": len(rows),
        "correct": sum(row["correct"] for row in rows),
        "accuracy_pct": round(100 * mean([row["correct"] for row in rows]), 2) if rows else 0.0,
        "wins": sum(value > 0 for value in pnl),
        "losses": sum(value < 0 for value in pnl),
        "win_rate_pct": round(100 * sum(value > 0 for value in pnl) / len(pnl), 2) if pnl else 0.0,
        "net_gold_pips": round(sum(row["pnl_pips"] for row in rows), 1),
        "net_usd_fresh_100_each": round(sum(pnl), 2),
        "avg_usd": round(mean(pnl), 2) if pnl else 0.0,
        "profit_factor": None if profit_factor(pnl) is None else round(profit_factor(pnl), 3),
        "max_cumulative_drawdown_usd": round(max_drawdown(pnl), 2),
    }


def select_regularization(x_train: np.ndarray, y_train: np.ndarray) -> tuple[float, list[dict]]:
    candidates = [0.03, 0.06, 0.1, 0.2, 0.35, 0.6, 1.0, 2.0]
    splitter = TimeSeriesSplit(n_splits=5)
    scores = []
    for c_value in candidates:
        fold_losses = []
        fold_accuracy = []
        for fit_indices, validation_indices in splitter.split(x_train):
            pipeline = Pipeline(
                [
                    ("scale", StandardScaler()),
                    (
                        "model",
                        LogisticRegression(
                            C=c_value,
                            class_weight="balanced",
                            max_iter=2_000,
                            random_state=42,
                        ),
                    ),
                ]
            )
            pipeline.fit(x_train[fit_indices], y_train[fit_indices])
            probabilities = pipeline.predict_proba(x_train[validation_indices])[:, 1]
            fold_losses.append(log_loss(y_train[validation_indices], probabilities, labels=[0, 1]))
            fold_accuracy.append(accuracy_score(y_train[validation_indices], probabilities >= 0.5))
        scores.append(
            {
                "c": c_value,
                "mean_log_loss": float(mean(fold_losses)),
                "mean_accuracy_pct": 100 * float(mean(fold_accuracy)),
            }
        )
    selected = min(scores, key=lambda item: (item["mean_log_loss"], -item["mean_accuracy_pct"], item["c"]))
    return float(selected["c"]), scores


def run() -> dict:
    events = build_calendar()
    print(f"Calendar: {len(events)} releases from {events[0].release_utc.date()} to {events[-1].release_utc.date()}")
    ensure_market_data()

    day_cache: dict[tuple[str, str], dict[int, dict[str, float]]] = {}
    event_days = sorted({event.release_utc.date().isoformat() for event in events})
    spread_by_year = annual_spreads(event_days)
    samples = []
    skipped = []
    imputed = []
    for event in events:
        day = event.release_utc.date().isoformat()
        for price_type in ("bid", "ask"):
            key = (day, price_type)
            if key not in day_cache:
                day_cache[key] = load_day(day, price_type)
        bid, ask, imputed_side = complete_sides(
            day_cache[(day, "bid")],
            day_cache[(day, "ask")],
            spread_by_year[event.release_utc.year],
        )
        if imputed_side:
            imputed.append({"date": day, "side": imputed_side, "spread": spread_by_year[event.release_utc.year]})
        sample = feature_row(event, bid, ask)
        if sample:
            samples.append(sample)
        else:
            skipped.append({"event": event.event, "release_utc": event.release_utc.isoformat()})

    train = [row for row in samples if date.fromisoformat(row["release_utc"][:10]) < TEST_START]
    test = [row for row in samples if date.fromisoformat(row["release_utc"][:10]) >= TEST_START]
    x_train = np.array([row["features"] for row in train])
    y_train = np.array([row["target"] for row in train])
    x_test = np.array([row["features"] for row in test])
    y_test = np.array([row["target"] for row in test])

    selected_c, cv_scores = select_regularization(x_train, y_train)
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    C=selected_c,
                    class_weight="balanced",
                    max_iter=2_000,
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(x_train, y_train)
    probabilities = model.predict_proba(x_test)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    results = []
    for sample, prediction, probability in zip(test, predictions, probabilities):
        direction = "UP" if prediction else "DOWN"
        pnl_price = sample["buy_pnl"] if prediction else sample["sell_pnl"]
        raw_usd = pnl_price * 100 * 0.08
        pnl_usd = max(-100.0, raw_usd)
        results.append(
            {
                "release_utc": sample["release_utc"],
                "event": sample["event"],
                "prediction": direction,
                "up_probability": round(float(probability), 5),
                "actual": sample["actual_direction"],
                "correct": int(prediction == sample["target"]),
                "entry": round(sample["entry_ask"] if prediction else sample["entry_bid"], 3),
                "exit": round(sample["exit_bid"] if prediction else sample["exit_ask"], 3),
                "spread": round(sample["spread"], 3),
                "pnl_pips": round(pnl_price / 0.01, 1),
                "pnl_usd": round(pnl_usd, 2),
                "balance_if_fresh_100": round(100 + pnl_usd, 2),
                "title": sample["title"],
            }
        )

    fields = list(results[0])
    with DETAIL_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)

    by_event = {name: summarize([row for row in results if row["event"] == name]) for name in EVENT_ORDER}
    with SUMMARY_PATH.open("w", newline="", encoding="utf-8") as handle:
        fields = ["event", *next(iter(by_event.values())).keys()]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for name in EVENT_ORDER:
            writer.writerow({"event": name, **by_event[name]})

    report = {
        "methodology": {
            "window": f"{START_DATE} through {END_DATE}",
            "train": f"{START_DATE} through {TEST_START - timedelta(days=1)}",
            "validation": f"{TEST_START} through {END_DATE}",
            "features_frozen": "30 minutes before each release",
            "target": "XAUUSD direction from T-1 minute executable entry to first release-minute close",
            "data": "Dukascopy XAUUSD M1 bid and ask, BLS/BEA/Federal Reserve release dates",
            "execution": "$100 reset per release, 0.08 lot, 1:500, recorded bid/ask spread, loss capped at $100",
            "warning": "Price-action classifier only; archived analyst consensus and release surprises are not available.",
        },
        "sample": {
            "calendar": len(events),
            "usable": len(samples),
            "train": len(train),
            "validation": len(test),
            "skipped": skipped,
            "imputed_release_sides": len(imputed),
            "imputed_dates": sorted({item["date"] for item in imputed}),
            "annual_median_spread_used_for_imputation": spread_by_year,
        },
        "train_direction_accuracy_pct": round(100 * accuracy_score(y_train, model.predict(x_train)), 2),
        "train_majority_baseline_pct": round(100 * max(float(np.mean(y_train)), 1 - float(np.mean(y_train))), 2),
        "model_selection": {
            "method": "Five-fold expanding-window time-series CV on training data only; minimum log loss",
            "selected_c": selected_c,
            "candidates": cv_scores,
        },
        "validation_direction_accuracy_pct": round(100 * accuracy_score(y_test, predictions), 2),
        "validation_roc_auc": round(float(roc_auc_score(y_test, probabilities)), 4),
        "validation_confusion_matrix": confusion_matrix(y_test, predictions).tolist(),
        "validation_overall": summarize(results),
        "validation_by_event": by_event,
        "feature_names": FEATURE_NAMES,
        "coefficients": {
            name: round(float(value), 6)
            for name, value in zip(FEATURE_NAMES, model.named_steps["model"].coef_[0])
        },
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        sys.exit(130)
