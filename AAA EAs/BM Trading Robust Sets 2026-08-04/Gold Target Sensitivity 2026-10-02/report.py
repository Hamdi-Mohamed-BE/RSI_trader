"""Complete target disclosure, static scientific plots and offline Calyx-styled report."""
from run import *
import html,math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'figure.facecolor':'#071511','axes.facecolor':'#0c1d17','axes.edgecolor':'#305047','text.color':'#eef9f1','axes.labelcolor':'#c6e5d7','xtick.color':'#c6e5d7','ytick.color':'#c6e5d7','grid.color':'#264039','font.size':10})
def curve(name,title,filename):
 p=OUT/name/'0-trace.csv.gz';assert p.exists();d=pd.read_csv(io.BytesIO(gzip.decompress(p.read_bytes())));t=pd.to_datetime(d.epoch,unit='s')
 fig,ax=plt.subplots(2,1,figsize=(12,6),sharex=True,gridspec_kw={'height_ratios':[3,1]})
 ax[0].plot(t,d.balance,color='#72ecc1',lw=1.2,label='Balance');ax[0].plot(t,d.equity,color='#ffcc77',lw=.6,alpha=.7,label='Equity · 5-minute samples');ax[0].set_title(title,loc='left',pad=12);ax[0].set_ylabel('USD');ax[0].legend(facecolor='#0c1d17',labelcolor='#eef9f1');ax[0].grid(alpha=.4)
 peak=np.maximum.accumulate(np.r_[10000,d.equity.to_numpy()])[1:];dd=(peak-d.equity)/peak*100;ax[1].fill_between(t,-dd,0,color='#f27e88',alpha=.7);ax[1].set_ylabel('Equity DD %');ax[1].grid(alpha=.4);fig.autofmt_xdate();fig.tight_layout();fig.savefig(ROOT/filename,dpi=140);plt.close(fig)
 return '<img src="'+filename+'" alt="'+html.escape(title)+'">'
def sensitivity(kind,rows):
 x=np.arange(len(rows));labels=[f"{r['parameters']['rr']:g}R"+(' †' if not r['clean'] else '') for r in rows];fig,ax=plt.subplots(3,1,figsize=(12,9),sharex=True)
 ax[0].bar(x-.17,[r['stats']['win_pct'] or 0 for r in rows],.34,color='#72ecc1',label='Net win rate');ax[0].bar(x+.17,[r['details']['full_tp_rate_pct'] or 0 for r in rows],.34,color='#ffcc77',label='Full TP rate');ax[0].set_ylabel('% of positions');ax[0].set_title(NAMES[kind]+' · last year · target sensitivity',loc='left',pad=12)
 ax[1].plot(x,[r['stats']['pf'] or 0 for r in rows],color='#72ecc1',marker='o',label='Profit factor');ax[1].plot(x,[r['stats']['sharpe'] or 0 for r in rows],color='#ffcc77',marker='s',label='Daily closed-P/L Sharpe');ax[1].axhline(1.2,color='#a0bdb0',ls=':',lw=.8,label='PF screen 1.20');ax[1].set_ylabel('Ratio')
 ax[2].bar(x-.17,[r['stats']['return_pct'] for r in rows],.34,color='#72ecc1',label='Return %');ax[2].bar(x+.17,[r['stats']['equity_dd_pct'] for r in rows],.34,color='#f27e88',label='Native max equity DD %');ax[2].set_ylabel('%');ax[2].set_xticks(x,labels);ax[2].set_xlabel('Target / initial stop distance')
 for a in ax:a.legend(facecolor='#0c1d17',labelcolor='#eef9f1',loc='upper left');a.grid(axis='y',alpha=.35)
 note='† Execution rejections: historical metrics retained, but not a clean research candidate. See the evidence table.' if any(not r['clean'] for r in rows) else 'All cases executed cleanly. Historical sensitivity only—not independent out-of-sample validation.'
 fig.text(.5,.01,note,ha='center',fontsize=9,color='#ffcc77')
 fig.tight_layout(rect=(0,.03,1,1));name=kind+'-sensitivity.png';fig.savefig(ROOT/name,dpi=140);plt.close(fig);return '<img src="'+name+'" alt="'+html.escape(NAMES[kind])+' target comparison">'
