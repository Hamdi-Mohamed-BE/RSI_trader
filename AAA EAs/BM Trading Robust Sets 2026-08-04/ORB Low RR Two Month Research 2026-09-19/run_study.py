"""Frozen low-RR comparison of seven active ORBs in an isolated native MT5 tester.

Generated .set/.ini files are research artifacts. No installer, live account,
deployed EA source, website, or portfolio configuration is modified.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / '_Backtests' / 'MT5-DMC-20260811'
SELECTED = PACKAGE / 'Selected Portfolio Settings 2026-09-01'
EXPERT_SUBDIR = Path('AAA Research') / 'ORB Low RR 20260919'
START, END = '2026.07.19', '2026.09.19'
PRAGUE = ZoneInfo('Europe/Prague')
NO_WINDOW = subprocess.CREATE_NO_WINDOW

EAS = [
    ('vp', 'XAU ORB Volume Profile', 'XAUUSD', 5, 'ORB Volume Audit', SELECTED/'05 ORB Volume Profile - DYNAMIC 50-20 - ALL DAY.set'),
    ('vpc', 'XAU ORB Volume Confirmed', 'XAUUSD', 5, 'ORB Volume Audit', SELECTED/'05C ORB Volume Profile Volume Confirmed - DYNAMIC 50-20 - ALL DAY.set'),
    ('xny', 'XAU ORB New York M30', 'XAUUSD', 30, 'ORB Volume Audit', SELECTED/'14 XAU ORB New York M30 - LOCKED STANDALONE.set'),
    ('xov', 'XAU ORB London/NY Overlap M30', 'XAUUSD', 30, 'ORB Volume Audit', SELECTED/'15 XAU ORB London NY Overlap M30 - LOCKED STANDALONE.set'),
    ('uny', 'US100 ORB New York M30', 'USTEC', 30, 'ORB Volume Audit', SELECTED/'16 US100 ORB New York M30 - LOCKED STANDALONE.set'),
    ('uh1', 'US100 H1 ORB 13UTC', 'USTEC', 15, 'ORB Volume Audit', PACKAGE/'ORB H1 Range Research 2026-09-05'/'Sets'/'USTEC - overlap-1300 - H1 opening range - RR6 - 1pct.set'),
    ('usel', 'US100 Selective ORB V3', 'USTEC', 5, 'Selective ORB Audit', PACKAGE/'US100 Selective ORB Research 2026-08-21'/'Sets'/'BEST V3 - US100 USTEC M5 - TIME DIRECTION OR30 - 1pct.set'),
]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def read_text(path):
    raw=path.read_bytes()
    if raw[:2] in (b'\xff\xfe',b'\xfe\xff') or b'\x00' in raw[:200]:
        return raw.decode('utf-16')
    return raw.decode('utf-8-sig')


def settings(path):
    result={}
    for line in read_text(path).splitlines():
        line=line.strip()
        if not line or line.startswith(';') or '=' not in line:
            continue
        key,value=line.split('=',1)
        result[key]=value.split('||')[0]
    return result


def number(value):
    return float(value.replace(' ','').replace('\xa0','')) if value.strip() else 0.0


def compile_wrappers():
    dest=TESTER/'MQL5'/'Experts'/EXPERT_SUBDIR
    dest.mkdir(parents=True,exist_ok=True)
    for name in ('ORB Volume Audit','Selective ORB Audit'):
        source=ROOT/(name+'.mq5')
        log=ROOT/(name+'.compile.log')
        began=time.time()
        command=f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{source}" /log:"{log}"'
        subprocess.run(command,
                       timeout=45,creationflags=NO_WINDOW,check=False)
        if log.stat().st_mtime<began-1 or '0 errors, 0 warnings' not in read_text(log):
            raise RuntimeError(read_text(log)[-4000:])
        shutil.copy2(source.with_suffix('.ex5'),dest/(name+'.ex5'))


def parse_native(report, native_journal, config, meta):
    parser_path=PACKAGE/'US100 Momentum Continuation Research 2026-08-31'/'Analyze-Reports.py'
    spec=importlib.util.spec_from_file_location('native_parser',parser_path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    summary=module.parse_report(report)
    soup=BeautifulSoup(read_text(report),'html.parser')
    section=None
    orders,trades={},[]
    opened=None
    for row in soup.find_all('tr'):
        title=row.get_text(' ',strip=True)
        if title in ('Orders','Deals'):
            section=title
            continue
        cells=[' '.join(c.get_text(' ',strip=True).split()) for c in row.find_all('td')]
        if not cells or not re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',cells[0]):
            continue
        if section=='Orders' and len(cells)==11:
            orders[int(cells[1])]=dict(stop=number(cells[6]),target=number(cells[7]))
        elif section=='Deals' and len(cells)==13 and cells[4] in ('in','out'):
            when=datetime.strptime(cells[0],'%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc)
            commission,swap,gross,balance=[number(cells[i]) for i in (8,9,10,11)]
            if cells[4]=='in':
                assert opened is None, 'Overlapping trades need an expanded parser'
                opened=dict(entry_time=when.isoformat(),side=cells[3],volume=number(cells[5]),entry_price=number(cells[6]),
                            entry_cash=commission+swap+gross,entry_commission=commission,entry_swap=swap,
                            balance_before=balance-commission-swap-gross,order=int(cells[7]),**orders[int(cells[7])])
            else:
                assert opened is not None,'Unmatched exit'
                assert abs(opened['volume']-number(cells[5]))<0.000001,'Partial exit not supported in these seven EAs'
                trade=dict(**opened,exit_time=when.isoformat(),exit_price=number(cells[6]),
                           gross_profit=gross,commission=opened['entry_commission']+commission,
                           swap=opened['entry_swap']+swap,net_profit=round(opened['entry_cash']+commission+swap+gross,2),
                           balance_after=balance,exit_comment=cells[12])
                contract=100.0 if meta['symbol']=='XAUUSD' else 1.0
                move=(trade['exit_price']-trade['entry_price'])*(1 if trade['side']=='buy' else -1)
                assert abs(move*contract*trade['volume']-gross)<0.11,'Unexpected contract P/L calculation'
                trade['initial_risk_usd']=abs(trade['entry_price']-trade['stop'])*contract*trade['volume']
                trade['initial_risk_pct']=100*trade['initial_risk_usd']/trade['balance_before']
                trade['target_r']=abs(trade['target']-trade['entry_price'])/abs(trade['entry_price']-trade['stop'])
                assert abs(trade['target_r']-float(config['InpRewardRisk']))<0.02,'RR mismatch'
                trade['entry_day_prague']=datetime.fromisoformat(trade['entry_time']).astimezone(PRAGUE).date().isoformat()
                trade['exit_day_prague']=when.astimezone(PRAGUE).date().isoformat()
                assert abs(trade['balance_before']+trade['net_profit']-trade['balance_after'])<0.021
                trades.append(trade)
                opened=None
    assert opened is None
    assert len(trades)==summary['trades']
    assert abs(sum(t['net_profit'] for t in trades)-summary['net_profit'])<0.03
    assert summary['initial_balance']==10000 and summary['bars']>0
    text=' '.join(soup.get_text(' ').split())
    abs_dd=re.search(r'Equity Drawdown Absolute:\s*([\d .]+)',text)
    summary['minimum_equity_native']=10000-number(abs_dd.group(1))
    audit_lines=[l for l in native_journal.splitlines() if f'TRIAL_AUDIT|{meta["case"]}|' in l]
    assert audit_lines,'Missing tick-by-tick account audit'
    audit={}
    for piece in audit_lines[-1].split('TRIAL_AUDIT|',1)[1].split('|')[1:]:
        key,value=piece.split('=',1)
        audit[key]=value
    assert abs(float(audit['final'])-summary['final_balance'])<0.02
    entry_days=len({t['entry_day_prague'] for t in trades})
    assert int(audit['entry_days'])==entry_days
    wins=sum(t['net_profit']>0 for t in trades)
    losses=sum(t['net_profit']<0 for t in trades)
    loss_cash=sum(max(0,-t['net_profit']) for t in trades)
    positive_cash=sum(max(0,t['net_profit']) for t in trades)
    streaks={}
    for name,sign in [('win',1),('loss',-1)]:
        current=longest=0
        for t in trades:
            current=current+1 if t['net_profit']*sign>0 else 0
            longest=max(longest,current)
        streaks[name]=longest
    summary.update(meta)
    summary.update(target_rr=float(config['InpRewardRisk']),net_wins=wins,net_losses=losses,
                   net_win_rate=100*wins/len(trades) if trades else 0,
                   net_pf=positive_cash/loss_cash if loss_cash else None,
                   longest_wins=streaks['win'],longest_losses=streaks['loss'],entry_days=entry_days,
                   max_initial_risk_pct=max((t['initial_risk_pct'] for t in trades),default=0),
                   min_initial_risk_pct=min((t['initial_risk_pct'] for t in trades),default=0),
                   overnight_trades=sum(t['entry_day_prague']!=t['exit_day_prague'] for t in trades),
                   audit=audit,config=config,
                   coverage_warnings=[l.strip() for l in native_journal.splitlines() if any(s in l.lower() for s in ('real ticks absent','no real ticks','ticks discarded','mismatch','not enough money','not enough history','no history data'))],
                   max_balance=max([10000]+[t['balance_after'] for t in trades]),
                   report_sha256=hashlib.sha256(report.read_bytes()).hexdigest())
    summary.pop('series',None)
    breach=int(audit['first_breach'])
    target=int(audit['first_target'])
    summary['phase_outcome']='passed' if target and (not breach or target<breach) else ('failed' if breach else 'pending')
    groups=defaultdict(list)
    for trade in trades:
        groups[trade['exit_day_prague'][:7]].append(trade)
    months=[]
    for month,items in groups.items():
        months.append(dict(month=month,trades=len(items),wins=sum(t['net_profit']>0 for t in items),
                           net_profit=round(sum(t['net_profit'] for t in items),2),
                           ending_balance=items[-1]['balance_after'],
                           commission=round(sum(t['commission'] for t in items),2),
                           swap=round(sum(t['swap'] for t in items),2)))
    return summary,trades,months


def run_case(ea, variant, start=START, target_percent=10, stage='phase1'):
    slug,label,symbol,period,expert,set_path=ea
    case=f'orb-lowrr-{slug}-{variant}-{stage}-20260919'
    output=ROOT/'cases'/case
    output.mkdir(parents=True,exist_ok=True)
    config=settings(set_path)
    if variant!='current':
        config['InpRewardRisk']='0.5' if variant=='rr050' else '0.75'
    config.update(InpRiskPercent='1.0',InpAdaptivePortfolioControls='false',
                  InpUseAutomaticLiveServerOffset='false',InpTesterServerUTCOffsetHours='0',
                  InpTrialAuditCase=case,InpTrialTargetPercent=str(target_percent))
    if expert=='Selective ORB Audit':
        config['InpFixedRiskMoney']='0.0'
    else:
        config['InpUseFixedTarget']='true'
        config['InpUseMarkovRegimeFilter']='false'
    expert_path=TESTER/'MQL5'/'Experts'/EXPERT_SUBDIR/(expert+'.ex5')
    fingerprint=hashlib.sha256(expert_path.read_bytes()+json.dumps(config,sort_keys=True).encode()+start.encode()+END.encode()).hexdigest()
    saved=output/'summary.json'
    if saved.exists():
        row=json.loads(saved.read_text())
        if row.get('fingerprint')==fingerprint:
            print(f'SAVED {case}',flush=True)
            return row
    set_text='\n'.join(f'{k}={v}' for k,v in config.items())+'\n'
    (output/(case+'.set')).write_text(set_text,encoding='utf-8')
    (TESTER/'MQL5'/'Profiles'/'Tester'/(case+'.set')).write_text(set_text,encoding='utf-8')
    ini=output/(case+'.ini')
    expert_name=str(EXPERT_SUBDIR/expert)
    ini.write_text(f'''[Common]
Login=472334559
Server=Exness-MT5Trial16
[Experts]
Enabled=0
[Tester]
Expert={expert_name}
ExpertParameters={case}.set
Symbol={symbol}
Period=M{period}
Login=472334559
Deposit=10000
Currency=USD
Leverage=1:30
Model=4
ExecutionMode=0
Optimization=0
FromDate={start}
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
    journal=TESTER/'Tester'/'logs'/'20260919.log'
    offset=journal.stat().st_size if journal.exists() else 0
    native_report=TESTER/'reports'/(case+'.htm')
    if native_report.exists():
        native_report.rename(native_report.with_name(case+f'.old-{time.time_ns()}.htm'))
    dump(ROOT/'progress.json',dict(case=case,label=label,variant=variant,stage=stage,state='running'))
    print(f'START {label} {variant} {stage}',flush=True)
    begin=time.monotonic()
    command=f'"{TESTER / "terminal64.exe"}" /portable /profile:"Calyx Research Empty" /config:"{ini}"'
    process=subprocess.Popen(command,creationflags=NO_WINDOW)
    try:
        process.wait(timeout=360)
    except subprocess.TimeoutExpired:
        # Only the isolated research process created above is stopped.
        process.terminate()
        process.wait(timeout=15)
        raise
    if not native_report.exists():
        raise RuntimeError(f'Native report missing for {case}')
    with journal.open('rb') as handle:
        handle.seek(offset)
        journal_text=handle.read().decode('utf-16-le',errors='replace')
    (output/'tester-journal.txt').write_text(journal_text,encoding='utf-8')
    for path in native_report.parent.glob(case+'*'):
        if '.old-' not in path.name:
            shutil.copy2(path,output/path.name)
    equity_files=list((TESTER/'Tester').glob(f'Agent-*/MQL5/Files/{case}-equity.csv'))
    if len(equity_files)!=1:
        raise RuntimeError(f'Expected one equity audit, found {equity_files}')
    shutil.copy2(equity_files[0],output/'daily-equity.csv')
    meta=dict(case=case,ea=label,slug=slug,symbol=symbol,variant=variant,stage=stage,start=start,end=END,
              source_set=str(set_path),source_set_sha256=hashlib.sha256(set_path.read_bytes()).hexdigest(),
              expert_sha256=hashlib.sha256(expert_path.read_bytes()).hexdigest(),fingerprint=fingerprint,
              elapsed_seconds=round(time.monotonic()-begin,2))
    row,trades,months=parse_native(output/native_report.name,journal_text,config,meta)
    dump(output/'summary.json',row)
    dump(output/'trades.json',trades)
    dump(output/'months.json',months)
    print(f'DONE {label} {variant}: trades={row["trades"]} WR={row["net_win_rate"]:.2f}% net={row["net_profit"]:.2f} DD={row["equity_dd_pct"]:.2f}% phase={row["phase_outcome"]}',flush=True)
    return row


def next_business_day(timestamp):
    day=datetime.fromtimestamp(timestamp,timezone.utc).date()+timedelta(days=1)
    while day.weekday()>4:
        day+=timedelta(days=1)
    return day.strftime('%Y.%m.%d')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--only',nargs='*')
    parser.add_argument('--no-compile',action='store_true')
    args=parser.parse_args()
    selected=[ea for ea in EAS if not args.only or ea[0] in args.only]
    plan=dict(start=START,end_exclusive=END,account=10000,requested_risk_percent=1,
              variants=['current','rr050','rr075'],broker='Exness-MT5Trial16',model=4,execution_delay=0,
              scope='Each EA standalone. No combined portfolio, no optimization.',
              rules_source='https://ftmo.com/en/trading-objectives/',
              risk_policy='Preserve deployed round-up/minimum-lot policy; record actual initial risk, which can exceed 1%.',
              management='Preserve current BE/trailing settings. Dynamic 50/20 uses fractions of TP distance, so its effective R trigger changes with TP.',
              no_live_changes=True,eas=[dict(slug=e[0],name=e[1],symbol=e[2],set=str(e[5])) for e in EAS])
    dump(ROOT/'frozen-plan.json',plan)
    if not args.no_compile:
        compile_wrappers()
    results=[]
    for ea in selected:
        for variant in ('current','rr050','rr075'):
            row=run_case(ea,variant)
            results.append(row)
            dump(ROOT/'results-partial.json',results)
    for row in results:
        if row['phase_outcome']!='passed':
            row['ftmo_outcome']='failed' if row['phase_outcome']=='failed' else 'phase1_pending'
            continue
        start=next_business_day(int(row['audit']['first_target']))
        if start>=END:
            row['ftmo_outcome']='phase1_passed_verification_not_started'
            continue
        ea=next(e for e in EAS if e[0]==row['slug'])
        verification=run_case(ea,row['variant'],start,5,'verification')
        row['verification_case']=verification['case']
        row['ftmo_outcome']={'passed':'both_phases_passed','failed':'verification_failed','pending':'verification_pending'}[verification['phase_outcome']]
    dump(ROOT/'results.json',results)
    dump(ROOT/'progress.json',dict(state='complete',cases=len(results)))
    print('COMPLETE',flush=True)


if __name__=='__main__':
    main()
