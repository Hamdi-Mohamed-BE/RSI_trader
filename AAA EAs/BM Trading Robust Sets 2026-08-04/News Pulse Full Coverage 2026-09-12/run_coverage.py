"""Independent native MT5 runs, current News Pulse logic, extended official calendar."""
from __future__ import annotations
import argparse
import configparser
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
STORE=PACKAGE.parent/'EA store'
TESTER=Path(os.environ.get('CALYX_MT5_TESTER', PACKAGE/'_Backtests'/'MT5-DMC-20260811'))
NAME='News Pulse Full Coverage'
FOLDER=Path('AAA Research')/'News Full Coverage 20260912'
WINDOWS={'6m':'2026-03-05','1y':'2025-09-05','3y':'2023-09-05','5y':'2021-09-05'}
END='2026-09-05'
SLUGS=('news-pulse-xau','news-pulse-xag','news-pulse-btc')
sys.path.insert(0,str(STORE))
from app.catalog import get_product
from app.mt5_evidence_jobs import _native_metrics,_native_trades,_read_report,_metric,_number,_set_values,_report_inputs
from app.trade_metrics import enrich_trades,outcome_streaks
from app.evidence_series import parse_mt5_balance_series

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def hidden():
    info=subprocess.STARTUPINFO();info.dwFlags|=subprocess.STARTF_USESHOWWINDOW;info.wShowWindow=subprocess.SW_HIDE
    return info

