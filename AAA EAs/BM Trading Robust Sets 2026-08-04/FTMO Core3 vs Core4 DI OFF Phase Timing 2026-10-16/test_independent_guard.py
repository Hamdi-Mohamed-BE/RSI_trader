"""Synthetic guard/accounting fixtures only: no historical portfolio outcomes."""
from pathlib import Path
from datetime import date, timedelta, datetime, timezone
import copy, hashlib, importlib.util, json, math

R = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("phase_replay_under_test", R/"run.py")
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)
PLAN = json.loads((R/"PLAN.json").read_text(encoding="utf-8-sig"))
CHECKS = []


def check(name, condition):
    CHECKS.append(dict(name=name, passed=bool(condition)))
    assert condition, name


def trial():
    d = date(2026, 1, 5)
    start = dict(date=str(d), epoch=model.midnight(d),
                 horizon_date=str(d+timedelta(days=180)),
                 horizon_epoch=model.midnight(d+timedelta(days=180)))
    t = model.Trial(copy.deepcopy(PLAN), "CORE4", start, "recorded_exness", "next_prague_midnight")
    t.day_reset(start["epoch"])
    return t, start["epoch"]+3600


def row(t, name="synthetic", ea="nasdaq-5m-candle-momentum", symbol="USTEC"):
    return dict(id=name, ea=ea, symbol=symbol, op=t, cl=t+60, position_id=1,
                end_censored=False, source_forced_close_epoch=None,
                open_price=100., close_price=200., sl=0., tp=0., side="Long",
                unit_risk=100., source_volume=1., entry_unit_cost=-4.,
                unit_gross=100., unit_commission=-8., unit_swap=-2., marks=[])


