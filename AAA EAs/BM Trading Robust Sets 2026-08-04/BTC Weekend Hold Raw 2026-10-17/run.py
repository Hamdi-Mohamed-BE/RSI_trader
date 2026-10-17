"""Fixed BTC weekend-hold reference; archived NumPy prices only, no MT5 import.

Running this file only writes research outputs beside this script. It does not
fetch market data, start programs, alter EAs, or access trading accounts.
"""
from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta, timezone
import hashlib
from html import escape
import json
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np


ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
UTC = timezone.utc
NY = ZoneInfo("America/New_York")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def iso(epoch: int) -> str:
    return datetime.fromtimestamp(int(epoch), UTC).isoformat()


def month_offset(value: datetime, months: int) -> datetime:
    index = value.year * 12 + value.month - 1 + months
    year, month0 = divmod(index, 12)
    month = month0 + 1
    return value.replace(year=year, month=month, day=min(value.day, calendar.monthrange(year, month)[1]))


def scheduled_weekends(start: int, end_exclusive: int) -> list[tuple[int, int]]:
    """Generate the two local wall clocks independently, honoring DST changes."""
    day = datetime.fromtimestamp(start, NY).date() - timedelta(days=1)
    last = datetime.fromtimestamp(end_exclusive, NY).date()
    pairs = []
    while day <= last:
        if day.weekday() == 4:
            entry = datetime.combine(day, time(17), NY)
            exit_time = datetime.combine(day + timedelta(days=2), time(17), NY)
            entry_epoch, exit_epoch = int(entry.timestamp()), int(exit_time.timestamp())
            if start <= entry_epoch < end_exclusive:
                pairs.append((entry_epoch, exit_epoch))
        day += timedelta(days=1)
    return pairs


def exact_index(times: np.ndarray, target: int) -> int | None:
    index = int(np.searchsorted(times, target))
    return index if index < len(times) and int(times[index]) == target else None


def quantity_for_notional(balance: float, ask: float, allocation: str, fixed_notional: float) -> float:
    if not math.isfinite(ask) or ask <= 0 or not math.isfinite(balance):
        raise ValueError("Invalid cash or ask price")
    if allocation == "cash":
        if balance <= 0:
            raise ValueError("Cash-funded allocation requires positive cash")
        notional = balance
    elif allocation == "fixed_reference":
        notional = fixed_notional
    else:
        raise ValueError("Unknown allocation")
    if not math.isfinite(notional) or notional <= 0:
        raise ValueError("Positive notional required")
    return notional / ask


def profit_factor(values: list[float]) -> float | None:
    profit = sum(value for value in values if value > 0)
    loss = -sum(value for value in values if value < 0)
    return profit / loss if loss > 0 else None


def streaks(values: list[float]) -> tuple[int, int]:
    wins = losses = max_wins = max_losses = 0
    for value in values:
        if value > 0:
            wins += 1
            losses = 0
        elif value < 0:
            losses += 1
            wins = 0
        else:
            wins = losses = 0
        max_wins, max_losses = max(max_wins, wins), max(max_losses, losses)
    return max_wins, max_losses


def drawdown(values: list[float] | np.ndarray) -> dict:
    array = np.asarray(values, dtype=float)
    if not len(array) or not np.all(np.isfinite(array)):
        raise ValueError("Finite equity observations required")
    peak = np.maximum.accumulate(array)
    dollars = peak - array
    percent = np.divide(dollars, peak, out=np.zeros_like(array), where=peak > 0) * 100
    return {"usd": float(dollars.max()), "percent": float(percent.max())}


