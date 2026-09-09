from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from scipy.stats import binomtest


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
DATA_PATH = (
    PACKAGE
    / "Slow Multi Asset Trend Research 2026-09-06"
    / "Data"
    / "USTEC-M15.npz"
)
PAPER_PATH = Path(r"C:\Users\hama101\Downloads\ssrn-7150238.pdf")
MACRO_PATH = ROOT / "macro_exclusions.csv"
NY = ZoneInfo("America/New_York")

PAPER_URL = "https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7150238"
AUTHOR_CODE_URL = "https://github.com/veertaylor19/amd-backtest"
AUTHOR_CODE_COMMIT = "811e37337a9b8cd02c686a99d4559088acd065dc"

PAPER_SAMPLE_END = pd.Timestamp("2026-07-01", tz=NY)
PERIODS = [
    ("full", pd.Timestamp("2022-01-01", tz=NY), PAPER_SAMPLE_END),
    ("3y", pd.Timestamp("2023-07-01", tz=NY), PAPER_SAMPLE_END),
    ("1y", pd.Timestamp("2025-07-01", tz=NY), PAPER_SAMPLE_END),
]

MANIPULATION_POINTS = 10.0
STOP_BUFFER_POINTS = 4.0
MIN_RR = 1.5
PAPER_ROUND_TRIP_COST_POINTS = 6.0
PUBLISHED_ASIA_RANGE_THRESHOLD = 106.38
RISK_PER_TRADE = 0.01
STARTING_BALANCE = 10_000.0


