from __future__ import annotations

import json
import re
from functools import lru_cache
from html import unescape
from pathlib import Path
from typing import Any

from .catalog import BOOKMAPER_ROOT, FILTERED_AUDIT_ROOT, PACKAGE_ROOT, Product


ACTIVE_AUDIT_ROOT = PACKAGE_ROOT / "Active BAT Backtest 2026-08-12"
ACTIVE_REPORTS_ROOT = ACTIVE_AUDIT_ROOT / "MT5 Reports"
ACTIVE_RESULTS_PATH = ACTIVE_AUDIT_ROOT / "portfolio-results.json"

CUSTOM_SERIES: dict[str, tuple[Path, str]] = {
    "US100 ORB 0.5R": (
        PACKAGE_ROOT
        / "US100 Selective ORB Research 2026-08-21"
        / "native-rr05-bat-one-year-results.json",
        "one-year-2025-2026",
    ),
    "US100 ORB 2R": (
        PACKAGE_ROOT
        / "US100 Selective ORB Research 2026-08-21"
        / "native-v3-time-direction-results.json",
        "one-year-2025-2026",
    ),
    "Nasdaq 5M Open EMA ATR": (
        PACKAGE_ROOT
        / "Nasdaq 5M Open EMA ATR Research 2026-08-20"
        / "literal-hold-results.json",
        "literal-hold-website-one-year",
    ),
}

CUSTOM_REPORTS: dict[str, Path] = {
    "US100 Fabio ORB 1R": (
        PACKAGE_ROOT
        / "US100 Fabio ORB Volatility Target Research 2026-08-26"
        / "Backtest Reports"
        / "literal-one-year-every-tick.htm"
    ),
    "BTC Top Down FVG Liquidity": (
        PACKAGE_ROOT
        / "Top Down FVG Liquidity Research 2026-08-27"
        / "Backtest Reports"
        / "btcusd-locked-year.htm"
    ),
    "ETH Top Down FVG Liquidity": (
        PACKAGE_ROOT
        / "Top Down FVG Liquidity Research 2026-08-27"
        / "Backtest Reports"
        / "ethusd-locked-year.htm"
    ),
}

