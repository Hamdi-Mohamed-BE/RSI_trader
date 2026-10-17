"""Post-freeze evidence audit. No broker, terminal, network or selection calls.

Read immutable native ledgers and a persisted selection. Historical execution
quality is a separate mandatory gate: reconciled cash is not live-fill proof.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import hashlib
import importlib.util
import gzip
import json
import math
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
FIELDS = ("hold_minutes", "target_r", "entry_window_minutes", "impulse_mult", "close_fraction")
NY = ZoneInfo("America/New_York")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def safe(value):
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    return value


def save(path, value):
    Path(path).write_text(json.dumps(safe(value), indent=2, allow_nan=False), encoding="utf-8")


def utc(value):
    return datetime.fromtimestamp(float(value), timezone.utc).isoformat()


def stamp(value):
    return pd.Timestamp(value, tz="UTC").timestamp() if isinstance(value, str) and pd.Timestamp(value).tzinfo is None else pd.Timestamp(value).timestamp()


def key(parameters):
    return json.dumps({k: float(parameters[k]) for k in FIELDS}, sort_keys=True)


def shared_statistics():
    path = ROOT.parent.parent / "Calyx Research Pipeline/calyx_pipeline.py"
    spec = importlib.util.spec_from_file_location("cpi_pipeline_shared_statistics", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def pf(values):
    values = np.asarray(values, dtype=float)
    gp, gl = float(values[values > 0].sum()), float(-values[values < 0].sum())
    return gp / gl if gl > 0 else None


def pf_status(values):
    values = np.asarray(values, dtype=float)
    if np.any(values < 0):
        return "finite"
    return "no_losses" if np.any(values > 0) else "no_nonzero_outcomes"


def daily_expected_shortfall(returns, confidence=.95):
    # Sparse event strategies have a large atom at zero. Including every return
    # <= a zero VaR would dilute a 5% tail with almost the entire calendar.
    ordered = np.sort(np.asarray(returns, dtype=float))
    if not len(ordered):
        return 0.0
    mass = (1 - confidence) * len(ordered)
    whole = int(math.floor(mass))
    fraction = mass - whole
    total = float(ordered[:whole].sum())
    if fraction and whole < len(ordered):
        total += fraction * float(ordered[whole])
    return -total / mass


def ledger_path(row, suffix):
    folder = ROOT / "native" / row["stage"]
    candidates = [folder / f"{int(row['index'])}-{suffix}.csv.gz"]
    if "native_case_index" in row:
        candidates.append(folder / f"{int(row['native_case_index'])}-{suffix}.csv.gz")
    found = next((p for p in candidates if p.exists()), None)
    assert found is not None, (row["stage"], suffix, "missing native ledger")
    return found


def frozen_verification(frozen, config, trials):
    locked = frozen["locked"]
    files = locked.get("files", locked.get("hashes", {}))
    assert files, "Selection freeze must contain file hashes"
    checks = {}
    for filename, expected in files.items():
        path = ROOT / filename
        checks[filename] = path.exists() and sha(path) == expected
        assert checks[filename], f"Frozen file changed or missing: {filename}"
    required = {"engine.mq5", "build_engine.py", "config.json", "calendar.json", "DATA-SPLIT.json", "SEARCH-PLAN.json", "SELECTION.json", "trials.json"}
    assert required.issubset(files), "Selection freeze omits mandatory source/selection files"
    oos = stamp(config["oos_start"])
    assert all(stamp(t["end"]) <= oos for t in trials), "A development trial consumes the final evaluation period"
    source = (ROOT / "engine.mq5").read_text(encoding="utf-8")
    assert "!MQLInfoInteger(MQL_TESTER)" in source
    assert "positive_spread=true" in source
    return dict(all_frozen_hashes_match=True, files=checks, all_search_windows_end_before_oos=True,
                tester_only_source_guard=True, fixed_positive_entry_quote_policy=True,
                source_sha256=sha(ROOT / "engine.mq5"), frozen_at_utc=frozen["frozen_at_utc"])


def freeze_launch_proof(frozen, holdout_rows, selected):
    freeze_time = pd.Timestamp(frozen["frozen_at_utc"]).timestamp()
    receipts = []
    for row in holdout_rows:
        if key(row["parameters"]) != key(selected):
            continue
        folder = ROOT / "native" / row["stage"]
        path = next((p for p in [folder / "owned-process.json", folder / "OWNED-PROCESS.json"] if p.exists()), None)
        if path is None:
            receipts.append(dict(stage=row["stage"], available=False))
            continue
        record = load(path)
        started = record.get("started", record.get("started_epoch"))
        if started is None and record.get("started_utc"):
            started = pd.Timestamp(record["started_utc"]).timestamp()
        receipts.append(dict(stage=row["stage"], available=started is not None,
                             owned_process_receipt=str(path), receipt_sha256=sha(path),
                             started_utc=utc(started) if started is not None else None,
                             freeze_precedes_launch=bool(started >= freeze_time) if started is not None else None))
    available = bool(receipts) and all(x["available"] for x in receipts)
    return dict(frozen_at_utc=frozen["frozen_at_utc"], selected_holdout_launches=receipts,
                freeze_precedes_selected_holdout=all(x.get("freeze_precedes_launch") is True for x in receipts) if available else None,
                interpretation="Source hashes plus owned-process timestamps prove ordering of this replay, not genuinely untouched historical data")


def enrich_and_verify(row, calendar, config):
    paths = {suffix: ledger_path(row, suffix) for suffix in ("deals", "decisions", "quotes", "equity", "stats")}
    tables = {name: pd.read_csv(path) for name, path in paths.items()}
    decisions, deals = tables["decisions"], tables["deals"]
    entries = decisions[decisions.reason == "entry_continuation"]
    native = row["native"]
    checks = {}

    def check(label, condition):
        checks[label] = bool(condition)
        assert checks[label], (row["stage"], row["index"], label)

    native_folder = ROOT / "native" / row["stage"]
    native_reports = [p for p in [native_folder / "report.htm.gz", native_folder / "report.xml.gz"] if p.exists()]
    check("native_report_receipt_present", len(native_reports) == 1)
    report_hash = hashlib.sha256(gzip.decompress(native_reports[0].read_bytes())).hexdigest()
    check("native_report_source_hash_reconciles", report_hash == row["report_sha256"])
    binary = native_folder / "OrbSearch.ex5"
    source = native_folder / "OrbSearch.mq5"
    check("native_binary_source_hash_reconciles", binary.exists() and sha(binary) == row["binary_sha256"])
    check("compiled_source_uses_frozen_engine", source.exists() and source.read_text(encoding="utf-8").endswith((ROOT / "engine.mq5").read_text(encoding="utf-8")))

    raw_trades = sorted(row["trades"], key=lambda t: (t["open_epoch"], t["position_id"]))
    net = sum(float(t["net_profit"]) for t in raw_trades)
    check("native_cash_reconciles", abs(net - float(native["net"])) < .031)
    cash = float((deals.profit + deals.commission + deals.swap + deals.fee).sum()) if len(deals) else 0.0
    check("deal_cash_reconciles", abs(cash - net) < .031)
    check("ending_native_balance_reconciles", abs(float(native["balance"]) - float(config["deposit"]) - net) < .031)
    check("native_count_reconciles", len(raw_trades) == int(native["trades"]))
    check("no_open_native_position", int(native["open_position"]) == 0)
    check("no_rejected_entries", int(native["failed_entries"]) == 0)
    check("no_rejected_exit_updates", int(native["failed_updates"]) == 0)
    check("one_successful_decision_per_trade", len(entries) == len(raw_trades))
    check("statistics_ledger_reconciles", abs(float(tables["stats"].iloc[0]["net"]) - net) < .031)
    check("native_equity_snapshots_provided", len(tables["equity"]) > 0)
    check("final_snapshot_balance_reconciles", abs(float(tables["equity"].iloc[-1].balance) - float(native["balance"])) < .031)
    scheduled = {int(e["epoch"]): e for e in calendar if stamp(row["start"]) <= int(e["epoch"]) < stamp(row["end"])}
    logged = set(decisions.event_epoch.astype(int))
    check("every_scheduled_release_accounted", set(scheduled).issubset(logged))
    enriched = []
    balance = float(config["deposit"])
    for t0 in raw_trades:
        t = dict(t0)
        # The native logger writes after the synchronous send; its epoch may
        # share or slightly lag the fill epoch. The event window is unambiguous.
        candidates = entries[(entries.epoch - float(t["open_epoch"])).abs() <= 5]
        check(f"entry_decision_unique_{t['position_id']}", len(candidates) == 1)
        m = candidates.iloc[0]
        event = int(m.event_epoch)
        check(f"scheduled_entry_{t['position_id']}", event in scheduled)
        side = 1 if t["side"] == "buy" else -1
        request_bid, request_ask = float(m.request_bid), float(m.request_ask)
        request = request_ask if side > 0 else request_bid
        stop_distance = side * (request - float(t["initial_sl"]))
        target_distance = side * (float(t["initial_tp"]) - request)
        unit_loss = float(m.unit_loss)
        budget = float(m.risk_budget)
        planned = float(t["volume"]) * unit_loss
        unit_cash_per_price = unit_loss / stop_distance if stop_distance > 0 else None
        filled_risk = float(t["volume"]) * abs(float(t["open_price"]) - float(t["initial_sl"])) * unit_cash_per_price if unit_cash_per_price else None
        p = row["parameters"]
        for field in FIELDS:
            check(f"parameter_{field}_{t['position_id']}", abs(float(m[field]) - float(p[field])) < 1e-7)
        check(f"causal_first_candle_{t['position_id']}", float(t["open_epoch"]) >= event + 60 and int(m.bar_epoch) == event)
        check(f"entry_inside_window_{t['position_id']}", float(t["open_epoch"]) < event + 60 * float(p["entry_window_minutes"]) + 2)
        check(f"side_follows_impulse_{t['position_id']}", side == int(m.spike))
        check(f"fixed_first_impulse_threshold_{t['position_id']}", abs(float(m.first_news_close) - float(m.fair)) + 1e-7 >= float(m.pre_atr) * float(p["impulse_mult"]))
        width = float(m.impulse_high) - float(m.impulse_low)
        extreme = float(m.impulse_high) - float(m.first_news_close) if side > 0 else float(m.first_news_close) - float(m.impulse_low)
        check(f"fixed_first_close_location_{t['position_id']}", width > 0 and extreme <= float(p["close_fraction"]) * width + 1e-7)
        check(f"strict_positive_request_spread_{t['position_id']}", request_ask > request_bid > 0)
        check(f"request_spread_cap_{t['position_id']}", request_ask - request_bid <= .1 * stop_distance + 1e-7)
        check(f"positive_stop_and_target_{t['position_id']}", stop_distance > 0 and target_distance > 0)
        check(f"rounded_target_multiple_{t['position_id']}", abs(target_distance - float(p["target_r"]) * stop_distance) < .0101)
        check(f"fresh_strictly_pre_release_reference_{t['position_id']}", 0 < event - int(m.pre_quote_epoch) <= 2)
        check(f"attached_broker_levels_{t['position_id']}", abs(float(m.sl) - float(t["initial_sl"])) < .011 and abs(float(m.tp) - float(t["initial_tp"])) < .011)
        check(f"native_volume_matches_{t['position_id']}", abs(float(m.lots) - float(t["volume"])) < 1e-7)
        check(f"planned_cash_within_budget_{t['position_id']}", planned <= budget + .001)
        check(f"risk_budget_uses_prior_equity_{t['position_id']}", abs(budget - balance * float(config["risk_percent"]) / 100) < .011)
        check(f"cash_components_{t['position_id']}", abs(float(t["profit"]) + float(t["commission"]) + float(t["swap"]) + float(t["fee"]) - float(t["net_profit"])) < .001)
        check(f"event_hard_close_{t['position_id']}", float(t["close_epoch"]) <= event + 3600 + 5)
        check(f"hold_deadline_{t['position_id']}", float(t["close_epoch"]) - float(t["open_epoch"]) <= float(p["hold_minutes"]) * 60 + 5)
        t.update(event_epoch=event, release_utc=utc(event), release_ny=datetime.fromtimestamp(event, timezone.utc).astimezone(NY).isoformat(),
                 request_bid=request_bid, request_ask=request_ask, entry_spread_points=request_ask - request_bid,
                 pre_atr=float(m.pre_atr), fair=float(m.fair), first_close=float(m.first_news_close),
                 impulse_high=float(m.impulse_high), impulse_low=float(m.impulse_low), spike=int(m.spike),
                 risk_budget=budget, planned_risk_cash=planned, filled_initial_risk_cash=filled_risk,
                 cash_per_index_point_per_lot=unit_cash_per_price,
                 realised_r=float(t["net_profit"]) / budget if budget > 0 else None,
                 hold_minutes=(float(t["close_epoch"]) - float(t["open_epoch"])) / 60,
                 exit_label={3: "TIME", 4: "SL", 5: "TP"}.get(int(t["exit_reason"]), f"native_reason_{t['exit_reason']}"),
                 open_utc=utc(t["open_epoch"]), close_utc=utc(t["close_epoch"]), parameters=p)
        balance += float(t["net_profit"])
        enriched.append(t)
    check("one_trade_per_release", len({t["event_epoch"] for t in enriched}) == len(enriched))
    check("all_trades_within_requested_window", all(stamp(row["start"]) <= t["open_epoch"] < stamp(row["end"]) for t in enriched))
    quote = tables["quotes"]
    quote_spread = quote.ask - quote.bid if len(quote) else pd.Series(dtype=float)
    pre = decisions[decisions.reason == "pre_event_reference_confirmed"]
    verification = dict(passed=all(checks.values()), checks=checks, check_count=len(checks), scheduled_events=len(scheduled),
                        logged_events=len(set(scheduled).intersection(logged)), source_files={name: dict(path=str(path), sha256=sha(path)) for name, path in paths.items()},
                        quote_callbacks=len(quote), positive_quote_callbacks=int((quote_spread > 0).sum()),
                        zero_quote_callbacks=int((quote_spread == 0).sum()),
                        zero_pre_release_references=int(((pre.pre_quote_ask - pre.pre_quote_bid) == 0).sum()) if len(pre) else 0,
                        native_equity_snapshots=len(tables["equity"]), native_floating_drawdown_source="MT5 full-tick TesterStatistics, not reconstructed minute snapshots",
                        native_full_window_equity_dd_statistics_provided=math.isfinite(float(native["equity_dd"])),
                        native_full_tick_equity_path_recorded=False,
                        caution="Accounting/source-guard consistency, not independent authentic quote-history certification")
    return sorted(enriched, key=lambda t: (t["close_epoch"], t["position_id"])), tables, verification


def metrics(trades, start, end, starting_balance, shared, native=None, actual_first=None, actual_last=None):
    selected = sorted([t for t in trades if stamp(start) <= t["close_epoch"] < stamp(end)], key=lambda t: (t["close_epoch"], t["position_id"]))
    p = np.asarray([t["net_profit"] for t in selected], dtype=float)
    equity = np.r_[starting_balance, starting_balance + np.cumsum(p)]
    peaks = np.maximum.accumulate(equity)
    closed_dd = peaks - equity
    closed_pct = np.divide(closed_dd, peaks, out=np.zeros_like(closed_dd), where=peaks > 0) * 100
    days = pd.date_range(start, pd.Timestamp(end) - pd.Timedelta(days=1), freq="D", tz="UTC")
    cash = pd.Series(0.0, index=days)
    daily_peak = {}
    daily_max = daily_max_pct = 0.0
    balance = starting_balance
    for t in selected:
        day = pd.Timestamp(t["close_epoch"], unit="s", tz="UTC").normalize()
        cash.loc[day] += float(t["net_profit"])
        peak = max(daily_peak.get(day, balance), balance)
        balance += float(t["net_profit"])
        peak = max(peak, balance)
        daily_peak[day] = peak
        daily_max = max(daily_max, peak - balance)
        daily_max_pct = max(daily_max_pct, (peak - balance) / peak * 100 if peak > 0 else 0)
    end_balance = starting_balance + cash.cumsum()
    previous = end_balance.shift(1).fillna(starting_balance)
    returns = cash / previous
    wins, losses = int((p > 0).sum()), int((p < 0).sum())
    ws, ls = shared.streaks(p.tolist())
    sd = float(returns.std(ddof=1))
    wilson = [100 * v for v in shared.wilson_interval(wins, len(p))] if len(p) else [None, None]
    value = dict(trades=len(p), wins=wins, losses=losses, flat=int((p == 0).sum()),
                 win_rate_pct=100 * wins / len(p) if len(p) else None, win_rate_wilson_95_pct=wilson,
                 pf=pf(p), pf_status=pf_status(p), net_profit=float(p.sum()),
                 profit=sum(float(t["profit"]) for t in selected), commission=sum(float(t["commission"]) for t in selected),
                 swap=sum(float(t["swap"]) for t in selected), fee=sum(float(t["fee"]) for t in selected),
                 return_pct=float(p.sum()) / starting_balance * 100 if starting_balance > 0 else None,
                 return_contribution_pct=float(p.sum()) / 10000 * 100,
                 starting_balance=starting_balance, ending_balance=float(end_balance.iloc[-1]) if len(end_balance) else starting_balance,
                 max_closed_dd_pct=float(closed_pct.max()), max_closed_dd_usd=float(closed_dd.max()),
                 max_daily_closed_dd_pct=daily_max_pct, max_daily_closed_dd_usd=daily_max,
                 native_equity_dd_pct=float(native["equity_dd"]) if native is not None else None,
                 native_balance_dd_pct=float(native["balance_dd"]) if native is not None else None,
                 daily_closed_sharpe=float(returns.mean()) / sd * math.sqrt(365) if sd > 0 else 0.0,
                 max_win_streak=ws, max_loss_streak=ls, average_trade=float(p.mean()) if len(p) else None,
                 avg_realised_r=float(np.mean([t["realised_r"] for t in selected])) if selected else None,
                 avg_hold_minutes=float(np.mean([t["hold_minutes"] for t in selected])) if selected else None,
                 max_hold_minutes=max((t["hold_minutes"] for t in selected), default=None),
                 expected_shortfall_95_daily_pct=daily_expected_shortfall(returns) * 100,
                 expected_shortfall_convention="Worst exact 5% of requested calendar-day returns, fractional boundary weight; zero-return ties are not all added to the tail",
                 actual_first_quote_utc=actual_first, actual_last_quote_utc=actual_last,
                 calendar_days=len(days), sharpe_convention="Daily completed-position net cash / prior closed balance, full requested UTC calendar including zeros, sqrt(365)")
    curve = [dict(date=str(day.date()), balance=float(end_balance.loc[day]), pnl=float(cash.loc[day]), return_pct=float(returns.loc[day]) * 100) for day in days]
    return value, curve, returns.to_numpy(dtype=float), selected


def event_bootstrap(trades, events, start, end, config, seed):
    dates = [int(e["epoch"]) for e in events if stamp(start) <= int(e["epoch"]) < stamp(end)]
    paths, block = int(config["monte_carlo_paths"]), int(config["monte_carlo_block_events"])
    if not dates or not trades:
        return dict(status="insufficient_trades", paths=0, requested_paths=paths, n_event_dates=len(dates), return_p05=None, return_p50=None, return_p95=None,
                    pf_interval=None, DD_interval=None, probability_profit_pct=None)
    realized = {int(t["event_epoch"]): float(t["realised_r"]) for t in trades}
    r = np.asarray([realized.get(t, 0.0) for t in dates])
    rng = np.random.default_rng(seed)
    starts = rng.integers(0, len(r), size=(paths, math.ceil(len(r) / block)))
    indices = ((starts[:, :, None] + np.arange(block)) % len(r)).reshape(paths, -1)[:, :len(r)]
    sampled = r[indices] * float(config["risk_percent"]) / 100
    balances = np.cumprod(np.maximum(0, 1 + sampled), axis=1)
    previous = np.c_[np.ones(paths), balances[:, :-1]]
    cash = previous * sampled
    gp = np.maximum(cash, 0).sum(axis=1)
    gl = -np.minimum(cash, 0).sum(axis=1)
    finite = gl > 0
    no_loss = (gl == 0) & (gp > 0)
    all_zero = (gl == 0) & (gp == 0)
    pfs = np.divide(gp, gl, out=np.full(paths, np.nan), where=finite)
    pfs[no_loss] = np.inf
    defined = np.sort(pfs[~np.isnan(pfs)])
    pf_quantiles, pf_kinds = {}, {}
    for label, q in (("p05", .05), ("p50", .5), ("p95", .95)):
        x = float(defined[max(0, math.ceil(q * len(defined)) - 1)]) if len(defined) else None
        pf_quantiles[label] = x if x is not None and math.isfinite(x) else None
        pf_kinds[label] = "finite" if x is not None and math.isfinite(x) else "no_losses" if x is not None else "undefined_no_outcomes"
    peaks = np.maximum.accumulate(np.c_[np.ones(paths), balances], axis=1)[:, 1:]
    dd = ((peaks - balances) / peaks).max(axis=1) * 100
    final = (balances[:, -1] - 1) * 100
    qs = np.quantile(final, [.05, .5, .95]).tolist()
    return dict(status="completed", paths=paths, seed=seed, block_length_event_dates=block, n_event_dates=len(dates),
                n_nonzero_event_dates=int((r != 0).sum()), return_p05=qs[0], return_p50=qs[1], return_p95=qs[2],
                pf_interval=dict(**pf_quantiles, quantile_kinds=pf_kinds, no_loss_paths_pct=float(no_loss.mean() * 100),
                                 all_zero_paths_pct=float(all_zero.mean() * 100), finite_pf_paths=int(finite.sum()),
                                 note="No-loss paths are not assigned a fabricated finite PF; null percentiles carry explicit no-loss/undefined kind"),
                DD_interval=dict(zip(("p05", "p50", "p95"), np.quantile(dd, [.05, .5, .95]).tolist())),
                probability_profit_pct=float((final > 0).mean() * 100), total_10pct_closed_balance_breach_proxy_pct=float((balances.min(axis=1) <= .9).mean() * 100),
                scope="10,000 circular blocks of five scheduled CPI event dates, including zero/no-trade events; replay frozen net-R outcomes at nominal dynamic risk. No signal/quote regeneration, broker lot rounding, margin, floating DD or prop challenge pass simulation")


def cost_stress(trades, quote_table):
    stressed = []
    extra = []
    for t in trades:
        cost = t["entry_spread_points"] * t["volume"] * t["cash_per_index_point_per_lot"]
        extra.append(cost)
        stressed.append(t["net_profit"] - cost)
    q = quote_table.copy()
    if len(q):
        q = q[(q.entry == 0) & (q.ask > q.bid) & (q.epoch >= stamp("2026-01-01"))]
    return dict(archive_proxy=dict(extra_cost_rule="One additional full entry-request spread x recorded lot x native cash-per-price conversion",
                                   trades=len(trades), extra_cash_total=sum(extra), net_profit=sum(stressed), pf=pf(stressed),
                                   pf_status=pf_status(stressed),
                                   per_trade_extra_cash=extra, execution_replayed=False,
                                   caveat="Ledger-only sensitivity at frozen fills/lots; extra spread can change eligibility, stop geometry, fills and lot sizing in a true replay. Older quote costs can be generated artifacts."),
                strictly_positive_2026_entry_callbacks=len(q), positive_2026_spread_cash=[float(x) for x in q.spread_cash] if len(q) else [],
                measured_live_cost_evidence_sufficient=False,
                reliable_event_bid_ask_gate=False,
                measured_evidence_note="Positive callback spread and a 2026 timestamp do not prove complete authentic event liquidity or live slippage. Sparse realized entries cannot certify measured live news-execution costs.")


def simple_group(trades):
    values = [float(t["net_profit"]) for t in trades]
    return dict(trades=len(values), net_profit=sum(values), pf=pf(values), pf_status=pf_status(values),
                win_rate_pct=100 * sum(x > 0 for x in values) / len(values) if values else None)


def calendar_thirds(trades, start, end):
    left, right = stamp(start), stamp(end)
    rows = []
    for i in range(3):
        a, b = left + (right - left) * i / 3, left + (right - left) * (i + 1) / 3
        rows.append(dict(part=i + 1, start_utc=utc(a), end_exclusive_utc=utc(b),
                         **simple_group([t for t in trades if a <= t["close_epoch"] < b])))
    return rows


def concentration(trades):
    years = sorted({datetime.fromtimestamp(t["close_epoch"], timezone.utc).year for t in trades})
    annual = {str(y): simple_group([t for t in trades if datetime.fromtimestamp(t["close_epoch"], timezone.utc).year == y]) for y in years}
    excluded = {str(y): simple_group([t for t in trades if datetime.fromtimestamp(t["close_epoch"], timezone.utc).year != y]) for y in years}
    positive = sum(max(0, x["net_profit"]) for x in annual.values())
    return dict(annual=annual, leave_one_year_out=excluded,
                largest_positive_year_share_pct=max((max(0, x["net_profit"]) for x in annual.values()), default=0) / positive * 100 if positive else None,
                note="Descriptive concentration check, not reoptimized leave-one-year-out validation")


def analyse(row, alias, events, config, shared, tested, seed):
    trades, tables, verification = enrich_and_verify(row, events, config)
    first = utc(float(tables["equity"].iloc[0].epoch))
    last = utc(row["native"]["last_quote_epoch"])
    m, curve, returns, _ = metrics(trades, row["start"], row["end"], float(config["deposit"]), shared, row["native"], first, last)
    thirds = calendar_thirds(trades, row["start"], row["end"])
    midpoint = (stamp(row["start"]) + stamp(row["end"])) / 2
    recent = [t for t in trades if t["close_epoch"] >= midpoint]
    decisions = tables["decisions"]
    event_rows = []
    for event in events:
        when = int(event["epoch"])
        if not stamp(row["start"]) <= when < stamp(row["end"]):
            continue
        log = decisions[decisions.event_epoch == when]
        local = [t for t in trades if t["event_epoch"] == when]
        meaningful = log[~log.reason.isin(["event_start", "event_end", "pre_event_reference_confirmed", "impulse_confirmed"])]
        reason = "traded" if local else str(meaningful.iloc[-1].reason) if len(meaningful) else "no_qualifying_entry"
        event_rows.append(dict(event_epoch=when, release_utc=utc(when), disposition=reason, **simple_group(local)))
    return dict(label=alias, stage=row["stage"], index=row["index"], parameters=row["parameters"], start=row["start"], end_exclusive=row["end"],
                metrics=m, monte_carlo=event_bootstrap(trades, events, row["start"], row["end"], config, seed),
                cost_stress=cost_stress(trades, tables["quotes"]), verification=verification,
                sharpe=shared.sharpe_statistics(returns.tolist(), tested, 365),
                calendar_thirds=thirds, recent_half_pf=pf([t["net_profit"] for t in recent]), recent_half=simple_group(recent),
                concentration=concentration(trades), trades=trades, daily_curve=curve, events=event_rows,
                native_model=row["model"], native_tick_notes=row.get("tick_notes", []),
                equity_scope="Native full-window floating DD is authoritative; plotted daily completed-position balances do not measure intraday floating DD")


def segment(analysis, start, end, shared):
    before = sum(t["net_profit"] for t in analysis["trades"] if t["close_epoch"] < stamp(start))
    starting = float(analysis["metrics"]["starting_balance"]) + before
    m, curve, _, trades = metrics(analysis["trades"], start, end, starting, shared,
                                 actual_first=analysis["metrics"]["actual_first_quote_utc"], actual_last=analysis["metrics"]["actual_last_quote_utc"])
    return dict(start=start, end_exclusive=end, metrics=m, daily_curve=curve, trades=trades,
                account_scope="Continuous slice of parent native account; no artificial $10,000 reset or fresh lot sizing",
                native_floating_dd_available=False, parent_native_window=[analysis["start"], analysis["end_exclusive"]])


def pair(analyses, baseline, selected):
    assert analyses
    base = next((x for x in analyses if key(x["parameters"]) == key(baseline)), None)
    winner = next((x for x in reversed(analyses) if key(x["parameters"]) == key(selected)), None)
    return dict(baseline=base, selected=winner)


def null_family(trials, selected, config, events):
    unique = {}
    for trial in trials:
        if trial["start"] == config["start"] and trial["end"] == config["development_end_exclusive"]:
            unique[key(trial["parameters"])] = trial
    if key(selected) not in unique:
        return dict(status="unavailable", reason="Selected setting lacks a complete common-development native trial")
    dates = [int(e["epoch"]) for e in events if stamp(config["start"]) <= int(e["epoch"]) < stamp(config["development_end_exclusive"])]
    if len(dates) < 3:
        return dict(status="insufficient_development_events")
    matrix, keys = [], []
    for k, row in sorted(unique.items()):
        values = np.zeros(len(dates))
        event_index = {t: i for i, t in enumerate(dates)}
        for trade in row["trades"]:
            index = int(np.searchsorted(dates, trade["open_epoch"], side="right") - 1)
            assert index >= 0 and 60 <= trade["open_epoch"] - dates[index] < 10 * 60 + 2
            values[event_index[dates[index]]] += float(trade["net_profit"])
        matrix.append(values)
        keys.append(k)
    matrix = np.asarray(matrix)
    centered = matrix - matrix.mean(axis=1, keepdims=True)
    rng = np.random.default_rng(2026101621)
    paths, n = 2000, len(dates)
    signs = rng.choice([-1.0, 1.0], size=(paths, n))
    sums = signs @ centered.T
    ss = (centered ** 2).sum(axis=1)
    denom = np.sqrt(np.maximum(n * ss[None, :] - sums ** 2, 0))
    scores = np.divide(sums * math.sqrt(n - 1), denom, out=np.zeros_like(sums), where=denom > 0)
    means, deviations = matrix.mean(axis=1), matrix.std(axis=1, ddof=1)
    observed = np.divide(means * math.sqrt(n), deviations, out=np.zeros_like(means), where=deviations > 0)
    i = keys.index(key(selected))
    maxima = scores.max(axis=1)
    return dict(status="completed", paths=paths, seed=2026101621, configurations=len(keys), common_scheduled_development_events=n,
                selected_studentized_mean=float(observed[i]),
                selected_fixed_rule_one_sided_p=float((1 + (scores[:, i] >= observed[i]).sum()) / (paths + 1)),
                registered_family_maximum_one_sided_p=float((1 + (maxima >= observed[i]).sum()) / (paths + 1)),
                null_family_maximum_p50_p95=np.quantile(maxima, [.5, .95]).tolist(),
                scope="Shared-event Rademacher signs applied to each preregistered full-development strategy's centered net-P&L residuals; zero/no-trade events retained. Conditional registered-family diagnostic, not price-path scrambling or full signal/fill reexecution.",
                limitations="Net residual sign flips are not a cost-preserving executable fake-market model. Unrecorded historical asset/model searches are not included; no claim of beating the entire research universe.")


def main():
    required = ["RUNS.json", "config.json", "calendar.json", "trials.json", "SELECTION.json", "FROZEN.json", "DATA-SPLIT.json", "RAW-GATES.json", "WALK-FORWARD.json"]
    assert all((ROOT / name).exists() for name in required), "Run and freeze the native pipeline first; audit cannot create missing results"
    config, calendar = load(ROOT / "config.json"), load(ROOT / "calendar.json")["events"]
    runs, trials = load(ROOT / "RUNS.json"), load(ROOT / "trials.json")
    selection, frozen = load(ROOT / "SELECTION.json"), load(ROOT / "FROZEN.json")
    assert config["symbol"] == "US500" and config["research_only"] and not config["live_changes"]
    assert trials, "The registered search/training ledger must not be empty"
    assert all(name in runs for name in ["parity", "raw-3y", "holdout", "full", "validation", "delay-500", "delay-1000", "generated-diagnostic"]), "Incomplete required native stages"
    verified_freeze = frozen_verification(frozen, config, trials)
    assert frozen["locked"]["selected"] == selection["selected"]
    source_helper = shared_statistics()
    unique = {key(t["parameters"]) for t in trials}
    prior = int(config.get("prior_raw_asset_model_choices_for_dsr", 12))
    execution = int(config.get("fixed_postselection_execution_scenarios_for_dsr", 3))
    tested = len(unique) + prior + execution
    trial_count = dict(unique_current_parameter_configurations=len(unique), total_recorded_training_evaluations=len(trials),
                       prior_raw_asset_model_choices=prior, fixed_execution_scenarios=execution, dsr_tested_configurations=tested,
                       scope="Conservative nominal count of this registered search, earlier raw asset/model/policy choices and fixed execution scenarios; not all historical research. Repeated settings across walk-forward training windows are disclosed, not counted as independent new parameters.")
    stages = {}
    selected_aliases = ["parity", "raw-3y", "dev-baseline", "validation", "holdout", "full", "delay-500", "delay-1000", "generated-diagnostic"]
    for j, alias in enumerate(selected_aliases):
        if alias not in runs:
            continue
        print(f"AUDIT {alias}", flush=True)
        stages[alias] = [analyse(row, alias, calendar, config, source_helper, tested, 2026101600 + j * 10 + i) for i, row in enumerate(runs[alias])]
    baseline, selected = selection["baseline"], selection["selected"]
    comparisons = {name: pair(stages[name], baseline, selected) for name in ["full", "holdout", "validation"]}
    comparisons["periods"] = {}
    end = config["end_exclusive"]
    for period, months in [("3m", 3), ("6m", 6), ("1y", 12), ("3y", 36), ("5y", 60)]:
        start = (pd.Timestamp(end) - pd.DateOffset(months=months)).strftime("%Y-%m-%d")
        parent = comparisons["holdout"] if stamp(start) >= stamp(config["oos_start"]) else comparisons["full"]
        comparisons["periods"][period] = {role: segment(parent[role], start, end, source_helper) if parent[role] is not None else None for role in ["baseline", "selected"]}
    comparisons["periods"]["yearly"] = {}
    for year in range(int(config["start"][:4]), int(end[:4]) + 1):
        start, finish = max(config["start"], f"{year}-01-01"), min(end, f"{year + 1}-01-01")
        if start >= finish:
            continue
        comparisons["periods"]["yearly"][str(year)] = {role: segment(comparisons["full"][role], start, finish, source_helper) if comparisons["full"][role] is not None else None for role in ["baseline", "selected"]}
    original = load(ROOT.parent / "US500 CPI Continuation vs Reversion Raw 2026-10-16/RESULTS.json")[3]
    p = runs["parity"][0]
    fields = ["open_epoch", "close_epoch", "side", "volume", "open_price", "close_price", "net_profit", "initial_sl", "initial_tp"]
    assert [[t[k] for k in fields] for t in p["trades"]] == [[t[k] for k in fields] for t in original["trades"]], "Raw native baseline parity failed"
    launch_proof = freeze_launch_proof(frozen, runs["holdout"], selected)
    holdout = comparisons["holdout"]["selected"]
    assert holdout is not None
    mc, sharp = holdout["monte_carlo"], holdout["sharpe"]
    centres = selection.get("centres", [])
    centre = next((x for x in centres if key(x["parameters"]) == key(selected)), None)
    majority = bool(centre and centre["positive_neighbours"] > centre["total_neighbours"] / 2)
    validation_selected = comparisons["validation"]["selected"]
    validation_metric = validation_selected["metrics"] if validation_selected else {}
    raw = load(ROOT / "RAW-GATES.json")
    gate = dict(minimum_30_final_oos_trades=holdout["metrics"]["trades"] >= 30,
                positive_final_oos_net=holdout["metrics"]["net_profit"] > 0,
                final_oos_pf_above_one=(holdout["metrics"]["pf"] or 0) > 1,
                monte_carlo_profit_probability_95pct=(mc.get("probability_profit_pct") or 0) >= 95,
                monte_carlo_return_p05_positive=(mc.get("return_p05") or 0) > 0,
                monte_carlo_finite_pf_p05_above_one=((mc.get("pf_interval") or {}).get("p05") or 0) > 1,
                deflated_sharpe_95pct=sharp["deflated_sharpe_pct"] >= 95,
                profitable_development_neighbour_majority=majority,
                validation_minimum_registered_trades=validation_metric.get("trades", 0) >= int(config["validation_research_selection"]["minimum_trades"]),
                validation_positive_net=validation_metric.get("net_profit", 0) > 0,
                validation_pf_above_one=(validation_metric.get("pf") or 0) > 1,
                raw_three_year_gates_pass=all(raw["three_year_checks"].values()),
                raw_five_year_complete_and_pass=not bool(raw.get("five_year_unavailable", True)) and bool(raw.get("five_year_passed", False)),
                recent_calendar_half_pf_above_one=(holdout["recent_half_pf"] or 0) > 1,
                two_of_three_calendar_parts_profitable=sum(x["net_profit"] > 0 for x in holdout["calendar_thirds"]) >= 2,
                both_native_delay_stresses_profitable=all(stages[name][0]["metrics"]["net_profit"] > 0 and (stages[name][0]["metrics"]["pf"] or 0) > 1 for name in ["delay-500", "delay-1000"]),
                reliable_event_bid_ask=False, measured_broker_slippage_cost_stress=False,
                native_full_window_equity_dd_statistics_provided=holdout["verification"]["native_full_window_equity_dd_statistics_provided"],
                selected_native_accounting_and_causality=holdout["verification"]["passed"],
                freeze_precedes_selected_holdout=launch_proof["freeze_precedes_selected_holdout"] is True)
    verdict = "PASS_FOR_FORWARD_TEST" if all(gate.values()) else "RESEARCH_ONLY_WATCH" if holdout["metrics"]["net_profit"] > 0 and (holdout["metrics"]["pf"] or 0) > 1 else "RESEARCH_ONLY_REJECT"
    null = null_family(trials, selected, config, calendar)
    verification = dict(generated_utc=datetime.now(timezone.utc).isoformat(), all_frozen_checks=verified_freeze,
                        baseline_exact_raw_parity=True, baseline_parity_fields=fields, baseline_parity_trades=len(p["trades"]),
                        launch_order=launch_proof, all_analysed_native_rows_pass=all(x["verification"]["passed"] for rows in stages.values() for x in rows),
                        total_local_checks=sum(x["verification"]["check_count"] for rows in stages.values() for x in rows),
                        native_source_sha256=sha(ROOT / "engine.mq5"), audit_source_sha256=sha(Path(__file__)),
                        live_changes=False, external_calls=False, scope="Local cash/epoch/parameter/causal-source and frozen-artifact audit, not independent quote authenticity or live broker execution certification")
    metadata = dict(study=config["study"], symbol=config["symbol"], instrument=config["instrument"],
                    initial_balance=config["deposit"], risk_percent=config["risk_percent"], start=config["start"], end_exclusive=end,
                    oos_start=config["oos_start"], data_split=load(ROOT / "DATA-SPLIT.json"),
                    oos_status=config["oos_status"], selection_freeze_utc=frozen["frozen_at_utc"],
                    freeze_precedes_selected_holdout=launch_proof["freeze_precedes_selected_holdout"], launch_order_proof=launch_proof,
                    validation_gate_scope=dict(label="Registered research-selection validation, not a newly introduced promotion threshold",
                                               minimum_trades=config["validation_research_selection"]["minimum_trades"],
                                               policy=config["validation_research_selection"],
                                               unchanged_raw_and_final_oos_minimum_trades=30),
                    study_source_sha256={name: sha(ROOT / name) for name in required},
                    period_account_scope="Full and final-OOS are separate native accounts reset to $10,000; recent windows slice OOS continuously; 3y/5y/yearly windows slice full account continuously. The rolling 5y display includes evaluation history, is never selection evidence and is not the unavailable five-year pre-development raw gate. No period-specific retuning or re-sizing.")
    result = dict(metadata=metadata, selection=selection, raw_gates=raw, walk_forward=load(ROOT / "WALK-FORWARD.json"),
                  trial_count=trial_count, stages=stages, comparisons=comparisons, null_family=null,
                  gates=gate, all_mandatory_gates_pass=all(gate.values()), verdict=verdict, verification=verification,
                  limitations=["Research only. Related raw results, asset/model choice and historical final-period data were previously inspected; this is not untouched OOS.",
                               "No more than 23 scheduled CPI events in final two years and one trade per release: the 30-trade final evidence gate cannot pass.",
                               "Five pre-development years are unavailable; validation or final-period history is not consumed to manufacture them.",
                               "Pre-2026 generated ticks and zero-spread historical references prevent reliable event-level execution certification, even when entry spreads are positive.",
                               "Native full-tick floating DD applies only to each exact native window. Segment daily and closed-position curves are not intraday floating equity.",
                               "Near-event minute snapshots are not a stored full-tick equity path; only the native exact-window maximum floating-DD statistic is supplied.",
                               "10,000-event-block paths reapply saved net-R at nominal risk, not signals, market prices, broker volume steps, slippage or prop-firm challenge rules.",
                               "The sparse real-year event entry sample cannot establish measured live spread/slippage; ledger-only extra-cost sensitivities cannot pass that gate.",
                               "Registered-family centered-P&L null diagnostic is not price-replayed fake-market validation and does not cover the whole research history.",
                               "No live trading, installer, portfolio, website or risk setting was changed."], live_changes=False)
    save(ROOT / "AUDIT.json", result)
    save(ROOT / "VERIFICATION.json", verification)
    save(ROOT / "TRADES.json", {name: [x["trades"] for x in rows] for name, rows in stages.items()})
    print(json.dumps(dict(verdict=verdict, mandatory_gates_passed=sum(gate.values()), mandatory_gates=len(gate),
                          selected=selected, final_oos=holdout["metrics"], outputs=["AUDIT.json", "VERIFICATION.json", "TRADES.json"]), indent=2), flush=True)
    return result


if __name__ == "__main__":
    main()
