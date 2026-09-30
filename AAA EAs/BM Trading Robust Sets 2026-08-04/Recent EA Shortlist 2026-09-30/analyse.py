"""Read-only evidence verification and local report generation."""
import json,gzip,hashlib,importlib.util,html
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('stats',ROOT.parent/'No Wick Multi Asset Raw 2026-09-30/analyse.py')
stats=importlib.util.module_from_spec(spec);spec.loader.exec_module(stats)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def collect():
    selections=json.loads((ROOT/'selection.json').read_text());rows=[]
    for s in selections:
        windows={}
        for period in ('3m','6m'):
            folder=ROOT/'native'/f"nw-{s['symbol']}-{s['slug']}-{period}"
            if not (folder/'run.json').exists():continue
            m=json.loads((folder/'run.json').read_text())
            if not m.get('audited'):continue
            assert sha(ROOT/'snapshot'/s['slug']/'selected.ex5')==s['ex5_sha256']==m['ex5_sha256']
            assert sha(folder/'trades.json.gz')==m['trades_sha256']
            raw=gzip.decompress(next(folder.glob('*.htm.gz')).read_bytes())
            assert hashlib.sha256(raw).hexdigest()==m['report_sha256']
            setting=next(folder.glob('*.set')).read_text(encoding='utf-8')
            assert hashlib.sha256(setting.encode()).hexdigest()==m['set_sha256']
            trades=json.loads(gzip.decompress((folder/'trades.json.gz').read_bytes()))
            n=stats.trade_statistics(trades,m['start'],m['end_exclusive'],s['symbol'])
            assert n['trades']==m['metrics']['trades']
            assert abs(n['net_profit']-m['metrics']['net_profit'])<max(.05,len(trades)*.011)
            windows[period]={'net':n,'native':m['metrics'],'flags':m['journal_flags'],'tick_notes':m['tick_notes']}
        fail=[]
        for period,minimum in [('3m',10),('6m',20)]:
            if period not in windows:fail.append(period+' missing');continue
            n=windows[period]['net']
            if n['net_profit']<=0:fail.append(period+' nonpositive profit')
            if n['net_profit_factor'] is None or n['net_profit_factor']<1.2:fail.append(period+' PF below 1.20')
            if n['trades']<minimum:fail.append(period+' insufficient sample')
        rows.append({'slug':s['slug'],'label':s['label'],'mode':s['mode'],'symbol':s['symbol'],'timeframe':s['period'],
          'windows':windows,'screen_pass':not fail,'screen_failures':fail,
          'warning':'WATCH ONLY: selected trio failed prior 2019–2021 holdout; recent screen is not rehabilitation.' if s['slug']=='3-way-gold' else '',
          'current_ex5_unchanged':sha(Path(s['expert']))==s['ex5_sha256'],
          'current_set_unchanged':sha(Path(s['set']))==s['set_sha256']})
    return sorted(rows,key=lambda r:r['windows'].get('6m',{}).get('net',{}).get('net_win_rate_pct',-1),reverse=True)
