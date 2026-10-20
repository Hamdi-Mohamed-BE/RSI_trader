"""Frozen two-EA subset replay, research only; never accesses MT5/live files.

Filter standalone source candidates BEFORE portfolio admission and sizing.
Do not subtract other EAs from the old portfolio's admitted ledger.
"""
from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
ORIGINAL = PARENT.parent
_spec = importlib.util.spec_from_file_location('frozen_actual_five_percent_engine', PARENT/'run.py')
engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(engine)
base = engine.base
SELECTED = frozenset(('nasdaq-5m-candle-momentum', 'xau-rsi-vwap'))
SCENARIOS = tuple(dict(s) for s in engine.SCENARIOS if s['guard_policy'] == 'research_10daily_20total')


def filtered_inputs(data):
    return {**data,
        'candidates': [row for row in data['candidates'] if row['ea'] in SELECTED],
        'coverage': [row for row in data['coverage'] if row['ea'] in SELECTED]}


def verify_frozen(frozen):
    for p, expected in {**frozen['files'], **frozen['source_files']}.items():
        assert base.sha(p) == expected, ('Frozen file changed', p)


def freeze():
    assert not (ROOT/'RESULTS.json').exists(), 'Never refreeze after outcomes'
    prior = base.read(PARENT/'FROZEN.json')
    verify_frozen(prior)
    data = filtered_inputs(base.read(ORIGINAL/'INPUTS.json'))
    assert {x['ea'] for x in data['coverage']} == SELECTED
    previous_plan = base.read(PARENT/'PLAN.json')
    priority = [ea for ea in base.read(ORIGINAL/'PLAN.json')['priority'] if ea in SELECTED]
    settings = {case['slug']: Path(case['path']).parent/'inputs.set'
        for case in base.read(ORIGINAL/'native_cases.json')['cases'] if case['slug'] in SELECTED}
    assert 'InpRequireDIAgreement=true' in settings['nasdaq-5m-candle-momentum'].read_text(encoding='utf-8-sig')
    plan = {**previous_plan,
        'user_request': 'Only Nasdaq 5M momentum and RSI VWAP Gold, same two-month 1000USD true5% compounding versus fixed50 research comparison.',
        'portfolio': 'Nasdaq 5M + RSI VWAP Gold only',
        'priority': priority,
        'scenarios': SCENARIOS,
        'controls': 'Read-only comparison against matching prior full nine-EA actual-risk outcomes; no new capped/old-guard controls.',
        'selection_method': 'Filter source candidates and coverage BEFORE the chronological admission replay. No optimization or subtraction from old admitted ledgers.',
        'source_candidates': len(data['candidates']),
        'per_ea_candidates': {ea: sum(row['ea'] == ea for row in data['candidates']) for ea in priority},
        'signal_settings': 'Unchanged source logic/settings: Nasdaq DI remains ON as in the frozen Prop Ready default. RSI VWAP unchanged. No new stop/target/filter search.',
        'signal_settings_receipts': {ea: dict(path=str(p), sha256=base.sha(p)) for ea, p in settings.items()},
        'comparison_source': str(PARENT/'RESULTS.json'),
        'comparison_source_sha256': base.sha(PARENT/'RESULTS.json'),
        'default_live_profile_changed': False}
    base.save(ROOT/'PLAN.json', plan)
    files = {str(p): base.sha(p) for p in (
        ROOT/'run.py', ROOT/'test_run.py', ROOT/'PLAN.json',
        PARENT/'FROZEN.json', PARENT/'PLAN.json', PARENT/'RESULTS.json',
        PARENT/'run.py', PARENT/'report.py', ORIGINAL/'PLAN.json',
        ORIGINAL/'INPUTS.json', ORIGINAL/'BROKER.json')}
    original_files = {**prior['files'], **prior['source_files']}
    files.update({str(p): base.sha(p) for p in settings.values()})
    base.save(ROOT/'FROZEN.json', dict(files=files, source_files=original_files,
        frozen_before_new_outcomes=True, filter_before_admission=True))
    print('Frozen two-EA study:', plan['per_ea_candidates'], 'priority:', priority)


def run():
    frozen = base.read(ROOT/'FROZEN.json')
    verify_frozen(frozen)
    plan = base.read(ROOT/'PLAN.json')
    data = filtered_inputs(base.read(ORIGINAL/'INPUTS.json'))
    broker = base.read(ORIGINAL/'BROKER.json')
    assert len(data['candidates']) == plan['source_candidates']
    assert {r['ea'] for r in data['candidates']} <= SELECTED
    events = base.events_for(plan, data)
    results = []
    for stress in (False, True):
        for scenario in SCENARIOS:
            model = engine.ResearchReplay(scenario, broker, stress)
            for t, kind, _, _, row, mark in events:
                if not base.START <= t < base.END:
                    continue
                if kind == 0:
                    model.observe(t)
                elif kind in (1, 4):
                    model.closing(row, t)
                elif kind == 2:
                    model.mark(row, mark, t)
                else:
                    model.opening(row, t)
            result = model.result()
            assert len(result['decisions']) == len(data['candidates'])
            results.append(result)
            print(scenario['id'], 'stress' if stress else 'source costs', result['metrics'], flush=True)
    base.save(ROOT/'RESULTS.json', dict(plan=plan, broker=broker, results=results,
        coverage=data['coverage'], selected=sorted(SELECTED),
        source_candidates=len(data['candidates']),
        frozen_sha256=base.sha(ROOT/'FROZEN.json'),
        original_studies_unchanged=True, generated_at_utc=base.iso(base.datetime.now(base.UTC).timestamp())))


if __name__ == '__main__':
    {'freeze': freeze, 'run': run}[sys.argv[1]]()
