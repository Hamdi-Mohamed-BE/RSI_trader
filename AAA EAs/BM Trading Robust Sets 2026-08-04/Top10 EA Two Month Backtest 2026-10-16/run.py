"""Fresh, fixed-rule standalone native tests. Never a live terminal/API.

prepare: AST-only current recommended settings, frozen sources/binaries/SETs.
run: isolated portable empty-chart tester, sequential native cases only.
No parameter search, no journal data, no portfolio replay, no deployment.
"""
from pathlib import Path
from datetime import datetime, timezone
import copy, gzip, hashlib, importlib.util, inspect, json, msvcrt, os, re, shutil, subprocess, sys, time, traceback

ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
START,END='2026-08-16','2026-10-16'
os.environ['EA_STORE_DISABLE_MT5']='1'
sys.path.insert(0,str(BASE/'Portfolio Long History 2026-10-08'))
spec=importlib.util.spec_from_file_location('two_month_long_helpers',BASE/'Portfolio Long History 2026-10-08/run.py')
l=importlib.util.module_from_spec(spec);spec.loader.exec_module(l)
l.ROOT=ROOT;n=l.n;n.R=ROOT;n.START=START.replace('-','.');n.END=END.replace('-','.')

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):n.save(Path(p),v)

def prepare():
    assert not (ROOT/'RUN_STATUS.json').exists(),'Do not alter a plan after any case starts'
    result=subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'extract_settings.ps1')],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
    assert result.returncode==0,result.stderr
    current=json.loads(result.stdout.lstrip('\ufeff'))
    save(ROOT/'CURRENT-SETTINGS.json',current)
    products=n.get_website_catalog()
    rows=[]
    for item in current:
        binary=Path(item['expert']).resolve();source=binary.with_suffix('.mq5');preset=Path(item['preset']).resolve()
        matches=[p for p in products if any(str((BASE/value).resolve()).casefold()==str(preset).casefold() for value in (p.set_source,p.safe_set_source,p.dynamic_set_source) if value)]
        if not matches:
            matches=[p for p in products if p.label.casefold()==item['label'].casefold()]
        assert len(matches)==1,('Current installer preset must identify exactly one catalogue member',item['label'],str(preset),[p.slug for p in matches])
        p=matches[0]
        inputs={k:str(v).lower() if isinstance(v,bool) else str(v) for k,v in item['inputs'].items()}
        slug=p.slug
        if slug.startswith('news-pulse-'):
            inputs.update(InpTesterFromDateUTC=START.replace('-',''),InpTesterToDateUTC=END.replace('-',''))
        if slug.endswith('hourly-profiles'):
            inputs['InpAuditTag']='two-month-20261016-'+slug
        destination=ROOT/'snapshots'/slug;destination.mkdir(parents=True,exist_ok=True)
        shutil.copy2(binary,destination/'production.ex5');shutil.copy2(preset,destination/'production.set')
        save(destination/'inputs.json',inputs)
        hashes={str(path):sha(path) for path in sorted(n.closure(source)|{binary,preset})}
        row=dict(slug=slug,case_id=slug,label=item['label'],symbol=item['symbol'],period={1:'M1',5:'M5',15:'M15',30:'M30',60:'H1',240:'H4'}[item['period_minutes']],
            expert=str(binary),source=str(source),preset=str(preset),input_settings=inputs,candidate_overrides={},production_hashes=hashes,
            production_binary_snapshot=str(destination/'production.ex5'),production_set_snapshot=str(destination/'production.set'),
            selected_risk_percent=item['selected_risk_percent'],news=item['news'],safe_by_design=item['safe_by_design'],
            historical_loss_sizing=item['historical_loss_sizing'],dedicated_safe_preset=item['dedicated_safe_preset'],dynamic_by_design=item['dynamic_by_design'])
        rows.append(row)
    assert len(rows)==37 and len({r['slug'] for r in rows})==37
    assert len([r for r in rows if r['news']])==5
    calendar_sources=[BASE/'US100 News Reversion Pipeline 2020-2024 2026-10-08/calendar.json',BASE/'XAU CPI Continuation vs Reversion Raw 2026-10-16/calendar.json']
    events={}
    for path in calendar_sources:
        for event in read(path)['events']:
            if START<=event['release_utc'][:10]<END:
                events.setdefault((event['epoch'],event['kind']),event)
    events=sorted(events.values(),key=lambda e:(e['epoch'],e['kind']))
    assert [(e['kind'],e['release_utc']) for e in events]==[
        ('NFP','2026-09-04T12:30:00+00:00'),('CPI','2026-09-11T12:30:00+00:00'),('FOMC','2026-09-16T18:00:00+00:00'),('NFP','2026-10-02T12:30:00+00:00'),('CPI','2026-10-14T12:30:00+00:00')]
    assert all(e.get('source') and e.get('receipt') for e in events)
    save(ROOT/'Calendar.json',dict(start=START,end_exclusive=END,events=events,sources={str(p):sha(p) for p in calendar_sources},calendar_vintage_verified=False,only_schedule_used=True))
    digest=hashlib.sha256(json.dumps([(e['epoch'],e['kind']) for e in events],separators=(',',':')).encode()).hexdigest()
    include='''// Receipted official schedule in a tester-only copy; no historical AI predictions.
#ifndef CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define NP_TESTER_CALENDAR_COVERAGE_START_DATE 20260816
#define NP_TESTER_CALENDAR_COVERAGE_END_DATE 20261016
#define NP_TESTER_CALENDAR_EXPECTED_EVENTS 5
long NP_GENERATED_EVENT_UTC_EPOCHS[]={'''+','.join(str(e['epoch']) for e in events)+'''};
string NP_GENERATED_EVENT_KINDS[]={'''+','.join(json.dumps(e['kind']) for e in events)+'''};
string NP_GeneratedCalendarProvider(){return "Official BLS + Federal Reserve; saved receipted chronology";}
string NP_GeneratedCalendarHash(){return "'''+digest+'''";}
string NP_GeneratedCalendarFetchedAt(){return "2026-10-16";}
int NP_GeneratedCalendarEventCount(){return ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);}
#endif
'''
    (ROOT/'HistoricalCalendar.mqh').write_text(include,encoding='utf-8')
    shutil.copy2(BASE/'All EAs Shared Two Week 2026-10-09/ReadOnlyAudit.mqh',ROOT/'ReadOnlyAudit.mqh')
    plan=dict(prepared_at_utc=datetime.now(timezone.utc).isoformat(),start=START,end_exclusive=END,timezone_convention='Native tester timestamps treated as UTC; completed days through 15 October, not Lagos account-journal snapshot.',
        cases=rows,roster='current Full EA launcher recommended selections; all 37 members',initial_balance=10000,currency='USD',normal_risk_percent=1.0,news_risk_percent_per_order=.10,
        sizing='Fresh native dynamic per-EA risk input; most EAs equity-percent, hourly balance-percent against frozen historical maximum loss distance. Existing broker rounding and split/module allocations retained.',
        adaptive_portfolio_controls=False,standalone_native=True,native_simultaneous_portfolio=False,carry_in=False,model=4,execution_delay_ms=150,
        primary_ranking='Require at least one executed position, then descending native ending net return INCLUDING explicitly flagged end-of-test liquidations; no further minimum sample gate. Zero-trade cases displayed unranked; all 36 reproducible candidates shown. Retrospective selection, not untouched OOS.',
        natural_close_only_secondary=True,optimization=False,live_changes=False,
        explicitly_missing={'gold-news-v9-direction':'No historical pre-release AI direction/confidence ledger. Live HTTP/file bridge will not be called. Not a zero-profit test.'},
        method_changes=['Native risk inputs normalized to 1% normal and 0.10% per news order; portfolio adaptive multipliers disabled for standalone comparability.',
            'Current recommended SafeByDesign, dynamic exits, DI and five 0.5R ORB defaults obtained from pure current installer functions, not stale website settings.',
            'News schedule-only injection and previously parity-verified calendar lookup acceleration; no changes to stops, offsets, order fallback, timing or exit rules.',
            'Tester-only read-only instrumentation and existing harmless baseline-disabled TP accessors from the audited harness; original production source/EX5/SET hashes retained.'],
        configuration_sources={str(p):sha(p) for p in (BASE/'_Auto Deploy/Install-BMTradingPortfolio.ps1',BASE/'_Auto Deploy/News-Launcher-Policy.ps1',BASE/'_00 Live profiles/Start-LiveProfile.ps1',BASE.parent/'EA store/data/portfolios.json')})
    save(ROOT/'PLAN.json',plan)
    freeze_files=[ROOT/'PLAN.json',ROOT/'CURRENT-SETTINGS.json',ROOT/'Calendar.json',ROOT/'HistoricalCalendar.mqh',ROOT/'ReadOnlyAudit.mqh',ROOT/'run.py',ROOT/'extract_settings.ps1']
    dependencies=[BASE/'Portfolio Long History 2026-10-08/run.py',BASE/'Portfolio Long History 2026-10-08/calendar_search.py',BASE/'ORB and Range Breakout RR05 Comparison 2026-10-08/run.py',BASE/'FTMO Exit Management Research 2026-09-27/run.py']
    save(ROOT/'FROZEN.json',dict(frozen_at_utc=datetime.now(timezone.utc).isoformat(),files={str(p):sha(p) for p in freeze_files+dependencies},cases=37,searched_configurations=0,ranking_frozen_before_results=True))
    print(json.dumps(dict(roster=plan['roster'],window=[START,END],risk=[1,.1],calendar_events=len(events),rows=[{k:r[k] for k in ('slug','selected_risk_percent','safe_by_design','historical_loss_sizing')} for r in rows]),indent=2))

