from __future__ import annotations

import csv
import itertools
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from statistics import median

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
STORE = ROOT / "EA store"
CACHE = STORE / "data" / "evidence-cache" / "v1" / "products"
OUT = Path(__file__).resolve().parent

ACCOUNT = 200_000.0
PHASE1_TARGET = 0.10
PHASE2_TARGET = 0.05
MAX_DAILY_LOSS = 0.05
MAX_TOTAL_LOSS = 0.10
MIN_TRADING_DAYS = 4
MAX_PHASE_DAYS = 730  # FTMO is unlimited; this is a reporting/censoring horizon.
MARGIN_RESERVE = 0.20

NEWS = {
    "news-pulse-xau": "News Pulse XAU",
    "news-pulse-xag": "News Pulse XAG",
    "news-pulse-btc": "News Pulse BTC",
}
TOP5 = {
    "orb-volume-profile-volume-confirmed": "ORB Volume Profile Volume Confirmed",
    "xau-trend-progression": "XAU Trend Progression",
    "usdjpy-london-open-momentum": "USDJPY London Open Momentum",
    "us100-orb-new-york-m30": "US100 ORB New York M30",
    "us100-h1-orb-13utc": "US100 H1 ORB 13UTC",
}
ALL = {**NEWS, **TOP5}
MODES = {slug: "standard" for slug in ALL}

# Current FTMO Swing asset-class leverage. These constraints are deliberately
# separated from the connected Standard account (which reports 1:100 overall).
LEVERAGE = {"XAUUSD": 9.0, "XAGUSD": 9.0, "BTCUSD": 1.0,
            "USTEC": 15.0, "USDJPY": 30.0}
CONTRACT = {"XAUUSD": 100.0, "XAGUSD": 5000.0, "BTCUSD": 1.0,
            "USTEC": 1.0, "USDJPY": 100_000.0}


@dataclass(frozen=True)
class Params:
    non_news_risk_pct: float
    non_news_daily_stop_pct: float
    max_open_risk_pct: float
    dd_soft_pct: float = 4.0
    dd_hard_pct: float = 7.0
    streak_soft: int = 3
    streak_hard: int = 5


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def summary(slug: str, period: str):
    return read_json(CACHE / slug / MODES[slug] / f"{period}.json")


def ledger(slug: str):
    return read_json(CACHE / slug / MODES[slug] / "5y.trades.json")


def swing_margin(symbol: str, volume: float, price: float) -> float:
    canonical = "USTEC" if symbol.upper().startswith(("USTEC", "US100", "NAS")) else symbol.upper().rstrip("R")
    if canonical == "USDJPY":
        notional_usd = volume * CONTRACT[canonical]
    else:
        notional_usd = volume * CONTRACT[canonical] * price
    return notional_usd / LEVERAGE[canonical]


def load_templates():
    starts = [date.fromisoformat(summary(slug, "5y")["available_from"]) for slug in ALL]
    ends = [date.fromisoformat(summary(slug, "5y")["available_to"]) for slug in ALL]
    common_start, common_end = max(starts), min(ends)
    week0 = common_start - timedelta(days=common_start.weekday())
    last_week = (common_end - timedelta(days=1)) - timedelta(days=(common_end - timedelta(days=1)).weekday())
    weeks = []
    cursor = week0
    while cursor <= last_week:
        weeks.append(cursor)
        cursor += timedelta(days=7)
    by_week = {week: [] for week in weeks}
    counts = Counter()
    for slug in ALL:
        for row in ledger(slug):
            opened = datetime.fromisoformat(row["open_time"])
            if not common_start <= opened.date() < common_end:
                continue
            closed = datetime.fromisoformat(row["close_time"])
            week = opened.date() - timedelta(days=opened.weekday())
            item = dict(row)
            item["slug"] = slug
            item["news"] = slug in NEWS
            item["open_offset"] = opened - datetime.combine(week, datetime.min.time())
            item["duration"] = max(closed - opened, timedelta(seconds=1))
            item["base_risk_pct"] = float(row.get("configured_risk_pct") or (0.75 if slug in NEWS else 1.0))
            item["risk_cash"] = float(row.get("estimated_risk_cash") or 100.0)
            item["source_balance"] = item["risk_cash"] / (item["base_risk_pct"] / 100.0)
            item["volume"] = float(row.get("volume") or row.get("lots") or 0.0)
            by_week[week].append(item)
            counts[slug] += 1
    return [by_week[w] for w in weeks], common_start, common_end, counts