def daily_cash_statistics(trades: list[dict], start: int, end: int, initial: float) -> dict:
    first = datetime.fromtimestamp(start, UTC).date()
    last = datetime.fromtimestamp(end - 1, UTC).date()
    cash_by_date = {}
    for trade in trades:
        day = datetime.fromtimestamp(trade["exit_epoch"], UTC).date()
        cash_by_date[day] = cash_by_date.get(day, 0.0) + trade["pnl_usd"]
    balance = initial
    curve = []
    returns = []
    day = first
    while day <= last:
        pnl = cash_by_date.get(day, 0.0)
        returns.append(pnl / balance if balance > 0 else math.nan)
        balance += pnl
        curve.append({"date": day.isoformat(), "pnl_usd": pnl, "balance_usd": balance})
        day += timedelta(days=1)
    array = np.asarray(returns, dtype=float)
    valid = bool(np.all(np.isfinite(array)))
    std = float(np.std(array, ddof=1)) if len(array) > 1 and valid else 0.0
    sharpe = float(np.mean(array) / std * math.sqrt(365)) if std > 0 else None
    return {"calendar_days": len(curve), "closed_cash_sharpe": sharpe, "daily_closed_curve": curve}


def load_source(config: dict) -> tuple[np.ndarray, dict]:
    path = BASE / config["relative_path"]
    digest = sha256(path)
    if digest != config["sha256"]:
        raise ValueError("Price archive differs from preregistered source: " + config["relative_path"])
    with np.load(path, allow_pickle=False) as archive:
        rates = archive["rates"].copy()
    required = {"time", "open", "high", "low", "close", "spread"}
    if not required.issubset(rates.dtype.names or ()):
        raise ValueError("Unexpected archived rates schema")
    times = rates["time"]
    if not len(rates) or not np.all(np.diff(times) > 0):
        raise ValueError("Source timestamps must be strictly increasing")
    if not np.all(np.isfinite(rates["open"])) or not np.all(rates["open"] > 0):
        raise ValueError("Invalid source opening price")
    step = config["timeframe_seconds"]
    differences = np.diff(times)
    metadata_path = BASE / config["metadata_relative_path"]
    metadata = {
        "relative_path": config["relative_path"], "sha256": digest,
        "metadata_relative_path": config["metadata_relative_path"], "metadata_sha256": sha256(metadata_path),
        "server": config["server"], "timeframe_seconds": step,
        "rows": len(rates), "first_utc": iso(times[0]), "last_bar_open_utc": iso(times[-1]),
        "gap_count": int(np.sum(differences > step)), "largest_gap_seconds": int(np.max(differences)),
        "zero_or_negative_spread_bars": int(np.sum(rates["spread"] <= 0)),
        "spread_points_median": float(np.median(rates["spread"])),
        "spread_points_p95": float(np.percentile(rates["spread"], 95)),
        "schema": [[name, str(rates.dtype[name])] for name in rates.dtype.names],
    }
    return rates, metadata


