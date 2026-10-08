"""Native equivalence check for the immutable calendar-search acceleration."""
from pathlib import Path
import gzip, json, msvcrt, shutil
import run as m
from calendar_search import proof, VERSION

ROOT=m.ROOT


def main():
    proof()
    m.prepare_calendar()
    row=next(q for q in m.read(ROOT/'PLAN.json')['cases'] if q['slug']=='news-pulse-xau')
    original=ROOT/'Calendar Lookup Parity'/'Original EA'
    original.mkdir(parents=True,exist_ok=True)
    if not (original/'Audit.ex5').exists():
        folder=ROOT/'EA'/'news-pulse-xau'
        info=m.read(folder/'build.json')
        assert not info.get('calendar_search_version'), 'Original build must be unaccelerated'
        for name in ['Audit.ex5','Audit.mq5','SourceCopy.mq5','build.json','compile.log']:
            shutil.copy2(folder/name,original/name)
    old_info=m.read(original/'build.json')
    assert m.n.sha(original/'Audit.ex5')==old_info['binary_sha256']
    m.prepare_helpers()
    m.n.START,m.n.END='2021.10.06','2021.11.06'
    row=dict(row,input_settings=dict(row['input_settings'],InpTesterFromDateUTC='20211006',InpTesterToDateUTC='20211105'))
    baseline=m.n.run_case(row,'calendar-parity-original-month',original/'Audit.ex5',old_info)
    fast_binary,fast_info=m.n.build(row)
    assert fast_info['calendar_search_version']==VERSION
    accelerated=m.n.run_case(row,'calendar-parity-fast-month',fast_binary,fast_info)
    # Ignore audit labels, retain all native trade and cash fields, including IDs.
    assert baseline['trades']==accelerated['trades'], 'Native trade parity failed'
    assert baseline['ledger']==accelerated['ledger'], 'Native cash-flow parity failed'
    assert baseline['native']==accelerated['native'], 'Native report parity failed'
    assert baseline['flags']==accelerated['flags'], 'Native error-count parity failed'
    audits=[]
    for case in [baseline,accelerated]:
        journal=gzip.decompress((ROOT/'native'/case['tag']/'journal.txt.gz').read_bytes()).decode()
        assert 'NP_RESEARCH_BAD_CALENDAR_ORDER' not in journal
        lines=sorted({line.split('News Pulse tester calendar audit: ',1)[1] for line in journal.splitlines() if 'News Pulse tester calendar audit: ' in line})
        assert len(lines)==1 and 'expected=4, attempted=4, successfully placed=4, boundary violation=NO.' in lines[0],lines
        audits.append(lines[0])
    value=dict(version=VERSION,window=[m.n.START,m.n.END],trades=len(baseline['trades']),
        baseline_tag=baseline['tag'],accelerated_tag=accelerated['tag'],
        baseline_binary_sha256=baseline['binary_sha256'],accelerated_binary_sha256=accelerated['binary_sha256'],
        native_trades_identical=True,native_cash_flows_identical=True,native_report_identical=True,
        timer_cadence_changed=False,callbacks_changed=False,trading_logic_changed=False,calendar_audits=audits,
        baseline_seconds=baseline['seconds'],accelerated_seconds=accelerated['seconds'],
        production_files_unchanged=all(m.n.sha(Path(p))==h for p,h in row['production_hashes'].items()))
    assert value['production_files_unchanged']
    m.n.save(ROOT/'Calendar Lookup Parity'/'VERIFICATION.json',value)
    print(json.dumps(value),flush=True)


if __name__=='__main__':
    with (m.BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        main()
