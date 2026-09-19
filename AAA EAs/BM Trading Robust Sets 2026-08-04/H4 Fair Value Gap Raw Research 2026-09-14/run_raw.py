from __future__ import annotations
import argparse,configparser,csv,hashlib,importlib.util,json,re,shutil,subprocess,sys,time
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
NAME='H4 Fair Value Gap Raw'
FOLDER=Path('AAA Research')/'H4 FVG Raw 20260914'
SOURCE=ROOT/'EA'/f'{NAME}.mq5'
WINDOWS={'6m':('2026.03.05','2026.09.05'),'1y':('2025.09.05','2026.09.05'),
         '3y':('2023.09.05','2026.09.05'),'5y':('2021.09.05','2026.09.05')}
sys.path.insert(0,str(PACKAGE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_trades
spec=importlib.util.spec_from_file_location('parser',PACKAGE/'POC Fibonacci Volume Profile Research 2026-09-04'/'Analyze-POCFib.py')
parser=importlib.util.module_from_spec(spec);spec.loader.exec_module(parser)

def hidden():
    x=subprocess.STARTUPINFO();x.dwFlags|=subprocess.STARTF_USESHOWWINDOW;x.wShowWindow=subprocess.SW_HIDE;return x
def save(p,o):p.write_text(json.dumps(o,indent=2,allow_nan=False),encoding='utf-8')
def prepare():
    target=TESTER/'MQL5'/'Experts'/FOLDER
    for p in (target,ROOT/'Sets',ROOT/'Backtest Reports',ROOT/'Audit',
              TESTER/'backtest-configs'/'h4-fvg-raw',TESTER/'reports'/'h4-fvg-raw'):
        p.mkdir(parents=True,exist_ok=True)
    shutil.copy2(SOURCE,target/SOURCE.name)
    log=ROOT/'compile.log';started=time.time()
    cmd=f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{target/SOURCE.name}" /log:"{log}"'
    subprocess.run(cmd,cwd=TESTER,startupinfo=hidden(),timeout=120)
    text=log.read_text(encoding='utf-16',errors='replace')
    assert log.stat().st_mtime>=started-2 and '0 errors, 0 warnings' in text,text
    shutil.copy2(target/f'{NAME}.ex5',ROOT/'EA'/f'{NAME}.ex5')
    print('COMPILE OK: zero errors, zero warnings',flush=True)
def stats(report,label):
    s=parser.parse_report(report);s.pop('score',None);s.pop('deals',None)
    ts=_native_trades(report,label);assert len(ts)==s['trades'];assert abs(sum(t['net_profit'] for t in ts)-s['net_profit'])<.051
    win=[t for t in ts if t['net_profit']>0];loss=[t for t in ts if t['net_profit']<0];streak=worst=0
    for t in ts:
        t['holding_minutes']=(datetime.fromisoformat(t['close_time'])-datetime.fromisoformat(t['open_time'])).total_seconds()/60
        streak=streak+1 if t['net_profit']<0 else 0;worst=max(worst,streak)
    fields={}
    for row in parser.read_report(report).find_all('tr'):
        cells=[parser.compact(c.get_text(' ',strip=True)) for c in row.find_all(['td','th'],recursive=False)]
        for i,c in enumerate(cells[:-1]):
            if c.endswith(':'):fields[c[:-1]]=cells[i+1]
    s.update(net_pf=sum(t['net_profit'] for t in win)/-sum(t['net_profit'] for t in loss) if loss else None,
      net_win_rate=100*len(win)/len(ts) if ts else 0,wins=len(win),losses=len(loss),breakeven=len(ts)-len(win)-len(loss),
      average_win=sum(t['net_profit'] for t in win)/len(win) if win else 0,
      average_loss=sum(t['net_profit'] for t in loss)/len(loss) if loss else 0,max_loss_streak=worst,
      long_trades=sum(t['side']=='Long' for t in ts),short_trades=sum(t['side']=='Short' for t in ts),
      long_net=sum(t['net_profit'] for t in ts if t['side']=='Long'),short_net=sum(t['net_profit'] for t in ts if t['side']=='Short'),
      overnight_trades=sum(t['open_time'][:10]!=t['close_time'][:10] for t in ts),
      mean_holding_minutes=sum(t['holding_minutes'] for t in ts)/len(ts) if ts else 0,
      equity_dd_relative=fields.get('Equity Drawdown Relative'),equity_dd_maximal=fields.get('Equity Drawdown Maximal'),
      report_period=fields.get('Period'),report_ticks=fields.get('Ticks'),report_bars=fields.get('Bars'))
    return s,ts
def run(symbol,period,model):
    start,end=WINDOWS[period];tag=f'{symbol.lower()}-h4-fvg-raw-{period}-model{model}'
    magic=91440000+(['XAUUSD','USTEC'].index(symbol)+1)*100+list(WINDOWS).index(period)*10+model
    setname=tag+'.set';settings=f'InpRiskPercent=1\nInpRewardRisk=2\nInpMagic={magic}\nInpDeviationPoints=30\nInpExportH4=true\n'
    (ROOT/'Sets'/setname).write_text(settings,encoding='utf-8');shutil.copy2(ROOT/'Sets'/setname,TESTER/'MQL5'/'Profiles'/'Tester'/setname)
    ref=configparser.ConfigParser();ref.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16')
    common=dict(ref['Common']);assert common.get('server')=='Exness-MT5Trial16','Unexpected isolated tester account'
    content='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())
    content+='\n[Experts]\nEnabled=0\nAllowLiveTrading=0\nAllowDllImport=0\nAccount=1\nProfile=1\n\n[Charts]\nProfileLast=CappedResearchOnly\n\n[Tester]\n'
    content+=f'Expert={FOLDER}\\{NAME}\nExpertParameters={setname}\nSymbol={symbol}\nPeriod=H4\nLogin={common["login"]}\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel={model}\nExecutionMode=1\nOptimization=0\n'
    content+=f'FromDate={start}\nToDate={end}\nForwardMode=0\nReport=reports\\h4-fvg-raw\\{tag}.htm\nReplaceReport=1\nShutdownTerminal=1\nUseLocal=1\nUseRemote=0\nUseCloud=0\nVisual=0\n'
    cfg=TESTER/'backtest-configs'/'h4-fvg-raw'/f'{tag}.ini';cfg.write_text(content,encoding='utf-16')
    profile=TESTER/'MQL5'/'Profiles'/'Charts'/'CappedResearchOnly';assert profile.is_dir() and not list(profile.glob('*.chr'))
    report=TESTER/'reports'/'h4-fvg-raw'/f'{tag}.htm';sizes={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')}
    started=time.time();print('START',tag,start,'to',end,flush=True)
    p=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{cfg.relative_to(TESTER)}'],cwd=TESTER,startupinfo=hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:p.wait(timeout=1800)
    except subprocess.TimeoutExpired:p.kill();raise RuntimeError('Owned isolated tester timeout '+tag)
    assert report.is_file() and report.stat().st_mtime>=started-2,'No fresh native report'
    for x in report.parent.glob(tag+'*'):shutil.copy2(x,ROOT/'Backtest Reports'/x.name)
    prefix=f'H4FVGRaw-{magic}';files=[]
    for x in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/{prefix}*.csv'):
        if x.stat().st_mtime<started-2:continue
        dest=ROOT/'Audit'/(tag+x.name[len(prefix):]);shutil.copy2(x,dest);files.append(dest.name)
    assert len(files)==2,(tag,files)
    journal=''
    for x in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
        if x.stat().st_mtime<started-2:continue
        with x.open('rb') as f:f.seek(sizes.get(x,0));journal+=f.read().decode('utf-16-le',errors='replace')
    (ROOT/'Audit'/f'{tag}-journal.log').write_text(journal,encoding='utf-8')
    summary,trades=stats(report,f'{symbol} H4 FVG raw')
    audit=list(csv.DictReader((ROOT/'Audit'/f'{tag}.csv').open(encoding='utf-8-sig')))
    fills=[r for r in audit if r['event']=='accepted'];assert len(fills)==len(trades)
    for t,a in zip(trades,fills):
        t.update(initial_stop=float(a['stop']),initial_target=float(a['target']),planned_risk_cash=float(a['risk_cash']),
                 fill_rr=abs(float(a['target'])-float(a['entry']))/abs(float(a['entry'])-float(a['stop'])))
    q=[line for line in journal.splitlines() if re.search('real ticks|execution delay|H4 FVG RAW|no history|no prices|not enough money|stop out',line,re.I)]
    signals=[r for r in audit if r['event'] in ('accepted','error','rejected')]
    summary.update(zones=sum(r['event']=='zone' for r in audit),invalidated=sum(r['event']=='invalidate' for r in audit),
      rejected=sum(r['event']=='rejected' for r in audit),execution_errors=[r['detail'] for r in audit if r['event']=='error'],
      planned_risk_pct_min=min((100*float(r['risk_cash'])/float(r['equity']) for r in fills),default=0),
      planned_risk_pct_max=max((100*float(r['risk_cash'])/float(r['equity']) for r in fills),default=0),
      fill_rr_min=min((t['fill_rr'] for t in trades),default=None),fill_rr_max=max((t['fill_rr'] for t in trades),default=None),
      boundary_exits=sum('end of test' in t['exit_comment'].lower() for t in trades),quality_journal=q,
      attempted=len(signals))
    row=dict(symbol_requested=symbol,period=period,from_date=start,to_exclusive=end,model=model,execution_delay_ms=1,
      source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),elapsed_seconds=round(time.time()-started,1),**summary)
    save(ROOT/'Audit'/f'{tag}-trades.json',trades);save(ROOT/f'{tag}-stats.json',row)
    print('DONE',json.dumps({k:row[k] for k in ('symbol_requested','period','return_pct','trades','net_win_rate','net_pf','max_drawdown_pct','zones','execution_errors')}),flush=True)
    return row
def main():
    cli=argparse.ArgumentParser();cli.add_argument('--symbols',default='XAUUSD,USTEC');cli.add_argument('--periods',default=','.join(WINDOWS));cli.add_argument('--model',type=int,default=4);cli.add_argument('--compile-only',action='store_true');a=cli.parse_args()
    prepare()
    if a.compile_only:return
    rows=[run(s,p,a.model) for s in a.symbols.split(',') for p in a.periods.split(',')]
    save(ROOT/f'run-summary-model{a.model}.json',rows)
if __name__=='__main__':main()
