from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from bs4 import BeautifulSoup

from .backtest import calculate_metrics
from .config import ACTIVE_RISK_JSON, ASSETS, INITIAL_BALANCE
from .regime import walk_forward_signals


TIME_PATTERN = re.compile(r"^\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}$")


@dataclass(frozen=True)
class ActiveTrade:
    trade_id: str
    bot: str
    symbol: str
    asset_key: str
    direction: str
    open_time: datetime
    close_time: datetime
    base_net: float


def _compact(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def _number(value: str) -> float:
    cleaned = _compact(value).replace(" ", "").replace(",", "")
    return float(cleaned) if cleaned else 0.0


def _read_report(path: Path) -> str:
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeError:
            continue
    raise UnicodeError(f"Could not decode {path}")


def _asset_for_symbol(symbol: str) -> str | None:
    canonical = symbol.upper().replace(".", "")
    if "XAU" in canonical:
        return "xau"
    if "USTEC" in canonical or "US100" in canonical or "UT100" in canonical:
        return "us100"
    if "BTC" in canonical:
        return "btc"
    if "ETH" in canonical:
        return "eth"
    if "US30" in canonical:
        return "us30"
    return None


def parse_mt5_trades(path: Path, label: str, symbol: str) -> tuple[list[ActiveTrade], dict[str, Any]]:
    asset_key = _asset_for_symbol(symbol)
    if asset_key is None:
        return [], {"report": str(path), "skipped": f"Unsupported symbol {symbol}"}
    soup = BeautifulSoup(_read_report(path), "html.parser")
    in_deals = False
    open_legs: list[dict[str, Any]] = []
    trades: list[ActiveTrade] = []
    leftover_cashflow = 0.0

    for row in soup.find_all("tr"):
        if _compact(row.get_text(" ", strip=True)) == "Deals":
            in_deals = True
            continue
        if not in_deals:
            continue
        cells = [_compact(cell.get_text(" ", strip=True)) for cell in row.find_all("td", recursive=False)]
        if len(cells) != 13 or not TIME_PATTERN.fullmatch(cells[0]):
            continue
        if cells[3].lower() == "balance":
            continue
        when = datetime.strptime(cells[0], "%Y.%m.%d %H:%M:%S")
        entry_type = cells[4].lower()
        side = cells[3].lower()
        volume = _number(cells[5])
        cashflow = _number(cells[8]) + _number(cells[9]) + _number(cells[10])
        if entry_type == "in":
            open_legs.append(
                {"time": when, "volume": volume, "cost": cashflow, "side": side}
            )
            continue
        if entry_type not in {"out", "in/out", "inout"}:
            leftover_cashflow += cashflow
            continue

        remaining = volume
        entry_cost = 0.0
        open_times: list[datetime] = []
        sides: list[str] = []
        while remaining > 1e-9 and open_legs:
            leg = open_legs[0]
            available = float(leg["volume"])
            take = min(remaining, available)
            ratio = take / available if available else 0.0
            entry_cost += float(leg["cost"]) * ratio
            open_times.append(leg["time"])
            sides.append(str(leg["side"]))
            leg["volume"] = available - take
            leg["cost"] = float(leg["cost"]) * (1.0 - ratio)
            remaining -= take
            if float(leg["volume"]) <= 1e-9:
                open_legs.pop(0)
        open_time = min(open_times) if open_times else when
        direction = sides[0] if sides else ("buy" if side == "sell" else "sell")
        trades.append(
            ActiveTrade(
                trade_id=f"{label}:{len(trades) + 1}",
                bot=label,
                symbol=symbol,
                asset_key=asset_key,
                direction=direction,
                open_time=open_time,
                close_time=when,
                base_net=entry_cost + cashflow,
            )
        )

    leftover_cashflow += sum(float(leg["cost"]) for leg in open_legs)
    if trades and abs(leftover_cashflow) > 1e-9:
        last = trades[-1]
        trades[-1] = ActiveTrade(
            **(asdict(last) | {"base_net": last.base_net + leftover_cashflow})
        )
    return trades, {
        "report": str(path),
        "parsed_trades": len(trades),
        "parsed_net": round(sum(item.base_net for item in trades), 2),
        "leftover_cashflow": round(leftover_cashflow, 8),
    }


def load_active_trades() -> tuple[list[ActiveTrade], list[dict[str, Any]]]:
    manifest = json.loads(ACTIVE_RISK_JSON.read_text(encoding="utf-8-sig"))
    all_trades: list[ActiveTrade] = []
    audits: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        report = Path(source["report"])
        trades, audit = parse_mt5_trades(report, source["label"], source["symbol"])
        audit.update({"label": source["label"], "symbol": source["symbol"]})
        audits.append(audit)
        all_trades.extend(trades)
    all_trades.sort(key=lambda item: (item.close_time, item.open_time, item.trade_id))
    return all_trades, audits


def _prior_signal(signal: pd.Series, when: datetime) -> float | None:
    # Strictly earlier daily close: an intraday trade cannot use its own day's close.
    index = signal.index.searchsorted(pd.Timestamp(when.date()), side="left") - 1
    if index < 0:
        return None
    value = signal.iloc[index]
    return float(value) if pd.notna(value) else None


def _cashflow_result(trades: list[ActiveTrade]) -> dict[str, Any]:
    ordered = sorted(trades, key=lambda item: (item.close_time, item.trade_id))
    balance = INITIAL_BALANCE
    values = [balance]
    dates = [pd.Timestamp(ordered[0].open_time) if ordered else pd.Timestamp("2025-08-11")]
    shaped: list[dict[str, Any]] = []
    for trade in ordered:
        balance += trade.base_net
        values.append(balance)
        dates.append(pd.Timestamp(trade.close_time))
        shaped.append({"net": trade.base_net})
    equity = pd.Series(values, index=pd.DatetimeIndex(dates), name="Balance")
    return {
        "metrics": calculate_metrics(equity, shaped),
        "equity": equity,
    }


def evaluate_regime_filter(
    market: dict[str, pd.DataFrame],
    selected_configs: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    trades, audits = load_active_trades()
    signals: dict[str, pd.Series] = {}
    for key, frame in market.items():
        config = selected_configs[key]
        signals[key] = walk_forward_signals(
            frame["Close"], window=int(config["window"]), threshold=float(config["threshold"])
        )["signal"]

    accepted: list[ActiveTrade] = []
    decisions: list[dict[str, Any]] = []
    for trade in trades:
        if trade.asset_key not in signals:
            decisions.append(asdict(trade) | {"accepted": True, "reason": "No regime proxy"})
            accepted.append(trade)
            continue
        raw = _prior_signal(signals[trade.asset_key], trade.open_time)
        gate = float(selected_configs[trade.asset_key]["signal_gate"])
        wanted = 1 if trade.direction == "buy" else -1
        passed = raw is not None and ((raw > gate) if wanted > 0 else (raw < -gate))
        decisions.append(
            asdict(trade)
            | {
                "signal": raw,
                "gate": gate,
                "accepted": passed,
                "reason": "aligned" if passed else "regime veto",
            }
        )
        if passed:
            accepted.append(trade)

    baseline = _cashflow_result(trades)
    filtered = _cashflow_result(accepted)
    by_bot: list[dict[str, Any]] = []
    for label in sorted({trade.bot for trade in trades}):
        original = [trade for trade in trades if trade.bot == label]
        kept = [trade for trade in accepted if trade.bot == label]
        by_bot.append(
            {
                "ea": label,
                "symbol": original[0].symbol,
                "baseline": _cashflow_result(original)["metrics"],
                "filtered": _cashflow_result(kept)["metrics"],
                "accepted_pct": round(len(kept) / len(original) * 100.0 if original else 0.0, 2),
            }
        )
    return {
        "baseline": baseline,
        "filtered": filtered,
        "by_ea": by_bot,
        "audits": audits,
        "decisions": decisions,
    }