def verify_freeze():
    frozen=read(ROOT/'FROZEN.json')
    assert all(sha(p)==v for p,v in frozen['files'].items()),'Frozen study inputs changed'
    plan=read(ROOT/'PLAN.json')
    assert all(sha(p)==v for row in plan['cases'] for p,v in row['production_hashes'].items()),'Production inputs changed'
    return plan

def prepare_helpers():
    l.prepare_helpers()
    spec=importlib.util.spec_from_file_location('two_month_original_case',l.PRIOR/'run.py')
    original=importlib.util.module_from_spec(spec);spec.loader.exec_module(original)
    source=inspect.getsource(original.run_case)
    replacements={
        "inputs['InpRiskPercent']='1.0'":"inputs['InpRiskPercent']=str(row['selected_risk_percent'])",
        "required=['InpRiskPercent','InpRR05AuditTag',*row['candidate_overrides']]":"required=['InpRR05AuditTag',*row['candidate_overrides']]",
        "inputs['InpRR05ModuleTarget']='0';inputs['InpRiskMode']='0';inputs['InpFixedRiskMoney']='0'":"inputs['InpRR05ModuleTarget']='0'",
        "destination=T/'MQL5/Experts/AAA Research/RR05All20261008'":"destination=T/'MQL5/Experts/AAA Research/Top10TwoMonth20261016'",
        "Expert=AAA Research\\\\RR05All20261008\\\\{slug}":"Expert=AAA Research\\\\Top10TwoMonth20261016\\\\{slug}",
        "reports/rr05-all-20261008":"reports/top10-two-month-20261016",
        "Report=reports\\\\rr05-all-20261008\\\\{tag}.htm":"Report=reports\\\\top10-two-month-20261016\\\\{tag}.htm",
    }
    for before,after in replacements.items():
        assert source.count(before)==1,(before,source.count(before))
        source=source.replace(before,after)
    exec(compile(source,str(ROOT/'run.py')+'::fresh_native_case','exec'),n.__dict__)
    parity=read(BASE/'Portfolio Long History 2026-10-08/Calendar Lookup Parity/VERIFICATION.json')
    assert parity['version']==l.CALENDAR_SEARCH_VERSION and all(parity[k] for k in ('native_trades_identical','native_cash_flows_identical','native_report_identical','production_files_unchanged'))

