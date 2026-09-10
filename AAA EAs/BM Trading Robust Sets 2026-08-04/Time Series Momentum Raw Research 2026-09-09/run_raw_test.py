"""Raw monthly 1/3/12-month time-series-momentum transfer to Calyx assets.

The signal follows Hurst, Ooi and Pedersen (2017): at each month end, each
market receives a long or short vote from its trailing 1-, 3- and 12-month
return. The three votes are averaged, positions are equal-risked, and the
portfolio is rebalanced at the first broker quote of the following month.

This is research evidence only. It deliberately contains no EMA, session,
stop-loss, take-profit, trailing stop, direction filter or optimized input.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
SLOW_DATA = PACKAGE / "Slow Multi Asset Trend Research 2026-09-06" / "Data"
FX_DATA = PACKAGE / "Intraday FX Session Effect Research 2026-09-08" / "Data"
CHARTS = ROOT / "Charts"

HORIZONS = (1, 3, 12)
TARGET_PORTFOLIO_VOL = 0.10
TRADING_DAYS = 252
VOL_LOOKBACK_DAYS = 252
EXTRA_COST_STRESS = 0.0005  # five basis points per one-way unit of turnover
NON_CRYPTO = ("XAUUSD", "XAGUSD", "EURUSD", "GBPUSD", "USDJPY")
ALL_ASSETS = NON_CRYPTO + ("BTCUSD",)


@dataclass(frozen=True)
class Source:
    path: Path
    metadata: Path
    broker: str


SOURCES = {
    "XAUUSD": Source(SLOW_DATA / "XAUUSD-M15.npz", SLOW_DATA / "metadata.json", "Exness-MT5Trial16"),
    "XAGUSD": Source(SLOW_DATA / "XAGUSD-M15.npz", SLOW_DATA / "metadata.json", "Exness-MT5Trial16"),
    "EURUSD": Source(SLOW_DATA / "EURUSD-M15.npz", SLOW_DATA / "metadata.json", "Exness-MT5Trial16"),
    "GBPUSD": Source(FX_DATA / "GBPUSD-M15.npz", FX_DATA / "metadata.json", "JustMarkets demo"),
    "USDJPY": Source(FX_DATA / "USDJPY-M15.npz", FX_DATA / "metadata.json", "JustMarkets demo"),
    "BTCUSD": Source(SLOW_DATA / "BTCUSD-M15.npz", SLOW_DATA / "metadata.json", "Exness-MT5Trial16"),
}


def json_default(value):
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    raise TypeError(type(value).__name__)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, allow_nan=False, default=json_default),
        encoding="utf-8",
    )


def load_symbol(symbol: str) -> tuple[pd.DataFrame, dict]:
    source = SOURCES[symbol]
    for required in (source.path, source.metadata):
        if not required.is_file():
            raise FileNotFoundError(required)
    rates = np.load(source.path)["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    frame = pd.DataFrame(
        {name: rates[name].astype(float) for name in ("open", "high", "low", "close", "spread")},
        index=index,
    )
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    metadata = json.loads(source.metadata.read_text(encoding="utf-8"))["symbols"][symbol]
    point = float(metadata["point"])
    positive = frame.loc[frame.spread > 0, "spread"]
    spread_floor_points = float(positive.quantile(0.20)) if len(positive) else 1.0
    frame["spread_price"] = np.maximum(frame.spread, spread_floor_points) * point
    meta = {
        "broker": source.broker,
        "point": point,
        "spread_floor_points": spread_floor_points,
        "bars": int(len(frame)),
        "first_utc": frame.index[0].isoformat(),
        "last_utc": frame.index[-1].isoformat(),
    }
    return frame, meta


def month_table(frame: pd.DataFrame) -> pd.DataFrame:
    """Build signals known before each month's first executable broker quote."""
    month = frame.index.strftime("%Y-%m")
    first = frame.groupby(month, sort=True).first()
    last = frame.groupby(month, sort=True).last()
    daily = frame.close.resample("1D").last().dropna()
    daily_returns = daily.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    months = list(first.index)
    rows: list[dict] = []
    for index in range(13, len(months) - 1):
        current = months[index]
        previous_index = index - 1
        if previous_index - 12 < 0:
            continue
        prior_close = float(last.close.iloc[previous_index])
        votes = []
        horizon_returns = {}
        for horizon in HORIZONS:
            anchor = float(last.close.iloc[previous_index - horizon])
            trailing = prior_close / anchor - 1.0
            horizon_returns[horizon] = trailing
            votes.append(1 if trailing >= 0 else -1)
        signal = float(np.mean(votes))
        entry_time = frame.index[month == current][0]
        next_month = months[index + 1]
        next_time = frame.index[month == next_month][0]
        before_entry = daily_returns[daily_returns.index < entry_time].tail(VOL_LOOKBACK_DAYS)
        if len(before_entry) < 126:
            continue
        annualized_vol = float(before_entry.std(ddof=1) * math.sqrt(TRADING_DAYS))
        if not math.isfinite(annualized_vol) or annualized_vol <= 0:
            continue
        entry = float(first.open.iloc[index])
        exit_price = float(first.open.iloc[index + 1])
        spread_fraction = float(first.spread_price.iloc[index] / entry)
        rows.append(
            {
                "month": current,
                "entry_time": entry_time,
                "exit_time": next_time,
                "asset_return": exit_price / entry - 1.0,
                "signal": signal,
                "signal_1m": votes[0],
                "signal_3m": votes[1],
                "signal_12m": votes[2],
                "return_1m": horizon_returns[1],
                "return_3m": horizon_returns[3],
                "return_12m": horizon_returns[12],
                "annualized_vol": annualized_vol,
                "half_spread_fraction": spread_fraction / 2.0,
            }
        )
    result = pd.DataFrame(rows).set_index("month")
    if result.empty:
        raise RuntimeError("No executable monthly observations")
    return result


