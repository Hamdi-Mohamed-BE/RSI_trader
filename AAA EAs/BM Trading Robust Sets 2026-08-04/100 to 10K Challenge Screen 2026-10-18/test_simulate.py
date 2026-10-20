"""Synthetic challenge fixtures. These do not read historical outcomes."""
import importlib.util
from pathlib import Path
import math
import pytest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('challenge_engine_under_test', ROOT/'simulate.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)


def specs(**changes):
    one = dict(volume_min=.01, volume_step=.01, volume_max=1000., spread_cash_per_lot=1.)
    one.update(changes)
    return {symbol: dict(one) for symbol in ('A', 'B', 'C')}


def row(key='a', pid=1, op=100, cl=200, profit=100., risk=100., entry=0.,
        symbol='A', margin=0., fractions=None, censored=False):
    flows = [dict(epoch=op, kind='entry', cash_unit=entry, swap_unit=0.,
                  closed_volume_fraction=0., deal_id=pid*10)]
    if fractions is None:
        fractions = [] if censored else [(cl, 1., profit)]
    for j, (stamp, fraction, amount) in enumerate(fractions, 1):
        flows.append(dict(epoch=stamp, kind='exit', cash_unit=amount, swap_unit=0.,
                          closed_volume_fraction=fraction, deal_id=pid*10+j))
    return dict(key=key, id=f'{key}|{pid}', op=op, cl=cl, symbol=symbol,
                unit_risk=risk, entry_unit_cash=entry, margin_unit_proxy=margin,
                flows=flows, end_censored=censored, variant_group=key)


def run(rows, risk=10, start=0, end=10000, symbols=None, stress=False):
    return s.replay(s.build_events(rows, {r['key'] for r in rows}),
                    symbols or specs(), risk, start, end, True, stress)


def test_minimum_lot_is_skipped_not_rounded_up():
    r = run([row(risk=10000)], risk=1)
    assert r['counts']['minimum_lot'] == 1
    assert r['ending_closed_cash'] == 100
    assert not r['closed_positions']


def test_volume_step_floors_and_maximum_caps():
    r = run([row(risk=300.)], symbols=specs(volume_step=.02, volume_max=.02))
    assert r['decisions'][0]['volume'] == .02
    assert r['decisions'][0]['planned_stop_risk'] == 6


def test_exact_minimum_is_admitted():
    r = run([row(risk=1000.)], risk=10)
    assert r['counts']['opened'] == 1
    assert r['closed_positions'][0]['lots'] == .01


def test_entry_fees_book_at_entry_rounded_to_cash_cents():
    r = run([row(entry=-.17, profit=0.)], risk=30)
    assert r['curve'][1]['balance'] == 99.95
    assert r['closed_positions'][0]['net'] == -.05
    assert r['ending_closed_cash'] == 99.95


def test_compounding_uses_only_closed_cash_not_next_outcome():
    first = row(pid=1, op=100, cl=200, profit=1000.)
    second = row(pid=2, op=300, cl=400, profit=100.)
    r = run([first, second])
    assert [t['lots'] for t in r['closed_positions']] == [.1, .2]
    assert r['ending_closed_cash'] == 220
    second['flows'][-1]['cash_unit'] = -100.
    changed = run([first, second])
    assert [d['volume'] for d in changed['decisions']] == [.1, .2]


def test_no_carry_in_ownership_and_ignored_foreign_close():
    r = run([row(pid=1, op=-100, cl=100, profit=100000.),
             row(pid=2, op=200, cl=300, profit=0.)], start=0)
    assert r['counts']['candidates'] == 1
    assert r['ending_closed_cash'] == 100
    assert len(r['closed_positions']) == 1


def test_partial_exits_keep_original_risk_and_margin_until_final():
    first = row(fractions=[(200,.5,0.), (400,.5,0.)], margin=10)
    second = row(key='b',pid=2,op=300,cl=500,profit=100.)
    r = run([first,second])
    assert r['decisions'][1]['decision'] == 'same_symbol_risk'
    assert r['ending_closed_cash'] == 100
    assert len(r['closed_positions']) == 1
    assert r['closed_positions'][0]['cl'] == 400


def test_partial_exit_cash_is_available_to_later_compounding():
    first = row(fractions=[(200,.5,1000.),(400,.5,0.)])
    second = row(key='b',pid=2,op=300,cl=500,profit=0.,symbol='B')
    r = run([first,second])
    assert r['decisions'][1]['budget'] == 20
    assert r['decisions'][1]['volume'] == .2
    assert r['closed_positions'][0]['net'] == 100


def test_target_waits_for_flat_and_final_loss_can_cancel_it():
    rows = [row(fractions=[(200,.5,100000.),(400,.5,-10000.)]),
            row(key='b',pid=2,op=300,cl=350,profit=1.,symbol='B')]
    r = run(rows)
    assert r['decisions'][1]['decision'] == 'target_waiting_flat'
    assert r['status'] == 'timeout'
    assert r['ending_closed_cash'] == 9100


def test_success_only_after_final_natural_exit():
    r = run([row(fractions=[(200,.5,100000.),(400,.5,0.)])])
    assert r['status'] == 'hit'
    assert r['hit_epoch'] == 400
    assert r['open_positions'] == 0


def test_floor_latches_even_if_existing_position_recovers():
    rows = [row(fractions=[(200,.5,-900.),(400,.5,1000.)]),
            row(key='b',pid=2,op=300,cl=500,symbol='B')]
    r = run(rows)
    assert r['status'] == 'floor'
    assert r['floor_epoch'] == 200
    assert r['ending_closed_cash'] == 110
    assert r['decisions'][1]['decision'] == 'floor_latched'


def test_daily_pause_latches_until_utc_next_day():
    rows = [row(pid=1,op=100,cl=200,profit=-200.),
            row(pid=2,op=300,cl=400,profit=100.),
            row(pid=3,op=s.DAY+100,cl=s.DAY+200,profit=100.)]
    r = run(rows,end=2*s.DAY)
    assert [d['decision'] for d in r['decisions']] == ['opened','daily_pause','opened']
    assert r['decisions'][2]['budget'] == 8


def test_aggregate_and_symbol_limits_are_separate():
    rows = [row(key='a',pid=1,op=100,cl=900,symbol='A'),
            row(key='b',pid=2,op=200,cl=900,symbol='B'),
            row(key='c',pid=3,op=300,cl=900,symbol='C')]
    r = run(rows)
    assert [d['decision'] for d in r['decisions']] == ['opened','opened','aggregate_risk']
    rows[1]['symbol'] = 'A'
    r = run(rows[:2])
    assert r['decisions'][1]['decision'] == 'same_symbol_risk'


def test_margin_protected_cash_uses_initial_risk_and_entry_fee():
    r = run([row(margin=720.,entry=-1.)])
    assert r['decisions'][0]['decision'] == 'margin_proxy'
    r = run([row(margin=719.)])
    assert r['decisions'][0]['decision'] == 'opened'


def test_stress_adds_spread_each_side_and_doubles_negative_swap():
    candidate = row(profit=95.)
    candidate['flows'][-1]['swap_unit'] = -5.
    a, b = run([candidate]), run([candidate],stress=True)
    assert a['ending_closed_cash'] == 109.5
    assert b['ending_closed_cash'] == 108.8
    assert b['closed_positions'][0]['net'] == 8.8


def test_stress_positive_swap_not_doubled():
    candidate = row(profit=105.)
    candidate['flows'][-1]['swap_unit'] = 5.
    b = run([candidate],stress=True)
    assert b['ending_closed_cash'] == 110.3


def test_stress_doubles_margin_proxy_before_admission():
    candidate = row(margin=400.)
    assert run([candidate])['decisions'][0]['decision'] == 'opened'
    assert run([candidate],stress=True)['decisions'][0]['decision'] == 'margin_proxy'


def test_censored_position_is_not_artificially_liquidated():
    r = run([row(entry=-1.,censored=True)])
    assert r['status'] == 'timeout'
    assert r['open_positions'] == 1
    assert r['ending_closed_cash'] == 99.9
    assert not r['closed_positions']


def test_end_boundary_is_exclusive_for_entries_and_exits():
    r = run([row(pid=1,op=100,cl=1000),row(pid=2,op=1000,cl=2000)],end=1000)
    assert r['counts']['candidates'] == 1
    assert r['open_positions'] == 1
    assert r['ending_closed_cash'] == 100


def test_closes_before_unrelated_same_stamp_opens_and_lexical_entries():
    rows = [row(key='z',pid=1,op=100,cl=200,profit=1000.),
            row(key='b',pid=2,op=200,cl=400,symbol='A'),
            row(key='a',pid=3,op=200,cl=400,symbol='A')]
    r = run(rows)
    assert [(d['key'],d['budget'],d['decision']) for d in r['decisions'][1:]] == [
        ('a',20.,'opened'),('b',20.,'same_symbol_risk')]


def test_publisher_epsilon_allows_same_native_second_owned_exit():
    r = run([row(op=100.,cl=100.001)])
    assert len(r['closed_positions']) == 1


def attempt(status='hit', days=10, cash=10000, dd=10):
    return dict(status=status,hit_days=days if status=='hit' else None,
        start=0,hit_epoch=days*s.DAY if status=='hit' else None,
        ending_closed_cash=cash,max_closed_dd_pct=dd,counts={},no_admitted_positions=False)


def test_summary_rates_and_failure_capped_completion_mean():
    result = s.summarize([attempt(),attempt('floor',cash=10),attempt('timeout',cash=100)])
    assert result['hit_pct'] == pytest.approx(100/3)
    assert result['floor_pct'] == pytest.approx(100/3)
    assert result['all_start_median_days'] is None
    assert result['mean_capped_days'] == pytest.approx((10+365+365)/3)


def test_all_start_median_is_ordinary_median_when_all_complete():
    result = s.summarize([attempt(days=d) for d in (10,20,30,40)])
    assert result['all_start_median_days'] == 25


def test_exact_half_completion_has_no_finite_ordinary_median():
    result = s.summarize([attempt(days=10),attempt(days=20),attempt('timeout'),attempt('floor')])
    assert result['all_start_median_days'] is None


def test_qualified_selection_faster_then_rate_then_dd_then_id():
    def c(ident,hit,days,dd=10):
        return dict(id=ident,summary=dict(hit_pct=hit,median_hit_days=days,
            median_closed_dd_pct=dd,mean_capped_days=300,ending_cash_median=100))
    assert min([c('slow',100,20),c('fast',50,10)],key=s.rank)['id'] == 'fast'
    assert min([c('a',60,10),c('b',70,10)],key=s.rank)['id'] == 'b'
    assert min([c('a',60,10,15),c('b',60,10,10)],key=s.rank)['id'] == 'b'
    assert min([c('a',60,10),c('b',60,10)],key=s.rank)['id'] == 'a'


def test_unqualified_selection_uses_rate_not_fast_lottery():
    a=dict(id='a',summary=dict(hit_pct=49,median_hit_days=100,median_closed_dd_pct=90,
        mean_capped_days=300,ending_cash_median=100))
    b=dict(id='b',summary=dict(hit_pct=1,median_hit_days=1,median_closed_dd_pct=20,
        mean_capped_days=350,ending_cash_median=500))
    assert min([a,b],key=s.rank)['id'] == 'a'


def test_weekly_starts_are_mondays_and_have_complete_followup():
    starts=s.weekly_starts(['2024-10-06','2026-10-06'])
    assert len(starts) == 53
    assert all(s.datetime.fromtimestamp(t,s.timezone.utc).weekday()==0 for t in starts)
    assert all(t+365*s.DAY <= s.epoch('2026-10-06') for t in starts)


def test_config_is_order_invariant_and_retains_risk():
    assert s.config(['b','a'],5) == dict(id='a+b@5',keys=['a','b'],risk_pct=5)


@pytest.mark.parametrize('q,expected',[(0,1),(.25,1.75),(.5,2.5),(1,4)])
def test_quantile_linear_interpolation(q,expected):
    assert s.quantile([4,1,3,2],q)==expected


@pytest.mark.parametrize('case,stressed',[(i,stress) for i in range(8) for stress in (False,True)])
def test_independent_reimplementation_synthetic_parity(case,stressed):
    spec=importlib.util.spec_from_file_location('challenge_independent_fixture',ROOT/'independent_verify.py')
    verifier=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    samples=[
        [row(entry=-.17,profit=100.)],
        [row(risk=10000.)],
        [row(fractions=[(200,.5,1000.),(500,.5,-200.)]),row(key='b',pid=2,op=300,cl=600,symbol='B')],
        [row(fractions=[(200,.5,-900.),(500,.5,1000.)]),row(key='b',pid=2,op=300,cl=600,symbol='B')],
        [row(fractions=[(200,.5,100000.),(500,.5,0.)])],
        [row(censored=True,entry=-2.)],
        [row(key=k,pid=i,op=100+i*100,cl=1000,symbol=sy) for i,(k,sy) in enumerate(zip('abc','ABC'),1)],
        [row(op=-100,cl=200),row(pid=2,op=300,cl=400,profit=-200.),
         row(pid=3,op=500,cl=600),row(pid=4,op=s.DAY+100,cl=s.DAY+200)]
    ]
    rows=samples[case]
    events=s.build_events(rows,{p['key'] for p in rows})
    expected=s.replay(events,specs(),10,0,2*s.DAY,True,stressed)
    actual=verifier.independent_attempt(verifier.events_for(rows,{p['key'] for p in rows}),
        specs(),10,0,2*s.DAY,True,stressed)
    verifier.equivalent(expected,actual)


def test_independent_summary_matches_failures_and_even_completed_median():
    spec=importlib.util.spec_from_file_location('challenge_independent_summary_fixture',ROOT/'independent_verify.py')
    verifier=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    for attempts in ([attempt(days=x) for x in (10,20,30,40)],
                     [attempt(days=10),attempt(days=20),attempt('floor'),attempt('timeout')],
                     [attempt(days=10),attempt('timeout'),attempt('timeout')]):
        verifier.equivalent(s.summarize(attempts),verifier.summary_of(attempts))
