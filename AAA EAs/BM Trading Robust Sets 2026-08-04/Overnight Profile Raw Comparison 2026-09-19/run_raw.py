"""Six independent raw native runs. No normal-terminal trading or deployment."""
from __future__ import annotations
import argparse, csv, hashlib, json, re, shutil, subprocess, sys, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import MetaTrader5 as mt5
import numpy as np

ROOT=Path(__file__).resolve().parent
PACKAGE=ROOT.parent
TESTER=PACKAGE/'_Backtests'/'MT5-DMC-20260811'
NORMAL=Path('C:/Program Files/MetaTrader 5/terminal64.exe')
SOURCE=ROOT/'Overnight Profile Raw.mq5'
START='2025.09.19';END='2026.09.19';NY=ZoneInfo('America/New_York')
sys.path.insert(0,str(PACKAGE.parent/'EA store'))
from app.mt5_evidence_jobs import _native_metrics, _native_trades, _read_report, _metric, _report_inputs, _same_setting

def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):
    raw=path.read_bytes()
    return raw.decode('utf-16') if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else raw.decode('utf-8-sig')
def connected():
    assert mt5.initialize(str(NORMAL)),mt5.last_error()
    account=mt5.account_info();terminal=mt5.terminal_info()
    assert account and terminal and terminal.connected,'Normal account is not connected'
    return account,terminal

def prepare():
    account,terminal=connected()
    # Account is dynamically discovered, not a fallback to an archived login.
    assert account.server.startswith('Exness-'),'This study requires an explicitly verified server clock for a different broker'
    all_symbols=mt5.symbols_get();chosen={}
    for canonical,aliases in {'XAU':['XAUUSD','GOLD'],'US100':['USTEC','US100','NAS100'],'SP500':['US500','SP500','SPX500']}.items():
        candidates=[s for s in all_symbols if any(s.name.upper()==a for a in aliases) and s.trade_mode==4]
        assert len(candidates)==1,(canonical,[s.name for s in candidates])
        chosen[canonical]=candidates[0].name
    spec_fields=['name','description','path','trade_contract_size','trade_tick_size','trade_tick_value','volume_min','volume_step','volume_max','trade_stops_level','trade_freeze_level','swap_mode','swap_long','swap_short','currency_profit']
    payload=dict(captured_utc=datetime.now(timezone.utc).isoformat(),account={k:getattr(account,k) for k in ['login','server','company','currency','leverage','trade_mode','balance','equity']},
                 normal_terminal=str(NORMAL),terminal_data_path=terminal.data_path,symbols=chosen,
                 contracts={key:{k:getattr(mt5.symbol_info(symbol),k) for k in spec_fields} for key,symbol in chosen.items()},
                 start=START,end_exclusive=END,deposit=10000,risk_percent=1,model=4,execution_delay_ms=150,server_utc_offset_hours=0,
                 source_sha256=sha(SOURCE),rules_sha256=sha(ROOT/'RULES.md'),scope='Two new raw profile versions only. Existing strategy transfers deferred. No live deployment.')
    save(ROOT/'manifest.json',payload)
    mt5.shutdown()
    log=ROOT/'compile.log';began=time.time()
    subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{SOURCE}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=90)
    assert log.stat().st_mtime>=began-1 and '0 errors, 0 warnings' in read(log),read(log)
    dest=TESTER/'MQL5'/'Experts'/'AAA Research'/'ONVP Raw 20260919'
    dest.mkdir(parents=True,exist_ok=True);shutil.copy2(SOURCE.with_suffix('.ex5'),dest/SOURCE.with_suffix('.ex5').name)
    payload['binary_sha256']=sha(SOURCE.with_suffix('.ex5'));save(ROOT/'manifest.json',payload)
    print('PREPARED',chosen,flush=True)
    return payload

def logs():
    return list((TESTER/'Tester'/'logs').glob('*.log'))+list((TESTER/'Tester').glob('Agent-*/logs/*.log'))

