"""Read-only independent audit of the requested Nasdaq + RSI-only subset.

The imported audit is a separate event engine, not run.py/ResearchReplay. Source
receipt and captured-mark audits cover all original evidence before subsetting.
Only this folder's VERIFICATION.json is written.
"""
from pathlib import Path
from datetime import datetime
import importlib.util
import json


ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
ORIGINAL = PARENT.parent
SPEC = importlib.util.spec_from_file_location('separate_five_percent_audit', PARENT/'independent_verify.py')
auditor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(auditor)
load, digest, require = auditor.load, auditor.digest, auditor.require
SELECTED = frozenset(('xau-rsi-vwap', 'nasdaq-5m-candle-momentum'))


def cost_paths(records, decisions):
    diagnostics = []
    for name in ('fixed50', 'compound5'):
        a = next(r for r in records if r['scenario']['id'] == name and not r['stress'])
        b = next(r for r in records if r['scenario']['id'] == name and r['stress'])
        divergence = next(((left, right) for left, right in zip(decisions[(name, False)], decisions[(name, True)])
                           if (left['reason'] == 'opened') != (right['reason'] == 'opened')), None)
        known = {t['id']: t for t in a['trades']}
        paired = []
        for t in b['trades']:
            original = known.get(t['id'])
            if original and abs(original['lots']-t['lots']) < 1e-10:
                require(t['net'] <= original['net']+1e-8, 'Higher cost improved identical-volume trade', 'cost_pairing')
                paired.append(dict(id=t['id'], volume=t['lots'], recorded_net=original['net'], stressed_net=t['net']))
        diagnostics.append(dict(scenario=name, matched_same_volume=paired,
            first_admission_divergence_utc=auditor.isoclock(divergence[0]['epoch']) if divergence else None,
            first_admission_divergence=dict(recorded=divergence[0], stress=divergence[1]) if divergence else None,
            interpretation='Cost and compounding changes can alter later guard admissions; aggregate outcomes are not assumed to be identical-trade cost comparisons.'))
    return diagnostics


def risk_mode_paths(records, decisions):
    diagnostics = []
    for stress in (False, True):
        fixed, compound = decisions[('fixed50', stress)], decisions[('compound5', stress)]
        differing_lots = next(((a, b) for a, b in zip(fixed, compound)
                               if abs(a['volume']-b['volume']) > 1e-9), None)
        differing_admission = next(((a, b) for a, b in zip(fixed, compound)
                                    if (a['reason'] == 'opened') != (b['reason'] == 'opened')), None)
        def evidence(pair):
            if pair is None:
                return None
            q = dict(utc=auditor.isoclock(pair[0]['epoch']), fixed=pair[0], compound=pair[1])
            for label, name, trace in (('fixed', 'fixed50', pair[0]), ('compound', 'compound5', pair[1])):
                record = next(r for r in records if r['scenario']['id'] == name and r['stress'] is stress)
                trade = next((t for t in record['trades'] if t['id'] == trace['id']), None)
                q[label+'_closed_trade'] = trade
            return q
        diagnostics.append(dict(stress=stress,
            first_lot_difference=evidence(differing_lots),
            first_admission_difference=evidence(differing_admission),
            interpretation='Compounding changes lot steps and reserved-risk admission, not only scaling of an identical realized trade list. This short two-month outcome is highly path dependent.'))
    return diagnostics


