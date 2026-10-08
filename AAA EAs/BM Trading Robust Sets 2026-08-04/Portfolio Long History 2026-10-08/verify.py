"""Independent read-only publication / native-ledger reconciliation.

Never imports a live trading API or starts a terminal. Pending histories are
reported as pending, not treated as zero P/L. Run again after the batch ends.
"""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, hashlib, importlib.util, json, math, re

ROOT=Path(__file__).resolve().parent
WEB=ROOT.parent.parent/'EA store'
CONTRACTS={'XAUUSD':100.,'XAGUSD':5000.,'USTEC':1.,'US30':1.,
           'BTCUSD':1.,'ETHUSD':1.,'EURUSD':100000.,'USDJPY':100000.}


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    plan=read(ROOT/'PLAN.json');state=read(ROOT/'RUN_STATUS.json')
    audit=read(ROOT/'AUDIT.json');publication=read(WEB/'data/portfolios.json')
    histories=read(ROOT/'HISTORIES.json');risk=read(ROOT/'RISK_ROWS.json')
    index={r['case_id']:r for r in plan['cases']}
    finished=set(state['complete'])|set(state['failed'])|set(state['missing'])
    assert not (set(state['complete']) & (set(state['failed'])|set(state['missing'])))
    assert finished<=set(index)
    assert audit['pending_cases']==len(set(index)-finished)
    assert audit['production_files_unchanged'] and audit['selection_frozen']
    assert publication['risk_ledger_sha256']==sha(WEB/'data/portfolio-risk-ledgers.json')
    assert not audit['native_simultaneous_portfolio'] and not audit['live_changes']
    files={p:v for row in plan['cases'] for p,v in row['production_hashes'].items()}
    assert all(sha(p)==v for p,v in files.items())
    checked=set();checked_symbols=set();flags={};native_trades=0
    # Load only parsing/reuse helpers: neither import executes its main runner.
    spec=importlib.util.spec_from_file_location('frozen_validation_helpers',ROOT/'run.py')
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    for case_id,receipt in state['complete'].items():
        path=Path(receipt['path']);assert sha(path)==receipt['sha256']
        native=read(path)
        assert native['slug']==index[case_id]['slug']
        assert native['window']==['2021.10.06','2026.10.06'] and native['no_live_changes']
        assert native['native']['history_quality']
        if native['slug'].startswith('news-pulse-'):
            calendar=native['calendar_audit']
            assert calendar['parity_verified'] and not calendar['boundary_violation']
            chronology=read(ROOT/'Calendar.json')['events']
            expected=sum(native['inputs'].get('InpWatch'+e['kind'],'true')=='true' for e in chronology)
            assert calendar['expected']==expected
            journal=gzip.decompress((path.parent/'journal.txt.gz').read_bytes()).decode()
            found=set(re.findall(r'News Pulse tester calendar audit: expected=(\d+), attempted=(\d+), successfully placed=(\d+), boundary violation=(YES|NO)',journal))
            assert found=={(str(expected),str(calendar['attempted']),str(calendar['placed']),'NO')}
            assert 'NP_RESEARCH_BAD_CALENDAR_ORDER' not in journal
        # Operational role variants must still match the original native ACTIVE
        # strategy settings. Reuse verification refuses unknown default values.
        if receipt.get('verified_same_active_inputs') or native.get('verified_same_active_inputs'):
            assert helper.verified_reuse(index[case_id],plan,state),case_id
        if path in checked:continue
        checked.add(path)
        origin=Path(native.get('original_native_results_path',path)).parent
        assert sha(origin/'report.htm')==native['report_sha256']
        with (origin/'deals.csv').open(encoding='utf-8-sig',newline='') as stream:
            deals=list(csv.DictReader(stream))
        cash=math.fsum(float(d[k]) for d in deals for k in ('gross','commission','swap','fee'))
        assert math.isclose(cash,native['native']['net_profit'],abs_tol=.031),case_id
        assert math.isclose(cash,math.fsum(t['net'] for t in native['trades']),abs_tol=.031),case_id
        assert len({d['deal'] for d in deals})==len(deals)
        positions={}
        for deal in deals:positions.setdefault(int(deal['position_id']),[]).append(deal)
        assert len(positions)==len(native['trades'])
        symbol=index[case_id]['symbol']
        for trade in native['trades']:
            parts=positions[trade['position_id']]
            entries=[d for d in parts if int(d['entry'])==0]
            exits=[d for d in parts if int(d['entry'])==1]
            assert len(entries)==1 and len(exits)==trade['exit_legs']
            assert math.isclose(float(entries[0]['volume']),math.fsum(float(d['volume']) for d in exits),abs_tol=1e-7)
            assert trade['sl']==float(entries[0]['sl'])
            assert trade['volume']==float(entries[0]['volume'])
            # Verify the USD contract conversion against actual native exit
            # profits, per exit leg (including partials). ETHUSD in this tester
            # has multiplier 1, not the archived overlay's assumed 10.
            sign=1 if trade['side']=='Long' else -1
            for leg in exits:
                expected=sign*(float(leg['price'])-trade['open_price'])*float(leg['volume'])*CONTRACTS[symbol]
                if symbol=='USDJPY':expected/=float(leg['price'])
                # MT5 converts positive JPY profit on the opposite quote side;
                # its conversion bid/ask is not exported. Require a tight 0.05%
                # tolerance for JPY only, versus cents for USD-quoted contracts.
                assert math.isclose(expected,float(leg['gross']),rel_tol=.0005 if symbol=='USDJPY' else 0.,abs_tol=.02),(case_id,'Contract/currency conversion')
                checked_symbols.add(symbol)
        assert all(not native['flags'][k] for k in ('init_failed','runtime','history','stopout','export_failed'))
        flags[native['tag']]=native['flags']
        native_trades+=len(native['trades'])
    profiles={p['slug']:p for p in publication['portfolios']}
    for slug,history in histories.items():
        expected=set(plan['mappings'][slug])
        provenance=audit['portfolios'][slug]
        tested={s['slug'] for s in provenance['sources']}
        missing={m['slug'] for m in provenance['missing']}
        assert tested|missing==expected and not tested&missing
        assert expected=={m['slug'] for m in profiles[slug]['members']}
        assert {r['key'] for r in risk[slug]}<=tested
        assert all(r['risk_weight']==(.5 if r['key']=='xau-weakness' else 1.) for r in risk[slug])
        for source in provenance['sources']:
            case=read(state['complete'][source['case_id']]['path'])
            boundary={t['position_id'] for t in case['trades'] if any('end of test' in c.lower() for c in t['exit_comments'])}
            assert source['excluded_boundary_positions']==len(boundary)
            assert not any(r['position_id'] in boundary for r in risk[slug] if r['key']==source['slug'])
        if slug!='full-eas':assert not missing
        for item in history:
            assert item['available'] and item['end_exclusive']=='2026-10-06'
            assert set(item['missing_members'])==missing
            stats=item['stats']
            assert stats['max_daily_equity_drawdown_pct'] is None
            assert math.isclose(stats['final_balance']-stats['initial_balance'],stats['net_profit'],abs_tol=1e-6)
            assert math.isclose(sum(m['net_profit'] for m in item['months']),stats['net_profit'],abs_tol=.05)
            assert math.isclose(item['curve'][-1]['balance'],stats['final_balance'],abs_tol=.05)
            if slug=='full-eas' or item['id'] in ('3y','5y'):
                published=next(h for h in profiles[slug]['history'] if h['id']==item['id'])
                assert published['stats']==stats
                assert published['evidence_kind']==item['evidence_kind']
    result=dict(verified_at=datetime.now(timezone.utc).isoformat(),
        complete_configurations=len(state['complete']),unique_native_receipts=len(checked),
        native_trade_records_checked=native_trades,pending_configurations=len(set(index)-finished),
        failed_configurations=state['failed'],explicit_gaps=state['missing'],ready_profiles=sorted(histories),
        production_files_checked=len(files),production_files_unchanged=True,
        live_changes=False,declared_contract_multipliers=CONTRACTS,
        verified_contract_multipliers={k:CONTRACTS[k] for k in sorted(checked_symbols)},
        jpy_profit_conversion_tolerance_pct=.05,native_flags=flags)
    # This is a generated verification receipt, not a mutation of source inputs.
    (ROOT/'VERIFICATION.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='native_flags'},indent=2))


if __name__=='__main__':main()