def analyze_window(
    rates: np.ndarray, start: int, end: int, *, initial: float = 10000.0,
    allocation: str = "cash", use_spread: bool = True, point: float = 0.01,
    step: int = 60, swap_charges: int = 0, swap_points: float = -1863.7,
    include_trades: bool = False,
) -> dict:
    times = rates["time"]
    balance = initial
    closed_balances = [initial]
    observed_peak = initial
    maximum_equity_dd_usd = maximum_equity_dd_pct = 0.0
    exposure_ratios = []
    trades, skipped = [], []
    for entry_epoch, exit_epoch in scheduled_weekends(start, end):
        if exit_epoch >= end:
            skipped.append({"entry_utc": iso(entry_epoch), "exit_utc": iso(exit_epoch), "reason": "exit outside completed requested window"})
            continue
        entry_index = exact_index(times, entry_epoch)
        exit_index = exact_index(times, exit_epoch)
        if entry_index is None or exit_index is None:
            skipped.append({"entry_utc": iso(entry_epoch), "exit_utc": iso(exit_epoch), "reason": "missing exact entry bar" if entry_index is None else "missing exact exit bar"})
            continue
        spread_points = int(rates["spread"][entry_index])
        if use_spread and spread_points <= 0:
            skipped.append({"entry_utc": iso(entry_epoch), "exit_utc": iso(exit_epoch), "reason": "nonpositive entry spread; no synthetic replacement"})
            continue
        entry_bid = float(rates["open"][entry_index])
        exit_bid = float(rates["open"][exit_index])
        entry_spread = spread_points * point if use_spread else 0.0
        entry_ask = entry_bid + entry_spread
        quantity = quantity_for_notional(balance, entry_ask, allocation, initial)
        notional = quantity * entry_ask
        exposure_ratios.append(notional / balance if balance > 0 else None)
        gross = quantity * (exit_bid - entry_bid)
        spread_cost = quantity * entry_spread
        financing = quantity * swap_points * point * swap_charges
        pnl = gross - spread_cost + financing
        before = balance
        marks = rates[entry_index:exit_index + 1]
        observed_equity = before + quantity * (marks["open"] - entry_ask)
        observed_equity[-1] += financing  # Sensitivities explicitly book assumed charges at exit.
        peaks = np.maximum.accumulate(np.concatenate(([observed_peak], observed_equity)))[1:]
        declines = peaks - observed_equity
        maximum_equity_dd_usd = max(maximum_equity_dd_usd, float(declines.max()))
        maximum_equity_dd_pct = max(maximum_equity_dd_pct, float(np.max(declines / peaks) * 100))
        observed_peak = max(observed_peak, float(observed_equity.max()))
        expected = (exit_epoch - entry_epoch) // step + 1
        missing = expected - len(marks)
        if missing < 0:
            raise ValueError("Unexpected off-grid or overcomplete price observations")
        balance += pnl
        closed_balances.append(balance)
        trades.append({
            "id": len(trades) + 1, "entry_epoch": entry_epoch, "exit_epoch": exit_epoch,
            "entry_utc": iso(entry_epoch), "exit_utc": iso(exit_epoch),
            "entry_new_york": datetime.fromtimestamp(entry_epoch, NY).isoformat(),
            "hold_hours": (exit_epoch - entry_epoch) / 3600,
            "entry_bid": entry_bid, "entry_ask_proxy": entry_ask, "exit_bid": exit_bid,
            "entry_spread_points": spread_points if use_spread else None,
            "quantity_btc": quantity, "entry_notional_usd": notional,
            "balance_before_usd": before, "balance_after_usd": balance,
            "gross_pnl_usd": gross, "entry_spread_cost_usd": spread_cost,
            "modeled_financing_usd": financing, "pnl_usd": pnl,
            "return_on_start_cash_pct": pnl / before * 100 if before > 0 else None,
            "observed_marks": len(marks), "missing_sample_bars": int(missing),
            "entry_delay_seconds": 0, "exit_delay_seconds": 0,
        })
    values = [trade["pnl_usd"] for trade in trades]
    positive = [value for value in values if value > 0]
    negative = [value for value in values if value < 0]
    max_wins, max_losses = streaks(values)
    daily = daily_cash_statistics(trades, start, end, initial)
    result = {
        "start_utc": iso(start), "end_exclusive_utc": iso(end),
        "allocation": allocation, "cost_basis": "bar-spread-only proxy" if use_spread else "gross, before all transaction costs",
        "swap_charges_per_weekend": swap_charges,
        "initial_balance_usd": initial, "ending_balance_usd": balance,
        "pnl_usd": balance - initial, "return_pct": (balance / initial - 1) * 100,
        "trades": len(values), "wins": len(positive), "losses": len(negative),
        "breakevens": len(values) - len(positive) - len(negative),
        "win_rate_pct": len(positive) / len(values) * 100 if values else None,
        "profit_factor": profit_factor(values), "profit_factor_note": "Undefined if no losing trades; never substituted with a finite value",
        "average_win_usd": sum(positive) / len(positive) if positive else None,
        "average_loss_usd": sum(negative) / len(negative) if negative else None,
        "max_win_streak": max_wins, "max_loss_streak": max_losses,
        "max_closed_drawdown": drawdown(closed_balances),
        "sampled_equity_drawdown": {"usd": maximum_equity_dd_usd, "percent": maximum_equity_dd_pct, "sampling_seconds": step},
        "total_gross_pnl_on_actual_quantities_usd": sum(trade["gross_pnl_usd"] for trade in trades),
        "total_entry_spread_cost_usd": sum(trade["entry_spread_cost_usd"] for trade in trades),
        "total_modeled_financing_usd": sum(trade["modeled_financing_usd"] for trade in trades),
        "maximum_entry_notional_to_equity": max((value for value in exposure_ratios if value is not None), default=None),
        "weekends_with_missing_interior_bars": sum(trade["missing_sample_bars"] > 0 for trade in trades),
        "missing_interior_sample_bars": sum(trade["missing_sample_bars"] for trade in trades),
        "skipped": skipped, "last_completed_exit_utc": trades[-1]["exit_utc"] if trades else None,
        **daily,
    }
    if include_trades:
        result["trade_ledger"] = trades
    return result


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def fmt(value, suffix="", digits=2):
    return "—" if value is None else f"{value:,.{digits}f}{suffix}"


