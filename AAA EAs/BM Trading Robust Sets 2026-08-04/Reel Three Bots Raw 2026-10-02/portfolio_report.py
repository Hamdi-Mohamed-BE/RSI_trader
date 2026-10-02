"""Real shared-account MT5 charts, not sums of independent EA equity curves."""
from pathlib import Path
from datetime import datetime,timezone
import base64,gzip,hashlib,html,json,re
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from report import reference

ROOT=Path(__file__).resolve().parent
LABELS={1002001:'DE30 range breakout',1002002:'Gold ATR candle',1002003:'Gold Donchian'}
plt.rcParams.update({'figure.facecolor':'#081512','axes.facecolor':'#0d211b','text.color':'#e9fff6','axes.labelcolor':'#bbd3c8','xtick.color':'#bbd3c8','ytick.color':'#bbd3c8','axes.edgecolor':'#28453a','font.size':11,'text.parse_math':False})

def verify(out,run,d,e):
    for name,h in run['source_hashes'].items():
        assert hashlib.sha256((out/'sources'/name).read_bytes()).hexdigest()==h,'Frozen source hash mismatch'
    assert len(d)==run['metrics']['trades']
    assert abs(d.net_profit.sum()-run['metrics']['net_profit'])<.03
    assert ((d.volume-d.closed_volume).abs()<1e-7).all()
    assert run['inputs'].get('InpRangeSymbol')=='DE30' and run['inputs'].get('InpGoldSymbol')=='XAUUSD'
    assert float(run['inputs']['InpRiskPercent'])==1
    start=int(datetime.strptime(run['start'],'%Y.%m.%d').replace(tzinfo=timezone.utc).timestamp())
    assert (d.open_epoch>=start).all() and (e.epoch>=start).all()
    assert set(d.magic).issubset(LABELS)
    for magic,group in d.groupby('magic'):
        ordered=group.sort_values('open_epoch')
        assert (ordered.open_epoch.to_numpy()[1:]>=ordered.close_epoch.to_numpy()[:-1]).all(),'One-position module limit broken'
    rr=d[d.magic==1002001]
    assert rr.symbol.eq('DE30').all()
    assert max(rr.open_epoch.map(reference).map(lambda x:x.date()).value_counts())<=1
    assert rr.open_epoch.map(reference).map(lambda x:11<=x.hour<18).all()
    assert rr.close_epoch.map(reference).map(lambda x:x.hour<=18).all()
    text=gzip.open(out/'journal.txt.gz','rt',encoding='utf-8').read()
    rejects=re.findall(r'RR_ENTRY_FAIL\s+(\d+)',text)
    assert all(x=='10018' for x in rejects),'Unexpected market rejection'
    range_rejects=sorted(set(re.findall(r'(20\d{2}\.\d{2}\.\d{2}\s+[\d:]+)\s+RR_RANGE_ENTRY_FAIL buy=(\d+) sell=(\d+)',text)))
    assert all(b=='10015' and s=='10015' for _,b,s in range_rejects),'Unexpected range rejection'
    assert not re.search(r'not enough money|margin call|stop out|RR_CANCEL_FAIL|RR_CLOSE_FAIL|RR_MODIFY_FAIL',text,re.I),'Execution failure needs review'
    events=sorted([(int(row.open_epoch),1) for row in d.itertuples()]+[(int(row.close_epoch),-1) for row in d.itertuples()])
    active=maxactive=0
    for _,change in events:active+=change;maxactive=max(maxactive,active)
    assert active==0 and maxactive<=3 and maxactive>=2,'Portfolio overlap missing/invalid'
    return {'hashes_verified':True,'ledger_matches_native_report':True,'max_concurrent_positions':maxactive,'market_closed_entry_rejections':len(rejects)//2,'range_pending_price_rejections':range_rejects,'range_rejection_meaning':'10015: price invalid after execution delay; day skipped and any surviving opposite pending cancelled','minimum_sampled_free_margin_usd':float(e.free_margin.min()),'sampling_interval_seconds':300}

def graph(window,run,e):
    m=run['metrics'];end=pd.Timestamp(run['end_exclusive'].replace('.','-'));ix=pd.to_datetime(e.epoch,unit='s')
    frame=e[['balance','equity']].copy();frame.index=ix
    frame.loc[end]=[m['final_balance'],m['final_balance']]
    fig,axes=plt.subplots(2,1,figsize=(14,8),sharex=True,gridspec_kw={'height_ratios':[3,1]})
    axes[0].plot(frame.index,frame.equity,color='#69f5c0',linewidth=1,label='Shared floating equity (5-minute samples)')
    axes[0].step(frame.index,frame.balance,where='post',color='#ffffff',linewidth=1.4,label='Shared account balance')
    axes[0].axhline(10000,color='#78978a',linewidth=.8,linestyle='--');axes[0].set_ylabel('One shared account (USD)')
    axes[0].legend(loc='best',facecolor='#0d211b',edgecolor='#28453a',labelcolor='#e9fff6',fontsize=10)
    dd=(frame.equity/frame.equity.cummax()-1)*100
    axes[1].fill_between(frame.index,dd,0,color='#ff8080',alpha=.22)
    axes[1].plot(frame.index,dd,color='#ff8080',linewidth=1);axes[1].set_ylabel('Sampled equity DD (%)')
    for ax in axes:ax.grid(alpha=.15)
    quality='100% real ticks' if window=='6m' else 'Older history includes generated ticks'
    fig.suptitle('ACTUAL SHARED MT5 PORTFOLIO | DE30 + Gold ATR + Gold Donchian\n'+('1 Apr - 1 Oct 2026' if window=='6m' else '1 Oct 2025 - 1 Oct 2026'),fontsize=16,y=.98)
    axes[0].set_title(f"Return {m['return_pct']:+.2f}%  |  PF {m['profit_factor']:.2f}  |  Win rate {m['win_rate_pct']:.1f}%  |  Native max equity DD {m['equity_dd_relative_pct']:.2f}%  |  {m['trades']} trades",fontsize=11,loc='left',pad=12)
    fig.autofmt_xdate();fig.tight_layout(rect=[0,.09,1,.91])
    fig.text(.03,.032,f"$10,000 starting balance; 1% CURRENT SHARED BALANCE risk per bot per trade; up to three simultaneous positions. {quality}.\nSpread, commissions, swaps and 150ms delay included. Native DD measured by MT5; chart DD uses 5-minute samples. Not an FTMO-rule simulation.",fontsize=10,color='#bbd3c8')
    path=ROOT/('shared-portfolio-'+window+'.png');fig.savefig(path,dpi=145);plt.close(fig)
    return base64.b64encode(path.read_bytes()).decode()

def main():
    results=[];sections=[]
    for window in ['6m','1y']:
        out=ROOT/'native'/('portfolio-percent-'+window)
        if not (out/'run.json').exists():continue
        run=json.loads((out/'run.json').read_text());d=pd.read_csv(out/'trades.csv');e=pd.read_csv(out/'equity.csv')
        run['verification']=verify(out,run,d,e);results.append(run)
        rows=[]
        for magic,group in d.groupby('magic'):
            p=group.net_profit;loss=-p[p<0].sum();pf=p[p>0].sum()/loss if loss else float('inf')
            rows.append(f'<tr><td>{LABELS[magic]}</td><td>{len(group)}</td><td>${p.sum():+,.2f}</td><td>{pf:.2f}</td><td>{(p>0).mean()*100:.2f}%</td></tr>')
        m=run['metrics'];image=graph(window,run,e)
        sections.append(f'<section><h2>{"Six months" if window=="6m" else "One year"}: one shared account</h2><img alt="Actual shared MT5 balance, floating equity and drawdown" src="data:image/png;base64,{image}"><p>Final balance ${m["final_balance"]:,.2f}; maximum winning / losing streak {m["max_win_streak"]} / {m["max_loss_streak"]}; maximum {run["verification"]["max_concurrent_positions"]} simultaneous positions. Range pending-price rejections: {len(run["verification"]["range_pending_price_rejections"])} skipped days; market-closed entry rejections: {run["verification"]["market_closed_entry_rejections"]}.</p><table><thead><tr><th>Module</th><th>Trades</th><th>Net contribution</th><th>PF</th><th>Win rate</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table><details><summary>Native metrics, inputs and audit</summary><pre>'+html.escape(json.dumps(run,indent=2))+'</pre></details></section>')
    assert results,'No completed percentage-risk portfolio test'
    comparison=''
    fixed=ROOT/'native/portfolio-6m/run.json'
    if fixed.exists():
        m=json.loads(fixed.read_text())['metrics']
        comparison=f'<p>Earlier fixed-$100 shared-account comparison (six months): return {m["return_pct"]:+.2f}%, PF {m["profit_factor"]:.2f}, native equity DD {m["equity_dd_relative_pct"]:.2f}%. The main graphs above use dynamic 1% of shared balance.</p>'
    doc='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Shared Three-Bot Portfolio</title><style>body{background:#081512;color:#e9fff6;margin:0;font:16px/1.65 system-ui}main{max-width:1250px;margin:auto;padding:36px 24px}h1{font-size:42px;line-height:1.2}section{background:#0d211b;border:1px solid #28453a;border-radius:14px;margin:24px 0;padding:20px}img{width:100%;height:auto}p{color:#bbd3c8}table{width:100%;border-collapse:collapse}td,th{padding:12px;text-align:left;border-bottom:1px solid #28453a}th,summary{color:#69f5c0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:13px/1.6 monospace}.warning{padding:16px;border:1px solid #77642d;background:#272715;border-radius:12px}</style><main><h1>One account. Three bots.<br>Actual shared-account MT5 test.</h1><p>$10,000 USD hedging account, 1:2000 tester leverage. Each module risks 1% of the current shared balance at entry. Lots are rounded down; below-minimum sizes skip. No added daily loss/target controls. No live deployment.</p><div class="warning">DE30 is used as requested; not independently verified as a DE40 feed. This is a real multicurrency MT5 portfolio run, not added individual curves. Gold processes each chart tick; DE30 processes the latest available quote on chart events plus a one-second timer fallback. Risk is a planned stop amount; commissions, swaps, slippage and gaps can exceed it. Annual data contains generated older ticks.</div>'''+''.join(sections)+comparison+'</main></html>'
    (ROOT/'Shared Portfolio.html').write_text(doc,encoding='utf-8')
    (ROOT/'SHARED PORTFOLIO RESULTS.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    page=ROOT/'Initial Results.html'
    if page.exists():
        old=page.read_text(encoding='utf-8');marker='<section id="actual-shared-portfolio">'
        old=re.sub(r'<section id="actual-shared-portfolio">.*?</section>','',old,flags=re.S)
        shared=marker+'<h2>Actual shared-account test: 1% per bot</h2><p>The earlier white-line graphs below are ledger overlays. The requested native shared-account portfolio is here:</p>'+''.join(f'<img alt="Actual shared portfolio {r["start"]}" src="data:image/png;base64,{base64.b64encode((ROOT/("shared-portfolio-"+("6m" if r["start"]=="2026.04.01" else "1y")+".png")).read_bytes()).decode()}">' for r in results)+'<p>Includes overlapping positions and floating equity in one MT5 account. Detailed native audit: <a href="Shared%20Portfolio.html">Shared Portfolio report</a>.</p></section>'
        page.write_text(old.replace('<main>','<main>'+shared,1),encoding='utf-8')
    print('Verified native shared portfolio reports:',[(r['start'],r['metrics'],r['verification']) for r in results])

if __name__=='__main__':main()