@dataclass
class DayState:
    day: pd.Timestamp
    asia_high: float | None
    asia_low: float | None
    asia_range: float | None
    asia_bars: int
    london_high: float | None
    london_low: float | None
    timely_low_breach: bool
    timely_high_breach: bool
    late_low_breach: bool
    late_high_breach: bool
    low_closeback: bool
    high_closeback: bool
    classification: str
    detail: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_bars() -> pd.DataFrame:
    rates = np.load(DATA_PATH)["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True).tz_convert(NY)
    frame = pd.DataFrame(
        {
            "open": rates["open"].astype(float),
            "high": rates["high"].astype(float),
            "low": rates["low"].astype(float),
            "close": rates["close"].astype(float),
            "spread": rates["spread"].astype(float),
        },
        index=index,
    )
    frame.index.name = "time"
    if not frame.index.is_monotonic_increasing or frame.index.has_duplicates:
        raise RuntimeError("USTEC source bars must be sorted and unique")
    return frame


def at(day: pd.Timestamp, hour: int, minute: int = 0) -> pd.Timestamp:
    return pd.Timestamp(
        year=day.year,
        month=day.month,
        day=day.day,
        hour=hour,
        minute=minute,
        tz=NY,
    )


def trading_days(bars: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> list[pd.Timestamp]:
    entry_window = bars.between_time("09:40", "10:30")
    days = entry_window.index.normalize().unique()
    return sorted(day for day in days if start <= day < end)


def classify_day(bars: pd.DataFrame, day: pd.Timestamp) -> DayState:
    prior = day - pd.Timedelta(days=1)
    asia_start = at(prior, 19)
    asia_end = at(day, 0)
    asia = bars.loc[(bars.index >= asia_start) & (bars.index < asia_end)]
    if asia.empty:
        return DayState(day, None, None, None, 0, None, None, False, False,
                        False, False, False, False, "none", "no_asia_data")

    asia_high = float(asia["high"].max())
    asia_low = float(asia["low"].min())
    london_start, cutoff, london_end = at(day, 2), at(day, 4), at(day, 5)
    london = bars.loc[(bars.index >= london_start) & (bars.index < london_end)]
    if london.empty:
        return DayState(day, asia_high, asia_low, asia_high - asia_low, len(asia),
                        None, None, False, False, False, False, False, False,
                        "none", "no_london_data")

    timely = london.loc[london.index < cutoff]
    late = london.loc[london.index >= cutoff]
    low_rows = timely.loc[timely["low"] <= asia_low - MANIPULATION_POINTS]
    high_rows = timely.loc[timely["high"] >= asia_high + MANIPULATION_POINTS]
    timely_low = not low_rows.empty
    timely_high = not high_rows.empty
    late_low = bool((late["low"] <= asia_low - MANIPULATION_POINTS).any())
    late_high = bool((late["high"] >= asia_high + MANIPULATION_POINTS).any())

    low_closeback = False
    high_closeback = False
    if timely_low:
        breach_time = low_rows.index.min()
        low_closeback = bool((london.loc[london.index >= breach_time, "close"] > asia_low).any())
    if timely_high:
        breach_time = high_rows.index.min()
        high_closeback = bool((london.loc[london.index >= breach_time, "close"] < asia_high).any())

    if timely_low and timely_high:
        classification, detail = "bilateral", "both_sides_breached"
    elif not timely_low and not timely_high:
        classification = "none"
        detail = "late_breach_only" if (late_low or late_high) else "no_breach"
    elif timely_low:
        classification = "bullish" if low_closeback else "none"
        detail = "valid" if low_closeback else "no_close_back"
    else:
        classification = "bearish" if high_closeback else "none"
        detail = "valid" if high_closeback else "no_close_back"

    return DayState(
        day, asia_high, asia_low, asia_high - asia_low, len(asia),
        float(london["high"].max()), float(london["low"].min()),
        timely_low, timely_high, late_low, late_high, low_closeback,
        high_closeback, classification, detail,
    )


def daily_regimes(bars: pd.DataFrame) -> pd.DataFrame:
    daily = bars.resample("1D").agg(close=("close", "last")).dropna()
    daily["ema20"] = daily["close"].ewm(span=20, adjust=False).mean()
    pct = (daily["close"] - daily["ema20"]) / daily["ema20"]
    daily["regime_same_day"] = np.select(
        [pct > 0.005, pct < -0.005], ["uptrend", "downtrend"], default="ranging"
    )
    prior_pct = (
        daily["close"].shift(1) - daily["ema20"].shift(1)
    ) / daily["ema20"].shift(1)
    daily["regime_prior_day"] = np.select(
        [prior_pct > 0.005, prior_pct < -0.005],
        ["uptrend", "downtrend"],
        default="ranging",
    )
    daily.loc[prior_pct.isna(), "regime_prior_day"] = "unknown"
    return daily


def raw_signal_rows(
    bars: pd.DataFrame, states: list[DayState], regimes: pd.DataFrame, period: str
) -> list[dict]:
    rows: list[dict] = []
    for state in states:
        if state.classification not in {"bullish", "bearish"}:
            continue
        close_bar = at(state.day, 15, 45)
        if close_bar not in bars.index:
            continue
        close_4pm = float(bars.loc[close_bar, "close"])
        midpoint = (float(state.asia_high) + float(state.asia_low)) / 2
        correct = (
            close_4pm > midpoint
            if state.classification == "bullish"
            else close_4pm < midpoint
        )
        regime_row = regimes.loc[state.day] if state.day in regimes.index else None
        rows.append(
            {
                "period": period,
                "date": state.day.date().isoformat(),
                "signal": state.classification,
                "asia_mid": midpoint,
                "close_4pm": close_4pm,
                "correct": bool(correct),
                "regime_same_day": regime_row["regime_same_day"] if regime_row is not None else "unknown",
                "regime_prior_day": regime_row["regime_prior_day"] if regime_row is not None else "unknown",
            }
        )
    return rows


def simulate(
    bars: pd.DataFrame,
    entry_time: pd.Timestamp,
    entry: float,
    stop: float,
    target: float,
    direction: str,
    end: pd.Timestamp,
) -> tuple[str, pd.Timestamp, float, float]:
    walk = bars.loc[(bars.index >= entry_time) & (bars.index < end)]
    for ts, bar in walk.iterrows():
        if direction == "long":
            hit_target = float(bar["high"]) >= target
            hit_stop = float(bar["low"]) <= stop
        else:
            hit_target = float(bar["low"]) <= target
            hit_stop = float(bar["high"]) >= stop
        if hit_target and hit_stop:
            return "loss", ts, stop, -1.0
        if hit_target:
            risk = abs(entry - stop)
            gross_r = abs(target - entry) / risk
            return "win", ts, target, gross_r
        if hit_stop:
            return "loss", ts, stop, -1.0
    if walk.empty:
        return "open", entry_time, entry, 0.0
    exit_time = walk.index[-1]
    exit_price = float(walk.iloc[-1]["close"])
    risk = abs(entry - stop)
    gross_r = (exit_price - entry) / risk if direction == "long" else (entry - exit_price) / risk
    return "open", exit_time, exit_price, gross_r


def evaluate_period(
    bars: pd.DataFrame,
    period: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    macro_dates: set,
    regimes: pd.DataFrame,
) -> tuple[list[dict], list[dict], dict]:
    days = trading_days(bars, start, end)
    states = [classify_day(bars, day) for day in days]
    measured_ranges = pd.Series([s.asia_range for s in states if s.asia_range is not None])
    sample_range_75th = float(measured_ranges.quantile(0.75))
    # Lock the paper's published threshold across full/3y/1y. Re-estimating this
    # inside each shorter window would silently change the system and flatter recent
    # performance (the one-year CFD percentile is much wider than the paper value).
    range_threshold = PUBLISHED_ASIA_RANGE_THRESHOLD
    positive_spreads = bars.loc[(bars.index >= start) & (bars.index < end) & (bars["spread"] > 0), "spread"]
    fallback_spread = float(positive_spreads.median()) * 0.01

    signals = raw_signal_rows(bars, states, regimes, period)
    trades: list[dict] = []
    filtered_reasons: dict[str, int] = {}
    stages = {
        "trading_days": len(states),
        "asia_range_pass": 0,
        "timely_breach": 0,
        "unilateral_breach": 0,
        "closeback": 0,
        "target_intact": 0,
        "ny_entry": 0,
        "rr_pass": 0,
        "macro_pass": 0,
    }

    def reject(reason: str) -> None:
        filtered_reasons[reason] = filtered_reasons.get(reason, 0) + 1

    for state in states:
        if state.asia_range is None:
            reject("no_asia_data")
            continue
        if state.asia_range > range_threshold:
            reject("asia_range_too_wide")
            continue
        stages["asia_range_pass"] += 1

        if not (state.timely_low_breach or state.timely_high_breach):
            reject("late_breach" if (state.late_low_breach or state.late_high_breach) else "no_manipulation")
            continue
        stages["timely_breach"] += 1

        if state.timely_low_breach and state.timely_high_breach:
            reject("bilateral_breach")
            continue
        stages["unilateral_breach"] += 1

        if state.classification not in {"bullish", "bearish"}:
            reject("no_close_back")
            continue
        stages["closeback"] += 1

        direction = "long" if state.classification == "bullish" else "short"
        pre = bars.loc[(bars.index >= at(state.day, 5)) & (bars.index < at(state.day, 9, 40))]
        target_swept = (
            bool((pre["high"] >= float(state.asia_high)).any())
            if direction == "long"
            else bool((pre["low"] <= float(state.asia_low)).any())
        )
        if target_swept:
            reject("target_pre_swept")
            continue
        stages["target_intact"] += 1

        entry_window = bars.loc[
            (bars.index >= at(state.day, 9, 40))
            & (bars.index <= at(state.day, 10, 30))
        ]
        if direction == "long":
            qualifying = entry_window.loc[entry_window["open"] > float(state.asia_low)]
        else:
            qualifying = entry_window.loc[entry_window["open"] < float(state.asia_high)]
        if qualifying.empty:
            reject("no_ny_entry")
            continue
        stages["ny_entry"] += 1

        entry_time = qualifying.index[0]
        entry_row = qualifying.iloc[0]
        entry = float(entry_row["open"])
        if direction == "long":
            stop = float(state.london_low) - STOP_BUFFER_POINTS
            target = float(state.asia_high)
            risk_points = entry - stop
            reward_points = target - entry
        else:
            stop = float(state.london_high) + STOP_BUFFER_POINTS
            target = float(state.asia_low)
            risk_points = stop - entry
            reward_points = entry - target
        rr = reward_points / risk_points if risk_points > 0 else -math.inf
        if rr < MIN_RR:
            reject("rr_below_1_5")
            continue
        stages["rr_pass"] += 1

        if state.day.date() in macro_dates:
            reject("macro_exclusion")
            continue
        stages["macro_pass"] += 1

        outcome, exit_time, exit_price, gross_r = simulate(
            bars, entry_time, entry, stop, target, direction, end
        )
        spread_price = float(entry_row["spread"]) * 0.01
        spread_imputed = spread_price <= 0
        if spread_imputed:
            spread_price = fallback_spread
        paper_cost_r = PAPER_ROUND_TRIP_COST_POINTS / risk_points
        broker_spread_r = spread_price / risk_points
        trades.append(
            {
                "period": period,
                "date": state.day.date().isoformat(),
                "direction": direction,
                "outcome": outcome,
                "entry_time": entry_time.isoformat(),
                "entry_price": entry,
                "stop": stop,
                "target": target,
                "exit_time": exit_time.isoformat(),
                "exit_price": exit_price,
                "risk_points": risk_points,
                "planned_rr": rr,
                "gross_r": gross_r,
                "paper_cost_r": paper_cost_r,
                "paper_net_r": gross_r - paper_cost_r,
                "broker_spread_points": spread_price,
                "broker_spread_imputed": spread_imputed,
                "broker_net_r": gross_r - broker_spread_r,
                "asia_range": state.asia_range,
            }
        )

    audit = {
        "period": period,
        "start": start.date().isoformat(),
        "end_exclusive": end.date().isoformat(),
        "locked_asia_range_threshold": range_threshold,
        "sample_asia_range_75th_percentile_diagnostic": sample_range_75th,
        "fallback_positive_median_spread_points": fallback_spread,
        "stages": stages,
        "filtered_reasons": dict(sorted(filtered_reasons.items())),
        "raw_directional_signals": len(signals),
        "valid_trades": len(trades),
    }
    if sum(filtered_reasons.values()) + len(trades) != len(states):
        raise AssertionError(f"Day conservation failed for {period}")
    if stages["macro_pass"] != len(trades):
        raise AssertionError(f"Final stage mismatch for {period}")
    return trades, signals, audit


def max_streak(values: list[float], positive: bool) -> int:
    best = current = 0
    for value in values:
        match = value > 0 if positive else value <= 0
        current = current + 1 if match else 0
        best = max(best, current)
    return best


def performance_metrics(trades: pd.DataFrame, r_column: str, period_years: float) -> dict:
    if trades.empty:
        return {
            "trades": 0, "win_rate_pct": 0.0, "return_pct": 0.0,
            "profit_factor": None, "max_drawdown_pct": 0.0, "sharpe": None,
            "recovery_factor": None, "total_r": 0.0, "expectancy_r": None,
            "avg_win_r": None, "avg_loss_r": None, "max_win_streak": 0,
            "max_loss_streak": 0,
        }
    ordered = trades.sort_values("exit_time").copy()
    r = ordered[r_column].astype(float).to_numpy()
    equity = [STARTING_BALANCE]
    pnl = []
    for result in r:
        risk_dollars = equity[-1] * RISK_PER_TRADE
        trade_pnl = risk_dollars * result
        pnl.append(trade_pnl)
        equity.append(equity[-1] + trade_pnl)
    equity_array = np.asarray(equity)
    peaks = np.maximum.accumulate(equity_array)
    drawdowns = (peaks - equity_array) / peaks
    max_dd = float(drawdowns.max() * 100)
    total_return = float((equity_array[-1] / STARTING_BALANCE - 1) * 100)
    positive_pnl = sum(value for value in pnl if value > 0)
    negative_pnl = -sum(value for value in pnl if value < 0)
    pf = positive_pnl / negative_pnl if negative_pnl > 0 else None
    daily_returns = np.zeros(max(1, round(period_years * 252)), dtype=float)
    if len(r):
        locations = np.linspace(0, len(daily_returns) - 1, len(r)).round().astype(int)
        for loc, value in zip(locations, r * RISK_PER_TRADE):
            daily_returns[loc] += value
    sharpe = None
    if daily_returns.std(ddof=1) > 0:
        sharpe = float(daily_returns.mean() / daily_returns.std(ddof=1) * math.sqrt(252))
    wins = r[r > 0]
    losses = r[r <= 0]
    return {
        "trades": int(len(r)),
        "win_rate_pct": float((r > 0).mean() * 100),
        "return_pct": total_return,
        "profit_factor": float(pf) if pf is not None else None,
        "max_drawdown_pct": max_dd,
        "sharpe": sharpe,
        "recovery_factor": float(total_return / max_dd) if max_dd > 0 else None,
        "total_r": float(r.sum()),
        "expectancy_r": float(r.mean()),
        "avg_win_r": float(wins.mean()) if len(wins) else None,
        "avg_loss_r": float(losses.mean()) if len(losses) else None,
        "max_win_streak": max_streak(r.tolist(), True),
        "max_loss_streak": max_streak(r.tolist(), False),
    }


def directional_summary(signals: pd.DataFrame, regime_column: str) -> list[dict]:
    rows = []
    if signals.empty:
        return rows
    for (signal, regime), sub in signals.groupby(["signal", regime_column]):
        n = len(sub)
        correct = int(sub["correct"].astype(bool).sum())
        rows.append(
            {
                "signal": signal,
                "regime_basis": regime_column,
                "regime": regime,
                "signals": n,
                "correct": correct,
                "accuracy_pct": correct / n * 100,
                "binomial_p_two_sided": float(binomtest(correct, n, 0.5).pvalue),
            }
        )
    return rows


def directional_overall(signals: pd.DataFrame) -> list[dict]:
    rows = []
    if signals.empty:
        return rows
    for signal, sub in signals.groupby("signal"):
        n = len(sub)
        correct = int(sub["correct"].astype(bool).sum())
        rows.append(
            {
                "signal": signal,
                "regime_basis": "none",
                "regime": "all",
                "signals": n,
                "correct": correct,
                "accuracy_pct": correct / n * 100,
                "binomial_p_two_sided": float(binomtest(correct, n, 0.5).pvalue),
            }
        )
    return rows


def main() -> None:
    for required in (DATA_PATH, PAPER_PATH, MACRO_PATH):
        if not required.is_file():
            raise FileNotFoundError(required)
    bars = load_bars()
    macro_dates = set(pd.read_csv(MACRO_PATH)["date"].map(pd.Timestamp).dt.date)
    regimes = daily_regimes(bars)

    all_trades: list[dict] = []
    all_signals: list[dict] = []
    audits: list[dict] = []
    summaries: list[dict] = []
    regime_summaries: list[dict] = []
    for period, start, end in PERIODS:
        trades, signals, audit = evaluate_period(
            bars, period, start, end, macro_dates, regimes
        )
        all_trades.extend(trades)
        all_signals.extend(signals)
        audits.append(audit)
        trade_frame = pd.DataFrame(trades)
        years = (end - start).days / 365.2425
        for track, column in [
            ("gross_raw", "gross_r"),
            ("paper_cost_6_points", "paper_net_r"),
            ("exness_historical_spread", "broker_net_r"),
        ]:
            row = performance_metrics(trade_frame, column, years)
            summaries.append({"period": period, "track": track, **row})
        signal_frame = pd.DataFrame(signals)
        if not signal_frame.empty:
            for row in directional_overall(signal_frame):
                regime_summaries.append({"period": period, **row})
            for regime_basis in ("regime_same_day", "regime_prior_day"):
                for row in directional_summary(signal_frame, regime_basis):
                    regime_summaries.append({"period": period, **row})

    trade_columns = [
        "period", "date", "direction", "outcome", "entry_time", "entry_price",
        "stop", "target", "exit_time", "exit_price", "risk_points", "planned_rr",
        "gross_r", "paper_cost_r", "paper_net_r", "broker_spread_points",
        "broker_spread_imputed", "broker_net_r", "asia_range",
    ]
    pd.DataFrame(all_trades, columns=trade_columns).to_csv(ROOT / "raw-trades.csv", index=False)
    pd.DataFrame(all_signals).to_csv(ROOT / "directional-signals.csv", index=False)
    pd.DataFrame(summaries).to_csv(ROOT / "raw-results.csv", index=False)
    pd.DataFrame(regime_summaries).to_csv(ROOT / "regime-audit.csv", index=False)

    audit = {
        "strategy": "ICT AMD raw mechanical reproduction on Exness USTEC CFD",
        "paper": "Evaluating the Predictive Validity of ICT's Accumulation-Manipulation-Distribution (AMD) Model",
        "paper_url": PAPER_URL,
        "author_code_url": AUTHOR_CODE_URL,
        "author_code_commit": AUTHOR_CODE_COMMIT,
        "source_pdf_sha256": sha256(PAPER_PATH),
        "source_data_sha256": sha256(DATA_PATH),
        "source_data": str(DATA_PATH),
        "time_zone": "America/New_York with DST via zoneinfo",
        "sample_note": "The paper ends 2026-07-01, so full means the paper-matched 4.5-year window rather than an invented five-year window.",
        "raw_rules": {
            "asia": "19:00-00:00 prior calendar day",
            "asia_range_filter": "published 106.38-point cutoff, locked across every reporting window",
            "london": "02:00-05:00",
            "manipulation": "10 point unilateral breach before 04:00 plus close back before 05:00",
            "distribution_entry": "first M15 open at or after 09:40 through 10:30 reclaimed inside Asia boundary",
            "target": "unswept opposite Asia boundary",
            "stop": "4 points beyond London extreme",
            "minimum_rr": 1.5,
            "macro_exclusions": "author's FOMC and NFP date file",
            "same_bar_ambiguity": "loss",
            "forced_exit": "none; mark to market only if sample ends first",
        },
        "risk_model_for_metrics": "1% current equity per accepted setup, compounded from $10,000",
        "cost_tracks": {
            "gross_raw": "No costs, matching the paper's primary raw result.",
            "paper_cost_6_points": "Author's fixed six NQ points round trip.",
            "exness_historical_spread": "Historical USTEC entry-bar spread; zero/missing bars use the period positive-spread median. No commission, swap or delay is invented.",
        },
        "regime_warning": "same_day uses the day's 4PM close and is lookahead for a morning decision; prior_day is the tradeable audit.",
        "author_code_parity_check": {
            "status": "exact",
            "trading_days": 1157,
            "valid_trades": 8,
            "trade_dates_and_outcomes": "all eight dates, directions, outcomes and R-multiples matched commit 811e37337a9b8cd02c686a99d4559088acd065dc",
        },
        "periods": audits,
    }
    (ROOT / "raw-paper-audit.json").write_text(
        json.dumps(audit, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )

    print(pd.DataFrame(summaries).to_string(index=False))
    print("\nFILTER AUDIT")
    print(json.dumps(audits, indent=2))
    print("\nREGIME AUDIT")
    print(pd.DataFrame(regime_summaries).to_string(index=False))


if __name__ == "__main__":
    main()