def run_case(meta,asset,mode):
    account,_=connected();assert account.login==meta['account']['login'] and account.server==meta['account']['server'],'Connected account changed';mt5.shutdown()
    case=f'onvp-{asset.lower()}-{mode}-20260919';out=ROOT/'native'/case;out.mkdir(parents=True,exist_ok=True)
    params=dict(InpDirectionMode=0 if mode=='VA' else 1,InpBins=64,InpValueAreaPercent=70,InpMinimumProfileBars=120,
                InpRiskPercent=1,InpServerUTCOffsetHours=0,InpExpectedLogin=meta['account']['login'],InpExpectedServer=meta['account']['server'],InpMagic=89191901,InpCase=case)
    fp=hashlib.sha256(json.dumps([meta['source_sha256'],meta['binary_sha256'],params,meta['symbols'][asset],START,END,150],sort_keys=True).encode()).hexdigest()
    summary_path=out/'summary.json'
    if summary_path.exists() and json.loads(summary_path.read_text()).get('fingerprint')==fp:
        print('REUSE',case,flush=True);return json.loads(summary_path.read_text())
    text='\n'.join(f'{k}={v}' for k,v in params.items())+'\n';setname=case+'.set'
    (out/setname).write_text(text);(TESTER/'MQL5'/'Profiles'/'Tester'/setname).write_text(text)
    config=out/'tester.ini'
    config.write_text(f'''[Common]
Login={meta['account']['login']}
Server={meta['account']['server']}
[Experts]
Enabled=0
AllowLiveTrading=0
AllowDllImport=0
[Tester]
Expert=AAA Research\\ONVP Raw 20260919\\Overnight Profile Raw
ExpertParameters={setname}
Symbol={meta['symbols'][asset]}
Period=M5
Deposit=10000
Currency=USD
Leverage=1:{meta['account']['leverage']}
Model=4
ExecutionMode=150
Optimization=0
FromDate={START}
ToDate={END}
ForwardMode=0
Report=reports\\{case}.htm
ReplaceReport=1
ShutdownTerminal=1
UseLocal=1
UseRemote=0
UseCloud=0
Visual=0
''',encoding='utf-8-sig')
    offsets={p:p.stat().st_size for p in logs()};began=time.time()
    save(ROOT/'progress.json',dict(case=case,state='running',started_utc=datetime.now(timezone.utc).isoformat()))
    print('START',case,flush=True)
    process=subprocess.Popen(f'"{TESTER/"terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{config}"',cwd=TESTER,creationflags=subprocess.CREATE_NO_WINDOW)
    try:process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        process.terminate();process.wait(timeout=15);raise
    journal=''
    for path in logs():
        if path.stat().st_mtime<began:continue
        with path.open('rb') as h:h.seek(offsets.get(path,0));journal+=h.read().decode('utf-16-le',errors='replace')
    (out/'journal.txt').write_text(journal)
    report=TESTER/'reports'/(case+'.htm')
    assert report.exists() and report.stat().st_mtime>=began-2,'Missing fresh native report: '+case
    for p in report.parent.glob(case+'*'):
        if p.is_file() and p.stat().st_mtime>=began-2:shutil.copy2(p,out/p.name)
    audits=[p for p in (TESTER/'Tester').glob(f'Agent-*/MQL5/Files/{case}-audit.csv') if p.stat().st_mtime>=began-2]
    assert len(audits)==1,audits
    shutil.copy2(audits[0],out/'audit.csv')
    save(out/'run.json',dict(asset=asset,mode=mode,params=params,fingerprint=fp,elapsed_seconds=time.time()-began,**meta))
    row=parse_case(out);save(out/'summary.json',row);print('DONE',case,row['return_pct'],row['trades'],row['history_quality'],flush=True)
    return row

