"""Frozen 37-member full roster: native signals, offline shared-balance replay.

Isolated tester only. No live-account API, installation or production writes.
One research process at a time; an occupied terminal is never stopped.
"""
from pathlib import Path
import copy, gzip, hashlib, importlib.util, inspect, json, msvcrt, os, re, sys, time, traceback

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
LONG=BASE/'Portfolio Long History 2026-10-08'
START,END='2026-09-25','2026-10-09'
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(LONG))
spec=importlib.util.spec_from_file_location('shared_two_week_native',LONG/'run.py')
l=importlib.util.module_from_spec(spec);spec.loader.exec_module(l)
l.ROOT=ROOT
n=l.n
n.R=ROOT;n.START=START.replace('-','.');n.END=END.replace('-','.')

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def frozen_plan():
    original=read(LONG/'PLAN.json')
    index={r['case_id']:r for r in original['cases']}
    cases=[]
    for slug,case_id in original['mappings']['full-eas'].items():
        row=copy.deepcopy(index[case_id])
        row['source_case_id']=case_id
        if slug.startswith('news-pulse-'):
            row['input_settings'].update(InpRiskPercent='0.10',InpTesterFromDateUTC=START.replace('-',''),InpTesterToDateUTC=END.replace('-',''))
        if slug.endswith('hourly-profiles'):
            row['input_settings']['InpAuditTag']='shared-two-week-'+slug
        signature=hashlib.sha256(json.dumps([row['source'],row['input_settings']],sort_keys=True).encode()).hexdigest()[:12]
        row['case_id']=slug+'-'+signature
        assert not row['candidate_overrides']
        assert all(n.sha(Path(p))==v for p,v in row['production_hashes'].items()),('Production settings changed',slug)
        cases.append(row)
    publication=read(BASE.parent/'EA store/data/portfolios.json')
    current=next(p for p in publication['portfolios'] if p['slug']=='full-eas')
    assert {m['slug'] for m in current['members']}=={r['slug'] for r in cases}
    assert len(cases)==37
    plan=dict(start=START,end_exclusive=END,roster='full-eas',cases=cases,selection_frozen=True,
        initial_balance=10000,normal_risk_percent=1.0,news_risk_percent_per_order=.10,
        retain_adaptive_controls=True,no_extra_custom_daily_guard=True,native_simultaneous_portfolio=False,
        source_plan_sha256=n.sha(LONG/'PLAN.json'),production_publication_sha256=n.sha(BASE.parent/'EA store/data/portfolios.json'),
        model=4,execution_delay_ms=150,carry_in=False,exclude_tester_end_liquidations=True,
        actual_tick_times_treated_as_utc=True,live_changes=False)
    path=ROOT/'PLAN.json'
    if path.exists():assert read(path)==plan,'Frozen plan changed'
    else:n.save(path,plan)
    return plan

def prepare_calendar():
    path=BASE/'US100 News Reversion Pipeline 2020-2024 2026-10-08/calendar.json'
    original=read(path)
    events=[e for e in original['events'] if START<=e['release_utc'][:10]<END]
    assert len(events)==1 and events[0]['kind']=='NFP' and events[0]['release_utc']=='2026-10-02T12:30:00+00:00'
    assert all(e.get('source') and e.get('receipt') for e in events)
    digest=hashlib.sha256(json.dumps([(e['epoch'],e['kind']) for e in events],separators=(',',':')).encode()).hexdigest()
    n.save(ROOT/'Calendar.json',dict(source=str(path),source_sha256=n.sha(path),coverage_start=START,end_exclusive=END,events=events,
        verified_online='2026-10-09',calendar_vintage_verified=False,
        checked_sources=['https://www.bls.gov/schedule/2026/09_sched.htm','https://www.bls.gov/schedule/2026/10_sched.htm','https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm'],
        note='NFP only in the selected window; FOMC minutes are not the watched rate-decision event. Schedule receipt, not historical AI predictions.'))
    include='''// Official-source schedule; isolated tester only, not a point-in-time calendar vintage.
#ifndef CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define NP_TESTER_CALENDAR_COVERAGE_START_DATE 20260925
#define NP_TESTER_CALENDAR_COVERAGE_END_DATE 20261009
#define NP_TESTER_CALENDAR_EXPECTED_EVENTS 1
long NP_GENERATED_EVENT_UTC_EPOCHS[]={1790944200};
string NP_GENERATED_EVENT_KINDS[]={"NFP"};
string NP_GeneratedCalendarProvider(){return "Official BLS + Federal Reserve; receipted chronology";}
string NP_GeneratedCalendarHash(){return "'''+digest+'''";}
string NP_GeneratedCalendarFetchedAt(){return "2026-10-09";}
int NP_GeneratedCalendarEventCount(){return ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);}
#endif
'''
    (ROOT/'HistoricalCalendar.mqh').write_text(include,encoding='utf-8')

