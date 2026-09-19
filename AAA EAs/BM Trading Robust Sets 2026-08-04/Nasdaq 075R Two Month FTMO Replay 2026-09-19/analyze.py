"""Reconcile the exact 0.75R native test and compare cash results to FTMO rules.

Research only. Does not connect to or change an MT5 account or deployed EAs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
TESTER = PACKAGE / '_Backtests' / 'MT5-DMC-20260811'
CASE = 'calyx-nasdaq075-recent-20260919'
PRAGUE = ZoneInfo('Europe/Prague')


def number(value):
    return float(value.replace(' ', '').replace('\xa0', '')) if value.strip() else 0.0


def load_report():
    original = TESTER / 'reports' / (CASE + '.htm')
    evidence = ROOT / 'native'
    evidence.mkdir(exist_ok=True)
    for path in original.parent.glob(CASE + '*'):
        shutil.copy2(path, evidence / path.name)
    shutil.copy2(TESTER / 'Tester' / 'logs' / '20260919.log', evidence / 'tester-journal.txt')
    report = evidence / original.name
    parser_path = PACKAGE / 'US100 Momentum Continuation Research 2026-08-31' / 'Analyze-Reports.py'
    spec = importlib.util.spec_from_file_location('native_parser', parser_path)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    summary = parser.parse_report(report)
    soup = BeautifulSoup(parser.read_report(report), 'html.parser')
    section = None
    orders, trades = {}, []
    opened = None
    for row in soup.find_all('tr'):
        cells = [' '.join(c.get_text(' ', strip=True).split()) for c in row.find_all('td')]
        title = row.get_text(' ', strip=True)
        if title in ('Orders', 'Deals'):
            section = title
            continue
        if not cells or not re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}', cells[0]):
            continue
        if section == 'Orders' and len(cells) == 11:
            orders[int(cells[1])] = dict(stop=number(cells[6]), target=number(cells[7]))
        elif section == 'Deals' and len(cells) == 13 and cells[4] in ('in', 'out'):
            timestamp = datetime.strptime(cells[0], '%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc)
            commission, swap, gross, balance = [number(cells[i]) for i in (8, 9, 10, 11)]
            if cells[4] == 'in':
                assert opened is None, 'Overlapping trades require a different audit'
                opened = dict(entry_time=timestamp.isoformat(), entry_epoch=int(timestamp.timestamp()),
                              side=cells[3], volume=number(cells[5]), entry_price=number(cells[6]),
                              entry_commission=commission, entry_swap=swap, entry_gross=gross,
                              balance_before=balance-commission-swap-gross,
                              order=int(cells[7]), **orders[int(cells[7])])
            else:
                assert opened is not None, 'Unmatched exit'
                trade = dict(**opened, exit_time=timestamp.isoformat(), exit_epoch=int(timestamp.timestamp()),
                             exit_price=number(cells[6]), exit_commission=commission,
                             exit_swap=swap, gross_profit=opened['entry_gross']+gross,
                             commission=opened['entry_commission']+commission,
                             swap=opened['entry_swap']+swap, balance_after=balance,
                             exit_comment=cells[12])
                trade['net_profit'] = round(trade['gross_profit']+trade['commission']+trade['swap'], 2)
                trade['entry_day_prague'] = datetime.fromisoformat(trade['entry_time']).astimezone(PRAGUE).date().isoformat()
                trade['exit_day_prague'] = timestamp.astimezone(PRAGUE).date().isoformat()
                trade['holding_minutes'] = (trade['exit_epoch']-trade['entry_epoch'])/60
                sign = 1 if trade['side'] == 'buy' else -1
                move = sign*(trade['exit_price']-trade['entry_price'])
                trade['cash_per_point_per_lot'] = trade['gross_profit']/move/trade['volume']
                assert abs(trade['cash_per_point_per_lot']-1) < 0.005
                # This Exness index is approximately $1/point/lot; rounding comes from report prices.
                trade['initial_price_risk_usd'] = abs(trade['entry_price']-trade['stop'])*trade['volume']
                trade['initial_price_risk_pct'] = 100*trade['initial_price_risk_usd']/trade['balance_before']
                trade['target_r'] = abs(trade['target']-trade['entry_price'])/abs(trade['entry_price']-trade['stop'])
                assert abs(trade['target_r']-0.75) < 0.001
                assert abs(trade['balance_before']+trade['net_profit']-trade['balance_after']) < 0.021
                trades.append(trade)
                opened = None
    assert opened is None
    assert len(trades) == summary['trades'] == 45
    assert abs(sum(t['net_profit'] for t in trades)-summary['net_profit']) < 0.02
    assert len({t['entry_day_prague'] for t in trades}) == len(trades)
    text = ' '.join(soup.get_text(' ').split())
    absolute_dd = float(re.search(r'Equity Drawdown Absolute:\s*([\d .]+)', text).group(1).replace(' ', ''))
    summary['minimum_equity_native'] = summary['initial_balance']-absolute_dd
    summary['maximum_balance'] = max([summary['initial_balance']]+[t['balance_after'] for t in trades])
    summary['minimum_closed_trade_balance'] = min([summary['initial_balance']]+[t['balance_after'] for t in trades])
    summary['minimum_balance_native'] = summary['initial_balance']-float(re.search(r'Balance Drawdown Absolute:\s*([\d .]+)',text).group(1).replace(' ',''))
    for name, label in [('longest_win_streak','wins'), ('longest_loss_streak','losses')]:
        summary[name] = int(re.search('Maximum consecutive '+label+r' \(\$\):\s*(\d+)', text).group(1))
    summary['risk_pct_min'] = min(t['initial_price_risk_pct'] for t in trades)
    summary['risk_pct_max'] = max(t['initial_price_risk_pct'] for t in trades)
    summary['maximum_holding_minutes'] = max(t['holding_minutes'] for t in trades)
    summary['same_prague_day_all_trades'] = all(t['entry_day_prague']==t['exit_day_prague'] for t in trades)
    summary['requested_start'] = '2026-07-19'
    summary['requested_end_exclusive'] = '2026-09-19'
    summary['initial_sync_missing_real_tick_minutes'] = 2772
    summary['initial_sync_total_minute_bars'] = 61814
    summary['initial_sync_minute_bars_with_real_ticks_pct'] = 100*(1-2772/61814)
    summary['initial_sync_whole_days_without_real_ticks'] = ['2026-09-14','2026-09-15']
    summary['data_quality_caveat'] = 'Initial synchronization reported generated fallback ticks. A later refresh added 97035 ticks. Final 100% real-tick coverage has NOT been independently certified.'
    summary['execution'] = 'Native MT5 model 4, zero added execution delay; historical tick price gaps present; no extra latency/slippage stress'
    summary['broker'] = 'Exness-MT5Trial16 USTEC, NOT FTMO data or symbol specification'
    summary['configured_tester_leverage'] = '1:30; symbol-specific Exness margin rules still apply'
    summary['maximum_notional_usd'] = max(t['volume']*t['entry_price'] for t in trades)
    summary['max_simple_margin_fraction_at_1_to_15'] = max(t['volume']*t['entry_price']/15/t['balance_before'] for t in trades)
    summary['margin_sensitivity_note'] = 'Simple notional/15 sensitivity only; not a verified FTMO symbol margin calculation.'
    summary['net_trade_profit_factor'] = sum(max(0,t['net_profit']) for t in trades)/sum(max(0,-t['net_profit']) for t in trades)
    summary['source_set_sha256'] = hashlib.sha256((TESTER/'MQL5'/'Profiles'/'Tester'/'calyx-nasdaq075-recent-20260919.set').read_bytes()).hexdigest()
    summary['expert_sha256'] = hashlib.sha256((TESTER/'MQL5'/'Experts'/'AAA Research'/'Active Portfolio Reaudit 20260907'/'Nasdaq Momentum Audit'/'Nasdaq 5M Candle Momentum Audit EA.ex5').read_bytes()).hexdigest()
    summary['report_sha256'] = hashlib.sha256(report.read_bytes()).hexdigest()
    summary.pop('series', None)
    month_groups = defaultdict(list)
    for trade in trades:
        month_groups[trade['exit_day_prague'][:7]].append(trade)
    months = []
    for month, items in month_groups.items():
        net = round(sum(t['net_profit'] for t in items),2)
        months.append(dict(month=month, trades=len(items), wins=sum(t['net_profit']>0 for t in items),
                           losses=sum(t['net_profit']<0 for t in items), net_profit=net,
                           starting_balance=items[0]['balance_before'], ending_balance=items[-1]['balance_after'],
                           return_pct=100*net/items[0]['balance_before'],
                           commission=round(sum(t['commission'] for t in items),2),
                           swap=round(sum(t['swap'] for t in items),2)))
    # Phase 2 cannot start until phase 1 reaches target on a flat account and four entry days.
    assert summary['maximum_balance'] < 11000
    rules = dict(initial_balance=10000, challenge_target=11000, verification_target=10500,
                 daily_loss_amount=500, static_equity_floor=9000, minimum_trading_days_each_phase=4,
                 day_timezone='Europe/Prague', source='https://ftmo.com/en/trading-objectives/',
                 checked_on='2026-09-19', first_phase_passed=False, verification_started=False,
                 status='CHALLENGE STILL OPEN / TARGET NOT REACHED',
                 total_loss_breach_in_native_test=summary['minimum_equity_native']<9000,
                 daily_floating_equity_audit='pending tick-path replay',
                 worst_closed_day=min(t['net_profit'] for t in trades),
                 minimum_days_satisfied=True,
                 note='No two-month deadline under FTMO rules; not passing within this window is not automatically a rule failure.')
    return summary, trades, months, rules


def main():
    global CASE
    args_parser = argparse.ArgumentParser()
    args_parser.add_argument('--case',default=CASE)
    args_parser.add_argument('--finalize-audit',action='store_true')
    args = args_parser.parse_args()
    CASE = args.case
    summary, trades, months, rules = load_report()
    if args.finalize_audit:
        with (ROOT/'equity-audit-days.csv').open(encoding='ascii') as handle:
            days=list(csv.DictReader(handle,delimiter=';'))
        assert abs(float(days[-1]['day_end_balance'])-summary['final_balance']) < 0.02
        assert sum(int(d['daily_breach']) for d in days)==0
        assert sum(int(d['total_breach']) for d in days)==0
        rules['daily_floating_equity_audit']='Independent tester tick-path replay of saved fills, timestamps rounded to report seconds'
        rules['daily_loss_breach_in_replay']=False
        rules['maximum_daily_equity_loss_usd']=max(float(d['daily_loss_usd']) for d in days)
        rules['minimum_equity_replay']=min(float(d['minimum_equity']) for d in days)
        rules['tick_replay_vs_native_minimum_equity_difference']=round(rules['minimum_equity_replay']-summary['minimum_equity_native'],2)
        rules['tick_replay_caveat']='Native report is authoritative for whole-run equity DD. Saved fills have only second precision, so the independent replay can differ slightly within execution seconds.'
        rules['status']='NOT PASSED; NO MODELED LOSS-LIMIT BREACH; STILL IN PHASE 1'
    for name, obj in [('summary.json',summary),('trades.json',trades),('months.json',months),('ftmo-rule-audit.json',rules)]:
        (ROOT/name).write_text(json.dumps(obj, indent=2, allow_nan=False),encoding='utf-8')
    # Input to an independent no-trading MT5 equity replay; only synthetic tester trades.
    with (ROOT/'equity-audit-input.csv').open('w',newline='',encoding='ascii') as handle:
        writer=csv.writer(handle, delimiter=';', lineterminator='\n')
        for t in trades:
            writer.writerow([t['entry_epoch'],t['exit_epoch'],1 if t['side']=='buy' else -1,
                             t['volume'],t['entry_price'],t['entry_commission']+t['entry_swap']+t['entry_gross'],
                             t['exit_commission']+t['exit_swap']+t['gross_profit']-t['entry_gross']])
    print(json.dumps(dict(summary=summary,months=months,ftmo=rules),indent=2))


if __name__=='__main__':
    main()