def table(rows):
 heads=['Target','Return','PF','Net win rate','Full TP rate','Equity DD','Daily Sharpe','Positions','Max win / loss run','Average win / loss run','Avg winner / loser R','Cash payoff','Positive SL exits','Initial-risk / budget mean / max','Test-end closes','Execution']
 h='<div class="scroll"><table><thead><tr>'+''.join('<th>'+x+'</th>' for x in heads)+'</tr></thead><tbody>'
 def f(v,n=2):return '—' if v is None else f'{v:.{n}f}'
 for r in rows:
  s,d=r['stats'],r['details'];v=[f"{r['parameters']['rr']:g}R",f"{s['return_pct']:+.2f}%",f(s['pf']),f(s['win_pct'])+'%',f(d['full_tp_rate_pct'])+'%',f(s['equity_dd_pct'])+'%',f(s['sharpe']),s['trades'],f"{s['max_win_streak']} / {s['max_loss_streak']}",f(s['avg_win_streak'])+' / '+f(s['avg_loss_streak']),f(d['avg_winning_R'])+' / '+f(d['avg_losing_R']),f(d['realized_cash_payoff']),d['positive_sl_count'],f(d['risk_ratio_mean'],3)+' / '+f(d['risk_ratio_max'],3),d['boundary'],'clean' if r['clean'] else 'REJECTED: execution failures']
  h+='<tr>'+''.join('<td>'+html.escape(str(z))+'</td>' for z in v)+'</tr>'
 return h+'</tbody></table></div>'