def run():
    plan=verify_freeze();prepare_helpers()
    profile=n.T/'MQL5/Profiles/Charts/Calyx Research Empty'
    assert profile.is_dir() and not list(profile.glob('*.chr')),'Research profile is not empty'
    assert n.T.resolve()!=Path('C:/Program Files/MetaTrader 5').resolve()
    state=dict(window=[START,END],total=37,complete={},failed={},missing={},live_changes=False,standalone_native=True)
    status_path=ROOT/'RUN_STATUS.json'
    if status_path.exists():state=read(status_path)
    selected=sys.argv[2:]
    for row in plan['cases']:
        slug=row['slug']
        if selected and slug not in selected:continue
        if slug in state['complete'] or slug in state['missing']:continue
        if slug in plan['explicitly_missing']:
            state['missing'][slug]=plan['explicitly_missing'][slug];save(status_path,state);continue
        verify_freeze()
        try:
            binary,build=n.build(row)
            result=n.run_case(row,'two-month-20261016',binary,build)
            actual=result['inputs']
            active_mismatches=[key for key,value in row['input_settings'].items() if key in actual and not n.h._same_setting(value,actual[key])]
            assert not active_mismatches,('Actual current settings mismatch',active_mismatches)
            risk_keys=['InpMomentumRiskPercent','InpContrarianRiskPercent','InpAbsoluteRiskCapPercent'] if slug=='lta-volume-profile' else ['InpRiskPercent']
            assert all(key in actual and abs(float(actual[key])-row['selected_risk_percent'])<1e-10 for key in risk_keys),'Native risk normalization not applied'
            if 'InpAdaptivePortfolioControls' in actual:assert actual['InpAdaptivePortfolioControls']=='false'
            if row['historical_loss_sizing']:
                assert actual['InpSizingMode']=='1' and float(actual['InpHistoricalLossPoints'])>0
            result['boundary_liquidation_positions']=[t['position_id'] for t in result['trades'] if any('end of test' in c.lower() for c in t['exit_comments'])]
            result['ranking_includes_boundary_liquidations']=True
            result['current_active_input_verification']=True
            if slug.startswith('news-pulse-'):
                journal=gzip.decompress((ROOT/'native'/result['tag']/'journal.txt.gz').read_bytes()).decode()
                assert 'NP_RESEARCH_BAD_CALENDAR_ORDER' not in journal
                found=set(re.findall(r'News Pulse tester calendar audit: expected=(\d+), attempted=(\d+), successfully placed=(\d+), boundary violation=(YES|NO)',journal))
                assert len(found)==1,('Missing calendar audit',found)
                expected,attempted,placed,boundary=next(iter(found))
                enabled=sum(row['input_settings'].get('InpWatch'+e['kind'],'true')=='true' for e in read(ROOT/'Calendar.json')['events'])
                assert int(expected)==enabled and boundary=='NO' and 0<=int(placed)<=int(attempted)<=enabled
                result['calendar_audit']=dict(expected=int(expected),attempted=int(attempted),placed=int(placed),boundary_violation=False,lookup_parity_verified=True)
            path=ROOT/'native'/result['tag']/'results.json';save(path,result)
            state['complete'][slug]=dict(path=str(path),sha256=sha(path),trades=len(result['trades']),seconds=result['seconds'],history_quality=result['native']['history_quality'])
            state['failed'].pop(slug,None)
        except Exception as error:
            state['failed'][slug]=dict(error=str(error),trace=traceback.format_exc()[-7000:])
            print('CASE FAILED '+slug+': '+str(error),flush=True)
        save(status_path,state)
        print('PROGRESS '+str(len(state['complete']))+'/36 reproducible complete; failed='+str(len(state['failed']))+'; unavailable='+str(len(state['missing'])),flush=True)
    verify_freeze()
    print('BATCH END; no production/live changes',flush=True)

if __name__=='__main__':
    if sys.argv[1:]==['prepare']:
        prepare()
    elif sys.argv[1:2]==['run']:
        with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
            lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
            n.available()
            run()
    else:
        raise SystemExit('Use prepare or run [optional slug ...]')