def metrics_table(rows):
    text = '<table><thead><tr><th>Window / basis</th><th>Trades</th><th>Return</th><th>P&amp;L</th><th>Win rate</th><th>PF</th><th>Win/loss streak</th><th>Closed DD</th><th>Sampled equity DD</th><th>Daily cash Sharpe</th></tr></thead><tbody>'
    for label, row in rows:
        text += f'<tr><td>{escape(label)}</td><td>{row["trades"]}</td><td>{fmt(row["return_pct"], "%")}</td><td>${fmt(row["pnl_usd"])}</td><td>{fmt(row["win_rate_pct"], "%")}</td><td>{fmt(row["profit_factor"])}</td><td>{row["max_win_streak"]} / {row["max_loss_streak"]}</td><td>{fmt(row["max_closed_drawdown"]["percent"], "%")}</td><td>{fmt(row["sampled_equity_drawdown"]["percent"], "%")}</td><td>{fmt(row["closed_cash_sharpe"])}</td></tr>'
    return text + '</tbody></table>'


def ledger_table(trades):
    text = '<table><thead><tr><th>Entry UTC</th><th>Exit UTC</th><th>Hours</th><th>Buy ask proxy</th><th>Sell bid</th><th>BTC</th><th>Gross P&amp;L</th><th>Spread cost</th><th>Spread-only P&amp;L</th><th>Balance</th><th>Missing M1 marks</th></tr></thead><tbody>'
    for trade in trades:
        text += '<tr>' + ''.join(f'<td>{value}</td>' for value in (
            escape(trade["entry_utc"]), escape(trade["exit_utc"]), fmt(trade["hold_hours"], digits=0),
            fmt(trade["entry_ask_proxy"]), fmt(trade["exit_bid"]), fmt(trade["quantity_btc"], digits=6),
            fmt(trade["gross_pnl_usd"]), fmt(trade["entry_spread_cost_usd"]), fmt(trade["pnl_usd"]),
            fmt(trade["balance_after_usd"]), str(trade["missing_sample_bars"]),
        )) + '</tr>'
    return text + '</tbody></table>'


def make_report(results: dict, protocol: dict):
    recent = results["recent"]
    full = recent["full_recent"]["spread_only"]
    window_rows = []
    for name, values in recent.items():
        window_rows += [(name + " · spread-only proxy", values["spread_only"]), (name + " · gross independent counterfactual", values["gross"])]
    sensitivity_rows = [(f'{charges} assumed swap charges/weekend', row) for charges, row in results["financing_sensitivity"].items()]
    fixed = results["fixed_initial_notional_reference"]
    long = results["long_m5_gross"]
    sources = ''.join(f'<li>{escape(source["relative_path"])}<br>{source["rows"]:,} bars · {escape(source["first_utc"])} → {escape(source["last_bar_open_utc"])} · {escape(source["server"])}<br>SHA256: <code>{source["sha256"]}</code></li>' for source in results["sources"])
    page = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>BTC weekend hold · raw research</title>