def prepare(indexed_lookup=False):
    product=get_product(SLUGS[0]);source=(PACKAGE/product.expert_source).with_suffix('.mq5')
    target=TESTER/'MQL5'/'Experts'/FOLDER
    for folder in (target,ROOT/'EA',ROOT/'Sets',ROOT/'Backtest Reports',ROOT/'Audit',TESTER/'backtest-configs'/'news-full-coverage',TESTER/'reports'/'news-full-coverage'):
        folder.mkdir(parents=True,exist_ok=True)
    code=source.read_text(encoding='utf-8-sig')
    code=code.replace('"..\\..\\_Shared\\CalyxAdaptivePortfolio.mqh"','"CalyxAdaptivePortfolio.mqh"')
    if indexed_lookup:
        # Research harness only: same interval/enable predicate, logarithmic
        # search of the sorted release array instead of 158 conversions/tick.
        old='''   for(int i=0;i<total;i++)
   {
      string candidate_kind=NP_GENERATED_EVENT_KINDS[i];
      if(!NP_TesterKindEnabled(candidate_kind)) continue;
      datetime candidate=AAA_ToServer((datetime)NP_GENERATED_EVENT_UTC_EPOCHS[i]);'''
        new='''   int offset=AAA_ServerOffsetSeconds();
   datetime utc_now=now-offset;
   int left=0,right=total;
   while(left<right)
   {
      int middle=(left+right)/2;
      if((datetime)NP_GENERATED_EVENT_UTC_EPOCHS[middle]<=utc_now) left=middle+1;
      else right=middle;
   }
   for(int i=left;i<total;i++)
   {
      datetime candidate=(datetime)NP_GENERATED_EVENT_UTC_EPOCHS[i]+offset;
      if(candidate>now+InpPlacementLeadSeconds) break;
      string candidate_kind=NP_GENERATED_EVENT_KINDS[i];
      if(!NP_TesterKindEnabled(candidate_kind)) continue;'''
        assert code.count(old)==1
        code=code.replace(old,new)
    (ROOT/'EA'/f'{NAME}.mq5').write_text(code,encoding='utf-8')
    for include in source.parent.glob('*.mqh'):
        if include.name!='NewsPulseTesterCalendar.mqh':shutil.copy2(include,ROOT/'EA'/include.name)
    shutil.copy2(PACKAGE/'_Shared'/'CalyxAdaptivePortfolio.mqh',ROOT/'EA'/'CalyxAdaptivePortfolio.mqh')
    shutil.copy2(ROOT/'NewsPulseTesterCalendar.mqh',ROOT/'EA'/'NewsPulseTesterCalendar.mqh')
    for path in (ROOT/'EA').iterdir():
        if path.suffix in ('.mq5','.mqh'):shutil.copy2(path,target/path.name)
    log=ROOT/'compile.log'
    # MetaEditor can return 1 despite successful compilation; verify its log.
    subprocess.run(f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{target / (NAME+".mq5")}" /log:"{log}"',cwd=TESTER,startupinfo=hidden(),timeout=120)
    assert '0 errors, 0 warnings' in log.read_text(encoding='utf-16'),log.read_text(encoding='utf-16')
    shutil.copy2(target/(NAME+'.ex5'),ROOT/'EA'/(NAME+'.ex5'))
    identity=dict(source_path=str(source.relative_to(PACKAGE)),source_sha256=sha(source),research_source_sha256=sha(ROOT/'EA'/(NAME+'.mq5')),compiled_sha256=sha(ROOT/'EA'/(NAME+'.ex5')),indexed_lookup=indexed_lookup,changes='News Pulse v2.16 production source with verified tester calendar expansion'+('; equivalent binary-search historical lookup' if indexed_lookup else ''),dependencies={p.name:sha(p) for p in (ROOT/'EA').glob('*.mqh')})
    (ROOT/'BUILD MANIFEST.json').write_text(json.dumps(identity,indent=2),encoding='utf-8')
    print('COMPILED News Pulse v2.16 + official five-year calendar',flush=True)

def parse_result(slug,period,model,report,journal):
    calendar=json.loads((ROOT/'OFFICIAL CALENDAR.json').read_text())
    start=WINDOWS[period]
    events=[r for r in calendar['events'] if start<=r['release_utc'][:10]<END]
    expected=len(events)
    audit=re.search(r'News Pulse tester calendar audit: expected=(\d+), attempted=(\d+), successfully placed=(\d+), boundary violation=(YES|NO)',journal)
    assert audit, 'No completed tester-calendar audit'
    assert int(audit[1])==expected and audit[4]=='NO',(audit[0],expected)
    report_text=_read_report(report)
    assert _number(_metric(report_text,'OnTester result'))==int(audit[3])
    inputs=_report_inputs(report)
    assert inputs['InpRiskPercent']=='0.75'
    assert inputs['InpAdaptivePortfolioControls']=='false'
    if slug == 'news-pulse-xau':
        assert inputs['InpPlacementLeadSeconds']=='15'
        assert inputs['InpEntryOffsetPrice']=='4'
        assert inputs['InpStopLossPrice']=='4'
        assert inputs['InpUseTrailingStop']=='false'
        assert inputs['InpForceCloseSecondsAfterEvent']=='60'
    assert inputs['InpTesterFromDateUTC']==start.replace('-','')
    assert inputs['InpTesterToDateUTC']==END.replace('-','')
    product=get_product(slug)
    trades=enrich_trades(_native_trades(report,product.label),slug)
    native=_native_metrics(report)
    assert len(trades)==native['trades']
    assert abs(sum(t['net_profit'] for t in trades)-native['net_profit'])<.05
    by_id={r['epoch']:r for r in events}
    for trade in trades:
        comment=trade['entry_comment']
        match=re.match(r'NP\|(\d+)\|(NFP|CPI|FOMC)\|([BS])',comment)
        assert match,('Missing event identity',trade)
        release=by_id[int(match[1])]
        assert match[2]==release['kind']
        assert (match[3]=='B')==(trade['side']=='Long'),('Wrong deal pairing',trade)
        trade['news_event_kind']=release['kind'];trade['news_event_utc']=release['release_utc']
        trade['news_event_source']=release['source']
        trade['cache_slug']=slug;trade['cache_period']=period;trade['cache_mode']='standard'
        trade['source']='Precomputed native MT5 deals'
        assert start<=trade['open_time'][:10]<END
        direction=1 if trade['side']=='Long' else -1
        assert (trade['close_price']-trade['open_price'])*direction*trade['gross_profit']>=-.01,('Mispaired price/P&L',trade)
    wins=sum(max(0,t['net_profit']) for t in trades);losses=-sum(min(0,t['net_profit']) for t in trades)
    native['native_profit_factor']=native['profit_factor']
    native['profit_factor']=round(wins/losses,2) if losses else None
    native['win_rate_pct']=round(sum(t['net_profit']>0 for t in trades)/len(trades)*100,2) if trades else 0
    # Use maximum RELATIVE equity DD rather than the percentage at maximum cash DD.
    dd=re.match(r'([\d.]+)%',_metric(report_text,'Equity Drawdown Relative'))
    assert dd;native['max_drawdown_pct']=float(dd[1])
    native.update(outcome_streaks(trades))
    native.update(commission=round(sum(t['commission'] for t in trades),2),swap=round(sum(t['swap'] for t in trades),2),from_date=start,to_exclusive=END)
    native['total_costs']=round(native['commission']+native['swap'],2)
    no_fills=sorted(set(by_id)-{int(re.match(r'NP\|(\d+)\|',t['entry_comment'])[1]) for t in trades})
    identity=json.loads((ROOT/'BUILD MANIFEST.json').read_text())
    return dict(slug=slug,label=product.label,period_key=period,from_date=start,to_exclusive=END,model=model,fixed_execution_delay_ms=1,calendar_sha256=calendar['sha256'],calendar_expected=expected,calendar_attempted=int(audit[2]),calendar_placed=int(audit[3]),calendar_complete=True,events_without_closed_trades=[by_id[x] for x in no_fills],placement_complete=int(audit[3])==expected,activation_margin_rejections=journal.count('not enough money for order'),stats=native,trades=trades,series=list(parse_mt5_balance_series(report)),source_report_sha256=sha(report),source_report=str(report.relative_to(ROOT)),settings=inputs,build=identity)

def run(slug,period,model):
    product=get_product(slug);start=WINDOWS[period]
    tag=f'{slug}-{period}-model{model}'
    settings=_set_values(PACKAGE/product.set_source,False,{'InpAdaptivePortfolioControls':'false','InpTesterFromDateUTC':start.replace('-',''),'InpTesterToDateUTC':END.replace('-','')})
    set_name=tag+'.set'
    (ROOT/'Sets'/set_name).write_text(settings,encoding='utf-8')
    shutil.copy2(ROOT/'Sets'/set_name,TESTER/'MQL5'/'Profiles'/'Tester'/set_name)
    reference_path=next((TESTER/'backtest-configs').rglob('*.ini'),None)
    if reference_path is None: raise FileNotFoundError('No MT5 tester reference config found under '+str(TESTER/'backtest-configs'))
    reference_encoding='utf-16' if reference_path.read_bytes().startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
    reference=configparser.ConfigParser();reference.read(reference_path,encoding=reference_encoding)
    common=dict(reference['Common'])
    config='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())+'\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\n\n[Tester]\n'
    config+=f'Expert={FOLDER}\\{NAME}\nExpertParameters={set_name}\nSymbol={product.canonical}\nPeriod=M1\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel={model}\nExecutionMode=1\nOptimization=0\nFromDate={start.replace("-",".")}\nToDate={END.replace("-",".")}\nForwardMode=0\nReport=reports\\news-full-coverage\\{tag}.htm\nReplaceReport=1\nShutdownTerminal=1\nUseCloud=0\nVisual=0\n'
    config_path=TESTER/'backtest-configs'/'news-full-coverage'/(tag+'.ini');config_path.write_text(config,encoding='utf-16')
    logs=TESTER/'Tester'/'Agent-127.0.0.1-3000'/'logs'
    offsets={p:p.stat().st_size for p in logs.glob('*.log')}
    started=time.time();print('START '+tag,flush=True)
    p=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{config_path.relative_to(TESTER)}'],cwd=TESTER,startupinfo=hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:p.wait(timeout=2400)
    except subprocess.TimeoutExpired:
        p.kill();raise RuntimeError('MT5 run exceeded 40 minutes: '+tag)
    report=TESTER/'reports'/'news-full-coverage'/(tag+'.htm')
    assert report.is_file() and report.stat().st_mtime>=started-2,'No fresh report '+tag
    journal=''
    for path in sorted(logs.glob('*.log')):
        if path.stat().st_mtime<started:continue
        data=path.read_bytes()[offsets.get(path,0):]
        journal+=data.decode('utf-16-le',errors='replace')
    journal=journal.replace('\r\n','\n').replace('\r','\n')
    (ROOT/'Audit'/(tag+'-journal.txt')).write_text(journal,encoding='utf-8')
    for path in report.parent.glob(tag+'*'):shutil.copy2(path,ROOT/'Backtest Reports'/path.name)
    result=parse_result(slug,period,model,ROOT/'Backtest Reports'/report.name,journal)
    (ROOT/(tag+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('DONE '+json.dumps({k:result[k] for k in ('slug','period_key','calendar_expected','calendar_attempted','calendar_placed','stats')}),flush=True)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--model',type=int,default=4,choices=(0,4));parser.add_argument('--periods',default=','.join(WINDOWS));parser.add_argument('--slugs',default=','.join(SLUGS));parser.add_argument('--resume',action='store_true');parser.add_argument('--indexed-lookup',action='store_true')
    args=parser.parse_args();prepare(args.indexed_lookup)
    for period in args.periods.split(','):
        for slug in args.slugs.split(','):
            if args.resume and (ROOT/f'{slug}-{period}-model{args.model}.json').is_file():continue
            run(slug,period,args.model)

if __name__=='__main__':main()
