"""Frozen portfolio histories. Isolated tester only; never a live-account API.

Five-year standalone signal ledgers are replayed offline for each portfolio.
Settings/rosters are frozen BEFORE results; no re-selection or optimization.
The three-year view is a clearly labelled slice/replay, not an independent test.
"""
from pathlib import Path
import gzip, hashlib, importlib.util, inspect, json, msvcrt, os, re, sys, time, traceback
from calendar_search import rewrite as fast_calendar_search, VERSION as CALENDAR_SEARCH_VERSION

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
PRIOR = BASE / 'ORB and Range Breakout RR05 Comparison 2026-10-08'
os.environ['EA_STORE_DISABLE_MT5'] = '1'
spec = importlib.util.spec_from_file_location('portfolio_native_helpers', PRIOR/'run.py')
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)
n.R = ROOT
n.START, n.END = '2021.10.06', '2026.10.06'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def stringify(inputs):
    return {k: str(v).lower() if isinstance(v, bool) else str(v) for k,v in inputs.items()}


def frozen_plan():
    website = BASE.parent/'EA store'
    publication = read(website/'data/portfolios.json')
    products = {p.slug:p for p in n.get_website_catalog()}
    cases, mappings = {}, {}
    # First run the five screened ORBs, then the guarded/current rosters.
    order = ['orbs-only','ftmo','current14-orb05','full-eas']
    for name in order:
        profile = next(p for p in publication['portfolios'] if p['slug']==name)
        mappings[name] = {}
        for member in profile['members']:
            slug = member['slug']; p = products[slug]
            binary = (BASE/(p.dynamic_expert_source if p.recommended_dynamic_mode and p.dynamic_expert_source else p.expert_source)).resolve()
            source = binary.with_suffix('.mq5')
            preset = (p.dynamic_set_source if p.recommended_dynamic_mode else p.safe_set_source if p.recommended_safe_mode else p.set_source) or p.set_source
            preset = (BASE/preset).resolve()
            inputs = stringify(member['inputs'])
            # Sizing/adaptive controls are replayed at portfolio entry time, not
            # independently against each EA's unrelated standalone balance.
            for key in list(inputs):
                if key in ('InpRiskPercent','InpGridRiskPercent','InpMomentumRiskPercent','InpContrarianRiskPercent'):
                    inputs[key] = '1.0'
                if key=='InpAdaptivePortfolioControls': inputs[key]='false'
            if slug.startswith('news-pulse-'):
                inputs.update(InpTesterFromDateUTC='20211006',InpTesterToDateUTC='20261006')
            if slug.endswith('hourly-profiles'):
                inputs.update(InpAuditTag='portfolio-long-'+slug)
            signature = hashlib.sha256(json.dumps([str(source),inputs],sort_keys=True).encode()).hexdigest()[:12]
            case_id = slug+'-'+signature
            mappings[name][slug]=case_id
            if case_id in cases: continue
            hashes = {str(f):n.sha(f) for f in sorted(n.closure(source)|{binary,preset})}
            cases[case_id] = dict(slug=slug,case_id=case_id,label=p.label,symbol='USTEC' if p.canonical=='US100' else p.canonical,
                period=p.timeframe,source=str(source),expert=str(binary),preset=str(preset),input_settings=inputs,
                candidate_overrides={},production_hashes=hashes)
    plan=dict(start=n.START,end_exclusive=n.END,model=4,execution_delay_ms=150,
        mappings=mappings,cases=list(cases.values()),selection_frozen=True,live_changes=False,
        three_year_method='Fresh offline risk/guard replay of the frozen five-year signal ledger; no carry-in positions.',
        publication_sha256=n.sha(website/'data/portfolios.json'))
    path=ROOT/'PLAN.json'
    if path.exists():
        old=read(path)
        # Publication changes only after completion; retain original signatures.
        assert old['cases']==plan['cases'] and old['mappings']==plan['mappings'], 'Frozen configuration changed'
        return old
    n.save(path,plan)
    return plan


