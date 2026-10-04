"""Final read-only evidence coverage and unchanged production verification."""
from pathlib import Path
import gzip,hashlib,json,os
R=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    rows=read(R/'SUMMARY.json');bots=read(R/'bots.json');parity=read(R/'PARITY.json');nom=read(R/'NOMINATIONS.json')
    decisions=read(R/'DECISION.json');assert len(decisions)==5 and not any(x['promoted'] for x in decisions)
    assert len([r for r in rows if r['window']=='1y' and not r['original']])==37
    assert len(parity)==5 and all(v['identical_entry_exit_volume_costs'] for v in parity.values())
    assert len([r for r in rows if r['window']=='3m' and r['original']])==5
    untouched={}
    for key,b in bots.items():
        checks={b['source']:b['source_sha'],b['original']:b['original_sha'],b['setting']:b['set_sha'],**b['helpers']}
        assert all(digest(Path(p))==v for p,v in checks.items());untouched[key]=checks
        if nom[key]['variant']:
            v=nom[key]['variant']
            for window in ('3m','3y','5y'):
                assert any(r['ea']==key and r['window']==window and not r['original'] and r['variant']==v for r in rows)
                assert any(r['ea']==key and r['window']==window and (r['original'] or r['variant']=='BASE') for r in rows)
    cases=list((R/'native').glob('*/result.json'))
    for p in cases:
        result=read(p);manifest=read(p.parent/'manifest.json')
        assert hashlib.sha256(gzip.decompress((p.parent/'report.htm.gz').read_bytes())).hexdigest()==result['report_sha']
        assert manifest['protocol_sha']==digest(R/'PROTOCOL.txt') and manifest['delay_ms']==150 and manifest['model']==4
    report=(R/'Results.html').read_text();assert 'Partial — research still running' not in report
    prior=R/'before-common/trio-ledger.csv'
    shared=Path(os.environ['APPDATA'])/'MetaQuotes/Terminal/Common/Files/Calyx3WayGold/ledger.csv'
    assert prior.is_file() and shared.is_file() and digest(prior)==digest(shared)
    outcome=dict(complete=True,year_configurations=37,original_parity_controls=5,native_runs=len(cases),
        nominal_year_risk_pct=1.0,dates='2025-10-02 to 2026-10-02 exclusive',
        baseline_matching_trades={k:v['trades'] for k,v in parity.items()},
        production_source_binary_set_helpers_unchanged=True,verified_hashes=untouched,
        independent_validation=False,production_promoted=False,live_mt5_changed=False,prior_common_research_ledger_restored=True,
        limitations=['Retrospective multiple-filter selection','Quarter and long windows overlap searched year',
          '1y 75%, 3y 25%, 5y 15% real ticks; generated ticks cover gaps','No shared portfolio or FTMO payout simulation',
          '3 Way partial exits grouped by position; reconstructed daily Sharpe books final-close cash'])
    (R/'VERIFICATION.json').write_text(json.dumps(outcome,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in outcome.items() if k!='verified_hashes'},indent=2))
if __name__=='__main__':main()