def aligned_daily_covariance(
    frames: dict[str, pd.DataFrame], symbols: tuple[str, ...], before: pd.Timestamp
) -> pd.DataFrame:
    series = {}
    for symbol in symbols:
        daily = frames[symbol].close.resample("1D").last().dropna().pct_change()
        series[symbol] = daily[daily.index < before].tail(VOL_LOOKBACK_DAYS)
    returns = pd.DataFrame(series).dropna(how="any").tail(VOL_LOOKBACK_DAYS)
    if len(returns) < 126:
        raise RuntimeError(f"Only {len(returns)} aligned daily returns before {before}")
    return returns.cov() * TRADING_DAYS


def build_strategy(
    frames: dict[str, pd.DataFrame],
    monthly: dict[str, pd.DataFrame],
    symbols: tuple[str, ...],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    common = sorted(set.intersection(*(set(monthly[symbol].index) for symbol in symbols)))
    if not common:
        raise RuntimeError(f"No common months for {symbols}")
    previous = pd.Series(0.0, index=symbols)
    results = []
    weights = []
    for month in common:
        rows = {symbol: monthly[symbol].loc[month] for symbol in symbols}
        raw = pd.Series(
            {
                symbol: float(rows[symbol].signal)
                * TARGET_PORTFOLIO_VOL
                / float(rows[symbol].annualized_vol)
                / len(symbols)
                for symbol in symbols
            }
        )
        covariance = aligned_daily_covariance(
            frames, symbols, min(pd.Timestamp(rows[symbol].entry_time) for symbol in symbols)
        )
        raw_vol = float(math.sqrt(max(0.0, raw @ covariance.loc[list(symbols), list(symbols)] @ raw)))
        portfolio_scale = TARGET_PORTFOLIO_VOL / raw_vol if raw_vol > 0 else 0.0
        weight = raw * portfolio_scale
        turnover = float((weight - previous).abs().sum())
        observed_cost = float(
            sum(
                abs(float(weight[symbol] - previous[symbol]))
                * float(rows[symbol].half_spread_fraction)
                for symbol in symbols
            )
        )
        gross_return = float(
            sum(float(weight[symbol]) * float(rows[symbol].asset_return) for symbol in symbols)
        )
        entry_time = min(pd.Timestamp(rows[symbol].entry_time) for symbol in symbols)
        exit_time = max(pd.Timestamp(rows[symbol].exit_time) for symbol in symbols)
        results.append(
            {
                "month": month,
                "entry_time": entry_time,
                "exit_time": exit_time,
                "gross_return": gross_return,
                "observed_spread_cost": observed_cost,
                "net_return": gross_return - observed_cost,
                "stress_return": gross_return - observed_cost - EXTRA_COST_STRESS * turnover,
                "turnover": turnover,
                "gross_exposure": float(weight.abs().sum()),
                "portfolio_scale": portfolio_scale,
                "ex_ante_vol": raw_vol * portfolio_scale,
            }
        )
        weights.append({"month": month, **{symbol: float(weight[symbol]) for symbol in symbols}})
        previous = weight
    return pd.DataFrame(results).set_index("month"), pd.DataFrame(weights).set_index("month")


def metrics(returns: pd.Series) -> dict:
    values = returns.astype(float).to_numpy()
    curve = np.r_[1.0, np.cumprod(1.0 + values)]
    total = float(curve[-1] - 1.0)
    years = len(values) / 12.0
    annualized = float((curve[-1] ** (1.0 / years) - 1.0) if years > 0 and curve[-1] > 0 else -1.0)
    volatility = float(np.std(values, ddof=1) * math.sqrt(12.0)) if len(values) > 1 else 0.0
    sharpe = float(np.mean(values) / np.std(values, ddof=1) * math.sqrt(12.0)) if volatility > 0 else 0.0
    drawdown = float(np.max(1.0 - curve / np.maximum.accumulate(curve)))
    gains = values[values > 0]
    losses = values[values < 0]
    profit_factor = float(gains.sum() / -losses.sum()) if len(losses) else None
    return {
        "return_pct": total * 100.0,
        "annualized_return_pct": annualized * 100.0,
        "annualized_volatility_pct": volatility * 100.0,
        "profit_factor": profit_factor,
        "win_rate_pct": float(np.mean(values > 0) * 100.0),
        "max_drawdown_pct": drawdown * 100.0,
        "sharpe": sharpe,
        "recovery_factor": total / drawdown if drawdown > 0 else None,
        "months": int(len(values)),
        "best_month_pct": float(np.max(values) * 100.0),
        "worst_month_pct": float(np.min(values) * 100.0),
    }


def individual_strategy(table: pd.DataFrame) -> pd.DataFrame:
    previous = 0.0
    rows = []
    for month, row in table.iterrows():
        weight = float(row.signal) * TARGET_PORTFOLIO_VOL / float(row.annualized_vol)
        turnover = abs(weight - previous)
        gross = weight * float(row.asset_return)
        observed = turnover * float(row.half_spread_fraction)
        rows.append(
            {
                "month": month,
                "net_return": gross - observed,
                "stress_return": gross - observed - EXTRA_COST_STRESS * turnover,
                "gross_return": gross,
                "weight": weight,
                "turnover": turnover,
            }
        )
        previous = weight
    return pd.DataFrame(rows).set_index("month")


def period_metrics(returns: pd.Series) -> dict[str, dict]:
    return {
        "full": metrics(returns),
        "latest_12_months": metrics(returns.tail(12)),
    }


def chart(evaluations: dict[str, pd.DataFrame]) -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    plt.style.use("dark_background")
    fig, axes = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"height_ratios": [2, 1]})
    palette = {
        "Metals only": "#65f6c1",
        "FX only": "#ff6b78",
        "Metals + FX": "#a78bfa",
        "All six assets": "#5ba6ff",
        "BTCUSD alone": "#f6c65b",
    }
    for label, table in evaluations.items():
        values = table.net_return
        dates = pd.to_datetime(values.index.astype(str) + "-01", utc=True)
        equity = 10_000.0 * (1.0 + values).cumprod()
        axes[0].plot(dates, equity, label=label, linewidth=1.8, color=palette[label])
        drawdown = equity / equity.cummax() - 1.0
        axes[1].plot(dates, drawdown * 100.0, label=label, linewidth=1.4, color=palette[label])
    axes[0].set_title("Raw monthly 1/3/12 time-series momentum")
    axes[0].set_ylabel("Growth of $10,000")
    axes[0].grid(alpha=0.15)
    axes[0].legend(loc="upper left")
    axes[1].set_ylabel("Drawdown %")
    axes[1].set_xlabel("Position month")
    axes[1].grid(alpha=0.15)
    fig.tight_layout()
    fig.savefig(CHARTS / "raw-equity-and-drawdown.png", dpi=180)
    plt.close(fig)