<style>body{{background:#081712;color:#e9f5ee;font:16px system-ui;margin:0}}main{{max-width:1400px;margin:auto;padding:28px}}h1,h2{{color:#82f5c3}}a{{color:#80ebda}}p,li{{line-height:1.6}}.notice{{border:1px solid #ad8d37;padding:16px;background:#2b2513}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse;font-size:14px;margin:18px 0}}th,td{{text-align:right;padding:10px;border-bottom:1px solid #294139;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}code{{overflow-wrap:anywhere}}small{{color:#b8c8c0}}</style>
<main><p>RAW RESEARCH · NO OPTIMIZATION · NO EA OR ACCOUNT CHANGES</p><h1>Buy BTC Friday evening, sell Sunday evening</h1>
<p>Buy at Friday <b>17:00 New York</b>; sell at Sunday <b>17:00 New York</b>. The two local clocks are converted independently, so DST weekends last 47 or 49 hours. BTC trades continuously; these are the conventional FX-weekend boundaries, not a BTC market reopening.</p>
<div class="notice">Headline: start with $10,000 and allocate <b>100% of current cash</b> each weekend, with fractional BTC and no borrowing. <b>No stop loss</b>: this is not 1% or 0.5% stop-risk sizing. Loss can be substantial. Results below include a recorded-bar spread proxy, <b>not verified all-in costs</b>.</div>
<p>Archive cutoff: {escape(results["recent_end_exclusive_utc"])}. Last completed exit: {escape(full["last_completed_exit_utc"] or "none")}. The current October 16–18 weekend is not complete and is not tested. Entry and exit must have the exact scheduled bar; no late fills, interpolation or replacement candles.</p>
<h2>Recent M1 results</h2><p>Each window starts a fresh $10,000 account. The gross row is a separate cost-free, cash-compounding counterfactual; it is not the same quantity path as spread-only. The detailed spread-only ledger separately reconciles gross cash minus recorded entry-spread cost.</p><div class="scroll">{metrics_table(window_rows)}</div>
<h2>Financing sensitivity, full recent period</h2><p>Archived current swap: −1863.7 points per BTC lot × $0.01 = −$18.637 per BTC per charge. The 0/3/4-charge cases are assumptions, booked at exit; historical rates, account exemptions and rollover ordering are not known. These are not measured historical swap bills. No commission or slippage is added.</p><div class="scroll">{metrics_table(sensitivity_rows)}</div>
<h2>Fixed initial $10,000 notional reference</h2><p>This secondary comparison keeps each purchase at $10,000 rather than current cash. Its maximum entry notional/equity ratio was {fmt(fixed["maximum_entry_notional_to_equity"], "×", 4)}. If that ratio exceeds 1× after losses, it requires financing or additional capital and is <b>not claimed unlevered executable performance</b>.</p><div class="scroll">{metrics_table([("Fixed $10k notional · spread-only reference", fixed)])}</div>
<h2>Separate longer M5 descriptive check</h2><p>Different archived server (Trial16), never stitched into Trial15 M1. {long["trades"]} weekends traded; {len(long["skipped"])} skipped. This panel is <b>gross before all costs</b>: old zero-spread bars do not provide a defensible measured-cost reconstruction.</p><div class="scroll">{metrics_table([("2022 → Aug 2026 · gross M5", long)])}</div>
<h2>Every recent spread-only trade</h2><p>All {full["trades"]} completed weekends; {full["weekends_with_missing_interior_bars"]} contain missing interior M1 bars ({full["missing_interior_sample_bars"]} missing marks). Endpoint returns remain observed; sampled drawdown can miss intraminute moves and missing intervals.</p><div class="scroll">{ledger_table(full["trade_ledger"])}</div>
<h2>Definitions and limitations</h2><ul>
<li>Entry ask proxy = scheduled bid bar open + its recorded spread points × $0.01. Exit = scheduled bid bar open. A bar's spread is not a timestamp-matched opening ask quote; this is not a tick-fill backtest.</li>
<li>PF = sum positive completed-trade P&amp;L ÷ absolute sum negative P&amp;L; undefined if there is no loss. Win rate uses positive P&amp;L / all completed trades. A zero resets both streaks.</li>
<li>Closed DD uses the chronological closed-cash balance, including the starting balance. Sampled equity DD uses every available M1 bid OPEN while held (M5 in the long panel), plus initial cash; it is not true tick or intrabar equity DD. USD and percentage maxima are independent maxima.</li>
<li>Daily cash Sharpe uses all UTC calendar dates, including zero-trade days: mean(realized daily P&amp;L / prior closed balance) ÷ sample standard deviation × √365. It excludes unrealized daily returns and is not an annual-return forecast.</li>
<li>Fractional BTC is a research reference: broker lot minimums, lot steps, leverage and margin, liquidity, slippage, commissions and historical financing are not verified. No profit target, risk optimization, live installation or order execution.</li>
<li>One weekend rule tested as specified, with no timing search. The longer record is descriptive, not untouched proof; overlapping recent windows are not independent tests.</li></ul>
<h2>Source receipts</h2><ul>{sources}</ul>
<p><a href="{escape(protocol["official_broker_reference"], quote=True)}">Exness cryptocurrency trading and financing reference</a> · <a href="PROTOCOL.json">Frozen rules</a> · <a href="FROZEN.json">Input hashes before execution</a> · <a href="RESULTS.json">All metrics and trade ledgers</a> · <a href="VERIFICATION.json">Accounting and coverage checks</a></p></main></html>'''
    (ROOT / "Results.html").write_text(page, encoding="utf-8")


def main():
    protocol_path = ROOT / "PROTOCOL.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    recent_rates, recent_metadata = load_source(protocol["recent_source"])
    long_rates, long_metadata = load_source(protocol["long_source"])
    end = int(datetime.fromisoformat(protocol["recent_end"]).timestamp())
    long_end = int(datetime.fromisoformat(protocol["long_end"]).timestamp())
    if end > int(recent_rates["time"][-1]) + 60 or long_end > int(long_rates["time"][-1]) + 300:
        raise ValueError("Requested period exceeds archived coverage")
    frozen = {
        "frozen_at_utc": datetime.now(UTC).isoformat(), "before_outcomes": True,
        "files": {"PROTOCOL.json": sha256(protocol_path), "run.py": sha256(Path(__file__)), "test_weekend.py": sha256(ROOT / "test_weekend.py")},
        "sources": [recent_metadata, long_metadata],
        "execution": "Offline NumPy only; no MT5, network, subprocesses, live charts, trading, or package changes",
    }
    write_json(ROOT / "FROZEN.json", frozen)
    initial = float(protocol["initial_balance_usd"])
    common = dict(initial=initial, point=protocol["point_usd"], swap_points=protocol["archived_swap_long_points_per_lot"])
    end_time = datetime.fromtimestamp(end, UTC)
    starts = {f"{months}m" if months < 12 else "1y": int(month_offset(end_time, -months).timestamp()) for months in protocol["recent_calendar_month_windows"]}
    starts["full_recent"] = int(recent_rates["time"][0])
    recent = {}
    for name, start in starts.items():
        recent[name] = {
            "spread_only": analyze_window(recent_rates, start, end, **common, include_trades=name == "full_recent"),
            "gross": analyze_window(recent_rates, start, end, **common, use_spread=False),
        }
    full_start = starts["full_recent"]
    financing = {str(charges): analyze_window(recent_rates, full_start, end, **common, swap_charges=charges) for charges in protocol["modeled_swap_charges_per_weekend"]}
    fixed = analyze_window(recent_rates, full_start, end, **common, allocation="fixed_reference")
    long = analyze_window(long_rates, int(long_rates["time"][0]), long_end, **common, use_spread=False, step=300, include_trades=True)
    results = {
        "generated_at_utc": datetime.now(UTC).isoformat(), "protocol_version": protocol["version"],
        "research_only": True, "recent_end_exclusive_utc": iso(end),
        "sources": [recent_metadata, long_metadata], "recent": recent,
        "financing_sensitivity": financing, "fixed_initial_notional_reference": fixed,
        "long_m5_gross": long,
        "formulas": {
            "headline_quantity": "current closed cash / (scheduled bid OPEN + recorded entry bar spread * 0.01)",
            "headline_pnl": "quantity * (exit bid OPEN - entry ask proxy)",
            "financing_sensitivity": "headline PnL + quantity * (-1863.7) * 0.01 * assumed charge count, then next weekend resized from resulting cash",
            "gross_counterfactual": "independent cash-funded account: quantity=current balance / entry bid OPEN, PnL=quantity*(exit bid OPEN-entry bid OPEN)",
            "closed_drawdown": "peak-to-trough of starting and completed-position cash balances",
            "sampled_equity_drawdown": "peak-to-trough of all observed held-position bar OPEN NAV and initial cash; neither ticks nor intrabar extremes",
            "daily_cash_sharpe": "mean(all UTC-calendar daily realized PnL / prior closed cash) / sample std * sqrt(365)",
        },
    }
    verification_checks = {}
    panels = [values[basis] for values in recent.values() for basis in ("spread_only", "gross")] + list(financing.values()) + [fixed, long]
    for index, panel in enumerate(panels):
        verification_checks[f"panel_{index}_cash_reconciles"] = math.isclose(sum(row["pnl_usd"] for row in panel["daily_closed_curve"]), panel["pnl_usd"], abs_tol=1e-8)
        verification_checks[f"panel_{index}_cash_components_reconcile"] = math.isclose(panel["total_gross_pnl_on_actual_quantities_usd"] - panel["total_entry_spread_cost_usd"] + panel["total_modeled_financing_usd"], panel["pnl_usd"], abs_tol=1e-8)
        verification_checks[f"panel_{index}_wins_losses_match_count"] = panel["wins"] + panel["losses"] + panel["breakevens"] == panel["trades"]
    for name, values in recent.items():
        verification_checks[name + "_cash_allocation_is_one_times"] = math.isclose(values["spread_only"]["maximum_entry_notional_to_equity"], 1.0, abs_tol=1e-12)
    ledger = recent["full_recent"]["spread_only"]["trade_ledger"]
    verification_checks["all_recent_exact_clock_fills"] = all(row["entry_delay_seconds"] == row["exit_delay_seconds"] == 0 for row in ledger)
    verification_checks["no_stop_loss_or_risk_percent"] = protocol["stop_loss"] is None and protocol["stop_risk_percent"] is None
    verification_checks["dst_holds_include_47_48_49_hours"] = {row["hold_hours"] for row in ledger} == {47.0, 48.0, 49.0}
    verification_checks["financing_zero_matches_spread_headline"] = math.isclose(financing["0"]["pnl_usd"], recent["full_recent"]["spread_only"]["pnl_usd"], abs_tol=1e-8)
    verification_checks["sources_unchanged_after_analysis"] = all(sha256(BASE / source["relative_path"]) == source["sha256"] for source in results["sources"])
    verification = {"status": "PASS" if all(verification_checks.values()) else "FAIL", "checks": verification_checks, "results_sha256": None}
    if verification["status"] != "PASS":
        raise AssertionError(verification)
    write_json(ROOT / "RESULTS.json", results)
    verification["results_sha256"] = sha256(ROOT / "RESULTS.json")
    write_json(ROOT / "VERIFICATION.json", verification)
    make_report(results, protocol)
    for name, values in recent.items():
        row = values["spread_only"]
        print(json.dumps({"window": name, "trades": row["trades"], "return_pct": row["return_pct"], "win_rate_pct": row["win_rate_pct"], "pf": row["profit_factor"], "closed_dd_pct": row["max_closed_drawdown"]["percent"], "sampled_equity_dd_pct": row["sampled_equity_drawdown"]["percent"]}))
    print("PASS: fixed offline weekend study; no live account accessed.")


if __name__ == "__main__":
    main()
