from __future__ import annotations
import argparse
import configparser
import csv
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / '_Backtests' / 'MT5-DMC-20260811'
NAME = 'D14 H1 M5 Break Retest Raw'
EXPERT_FOLDER = Path('AAA Research') / 'D14 Break Retest 20260913'
SOURCE = ROOT / 'EA' / f'{NAME}.mq5'
WINDOWS = {'6m': ('2026.03.05', '2026.09.05'), '1y': ('2025.09.05', '2026.09.05'),
           '3y': ('2023.09.05', '2026.09.05'), '5y': ('2021.09.05', '2026.09.05')}
sys.path.insert(0, str(PACKAGE.parent / 'EA store'))
from app.mt5_evidence_jobs import _native_trades
spec = importlib.util.spec_from_file_location('raw_mt5_parser', PACKAGE / 'POC Fibonacci Volume Profile Research 2026-09-04' / 'Analyze-POCFib.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

def hidden():
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    return info

def prepare():
    target = TESTER / 'MQL5' / 'Experts' / EXPERT_FOLDER
    for path in (target, ROOT/'Sets', ROOT/'Backtest Reports', ROOT/'Audit',
                 TESTER/'backtest-configs'/'d14-break-retest', TESTER/'reports'/'d14-break-retest'):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, target/SOURCE.name)
    log = ROOT/'compile.log'
    started = time.time()
    command = f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{target/SOURCE.name}" /log:"{log}"'
    subprocess.run(command, cwd=TESTER, timeout=120, startupinfo=hidden())
    if not log.is_file() or log.stat().st_mtime < started-2:
        raise RuntimeError('No fresh compile log')
    content = log.read_text(encoding='utf-16', errors='replace')
    if '0 errors, 0 warnings' not in content:
        raise RuntimeError(content)
    shutil.copy2(target/f'{NAME}.ex5', ROOT/'EA'/f'{NAME}.ex5')
    print('COMPILE OK: zero errors, zero warnings', flush=True)

def refresh_isolated_session():
    # Account files remain local in the already-established isolated tester.
    # Never copy these credentials into the repository's research report folder.
    active=Path.home()/'AppData'/'Roaming'/'MetaQuotes'/'Terminal'/'D0E8209F77C8CF37AD8BF550E51FF075'/'config'
    for name in ('accounts.dat','servers.dat','common.ini'):
        source=active/name
        if source.is_file():shutil.copy2(source,TESTER/'Config'/name)
    print('Refreshed isolated login cache from the current Exness terminal; live terminal unchanged.',flush=True)

def report_stats(report, label):
    summary = parser.parse_report(report)
    summary.pop('score', None); summary.pop('deals', None)
    trades = _native_trades(report, label)
    assert len(trades) == summary['trades'], (len(trades), summary['trades'])
    assert abs(sum(t['net_profit'] for t in trades)-summary['net_profit']) < .051
    wins=[t['net_profit'] for t in trades if t['net_profit']>0]
    losses=[t['net_profit'] for t in trades if t['net_profit']<0]
    for t in trades:
        from datetime import datetime
        t['holding_minutes']=(datetime.fromisoformat(t['close_time'])-datetime.fromisoformat(t['open_time'])).total_seconds()/60
    streak=worst=0
    for t in trades:
        streak=streak+1 if t['net_profit']<0 else 0
        worst=max(worst,streak)
    soup=parser.read_report(report)
    fields={}
    for row in soup.find_all('tr'):
        cells=[parser.compact(c.get_text(' ',strip=True)) for c in row.find_all(['td','th'],recursive=False)]
        for i,c in enumerate(cells[:-1]):
            if c.endswith(':'): fields[c[:-1]]=cells[i+1]
    summary.update(net_pf=sum(wins)/-sum(losses) if losses else None,
                   net_win_rate=100*len(wins)/len(trades) if trades else 0,
                   wins=len(wins), losses=len(losses), breakeven=len(trades)-len(wins)-len(losses),
                   average_win=sum(wins)/len(wins) if wins else 0,
                   average_loss=sum(losses)/len(losses) if losses else 0,
                   largest_win=max(wins,default=0),largest_loss=min(losses,default=0),
                   max_loss_streak=worst,
                   long_trades=sum(t['side']=='Long' for t in trades),
                   short_trades=sum(t['side']=='Short' for t in trades),
                   long_net=sum(t['net_profit'] for t in trades if t['side']=='Long'),
                   short_net=sum(t['net_profit'] for t in trades if t['side']=='Short'),
                   overnight_trades=sum(t['open_time'][:10]!=t['close_time'][:10] for t in trades),
                   mean_holding_minutes=sum(t['holding_minutes'] for t in trades)/len(trades) if trades else 0,
                   max_holding_minutes=max((t['holding_minutes'] for t in trades),default=0),
                   first_trade=trades[0]['open_time'] if trades else None,
                   last_trade=trades[-1]['close_time'] if trades else None,
                   equity_dd_relative=fields.get('Equity Drawdown Relative'),
                   equity_dd_maximal=fields.get('Equity Drawdown Maximal'),
                   balance_dd_relative=fields.get('Balance Drawdown Relative'),
                   report_period=fields.get('Period'),symbol=fields.get('Symbol'),
                   report_ticks=fields.get('Ticks'),report_bars=fields.get('Bars'))
    return summary,trades