def prepare_helpers():
    l.prepare_helpers()
    # Respect the requested 0.10% native news-order setting rather than the old
    # helper's universal 1% diagnostic default. Entry rules remain frozen.
    # The verified helper is generated with exec, so obtain its original text
    # directly and apply the same verifier generalization explicitly.
    source=inspect.getsource(read_original_runner())
    old="required=['InpRiskPercent','InpRR05AuditTag',*row['candidate_overrides']]"
    assert source.count(old)==1
    source=source.replace(old,"required=['InpRR05AuditTag',*row['candidate_overrides']]")
    old="inputs['InpRiskPercent']='1.0'"
    assert source.count(old)==1
    source=source.replace(old,"inputs['InpRiskPercent']=row['input_settings'].get('InpRiskPercent','1.0')")
    exec(compile(source,str(ROOT/'run.py')+'::native_runner','exec'),n.__dict__)
    parity=read(LONG/'Calendar Lookup Parity/VERIFICATION.json')
    assert parity['version']==l.CALENDAR_SEARCH_VERSION and all(parity[k] for k in
        ('native_trades_identical','native_cash_flows_identical','native_report_identical','production_files_unchanged'))

def read_original_runner():
    spec=importlib.util.spec_from_file_location('shared_two_week_original',l.PRIOR/'run.py')
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    return original.run_case

def main():
    plan=frozen_plan();prepare_calendar();prepare_helpers()
    state=dict(window=[START,END],total=37,complete={},failed={},missing={},live_changes=False)
    status_path=ROOT/'RUN_STATUS.json'
    if status_path.exists():state=read(status_path)
    for row in plan['cases']:
        case=row['case_id']
        if case in state['complete'] or case in state['missing']:continue
        if sys.argv[1:] and sys.argv[1]!='all' and row['slug'] not in sys.argv[1:]:continue
        if row['slug']=='gold-news-v9-direction':
            state['missing'][case]='No historical timestamped V9 AI direction/confidence ledger; live HTTP/file bridge intentionally not called. Not assigned zero P/L.'
            n.save(status_path,state);continue
        try:
            binary,build=n.build(row)
            result=n.run_case(row,'two-week-'+case.split('-')[-1],binary,build)
            if row['slug'].startswith('news-pulse-'):
                journal=gzip.decompress((ROOT/'native'/result['tag']/'journal.txt.gz').read_bytes()).decode()
                assert 'NP_RESEARCH_BAD_CALENDAR_ORDER' not in journal
                found=set(re.findall(r'News Pulse tester calendar audit: expected=(\d+), attempted=(\d+), successfully placed=(\d+), boundary violation=(YES|NO)',journal))
                assert len(found)==1,('Calendar audit missing/ambiguous',found)
                expected,attempted,placed,boundary=next(iter(found))
                enabled=sum(row['input_settings'].get('InpWatch'+e['kind'],'true')=='true' for e in read(ROOT/'Calendar.json')['events'])
                assert int(expected)==enabled and boundary=='NO' and 0<=int(placed)<=int(attempted)<=enabled
                result['calendar_audit']=dict(expected=int(expected),attempted=int(attempted),placed=int(placed),boundary_violation=False,lookup_parity_verified=True)
                n.save(ROOT/'native'/result['tag']/'results.json',result)
            path=ROOT/'native'/result['tag']/'results.json'
            state['complete'][case]=dict(path=str(path),sha256=n.sha(path),trades=len(result['trades']),history_quality=result['native']['history_quality'])
            state['failed'].pop(case,None)
        except Exception as error:
            state['failed'][case]=dict(error=str(error),trace=traceback.format_exc()[-5000:])
            print('CASE FAILED '+case+': '+str(error),flush=True)
        n.save(status_path,state)
        print('PROGRESS '+str(len(state['complete']))+'/37 complete; '+str(len(state['failed']))+' failed; '+str(len(state['missing']))+' explicit gaps',flush=True)
    assert all(n.sha(Path(p))==v for row in plan['cases'] for p,v in row['production_hashes'].items())
    print('BATCH FINISHED; production unchanged, no live changes',flush=True)

if __name__=='__main__':
    with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
        # Another research job need not use the lease. Check the dedicated
        # terminal as well; never stop an occupied terminal to free it.
        deadline=time.monotonic()+900
        while True:
            try:n.available();break
            except AssertionError:
                if time.monotonic()>deadline:raise
                print('WAIT: independent research tester occupied; other process left untouched',flush=True)
                time.sleep(30)
        main()