TEMPLATES, COMMON_START, COMMON_END, HISTORICAL_COUNTS = load_templates()


def stress_pnl(row: dict, stress: str) -> float:
    pnl = float(row["net_profit"])
    risk = float(row["risk_cash"])
    if stress == "observed":
        return pnl
    if row["news"]:
        return pnl * (0.65 if pnl > 0 else 1.25) - 0.15 * risk
    return pnl * (0.90 if pnl > 0 else 1.10) - 0.02 * risk


def generate_events(week_plan: np.ndarray):
    events = []
    synthetic_week0 = datetime(2027, 1, 4)
    identifier = 0
    for index, source_index in enumerate(week_plan):
        destination = synthetic_week0 + timedelta(days=7 * index)
        for source in TEMPLATES[int(source_index)]:
            row = dict(source)
            opened = destination + source["open_offset"]
            closed = opened + source["duration"]
            row["id"] = identifier
            events.append((opened, 1, identifier, "open", row))
            events.append((closed, 0, identifier, "close", row))
            identifier += 1
    events.sort(key=lambda event: (event[0], event[1], event[2]))
    return events


def last_sunday(year: int, month: int) -> date:
    if month == 12:
        following = date(year + 1, 1, 1)
    else:
        following = date(year, month + 1, 1)
    last = following - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)


def prague_day(moment: datetime):
    """FTMO daily reset date in CE(S)T without requiring an OS tz database."""
    dst_start = datetime.combine(last_sunday(moment.year, 3), datetime.min.time()) + timedelta(hours=1)
    dst_end = datetime.combine(last_sunday(moment.year, 10), datetime.min.time()) + timedelta(hours=1)
    utc_offset = 2 if dst_start <= moment < dst_end else 1
    return (moment + timedelta(hours=utc_offset)).date()


