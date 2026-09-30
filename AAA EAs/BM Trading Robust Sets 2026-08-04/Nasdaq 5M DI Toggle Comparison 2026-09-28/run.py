"""Exact one-factor experiment using the existing isolated native runner.
Private research account configuration is read in memory; never printed or exported.
"""
from pathlib import Path
from datetime import datetime, timedelta
import gzip, hashlib, importlib.util, json, os, re, shutil

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
OLD = BASE / 'Nasdaq 5M QuantLab Style Research 2026-09-25'
SELECT = BASE / 'Nasdaq 5M DI ATR Deployment 2026-09-28/SELECTION.json'
selection = json.loads(SELECT.read_text())
spec = importlib.util.spec_from_file_location('original_nasdaq_runner', OLD / 'run_n5ql.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

def save(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')

def assert_free():
    assert not r.isolated_running(), 'Research tester occupied; no process stopped'
    assert not r.port_3000_busy(), 'Tester port 3000 occupied; no process stopped'

def ledger(folder):
    return json.loads(gzip.decompress((folder / 'trades.json.gz').read_bytes()))

def canonical(trades):
    keys = ('symbol','side','volume','open_time','close_time','open_price','close_price',
            'gross_profit','commission','swap','net_profit','entry_comment','exit_comment')
    return [{k:t.get(k) for k in keys} for t in trades]

def streaks(trades):
    runs = {1:[], -1:[]}; previous = 0; length = 0
    for t in trades:
        side = 1 if t['net_profit'] > 0 else -1 if t['net_profit'] < 0 else 0
        if side == previous and side != 0:
            length += 1
        else:
            if previous: runs[previous].append(length)
            previous, length = side, int(side != 0)
    if previous: runs[previous].append(length)
    return {name: {'max':max(runs[side], default=0),
                   'average':round(sum(runs[side])/len(runs[side]), 3) if runs[side] else 0}
            for name,side in [('win',1),('loss',-1)]}

def enrich(meta):
    folder = r.OUT / meta['case']
    trades = ledger(folder)
    assert len(trades) == meta['metrics']['trades'], 'Trade reconstruction count mismatch'
    assert abs(sum(t['net_profit'] for t in trades)-meta['metrics']['net_profit']) < .10, 'Net P&L reconciliation failed'
    report = r.REPORT_DIR / (meta['case']+'.htm')
    body = r._read_report(report)
    inputs = r._report_inputs(report)
    expected = r.variant_inputs(meta['variant'])
    assert all(k in inputs and r._same_setting(v,inputs[k]) for k,v in expected.items()), 'Missing/mismatched input'
    assert not any(meta['journal_flags'][k] for k in ('init_failed','no_history','critical')), 'Fatal journal condition'
    journal = gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
    assert 'testing with execution delay 150 milliseconds' in journal
    assert r.sha(BASE/selection['expert']) == selection['expert_sha']
    start = datetime.strptime(meta['start'], '%Y.%m.%d')
    end = datetime.strptime(meta['end_exclusive'], '%Y.%m.%d')
    weekdays = sum((start+timedelta(days=i)).weekday()<5 for i in range((end-start).days))
    months = {'6m':6,'1y':12,'3y':36,'5y':60}[meta['period']]
    # Relative is maximum percentage DD; Maximal is maximum cash DD and its corresponding percent.
    relative = r._metric(body, 'Equity Drawdown Relative')
    dd = float(re.search(r'([\d.,]+)\s*%', relative).group(1).replace(',',''))
    enhanced = dict(meta, actual_inputs=inputs, equity_relative_dd_pct=dd,
                    equity_relative_dd_raw=relative,
                    trade_frequency={'per_month':round(len(trades)/months,3),
                                     'per_weekday':round(len(trades)/weekdays,3),
                                     'per_five_weekdays':round(5*len(trades)/weekdays,3),
                                     'weekday_denominator':weekdays},
                    net_streaks=streaks(trades),
                    recorded_commission=round(sum(t['commission'] for t in trades),2),
                    recorded_swap=round(sum(t['swap'] for t in trades),2),
                    stop_modification_failures=len(re.findall('N5EMA stop modification failed',journal)),
                    lots_rounded_up_messages=len(re.findall('actual risk exceeds the selected target',journal)),
                    binary_sha256=selection['expert_sha'])
    if meta['variant'] == 'DI_ON':
        archived = OLD/'native'/('n5ql-USTEC-QL_ATR-'+meta['period'])
        old = json.loads((archived/'run.json').read_text())
        enhanced['archived_comparison'] = {
            'exact_trade_parity':canonical(trades)==canonical(ledger(archived)),
            'archived_metrics':old['metrics'],
            'net_profit_difference':round(meta['metrics']['net_profit']-old['metrics']['net_profit'],2)}
    save(folder/'verified.json', enhanced)
    return enhanced

def main():
    assert_free()
    assert r.sha(BASE/selection['expert']) == selection['expert_sha']
    assert r.sha(BASE/selection['settings']) == selection['settings_sha']
    inputs = dict(selection['inputs'])
    inputs['InpAdaptivePortfolioControls'] = 'false'
    r.ROOT = ROOT; r.OUT = ROOT/'native'; r.STATUS = r.OUT/'status.json'
    # The reused runner's INI report directory is fixed. Case names DI_ON/OFF
    # are new, so this shares its report directory without overwriting old cases.
    r.REPORT_DIR = r.TESTER/'reports/calyx-n5-quantlab'
    r.CONFIG.update(expert_dir='AAA Research\\Nasdaq DI Toggle 20260928',
                    expert_file='Nasdaq 5M DI Wide ATR EA.ex5',
                    variants={'DI_ON':{'inputs':{'InpRequireDIAgreement':'true'}},
                              'DI_OFF':{'inputs':{'InpRequireDIAgreement':'false'}}},
                    periods={'6m':'2026.03.25','1y':'2025.09.25','3y':'2023.09.25','5y':'2021.09.25'},
                    end_date='2026.09.25',model=4,execution_delay_ms=150,deposit=10000,
                    timeout_seconds=1800)
    r.base_set_values = lambda: inputs.copy()
    r.wait_for_port_3000 = assert_free
    on,off = r.variant_inputs('DI_ON'),r.variant_inputs('DI_OFF')
    assert [k for k in on if on[k]!=off[k]] == ['InpRequireDIAgreement']
    config = {'design':'one-factor DI toggle; no optimization', 'configurations_tried':2,
              'planned_runs':8,'symbol':'USTEC','timeframe':'M5','deposit':10000,
              'risk_percent':1,'model':4,'delay_ms':150,'currency':r.CONFIG['currency'],
              'leverage':r.CONFIG['leverage'],'periods':r.CONFIG['periods'],
              'end_exclusive':r.CONFIG['end_date'],'binary_sha256':selection['expert_sha'],
              'inputs':{'DI_ON':on,'DI_OFF':off},'live_terminal_changed':False}
    if (ROOT/'run-config.json').exists():
        assert json.loads((ROOT/'run-config.json').read_text())==config, 'Frozen configuration changed'
    else: save(ROOT/'run-config.json',config)
    dest = r.TESTER/'MQL5/Experts'/r.CONFIG['expert_dir']
    dest.mkdir(parents=True,exist_ok=True)
    shutil.copy2(BASE/selection['expert'],dest/r.CONFIG['expert_file'])
    assert r.sha(dest/r.CONFIG['expert_file']) == selection['expert_sha']
    rows=[]
    for period in r.CONFIG['periods']:
        for variant in r.CONFIG['variants']:
            rows.append(enrich(r.run_case('USTEC',variant,period)))
            save(ROOT/'RESULTS.json',rows)
    r.status(state='ALL DONE',event='All eight native DI-toggle cases verified; active settings untouched')

if __name__ == '__main__': main()