def prepare_helpers():
    audit=ROOT/'ReadOnlyAudit.mqh'
    if not audit.exists(): audit.write_bytes((PRIOR/'ReadOnlyAudit.mqh').read_bytes())
    # Generalize ONLY verification of the risk input: LTA has separate momentum /
    # contrarian sizing. Supplied active values are still verified individually.
    source=inspect.getsource(n.run_case)
    old="required=['InpRiskPercent','InpRR05AuditTag',*row['candidate_overrides']]"
    assert source.count(old)==1
    source=source.replace(old,"required=['InpRR05AuditTag',*row['candidate_overrides']]")
    exec(compile(source,str(ROOT/'run.py')+'::verified_runner','exec'), n.__dict__)
    source=inspect.getsource(n.build)
    old="info['audit_sha256']==sha(R/'ReadOnlyAudit.mqh') and"
    assert source.count(old)==1
    source=source.replace(old,old+"\n      (not row['slug'].startswith('news-pulse-') or info.get('calendar_search_version')==CALENDAR_SEARCH_VERSION) and")
    old="origin=Path(row['source']);text=h.text(origin)"
    assert source.count(old)==1
    new=old+"\n if row['slug'].startswith('news-pulse-'):\n  text=re.sub(r'^\\s*#include\\s+\"[^\"]*NewsPulseTesterCalendar.mqh\"', '#include \"'+str(R/'HistoricalCalendar.mqh').replace('\\\\','/')+'\"', text, flags=re.M)"
    source=source.replace(old,new)
    old='changes=[]'
    assert source.count(old)==1
    source=source.replace(old,old+"\n if row['slug'].startswith('news-pulse-'):\n  text=fast_calendar_search(text);changes.append(CALENDAR_SEARCH_VERSION+'; timer/callbacks/trading unchanged')")
    old="save(folder/'build.json',value);return binary,value"
    assert source.count(old)==1
    source=source.replace(old,"value['calendar_search_version']=CALENDAR_SEARCH_VERSION if row['slug'].startswith('news-pulse-') else None\n "+old)
    n.fast_calendar_search=fast_calendar_search;n.CALENDAR_SEARCH_VERSION=CALENDAR_SEARCH_VERSION
    exec(compile(source,str(ROOT/'run.py')+'::calendar_copy','exec'),n.__dict__)


def prepare_calendar():
    path=BASE/'US100 News Reversion Pipeline 2020-2024 2026-10-08/calendar.json'
    original=read(path)
    events=[e for e in original['events'] if '2021-10-06'<=e['release_utc'][:10]<'2026-10-06']
    assert events and len({(e['epoch'],e['kind']) for e in events})==len(events)
    assert all(e.get('source') and e.get('receipt') for e in events)
    digest=hashlib.sha256(json.dumps([(e['epoch'],e['kind']) for e in events],separators=(',',':')).encode()).hexdigest()
    n.save(ROOT/'Calendar.json',dict(source=str(path),source_sha256=n.sha(path),
        coverage_start='2021-10-06',end_exclusive='2026-10-06',events=events,
        calendar_vintage_verified=False,source_note=original['note']))
    include='''// Official-source receipted schedule; tester-only copy, not a point-in-time vintage.
#ifndef CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define CALYX_NEWS_PULSE_TESTER_CALENDAR_MQH
#define NP_TESTER_CALENDAR_COVERAGE_START_DATE 20211006
#define NP_TESTER_CALENDAR_COVERAGE_END_DATE 20261006
#define NP_TESTER_CALENDAR_EXPECTED_EVENTS '''+str(len(events))+'''
long NP_GENERATED_EVENT_UTC_EPOCHS[]={'''+','.join(str(e['epoch']) for e in events)+'''};
string NP_GENERATED_EVENT_KINDS[]={'''+','.join(json.dumps(e['kind']) for e in events)+'''};
string NP_GeneratedCalendarProvider(){return "Official BLS + Federal Reserve; saved receipted chronology";}
string NP_GeneratedCalendarHash(){return "'''+digest+'''";}
string NP_GeneratedCalendarFetchedAt(){return "2026-10-08";}
int NP_GeneratedCalendarEventCount(){return ArraySize(NP_GENERATED_EVENT_UTC_EPOCHS);}
#endif
'''
    (ROOT/'HistoricalCalendar.mqh').write_text(include,encoding='utf-8')


def verified_reuse(row, plan, state):
    """Reuse only same source, symbol, timeframe and equivalent ACTIVE inputs.

    Original manifests include obsolete/guard-only parameters that the unguarded
    signal EA doesn't expose. Native reports identify the actually active inputs.
    Missing candidate values must match the original source's declared defaults.
    """
    ignored={'InpRR05AuditTag','InpAuditTag','InpMagic','InpMagicNumber'}
    defaults={}
    literals={}
    defines={}
    for path in n.closure(Path(row['source'])):
        body=n.h.text(path)
        for key,value in re.findall(r'^\s*#define\s+(\w+)\s+([+-]?[\d.]+)\s*$',body,re.M):defines.setdefault(key,set()).add(value)
        body=re.sub(r'//[^\r\n]*|/\*.*?\*/','',body,flags=re.S)
        for block in re.findall(r'\benum\s+\w+\s*\{([^}]+)\}',body,re.S):
            number=-1
            for field in block.split(','):
                pair=field.strip().split('=',1);key=pair[0].strip()
                try:number=int(pair[1].strip(),0) if len(pair)==2 else number+1
                except ValueError:break # Never evaluate arbitrary expressions.
                if re.fullmatch(r'\w+',key):literals[key]=str(number)
        for key,value in re.findall(r'^\s*input\s+(?!group\b)\w+\s+(\w+)\s*=\s*([^;\r\n]+);',body,re.M):
            defaults[key]=value.strip().strip('"')
    # Conditional fallback macros cannot be resolved safely by a regex parser.
    # Differing definitions remain unknown, preventing rather than guessing reuse.
    literals.update({key:next(iter(values)) for key,values in defines.items() if len(values)==1})
    defaults={k:literals.get(v,v) for k,v in defaults.items()}
    expected=dict(row['input_settings'],InpRiskPercent='1.0')
    for old in plan['cases']:
        if old['case_id'] not in state['complete'] or any(old[k]!=row[k] for k in ('source','symbol','period')):continue
        receipt=state['complete'][old['case_id']]
        result=read(receipt['path'])
        actual=result['inputs']
        old_expected=dict(old['input_settings'],InpRiskPercent='1.0')
        keys=(set(expected)|set(old_expected)) & set(actual) - ignored
        if all(n.h._same_setting(literals.get(expected.get(key,''),expected.get(key,defaults.get(key,'<unknown>'))),actual[key]) for key in keys):
            assert n.sha(Path(receipt['path']))==receipt['sha256']
            return dict(receipt,verified_same_active_inputs=True,reused_case=old['case_id'])
    return None