def run(symbol,period,model):
    start,end=WINDOWS[period]
    tag=f'{symbol.lower()}-d14-raw-{period}-model{model}'
    magic=84133000+(['XAUUSD','USTEC'].index(symbol)+1)*100+list(WINDOWS).index(period)*10+model
    setname=tag+'.set'
    settings=f'InpRiskPercent=1\nInpMagic={magic}\nInpDeviationPoints=30\n'
    (ROOT/'Sets'/setname).write_text(settings,encoding='utf-8')
    shutil.copy2(ROOT/'Sets'/setname,TESTER/'MQL5'/'Profiles'/'Tester'/setname)
    reference=configparser.ConfigParser()
    reference.read(TESTER/'backtest-configs'/'xauusd-closing-momentum-20260912'/'6m.ini',encoding='utf-16')
    common=dict(reference['Common'])
    content='[Common]\n'+''.join(f'{k}={v}\n' for k,v in common.items())+'\n[Tester]\n'
    content+=f'Expert={EXPERT_FOLDER}\\{NAME}\nExpertParameters={setname}\nSymbol={symbol}\nPeriod=M5\n'
    content+=f'Login={common["login"]}\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel={model}\nExecutionMode=1\nOptimization=0\n'
    content+=f'FromDate={start}\nToDate={end}\nForwardMode=0\nReport=reports\\d14-break-retest\\{tag}.htm\nReplaceReport=1\nShutdownTerminal=1\nUseCloud=0\nVisual=0\n'
    config=TESTER/'backtest-configs'/'d14-break-retest'/f'{tag}.ini'
    config.write_text(content,encoding='utf-16')
    report=TESTER/'reports'/'d14-break-retest'/f'{tag}.htm'
    log_sizes={p:p.stat().st_size for p in (TESTER/'Tester').glob('Agent-*/logs/*.log')}
    started=time.time()
    print(f'START {tag}: {start} to {end}',flush=True)
    process=subprocess.Popen([str(TESTER/'terminal64.exe'),'/portable',f'/config:{config.relative_to(TESTER)}'],cwd=TESTER,startupinfo=hidden(),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try: process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f'Owned isolated tester exceeded 30 minutes: {tag}')
    if not report.is_file() or report.stat().st_mtime<started-2:
        raise RuntimeError(f'No fresh native report: {tag}')
    for p in report.parent.glob(tag+'*'): shutil.copy2(p,ROOT/'Backtest Reports'/p.name)
    prefix=f'D14BreakRetest-{magic}'
    files=list((TESTER/'Tester').glob(f'Agent-*/MQL5/Files/{prefix}*.csv'))
    saved=[]
    for p in files:
        if p.stat().st_mtime<started-2: continue
        suffix=p.name[len(prefix):]
        dest=ROOT/'Audit'/f'{tag}{suffix}'
        shutil.copy2(p,dest);saved.append(dest.name)
    if len(saved)!=4: raise RuntimeError(f'Expected signal audit plus three timeframes: {tag}: {saved}')
    journals=[]
    for p in (TESTER/'Tester').glob('Agent-*/logs/*.log'):
        if p.stat().st_mtime<started-2: continue
        with p.open('rb') as f:
            f.seek(log_sizes.get(p,0)); raw=f.read()
        journals.append(raw.decode('utf-16-le',errors='replace'))
    journal='\n'.join(journals)
    (ROOT/'Audit'/f'{tag}-journal.log').write_text(journal,encoding='utf-8')
    stats,trades=report_stats(report,f'{symbol} D14/H1/M5 raw')
    audit=list(csv.DictReader((ROOT/'Audit'/f'{tag}.csv').open(encoding='utf-8-sig')))
    sig=[r for r in audit if r['event']=='signal']
    accepted=[r for r in audit if r['event']=='accepted']
    assert len(accepted)==len(trades), (len(accepted),len(trades))
    for t,a in zip(trades,accepted):
        t['initial_stop']=float(a['stop']);t['initial_target']=float(a['target'])
        t['planned_risk_cash']=float(a['risk_cash'])
        t['fill_rr']=abs(float(a['target'])-float(a['entry']))/abs(float(a['entry'])-float(a['stop']))
    useful=[line for line in journal.splitlines() if re.search('real ticks|execution delay|RAW CONTRACT|SELF TEST|no history|no prices|not enough money|stopped because',line,re.I)]
    stats.update(zones=sum(r['event']=='zone' for r in audit),holds=sum(r['event']=='held' for r in audit),
                 signals=len(sig),execution_errors=[r['detail'] for r in audit if r['event']=='error'],
                 rejected=sum(r['event']=='rejected' for r in audit),
                 planned_risk_pct_min=min((100*float(r['risk_cash'])/float(r['equity']) for r in sig),default=0),
                 planned_risk_pct_max=max((100*float(r['risk_cash'])/float(r['equity']) for r in sig),default=0),
                 fill_rr_min=min((t['fill_rr'] for t in trades),default=None),
                 fill_rr_max=max((t['fill_rr'] for t in trades),default=None),
                 quality_journal=useful,
                 boundary_exits=sum(r['event']=='exit' and r['detail']=='0' for r in audit))
    row={'symbol_requested':symbol,'period':period,'from':start.replace('.','-'),'to_exclusive':end.replace('.','-'),
         'model':model,'execution_delay_ms':1,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
         'elapsed_seconds':round(time.time()-started,1),**stats}
    (ROOT/'Audit'/f'{tag}-trades.json').write_text(json.dumps(trades,indent=2),encoding='utf-8')
    (ROOT/f'{tag}-stats.json').write_text(json.dumps(row,indent=2),encoding='utf-8')
    print('DONE '+json.dumps({k:row[k] for k in ('symbol_requested','period','model','return_pct','net_pf','net_win_rate','trades','max_drawdown_pct','execution_errors','zones','holds')}),flush=True)
    return row

def main():
    cli=argparse.ArgumentParser();cli.add_argument('--symbols',default='XAUUSD,USTEC');cli.add_argument('--periods',default=','.join(WINDOWS));cli.add_argument('--model',type=int,choices=(0,1,4),default=4);cli.add_argument('--compile-only',action='store_true');cli.add_argument('--refresh-session',action='store_true')
    args=cli.parse_args()
    if args.refresh_session:refresh_isolated_session()
    prepare()
    if args.compile_only:return
    rows=[]
    for symbol in args.symbols.split(','):
        for period in args.periods.split(','): rows.append(run(symbol,period,args.model))
    (ROOT/f'run-summary-model{args.model}.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
if __name__=='__main__':main()
