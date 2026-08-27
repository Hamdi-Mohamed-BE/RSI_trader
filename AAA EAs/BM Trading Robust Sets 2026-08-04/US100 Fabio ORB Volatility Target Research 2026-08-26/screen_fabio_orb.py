from __future__ import annotations

import csv
import itertools
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import MetaTrader5 as mt5
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "Screen Results"
OUT.mkdir(parents=True, exist_ok=True)
NY = ZoneInfo("America/New_York")
INITIAL = 10_000.0
RISK_FRACTION = 0.01
POINT = 0.01
EXIT_SLIPPAGE_POINTS = 1.0

TRAIN_END = pd.Timestamp("2024-01-01", tz="America/New_York")
VALIDATION_END = pd.Timestamp("2025-07-01", tz="America/New_York")


@dataclass(frozen=True)
class Config:
    orb_minutes: int
    cutoff_minutes: int
    reward_risk: float
    require_bullish_breakout: bool
    direction: str = "long"

    @property
    def slug(self) -> str:
        return (
            f"orb{self.orb_minutes}-cut{self.cutoff_minutes}-rr{self.reward_risk:g}"
            f"-bull{int(self.require_bullish_breakout)}-{self.direction}"
        )


def pull_data() -> tuple[pd.DataFrame, dict]:
    terminal = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    if not mt5.initialize(path=terminal):
        raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
    try:
        info = mt5.symbol_info("USTEC")
        if info is None or (not info.visible and not mt5.symbol_select("USTEC", True)):
            raise RuntimeError("USTEC is unavailable on the connected broker")
        start = datetime(2015, 1, 1, tzinfo=timezone.utc)
        end = datetime.now(timezone.utc)
        rates = mt5.copy_rates_range("USTEC", mt5.TIMEFRAME_M1, start, end)
        account = mt5.account_info()
        terminal_info = mt5.terminal_info()
        if rates is None or len(rates) == 0:
            raise RuntimeError(f"No USTEC M1 rates: {mt5.last_error()}")
        frame = pd.DataFrame(rates)
        frame.index = pd.DatetimeIndex(pd.to_datetime(frame.pop("time"), unit="s", utc=True)).tz_convert(NY)
        frame = frame[~frame.index.duplicated(keep="last")].sort_index()
        meta = {
            "pulled_utc": datetime.now(timezone.utc).isoformat(),
            "requested_from": start.isoformat(),
            "actual_from": frame.index.min().isoformat(),
            "actual_to": frame.index.max().isoformat(),
            "m1_rows": int(len(frame)),
            "symbol": "USTEC",
            "broker": getattr(account, "company", None),
            "server": getattr(account, "server", None),
            "login_last_four": str(getattr(account, "login", ""))[-4:],
            "terminal_connected": bool(getattr(terminal_info, "connected", False)),
            "point": float(info.point),
            "digits": int(info.digits),
            "note": "Fresh MT5 pull. No stored market-data cache was read by this script.",
        }
        return frame, meta
    finally:
        mt5.shutdown()


def prepare_sessions(m1: pd.DataFrame) -> list[dict]:
    intraday = m1.between_time("09:30", "15:00", inclusive="left").copy()
    bars = intraday.resample("5min", label="left", closed="left").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
        spread=("spread", "last"),
        count=("close", "count"),
    )
    bars = bars[(bars["count"] >= 4) & bars.open.notna()].drop(columns="count")
    sessions: list[dict] = []
    for date, group in bars.groupby(bars.index.date):
        group = group.sort_index()
        if len(group) < 60:
            continue
        first = group.index[0]
        if first.hour != 9 or first.minute != 30:
            continue
        sessions.append({"date": pd.Timestamp(date, tz=NY), "bars": group})
    return sessions


def candidate_trade(session: dict, config: Config) -> dict | None:
    bars: pd.DataFrame = session["bars"]
    opening_count = config.orb_minutes // 5
    if len(bars) <= opening_count + 1:
        return None
    opening = bars.iloc[:opening_count]
    orb_high = float(opening.high.max())
    orb_low = float(opening.low.min())
    if orb_high <= orb_low:
        return None
    cutoff = bars.index[0] + pd.Timedelta(minutes=config.cutoff_minutes)
    candidates = bars.iloc[opening_count:]
    candidates = candidates[candidates.index < cutoff]
    for timestamp, signal in candidates.iterrows():
        direction = 0
        if float(signal.close) > orb_high:
            direction = 1
        elif config.direction in {"short", "both"} and float(signal.close) < orb_low:
            direction = -1
        if direction == 0:
            continue
        if config.direction == "long" and direction < 0:
            continue
        if config.direction == "short" and direction > 0:
            continue
        if config.require_bullish_breakout:
            if direction > 0 and float(signal.close) <= float(signal.open):
                continue
            if direction < 0 and float(signal.close) >= float(signal.open):
                continue
        location = bars.index.get_loc(timestamp)
        if location + 1 >= len(bars):
            return None
        entry_bar = bars.iloc[location + 1]
        spread_price = max(0.0, float(entry_bar.spread)) * POINT
        entry = float(entry_bar.open) + spread_price if direction > 0 else float(entry_bar.open)
        stop = orb_low if direction > 0 else orb_high + spread_price
        risk_points = direction * (entry - stop)
        if risk_points <= 0.0:
            return None
        target = entry + direction * config.reward_risk * risk_points
        return {
            "session": session["date"],
            "signal_time": timestamp,
            "entry_time": bars.index[location + 1],
            "direction": direction,
            "entry": entry,
            "stop": stop,
            "target": target,
            "risk_points": risk_points,
            "spread_points": spread_price,
            "future": bars.iloc[location + 1 :],
            "orb_high": orb_high,
            "orb_low": orb_low,
        }
    return None