def report(rows):
    completed=sum(len(r['windows']) for r in rows)
    lines=['# Recent EA comparison — 30 September 2026',
      f'{completed}/24 fresh native tests verified. Twelve shortlisted current presets; not an exhaustive rerun of all 35 EAs.',
      'Six months: 30 March–29 September 2026. Three months: 30 June–29 September 2026. End date is exclusive; September 30 is incomplete.',
      '$10,000 separate starting balance per test, Exness-MT5Trial16, real-tick model, 150 ms delay, original selected 1% sizing. Three-Way Gold can risk 1% per module; risk stacks. Lot rounding, overnight exits and overlapping positions mean returns are not equal-risk portfolio forecasts. Existing settings unchanged; no optimization.',
      'Win rate and profit factor below are recomputed per closing deal, reconciled to MT5 trade counts, including reported commission/swap. Partial exits can count separately and are not independent setups (particularly 3-Way Gold). Same-side entry fees are allocated by matched volume; FIFO fragments are recombined by exit ticket, not counted as extra trades. Drawdown is native maximum relative EQUITY drawdown, including open P&L. No additional hypothetical broker commission was inserted.',
      '## Recent screen',
      'Positive return, net PF ≥1.20 in both overlapping windows, at least 20 six-month and 10 three-month trades. A pass is only a recent screen, not independent validation. Ranking is six-month net win rate, not expected future profit.',
      '| EA | 6m win | 6m PF | 6m return | 6m equity DD | 6m trades | 3m win | 3m PF | 3m return | 3m trades | Max win/loss streak 6m | Screen |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    table=[]
    for r in rows:
        if len(r['windows'])!=2:continue
        a=r['windows']['6m'];b=r['windows']['3m'];x=a['net'];y=b['net']
        vals=[r['label'],f"{x['net_win_rate_pct']:.1f}%",f"{x['net_profit_factor']:.2f}" if x['net_profit_factor'] else 'N/A',
          f"{a['native']['return_pct']:+.2f}%",f"{a['native']['relative_equity_dd_pct']:.2f}%",str(x['trades']),
          f"{y['net_win_rate_pct']:.1f}%",f"{y['net_profit_factor']:.2f}" if y['net_profit_factor'] else 'N/A',
          f"{b['native']['return_pct']:+.2f}%",str(y['trades']),f"{x['longest_win_streak']}/{x['longest_loss_streak']}",
          ('PASS'+(' — WATCH ONLY' if r['warning'] else '')) if r['screen_pass'] else '; '.join(r['screen_failures'])]
        lines.append('| '+' | '.join(vals)+' |');table.append(vals)
    lines+=['## Material caveats',
      '- 3-Way Gold failed an earlier 2019–2021 holdout. Its latest strong figures do not make it a validated production recommendation.',
      '- Gold Overnight has weak longer-term expectancy; judge the latest three-month deterioration, not just its winning percentage. Its six-month test includes one rejected entry on April 13 (invalid stops); do not confuse duplicated journal/summary matches with separate rejected orders.',
      '- News Pulse is excluded from this fresh ranking: checked-in verified calendar covers only 12 June–11 September 2026. Older cached results and fitted event settings are not fresh, independent evidence through today.',
      '- Twelve shortlisted presets were selected from existing evidence. Selection bias remains. The windows overlap; neither is a newly reserved holdout. Do not add their returns together or promise these win rates.',
      '- All results are simulated, not the recipient’s broker or live trading. Spread, slippage, fees and symbol contracts can change results.',
      '## Monthly licensing plan (not implemented)',
      'The store already has single-EA BAT/ZIP generation, per-product keys, account/server binding, expiry and revoke/extend controls. A five-EA customer bundle can reuse these components, but a customer installer is not an administrator licence builder.',
      '1. Owner selects the five authorised EA versions and recipient account/server. Generate separate licensed EX5 files, matching SETs and one portfolio installer. Do not ship source code, original unlicensed EX5s or signing secrets.',
      '2. Set a true 30-day runtime expiry, not merely the existing 12-month update entitlement. Only an owner action extends expiry; routine licence checks do not renew it.',
      '3. Enforce entitlement inside each EA, not in the BAT. Use HTTPS and a signed expiration/account/product entitlement; cap any offline grace at the entitlement expiry.',
      '4. On expiry, prevent new entries and cancel that EA’s own pending entry orders, but continue protective management of existing positions until flat. Do not interfere with unrelated/manual trades.',
      '5. Test expiry, renewal, offline/restart behaviour, wrong account/server, altered settings and all original strategy exits on demo before distribution; then verify licensed/unlicensed backtest parity.',
      'IMPORTANT: current code checks about every 24 hours, allows 72 hours offline after last success and uses ExpertRemove on denial. That can stop trailing/time exits and is unsuitable for the proposed precise, safe monthly expiry without changes. Server expiry support alone is not sufficient.',
      'MQL5 WebRequest requires an allowed URL and does not execute in Strategy Tester: https://www.mql5.com/en/docs/network/webrequest . ExpertRemove stops the EA: https://www.mql5.com/en/docs/common/expertremove . Licence lifecycle therefore needs demo tests as well as backtests.',
      'No licence was issued, no package distributed, no live terminal changed and no website evidence overwritten in this study.']
    rendered=[]
    for i,line in enumerate(lines):
        if rendered and (line.startswith('## ') or (line.startswith(('- ','1. ')) and not lines[i-1].startswith(('- ','1. ')))):rendered.append('')
        rendered.append(line)
        if line.startswith(('# ','## ')) or i in (1,2,3,4,6):rendered.append('')
    (ROOT/'REPORT.md').write_text('\n'.join(rendered),encoding='utf-8')
    header=['EA','6m win','6m PF','6m return','6m equity DD','6m trades','3m win','3m PF','3m return','3m trades','6m W/L streak','Screen']
    body='<table><thead><tr>'+''.join('<th>'+v+'</th>' for v in header)+'</tr></thead><tbody>'
    body+=''.join('<tr>'+''.join('<td>'+html.escape(v)+'</td>' for v in vals)+'</tr>' for vals in table)+'</tbody></table>'
    tail=lines[7+len(table)+1:]
    out='<!doctype html><meta charset="utf-8"><title>Recent EA comparison</title><style>body{font:15px system-ui;background:#101a24;color:#e1ebef;margin:35px}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:11px;border-bottom:1px solid #345;text-align:right}td:first-child,th:first-child{text-align:left}th{color:#7fe3cc}p{line-height:1.55;max-width:1200px}</style>'
    out+='<h1>Recent EA comparison — 30 September 2026</h1>'+''.join('<p>'+html.escape(t)+'</p>' for t in lines[1:7])+body
    out+=''.join('<h2>'+html.escape(t[3:])+'</h2>' if t.startswith('## ') else '<p>'+html.escape(t)+'</p>' for t in tail if not t.startswith('|'))
    (ROOT/'REPORT.html').write_text(out,encoding='utf-8')
    result={'completed_runs':completed,'planned_runs':24,'rows':rows}
    (ROOT/'ANALYSIS.json').write_text(json.dumps(result,indent=2))
    verified={'completed_runs':completed,'expected_runs':24,'complete':completed==24,
      'unchanged_selected_binaries_and_sets':all(r['current_ex5_unchanged'] and r['current_set_unchanged'] for r in rows),
      'report_ledger_snapshot_and_setting_hashes_verified':True,
      'all_report_history_quality':sorted({w['native']['history_quality'] for r in rows for w in r['windows'].values()}),
      'fatal_initialization_or_history_flags':[(r['slug'],p,w['flags']) for r in rows for p,w in r['windows'].items() if any(w['flags'][k] for k in ('init_failed','critical','no_history'))],
      'passing_recent_screen':[r['slug'] for r in rows if r['screen_pass']],
      'entry_cost_matching':'volume-matched FIFO, recombined by unique exit deal ticket; partial exits count separately',
      'scope':'Twelve shortlisted current presets, not all 35 EAs; no optimization or live deployment',
      'rules_sha256':sha(ROOT/'RULES.md'),'selection_sha256':sha(ROOT/'selection.json')}
    (ROOT/'VERIFICATION.json').write_text(json.dumps(verified,indent=2))
    print(f'Verified {completed}/24 runs')
    for r in rows:
        if len(r['windows'])==2:
            print(r['label'],[(p,round(r['windows'][p]['net']['net_win_rate_pct'],2),round(r['windows'][p]['net']['net_profit_factor'] or 0,3),r['windows'][p]['native']['return_pct'],r['windows'][p]['net']['trades']) for p in ('6m','3m')],r['screen_failures'])
if __name__=='__main__':report(collect())
