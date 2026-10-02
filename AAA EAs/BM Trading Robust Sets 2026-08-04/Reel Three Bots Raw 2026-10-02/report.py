from pathlib import Path
from datetime import datetime,timedelta,timezone
import base64,hashlib,html,json,re
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['text.parse_math']=False

ROOT=Path(__file__).resolve().parent
LABELS={'range':'German index range - Exness DE30 proxy','atr':'Gold H1 ATR candle breakout','donchian':'Gold Donchian H1 / M1 breakout'}
COLORS={'range':'#ffd166','atr':'#69f5c0','donchian':'#8ab4ff'}

def sunday(year,month):
    t=datetime(year,month+1,1,tzinfo=timezone.utc)-timedelta(days=1)
    return t-timedelta(days=(t.weekday()+1)%7)

def reference(t):
    utc=datetime.fromtimestamp(int(t),timezone.utc)
    a=sunday(utc.year,3).replace(hour=1);b=sunday(utc.year,10).replace(hour=1)
    return utc+timedelta(hours=3 if a<=utc<b else 2)

def audit(run,d):
    for name,h in run['source_hashes'].items():
        assert hashlib.sha256((ROOT/'EA'/name).read_bytes()).hexdigest()==h
    assert len(d)==run['metrics']['trades']
    assert abs(d.net_profit.sum()-run['metrics']['net_profit'])<.03
    assert ((d.volume-d.closed_volume).abs()<1e-7).all()
    ordered=d.sort_values('open_epoch')
    assert (ordered.open_epoch.to_numpy()[1:]>=ordered.close_epoch.to_numpy()[:-1]).all(),'Overlapping positions'
    if run['name']=='range' and len(d):
        opens=d.open_epoch.map(reference)
        assert max(opens.map(lambda x:x.date()).value_counts())==1,'More than one trade/day'
        assert opens.map(lambda x:11<=x.hour<18).all()
        assert d.close_epoch.map(reference).map(lambda x:x.hour<=18).all()
    journal=(ROOT/'native'/(run['name']+'-'+('1y' if run['start']=='2025.10.01' else '6m'))/'journal.txt.gz')
    import gzip
    text=gzip.open(journal,'rt',encoding='utf-8').read()
    errors=sorted(set(re.findall(r'RR_ENTRY_FAIL\s+(\d+)',text)))
    assert all(x=='10018' for x in errors),'Unexpected entry rejection'
    return {'source_hash_verified':True,'ledger_matches_native_report':True,'no_overlapping_positions':True,'entry_rejection_codes':errors,'entry_rejection_meaning':'10018: market closed; signal not chased after reopen' if errors else 'None'}

def make_plot(window,runs):
    plt.rcParams.update({'figure.facecolor':'#081512','axes.facecolor':'#0d211b','text.color':'#e9fff6','axes.labelcolor':'#bbd3c8','xtick.color':'#bbd3c8','ytick.color':'#bbd3c8','axes.edgecolor':'#28453a','font.size':10})
    fig,axes=plt.subplots(2,1,figsize=(12,7),sharex=True,gridspec_kw={'height_ratios':[2,1]})
    for name,run,d in runs:
        ix=pd.to_datetime(d.close_epoch,unit='s')
        start=pd.Timestamp(run['start'].replace('.','-'))
        dates=pd.DatetimeIndex([start,*ix.tolist()])
        balance=pd.Series([10000,*((10000+d.net_profit.cumsum()).tolist())],index=dates)
        axes[0].step(dates,balance,where='post',color=COLORS[name],label=LABELS[name],linewidth=1.5)
        dd=(balance/balance.cummax()-1)*100
        axes[1].step(dates,dd,where='post',color=COLORS[name],linewidth=1.2)
    axes[0].axhline(10000,color='#78978a',linewidth=.7,linestyle='--')
    axes[0].set_ylabel('Individual closed balance (USD)');axes[1].set_ylabel('Closed-balance DD (%)')
    axes[0].legend(facecolor='#0d211b',edgecolor='#28453a',labelcolor='#e9fff6',fontsize=9)
    for ax in axes:ax.grid(alpha=.15)
    axes[0].set_title('Separate $10,000 accounts - not a combined portfolio',loc='left',pad=12)
    fig.autofmt_xdate();fig.tight_layout();path=ROOT/(window+'-comparison.png');fig.savefig(path,dpi=145);plt.close(fig)
    return base64.b64encode(path.read_bytes()).decode()

def closed_curve(run,d):
    events=d.groupby('close_epoch').net_profit.sum().sort_index()
    start=pd.Timestamp(run['start'].replace('.','-'))
    end=pd.Timestamp(run['end_exclusive'].replace('.','-'))
    dates=pd.DatetimeIndex([start,*pd.to_datetime(events.index,unit='s').tolist(),end])
    values=[10000,*((10000+events.cumsum()).tolist()),10000+events.sum()]
    return dates,values