def resolve_trade(trade: dict) -> dict:
    direction = trade["direction"]
    entry = trade["entry"]
    stop = trade["stop"]
    target = trade["target"]
    risk = trade["risk_points"]
    exit_price = float(trade["future"].iloc[-1].close)
    exit_time = trade["future"].index[-1] + pd.Timedelta(minutes=5)
    reason = "15:00 close"
    for timestamp, bar in trade["future"].iterrows():
        stop_hit = float(bar.low) <= stop if direction > 0 else float(bar.high) >= stop
        target_hit = float(bar.high) >= target if direction > 0 else float(bar.low) <= target
        if stop_hit and target_hit:
            target_hit = False
        if stop_hit:
            exit_price = stop
            exit_time = timestamp
            reason = "stop"
            break
        if target_hit:
            exit_price = target
            exit_time = timestamp
            reason = "target"
            break
    raw_points = direction * (exit_price - entry) - EXIT_SLIPPAGE_POINTS * POINT
    outcome_r = raw_points / risk
    result = {key: value for key, value in trade.items() if key != "future"}
    result.update({"exit_time": exit_time, "exit_price": exit_price, "exit_reason": reason, "outcome_r": outcome_r})
    return result


def simulate(sessions: list[dict], config: Config) -> list[dict]:
    trades = []
    for session in sessions:
        candidate = candidate_trade(session, config)
        if candidate is not None:
            trades.append(resolve_trade(candidate))
    return trades


def metrics(trades: list[dict], start: pd.Timestamp, end: pd.Timestamp) -> dict:
    selected = [trade for trade in trades if start <= trade["session"] < end]
    balance = INITIAL
    peak = INITIAL
    maximum_dd = 0.0
    wins = 0
    gross_profit = 0.0
    gross_loss = 0.0
    for trade in selected:
        cash = balance * RISK_FRACTION * float(trade["outcome_r"])
        trade["cashflow"] = cash
        balance += cash
        trade["balance"] = balance
        peak = max(peak, balance)
        maximum_dd = max(maximum_dd, (peak - balance) / peak * 100.0)
        if cash > 0:
            wins += 1
            gross_profit += cash
        elif cash < 0:
            gross_loss += cash
    count = len(selected)
    return {
        "initial_balance": INITIAL,
        "final_balance": balance,
        "return_pct": (balance / INITIAL - 1.0) * 100.0,
        "profit_factor": gross_profit / abs(gross_loss) if gross_loss else (999.0 if gross_profit else 0.0),
        "win_rate_pct": wins / count * 100.0 if count else 0.0,
        "max_drawdown_pct": maximum_dd,
        "trades": count,
        "wins": wins,
        "losses": count - wins,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
    }


def result_row(config: Config, trades: list[dict], start: pd.Timestamp, actual_end: pd.Timestamp) -> dict:
    periods = {
        "training": (start, TRAIN_END),
        "validation": (TRAIN_END, VALIDATION_END),
        "locked": (VALIDATION_END, actual_end),
        "full": (start, actual_end),
    }
    row = {"slug": config.slug, **asdict(config)}
    for name, (left, right) in periods.items():
        for key, value in metrics(trades, left, right).items():
            row[f"{name}_{key}"] = value
    train_pf = min(float(row["training_profit_factor"]), 3.0)
    valid_pf = min(float(row["validation_profit_factor"]), 3.0)
    train_return = float(row["training_return_pct"])
    valid_return = float(row["validation_return_pct"])
    row["eligible"] = (
        row["training_trades"] >= 100
        and row["validation_trades"] >= 30
        and train_return > 0
        and valid_return > 0
        and train_pf >= 1.05
        and valid_pf >= 1.05
        and row["training_max_drawdown_pct"] <= 25
        and row["validation_max_drawdown_pct"] <= 25
    )
    if train_return <= 0 or valid_return <= 0:
        row["score"] = min(train_return, valid_return)
    else:
        harmonic_return = 2.0 / (1.0 / train_return + 1.0 / valid_return)
        row["score"] = harmonic_return * math.sqrt(train_pf * valid_pf) / (
            1.0 + max(row["training_max_drawdown_pct"], row["validation_max_drawdown_pct"]) / 10.0
        )
    return row