def main():
    prepare_calendar()
    prepare_helpers()
    plan=frozen_plan()
    parity=read(ROOT/'Calendar Lookup Parity'/'VERIFICATION.json')
    assert parity['version']==CALENDAR_SEARCH_VERSION and all(parity[k] for k in
        ('native_trades_identical','native_cash_flows_identical','native_report_identical','production_files_unchanged'))
    state=dict(window=[n.START,n.END],total=len(plan['cases']),complete={},failed={},missing={},live_changes=False)
    if (ROOT/'RUN_STATUS.json').exists(): state=read(ROOT/'RUN_STATUS.json')
    for row in plan['cases']:
        case=row['case_id']
        if case in state['complete'] or case in state['missing']: continue
        if sys.argv[1:] and sys.argv[1]!='all' and row['slug'] not in sys.argv[1:]: continue
        if row['slug']=='gold-news-v9-direction':
            # Its current file/HTTP bridge is not a historical, timestamped
            # prediction ledger. Never call it or treat a silent zero as history.
            state['missing'][case]='Historical pre-release V9 direction/confidence predictions are not available; current live HTTP/file bridge is intentionally not called.'
            n.save(ROOT/'RUN_STATUS.json',state)
            continue
        try:
            reused=verified_reuse(row,plan,state)
            if reused:
                state['complete'][case]=reused
                state['failed'].pop(case,None)
                n.save(ROOT/'RUN_STATUS.json',state)
                print('VERIFIED SAME ACTIVE SETTINGS '+case+' <- '+reused['reused_case'],flush=True)
                continue
            binary, build=n.build(row)
            result=n.run_case(row,'long-'+case.split('-')[-1],binary,build)
            if row['slug'].startswith('news-pulse-'):
                journal=gzip.decompress((ROOT/'native'/result['tag']/'journal.txt.gz').read_bytes()).decode()
                assert 'NP_RESEARCH_BAD_CALENDAR_ORDER' not in journal
                found=set(re.findall(r'News Pulse tester calendar audit: expected=(\d+), attempted=(\d+), successfully placed=(\d+), boundary violation=(YES|NO)',journal))
                assert len(found)==1,('Missing/ambiguous calendar audit',found)
                expected,attempted,placed,boundary=next(iter(found))
                enabled=sum(row['input_settings'].get('InpWatch'+e['kind'],'true')=='true' for e in read(ROOT/'Calendar.json')['events'])
                assert int(expected)==enabled and boundary=='NO' and 0<=int(placed)<=int(attempted)<=enabled
                result['calendar_audit']=dict(expected=int(expected),attempted=int(attempted),placed=int(placed),boundary_violation=False,
                    lookup_version=CALENDAR_SEARCH_VERSION,parity_verified=True)
                n.save(ROOT/'native'/result['tag']/'results.json',result)
            state['complete'][case]=dict(path=str(ROOT/'native'/result['tag']/'results.json'),
                sha256=n.sha(ROOT/'native'/result['tag']/'results.json'),trades=len(result['trades']),
                history_quality=result['native']['history_quality'])
            state['failed'].pop(case,None)
        except Exception as error:
            state['failed'][case]=dict(error=str(error),trace=traceback.format_exc()[-5000:])
            print('CASE FAILED '+case+': '+str(error),flush=True)
        n.save(ROOT/'RUN_STATUS.json',state)
        print('PROGRESS '+str(len(state['complete']))+'/'+str(state['total'])+' complete, '+str(len(state['failed']))+' failed, '+str(len(state['missing']))+' explicit gaps',flush=True)
    assert all(n.sha(Path(path))==digest for row in plan['cases'] for path,digest in row['production_hashes'].items()), 'Production changed'
    print('BATCH FINISHED; production files unchanged',flush=True)


if __name__=='__main__':
    with (BASE/'LTA VWAP Developing POC Comparison 2026-10-05/tester.lock').open('a+b') as lease:
        wait='--wait' in sys.argv
        if wait:sys.argv.remove('--wait')
        while True:
            try:
                lease.seek(0);msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
                break
            except OSError:
                if not wait:raise
                print('WAIT: isolated research tester lease held; no terminal stopped',flush=True)
                time.sleep(30)
        main()