def make_dashboard(window,runs):
    combined=pd.concat([d for _,_,d in runs],ignore_index=True)
    dates,total=closed_curve(runs[0][1],combined)
    curves=[closed_curve(run,d) for _,run,d in runs]
    allvalues=[v for _,values in curves for v in values]+total
    padding=max(100,(max(allvalues)-min(allvalues))*.14)
    limits=(min(allvalues)-padding,max(allvalues)+padding)
    fig,axes=plt.subplots(2,2,figsize=(16,9),sharex=True,sharey=True)
    def configure(ax):
        ax.axhline(10000,color='#78978a',linewidth=.8,linestyle='--')
        ax.grid(alpha=.15);ax.set_ylim(*limits)
        ax.set_xlim(dates[0],dates[-1]);ax.set_ylabel('Closed balance (USD)')
        ax.tick_params(axis='x',rotation=20,labelbottom=True)
    for ax,(name,run,d),(ix,values) in zip(axes.flat,runs,curves):
        m=run['metrics']
        ax.step(ix,values,where='post',color=COLORS[name],linewidth=2)
        ax.set_title(LABELS[name],loc='left',fontsize=13,pad=12)
        ax.text(.02,.96,f"Return {m['return_pct']:+.2f}%  |  PF {m['profit_factor']:.2f}  |  WR {m['win_rate_pct']:.1f}%\n{m['trades']} trades  |  Native equity DD {m['equity_dd_relative_pct']:.2f}%",transform=ax.transAxes,va='top',fontsize=10,bbox={'facecolor':'#0d211b','edgecolor':'none','alpha':.9})
        configure(ax)
        solo,sax=plt.subplots(figsize=(10,5))
        sax.step(ix,values,where='post',color=COLORS[name],linewidth=2)
        sax.axhline(10000,color='#78978a',linewidth=.8,linestyle='--');sax.grid(alpha=.15)
        sax.set_title(LABELS[name]+f" | {window} | {m['return_pct']:+.2f}%",loc='left',pad=14)
        sax.set_ylabel('Closed balance (USD)');sax.set_xlim(dates[0],dates[-1])
        solo.autofmt_xdate();solo.tight_layout();solo.savefig(ROOT/(window+'-'+name+'.png'),dpi=145);plt.close(solo)
    ax=axes.flat[3]
    for (name,_,_),(ix,values) in zip(runs,curves):
        ax.step(ix,values,where='post',color=COLORS[name],linewidth=1,alpha=.6,label=name+' alone')
    ax.step(dates,total,where='post',color='#ffffff',linewidth=2.2,label='All three: summed closed P/L')
    returned=(total[-1]/10000-1)*100
    ax.set_title(f'All three together: closed-trade overlay ({returned:+.2f}%)',loc='left',fontsize=13,pad=12)
    configure(ax);ax.legend(loc='best',facecolor='#0d211b',edgecolor='#28453a',labelcolor='#e9fff6',fontsize=9)
    window_label='1 Apr - 1 Oct 2026 | 100% real-tick individual tests' if window=='6m' else '1 Oct 2025 - 1 Oct 2026 | Older history includes generated ticks'
    fig.suptitle('Three raw bots: individual results and all together\n'+window_label,fontsize=17,y=.99)
    fig.tight_layout(rect=[0,.045,1,.93])
    fig.text(.02,.018,'$10,000 reference; $100 planned risk per trade. Combined = independent closed P/L added together; NOT a shared-account portfolio backtest.\nCharts exclude open P/L. Native equity drawdown shown in individual panels includes floating losses.',fontsize=10,color='#bbd3c8')
    path=ROOT/(window+'-individual-and-combined.png');fig.savefig(path,dpi=145);plt.close(fig)
    return base64.b64encode(path.read_bytes()).decode()