def main():
 result=load(ROOT/'RESULTS.json');picks=load(ROOT/'PICKS.json');trials=load(ROOT/'TRIALS.json');provenance=load(ROOT/'SOURCES.json');parts=[]
 assert set(result)==set('TS')
 for kind in 'TS':
  parity_result=load(ROOT/('PARITY-'+kind+'.json'));assert parity_result['exact']
  parts+=['<section><h2>'+NAMES[kind]+'</h2><p>Original target: '+str(BASELINES[kind])+'R. '+('Long-only EMA/pullback/confirmation model; five-bar structural stop. Break-even still activates at 1R with +0.05R lock.' if kind=='T' else 'Long/short 1-, 3-, 6-month momentum votes with EMA100-day bias; 1.5 × ATR stop. One position and 24-hour cooldown. No trailing/break-even management.')+'</p>']
  pick=picks[kind];parts+=['<div class="box"><p>Historical screen · highest net win rate: <strong>'+('none' if pick['highest_win_rate'] is None else str(pick['highest_win_rate'])+'R')+'</strong> · balanced Sharpe candidate: <strong>'+('none' if pick['balanced'] is None else str(pick['balanced'])+'R')+'</strong>.</p><p>Screened targets: '+(', '.join(str(x)+'R' for x in pick['screened_targets']) or 'none')+'. These are research candidates, not fresh out-of-sample winners or live recommendations.</p></div>']
  parts+=['<p>Highest observed one-year net win rate (descriptive only): '+str(pick.get('highest_observed_win_rate','see table'))+'R. This can fail the PF/stability screen even when its winning streak looks attractive.</p>',sensitivity(kind,result[kind]['1y'])]
  for per in WINDOWS:
   if per=='1y':parts+=['<h3>Last year · Oct 1, 2025–Oct 1, 2026</h3>',table(result[kind][per])]
   else:parts+=['<details><summary>'+per+' · every target and metric</summary>',table(result[kind][per]),'</details>']
  charts=load(ROOT/('CHARTS-'+kind+'.json'))
  for rr,name in charts.items():
   row=load(OUT/name/'results.json')[0]
   parts+=['<h3>'+rr+'R · native balance / floating equity</h3><p>Native worst-tick equity drawdown: '+f"{row['net']['equity_dd_pct']:.2f}%"+'. Chart drawdown uses five-minute samples and may understate the worst tick.</p>',curve(name,NAMES[kind]+' · '+rr+'R · last year',kind+'-'+rr+'R-curve.png')]
  parts+=['<details><summary>Baseline parity, frozen source/settings and selection evidence</summary><pre>'+html.escape(json.dumps(dict(parity=parity_result,provenance=provenance[kind],selection=pick),indent=2))+'</pre></details><details><summary>Complete native results, risk and execution counters</summary><pre>'+html.escape(json.dumps(result[kind],indent=2))+'</pre></details></section>']
 risk_peak=max(r['details']['risk_ratio_max'] for kind in 'TS' for r in result[kind]['1y'])
 parts.insert(0,f'<div class="box warn"><strong>Risk warning:</strong> 1% is nominal, not a hard cap. Preserving the current ceil/minimum-lot override produced initial stop risk up to {risk_peak:.2f}% of entry equity in the last-year variants, before commissions, swap and later gaps. Do not interpret these as strictly capped 1% sizing or FTMO-compliant results.</div>')
 style='body{background:#071511;color:#eef9f1;font:16px system-ui;margin:auto;max-width:1450px;padding:35px}h1{font-size:46px;letter-spacing:-1.5px}h2{font-size:29px}p{color:#b9d6ca;line-height:1.6}section,.box{background:#0c1d17;border:1px solid #2a463c;border-radius:17px;padding:24px;margin:25px 0}img{width:100%;border-radius:10px}table{border-collapse:collapse;font-size:14px;width:100%}th,td{padding:12px;border-bottom:1px solid #2a463c;text-align:left;white-space:nowrap}th{color:#72ecc1}.scroll{overflow:auto}.warn{color:#ffcc77}pre{white-space:pre-wrap;max-height:650px;overflow:auto;font-size:12px}summary{color:#72ecc1;cursor:pointer;padding:12px 0}a{color:#72ecc1}'
 page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Calyx · Gold target sensitivity</title><style>'+style+'</style><header><p>CALYX · RESEARCH ONLY · 2 OCTOBER 2026</p><h1>Smaller targets.<br>Better win rates—or just smaller wins?</h1><p>Trend Progression and Slow Trend · 0.5R / 0.6R / 0.7R / 1R / 2R / 3R / 6R.</p></header><div class="box warn">Target-only historical sensitivity, not a new full-pipeline qualification. All overlapping windows and all target settings are disclosed. No active account, production EA or website settings were changed.</div><p>Each run: separate $10,000 USD research account; nominal 1% equity risk; H4; 150 ms delay; broker costs; 1:2000 research leverage. Current ceil/minimum-lot policy is preserved and can exceed nominal risk. Real ticks begin January 2026; older ticks are generated. 365-day no-entry warm-up. End date is exclusive October 2, 2026.</p><p>Screen: clean execution, positive return, PF ≥ 1.20 and positive daily Sharpe in both 1y/5y, with ≥20/30 positions. Highest-win-rate candidate ranks 1y net WR; balanced candidate maximizes the lower 1y/5y Sharpe. Six-month/3y results expose fragility. No retuning was done after the comparison.</p><p>Net win rate includes positive stop exits; full TP rate is separate. Costs can turn nominal break-even exits into losses. Winning streaks depend on sample size; average runs and loss runs are shown too. Sharpe uses zero-filled calendar-day closed P/L, not floating equity or MT5 per-deal Sharpe. Every partial fill is aggregated by position ID.</p><p>For a pure fixed-payoff strategy before costs, break-even WR is 66.7% at 0.5R, 62.5% at 0.6R, 58.8% at 0.7R, 50% at 1R and 33.3% at 2R. Trend Progression management changes realized payoffs, so those thresholds are illustrative, not a substitute for measured PF.</p>'+''.join(parts)+'<footer><p>'+str(trials['unique_target_settings'])+' unique target settings; '+str(trials['native_attempts'])+' native case attempts including parity, chart and compile attempts. SOURCES.json, RESULTS.json, PICKS.json, PARITY-T/S.json, PROTOCOL.txt and each native batch retain the evidence. Historical returns and streaks do not forecast future results.</p></footer></html>'
 (ROOT/'Gold Target Results.html').write_text(page,encoding='utf-8')
 summary={kind:dict(name=NAMES[kind],baseline=BASELINES[kind],picks=picks[kind],periods={per:{str(r['parameters']['rr']):dict(stats=r['stats'],details=r['details'],clean=r['clean']) for r in rows} for per,rows in result[kind].items()}) for kind in 'TS'}
 save(ROOT/'SUMMARY.json',dict(strategies=summary,trials=trials,scope='Historical sensitivity only; no fresh out-of-sample qualification or deployment'));status('TARGET REPORT COMPLETE')
if __name__=='__main__':main()