def run_phase(week_plan: np.ndarray, target_pct: float, params: Params,
              *, stress: str, risk_envelope: bool, use_swing_margin: bool):
    balance = peak = ACCOUNT
    static_floor = ACCOUNT * (1.0 - MAX_TOTAL_LOSS)
    active = {}
    accepted = {}
    daily_anchor = ACCOUNT
    current_day = None
    daily_closed = 0.0
    loss_streak = defaultdict(int)
    trading_days = set()
    counters = Counter()
    start = None
    last = None

    for at, _, identifier, kind, row in generate_events(week_plan):
        if start is None:
            start = at
        if (at - start).days > MAX_PHASE_DAYS:
            break
        last = at
        day = prague_day(at)
        if day != current_day:
            current_day = day
            daily_anchor = balance
            daily_closed = 0.0
        daily_floor = daily_anchor - ACCOUNT * MAX_DAILY_LOSS
        slug = row["slug"]

        if kind == "open":
            news = bool(row["news"])
            if not news and daily_closed <= -ACCOUNT * params.non_news_daily_stop_pct / 100.0:
                counters["internal_daily_skips"] += 1
                continue
            scale = 1.0 if news else params.non_news_risk_pct / row["base_risk_pct"]
            reasons = ["news-exempt"] if news else []
            if not news:
                drawdown = 100.0 * (peak - balance) / peak if peak else 0.0
                if drawdown >= params.dd_hard_pct:
                    scale *= 0.25; reasons.append("hard-dd")
                elif drawdown >= params.dd_soft_pct:
                    scale *= 0.50; reasons.append("soft-dd")
                streak = loss_streak[slug]
                if streak >= params.streak_hard:
                    scale *= 0.25; reasons.append("hard-streak")
                elif streak >= params.streak_soft:
                    scale *= 0.50; reasons.append("soft-streak")
            # Lots/P&L in the source test already changed with its balance.
            # Normalize from the reconstructed balance at that trade's entry,
            # otherwise the historical compounding would be counted twice.
            balance_factor = balance / row["source_balance"]
            risk_cash = row["risk_cash"] * balance_factor * scale
            if not news and sum(position["risk"] for position in active.values()) + risk_cash > ACCOUNT * params.max_open_risk_pct / 100.0:
                counters["open_risk_cap_skips"] += 1
                continue
            volume = row["volume"] * balance_factor * scale
            margin = swing_margin(row["symbol"], volume, float(row["open_price"])) if use_swing_margin else 0.0
            if use_swing_margin and sum(position["margin"] for position in active.values()) + margin > balance * (1.0 - MARGIN_RESERVE):
                counters[f"margin_reject:{slug}"] += 1
                continue
            position = {"risk": risk_cash, "margin": margin, "scale": balance_factor * scale,
                        "reasons": reasons, "row": row}
            active[identifier] = position
            accepted[identifier] = position
            trading_days.add(day)
            counters[f"accepted:{slug}"] += 1
            if news:
                counters["news_accepted"] += 1
            if risk_envelope:
                worst_equity = balance - sum(position["risk"] for position in active.values())
                if worst_equity <= static_floor:
                    return "max_loss_envelope", (at - start).days + 1, counters
                if worst_equity <= daily_floor:
                    return "daily_loss_envelope", (at - start).days + 1, counters
            continue

        position = active.pop(identifier, None)
        if position is None:
            continue
        source_pnl = stress_pnl(row, stress)
        pnl = source_pnl * position["scale"]
        balance += pnl
        daily_closed += pnl
        peak = max(peak, balance)
        counters["closed_trades"] += 1
        if pnl < 0:
            loss_streak[slug] += 1
        elif pnl > 0:
            loss_streak[slug] = 0
        if balance <= static_floor:
            return "max_loss", (at - start).days + 1, counters
        if balance <= daily_floor:
            return "daily_loss", (at - start).days + 1, counters
        if balance >= ACCOUNT * (1.0 + target_pct) and len(trading_days) >= MIN_TRADING_DAYS and not active:
            return "pass", (at - start).days + 1, counters

    days = (last - start).days + 1 if start and last else MAX_PHASE_DAYS
    return "timeout", days, counters


def trial(plans, params, *, stress="stressed", risk_envelope=False, use_swing_margin=True):
    phase1, days1, counters1 = run_phase(plans[0], PHASE1_TARGET, params, stress=stress,
                                         risk_envelope=risk_envelope, use_swing_margin=use_swing_margin)
    counters = Counter(counters1)
    if phase1 != "pass":
        return {"outcome": phase1, "phase": 1, "days": days1, "counters": counters}
    phase2, days2, counters2 = run_phase(plans[1], PHASE2_TARGET, params, stress=stress,
                                         risk_envelope=risk_envelope, use_swing_margin=use_swing_margin)
    counters.update(counters2)
    return {"outcome": phase2, "phase": 2, "days": days1 + days2, "phase1_days": days1,
            "phase2_days": days2, "counters": counters}


def plans(seed: int, paths: int):
    rng = np.random.default_rng(seed)
    weeks = math.ceil(MAX_PHASE_DAYS / 7) + 2
    return rng.integers(0, len(TEMPLATES), size=(paths, 2, weeks), dtype=np.int16)


