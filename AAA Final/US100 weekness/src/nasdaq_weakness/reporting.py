from __future__ import annotations

from dataclasses import asdict
import json
import math
from pathlib import Path

import pandas as pd

from .models import BacktestResult


def _json_default(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, float) and math.isinf(value):
        return "Infinity"
    raise TypeError(f"Cannot serialize {type(value)!r}")


def save_backtest(
    result: BacktestResult, reports_dir: Path, stem: str
) -> tuple[Path, Path]:
    journal = reports_dir / f"{stem}_trades.csv"
    summary = reports_dir / f"{stem}_summary.json"
    pd.DataFrame([asdict(item) for item in result.trades]).to_csv(
        journal, index=False
    )
    payload = {
        "symbol": result.symbol,
        "start": result.start,
        "end": result.end,
        "parameters": result.parameters,
        "stats": asdict(result.stats),
    }
    summary.write_text(
        json.dumps(payload, indent=2, default=_json_default),
        encoding="utf-8",
    )
    return journal, summary


def save_optimization(payload: dict[str, object], reports_dir: Path) -> Path:
    symbol = str(payload["symbol"])
    path = reports_dir / f"{symbol}_optimization.json"
    serializable = {
        key: value for key, value in payload.items() if key != "full_result"
    }
    path.write_text(
        json.dumps(serializable, indent=2, default=_json_default),
        encoding="utf-8",
    )
    leaderboard = reports_dir / f"{symbol}_leaderboard.csv"
    pd.DataFrame(payload["leaderboard"]).to_csv(leaderboard, index=False)
    save_backtest(
        payload["full_result"], reports_dir, f"{symbol}_optimized_full"
    )
    return path