INSTALLER_LABEL_ALIASES = {
    "AAA Final News Pulse - NFP CPI FOMC - LONG ONLY ROBUST 60s": "AAA Final News Pulse — long only",
}

ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
CELL_RE = re.compile(r"<td\b[^>]*>(.*?)</td>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
TIME_RE = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _clean_cell(value: str) -> str:
    return " ".join(unescape(TAG_RE.sub("", value)).replace("\xa0", " ").split())


def _number(value: str) -> float:
    return float(value.replace(" ", "").replace(",", ""))


def _sample(series: list[dict[str, Any]], maximum: int = 900) -> list[dict[str, Any]]:
    if len(series) <= maximum:
        return series
    step = (len(series) - 1) / (maximum - 1)
    indexes = sorted({round(index * step) for index in range(maximum)} | {0, len(series) - 1})
    return [series[index] for index in indexes]


@lru_cache(maxsize=32)
def parse_mt5_balance_series(report_path: Path) -> tuple[dict[str, Any], ...]:
    raw: str | None = None
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            raw = report_path.read_text(encoding=encoding)
            break
        except UnicodeError:
            continue
    if raw is None:
        return ()

    marker = raw.lower().find("<b>deals</b>")
    if marker < 0:
        return ()

    series: list[dict[str, Any]] = []
    for row_html in ROW_RE.findall(raw[marker:]):
        cells = [_clean_cell(cell) for cell in CELL_RE.findall(row_html)]
        if len(cells) < 12 or not TIME_RE.match(cells[0]):
            continue
        try:
            balance = _number(cells[11])
        except ValueError:
            continue
        series.append(
            {
                "time": cells[0].replace(".", "-", 2).replace(" ", "T", 1),
                "balance": round(balance, 2),
            }
        )
    return tuple(_sample(series))


def _normalise_json_series(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for point in values:
        timestamp = point.get("time") or point.get("date")
        balance = point.get("balance")
        if timestamp is None or balance is None:
            continue
        text_time = str(timestamp).replace(" ", "T", 1)
        series.append({"time": text_time, "balance": round(float(balance), 2)})
    return _sample(series)


@lru_cache(maxsize=1)
def _active_bot_rows() -> tuple[dict[str, Any], ...]:
    if not ACTIVE_RESULTS_PATH.is_file():
        return ()
    data = _load_json(ACTIVE_RESULTS_PATH)
    return tuple(data.get("bots", []))


def _active_report_for(installer_label: str) -> Path | None:
    wanted = INSTALLER_LABEL_ALIASES.get(installer_label, installer_label)
    for row in _active_bot_rows():
        if row.get("label") == wanted and row.get("file"):
            path = ACTIVE_REPORTS_ROOT / str(row["file"])
            return path if path.is_file() else None
    return None


@lru_cache(maxsize=8)
def _custom_series(label: str) -> tuple[dict[str, Any], ...]:
    config = CUSTOM_SERIES.get(label)
    if config is None:
        return ()
    path, case_name = config
    if not path.is_file():
        return ()
    data = _load_json(path)
    rows = data if isinstance(data, list) else [data]
    selected = next((row for row in rows if row.get("case") == case_name), None)
    if selected is None:
        return ()
    return tuple(_normalise_json_series(selected.get("series", [])))


def product_equity_series(product: Product) -> list[dict[str, Any]]:
    if product.label == "XAU Markov Regime":
        path = BOOKMAPER_ROOT / "artifacts" / "standalone-results.json"
        if path.is_file():
            row = _load_json(path).get("xau", {}).get("optimized", {})
            return [
                {"time": str(point["date"]), "balance": round(float(point["equity"]), 2)}
                for point in row.get("equity", [])
            ]
    native_filtered = {
        "Asia Breakout": "asia.htm",
        "DmC": "dmc.htm",
        "XAU Weakness": "xau-weakness.htm",
    }
    if product.label in native_filtered:
        path = PACKAGE_ROOT / "_Backtests" / "MT5-DMC-20260811" / "reports" / "selected-regime-20260828" / native_filtered[product.label]
        if path.is_file():
            return [dict(point) for point in parse_mt5_balance_series(path)]
    custom_report = CUSTOM_REPORTS.get(product.label)
    if custom_report is not None and custom_report.is_file():
        return [dict(point) for point in parse_mt5_balance_series(custom_report)]
    custom = _custom_series(product.label)
    if custom:
        return [dict(point) for point in custom]
    report = _active_report_for(product.installer_label)
    if report is None:
        return []
    return [dict(point) for point in parse_mt5_balance_series(report)]


@lru_cache(maxsize=1)
def portfolio_equity_series() -> tuple[dict[str, Any], ...]:
    filtered_path = FILTERED_AUDIT_ROOT / "portfolio-results.json"
    if filtered_path.is_file():
        data = _load_json(filtered_path)
        return tuple(_sample(data.get("combined", {}).get("series", [])))
    events: list[tuple[str, float]] = []
    for row in _active_bot_rows():
        filename = row.get("file")
        if not filename:
            continue
        series = parse_mt5_balance_series(ACTIVE_REPORTS_ROOT / str(filename))
        for previous, current in zip(series, series[1:]):
            events.append((str(current["time"]), float(current["balance"]) - float(previous["balance"])))

    balance = 10_000.0
    combined: list[dict[str, Any]] = []
    if events:
        combined.append({"time": min(timestamp for timestamp, _delta in events), "balance": balance})
    for timestamp, delta in sorted(events, key=lambda item: item[0]):
        balance += delta
        combined.append({"time": timestamp, "balance": round(balance, 2)})
    return tuple(_sample(combined))
