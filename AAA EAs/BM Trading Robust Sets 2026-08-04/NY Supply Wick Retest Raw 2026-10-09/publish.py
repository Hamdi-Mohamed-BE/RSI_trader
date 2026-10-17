"""Publish six native raw cases, with frozen rules and honest data limitations."""
from pathlib import Path
from datetime import datetime, timezone
import csv, gzip, html, importlib.util, json, re
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('cash_history_helpers',ROOT.parent/'Forex Daily Zone M15 Reconstruction 2026-10-09/publish.py')
cash=importlib.util.module_from_spec(spec);spec.loader.exec_module(cash)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def f(value,d=2):return '—' if value is None else f'{value:,.{d}f}'
def text(t):return datetime.fromtimestamp(t,timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

def stats_table(rows,slice_label=None):
    header=['Asset','Trades','Win %','PF','Return %','Max equity DD %' if slice_label is None else 'Closed DD %','Win / loss streak','Sharpe' if slice_label is None else 'Cash P/L $']
    body=''
    for row in rows:
        m=row['metrics'] if slice_label is None else row['recent'][slice_label]
        body+='<tr><td>'+row['label']+'</td>'
        body+=''.join('<td>'+f(m.get(k),d)+'</td>' for k,d in [('trades',0),('win_rate',1),('pf',2),('return_pct',2),('equity_dd_pct' if slice_label is None else 'closed_dd_pct',2)])
        body+='<td>'+str(m['win_streak'])+' / '+str(m['loss_streak'])+'</td><td>'+f(m.get('sharpe_daily_equity' if slice_label is None else 'net_profit'))+'</td></tr>'
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+h+'</th>' for h in header)+'</tr></thead><tbody>'+body+'</tbody></table></div>'