def fmt(value, digits=2) -> str:
    return "n/a" if value is None else f"{float(value):.{digits}f}"


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    frames: dict[str, pd.DataFrame] = {}
    source_meta = {}
    monthly = {}
    for symbol in ALL_ASSETS:
        frame, meta = load_symbol(symbol)
        frames[symbol] = frame
        source_meta[symbol] = meta
        monthly[symbol] = month_table(frame)

    metals, metals_weights = build_strategy(frames, monthly, ("XAUUSD", "XAGUSD"))
    fx, fx_weights = build_strategy(frames, monthly, ("EURUSD", "GBPUSD", "USDJPY"))
    non_crypto, non_crypto_weights = build_strategy(frames, monthly, NON_CRYPTO)
    all_assets, all_weights = build_strategy(frames, monthly, ALL_ASSETS)
    btc = individual_strategy(monthly["BTCUSD"])
    evaluations = {
        "Metals only": metals,
        "FX only": fx,
        "Metals + FX": non_crypto,
        "All six assets": all_assets,
        "BTCUSD alone": btc,
    }
    chart(evaluations)

    individual = {}
    individual_tables = {}
    for symbol in ALL_ASSETS:
        table = individual_strategy(monthly[symbol])
        individual_tables[symbol] = table
        individual[symbol] = {
            "observed_spread": period_metrics(table.net_return),
            "cost_stress": period_metrics(table.stress_return),
            "average_absolute_exposure": float(table.weight.abs().mean()),
            "maximum_absolute_exposure": float(table.weight.abs().max()),
            "direction_changes": int((np.sign(table.weight).diff().fillna(0) != 0).sum()),
        }

    portfolio = {}
    for label, table in evaluations.items():
        exposure = table["gross_exposure"] if "gross_exposure" in table.columns else table["weight"].abs()
        portfolio[label] = {
            "observed_spread": period_metrics(table.net_return),
            "cost_stress": period_metrics(table.stress_return),
            "average_monthly_turnover": float(table.turnover.mean()),
            "average_gross_exposure": float(exposure.mean()),
            "maximum_gross_exposure": float(exposure.max()),
        }

    result = {
        "strategy": "Raw monthly 1/3/12 time-series momentum",
        "decision": "RESEARCH ONLY - await user review",
        "paper": "Hurst, Ooi and Pedersen (2017), A Century of Evidence on Trend-Following Investing",
        "paper_url": "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2993026",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rules": {
            "signal": "Equal-weighted votes from completed 1-, 3- and 12-month returns",
            "direction": "Long for a positive horizon return; short for a negative horizon return",
            "execution": "Rebalance at the first available broker quote of each following month",
            "risk": "Equal asset risk and 10% annualized ex-ante portfolio volatility target",
            "risk_estimation_deviation": "252 aligned daily observations because the local common broker archive cannot support the paper's rolling three-year monthly covariance and a three-year evaluation simultaneously",
            "exits": "Monthly rebalance only; no SL, TP or management overlay",
            "costs": "Recorded broker spread with a 20th-percentile floor; separate extra five-basis-point one-way turnover stress",
        },
        "data": source_meta,
        "portfolio": portfolio,
        "individual": individual,
        "limitations": [
            "The common local evaluation has only 35 monthly observations after the 12-month signal warm-up.",
            "XAUUSD, XAGUSD, EURUSD and BTCUSD use archived Exness bars; GBPUSD and USDJPY use archived JustMarkets bars because matching Exness M15 archives were unavailable.",
            "The paper trades futures and currency forwards. This transfer uses CFD spot-price returns, so futures roll yield and FX forward carry are absent.",
            "Historical overnight financing is unavailable. BTCUSD in particular must not be deployed from these price-only results because live CFD swap can be material.",
            "Profit factor and win rate are measured across monthly portfolio returns, not conventional stop-to-exit EA trades.",
        ],
    }
    dump(ROOT / "raw-results.json", result)

    rows = []
    for label, block in portfolio.items():
        for period, values in block["observed_spread"].items():
            rows.append({"scope": label, "period": period, "cost_mode": "observed-spread", **values})
        for period, values in block["cost_stress"].items():
            rows.append({"scope": label, "period": period, "cost_mode": "plus-5bps-turnover", **values})
    for symbol, block in individual.items():
        for period, values in block["observed_spread"].items():
            rows.append({"scope": symbol, "period": period, "cost_mode": "observed-spread", **values})
        for period, values in block["cost_stress"].items():
            rows.append({"scope": symbol, "period": period, "cost_mode": "plus-5bps-turnover", **values})
    pd.DataFrame(rows).to_csv(ROOT / "raw-results.csv", index=False)
    non_crypto.to_csv(ROOT / "monthly-portfolio-ledger.csv")
    metals_weights.to_csv(ROOT / "monthly-metals-weights.csv")
    fx_weights.to_csv(ROOT / "monthly-fx-weights.csv")
    non_crypto_weights.to_csv(ROOT / "monthly-portfolio-weights.csv")
    all_weights.to_csv(ROOT / "monthly-all-assets-weights.csv")

    lines = [
        "# Time-Series Momentum — raw monthly test",
        "",
        "**Decision: RESEARCH ONLY. No EA, website, BAT or recommended portfolio was changed.**",
        "",
        "The test uses the paper's unoptimized 1/3/12-month vote, trades both directions, rebalances monthly, equal-risks markets and targets 10% annualized portfolio volatility. It deliberately has no EMA, session, stop, target, trailing exit or direction filter.",
        "",
        "## Portfolio results — observed spread",
        "",
        "| Portfolio | Window | Return | Annualized | PF | Win months | Max DD | Sharpe | Months |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label, table in evaluations.items():
        for period, series in (("Full common history", table.net_return), ("Latest 12 months", table.net_return.tail(12))):
            value = metrics(series)
            lines.append(
                f"| {label} | {period} | {value['return_pct']:+.2f}% | {value['annualized_return_pct']:+.2f}% | "
                f"{fmt(value['profit_factor'])} | {value['win_rate_pct']:.2f}% | {value['max_drawdown_pct']:.2f}% | "
                f"{value['sharpe']:.2f} | {value['months']} |"
            )
    lines += [
        "",
        "## Individual markets — full common history",
        "",
        "Each market below is volatility-scaled to a 10% annualized target. These are monthly return observations, not ordinary SL/TP trades.",
        "",
        "| Asset | Broker archive | Return | Annualized | PF | Win months | Max DD | Sharpe | Direction changes |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for symbol in ALL_ASSETS:
        value = individual[symbol]["observed_spread"]["full"]
        lines.append(
            f"| {symbol} | {source_meta[symbol]['broker']} | {value['return_pct']:+.2f}% | "
            f"{value['annualized_return_pct']:+.2f}% | {fmt(value['profit_factor'])} | "
            f"{value['win_rate_pct']:.2f}% | {value['max_drawdown_pct']:.2f}% | "
            f"{value['sharpe']:.2f} | {individual[symbol]['direction_changes']} |"
        )
    lines += [
        "",
        "## Evidence boundary",
        "",
        f"- The common portfolio test contains only {len(non_crypto)} months after the required 12-month warm-up; this is a useful local transfer test, not proof of the century result.",
        "- The paper uses futures and currency forwards. Spot CFD prices omit roll yield and forward carry.",
        "- Historical overnight financing is unavailable. The BTC result is therefore displayed separately and is not deployable evidence.",
        "- GBPUSD and USDJPY use the available JustMarkets archive; the other instruments use Exness. A single-broker native MT5 validation is required before promotion.",
        "- A separate stress file adds five basis points per one-way unit of turnover on top of recorded spread.",
        "",
        "![Raw equity and drawdown](Charts/raw-equity-and-drawdown.png)",
        "",
        "## Next gate",
        "",
        "Review the raw result first. Only if it is acceptable should we compile a native MT5 EA, obtain longer same-broker history, or run the normal optimization pipeline.",
        "",
    ]
    (ROOT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")

    print("RAW TIME-SERIES MOMENTUM COMPLETE")
    for label, table in evaluations.items():
        value = metrics(table.net_return)
        print(
            f"{label:18s} return={value['return_pct']:+.2f}% PF={fmt(value['profit_factor'])} "
            f"WR={value['win_rate_pct']:.2f}% DD={value['max_drawdown_pct']:.2f}% "
            f"Sharpe={value['sharpe']:.2f} months={value['months']}"
        )


if __name__ == "__main__":
    main()
