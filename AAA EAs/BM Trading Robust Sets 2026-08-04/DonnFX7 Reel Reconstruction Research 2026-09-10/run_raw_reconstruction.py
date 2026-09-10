"""No-lookahead reconstruction of the DonnFX7 Instagram trade breakdown.

The reel does not publish executable rules.  This script therefore turns only
the visible concepts into objective rules and keeps the work isolated from the
production Calyx system.  It uses the existing Exness XAUUSD M15 archive.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PORTFOLIO = ROOT.parent
SOURCE_DATA = PORTFOLIO / "Slow Multi Asset Trend Research 2026-09-06" / "Data"
DATA = SOURCE_DATA / "XAUUSD-M15.npz"
METADATA = SOURCE_DATA / "metadata.json"
RISK_FRACTION = 0.01
DEVELOPMENT_START = pd.Timestamp("2023-09-01", tz="UTC")
LOCKED_START = pd.Timestamp("2025-09-01", tz="UTC")
END = pd.Timestamp("2026-09-01", tz="UTC")


@dataclass(frozen=True)
class Spec:
    name: str
    require_profile: bool = True
    require_relative_volume: bool = False
    require_choch: bool = True
    require_trend: bool = False
    confirmation_bars: int = 8
    allow_long: bool = True
    allow_short: bool = True
    target_mode: str = "fixed"
    reward_risk: float = 2.5


@dataclass
class Metrics:
    return_pct: float
    profit_factor: float
    win_rate_pct: float
    max_drawdown_pct: float
    trades: int
    sharpe: float
    recovery: float
    expected_r: float
    average_win_r: float
    average_loss_r: float
    max_win_streak: int
    max_loss_streak: int
    long_trades: int
    short_trades: int


SPECS = (
    Spec("reel-mechanical-fixed-2.5R"),
    Spec("reel-mechanical-structural-target", target_mode="structural"),
    Spec("long-only-as-shown", allow_short=False),
    Spec("no-profile-ablation", require_profile=False),
    Spec("h1-trend-filter-ablation", require_trend=True),
    Spec("relative-volume-ablation", require_relative_volume=True),
    Spec("direct-sweep-ablation", require_choch=False),
)


def load_data() -> tuple[pd.DataFrame, dict]:
    with np.load(DATA) as archive:
        rates = archive["rates"]
    frame = pd.DataFrame({name: rates[name] for name in rates.dtype.names})
    frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
    frame = frame.set_index("time").sort_index()
    frame = frame[(frame.index >= pd.Timestamp("2022-01-01", tz="UTC")) & (frame.index < END)].copy()
    metadata = json.loads(METADATA.read_text(encoding="utf-8"))["symbols"]["XAUUSD"]
    return frame, metadata


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    previous_close = result["close"].shift(1)
    tr = pd.concat(
        [
            result["high"] - result["low"],
            (result["high"] - previous_close).abs(),
            (result["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    result["atr"] = tr.ewm(alpha=1.0 / 14.0, adjust=False).mean()
    result["prior_low_16"] = result["low"].shift(1).rolling(16).min()
    result["prior_high_16"] = result["high"].shift(1).rolling(16).max()
    result["volume_median_32"] = result["tick_volume"].shift(1).rolling(32).median()

    h1 = result.resample("1h", label="right", closed="right").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last"}
    ).dropna()
    h1["ema50"] = h1["close"].ewm(span=50, adjust=False).mean()
    h1["ema50_previous"] = h1["ema50"].shift(4)
    aligned = h1[["close", "ema50", "ema50_previous"]].reindex(result.index, method="ffill")
    result["h1_close"] = aligned["close"]
    result["h1_ema50"] = aligned["ema50"]
    result["h1_ema50_previous"] = aligned["ema50_previous"]
    result["week"] = result.index.to_period("W-SUN").astype(str)
    return result


def volume_profile(week: pd.DataFrame, bins: int = 128, value_area: float = 0.70) -> dict | None:
    if len(week) < 80:
        return None
    low = float(week["low"].min())
    high = float(week["high"].max())
    if high <= low:
        return None
    edges = np.linspace(low, high, bins + 1)
    activity = np.zeros(bins, dtype=float)
    for bar in week.itertuples():
        first = int(np.clip(np.searchsorted(edges, float(bar.low), side="right") - 1, 0, bins - 1))
        last = int(np.clip(np.searchsorted(edges, float(bar.high), side="left"), 0, bins - 1))
        if last < first:
            first, last = last, first
        share = float(bar.tick_volume) / max(1, last - first + 1)
        activity[first : last + 1] += share
    poc_index = int(np.argmax(activity))
    included = {poc_index}
    accumulated = float(activity[poc_index])
    target = float(activity.sum()) * value_area
    lower = poc_index - 1
    upper = poc_index + 1
    while accumulated < target and (lower >= 0 or upper < bins):
        lower_value = activity[lower] if lower >= 0 else -1.0
        upper_value = activity[upper] if upper < bins else -1.0
        chosen = lower if lower_value >= upper_value else upper
        included.add(chosen)
        accumulated += float(activity[chosen])
        if chosen == lower:
            lower -= 1
        else:
            upper += 1
    return {
        "week_low": low,
        "week_high": high,
        "poc": float((edges[poc_index] + edges[poc_index + 1]) / 2.0),
        "val": float(edges[min(included)]),
        "vah": float(edges[max(included) + 1]),
        "bars": int(len(week)),
    }


def attach_previous_week_profiles(frame: pd.DataFrame) -> pd.DataFrame:
    profiles: dict[str, dict] = {}
    week_order = list(dict.fromkeys(frame["week"].tolist()))
    for label, subset in frame.groupby("week", sort=False):
        profile = volume_profile(subset)
        if profile:
            profiles[label] = profile
    previous: dict[str, dict] = {}
    for index in range(1, len(week_order)):
        prior = profiles.get(week_order[index - 1])
        if prior:
            previous[week_order[index]] = prior
    for key in ("week_low", "week_high", "poc", "val", "vah", "bars"):
        frame[key] = frame["week"].map(lambda label: previous.get(label, {}).get(key, np.nan))
    weekly_range = frame["week_high"] - frame["week_low"]
    frame["long_zone_low"] = frame["week_high"] - 0.786 * weekly_range
    frame["long_zone_high"] = frame["week_high"] - 0.618 * weekly_range
    frame["short_zone_low"] = frame["week_low"] + 0.618 * weekly_range
    frame["short_zone_high"] = frame["week_low"] + 0.786 * weekly_range
    return frame


def profile_matches(row: pd.Series, direction: int) -> bool:
    tolerance = 0.25 * float(row.atr)
    if direction > 0:
        return float(row.val) >= float(row.long_zone_low) - tolerance and float(row.val) <= float(row.long_zone_high) + tolerance
    return float(row.vah) >= float(row.short_zone_low) - tolerance and float(row.vah) <= float(row.short_zone_high) + tolerance


def sweep_signal(row: pd.Series, direction: int, require_trend: bool) -> bool:
    atr = float(row.atr)
    if not math.isfinite(atr) or atr <= 0.0:
        return False
    bar_range = max(float(row.high) - float(row.low), 1e-9)
    if direction > 0:
        level = float(row.prior_low_16)
        in_zone = float(row.low) <= float(row.long_zone_high) and float(row.low) >= float(row.long_zone_low) - 0.75 * atr
        swept = float(row.low) <= level - 0.05 * atr and float(row.close) > level
        close_location = (float(row.close) - float(row.low)) / bar_range
        trend = float(row.h1_close) > float(row.h1_ema50) and float(row.h1_ema50) >= float(row.h1_ema50_previous)
    else:
        level = float(row.prior_high_16)
        in_zone = float(row.high) >= float(row.short_zone_low) and float(row.high) <= float(row.short_zone_high) + 0.75 * atr
        swept = float(row.high) >= level + 0.05 * atr and float(row.close) < level
        close_location = (float(row.high) - float(row.close)) / bar_range
        trend = float(row.h1_close) < float(row.h1_ema50) and float(row.h1_ema50) <= float(row.h1_ema50_previous)
    return bool(in_zone and swept and close_location >= 0.60 and (trend or not require_trend))


def confirmation(
    row: pd.Series,
    setup: dict,
    direction: int,
    require_relative_volume: bool,
    require_profile: bool,
) -> bool:
    atr = float(row.atr)
    body = abs(float(row.close) - float(row.open))
    directional = float(row.close) > float(row.open) if direction > 0 else float(row.close) < float(row.open)
    broke = float(row.close) > float(setup["choch_level"]) if direction > 0 else float(row.close) < float(setup["choch_level"])
    volume_ok = float(row.tick_volume) >= float(row.volume_median_32) if require_relative_volume else True
    profile_reclaim = (float(row.close) > float(row.val) if direction > 0 else float(row.close) < float(row.vah)) if require_profile else True
    return directional and broke and body >= 0.20 * atr and volume_ok and profile_reclaim


def trade_return_r(position: dict, row: pd.Series, point: float) -> tuple[float, str] | None:
    spread = max(0.0, float(row.spread) * point)
    if position["direction"] > 0:
        stop_hit = float(row.low) <= position["stop"]
        target_hit = float(row.high) >= position["target"]
        if stop_hit and target_hit:
            return -1.0, "ambiguous-stop-first"
        if stop_hit:
            return -1.0, "stop"
        if target_hit:
            return (position["target"] - position["entry"]) / position["risk"], "target"
        mark = float(row.close)
        pnl = mark - position["entry"]
    else:
        ask_high = float(row.high) + spread
        ask_low = float(row.low) + spread
        stop_hit = ask_high >= position["stop"]
        target_hit = ask_low <= position["target"]
        if stop_hit and target_hit:
            return -1.0, "ambiguous-stop-first"
        if stop_hit:
            return -1.0, "stop"
        if target_hit:
            return (position["entry"] - position["target"]) / position["risk"], "target"
        mark = float(row.close) + spread
        pnl = position["entry"] - mark
    if position["bars"] >= 96:
        return pnl / position["risk"], "time"
    return None


def simulate(frame: pd.DataFrame, spec: Spec, point: float) -> list[dict]:
    trades: list[dict] = []
    setups: dict[int, dict | None] = {1: None, -1: None}
    pending: dict | None = None
    position: dict | None = None
    last_trade_day: dict[int, str] = {1: "", -1: ""}
    rows = list(frame.itertuples())

    for index in range(40, len(frame) - 1):
        timestamp = frame.index[index]
        row = frame.iloc[index]

        if position is not None:
            position["bars"] += 1
            closed = trade_return_r(position, row, point)
            if closed is not None:
                result_r, reason = closed
                trades.append(
                    {
                        "spec": spec.name,
                        "entry_time": position["entry_time"].isoformat(),
                        "exit_time": timestamp.isoformat(),
                        "direction": "long" if position["direction"] > 0 else "short",
                        "entry": position["entry"],
                        "stop": position["stop"],
                        "target": position["target"],
                        "result_r": float(result_r),
                        "result_pct": float(result_r) * RISK_FRACTION * 100.0,
                        "exit_reason": reason,
                        "profile_poc": position["poc"],
                        "profile_val": position["val"],
                        "profile_vah": position["vah"],
                        "week_low": position["week_low"],
                        "week_high": position["week_high"],
                    }
                )
                position = None

        if position is None and pending is not None and pending["entry_index"] == index:
            direction = int(pending["direction"])
            spread = max(0.0, float(row.spread) * point)
            entry = float(row.open) + spread if direction > 0 else float(row.open)
            atr = float(pending["atr"])
            if direction > 0:
                stop = min(float(pending["extreme"]) - 0.10 * atr, entry - 0.50 * atr)
                risk = entry - stop
                structural = float(pending["short_zone_low"])
                target = entry + spec.reward_risk * risk if spec.target_mode == "fixed" else structural
            else:
                stop = max(float(pending["extreme"]) + 0.10 * atr + spread, entry + 0.50 * atr)
                risk = stop - entry
                structural = float(pending["long_zone_high"])
                target = entry - spec.reward_risk * risk if spec.target_mode == "fixed" else structural
            reward = target - entry if direction > 0 else entry - target
            if risk > 0 and reward / risk >= 1.50 and risk <= 3.0 * atr:
                position = {
                    "direction": direction,
                    "entry_time": timestamp,
                    "entry": entry,
                    "stop": stop,
                    "target": target,
                    "risk": risk,
                    "bars": 0,
                    **{key: pending[key] for key in ("poc", "val", "vah", "week_low", "week_high")},
                }
                last_trade_day[direction] = timestamp.strftime("%Y-%m-%d")
            pending = None

        if position is not None or not math.isfinite(float(row.week_low)):
            continue

        for direction in (1, -1):
            if direction > 0 and not spec.allow_long:
                continue
            if direction < 0 and not spec.allow_short:
                continue
            setup = setups[direction]
            if setup is not None:
                setup["age"] += 1
                if setup["age"] > spec.confirmation_bars:
                    setups[direction] = None
                    setup = None
            if setup is not None:
                if not spec.require_choch or confirmation(row, setup, direction, spec.require_relative_volume, spec.require_profile):
                    pending = {
                        "entry_index": index + 1,
                        "direction": direction,
                        "extreme": setup["extreme"],
                        "atr": float(row.atr),
                        **{key: float(row[key]) for key in ("poc", "val", "vah", "week_low", "week_high", "short_zone_low", "long_zone_high")},
                    }
                    setups[direction] = None
                    break

            day = timestamp.strftime("%Y-%m-%d")
            if setups[direction] is None and day != last_trade_day[direction] and sweep_signal(row, direction, spec.require_trend):
                if spec.require_profile and not profile_matches(row, direction):
                    continue
                volume_ok = float(row.tick_volume) >= float(row.volume_median_32)
                if spec.require_relative_volume and not volume_ok:
                    continue
                if direction > 0:
                    choch_level = max(float(frame.iloc[index - offset].high) for offset in (1, 2, 3))
                    extreme = float(row.low)
                else:
                    choch_level = min(float(frame.iloc[index - offset].low) for offset in (1, 2, 3))
                    extreme = float(row.high)
                setups[direction] = {"age": 0, "choch_level": choch_level, "extreme": extreme}
                if not spec.require_choch:
                    # The following bar is still used, preventing close-to-open lookahead.
                    setups[direction]["choch_level"] = float(row.close)
    return trades


def streaks(values: list[float]) -> tuple[int, int]:
    best_win = best_loss = current_win = current_loss = 0
    for value in values:
        if value > 0:
            current_win += 1
            current_loss = 0
            best_win = max(best_win, current_win)
        elif value < 0:
            current_loss += 1
            current_win = 0
            best_loss = max(best_loss, current_loss)
        else:
            current_win = current_loss = 0
    return best_win, best_loss


def metrics(trades: list[dict], years: float) -> Metrics:
    values = [float(item["result_r"]) for item in trades]
    returns = np.asarray(values, dtype=float) * RISK_FRACTION
    equity = np.cumprod(1.0 + returns) if len(returns) else np.asarray([1.0])
    equity = np.concatenate(([1.0], equity))
    peak = np.maximum.accumulate(equity)
    drawdown = (peak - equity) / peak
    wins = [value for value in values if value > 0]
    losses = [value for value in values if value < 0]
    gross_win = sum(wins)
    gross_loss = -sum(losses)
    win_streak, loss_streak = streaks(values)
    annual_trades = len(values) / max(years, 1e-9)
    sharpe = float(np.mean(returns) / np.std(returns, ddof=1) * math.sqrt(annual_trades)) if len(returns) > 1 and np.std(returns, ddof=1) > 0 else 0.0
    total_return = float(equity[-1] - 1.0) * 100.0
    maximum_dd = float(drawdown.max()) * 100.0
    return Metrics(
        return_pct=total_return,
        profit_factor=gross_win / gross_loss if gross_loss > 0 else (999.0 if gross_win > 0 else 0.0),
        win_rate_pct=100.0 * len(wins) / len(values) if values else 0.0,
        max_drawdown_pct=maximum_dd,
        trades=len(values),
        sharpe=sharpe,
        recovery=total_return / maximum_dd if maximum_dd > 0 else 0.0,
        expected_r=float(np.mean(values)) if values else 0.0,
        average_win_r=float(np.mean(wins)) if wins else 0.0,
        average_loss_r=float(np.mean(losses)) if losses else 0.0,
        max_win_streak=win_streak,
        max_loss_streak=loss_streak,
        long_trades=sum(item["direction"] == "long" for item in trades),
        short_trades=sum(item["direction"] == "short" for item in trades),
    )


def period_trades(trades: list[dict], start: pd.Timestamp, end: pd.Timestamp) -> list[dict]:
    return [item for item in trades if start <= pd.Timestamp(item["entry_time"]) < end]


def save_equity_chart(all_trades: dict[str, list[dict]]) -> None:
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(14, 7))
    for spec in SPECS:
        trades = period_trades(all_trades[spec.name], DEVELOPMENT_START, END)
        if not trades:
            continue
        times = [DEVELOPMENT_START] + [pd.Timestamp(item["exit_time"]) for item in trades]
        returns = np.asarray([float(item["result_r"]) * RISK_FRACTION for item in trades])
        equity = np.concatenate(([10_000.0], 10_000.0 * np.cumprod(1.0 + returns)))
        ax.plot(times, equity, linewidth=1.5, label=spec.name)
    ax.axvline(LOCKED_START, color="#ffcc66", linestyle="--", linewidth=1.2, label="locked year starts")
    ax.set_title("DonnFX7 reel reconstruction — isolated XAUUSD M15 audit")
    ax.set_ylabel("Compounded equity at 1% risk")
    ax.grid(alpha=0.18)
    ax.legend(fontsize=8, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "equity-comparison.png", dpi=170)
    plt.close(fig)


def main() -> None:
    frame, metadata = load_data()
    frame = attach_previous_week_profiles(add_indicators(frame))
    point = float(metadata["point"])
    all_trades: dict[str, list[dict]] = {}
    rows: list[dict] = []
    for spec in SPECS:
        trades = simulate(frame, spec, point)
        all_trades[spec.name] = trades
        pd.DataFrame(trades).to_csv(ROOT / f"trades-{spec.name}.csv", index=False)
        for period, start, end, years in (
            ("development", DEVELOPMENT_START, LOCKED_START, 2.0),
            ("locked", LOCKED_START, END, 1.0),
            ("full", DEVELOPMENT_START, END, 3.0),
        ):
            result = metrics(period_trades(trades, start, end), years)
            rows.append({"spec": spec.name, "period": period, **asdict(result)})
        print(f"DONE {spec.name}: {len(trades)} archive trades", flush=True)

    result_frame = pd.DataFrame(rows)
    result_frame.to_csv(ROOT / "raw-results.csv", index=False)
    save_equity_chart(all_trades)
    payload = {
        "source": {
            "reel": "https://www.instagram.com/reel/DdFLweEt7Kf/",
            "creator": "DonnFX7 / Mortadha Haddad",
            "caption": "Trade Breakdown",
            "disclosure": "The reel supplies no transcript or exact parameters. Rules below are an auditable reconstruction, not a claim about the creator's private method.",
        },
        "data": {
            "broker": "Exness-MT5Trial16",
            "symbol": "XAUUSD",
            "timeframe": "M15",
            "first_bar": frame.index.min().isoformat(),
            "last_bar": frame.index.max().isoformat(),
            "spread": "historical MT5 bar spread used at entry and on short stop/target triggers",
            "risk": "1% equity per trade, compounded",
        },
        "mechanical_rules": {
            "context": "completed previous-week range; the unstated H1 EMA50 trend idea is retained only as an ablation",
            "zones": "previous completed week's 61.8%-78.6% discount/premium retracement band",
            "profile": "128-bin previous-week tick-volume profile, 70% value area; long requires VAL near discount and short requires VAH near premium",
            "sweep": "M15 pierces the prior 16-bar extreme by at least 0.05 ATR and closes back through it in the outer 40% of its range",
            "confirmation": "within eight M15 bars, a >=0.20 ATR directional body closes through the pre-sweep three-bar structure level and reclaims VAL/VAH; relative tick activity is tested only as an ablation",
            "entry": "next M15 open; long pays the historical spread",
            "stop": "beyond sweep by 0.10 ATR, minimum 0.50 ATR and maximum 3 ATR",
            "target": "2.5R strict target; separate opposing-zone structural-target audit",
            "holding": "maximum 96 M15 bars",
            "intrabar": "stop-first whenever both stop and target occur in one M15 bar",
        },
        "results": rows,
        "production_changes": [],
    }
    (ROOT / "raw-audit.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def row_for(spec_name: str, period: str) -> pd.Series:
        return result_frame[(result_frame.spec == spec_name) & (result_frame.period == period)].iloc[0]

    strict_dev = row_for("reel-mechanical-fixed-2.5R", "development")
    strict_locked = row_for("reel-mechanical-fixed-2.5R", "locked")
    locked_pass = strict_locked.return_pct > 0 and strict_locked.profit_factor >= 1.10 and strict_locked.trades >= 25
    verdict = (
        "RAW PASS FOR PIPELINE REVIEW. The mechanical reconstruction stayed profitable with PF >= 1.10 and at least 25 untouched locked-year trades. It is still not deployment-ready."
        if locked_pass
        else "RAW REJECT. The mechanical reconstruction did not meet the minimum untouched-year gate (positive return, PF >= 1.10, at least 25 trades). Do not optimize or deploy it unless the user deliberately approves a broader hypothesis test."
    )
    lines = [
        "# DonnFX7 reel reconstruction — raw XAUUSD result",
        "",
        "## Decision",
        "",
        f"**{verdict}**",
        "",
        "This is a no-lookahead mechanical reconstruction of what is visible in the reel—not a claim that these are the creator's unpublished exact rules. No Calyx EA, website page, BAT, recommended portfolio, or active MT5 terminal was changed.",
        "",
        "## What the reel shows",
        "",
        "- XAUUSD returning to a lower demand/discount region.",
        "- A liquidity sweep/rejection around a marked horizontal level.",
        "- Fixed-range volume-profile confluence around the completed move.",
        "- A long entry aimed at the opposing upper supply area.",
        "- The reel shows examples and account results, but not a complete rulebook, timeframe declaration, profile anchor rule, or objective zone algorithm.",
        "",
        "## Auditable rule translation",
        "",
        "1. Use only the previous completed week's XAUUSD M15 bars to build a 128-row, 70% value-area tick-volume profile.",
        "2. Treat the prior week's 61.8%-78.6% retracement as discount/premium. Longs require VAL near discount; shorts require VAH near premium.",
        "3. Require an M15 sweep of the prior 16-bar extreme and a close back through it inside the discount/premium zone.",
        "4. Within eight bars require a directional change-of-character close through the pre-sweep three-bar structure and a VAL/VAH reclaim.",
        "5. Enter next bar, stop beyond the sweep, target 2.5R, and force-close after 96 bars. Same-bar ambiguity is always charged as a loss.",
        "",
        "## Results",
        "",
        "| Version | Period | Return | PF | Win rate | DD | Trades | Sharpe | Exp. R | Long / short |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for spec in SPECS:
        for period in ("development", "locked", "full"):
            value = row_for(spec.name, period)
            lines.append(
                f"| {spec.name} | {period} | {value.return_pct:+.2f}% | {value.profit_factor:.2f} | {value.win_rate_pct:.2f}% | {value.max_drawdown_pct:.2f}% | {int(value.trades)} | {value.sharpe:.2f} | {value.expected_r:+.3f} | {int(value.long_trades)} / {int(value.short_trades)} |"
            )
    lines += [
        "",
        "## Reading the ablations",
        "",
        "- `no-profile-ablation` answers whether the volume-profile requirement adds value or merely removes trades.",
        "- `h1-trend-filter-ablation` measures the extra trend rule that was initially considered but is not stated by the reel.",
        "- `relative-volume-ablation` measures an additional median-volume confirmation that is not stated by the reel.",
        "- `direct-sweep-ablation` enters without the later structure break, measuring the contribution of confirmation.",
        "- `long-only-as-shown` tests only the direction actually demonstrated in the reel.",
        "- `structural-target` aims at the opposing weekly premium/discount boundary instead of forcing 2.5R.",
        "",
        f"Mechanical development: {strict_dev.return_pct:+.2f}% return, PF {strict_dev.profit_factor:.2f}, {int(strict_dev.trades)} trades. Mechanical untouched year: {strict_locked.return_pct:+.2f}% return, PF {strict_locked.profit_factor:.2f}, {int(strict_locked.trades)} trades.",
        "",
        "![Equity comparison](equity-comparison.png)",
    ]
    (ROOT / "RAW RESULT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"SAVED {ROOT / 'RAW RESULT.md'}", flush=True)


if __name__ == "__main__":
    main()