def parse_case(out):
    run=json.loads((out/'run.json').read_text());case=run['params']['InpCase'];report=out/(case+'.htm')
    inputs=_report_inputs(report)
    for key,value in run['params'].items():assert key in inputs and _same_setting(str(value),inputs[key]),(key,value,inputs.get(key))
    text=_read_report(report);stats=_native_metrics(report);trades=_native_trades(report,case)
    assert stats['initial_balance']==10000 and len(trades)==stats['trades']
    assert abs(sum(t['net_profit'] for t in trades)-stats['net_profit'])<.06
    audit=list(csv.DictReader((out/'audit.csv').open(encoding='utf-8-sig')))
    entry_audit=[a for a in audit if a['kind']=='entry'];assert len(entry_audit)==len(trades)
    journal=(out/'journal.txt').read_text()
    match=re.search(r'ONVP_SUMMARY\|'+re.escape(case)+r'\|([^\r\n]+)',journal);assert match,'Missing native audit'
    counters={k:float(v) for k,v in (p.split('=',1) for p in match[1].split('|'))}
    assert int(counters['entries'])==len(trades)
    assert counters['signals']==counters['entries']+counters['invalid_geometry']+counters['rejected']
    contract=run['contracts'][run['asset']]['trade_contract_size']
    balance=10000;seen=set();months=defaultdict(list)
    for t,a in zip(trades,entry_audit):
        opened=datetime.fromisoformat(t['open_time']).replace(tzinfo=timezone.utc);closed=datetime.fromisoformat(t['close_time']).replace(tzinfo=timezone.utc)
        day=opened.astimezone(NY).date();assert day not in seen,'More than one entry in a NY day';seen.add(day)
        assert opened.astimezone(NY).hour*60+opened.astimezone(NY).minute>=575,'Early entry'
        sign=1 if t['side']=='Long' else -1
        assert abs((t['close_price']-t['open_price'])*sign*t['volume']*contract-t['gross_profit'])<.12,'Contract P/L mismatch'
        stop=float(a['stop']);target=float(a['target']);risk=abs(t['open_price']-stop)*t['volume']*contract
        t.update(stop=stop,target=target,initial_risk_usd=risk,initial_risk_pct=100*risk/balance,
                 initial_rr=abs(target-t['open_price'])/abs(t['open_price']-stop),net_r=t['net_profit']/risk,
                 held_overnight=day!=closed.astimezone(NY).date(),
                 scheduled_exit_utc=datetime.fromtimestamp(int(a['cutoff_epoch']),timezone.utc).isoformat(),
                 exit_delay_minutes=max(0,(closed.timestamp()-int(a['cutoff_epoch']))/60),
                 entry_slippage_price=(t['open_price']-float(a['requested_entry']))*sign)
        t['open_time']=opened.isoformat();t['close_time']=closed.isoformat();balance+=t['net_profit'];t['balance_after']=round(balance,2)
        months[closed.astimezone(NY).strftime('%Y-%m')].append(t)
    pos=sum(max(0,t['net_profit']) for t in trades);neg=sum(max(0,-t['net_profit']) for t in trades)
    dd=re.match(r'([\d.]+)%',_metric(text,'Equity Drawdown Relative'));assert dd
    bdd=re.match(r'([\d.]+)%',_metric(text,'Balance Drawdown Relative'));assert bdd
    stats.update(asset=run['asset'],symbol=run['symbols'][run['asset']],mode=run['mode'],fingerprint=run['fingerprint'],
                 profit_factor=pos/neg if neg else None,win_rate_pct=100*sum(t['net_profit']>0 for t in trades)/len(trades) if trades else 0,
                 native_relative_equity_dd_pct=float(dd[1]),tick_observed_equity_dd_pct=counters['max_equity_dd'],
                 max_drawdown_pct=max(float(dd[1]),counters['max_equity_dd']),balance_drawdown_pct=float(bdd[1]),commission=sum(t['commission'] for t in trades),swap=sum(t['swap'] for t in trades),
                 average_rr=float(np.mean([t['initial_rr'] for t in trades])) if trades else None,
                 min_equity=counters['min_equity'],overnight_holdings=sum(t['held_overnight'] for t in trades),audit=counters,
                 exits_over_one_minute_late=sum(t['exit_delay_minutes']>1 for t in trades),
                 max_exit_delay_minutes=max((t['exit_delay_minutes'] for t in trades),default=0),
                 max_initial_risk_pct=max((t['initial_risk_pct'] for t in trades),default=0),report_sha256=sha(report),
                 warnings=[line.strip() for line in journal.splitlines() if any(s in line.lower() for s in ['real ticks absent','no real ticks','ticks discarded','mismatch','not enough money','no history data'])])
    for name,sign in [('win',1),('loss',-1)]:
        current=maximum=0
        for t in trades:
            current=current+1 if sign*t['net_profit']>0 else 0;maximum=max(maximum,current)
        stats['max_'+name+'_streak']=maximum
    stats['average_trade_usd']=stats['net_profit']/len(trades) if trades else 0
    stats['wins']=sum(t['net_profit']>0 for t in trades)
    stats['losses']=sum(t['net_profit']<0 for t in trades)
    stats['long_trades']=sum(t['side']=='Long' for t in trades)
    stats['short_trades']=sum(t['side']=='Short' for t in trades)
    stats['observed_roundtrip_commission_per_lot']=float(np.median([-t['commission']/t['volume'] for t in trades])) if trades else None
    stats['real_tick_start_lines']=sorted(set(line.split('Ticks',1)[-1].strip() for line in journal.splitlines() if 'real ticks begin from' in line))
    stats['months']=[dict(month=m,trades=len(ts),wins=sum(t['net_profit']>0 for t in ts),net_profit=round(sum(t['net_profit'] for t in ts),2),commission=round(sum(t['commission'] for t in ts),2),swap=round(sum(t['swap'] for t in ts),2)) for m,ts in sorted(months.items())]
    save(out/'trades.json',trades);return stats