def fixtures():
    s = PLAN["risk"]["specs"]["USDJPY"]
    lot, requested = model.source_then_guard_lots(9800., 100., s)
    check("below_initial_equity_keeps_source_requested_cap", abs(lot-.49)<1e-9 and abs(requested-.49)<1e-9)
    lot, requested = model.source_then_guard_lots(10000., 1200., PLAN["risk"]["specs"]["USTEC"])
    check("broker_minimum_is_rejected_not_oversized", lot == 0 and requested >= .05)
    lot, requested = model.source_then_guard_lots(10000., 333., s)
    check("source_rounds_up_guard_rounds_down", abs(requested-.16)<1e-9 and abs(lot-.15)<1e-9 and lot*333 <= 50)
    check("usdjpy_margin_base_currency_not_quote_multiplied", abs(model.margin_per_lot(row(1, symbol="USDJPY"), s)-100000/30)<1e-9)
    t, ep = trial(); t.balance = 9000.; t.observe(ep)
    check("source_static_floor_equality_is_hard_failure", t.failed and t.current()["hard_failure_kind"] == "static")
    t.balance = 12000.; t.observe(ep+1); t.day_reset(ep+86400)
    check("hard_failure_never_recovers_next_day", t.failed and t.current()["status"] == "failed")
    t, ep = trial(); t.balance = 9500.; t.observe(ep)
    check("source_daily_floor_equality_is_hard_failure", t.failed and t.current()["hard_failure_kind"] == "daily")
    t, ep = trial(); t.balance = 9700.; t.observe(ep)
    check("soft_daily_300_latches_without_failure", t.day_stopped and not t.failed)
    t.balance = 10000.; t.observe(ep+1)
    check("soft_daily_stop_does_not_clear_after_intraday_recovery", t.day_stopped)
    t.day_reset(model.midnight(date(2026, 1, 6)))
    check("soft_daily_stop_resets_next_prague_day", not t.day_stopped and not t.failed)
    t, ep = trial(); t.eq = 9267.5; t.anchor = 9000.
    check("projected_9200_equality_is_admissible", t.reject_reason(row(ep), ep, 50, 0) is None)
    t.eq = 9267.49
    check("projected_below_9200_is_soft_rejection_not_failure", t.reject_reason(row(ep), ep, 50, 0) == "soft_total_buffer9200" and not t.failed)
    t, ep = trial(); t.active = {"old": dict(risk=200., margin=0., row={"symbol": "XAUUSD"})}
    check("aggregate_risk_exact_225_permitted", t.reject_reason(row(ep), ep, 25., 0.) is None)
    check("aggregate_risk_above_225_rejected", t.reject_reason(row(ep), ep, 25.01, 0.) == "aggregate_initial_risk225")
    t.active = {"old": dict(risk=120., margin=0., row={"symbol": "USTEC"})}
    check("same_symbol_150_independent_limit", t.reject_reason(row(ep), ep, 50., 0.) == "same_symbol_initial_risk150")
    t, ep = trial(); t.last_entry = ep
    check("reconciliation_wait_blocks_second_entry_two_seconds_later", t.reject_reason(row(ep), ep+2, 50, 0) == "entry_reconciliation3s")
    check("reconciliation_wait_ends_at_three_seconds", t.reject_reason(row(ep), ep+3, 50, 0) is None)
    t.daily_entries = 7
    check("daily_entry_cap_counts_seven", t.reject_reason(row(ep), ep+3, 50, 0) == "daily_7_entry_limit")
    t.daily_entries = 0; t.daily_losses = 3
    check("three_completed_losses_stop_new_entries", t.reject_reason(row(ep), ep+3, 50, 0) == "daily_3_closed_loss_limit")
    t, ep = trial(); t.balance = t.eq = 11000.; t.days = {"2026-01-01", "2026-01-02", "2026-01-03"}
    t.maybe_pass(ep)
    check("target_with_three_entry_days_does_not_pass", t.current()["status"] == "pending")
    t.days.add("2026-01-04"); t.active = {"old": dict(risk=1., margin=0., row={"symbol": "XAUUSD"})}
    check("target_blocks_new_entries_even_not_flat", t.reject_reason(row(ep), ep, 1., 0.) == "target_entry_gate_await_flat")
    t.maybe_pass(ep)
    check("target_not_flat_does_not_qualify", t.current()["status"] == "pending")
    t.active = {}; t.maybe_pass(ep)
    check("target_flat_with_four_entry_days_passes", t.current()["status"] == "passed")
    t.activate(t.ready)
    check("phase2_is_fresh_10000_and_resets_days", t.phase == 2 and t.balance == 10000 and not t.days and not t.active)
    t, ep = trial(); r = row(ep); t.opening(r, ep)
    check("entry_cost_is_booked_at_entry", abs(t.balance-9998)<1e-9 and len(t.active) == 1)
    check("initial_float_is_zero_not_future_first_mark", t.eq == t.balance and t.active[r["id"]]["mark_epoch"] is None)
    refused = False
    try:
        t.mark(r, [ep, -200., 1., 0., -200.], ep)
    except AssertionError:
        refused = True
    check("entry_second_pre_strategy_mark_is_rejected", refused)
    refused = False
    try:
        t.mark(r, [ep+30, -200., 1., 0., -200.], ep+29)
    except AssertionError:
        refused = True
    check("future_mark_cannot_be_backfilled", refused)
    t.mark(r, [ep+30, -20., 1., 0., -20.], ep+30)
    check("owned_floating_scales_to_replay_volume", abs(t.eq-9988.)<1e-9)
    t.closing(r, ep+60)
    check("cash_cost_conservation_no_double_booked_entry_fee", abs(t.balance-10045.)<1e-9 and abs(t.trades[0]["net"]-45.)<1e-9)
    check("closing_removes_floating_before_cash_equity_check", not t.active and t.eq == t.balance)
    t, ep = trial(); r = row(ep); r.update(cl=None, end_censored=True, source_forced_close_epoch=ep+60)
    data = dict(candidates=[r], year_end_exclusive_epoch=ep+120)
    events = model.master_events(PLAN, data)
    check("forced_source_finalization_not_emitted_as_natural_exit", not any(e[1] in (1, 4) and e[3] == r["id"] for e in events))
    t.opening(r, ep); t.balance = t.eq = 11000.; t.days = {"1", "2", "3", "4"}; t.maybe_pass(ep+60)
    check("end_censored_open_position_never_false_passes", t.current()["status"] == "pending" and bool(t.active))
    p1 = datetime(2026, 3, 28, 23, 30, tzinfo=timezone.utc).timestamp()
    p2 = model.phase2_ready(p1, "next_prague_midnight")
    check("dst_handover_is_next_prague_midnight_not_fixed_24h", model.day_of(p2) == date(2026, 3, 30) and (p2-p1) < 24*3600)
    p1 = datetime(2026, 1, 9, 10, tzinfo=timezone.utc).timestamp()
    check("two_business_day_wait_skips_weekend", model.day_of(model.phase2_ready(p1, "two_business_day_wait")) == date(2026, 1, 13))
    result = dict(status="PASS", synthetic_only=True, total=len(CHECKS), failed=0,
                  checked_utc=datetime.now(timezone.utc).isoformat(),
                  engine_sha256=hashlib.sha256((R/"run.py").read_bytes()).hexdigest(), checks=CHECKS)
    (R/"INDEPENDENT-FIXTURE-TESTS.json").write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k != "checks"}, indent=2))


if __name__ == "__main__":
    fixtures()