def curves(rows):
    colors={'Gold':'#ffcb76','US100':'#83f0c9','Bitcoin':'#b6c7ff'}
    series=[]
    for row in rows:
        with (ROOT/'native'/row['tag']/'equity.csv').open(encoding='utf-8-sig') as stream:
            points={}
            for q in csv.DictReader(stream):points[int(q['epoch'])//86400]=float(q['equity'])
        series.append((row,[(d*86400,100*(v/10000-1)) for d,v in sorted(points.items())]))
    low=min(0,min(v for row,curve in series for t,v in curve))-1
    high=max(0,max(v for row,curve in series for t,v in curve))+1
    start=min(t for row,curve in series for t,v in curve);end=max(t for row,curve in series for t,v in curve)
    svg='<svg viewBox="0 0 1020 310" role="img" aria-label="Independent raw account equity curves">'
    for i in range(5):
        y=20+62.5*i;v=high-i*(high-low)/4
        svg+=f'<line x1="65" x2="990" y1="{y}" y2="{y}" stroke="#23473a"/><text x="5" y="{y+5}" fill="#a1bfb3" font-size="14">{v:.1f}%</text>'
    for row,curve in series:
        points=' '.join(f'{65+(t-start)/(end-start)*925:.1f},{20+(high-v)/(high-low)*250:.1f}' for t,v in curve)
        svg+=f'<polyline fill="none" stroke="{colors[row["label"]]}" stroke-width="2" points="{points}"/>'
    svg+='<text x="65" y="302" fill="#a1bfb3">9 Oct 2023</text><text x="893" y="302" fill="#a1bfb3">8 Oct 2026</text></svg>'
    return svg+'<p>Gold: amber · US100: mint · Bitcoin: lavender. Independent accounts, not a combined portfolio. Daily equity points from the native 5-minute mark-to-market audit.</p>'

def main():
    p=read(ROOT/'PLAN.json');s=read(ROOT/'RUN_STATUS.json')
    assert len(s['complete'])==6 and not s['failed'],s
    rows=[];verifications=[]
    for case in p['cases']:
        result=read(Path(s['complete'][case['slug']]['path']))
        folder=ROOT/'native'/result['tag']
        journal=gzip.decompress((folder/'journal.txt.gz').read_bytes()).decode()
        assert not any(result['flags'].values()),result['flags']
        assert result['inputs']['InpRiskPercent']=='0.5'
        assert result['known_target_at_entry_verified']
        assert abs(sum(t['net'] for t in result['trades'])-result['native']['net_profit'])<.031
        assert not result['tester_end_liquidations'],'Session time close did not flatten every position'
        gaps=sorted(set(re.findall(r'[^\r\n]*(?:real ticks absent|ticks discarded)[^\r\n]*',journal,re.I)))
        if case['window']=='2026':
            assert result['native']['history_quality']=='100% real ticks'
            assert not gaps,gaps
        with (folder/'signals.csv').open(encoding='utf-8-sig') as stream:signals=list(csv.DictReader(stream))
        risk_checks=[]
        balance=10000
        for signal,t in zip(signals,result['trades']):
            assert abs(float(signal['requested_risk_usd'])-balance*.005)<=.011
            assert t['side']=='Short'
            assert int(signal['signal_close_epoch'])<=t['open_epoch']
            assert int(signal['origin_epoch'])<int(signal['impulse_end_epoch'])<=int(signal['rejection_start_epoch'])
            assert float(signal['stop'])>max(float(signal['origin_high']),float(signal['rejection_high']))
            assert float(signal['target'])<float(signal['requested_entry'])<float(signal['stop'])
            rr=(float(signal['requested_entry'])-float(signal['target']))/(float(signal['stop'])-float(signal['requested_entry']))
            assert abs(rr-float(signal['reward_risk']))<1e-6
            risk_checks.append(rr);balance+=t['net']
        row=dict(label=case['label'],symbol=case['symbol'],window=case['window'],tag=result['tag'],
            metrics=result['metrics'],history_quality=result['native']['history_quality'],tick_notes=result['tick_notes'],
            gaps=gaps,diagnostics=result['diagnostics'],planned_r_median=float(np.median(risk_checks)) if risk_checks else None,
            planned_r_mean=float(np.mean(risk_checks)) if risk_checks else None,
            planned_r_min=min(risk_checks) if risk_checks else None,planned_r_max=max(risk_checks) if risk_checks else None,
            planned_r_ge3=sum(r>=3 for r in risk_checks),natural_trades=len(result['trades']))
        if case['window']=='3y':row.update(recent=cash.slices(result),annual=cash.annual(result))
        rows.append(row)
        verifications.append(dict(slug=case['slug'],active_inputs_verified=True,complete_cash_reconciliation=True,
            signal_to_native_trade_match=True,chronological_known_target_audit=True,dynamic_current_balance_budget=True,
            native_end_liquidations=0,history_quality=row['history_quality'],tick_gaps=gaps))
        fields=['position_id','side','volume','open_price','close_price','sl','tp','net','gross','commission','swap','fee']
        with (ROOT/(case['slug']+'-trades.csv')).open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.DictWriter(stream,['entry_utc','exit_utc',*fields,'planned_r','exit_reason']);writer.writeheader()
            for sig,t in zip(signals,result['trades']):
                reason='TP' if any(c.lower().startswith('tp ') for c in t['exit_comments']) else ('SL' if any(c.lower().startswith('sl ') for c in t['exit_comments']) else '16:00 ET time close')
                writer.writerow(dict(entry_utc=text(t['open_epoch']),exit_utc=text(t['close_epoch']),**{k:t[k] for k in fields},planned_r=sig['reward_risk'],exit_reason=reason))
    full=[r for r in rows if r['window']=='3y'];fresh=[r for r in rows if r['window']=='2026']
    recent=''
    for period in ['3 months','6 months','1 year']:
        begin=full[0]['recent'][period]['start']
        recent+='<h3>'+period+' · '+begin+' → 8 Oct 2026</h3>'+stats_table(full,period)
    rr_table='<div class="scroll"><table><tr><th>Asset</th><th>Median planned R</th><th>Mean planned R</th><th>Range</th><th>Trades targeting ≥3R</th></tr>'
    for row in full:
        rr_table+='<tr><td>'+row['label']+'</td><td>'+f(row['planned_r_median'])+'</td><td>'+f(row['planned_r_mean'])+'</td><td>'+f(row['planned_r_min'])+' – '+f(row['planned_r_max'])+'</td><td>'+str(row['planned_r_ge3'])+' / '+str(row['natural_trades'])+'</td></tr>'
    rr_table+='</table></div>'
    years='<div class="scroll"><table><tr><th>Asset</th><th>2023 partial %</th><th>2024 %</th><th>2025 %</th><th>2026 YTD %</th></tr>'
    for row in full:years+='<tr><td>'+row['label']+'</td>'+''.join('<td>'+f(y['return_pct'])+'</td>' for y in row['annual'])+'</tr>'
    years+='</table></div>'
    downloads='<ul>'+''.join('<li><a href="'+r['tag'].replace('allrr05-','').replace('-raw','')+'-trades.csv">'+r['label']+' · '+r['window']+' trade breakdown</a></li>' for r in rows)+'</ul>'
    # Filenames are case slugs rather than native helper tags; assert every link.
    for row in rows:
        filename='ny-supply-wick-'+row['symbol'].lower()+'-'+row['window']+'-trades.csv'
        assert (ROOT/filename).is_file()
    content='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>New York Supply Wick Retest · Raw</title><style>
    *{box-sizing:border-box}body{margin:0;background:#07130f;color:#eef9f3;font:16px/1.6 system-ui,sans-serif}main{max-width:1280px;margin:auto;padding:35px 25px}h1{font-size:35px;line-height:1.2}h2{margin-top:10px}h3{color:#89f5d0}p,li{color:#a6c5b7}.tag{color:#8bf5d3;font-size:13px;letter-spacing:2px}.warning{padding:20px;background:#242312;border:1px solid #85782f;border-radius:15px}.panel{padding:24px;margin:26px 0;border:1px solid #2a5341;border-radius:17px;background:#0c1e17}.scroll{overflow:auto}table{width:100%;white-space:nowrap;border-collapse:collapse;font-size:14px}th{text-align:left;color:#93f4d2;padding:12px;border-bottom:1px solid #426956}td{padding:12px;border-bottom:1px solid #244233}svg{display:block;width:100%;margin-top:24px}a{color:#93f8da}summary{color:#a0ffde;cursor:pointer}.small{font-size:13px}
    </style><main><div class="tag">CALYX · FROZEN RAW RECONSTRUCTION · NO LIVE CHANGES</div><h1>New York supply-zone wick retest</h1><p>Gold · US100 (Exness USTEC) · Bitcoin · M5 · short only. $10,000 independent accounts, 0.5% current-balance risk. Earliest opening bearish impulse → last up-candle supply → upper-wick rejection → sell the close.</p>'''
    content+='<div class="warning">The clip is one example, not a complete algorithm. Timeframe, impulse/wick thresholds, zone bounds, stop buffer and time exit are declared reconstruction assumptions. No claim to reproduce the exact September 10 trade.<br><br>The three-year native history is mixed: '+', '.join(r['label']+' '+r['history_quality'] for r in full)+'. Pre-2026 trading relies on generated ticks from historical bars. The fresh-start 2026 tests below use 100% real ticks.</div>'
    content+='<section class="panel"><h2>Three years · 9 Oct 2023 → 8 Oct 2026</h2><p>End exclusive: 9 Oct 2026. Frozen defaults; no optimization or selection using these outcomes.</p>'+stats_table(full)+curves(full)+'</section>'
    content+='<section class="panel"><h2>Fresh-start real-tick test · 1 Jan → 8 Oct 2026</h2><p>New $10,000 accounts, same settings. Native tester confirms 100% real ticks for each trading window, with no absent/discarded-tick warnings.</p>'+stats_table(fresh)+'</section>'
    content+='<section class="panel"><h2>The target is the known New York low—not fixed 3R</h2><p>The low is updated only from completed M5 candles since 09:30. It is frozen when the rejection closes. The eventual session low is never used as an entry-time target. These are requested reward/risk distances, not realized profits.</p>'+rr_table+'</section>'
    content+='<section class="panel"><h2>Recent slices of the three-year accounts</h2><p>These are historical closed-cash slices, not fresh-start re-tests. Return is relative to each account’s opening closed balance for that slice; a slice can inherit sizing from earlier results. PF and streaks use net whole-position outcomes. Slice DD is closed-balance only.</p>'+recent+'</section>'
    content+='<section class="panel"><h2>Calendar-year closed returns</h2><p>2023 begins on 9 October; 2026 ends on 8 October. These accounts differ from the fresh-start 2026 tests.</p>'+years+'</section>'
    content+='<details class="panel"><summary>Complete frozen rules and execution assumptions</summary><ul>'+''.join('<li><strong>'+html.escape(k.replace('_',' '))+':</strong> '+html.escape(v)+'</li>' for k,v in p['rules'].items())+'</ul><p>09:30–16:00 ET is the stock-market core session, used here as a clock anchor on all three CFD assets, not a claim that gold or Bitcoin exchanges open then. <a href="https://www.nyse.com/trade/trading-information">NYSE session reference</a> · <a href="https://www.nist.gov/pml/time-and-frequency-division/popular-links/daylight-saving-time-dst">NIST daylight-saving reference</a>.</p><p>Native broker lot increments, spreads, commission, swap and 150 ms execution delay are retained. Risk sizing is nominal stop risk; realized loss can exceed the budget through costs or slippage. Full-run max DD is native floating equity DD. Sharpe uses daily sampled equity, weekdays, √252, zero risk-free rate. No trailing or partial exits. The 16:00 ET exit is an added research assumption.</p></details>'
    content+='<details class="panel"><summary>Native audits and trade downloads</summary>'+downloads+'<ul>'+''.join('<li>'+r['label']+' '+r['window']+': '+html.escape(r['diagnostics'][0])+'</li>' for r in rows)+'</ul><p>Every native entry is matched to its recorded origin candle, impulse completion, rejection close, locked stop/target, lot size and account-risk budget. Cost-inclusive deal sums reconcile with all six native reports. No terminal-end liquidation is included; positions closed naturally or at the declared session exit.</p></details>'
    content+='<p class="small">Research only. Separate accounts are not a shared-portfolio simulation. No live trading, BATs, website or production EA settings changed. Sources, native reports, active inputs and signal ledgers are saved beside this report.</p></main></html>'
    (ROOT/'Results.html').write_text(content,encoding='utf-8')
    save(ROOT/'SUMMARY.json',dict(plan=p,rows=rows,completed=6,live_changes=False,optimization=False,combined_portfolio=False))
    save(ROOT/'VERIFICATION.json',dict(cases=verifications,native_reports_reconciled=6,
        signals_matched=True,no_terminal_end_liquidations=True,real_tick_fresh_tests=3,live_changes=False))
    print(json.dumps([dict(asset=r['label'],window=r['window'],metrics=r['metrics'],median_planned_r=r['planned_r_median']) for r in rows],indent=2))

if __name__=='__main__':main()