def report(rows):
    save(ROOT/'results.json',rows)
    lines=['# Overnight Profile — raw native MT5 comparison','',f'Window: {START} through {END} exclusive. Each strategy starts with $10,000 at 1% equity risk. No optimization.','',
           '| Asset | Direction | Return | Net USD | Trades | Net win rate | Net PF | Equity DD | Commission | Swap | Real-tick quality |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for r in rows:
        pf=f"{r['profit_factor']:.2f}" if r['profit_factor'] is not None else 'N/A'
        lines.append(f"| {r['symbol']} | {r['mode']} | {r['return_pct']:+.2f}% | {r['net_profit']:+.2f} | {r['trades']} | {r['win_rate_pct']:.2f}% | {pf} | {r['max_drawdown_pct']:.2f}% | {r['commission']:.2f} | {r['swap']:.2f} | {r['history_quality']} |")
    lines+=['','## Interpretation and limitations','',
            '- VA means close above/below the 70% value area; POC means close above/below its point of control. See RULES.md for the exact frozen assumptions.',
            '- Bid/ask spread and reported deal commissions/swaps are included. Native 150 ms delay creates modeled execution effects, not proof of live fill quality.',
            '- Profile uses completed M1 tick-volume at typical price, not futures traded volume. Reported generated-tick periods must not be described as real-tick proof.',
            '- Equity DD displayed is the larger of MT5 reported relative equity DD and the tick-by-tick EA equity audit. Both values are retained below; this conservatively avoids hiding a higher observed drawdown. It is not balance-only drawdown.',
            '- First and last monthly rows are partial months (September 19 onward / through September 18). Historical broker session/holiday closures can reject/delay the 16:00 NY exit. Therefore these results are NOT proof of a strict exit-by-16:00 strategy; late exits and overnight holdings are explicitly counted.',
            '- No website or BAT updates, no deployment, no older strategy transfers.',
            '', '## Signal and sizing audit','', '| Asset / mode | Profile days | Missing profiles | Signals | Invalid geometry | Rejected | Late exits >1m | Overnight holds | Max initial stop risk |', '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        a=r['audit'];lines.append(f"| {r['symbol']} {r['mode']} | {int(a['profiles'])} | {int(a['missing'])} | {int(a['signals'])} | {int(a['invalid_geometry'])} | {int(a['rejected'])} | {r['exits_over_one_minute_late']} | {r['overnight_holdings']} | {r['max_initial_risk_pct']:.3f}% |")
    lines+=['','## Exit, drawdown and streak detail','', '| Asset / mode | Average initial RR | Win streak | Loss streak | MT5 equity DD | Tick-audit equity DD | Average net trade |', '|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"| {r['symbol']} {r['mode']} | {r['average_rr']:.3f}R | {r['max_win_streak']} | {r['max_loss_streak']} | {r['native_relative_equity_dd_pct']:.2f}% | {r['tick_observed_equity_dd_pct']:.2f}% | ${r['average_trade_usd']:+.2f} |")
    lines+=['','## Monthly net USD (closed trades, including fees)','', '| Month | '+' | '.join(r['symbol']+' '+r['mode'] for r in rows)+' |','|---|'+'---:|'*len(rows)]
    months=sorted({m['month'] for r in rows for m in r['months']})
    for m in months:
        cells=[]
        for r in rows:
            match=next((x for x in r['months'] if x['month']==m),None)
            cells.append(f"{match['net_profit']:+.2f} ({match['trades']} trades)" if match else '0.00 (0 trades)')
        lines.append('| '+m+' | '+' | '.join(cells)+' |')
    (ROOT/'RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prepare-only',action='store_true');ap.add_argument('--assets',default='XAU,US100,SP500');ap.add_argument('--report-only',action='store_true');args=ap.parse_args()
    if args.report_only:
        rows=[parse_case(p.parent) for p in sorted((ROOT/'native').glob('*/run.json'))]
        for row in rows:save(ROOT/'native'/f"onvp-{row['asset'].lower()}-{row['mode']}-20260919"/'summary.json',row)
        report(rows);return
    meta=prepare()
    if args.prepare_only:return
    rows=[]
    for asset in args.assets.split(','):
        for mode in ['VA','POC']:
            rows.append(run_case(meta,asset,mode));report(rows)
    save(ROOT/'progress.json',dict(state='completed',cases=len(rows)))
if __name__=='__main__':main()