def main():
    allruns=[];sections=[]
    for window,title in [('6m','Fresh six-month test: 1 Apr 2026 - 1 Oct 2026'),('1y','Initial annual test: 1 Oct 2025 - 1 Oct 2026')]:
        runs=[];rows=[]
        for name in LABELS:
            out=ROOT/'native'/(name+'-'+window);run=json.loads((out/'run.json').read_text());d=pd.read_csv(out/'trades.csv');checks=audit(run,d)
            run['verification']=checks;allruns.append(run);runs.append((name,run,d));m=run['metrics']
            rows.append(f"<tr><td>{LABELS[name]}</td><td>{m['return_pct']:+.2f}%</td><td>{m['profit_factor']:.2f}</td><td>{m['win_rate_pct']:.2f}%</td><td>{m['equity_dd_relative_pct']:.2f}%</td><td>{m['trades']}</td><td>{m['max_win_streak']} / {m['max_loss_streak']}</td><td>{html.escape(m['history_quality'])}</td></tr>")
        plot=make_plot(window,runs)
        dashboard=make_dashboard(window,runs)
        sections.append(f'<section><h2>{title}: each bot and all together</h2><img alt="Three individual closed-balance charts alongside an all-three closing-trade overlay" src="data:image/png;base64,{dashboard}"><p>White line: $10,000 plus summed net closed-trade profit/loss from the three independent tests. It does not simulate shared margin, joint risk limits or combined floating equity.</p></section>')
        sections.append(f'<section><h2>{title}</h2><div class="scroll"><table><thead><tr><th>Bot</th><th>Return</th><th>PF</th><th>Win rate</th><th>Max equity DD</th><th>Positions</th><th>Win / loss streak</th><th>Tester tick quality</th></tr></thead><tbody>'+''.join(rows)+f'</tbody></table></div><img alt="Separate closing balance and closed balance drawdown charts" src="data:image/png;base64,{plot}"><p>Chart drawdown excludes floating losses. The table uses native MT5 equity drawdown, including open-position P/L.</p></section>')
    notes=[]
    for run in allruns:
        notes.append(f"<details><summary>{LABELS[run['name']]} - {run['start']} to {run['end_exclusive']} (exclusive)</summary><pre>{html.escape(json.dumps({'metrics':run['metrics'],'inputs':run['inputs'],'summary':run['summary'],'tick_notes':run['tick_notes'],'verification':run['verification']},indent=2))}</pre></details>")
    rules=html.escape((ROOT/'RULES.txt').read_text())
    verdict='<section><h2>Initial verdict</h2><p>All three recent six-month tests lost money and had profit factor below 1.00. None is ready for live use on this evidence. Donchian was closest to break-even and had the highest win rate / lowest equity drawdown, but only 21 recent positions. The ATR strategy had the strongest annual return and profit factor, with a very low win rate and long losing streaks; its recent result did not sustain that edge. The range idea used DE30, not a verified DE40 feed.</p><p>These are raw, pre-optimisation baselines. Any changes should be tested separately, with an untouched validation window, rather than replacing these results.</p></section>'
    doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Three reel bots - Initial research</title><style>body{margin:0;background:#081512;color:#e9fff6;font:16px/1.65 system-ui,sans-serif}main{max-width:1250px;margin:auto;padding:40px 24px}h1{font-size:clamp(30px,5vw,56px);line-height:1.15}h2{font-size:25px}small,p{color:#bbd3c8}.tag{color:#69f5c0;font-size:13px;letter-spacing:2px}.warn{border:1px solid #77642d;background:#272715;padding:18px;border-radius:12px}section,details{margin:24px 0;border:1px solid #28453a;border-radius:14px;padding:20px;background:#0d211b}table{border-collapse:collapse;width:100%;font-size:14px;white-space:nowrap}th,td{padding:12px;text-align:left;border-bottom:1px solid #28453a}th{color:#69f5c0}.scroll{overflow:auto}img{width:100%;height:auto;margin-top:18px}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.65 ui-monospace,monospace}summary{cursor:pointer;color:#69f5c0}</style><main><div class="tag">CALYX RESEARCH / 2 OCTOBER 2026 / UNOPTIMISED</div><h1>Three ideas.<br>Initial native MT5 results.</h1><p>Individual $10,000 accounts; $100 fixed planned stop risk per trade; spread, native commissions/swaps and 150 ms execution delay. No live deployment and no portfolio aggregation.</p><div class="warn">Research only. Exness DE30 is an unverified proxy for the requested DE40. Annual runs contain generated older ticks; see the fresh six-month real-tick tests. Profit factor and win rate are historical results, not forecasts. Settings and assumptions are chosen from the screenshots, not optimised.</div>'''+''.join(sections)+'''<section><h2>Implementation and limitations</h2><p>All three compile with zero errors and warnings. Research EAs refuse live chart operation. Executed-position ledgers reconcile to each native MT5 report. Range cancellation/time checks and one-position limits are verified against the ledgers. ATR annual test had four market-closed entry rejections; these signals were skipped, not replayed after reopening.</p><pre>'''+rules+'</pre></section><h2>Native evidence and diagnostic notes</h2>'+''.join(notes)+'</main></html>'
    doc=doc.replace('<h2>Native evidence and diagnostic notes</h2>',verdict+'<h2>Native evidence and diagnostic notes</h2>')
    doc=doc.replace('No live deployment and no portfolio aggregation.','No live deployment. Combined charts are closing-trade overlays, not shared-account portfolio tests.')
    (ROOT/'Initial Results.html').write_text(doc,encoding='utf-8')
    (ROOT/'RESULTS.json').write_text(json.dumps(allruns,indent=2),encoding='utf-8')
    print('Verified six native runs; report:',ROOT/'Initial Results.html')

if __name__=='__main__':main()
