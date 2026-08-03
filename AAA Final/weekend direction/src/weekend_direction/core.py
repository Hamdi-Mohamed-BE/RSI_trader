from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from statistics import median
from typing import Iterable

import numpy as np


@dataclass(frozen=True)
class SessionTiming:
    close_minute_of_week: int
    reopen_minute_of_week: int
    observations: int


@dataclass(frozen=True)
class MomentumSignal:
    side: str
    return_24h: float
    threshold: float
    close_utc: datetime
    week_id: str


def model_validated(metadata_path: Path, artifact: object | None = None) -> bool:
    if isinstance(artifact, dict) and artifact.get("validated") is False:
        return False
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    return metadata.get("selected_model", {}).get("deployment_status") == "validated"


def infer_weekly_timing(times: Iterable[int], minimum_gap_hours: int = 24) -> SessionTiming:
    stamps = sorted(int(value) for value in times)
    pairs: list[tuple[datetime, datetime]] = []
    for left, right in zip(stamps, stamps[1:]):
        if right - left >= minimum_gap_hours * 3600:
            pairs.append((datetime.fromtimestamp(left, timezone.utc), datetime.fromtimestamp(right, timezone.utc)))
    if len(pairs) < 4:
        raise RuntimeError("History does not contain enough stable weekly close/reopen gaps")
    close_minutes = [left.weekday() * 1440 + left.hour * 60 + left.minute for left, _ in pairs]
    reopen_minutes = [right.weekday() * 1440 + right.hour * 60 + right.minute for _, right in pairs]
    return SessionTiming(int(round(median(close_minutes))), int(round(median(reopen_minutes))), len(pairs))


def prior_only_threshold(friday_returns: list[float], quantile: float) -> float:
    if len(friday_returns) < 12:
        raise RuntimeError("At least 12 earlier Fridays are required")
    return float(np.quantile(np.abs(np.asarray(friday_returns, dtype=float)), quantile))


def momentum_signal(*, current_return: float, prior_returns: list[float], quantile: float, close_utc: datetime) -> MomentumSignal | None:
    threshold = prior_only_threshold(prior_returns, quantile)
    if abs(current_return) < threshold:
        return None
    return MomentumSignal("BUY" if current_return > 0 else "SELL", current_return, threshold, close_utc, close_utc.strftime("%G-W%V"))


def risk_sized_volume(cash_risk: float, loss_per_lot: float, minimum: float, maximum: float, step: float) -> float | None:
    if cash_risk <= 0 or loss_per_lot <= 0 or minimum * loss_per_lot > cash_risk + 1e-8:
        return None
    raw = min(maximum, cash_risk / loss_per_lot)
    volume = math.floor(raw / step + 1e-12) * step
    return round(max(minimum, volume), 8)


def discover_gold_symbol(symbols: Iterable[object]) -> object:
    matches = []
    for info in symbols:
        name = str(getattr(info, "name", ""))
        upper = name.upper()
        description = str(getattr(info, "description", "")).lower()
        is_gold = upper.startswith("XAUUSD") or upper == "GOLD" or "gold" in description
        is_usd = "USD" in upper or "us dollar" in description
        if is_gold and is_usd and int(getattr(info, "trade_mode", 0)) != 0:
            matches.append((0 if upper == "XAUUSD" else 1 if upper.startswith("XAUUSD") else 2, info))
    if not matches:
        raise RuntimeError("No tradable Gold-versus-USD symbol found")
    return min(matches, key=lambda item: (item[0], str(item[1].name)))[1]