def evaluate(plan_array, params, *, stress="stressed", risk_envelope=False, use_swing_margin=True):
    trials = [trial(path, params, stress=stress, risk_envelope=risk_envelope,
                    use_swing_margin=use_swing_margin) for path in plan_array]
    outcomes = Counter(row["outcome"] for row in trials)
    passed = [row for row in trials if row["outcome"] == "pass"]
    failed = [row for row in trials if row["outcome"] not in ("pass", "timeout")]
    aggregate = Counter()
    for row in trials:
        aggregate.update(row["counters"])
    n = len(trials)
    phase1_passes = sum(1 for row in trials if row["phase"] == 2)
    phase1_failures = sum(1 for row in trials if row["phase"] == 1 and row["outcome"] != "timeout")
    phase1_timeouts = sum(1 for row in trials if row["phase"] == 1 and row["outcome"] == "timeout")
    phase2_passes = len(passed)
    phase2_failures = sum(1 for row in trials if row["phase"] == 2 and row["outcome"] != "pass" and row["outcome"] != "timeout")
    phase2_timeouts = sum(1 for row in trials if row["phase"] == 2 and row["outcome"] == "timeout")
    failure_reasons_by_phase = {
        "phase1": dict(Counter(row["outcome"] for row in trials
                               if row["phase"] == 1 and row["outcome"] != "timeout")),
        "phase2": dict(Counter(row["outcome"] for row in trials
                               if row["phase"] == 2 and row["outcome"] not in ("pass", "timeout"))),
    }
    probability = len(passed) / n
    z = 1.96
    denominator = 1 + z * z / n
    center = (probability + z * z / (2 * n)) / denominator
    radius = z * math.sqrt(probability * (1 - probability) / n + z * z / (4 * n * n)) / denominator
    result = {
        "paths": n,
        "passes": len(passed),
        "pass_probability_pct": round(100 * probability, 2),
        "pass_probability_95ci_pct": [round(100 * max(0, center - radius), 2), round(100 * min(1, center + radius), 2)],
        "expected_challenges_per_pass": round(1 / probability, 2) if probability else None,
        "failures": n - len(passed) - outcomes["timeout"],
        "timeouts": outcomes["timeout"],
        "outcomes": dict(outcomes),
        "phase_breakdown": {
            "phase1": {"passes": phase1_passes, "failures": phase1_failures, "timeouts": phase1_timeouts},
            "phase2_conditional": {"entrants": phase1_passes, "passes": phase2_passes,
                                   "failures": phase2_failures, "timeouts": phase2_timeouts},
        },
        "failure_reasons_by_phase": failure_reasons_by_phase,
        "median_days_if_passed": round(median(row["days"] for row in passed), 1) if passed else None,
        "p90_days_if_passed": round(float(np.percentile([row["days"] for row in passed], 90)), 1) if passed else None,
        "median_days_to_rule_breach": round(median(row["days"] for row in failed), 1) if failed else None,
        "p90_days_to_rule_breach": round(float(np.percentile([row["days"] for row in failed], 90)), 1) if failed else None,
        "median_phase1_days": round(median(row["phase1_days"] for row in passed), 1) if passed else None,
        "median_phase2_days": round(median(row["phase2_days"] for row in passed), 1) if passed else None,
        "average_closed_trades_per_attempt": round(aggregate["closed_trades"] / n, 2),
        "average_margin_rejections_per_attempt": round(sum(v for k, v in aggregate.items() if k.startswith("margin_reject:")) / n, 2),
        "average_internal_daily_skips_per_attempt": round(aggregate["internal_daily_skips"] / n, 2),
        "average_open_risk_cap_skips_per_attempt": round(aggregate["open_risk_cap_skips"] / n, 2),
        "margin_rejections_by_ea": {k.split(":", 1)[1]: round(v / n, 2) for k, v in aggregate.items() if k.startswith("margin_reject:")},
        "accepted_trades_by_ea": {k.split(":", 1)[1]: round(v / n, 2) for k, v in aggregate.items() if k.startswith("accepted:")},
    }
    return result


def historical_stats():
    rows = []
    for slug, label in ALL.items():
        periods = {period: summary(slug, period)["stats"] for period in ("6m", "1y", "3y", "5y")}
        trades = ledger(slug)
        row = {"slug": slug, "label": label,
               "symbol": trades[0].get("symbol") if trades else None,
               "historical_trades_common_window": HISTORICAL_COUNTS[slug]}
        for period, stats in periods.items():
            for key in ("return_pct", "profit_factor", "win_rate_pct", "max_drawdown_pct", "trades"):
                row[f"{period}_{key}"] = stats[key]
        rows.append(row)
    return rows


