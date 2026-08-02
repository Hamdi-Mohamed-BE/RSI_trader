from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from .article_engine import ArticleParams, backtest_article_model
from .config import Config, load_config
from .engine import Trade, metrics


UTC = timezone.utc


def frozen_params() -> ArticleParams:
    """Model selected only from the 2024-07-30 through 2026-07-30 folds."""
    return ArticleParams(
        enable_fade=True,
        enable_distribution=False,
        trade_london=True,
        trade_new_york=False,
        max_trades_per_day=1,
        fade_rr=2.0,
        distribution_rr=2.0,
        sweep_min_fraction=0.02,
        sweep_max_fraction=0.60,
        breakout_fraction=0.00,
        retest_tolerance_fraction=0.04,
        stop_buffer_fraction=0.03,
        volume_factor=0.0,
        use_regime_filter=True,
        london_window_minutes=180,
        ny_window_minutes=180,
    )


def frozen_config(base: Config) -> Config:
    return replace(
        base,
        risk_pct=3.0,
        lock_trigger_r=0.30,
        lock_profit_r=0.15,
        regime_filter_enabled=True,
        regime_use_relative_atr=True,
        regime_atr_days=5,
        regime_atr_median_days=30,
        regime_atr_ratio_min=0.65,
        regime_atr_ratio_max=1.00,
        regime_asia_median_days=20,
        regime_asia_ratio_min=0.60,
        regime_asia_ratio_max=1.00,
    )


def _read_frame(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["time"] = pd.to_datetime(frame["time"], utc=True)
    return frame.sort_values("time").reset_index(drop=True)


def _slice(
    trades: list[Trade],
    start: datetime,
    end: datetime,
) -> list[Trade]:
    lower = pd.Timestamp(start)
    upper = pd.Timestamp(end)
    return [
        trade
        for trade in trades
        if lower <= pd.Timestamp(trade.entry_time) < upper
    ]


def _metric_row(
    label: str,
    trades: list[Trade],
    config: Config,
) -> dict[str, object]:
    result = metrics("XAUUSD..", trades, 1000.0, config.risk_pct)
    return {
        "period": label,
        "trades": result["trades"],
        "win_rate_pct": result["win_rate_pct"],
        "profit_factor": result["profit_factor"],
        "net_r": result["net_r"],
        "return_pct": result["return_pct"],
        "max_drawdown_pct": result["max_drawdown_pct"],
        "ending_balance": result["ending_balance"],
    }


def run() -> None:
    base = load_config()
    config = frozen_config(base)
    params = frozen_params()
    start = datetime(2023, 7, 30, tzinfo=UTC)
    midpoint = datetime(2024, 1, 30, tzinfo=UTC)
    end = datetime(2024, 7, 30, tzinfo=UTC)
    path = (
        base.root
        / "data"
        / "XAUUSD___20230620_20240730_M1.csv.gz"
    )
    if not path.exists():
        raise FileNotFoundError(path)
    frame = _read_frame(path)
    trades = backtest_article_model(
        frame,
        "XAUUSD..",
        0.01,
        config,
        params,
        start,
        end,
    )
    rows = [
        _metric_row("2023-07-30 to 2024-01-30", _slice(trades, start, midpoint), config),
        _metric_row("2024-01-30 to 2024-07-30", _slice(trades, midpoint, end), config),
        _metric_row("FULL UNSEEN YEAR", trades, config),
    ]
    result = pd.DataFrame(rows)
    trade_frame = pd.DataFrame([trade.to_dict() for trade in trades])
    if not trade_frame.empty:
        trade_frame["entry_time"] = pd.to_datetime(
            trade_frame["entry_time"],
            utc=True,
        )
        monthly_rows = []
        for month, group in trade_frame.groupby(
            trade_frame["entry_time"].dt.to_period("M")
        ):
            month_trades = [
                trade
                for trade in trades
                if pd.Timestamp(trade.entry_time).to_period("M") == month
            ]
            monthly_rows.append(
                _metric_row(str(month), month_trades, config)
            )
        monthly = pd.DataFrame(monthly_rows)
    else:
        monthly = pd.DataFrame()

    report_dir = base.root / "reports" / "robust_rebuild"
    report_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(report_dir / "unseen_2023_2024_metrics.csv", index=False)
    trade_frame.to_csv(report_dir / "unseen_2023_2024_trades.csv", index=False)
    monthly.to_csv(report_dir / "unseen_2023_2024_monthly.csv", index=False)
    specification = {
        "selection_period": "2024-07-30 through 2026-07-30",
        "untouched_test_period": "2023-07-30 through 2024-07-30",
        "params": asdict(params),
        "config": {
            "risk_pct": config.risk_pct,
            "lock_trigger_r": config.lock_trigger_r,
            "lock_profit_r": config.lock_profit_r,
            "relative_atr_days": config.regime_atr_days,
            "relative_atr_median_days": config.regime_atr_median_days,
            "relative_atr_min": config.regime_atr_ratio_min,
            "relative_atr_max": config.regime_atr_ratio_max,
            "asia_ratio_min": config.regime_asia_ratio_min,
            "asia_ratio_max": config.regime_asia_ratio_max,
        },
        "unseen_results": rows,
    }
    (report_dir / "frozen_model_validation.json").write_text(
        json.dumps(specification, indent=2, default=str),
        encoding="utf-8",
    )
    print("UNSEEN 2023-2024 VALIDATION")
    print(result.to_string(index=False))
    print("\nMONTHLY")
    print(monthly.to_string(index=False))


if __name__ == "__main__":
    run()
