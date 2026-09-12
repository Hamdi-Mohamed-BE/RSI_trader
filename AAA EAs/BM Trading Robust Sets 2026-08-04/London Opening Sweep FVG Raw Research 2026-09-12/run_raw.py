from __future__ import annotations

import argparse
import configparser
import csv
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / '_Backtests' / 'MT5-DMC-20260811'
NAME = 'XAU London Opening Sweep FVG Raw'
EXPERT_FOLDER = Path('AAA Research') / 'London Sweep FVG 20260912'
SOURCE = ROOT / 'EA' / f'{NAME}.mq5'
WINDOWS = {
    '6m': ('2026.03.05', '2026.09.05'),
    '1y': ('2025.09.05', '2026.09.05'),
    '3y': ('2023.09.05', '2026.09.05'),
    '5y': ('2021.09.05', '2026.09.05'),
}
sys.path.insert(0, str(PACKAGE.parent / 'EA store'))
from app.mt5_evidence_jobs import _native_trades

spec = importlib.util.spec_from_file_location('london_report_parser', PACKAGE / 'POC Fibonacci Volume Profile Research 2026-09-04' / 'Analyze-POCFib.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

def hidden_startup():
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    return info

def prepare():
    target = TESTER / 'MQL5' / 'Experts' / EXPERT_FOLDER
    for path in (target, ROOT / 'Sets', ROOT / 'Backtest Reports', ROOT / 'Audit', TESTER / 'backtest-configs' / 'london-sweep-fvg', TESTER / 'reports' / 'london-sweep-fvg'):
        path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, target / SOURCE.name)
    log = ROOT / 'compile.log'
    command = f'"{TESTER / "MetaEditor64.exe"}" /portable /compile:"{target / SOURCE.name}" /log:"{log}"'
    process = subprocess.run(command, cwd=TESTER, timeout=120, startupinfo=hidden_startup())
    content = log.read_text(encoding='utf-16', errors='replace')
    if '0 errors, 0 warnings' not in content:
        raise RuntimeError(content)
    shutil.copy2(target / f'{NAME}.ex5', ROOT / 'EA' / f'{NAME}.ex5')
    print('COMPILE OK', flush=True)