def main():
    # Use an independent 300-path screen to choose controls, then reserve the
    # required 1,000 paths exclusively for the final out-of-sample validation.
    calibration = plans(2026091201, 300)
    grid = []
    for risk, daily, exposure in itertools.product((0.20, 0.25, 0.35, 0.50), (1.0, 1.5, 2.0), (2.0, 3.0)):
        params = Params(risk, daily, exposure)
        result = evaluate(calibration, params, stress="stressed", use_swing_margin=True)
        grid.append({"params": params.__dict__, **result})
    # Highest lower confidence bound, then fewer failures, then faster completion.
    selected = max(grid, key=lambda row: (row["pass_probability_95ci_pct"][0], -row["failures"],
                                           -(row["median_days_if_passed"] or 99999)))
    params = Params(**selected["params"])
    validation = plans(2026091202, 1000)
    scenarios = {
        "observed_close_only": evaluate(validation, params, stress="observed", use_swing_margin=True),
        "stressed_close_only": evaluate(validation, params, stress="stressed", use_swing_margin=True),
        "stressed_stop_envelope": evaluate(validation, params, stress="stressed", risk_envelope=True, use_swing_margin=True),
        "naive_observed_ignoring_swing_margin": evaluate(validation, params, stress="observed", use_swing_margin=False),
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ftmo_product": "FTMO CFD 2-Step Swing, $200,000",
        "rules": {"phase1_target_pct": 10, "phase2_target_pct": 5, "max_daily_loss_pct": 5,
                  "max_total_loss_pct": 10, "minimum_trading_days_per_phase": 4,
                  "phase_horizon_days_for_reporting": MAX_PHASE_DAYS, "official_trading_period": "unlimited"},
        "selected_parameters": params.__dict__,
        "news_risk": "Locked 0.75% planned risk per entry; adaptive controls bypassed",
        "margin_reserve_pct": 100 * MARGIN_RESERVE,
        "source_window_common": [COMMON_START.isoformat(), COMMON_END.isoformat()],
        "source_weeks": len(TEMPLATES),
        "parameter_screen_paths": len(calibration),
        "validation_paths_per_scenario": len(validation),
        "portfolio": historical_stats(),
        "excluded": {
            "gold-news-v9-direction": "No verified historical backtest evidence.",
            "news-pulse-btc_from_ftmo_estimate": "Loaded for audit, but every attempted template is rejected by the conservative FTMO Swing 1:1 crypto margin model at locked risk.",
        },
        "selection_grid": grid,
        "validation_scenarios": scenarios,
        "stress": {"news_winner_multiplier": 0.65, "news_loser_multiplier": 1.25,
                   "news_extra_adverse_slippage_R": 0.15, "non_news_winner_multiplier": 0.90,
                   "non_news_loser_multiplier": 1.10, "non_news_extra_adverse_slippage_R": 0.02},
        "limitations": [
            "The five-year trades are the website's broker-native cached tests, not five years of FTMO ticks/fills.",
            "Only closed deals and configured stop risk are available; exact intratrade floating equity is unavailable.",
            "The close-only result can miss an intratrade FTMO breach. The stop-envelope result assumes every concurrent trade reaches its full planned stop together and is deliberately conservative.",
            "Weekly block bootstrap preserves sampled within-week clustering but cannot predict a new market regime.",
            "News real-tick coverage is 13% in the five-year source tests; missing older ticks were generated by MT5.",
            "Margin is modelled from historical lots/prices and FTMO Swing asset-class leverage with a 20% reserve; actual contract specifications and execution can change.",
            "A timeout at 730 days is censored, not an FTMO rule failure, because FTMO's trading period is unlimited.",
        ],
    }
    (OUT / "results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    with (OUT / "parameter-grid.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["non_news_risk_pct", "non_news_daily_stop_pct", "max_open_risk_pct",
                  "pass_probability_pct", "failures", "timeouts", "median_days_if_passed"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in grid:
            writer.writerow({**{key: row["params"][key] for key in fields[:3]},
                             **{key: row[key] for key in fields[3:]}})
    print(json.dumps({"selected": params.__dict__, "scenarios": scenarios,
                      "window": payload["source_window_common"]}, indent=2))


if __name__ == "__main__":
    main()