def main():
    results, frozen, plan = (load(ROOT/name) for name in ('RESULTS.json', 'FROZEN.json', 'PLAN.json'))
    original_frozen = load(ORIGINAL/'FROZEN.json')
    original_data, native = load(ORIGINAL/'INPUTS.json'), load(ORIGINAL/'native_cases.json')
    original_plan, broker = load(ORIGINAL/'PLAN.json'), load(ORIGINAL/'BROKER.json')
    auditor.source.verify_sources(original_data, native, original_frozen)
    begin, end = (int(datetime.fromisoformat(original_plan[key]).timestamp())
                  for key in ('start_utc', 'end_exclusive_utc'))
    auditor.verify_native_mark_values(original_data, native, begin, end)
    for ancestor in (ORIGINAL, PARENT, ROOT):
        f = load(ancestor/'FROZEN.json')
        for path, expected in {**f['files'], **f.get('source_files', {})}.items():
            require(digest(path) == expected, ('Frozen ancestry changed', str(ancestor), path), 'subset_freeze')
    require(any(frozen.get(key) is True for key in (
        'frozen_before_new_outcomes', 'frozen_before_outcomes', 'frozen_before_subset_outcomes')),
        'Subset pre-outcome freeze declaration missing', 'subset_freeze')
    require(results['frozen_sha256'] == digest(ROOT/'FROZEN.json'), 'Subset result freeze receipt', 'subset_freeze')
    require(results['plan'] == plan and results['broker'] == broker, 'Published subset protocol/broker differs', 'subset_protocol')
    require(set(results['selected']) == SELECTED, 'Requested exact two-EA subset changed', 'subset_protocol')
    data = dict(original_data,
        candidates=[q for q in original_data['candidates'] if q['ea'] in SELECTED],
        coverage=[q for q in original_data['coverage'] if q['ea'] in SELECTED])
    require(len(data['candidates']) == 42 and len(data['coverage']) == 2, 'Wrong subset source counts', 'subset_protocol')
    require(results['source_candidates'] == 42, 'Published subset candidate count differs', 'subset_protocol')
    require(results['coverage'] == data['coverage'], 'Published subset coverage differs', 'subset_protocol')
    priority = [ea for ea in original_plan['priority'] if ea in SELECTED]
    require(priority == ['xau-rsi-vwap', 'nasdaq-5m-candle-momentum'], 'Wrong relative source priority', 'subset_protocol')
    require(plan['priority'] == priority, 'Frozen subset priority changed', 'subset_protocol')
    pair_keys = [(r['scenario']['id'], r['stress']) for r in results['results']]
    require(len(pair_keys) == 4 and set(pair_keys) == {
        ('fixed50', False), ('fixed50', True), ('compound5', False), ('compound5', True)},
        'Exactly two requested risks times two costs expected', 'subset_protocol')
    derived = dict(original_plan, priority=priority)
    summaries, decisions = [], {}
    for record in results['results']:
        require(record['scenario']['guard_policy'] == 'research_10daily_20total', 'Inherited research guard changed', 'subset_protocol')
        require({p['ea'] for p in record['decisions']} == SELECTED and len(record['decisions']) == 42,
                'An unrelated EA entered subset event stream', 'subset_protocol')
        summary, trace = auditor.audit(record, data, derived, plan, broker)
        summary.update(closed_position_net_profit=record['metrics']['net_profit'],
            open_position_entry_cash=round(sum(p['paid_entry_cash'] for p in record['open_positions']), 2),
            ending_unrealized_sampled_profit=record['metrics']['ending_sampled_equity']-record['metrics']['ending_balance'])
        summaries.append(summary)
        decisions[(record['scenario']['id'], record['stress'])] = trace
    diagnostics = cost_paths(results['results'], decisions)
    risk_diagnostics = risk_mode_paths(results['results'], decisions)
    payload = dict(status='PASS', checks=sum(auditor.source.CHECKS.values()),
        categories=dict(auditor.source.CHECKS), selected=sorted(SELECTED),
        verified_subset_candidates=42, verified_source_candidates=93, source_eas=9, selected_eas=2,
        scenarios=summaries, cost_path_diagnostics=diagnostics, risk_mode_path_diagnostics=risk_diagnostics,
        results_sha256=digest(ROOT/'RESULTS.json'), freeze_sha256=digest(ROOT/'FROZEN.json'),
        verifier_sha256=digest(__file__), independent_engine_sha256=digest(PARENT/'independent_verify.py'),
        method=('Separate independent event engine, without importing the subset run.py, ResearchReplay or original replay.py. '
            'Reconstructs all original native receipts and captured mark values, filters only the two requested EAs without changing '
            'signals, and verifies every subset sizing/guard decision, chronological curve point, fee/swap/cash event, whole position, '
            'censored entry fee, daily/monthly cash, drawdown and Sharpe. All frozen ancestor and subset files remain unchanged.'),
        limitations=[
            'Numerical/source-evidence verification is not a durable-edge or future-return guarantee.',
            'Current source strategies, including existing DI settings, are unchanged. Subsetting is not signal or parameter optimization.',
            'Historical Trial16 fills and Trial15 demo specifications differ; higher size is a linear immutable-fill replay, not a native simultaneous same-demo backtest.',
            'Unavailable later signals, historical liquidity/fees/margin regimes and intrabar guard excursions cannot be reconstructed.',
            'The $800 stop threshold is an initial-capital admission floor; it is not forced liquidation or a trailing 20% drawdown cap.'
        ])
    (ROOT/'VERIFICATION.json').write_text(json.dumps(payload, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