def json_safe(value):
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    return value


def save_trades(path: Path, trades: list[dict]) -> None:
    rows = [{key: json_safe(value) for key, value in trade.items()} for trade in trades]
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def save_graph(selected: dict, selected_trades: list[dict], literal_trades: list[dict], start: pd.Timestamp, end: pd.Timestamp) -> None:
    def frame(trades: list[dict]) -> pd.DataFrame:
        balance = INITIAL
        rows = [{"date": start, "balance": balance}]
        for trade in sorted(trades, key=lambda item: item["entry_time"]):
            balance += balance * RISK_FRACTION * float(trade["outcome_r"])
            rows.append({"date": trade["exit_time"], "balance": balance})
        rows.append({"date": end, "balance": balance})
        result = pd.DataFrame(rows).sort_values("date")
        result["peak"] = result.balance.cummax()
        result["drawdown"] = (result.balance / result.peak - 1.0) * 100.0
        return result

    best = frame(selected_trades)
    literal = frame(literal_trades)
    plt.style.use("dark_background")
    fig, (ax, dd) = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [2.6, 1], "hspace": 0.16})
    fig.patch.set_facecolor("#071311")
    for axis in (ax, dd):
        axis.set_facecolor("#0b1c19")
        axis.grid(True, color="#28453f", alpha=0.45)
    ax.plot(best.date, best.balance, color="#5fffd1", lw=1.8, label="Training-selected")
    ax.plot(literal.date, literal.balance, color="#ffd166", lw=1.4, label="Literal ORB30 / 1R")
    ax.axhline(INITIAL, color="#9ab5ad", ls="--", lw=0.9)
    ax.set_title("US100 Fabio ORB — conservative screen, 1% volatility-targeted risk", loc="left", weight="bold")
    ax.set_ylabel("Balance USD")
    ax.legend(frameon=False)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    dd.fill_between(best.date, best.drawdown, 0, color="#ff6b6b", alpha=0.65)
    dd.plot(best.date, best.drawdown, color="#ff8a8a", lw=0.8)
    dd.set_ylabel("Selected DD")
    dd.yaxis.set_major_formatter(lambda value, _: f"{value:.0f}%")
    dd.xaxis.set_major_locator(mdates.YearLocator())
    dd.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.suptitle("$10,000 initial — fresh Exness USTEC M1 — actual spread + exit slippage", fontsize=15, weight="bold")
    fig.savefig(OUT / "screen-equity-comparison.png", dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def main() -> None:
    m1, source = pull_data()
    (OUT / "data-source.json").write_text(json.dumps(source, indent=2), encoding="utf-8")
    sessions = prepare_sessions(m1)
    print(f"constructed {len(sessions)} complete sessions", flush=True)
    start = min(session["date"] for session in sessions)
    end = max(session["date"] for session in sessions) + pd.Timedelta(days=1)

    configs = [
        Config(orb, cutoff, rr, bullish)
        for orb, cutoff, rr, bullish in itertools.product(
            (15, 30, 45), (60, 90, 120, 180, 330), (0.5, 0.75, 1.0, 1.25, 1.5), (False, True)
        )
        if cutoff > orb + 5
    ]
    rows = []
    trades_by_slug: dict[str, list[dict]] = {}
    for index, config in enumerate(configs, start=1):
        trades = simulate(sessions, config)
        trades_by_slug[config.slug] = trades
        rows.append(result_row(config, trades, start, end))
        if index % 25 == 0:
            print(f"screened {index}/{len(configs)}", flush=True)
    ranked = sorted(rows, key=lambda row: (bool(row["eligible"]), float(row["score"])), reverse=True)
    eligible = [row for row in ranked if row["eligible"]]
    selected = eligible[0] if eligible else ranked[0]
    literal_config = Config(30, 330, 1.0, False)
    literal = next(row for row in rows if row["slug"] == literal_config.slug)

    with (OUT / "all-screen-results.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ranked[0]))
        writer.writeheader()
        writer.writerows(ranked)
    (OUT / "top-screen-results.json").write_text(json.dumps(ranked[:50], indent=2), encoding="utf-8")
    summary = {
        "selected": selected,
        "literal": literal,
        "eligible_candidates": len(eligible),
        "selection_rule": "Training and validation only. Locked results were not used for selection.",
        "data_warning": "Exness USTEC has broker tick activity, not CME aggressive-buy/sell delta.",
    }
    (OUT / "screen-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    save_trades(OUT / "selected-screen-trades.csv", trades_by_slug[selected["slug"]])
    save_trades(OUT / "literal-screen-trades.csv", trades_by_slug[literal["slug"]])
    save_graph(selected, trades_by_slug[selected["slug"]], trades_by_slug[literal["slug"]], start, end)
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