def metrics(report, audit_path, label):
    summary = parser.parse_report(report)
    summary.pop('score', None)
    summary.pop('deals', None)
    trades = _native_trades(report, label)
    assert len(trades) == summary['trades'], (len(trades), summary['trades'])
    net = round(sum(t['net_profit'] for t in trades), 2)
    assert abs(net-summary['net_profit']) < .05, (net, summary['net_profit'])
    wins = [t['net_profit'] for t in trades if t['net_profit'] > 0]
    losses = [t['net_profit'] for t in trades if t['net_profit'] < 0]
    ws = ls = max_ws = max_ls = 0
    for trade in trades:
        value = trade['net_profit']
        if value > 0:
            ws += 1; ls = 0; max_ws = max(max_ws, ws)
        elif value < 0:
            ls += 1; ws = 0; max_ls = max(max_ls, ls)
        else:
            ls = ws = 0
    rows = list(csv.DictReader(audit_path.open(encoding='utf-8-sig')))
    orders = [r for r in rows if r['event'] == 'limit']
    fills = [r for r in rows if r['event'] == 'fill']
    errors = [r for r in rows if r['event'] == 'error']
    ratios = [abs(float(r['target'])-float(r['entry']))/abs(float(r['entry'])-float(r['stop'])) for r in orders if float(r['entry']) != float(r['stop'])]
    for trade in trades:
        opened = datetime.fromisoformat(trade['open_time'])
        closed = datetime.fromisoformat(trade['close_time'])
        trade['holding_minutes'] = (closed-opened).total_seconds()/60
        matching = [r for r in orders if r['server_time'].replace('.', '-').replace(' ', 'T') <= trade['open_time']]
        if matching:
            order = matching[-1]
            trade['planned_entry'] = float(order['entry'])
            trade['initial_stop'] = float(order['stop'])
            trade['initial_target'] = float(order['target'])
            trade['planned_rr'] = abs(float(order['target'])-float(order['entry'])) / abs(float(order['entry'])-float(order['stop']))
            trade['sweep_confirmed'] = order['sweep_confirmed']
    summary.update({
        'net_ledger_pf': round(sum(wins)/-sum(losses), 4) if losses else None,
        'net_ledger_win_rate': round(len(wins)/len(trades)*100, 2) if trades else 0,
        'wins': len(wins), 'losses': len(losses), 'breakeven': len(trades)-len(wins)-len(losses),
        'max_win_streak': max_ws, 'max_loss_streak': max_ls,
        'average_win': round(sum(wins)/len(wins), 2) if wins else 0,
        'average_loss': round(sum(losses)/len(losses), 2) if losses else 0,
        'largest_win': max(wins, default=0), 'largest_loss': min(losses, default=0),
        'long_trades': sum(t['side']=='Long' for t in trades),
        'short_trades': sum(t['side']=='Short' for t in trades),
        'long_net': round(sum(t['net_profit'] for t in trades if t['side']=='Long'), 2),
        'short_net': round(sum(t['net_profit'] for t in trades if t['side']=='Short'), 2),
        'first_trade': trades[0]['open_time'] if trades else None,
        'last_trade': trades[-1]['close_time'] if trades else None,
        'max_holding_minutes': max((t['holding_minutes'] for t in trades), default=0),
        'overnight_trades': sum(t['open_time'][:10] != t['close_time'][:10] for t in trades),
        'ranges': sum(r['event']=='range' for r in rows),
        'sweeps': sum(r['event']=='sweep' for r in rows),
        'fvgs': sum(r['event']=='fvg' for r in rows),
        'pending_orders': len(orders), 'audit_fills': len(fills),
        'execution_errors': len(errors), 'error_examples': errors[:5],
        'median_planned_rr': sorted(ratios)[len(ratios)//2] if ratios else None,
        'mean_planned_rr': sum(ratios)/len(ratios) if ratios else None,
    })
    return summary, trades

def run(tf, period, model):
    start, end = WINDOWS[period]
    tag = f'xau-london-sweep-fvg-m{tf}-{period}-model{model}'
    magic = 84124000 + tf*100 + list(WINDOWS).index(period)*10 + model
    set_name = f'{tag}.set'
    settings = f'InpRiskPercent=1\nInpEntryTimeframe={tf}\nInpLondonOpenHour=8\nInpLondonEndHour=17\nInpTesterServerUTCOffsetHours=0\nInpDeviationPoints=30\nInpMagic={magic}\n'
    (ROOT / 'Sets' / set_name).write_text(settings, encoding='utf-8')
    shutil.copy2(ROOT / 'Sets' / set_name, TESTER / 'MQL5' / 'Profiles' / 'Tester' / set_name)
    reference = configparser.ConfigParser()
    reference.read(TESTER / 'backtest-configs' / 'xauusd-closing-momentum-20260912' / '6m.ini', encoding='utf-16')
    common = dict(reference['Common'])
    content = '[Common]\n' + ''.join(f'{k}={v}\n' for k,v in common.items()) + '\n[Tester]\n'
    content += f'Expert={EXPERT_FOLDER}\\{NAME}\nExpertParameters={set_name}\nSymbol=XAUUSD\nPeriod=M1\n'
    content += f'Login={common["login"]}\nDeposit=10000\nCurrency=USD\nLeverage=1:2000\nModel={model}\nExecutionMode=1\nOptimization=0\n'
    content += f'FromDate={start}\nToDate={end}\nForwardMode=0\nReport=reports\\london-sweep-fvg\\{tag}.htm\nReplaceReport=1\nShutdownTerminal=1\nUseCloud=0\nVisual=0\n'
    config = TESTER / 'backtest-configs' / 'london-sweep-fvg' / f'{tag}.ini'
    config.write_text(content, encoding='utf-16')
    report = TESTER / 'reports' / 'london-sweep-fvg' / f'{tag}.htm'
    started = time.time()
    print(f'START {tag} {start} to {end}', flush=True)
    process = subprocess.Popen([str(TESTER / 'terminal64.exe'), '/portable', f'/config:{config.relative_to(TESTER)}'], cwd=TESTER, startupinfo=hidden_startup(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        process.kill()
        raise RuntimeError(f'Tester exceeded 30 minutes for {tag}')
    if not report.is_file() or report.stat().st_mtime < started-2:
        raise RuntimeError(f'Tester did not create a fresh report for {tag}')
    for path in report.parent.glob(tag+'*'):
        shutil.copy2(path, ROOT / 'Backtest Reports' / path.name)
    audit_name = f'LondonSweepFVG-{magic}.csv'
    audits = sorted((TESTER / 'Tester').glob(f'Agent-*/MQL5/Files/{audit_name}'), key=lambda p:p.stat().st_mtime, reverse=True)
    if not audits or audits[0].stat().st_mtime < started-2:
        raise RuntimeError(f'No fresh signal audit for {tag}')
    audit_saved = ROOT / 'Audit' / f'{tag}.csv'
    shutil.copy2(audits[0], audit_saved)
    stats, trades = metrics(report, audit_saved, f'London H1 Sweep / M{tf} FVG')
    row = {'entry_timeframe':f'M{tf}', 'period':period, 'from':start.replace('.', '-'), 'to_exclusive':end.replace('.', '-'), 'model':model, 'model_label':{0:'generated Every Tick',1:'1-minute OHLC',4:'Every Tick based on real ticks requested'}[model], **stats}
    (ROOT / 'Audit' / f'{tag}-trades.json').write_text(json.dumps(trades, indent=2), encoding='utf-8')
    (ROOT / f'{tag}-stats.json').write_text(json.dumps(row, indent=2), encoding='utf-8')
    print('DONE '+json.dumps({k:row[k] for k in ('entry_timeframe','period','model','return_pct','profit_factor','win_rate_pct','trades','max_drawdown_pct','execution_errors','overnight_trades')}), flush=True)
    return row

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--model', type=int, default=4, choices=(0,1,4))
    cli.add_argument('--periods', default=','.join(WINDOWS))
    cli.add_argument('--timeframes', default='1,5,15')
    args=cli.parse_args()
    prepare()
    rows=[]
    for period in args.periods.split(','):
        for tf in map(int,args.timeframes.split(',')):
            rows.append(run(tf, period, args.model))
    (ROOT/f'results-model{args.model}.json').write_text(json.dumps(rows,indent=2), encoding='utf-8')

if __name__=='__main__':
    main()
