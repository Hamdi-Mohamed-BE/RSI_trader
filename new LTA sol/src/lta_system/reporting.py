from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pandas as pd

from .backtest import BacktestResult
from .validation import ValidationResult


def save_backtest(result: BacktestResult, directory: Path, stem: str) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    trades_path = directory / f"{stem}_trades.csv"
    summary_path = directory / f"{stem}_summary.json"
    pd.DataFrame([trade.to_dict() for trade in result.trades]).to_csv(
        trades_path, index=False
    )
    summary_path.write_text(
        json.dumps(result.stats.to_dict(), indent=2, allow_nan=True),
        encoding="utf-8",
    )
    return trades_path, summary_path


def save_validation(
    result: ValidationResult,
    directory: Path,
    stem: str,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stem}_validation.json"
    payload = {
        "baseline": result.baseline.stats.to_dict(),
        "splits": [asdict(item) for item in result.splits],
        "stress": list(result.stress),
        "approved_for_forward": result.approved_for_forward,
        "reasons": list(result.reasons),
    }
    path.write_text(
        json.dumps(payload, indent=2, default=str, allow_nan=True),
        encoding="utf-8",
    )
    return path

