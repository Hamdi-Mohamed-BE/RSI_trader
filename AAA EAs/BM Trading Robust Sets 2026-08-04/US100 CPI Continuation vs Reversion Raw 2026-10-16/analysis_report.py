"""Reconcile frozen native CPI cases and render a self-contained research report.

This module never connects to MT5, downloads data, tunes a parameter, or changes
an installer. Run only after the isolated native replay has written RESULTS.json.
The local checks below are not independent validation of the strategy or data.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv
import gzip
import hashlib
import html
import io
import json
import math
import statistics

ROOT = Path(__file__).resolve().parent
UTC = timezone.utc
NATIVE = ROOT / "native" / "cpi-raw-20261016"
MODE_NAMES = {0: "Continuation · 1.5R", 1: "Reversion · anchor, ≥1.5R", 2: "Reversion · anchor diagnostic, no minimum R"}
EXIT_NAMES = {0: "Client", 1: "Mobile", 2: "Web", 3: "Expert/time close", 4: "SL", 5: "TP", 6: "Stop-out", 7: "Rollover", 8: "Variation margin", 9: "Split", 10: "Corporate action"}
ENTRY_REASONS = {"entry_continuation", "entry_fade_min1_5R", "entry_fade_anchor_diagnostic"}
NON_TERMINAL = {"event_start", "event_end", "pre_event_reference_confirmed", "impulse_confirmed", "time_close", "time_close_rejected"}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False, ensure_ascii=False), encoding="utf-8")


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def number(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (ValueError, TypeError):
        return default


def epoch(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp())


def iso(value):
    return datetime.fromtimestamp(number(value), UTC).isoformat().replace("+00:00", "Z")


def read_csv(path):
    # Native FILE_ANSI uses UTF-8-compatible ASCII headers/numeric data here.
    if not path.exists():
        return []
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    text = raw.decode("utf-8-sig", errors="replace")
    if "\x00" in text:
        text = raw.decode("utf-16")
    return list(csv.DictReader(io.StringIO(text)))


def case_name(row):
    return MODE_NAMES[int(row["parameters"]["mode"])]


def policy_name(row):
    return "Positive-spread entry guard" if row["parameters"].get("require_positive_spread") else "Archive reference · zero spreads retained"


def wilson(wins, count):
    if not count:
        return None
    z = 1.959963984540054
    p = wins / count
    d = 1 + z * z / count
    middle = (p + z * z / (2 * count)) / d
    radius = z * math.sqrt(p * (1 - p) / count + z * z / (4 * count * count)) / d
    return [100 * max(0.0, middle - radius), 100 * min(1.0, middle + radius)]


def streaks(profits):
    best_win = best_loss = win = loss = 0
    for profit in profits:
        win = win + 1 if profit > 0 else 0
        loss = loss + 1 if profit < 0 else 0
        best_win, best_loss = max(best_win, win), max(best_loss, loss)
    return best_win, best_loss


def period_metrics(trades, start, end, deposit=10000.0):
    """Chronological closed-cash metrics; no artificial reset at a subwindow."""
    start_epoch, end_epoch = epoch(start), epoch(end)
    ordered = sorted(trades, key=lambda t: (number(t["close_epoch"]), number(t.get("position_id"))))
    before = sum(number(t["net_profit"]) for t in ordered if number(t["close_epoch"]) < start_epoch)
    initial = deposit + before
    chosen = [t for t in ordered if start_epoch <= number(t["close_epoch"]) < end_epoch]
    profits = [number(t["net_profit"]) for t in chosen]
    net = sum(profits)
    gross_win = sum(max(0, p) for p in profits)
    gross_loss = -sum(min(0, p) for p in profits)
    wins, losses = sum(p > 0 for p in profits), sum(p < 0 for p in profits)
    win_streak, loss_streak = streaks(profits)
    cash, peak, max_dd_cash, max_dd_pct = initial, initial, 0.0, 0.0
    day_cash = defaultdict(float)
    daily_peak = initial
    current_day = None
    max_daily_cash = max_daily_pct = 0.0
    curve = [[start_epoch, initial]]
    for trade in chosen:
        day = datetime.fromtimestamp(number(trade["close_epoch"]), UTC).date().isoformat()
        if day != current_day:
            daily_peak, current_day = cash, day
        value = number(trade["net_profit"])
        curve.append([int(number(trade["close_epoch"])), cash])
        cash += value
        day_cash[day] += value
        peak, daily_peak = max(peak, cash), max(daily_peak, cash)
        max_dd_cash = max(max_dd_cash, peak - cash)
        max_dd_pct = max(max_dd_pct, 100 * (peak - cash) / peak if peak > 0 else 0)
        max_daily_cash = max(max_daily_cash, daily_peak - cash)
        max_daily_pct = max(max_daily_pct, 100 * (daily_peak - cash) / daily_peak if daily_peak > 0 else 0)
        curve.append([int(number(trade["close_epoch"])), cash])
    curve.append([end_epoch, cash])
    date = datetime.fromisoformat(start).date()
    stop = datetime.fromisoformat(end).date()
    daily_returns, previous = [], initial
    while date < stop:
        value = day_cash[date.isoformat()]
        daily_returns.append(value / previous if previous > 0 else 0.0)
        previous += value
        date += timedelta(days=1)
    sd = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
    sharpe = statistics.mean(daily_returns) / sd * math.sqrt(365) if sd > 0 else None
    entry_rr = []
    for trade in chosen:
        risk = abs(number(trade["open_price"]) - number(trade.get("initial_sl")))
        reward = abs(number(trade.get("initial_tp")) - number(trade["open_price"]))
        if risk > 0:
            entry_rr.append(reward / risk)
    return {
        "start": start, "end_exclusive": end, "starting_balance": initial, "ending_balance": initial + net,
        "trades": len(chosen), "wins": wins, "losses": losses, "breakeven": len(chosen) - wins - losses,
        "net": net, "return_pct": net / initial * 100 if initial > 0 else None,
        "pf": gross_win / gross_loss if gross_loss > 0 else None,
        "pf_status": "finite" if gross_loss > 0 else ("no_losses" if wins else "no_trades_or_no_profit"),
        "win_rate_pct": 100 * wins / len(chosen) if chosen else None,
        "win_rate_wilson_95_pct": wilson(wins, len(chosen)),
        "closed_dd_pct": max_dd_pct if chosen else 0.0, "closed_dd_cash": max_dd_cash,
        "max_daily_closed_dd_cash": max_daily_cash, "max_daily_closed_dd_pct": max_daily_pct,
        "daily_closed_balance_sharpe_sqrt365": sharpe,
        "max_win_streak": win_streak, "max_loss_streak": loss_streak,
        "average_trade": net / len(chosen) if chosen else None,
        "average_win": gross_win / wins if wins else None, "average_loss": -gross_loss / losses if losses else None,
        "mean_filled_entry_reward_risk": statistics.mean(entry_rr) if entry_rr else None,
        "min_filled_entry_reward_risk": min(entry_rr) if entry_rr else None,
        "max_filled_entry_reward_risk": max(entry_rr) if entry_rr else None,
        "calendar_days": len(daily_returns), "curve": curve,
    }


def audit_case(row, calendar):
    index = int(row["index"])
    decisions = read_csv(NATIVE / f"{index}-decisions.csv.gz")
    quotes = read_csv(NATIVE / f"{index}-quotes.csv.gz")
    deals = read_csv(NATIVE / f"{index}-deals.csv.gz")
    equity = read_csv(NATIVE / f"{index}-equity.csv.gz")
    event_epochs = sorted(int(e["epoch"]) for e in calendar["events"])
    entries = [d for d in decisions if d.get("reason") in ENTRY_REASONS]
    matched, unmatched, assigned = [], [], set()
    events = defaultdict(list)
    for decision in decisions:
        events[int(number(decision.get("event_epoch")))].append(decision)
    trades = sorted(row.get("trades", []), key=lambda t: (number(t["open_epoch"]), number(t.get("position_id"))))
    trade_events = Counter()
    enriched = []
    for trade in trades:
        t = dict(trade)
        opened = number(t["open_epoch"])
        prior = [e for e in event_epochs if e <= opened < e + 3600]
        event = prior[-1] if prior else None
        if event is not None:
            trade_events[event] += 1
        candidates = [(abs(number(d.get("epoch")) - opened), n, d) for n, d in enumerate(entries)
                      if n not in assigned and int(number(d.get("event_epoch"))) == event
                      and abs(number(d.get("epoch")) - opened) <= 5]
        decision = min(candidates, default=None, key=lambda x: (x[0], x[1]))
        if decision is None:
            unmatched.append(t.get("position_id", len(enriched)))
        else:
            _, entry_index, d = decision
            assigned.add(entry_index)
            budget, planned_cash = number(d.get("risk_budget")), number(d.get("unit_loss")) * number(d.get("lots"))
            filled_stop = abs(number(t["open_price"]) - number(t.get("initial_sl")))
            direction = 1 if t["side"] == "buy" else -1
            request_entry = number(d.get("request_ask" if direction > 0 else "request_bid"),
                                   number(d.get("ask" if direction > 0 else "bid")))
            request_stop = abs(request_entry - number(d.get("sl")))
            filled_risk_cash = planned_cash * filled_stop / request_stop if request_stop > 0 else None
            t.update(event_epoch=event, decision_epoch=int(number(d.get("epoch"))), risk_budget=budget,
                     planned_stop_risk_cash=planned_cash, filled_initial_stop_risk_cash=filled_risk_cash,
                     net_r_at_filled_initial_stop=(number(t["net_profit"]) / filled_risk_cash if filled_risk_cash and filled_risk_cash > 0 else None),
                     request_bid=number(d.get("request_bid"), number(d.get("bid"))),
                     request_ask=number(d.get("request_ask"), number(d.get("ask"))),
                     pre_atr=number(d.get("pre_atr")), anchor=number(d.get("fair")),
                     entry_decision_reason=d["reason"], net_over_budget_pct=100 * number(t["net_profit"]) / budget if budget > 0 else None)
            matched.append({"position_id": t.get("position_id"), "event_epoch": event,
                            "decision_epoch": int(number(d.get("epoch"))), "fill_epoch": opened,
                            "fill_minus_decision_seconds": opened - number(d.get("epoch")),
                            "planned_stop_risk_cash": planned_cash, "risk_budget": budget,
                            "filled_initial_stop_risk_cash": filled_risk_cash})
        t.setdefault("event_epoch", event)
        enriched.append(t)
    closed_order = sorted(enriched, key=lambda t: (number(t["close_epoch"]), number(t.get("position_id"))))
    invalid_stops = [t.get("position_id") for t in trades if (number(t["open_price"]) - number(t.get("initial_sl"))) * (1 if t["side"] == "buy" else -1) <= 0]
    invalid_targets = [t.get("position_id") for t in trades if (number(t.get("initial_tp")) - number(t["open_price"])) * (1 if t["side"] == "buy" else -1) <= 0]
    causal_fail = [t.get("position_id") for t in enriched if t["event_epoch"] is None or number(t["open_epoch"]) < t["event_epoch"] + 60]
    cash = sum(number(t["net_profit"]) for t in trades)
    deal_cash = sum(number(d.get(k)) for d in deals for k in ("profit", "commission", "swap", "fee"))
    native = row.get("native", {})
    tolerance = max(0.051, len(trades) * 0.001)
    zero_request = sum(number(t.get("request_ask")) == number(t.get("request_bid")) for t in enriched if "request_bid" in t)
    zero_roundtrip = sum(number(q.get("bid")) == number(q.get("ask")) for q in quotes)
    quote_audit = {
        "all_entry_exit_quote_callbacks": len(quotes), "zero_spread_callbacks": zero_roundtrip,
        "positive_spread_callbacks": sum(number(q.get("ask")) > number(q.get("bid")) for q in quotes),
        "invalid_or_negative_spread_callbacks": sum(number(q.get("bid")) <= 0 or number(q.get("ask")) < number(q.get("bid")) for q in quotes),
        "spread_cash_unavailable_callbacks": sum(number(q.get("spread_cash")) < 0 for q in quotes),
        "matched_entry_request_zero_spread": zero_request,
        "matched_entry_request_positive_spread": sum(number(t.get("request_ask")) > number(t.get("request_bid")) for t in enriched if "request_bid" in t),
        "note": "Quote callbacks include both entry and exit deals; zero bid/ask spread is not proof of free executable liquidity. Quote spread_cash is descriptive, not an extra charge to already-native P&L.",
    }
    status = []
    by_event = defaultdict(list)
    for t in enriched:
        by_event[t["event_epoch"]].append(t)
    for event in calendar["events"]:
        e = int(event["epoch"])
        ds = events[e]
        ts = by_event[e]
        terminal = [d for d in ds if d.get("reason") not in NON_TERMINAL and d.get("reason") not in ENTRY_REASONS]
        reason = "trade_closed" if ts else (terminal[-1]["reason"] if terminal else ("event_started_no_final_decision" if ds else "no_event_callback"))
        if not ts and any(d.get("reason") == "entry_rejected" for d in ds):
            reason = "entry_rejected"
        status.append({"event_epoch": e, "release_utc": event.get("release_utc", iso(e)),
                       "release_ny": event.get("release_ny"), "status": reason, "trades": len(ts),
                       "net": sum(number(t["net_profit"]) for t in ts),
                       "sides": [t["side"] for t in ts], "position_ids": [t.get("position_id") for t in ts],
                       "decision_reasons": [d.get("reason") for d in ds]})
    checks = {
        "all_trades_match_successful_entry_decision": not unmatched and len(entries) == len(trades),
        "native_money_reconciles": abs(cash - number(native.get("net"))) <= tolerance,
        "deal_money_reconciles": abs(cash - deal_cash) <= tolerance,
        "balance_reconciles": abs(number(native.get("balance")) - 10000 - cash) <= tolerance,
        "native_trade_count_reconciles": len(trades) == int(number(native.get("trades"))),
        "no_open_native_position": not number(native.get("open_position")),
        "positive_initial_stop_distances": not invalid_stops,
        "positive_initial_target_distances": not invalid_targets,
        "one_trade_per_event": max(trade_events.values(), default=0) <= 1,
        "entry_after_first_release_minute": not causal_fail,
        "all_trades_inside_study_boundaries": all(epoch(row["start"]) <= number(t["open_epoch"]) < epoch(row["end"]) for t in trades),
        "positive_guard_has_no_zero_spread_matched_entry": not row["parameters"].get("require_positive_spread") or zero_request == 0,
    }
    if entries:
        checks["planned_cash_not_above_risk_budget"] = all(number(m["planned_stop_risk_cash"]) <= number(m["risk_budget"]) + 1e-5 and number(m["planned_stop_risk_cash"]) > 0 for m in matched)
    return {
        "index": index, "checks": checks, "checks_all_pass": all(checks.values()),
        "interpretation": "Local accounting/causality checks only; not an independent review, proof of genuine real ticks, or strategy approval.",
        "matched_entries": matched, "unmatched_position_ids": unmatched,
        "unmatched_successful_entry_decisions": len(entries) - len(assigned),
        "invalid_stop_position_ids": invalid_stops, "invalid_target_position_ids": invalid_targets,
        "causality_failure_position_ids": causal_fail,
        "cash_reconciliation": {"trades_net": cash, "deals_net": deal_cash, "native_net": number(native.get("net")), "tolerance": tolerance},
        "quote_audit": quote_audit, "decision_reason_counts": dict(Counter(d.get("reason", "") for d in decisions)),
        "event_status_counts": dict(Counter(s["status"] for s in status)), "events": status,
        "trades": closed_order, "equity_snapshot_rows": len(equity),
        "native_full_period_floating_dd_pct": number(native.get("equity_dd")),
        "native_failed_entries": int(number(native.get("failed_entries"))),
        "native_failed_updates": int(number(native.get("failed_updates"))),
    }


def date_windows(cfg):
    end = cfg["end_exclusive"]
    last = datetime.fromisoformat(end).date()
    def months_ago(count):
        absolute = last.year * 12 + last.month - 1 - count
        y, m = divmod(absolute, 12)
        first_next = datetime(y + (m == 11), (m + 1) % 12 + 1, 1).date()
        max_day = (first_next - timedelta(days=1)).day
        return last.replace(year=y, month=m + 1, day=min(last.day, max_day)).isoformat()
    windows = [
        ("all", "Full archive", cfg["start"], end),
        ("development", "Development segment", cfg["start"], cfg["development_end_exclusive"]),
        ("validation", "Validation segment", cfg["development_end_exclusive"], cfg["validation_end_exclusive"]),
        ("oos", "Latest two-year retrospective evaluation", cfg["oos_start"], end),
        ("3y", "Last 3 years", months_ago(36), end),
        ("1y", "Last 1 year", months_ago(12), end),
        ("6m", "Last 6 months", months_ago(6), end),
        ("3m", "Last 3 months", months_ago(3), end),
    ]
    windows += [(str(year), str(year) + (" · partial through 15 October" if year == last.year else ""),
                 f"{year}-01-01", min(f"{year + 1}-01-01", end)) for year in range(2020, last.year + 1)]
    return windows


def h(value):
    return html.escape(str(value), quote=True)


def fmt(value, places=2, signed=False, suffix=""):
    if value is None:
        return "—"
    return f"{value:+,.{places}f}{suffix}" if signed else f"{value:,.{places}f}{suffix}"


def pf_fmt(metrics):
    if metrics["pf"] is not None:
        return fmt(metrics["pf"])
    return "∞ · no losses" if metrics["pf_status"] == "no_losses" else "—"


def chart(curve, title, color="#65ebbd", width=860, height=190):
    left, right, top, bottom = 62, 14, 18, 28
    xs, ys = [p[0] for p in curve], [p[1] for p in curve]
    xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
    padding = max(1.0, (ymax - ymin) * .1)
    ymin, ymax = ymin - padding, ymax + padding
    def coord(x, y):
        return left + (x-xmin) / max(1, xmax-xmin) * (width-left-right), top + (ymax-y) / (ymax-ymin) * (height-top-bottom)
    points = " ".join(f"{coord(x,y)[0]:.2f},{coord(x,y)[1]:.2f}" for x,y in curve)
    lines = []
    for fraction in (0, .5, 1):
        value = ymin + (ymax-ymin)*fraction
        _, y = coord(xmin, value)
        lines.append(f'<line x1="{left}" x2="{width-right}" y1="{y:.1f}" y2="{y:.1f}" stroke="#26453b"/><text x="{left-8}" y="{y+4:.1f}" text-anchor="end">${value:,.0f}</text>')
    first, last = datetime.fromtimestamp(xmin, UTC).strftime("%Y-%m-%d"), datetime.fromtimestamp(xmax, UTC).strftime("%Y-%m-%d")
    return f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{h(title)}"><title>{h(title)}</title>{"".join(lines)}<polyline fill="none" stroke="{color}" stroke-width="2.4" points="{points}"/><text x="{left}" y="{height-6}">{first}</text><text x="{width-right}" y="{height-6}" text-anchor="end">{last} exclusive</text></svg>'


def metric_table(cases, period_key):
    rows = []
    for case in cases:
        m = case["periods"][period_key]
        ci = m["win_rate_wilson_95_pct"]
        ci_text = f'{ci[0]:.1f}–{ci[1]:.1f}%' if ci else "—"
        tone = "positive" if m["net"] > 0 else "negative" if m["net"] < 0 else ""
        rows.append(f'<tr><td><a href="#case-{case["index"]}">{h(case["name"])}</a><small>{h(case["policy"])}</small></td>'
                    f'<td>{m["trades"]}</td><td>{fmt(m["win_rate_pct"],1,suffix="%")}<small>95% CI {ci_text}</small></td>'
                    f'<td>{pf_fmt(m)}</td><td class="{tone}">{fmt(m["return_pct"],2,True,"%")}</td>'
                    f'<td class="{tone}">${fmt(m["net"],2,True)}</td><td>{fmt(m["closed_dd_pct"],2,suffix="%")}</td>'
                    f'<td>{fmt(m["daily_closed_balance_sharpe_sqrt365"])}</td><td>{m["max_win_streak"]} / {m["max_loss_streak"]}</td>'
                    f'<td>${fmt(m["average_trade"])}</td></tr>')
    return '<div class="scroll"><table><thead><tr><th>Frozen model / quote policy</th><th>Trades</th><th>Win rate</th><th>PF</th><th>Return</th><th>Net</th><th>Closed DD</th><th>Sharpe</th><th>Win / loss streak</th><th>Avg trade</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'


def trade_table(case):
    rows = []
    for t in case["trades"]:
        risk = abs(number(t["open_price"]) - number(t["initial_sl"]))
        target_r = abs(number(t["initial_tp"]) - number(t["open_price"])) / risk if risk > 0 else None
        hold = (number(t["close_epoch"]) - number(t["open_epoch"])) / 60
        direction = "Long" if t["side"] == "buy" else "Short"
        exit_reason = EXIT_NAMES.get(int(number(t.get("exit_reason"))), str(t.get("exit_reason")))
        rows.append(f'<tr><td>{h(iso(t["open_epoch"]))}<small>Closed {h(iso(t["close_epoch"]))} · {hold:.2f} min</small></td>'
                    f'<td>{direction}<small>{fmt(t["volume"],2)} lots</small></td><td>{fmt(t["open_price"],3)}</td><td>{fmt(t["initial_sl"],3)}</td>'
                    f'<td>{fmt(t["initial_tp"],3)}</td><td>{fmt(t["close_price"],3)}</td><td>{h(exit_reason)}</td><td>{fmt(target_r,3)}R</td>'
                    f'<td>${fmt(t["net_profit"],2,True)}<small>Commission ${fmt(t.get("commission"))}; swap ${fmt(t.get("swap"))}; fee ${fmt(t.get("fee"))}</small></td>'
                    f'<td>{fmt(t.get("net_r_at_filled_initial_stop"),3,True)}R<small>Filled-stop estimate ${fmt(t.get("filled_initial_stop_risk_cash"))}</small></td>'
                    f'<td>${fmt(t.get("risk_budget"))}<small>Net / budget {fmt(t.get("net_over_budget_pct"),1,True,"%")}</small></td></tr>')
    if not rows:
        rows = ['<tr><td colspan="11">No completed trades. See event/skip diagnostics; no-trade results are not a directional win-rate test.</td></tr>']
    return '<div class="scroll"><table><thead><tr><th>UTC entry / exit</th><th>Side / size</th><th>Entry</th><th>Initial SL</th><th>Initial TP</th><th>Exit</th><th>Reason</th><th>Entry target R</th><th>Net cash</th><th>Realized net R</th><th>Risk budget</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'


def event_table(cases, calendar):
    lookup = {c["index"]: {e["event_epoch"]: e for e in c["events"]} for c in cases}
    rows = []
    for event in reversed(calendar["events"]):
        cells = []
        for case in cases:
            entry = lookup[case["index"]][int(event["epoch"]) ]
            if entry["trades"]:
                cells.append(f'<td class="{ "positive" if entry["net"] > 0 else "negative" }">{h(" / ".join(entry["sides"]))} · ${fmt(entry["net"],2,True)}<small>{entry["trades"]} closed trade</small></td>')
            else:
                cells.append(f'<td>{h(entry["status"].replace("_", " "))}</td>')
        rows.append(f'<tr><td>{h(event.get("release_utc",iso(event["epoch"]))) }<small>08:30 New York</small></td>{"".join(cells)}</tr>')
    heads = "".join(f'<th>Case {c["index"]}<small>{h(c["name"])}<br>{h(c["policy"])}</small></th>' for c in cases)
    return f'<div class="scroll"><table><thead><tr><th>Scheduled CPI release</th>{heads}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def source_links(calendar):
    urls = sorted({e.get("source", "") for e in calendar["events"] if str(e.get("source", "")).startswith("http")})
    return " ".join(f'<a href="{h(url)}" target="_blank" rel="noreferrer">Official calendar source {i+1}</a>' for i, url in enumerate(urls))


def optional_event_study():
    path = ROOT / "EVENT-STUDY.json"
    if not path.exists():
        return '<p class="muted">Separate unconditional event-study output is not present yet; trading results must not be described as an unconditional continuation probability.</p>', None
    study = load(path)
    # The independent event-study module may evolve its schema; preserve exact
    # output in a readable expandable block instead of guessing field meaning.
    rendered = '<p>Unconditional t+1 → t+5/15/30-minute price comparisons are separate from trade P&L and the strategy filters. Continuation means the horizon close moves farther in the first minute’s direction; reversion means the opposite increment—not necessarily a complete return to the pre-news price. A directional outcome is not the probability of a 1.5R trade win.</p><p><a href="EVENT-STUDY.json">Download event-study evidence</a></p>'
    for period_key, period_label in (("all_history","Full archive"),("retrospective_last_two_years","Last two years · retrospective"),("last_year","Last year")):
        section = study.get("summaries",{}).get(period_key)
        if not section:
            continue
        event_rows = []
        for cohort_key, cohort_label in (("all_nonzero_first_minute_impulses","All nonzero first-minute reactions"),("significant_common_impulse","Strong first-minute reaction filter")):
            for horizon in ("5","15","30"):
                data = section.get("cohorts",{}).get(cohort_key,{}).get(horizon)
                if not data:
                    continue
                ci = data.get("continuation_wilson_95_pct")
                ctext = f'{ci[0]:.1f}–{ci[1]:.1f}%' if ci else "—"
                count = int(data.get("observations",0))
                reversions = int(data.get("reversion_events",0))
                event_rows.append(f'<tr><td>{cohort_label}</td><td>+{horizon} min</td><td>{count}</td>'
                                  f'<td>{fmt(data.get("continuation_pct"),1,suffix="%")}<small>{data.get("continuation_events",0)} / {count} · 95% CI {ctext}</small></td>'
                                  f'<td>{fmt(100*reversions/count if count else None,1,suffix="%")}<small>{reversions} / {count}</small></td>'
                                  f'<td>{fmt(data.get("mean_signed_increment_points"),2,True)} pts</td></tr>')
        rendered += f'<h3>{period_label}</h3><p class="muted">{h(section.get("requested_start"))} → {h(section.get("requested_end_exclusive"))} exclusive · {section.get("scheduled_cpi_releases")} scheduled releases · {section.get("observed_initial_impulse_events")} observed nonzero initial impulses. Available horizon samples can be smaller.</p>'
        rendered += '<div class="scroll"><table><thead><tr><th>Cohort</th><th>Horizon from release</th><th>Observed</th><th>Continuation</th><th>Reversion</th><th>Mean signed increment after first minute</th></tr></thead><tbody>' + ''.join(event_rows) + '</tbody></table></div>'
    rendered += '<p class="muted">This descriptive study uses cached exact M1 windows and does not apply native quote-staleness or execution checks. Its eligible count need not match the native strategy count. Missing newest event windows remain missing; do not infer that a scheduled release was observed merely because it is in the calendar. No spread, slippage, fee, stop or target is included in these price-increment figures.</p>'
    for candidate in ("EVENT-STUDY.html", "EventStudy.html", "event_study.html"):
        if (ROOT / candidate).exists():
            rendered += f'<p><a href="{candidate}">Open event-study report</a></p>'
    compact = {k:v for k,v in study.items() if k not in ("sources","events","summaries")}
    rendered += f'<details><summary>Event-study definitions and limitations</summary><pre>{h(json.dumps(compact, indent=2,ensure_ascii=False))}</pre></details>'
    return rendered, {"file": path.name, "sha256": sha(path)}


def render(summary, config, calendar, windows):
    cases = summary["cases"]
    symbol = config["symbol"]
    instrument = config.get("instrument", symbol)
    study_date = config.get("study_date", "2026-10-16")
    first_year = cases[0]["periods"]["1y"]
    evaluation = cases[0]["periods"]["oos"]
    links = []
    for name in ("config.json", "FROZEN.json", "calendar.json", "CASES.json", "SUMMARY.json", "VERIFICATION.json", "INDEPENDENT-VERIFICATION.json", "COMPILER-ONLY-AMENDMENT.json", "ARTIFACTS.json", "native/ARTIFACTS.json"):
        if (ROOT / name).exists():
            links.append(f'<a class="pill" href="{h(name)}">{h(name)}</a>')
    period_sections = []
    for key, label, start, end in windows:
        count = sum(epoch(start) <= int(e["epoch"]) < epoch(end) for e in calendar["events"])
        period_sections.append(f'<section id="period-{key}" class="period-panel {"selected" if key == "1y" else ""}"><h3>{h(label)}</h3><p class="muted">{start} → {end} exclusive · {count} scheduled CPI events · continuous native account, not reset to $10,000 at this boundary</p>{metric_table(cases,key)}</section>')
    case_sections = []
    for case in cases:
        full = case["periods"]["all"]
        audit = case["audit"]
        qa = audit["quote_audit"]
        reasons = "".join(f'<tr><td>{h(reason.replace("_"," "))}</td><td>{count}</td></tr>' for reason,count in sorted(audit["event_status_counts"].items()))
        all_reasons = "".join(f'<tr><td>{h(reason)}</td><td>{count}</td></tr>' for reason,count in sorted(audit["decision_reason_counts"].items()))
        case_sections.append(f'<section class="card" id="case-{case["index"]}"><p class="eyebrow">CASE {case["index"]} · FROZEN, NOT OPTIMIZED</p><h2>{h(case["name"])}</h2><p>{h(case["policy"])}</p>'
          f'{chart(full["curve"],case["name"]+" closed balance")}'
          f'<p class="muted">Full-period closed-balance path. Full-period native floating-equity DD: {fmt(audit["native_full_period_floating_dd_pct"],2,suffix="%")}. Floating DD for subperiods is not inferred from this number or sparse snapshots.</p>'
          f'<div class="tiles"><div>Entry request quotes with zero spread<strong>{qa["matched_entry_request_zero_spread"]} / {len(case["trades"])}</strong></div>'
          f'<div>Entry + exit quote callbacks with zero spread<strong>{qa["zero_spread_callbacks"]} / {qa["all_entry_exit_quote_callbacks"]}</strong></div>'
          f'<div>Failed entry / close-update requests<strong>{audit["native_failed_entries"]} / {audit["native_failed_updates"]}</strong></div>'
          f'<div>Local reconciliation checks<strong>{"Passed" if audit["checks_all_pass"] else "CHECK FAILED"}</strong></div></div>'
          f'<p class="muted">Callback spread cash is not deducted again: broker-recorded trade P&L already uses the native fills. Positive entry spread does not prove authentic historical ticks, realistic exit spreads, or event liquidity.</p>'
          f'<details><summary>Event outcomes and all decision/skip reasons</summary><div class="two"><div><h3>One final status per scheduled release</h3><table>{reasons}</table></div><div><h3>All log reasons (may repeat within a release)</h3><table>{all_reasons}</table></div></div></details>'
          f'<details><summary>Full trade-by-trade breakdown · {len(case["trades"])} completed positions</summary>{trade_table(case)}</details></section>')
    event_html, _ = optional_event_study()
    options = "".join(f'<option value="{key}" {"selected" if key=="1y" else ""}>{h(label)}</option>' for key,label,_,_ in windows)
    notes = sorted({note for c in cases for note in c.get("tick_notes", [])})
    notes_html = "".join(f'<li>{h(note)}</li>' for note in notes) or '<li>No tester real-tick start note was returned. Absence of a note is not confirmation of full real-tick coverage.</li>'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{h(symbol)} CPI — continuation vs reversion raw study</title>
<style>:root{{--bg:#07120f;--panel:#0d211a;--line:#284d3e;--text:#e8fff5;--muted:#9ab6ac;--green:#65ebbd;--red:#ff9290;--gold:#f1ca79}}*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at top right,#113729,var(--bg) 65%);color:var(--text);font:15px/1.6 system-ui,Segoe UI,sans-serif}}main{{max-width:1500px;margin:auto;padding:46px 28px 90px}}h1{{font-size:clamp(30px,4vw,48px);line-height:1.15;max-width:1000px;margin:14px 0}}h2{{font-size:25px;margin:8px 0}}h3{{font-size:19px}}.eyebrow{{font:12px ui-monospace,monospace;letter-spacing:2px;color:var(--green)}}.muted,small{{color:var(--muted)}}small{{display:block;font-size:11px;font-weight:400;max-width:260px}}a{{color:var(--green)}}.warning{{border:1px solid #8c7136;background:#292412b3;color:#f5dc9a;border-radius:14px;padding:20px;margin:24px 0}}.card,.panel{{border:1px solid var(--line);border-radius:18px;background:#0b1b16dc;padding:26px;margin:25px 0}}.pills{{display:flex;gap:8px;flex-wrap:wrap}}.pill{{display:inline-block;border:1px solid var(--line);border-radius:8px;padding:7px 12px;text-decoration:none;font-size:12px}}.scroll{{overflow:auto;border:1px solid var(--line);border-radius:12px;margin:18px 0}}table{{width:100%;border-collapse:collapse;text-align:left;font-size:13px}}th,td{{padding:13px 12px;border-bottom:1px solid #244334;vertical-align:top}}th{{color:var(--muted);font-size:11px;letter-spacing:.3px;background:#0d231b;white-space:nowrap}}td:not(:first-child){{font-variant-numeric:tabular-nums}}tr:last-child td{{border-bottom:0}}.positive{{color:var(--green)}}.negative{{color:var(--red)}}.tiles{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:20px 0}}.tiles>div{{border:1px solid var(--line);border-radius:12px;padding:15px;font-size:12px;color:var(--muted)}}strong{{display:block;color:var(--text);font-size:23px;margin-top:5px}}.two{{display:grid;grid-template-columns:1fr 1fr;gap:24px}}svg{{display:block;width:100%;max-height:270px;margin:20px 0}}svg text{{font:11px system-ui;fill:var(--muted)}}details{{border-top:1px solid var(--line);padding:16px 0}}summary{{cursor:pointer;color:var(--green);font-weight:600}}pre{{overflow:auto;max-height:520px;font-size:11px;white-space:pre-wrap}}select{{padding:12px;border:1px solid var(--green);border-radius:8px;background:#0c251b;color:var(--text);font:inherit}}.period-panel{{display:none}}.period-panel.selected{{display:block}}.method li{{margin:8px 0}}.badge{{display:inline-block;border:1px solid #8c7136;color:var(--gold);padding:4px 10px;border-radius:50px;font-size:11px;letter-spacing:1px}}@media(max-width:800px){{main{{padding:25px 14px}}.card,.panel{{padding:18px}}.two{{grid-template-columns:1fr}}.tiles{{grid-template-columns:1fr 1fr}}th,td{{padding:10px}}}}@media print{{body{{background:white;color:black}}.period-panel{{display:block}}details>*{{display:block!important}}.scroll{{overflow:visible}}a,small,.muted{{color:#333}}}}</style></head><body><main>
<p class="eyebrow">CALYX RESEARCH · {h(symbol)} ONLY · {h(study_date)}</p><h1>{h(config.get('study', 'CPI continuation versus failed-spike reversion'))}</h1><p>Frozen raw comparison on {h(instrument)} · ${number(config['deposit']):,.0f} initial balance per separate case · {number(config['risk_percent']):g}% dynamic planned stop risk per trade · {number(config['execution_delay_ms']):g} ms execution delay. These six alternative cases are not one combined portfolio.</p><span class="badge">RESEARCH DIAGNOSTICS — NOT LIVE-TRADING APPROVAL</span>
<div class="warning"><b>Do not interpret these figures as verified executable news performance.</b> The archive includes generated fallback ticks before 2026 and many zero-spread event quotes. The second quote policy rejects zero-spread entries, but this alone neither repairs the archive nor proves real ticks or realistic exits. No live bots, BATs, or website settings were changed. We stop here for review before the next asset.</div>
<div class="pills">{"".join(links)}</div>
<section class="panel"><h2>Recent comparison · last year</h2><p class="muted">{h(first_year['start'])} → {h(first_year['end_exclusive'])} exclusive. Six predeclared cases; zero optimized parameter configurations. No winning case is selected or labelled validated.</p>{metric_table(cases,"1y")}<h2>Latest two-year retrospective evaluation</h2><p class="muted">{h(evaluation['start'])} → {h(evaluation['end_exclusive'])} exclusive. Related history has previously been inspected; this is not a claim of an untouched holdout.</p>{metric_table(cases,"oos")}</section>
<section class="panel"><h2>All date breakdowns</h2><label for="period">Period </label><select id="period">{options}</select>{"".join(period_sections)}<p class="muted">Returns use the continuous account balance at each window’s start. PF and win rate use net cash including recorded costs. Sharpe uses daily closed-balance returns × √365, including no-trade calendar days. Closed DD includes intraperiod closed-balance peaks and the starting balance; daily DD resets at UTC midnight. No floating-DD proxy is substituted.</p></section>
<section class="panel method"><h2>What is being compared?</h2><div class="two"><div><h3>Common setup</h3><ul><li>Official documented CPI release dates, 08:30 New York with DST handled; {len(calendar["events"])} scheduled events. Headline/core CPI are one simultaneous release, not duplicate opportunities.</li><li>Anchor: exact completed M1 close before release. ATR: simple mean of 14 true ranges using 15 contiguous pre-event M1 bars. All required data end strictly before release.</li><li>First release-aligned minute only: close displacement ≥1 pre-event ATR and close in the directional outer quartile. This is a price-reaction filter, not actual-versus-consensus surprise.</li><li>One signal attempt per model/event. Valid fresh quotes, spread ≤10% of stop distance, downward-rounded lot sizing. No forced market fallback, trailing, break-even, or partials.</li></ul></div><div><h3>Frozen entries and exits</h3><ul><li><b>Continuation:</b> executable break of the first minute’s extreme after its close, within five minutes of release. Stop beyond the opposite extreme + 0.1 ATR + one tick; target 1.5R; hold ≤15 minutes from fill.</li><li><b>Reversion:</b> a later completed M1 close crosses the first candle’s midpoint against the impulse; next executable quote, within ten minutes. Stop beyond the spike extreme; target the pre-release anchor; minimum offered reward/risk 1.5R; hold ≤30 minutes.</li><li><b>Anchor diagnostic:</b> same reversion, with no minimum-R gate. Predeclared to expose the midpoint/anchor geometry—not optimized or eligible for selection.</li><li>All modes hard-flat by release +60 minutes, at an available executable quote. Trading is prohibited outside the strategy tester.</li></ul></div></div><div class="warning">The strict anchor fade may take zero trades because returning from the midpoint to the pre-event anchor often offers less than 1.5R with the stop beyond the spike. That is a structural exclusion, not proof that reversals never occur. The continuation/reversion P&L difference is not a pure directional effect: their confirmations, target geometry and holding times differ.</div></section>
<section class="panel"><h2>Separate event-study evidence</h2>{event_html}</section>
{"".join(case_sections)}
<section class="panel"><h2>Every scheduled release: trigger, skip or outcome</h2><p class="muted">Each cell represents one scheduled CPI event under one frozen case. Statuses include missing/stale data and execution exclusions; those releases are not silently removed from the calendar.</p>{event_table(cases,calendar)}</section>
<section class="panel"><h2>Accounting and interpretation</h2><p>Full trade cash is reconciled to native deal cash, tester net profit and final balance. Successful entry decisions are matched to native fills within five seconds and the same scheduled release; rejected entry requests are excluded from matching. Causality checks require entry at or after release +60 seconds and at most one completed trade per event.</p><p>Realized net R is net P&L divided by the estimated cash risk from the actual fill to the initial stop, using native request-unit loss and linear price-distance scaling. It is not a guarantee of the maximum realized loss. Lot rounding and delayed fills can make realized risk differ from the 0.25% planned budget.</p><p>Wilson intervals describe the observed trade sample only; they are not independent-event bootstrap intervals, proof of stationarity, or correction for previous research. Multiple assets were not tested in this study. No Monte Carlo or optimization result is implied.</p><h3>Tester tick notes</h3><ul>{notes_html}</ul><p class="muted">Local verification is not an independent audit. No three-/five-year gate, recent profitable interval or no-failure accounting check overrides the execution-data limitations.</p><p>{source_links(calendar)}</p><p class="muted">Built from immutable native replay outputs at {h(summary["generated_at_utc"])} · source hashes in SUMMARY.json and VERIFICATION.json.</p></section>
</main><script>document.getElementById('period').addEventListener('change',function(){{document.querySelectorAll('.period-panel').forEach(p=>p.classList.remove('selected'));document.getElementById('period-'+this.value).classList.add('selected')}});</script></body></html>'''


def main():
    config = load(ROOT / "config.json")
    calendar = load(ROOT / "calendar.json")
    results = load(ROOT / "RESULTS.json")
    frozen = load(ROOT / "FROZEN.json")
    assert len(results) == 6 and sorted(int(r["index"]) for r in results) == list(range(6)), "Expected all six predeclared cases"
    assert [r["parameters"] for r in sorted(results,key=lambda r:r["index"])] == load(ROOT / "CASES.json"), "Frozen case mismatch"
    for key, filename in (("config_sha256","config.json"),("calendar_sha256","calendar.json"),("cases_sha256","CASES.json"),("engine_sha256","engine.mq5"),("build_sha256","build_engine.py")):
        assert sha(ROOT / filename) == frozen["locked"][key], f"Frozen input mismatch: {filename}"
    windows = date_windows(config)
    cases, verification_cases = [], []
    for row in sorted(results, key=lambda r: int(r["index"])):
        assert row["start"] == config["start"] and row["end"] == config["end_exclusive"]
        for suffix in ("decisions","quotes","equity","deals"):
            assert (NATIVE / f'{row["index"]}-{suffix}.csv.gz').exists(), f"Missing native {suffix} ledger"
        audited = audit_case(row, calendar)
        periods = {key: period_metrics(audited["trades"],start,end,number(config["deposit"])) for key,_,start,end in windows}
        verification = {k:v for k,v in audited.items() if k not in ("trades","events")}
        verification_cases.append(verification)
        cases.append({"index":int(row["index"]), "name":case_name(row), "policy":policy_name(row),
                      "parameters":row["parameters"], "periods":periods, "audit":verification,
                      "events":audited["events"], "trades":audited["trades"], "tick_notes":row.get("tick_notes",[]),
                      "report_sha256":row.get("report_sha256"), "binary_sha256":row.get("binary_sha256")})
    source_hashes = {name:sha(ROOT/name) for name in ("RESULTS.json","FROZEN.json","config.json","CASES.json","calendar.json","analysis_report.py")}
    for path in sorted(NATIVE.glob("*.csv.gz")):
        source_hashes[str(path.relative_to(ROOT)).replace("\\","/")] = sha(path)
    event_study = None
    if (ROOT / "EVENT-STUDY.json").exists():
        event_study = {"path":"EVENT-STUDY.json", "sha256":sha(ROOT / "EVENT-STUDY.json")}
    summary = {"study":config["study"], "generated_at_utc":datetime.now(UTC).isoformat(), "symbol":config["symbol"],
               "research_only":True, "live_changes":False, "parameters_searched":0, "enumerated_cases":6,
               "execution_quality":"Unverified archive reference. Generated pre-2026 ticks and zero-spread callbacks; positive-spread entry guard does not establish authentic executable historical news liquidity.",
               "selection":"No optimized or validated winner selected", "source_sha256":source_hashes,
               "periods":[dict(key=k,label=l,start=s,end_exclusive=e) for k,l,s,e in windows],
               "event_study":event_study, "cases":cases}
    verification = {"generated_at_utc":summary["generated_at_utc"],
                    "scope":"Local native-output accounting and elementary causality checks; not an independent review or data-quality certification.",
                    "source_sha256":source_hashes,"cases":verification_cases,
                    "all_local_checks_pass":all(c["checks_all_pass"] for c in verification_cases),
                    "limitations":["Generated historical ticks", "Zero-spread historical quote callbacks", "No verified point-in-time consensus archive", "Retrospective two-year evaluation", "Small and event-clustered samples", "No optimization or live approval"]}
    write_json(ROOT / "SUMMARY.json", summary)
    write_json(ROOT / "VERIFICATION.json", verification)
    (ROOT / "Results.html").write_text(render(summary,config,calendar,windows),encoding="utf-8")
    assert verification["all_local_checks_pass"], "Report written with local check failures; inspect VERIFICATION.json before presenting results"
    print(json.dumps({"report":str(ROOT/"Results.html"), "events":len(calendar["events"]), "all_local_checks_pass":True,
                      "one_year":[{"index":c["index"], **{k:v for k,v in c["periods"]["1y"].items() if k in ("trades","net","return_pct","pf","win_rate_pct","closed_dd_pct","max_win_streak","max_loss_streak")}} for c in cases]}, indent=2))


if __name__ == "__main__":
    main()
