"""Post-freeze robustness, honest research verdict and standalone results report."""
from pathlib import Path
from datetime import datetime
import gzip,html,importlib.util,io,json,math,re
import numpy as np
import pandas as pd
import runner as r
R=r.R;CFG=r.CONFIG;B=r.B
spec=importlib.util.spec_from_file_location('calyx_audit',B.parent/'Calyx Research Pipeline/calyx_pipeline.py');cp=importlib.util.module_from_spec(spec)
import sys
sys.modules[spec.name]=cp;spec.loader.exec_module(cp)
def daily(trades,start,end):
    days=pd.date_range(start,pd.Timestamp(end)-pd.Timedelta(days=1));p=pd.Series(0.,index=days)
    for t in trades:p.loc[pd.Timestamp(t['close_time']).normalize()]+=t['net_profit']
    prior=(10000+p.cumsum()).shift(1).fillna(10000);return days,(p/prior).to_numpy(),p.to_numpy()
def summary_paths(a):
    eq=np.cumprod(1+a,axis=1);peak=np.maximum.accumulate(np.c_[np.ones(len(eq)),eq],axis=1)[:,1:]
    dd=np.max(1-eq/peak,axis=1)*100;ret=(eq[:,-1]-1)*100
    return dict(probability_profit_pct=float(np.mean(ret>0)*100),return_p05_pct=float(np.quantile(ret,.05)),return_p50_pct=float(np.median(ret)),return_p95_pct=float(np.quantile(ret,.95)),
        max_drawdown_p50_pct=float(np.median(dd)),max_drawdown_p95_pct=float(np.quantile(dd,.95)),closed_pnl_total_breach_pct=float(np.mean(np.min(eq,axis=1)<=.9)*100),closed_pnl_daily_breach_pct=float(np.mean(np.min(a,axis=1)<=-.05)*100))
def samples(values,paths=10000,block=5,seed=261007):
    rng=np.random.default_rng(seed);n=len(values);starts=rng.integers(0,n,size=(paths,math.ceil(n/block)))
    indices=((starts[:,:,None]+np.arange(block))%n).reshape(paths,-1)[:,:n];return np.asarray(values)[indices]
def bootstrap(rec,seed):
    if not rec['trades']:return dict(paths=10000,block_length=5,status='insufficient_data',probability_profit_pct=0,return_p05_pct=None,profit_factor_p05=None,closed_pnl_total_breach_pct=100)
    _,returns,_=daily(rec['trades'],rec['start'],rec['end']);a=samples(returns,seed=seed);result=summary_paths(a)
    pnl=np.array([t['net_profit'] for t in rec['trades']]);b=samples(pnl,seed=seed+1);win=np.maximum(b,0).sum(1);loss=-np.minimum(b,0).sum(1);pf=np.divide(win,loss,out=np.full(len(loss),np.inf),where=loss>0)
    result.update(paths=10000,block_length=5,profit_factor_p05=float(np.quantile(pf,.05)),profit_factor_p50=float(np.median(pf)),profit_factor_p95=float(np.quantile(pf,.95)),scope='calendar-day closing balance bootstrap; trade-block PF separately; not native equity/rule pass probability')
    rng=np.random.default_rng(seed+2);miss={}
    for fraction in [.1,.2]:
        # Resample whole chronological trade blocks, then independently omit trades.
        prior=10000;tr=[]
        for t in rec['trades']:tr.append(t['net_profit']/prior);prior+=t['net_profit']
        x=samples(tr,seed=seed+3)* (rng.random((10000,len(tr)))>=fraction);miss[str(fraction)]=summary_paths(x)
    result['missed_trade_stress']=miss
    # Shuffle normalized trade returns: counts stay fixed, order is randomized.
    prior=10000;tr=[]
    for t in rec['trades']:tr.append(t['net_profit']/prior);prior+=t['net_profit']
    order=rng.random((10000,len(tr))).argsort(axis=1);shuffled=np.asarray(tr)[order];result['reshuffle']=summary_paths(shuffled)
    win=np.zeros(10000,dtype=int);loss=win.copy();mw=win.copy();ml=win.copy()
    for j in range(len(tr)):
        win=np.where(shuffled[:,j]>0,win+1,0);loss=np.where(shuffled[:,j]<0,loss+1,0);mw=np.maximum(mw,win);ml=np.maximum(ml,loss)
    result['reshuffle'].update(max_win_streak_p50=float(np.median(mw)),max_loss_streak_p50=float(np.median(ml)),max_loss_streak_p95=float(np.quantile(ml,.95)))
    result['reshuffle_note']='Compounded normalized closing-trade returns; preserves the observed sign/count sample, not changing regimes.'
    return r.safe(result)
def stress(rec):
    if not rec['trades']:return dict(status='insufficient_data',scenarios=[])
    folder=R/'native'/rec['stage'];q=pd.read_csv(io.BytesIO(gzip.decompress((folder/'0-quotes.csv.gz').read_bytes())))
    deals=pd.read_csv(io.BytesIO(gzip.decompress((folder/'0-deals.csv.gz').read_bytes())))
    assert q.ticket.is_unique and set(deals.ticket).issubset(set(q.ticket)),'Missing fill-time quote evidence'
    # USTEC CFD cash/point/lot checked against actual deal gross profits before using it.
    bypos={t['position_id']:t for t in rec['trades']}
    for pid,d in deals.groupby('position_id'):
        t=bypos[int(pid)];z=d[d.entry==1];expected=float(((z.price-t['open_price'])*z.volume).sum())*(1 if t['side']=='buy' else -1)
        assert abs(expected-t['profit'])<.03*len(z),'USTEC contract conversion assumption failed'
    spread_cash=(q.ask-q.bid)*q.volume
    extra=spread_cash.groupby(q.position_id).sum().to_dict();pnl=np.array([t['net_profit'] for t in rec['trades']]);cost=np.array([extra.get(t['position_id'],0) for t in rec['trades']])
    commission=np.array([-min(0,t['commission']+t['fee']) for t in rec['trades']]);roundtrip=cost.copy()
    decisions=pd.read_csv(io.BytesIO(gzip.decompress((folder/'0-decisions.csv.gz').read_bytes())),encoding='utf-16');sent=decisions[decisions.reason=='entry_sent'].sort_values('epoch')
    adverse=[]
    for t in rec['trades']:
        request=sent[sent.epoch<=t['open_epoch']+1].iloc[-1]
        maximum=2*rec['parameters']['tf']*60+1 if rec['parameters']['entry']>=2 else 2
        assert t['open_epoch']-request.epoch<=maximum and abs(request.lots-t['volume'])<1e-7,'Cannot match executed fill to its risk/price request'
        slip=(t['open_price']-request.entry_quote)*(1 if t['side']=='buy' else -1)
        adverse.append(max(0,slip)*t['volume'])
    adverse=np.asarray(adverse);cost+=commission+adverse
    rows=[]
    for mult in [1,2]:
        x=pnl-mult*cost;rows.append(dict(extra_recorded_roundtrip_cost_multiple=mult,mean_extra_cash_per_position=float((mult*cost).mean()),net=float(x.sum()),return_pct=float(x.sum()/100),pf=cp.profit_factor(x),win_rate=float(np.mean(x>0)*100)))
    return dict(status='measured',fill_quote_rows=len(q),mean_roundtrip_spread_cash=float(roundtrip.mean()),mean_roundtrip_commission_cash=float(commission.mean()),mean_adverse_entry_slippage_cash=float(adverse.mean()),scenarios=rows,
      zero_spread_warning=bool(np.all(roundtrip==0)),
      scope='Extra 1x/2x recorded fill-time spread + commissions + adverse requested-versus-filled entry slippage, on top of native costs. Zero measured spread is disclosed, not replaced with invented prices. Algebraic stress only; different fills, exit slippage and future costs are not reproduced.')
def ftmo_reference(rec,seed):
    # Saved local rule snapshot, not a claim about future terms or a validated prop account.
    days,ret,_=daily(rec['trades'],rec['start'],rec['end']);a=samples(ret,block=5,seed=seed)[:,:365]
    active=np.zeros(len(days),dtype=bool)
    for t in rec['trades']:
        d=pd.Timestamp(t['open_time']).normalize()
        if d in days:active[days.get_loc(d)]=True
    # Joint resampling indices keeps activity and returns aligned.
    rng=np.random.default_rng(seed);starts=rng.integers(0,len(days),size=(10000,math.ceil(len(days)/5)));idx=((starts[:,:,None]+np.arange(5))%len(days)).reshape(10000,-1)[:,:365];act=active[idx]
    eq=np.ones(10000);phase=np.zeros(10000,dtype=int);count=np.zeros(10000,dtype=int);bad=np.zeros(10000,dtype=bool);passed=np.zeros(10000,dtype=bool);finish=np.zeros(10000,dtype=int)
    for j in range(365):
        live=~bad & ~passed;old=eq.copy();eq[live]*=1+a[live,j];count[live]+=act[live,j]
        bad|=live & ((eq<=.9) | ((eq-old)<=-.05))
        target=np.where(phase==0,1.1,1.05);hit=live & ~bad & (eq>=target) & (count>=4)
        done=hit & (phase==1);passed|=done;finish[done]=j+1
        advance=hit & (phase==0);phase[advance]=1;eq[advance]=1;count[advance]=0
    phase1=phase==1
    return dict(paths=10000,horizon_calendar_days=365,closed_pnl_phase1_pass_pct=float(phase1.mean()*100),closed_pnl_phase2_pass_given_phase1_pct=float(passed.sum()/phase1.sum()*100) if phase1.any() else None,
        closed_pnl_two_phase_pass_pct=float(passed.mean()*100),closed_pnl_breach_pct=float(bad.mean()*100),unfinished_pct=float((~passed & ~bad).mean()*100),
        median_calendar_days_to_pass=float(np.median(finish[passed])) if passed.any() else None,
        scope='Exploratory daily closing-PnL proxy. Targets 10% then 5%, min 4 active days each, static total loss 10%, daily loss 5%. UTC day bins rather than CE(S)T reset; no intraday path, phase-review delays, or live FTMO guards. Not a forecast.')
def ftmo(rec,seed,handover_override=None):
    from dataclasses import replace
    from app.prop_sim.engine import SimConfig,sample_indices,simulate
    from app.prop_sim.ledger import Features
    from app.prop_sim.rules import get_programme
    programme=get_programme('ftmo-2step-standard')
    if handover_override is not None:programme=replace(programme,handover_days=tuple(handover_override))
    days,returns,pnl=daily(rec['trades'],rec['start'],rec['end']);opened=np.zeros(len(days));low=np.zeros(len(days));cash=np.zeros(len(days))
    prior=np.r_[10000,10000+np.cumsum(pnl)[:-1]]
    for t in sorted(rec['trades'],key=lambda t:t['close_time']):
        day=pd.Timestamp(t['close_time']).normalize();i=days.get_loc(day);cash[i]+=t['net_profit']/prior[i];low[i]=min(low[i],cash[i])
        day=pd.Timestamp(t['open_time']).normalize()
        if day in days:opened[days.get_loc(day)]+=1
    feature=Features(start=days[0].date(),days=len(days),pnl=returns,low_closed=low,low_envelope=low.copy(),opened=opened)
    cfg=SimConfig(account_size=10000,fee=None,sizing='pct_balance',horizon_days=365,paths=10000,method='bootstrap',block_days=5,seed=seed)
    idx=sample_indices(len(days),cfg);out=simulate(programme,feature,feature,cfg,idx,'closed')
    p1=out.pass_day[:,0]>=0;passed=out.pass_day[:,1]>=0;bad=(out.breach_cause>0)&(out.breach_stage<2)
    return dict(paths=10000,horizon_calendar_days=365,closed_pnl_phase1_pass_pct=float(p1.mean()*100),
      closed_pnl_phase2_pass_given_phase1_pct=float(passed.sum()/p1.sum()*100) if p1.any() else None,
      closed_pnl_two_phase_pass_pct=float(passed.mean()*100),closed_pnl_breach_pct=float(bad.mean()*100),unfinished_pct=float((~passed&~bad).mean()*100),
      median_calendar_days_to_pass=float(np.median(out.pass_day[passed,1]+1)) if passed.any() else None,
      median_calendar_days_to_funded=float(np.median(out.funded_day[passed]+1)) if passed.any() else None,
      phase1_median_days=float(np.median(out.pass_day[p1,0]+1)) if p1.any() else None,
      engine='Existing app.prop_sim.engine, closed ledger mode, 5-calendar-day blocks',handover_days=list(programme.handover_days),
      rules_snapshot=programme.verification,
      scope='Exploratory daily closing-position-PnL proxy: 10%/5% targets, 4 active days each, 5% daily / 10% static loss. Within-day closing-PnL minimum retained; floating equity, exact CE(S)T resets, entry-commission timing and installed FTMO guards are not replayed. Cached rule snapshot, not a forecast or current-account validation.')
def audit(bot,rec):
    frozen=r.load(R/(bot+' FROZEN.json'));outcomes=[cp.TradeOutcome(datetime.fromisoformat(t['close_time']),t['net_profit'],t['commission'],t['swap']) for t in rec['trades']]
    _,returns,_=daily(rec['trades'],rec['start'],rec['end']);n=frozen['tested_unique_configurations'];sr=cp.sharpe_statistics(list(returns),n,365);mc=bootstrap(rec,261007+(1 if bot=='vault' else 100));cost=stress(rec);thirds=cp.subperiods(outcomes)
    pnl=[t['net_profit'] for t in rec['trades']];recent=cp.profit_factor(pnl[len(pnl)//2:]);gates=dict(older_validation_clean=bool(frozen['selected_validation']['clean']),older_validation_minimum15=frozen['selected_validation']['metrics']['trades']>=15,
       older_validation_positive=frozen['selected_validation']['metrics']['net']>0,older_validation_pf_above1=(frozen['selected_validation']['metrics']['pf'] or 0)>1,
       oos_execution_clean=bool(rec['clean']),minimum30=len(pnl)>=30,positive=rec['metrics']['net']>0,pf_above1=(rec['metrics']['pf'] or 0)>1,
       bootstrap_p05_positive=(mc.get('return_p05_pct') or -1)>0,bootstrap_pf_p05_above1=(mc.get('profit_factor_p05') or 0)>1,bootstrap_probability95=(mc.get('probability_profit_pct') or 0)>=95,
       deflated_sharpe95=sr['deflated_sharpe_pct']>=95,two_profitable_thirds=sum(x['net_profit']>0 for x in thirds)>=2,recent_half_pf_above1=recent>1,
       closed_total_breach_below5=mc['closed_pnl_total_breach_pct']<=5,cost_stress_pf_above1=cost['status']=='measured' and all(x['pf']>1 for x in cost['scenarios']))
    research_verdict='FORWARD-TEST RESEARCH CANDIDATE' if all(gates.values()) else ('WATCH / NOT VALIDATED' if gates['positive'] and gates['pf_above1'] else 'REJECT FROZEN CANDIDATE')
    balance=10000;run=[];longest=[];run_balance=balance;longest_balance=balance
    for t in rec['trades']:
        if t['net_profit']<0:
            if not run:run_balance=balance
            run.append(t)
            if len(run)>len(longest):longest=list(run);longest_balance=run_balance
        else:run=[]
        balance+=t['net_profit']
    exits=dict(zero_gross_SL_exits_with_net_loss=sum(t['reason']==4 and abs(t['profit'])<.005 and t['net_profit']<0 for t in rec['trades']),
      longest_net_loss_streak=len(longest),streak_net_cash=sum(t['net_profit'] for t in longest),streak_opening_balance=longest_balance,
      streak_loss_pct_of_opening_balance=-sum(t['net_profit'] for t in longest)/longest_balance*100,
      streak_zero_gross_SL_exits=sum(t['reason']==4 and abs(t['profit'])<.005 for t in longest),
      scope='Net-position win rate and streaks include fees. Zero-gross SL exits are counted separately, never relabelled as wins. Streak percentage is reconstructed closing balance, not native intraday equity.')
    result=dict(metrics=rec['metrics'],exit_mix=exits,sharpe=sr,monte_carlo=mc,cost_stress=cost,thirds=thirds,recent_half_pf=recent,gates=gates,verdict=research_verdict,
       ftmo=ftmo(rec,261007+(1 if bot=='vault' else 100)),tested_configurations=n,multiple_test_note='Analytic DSR approximation; recorded prior-revision development configurations are included. Correlated trials and earlier informal exposure prevent an untouched institutional-validation claim.')
    return r.safe(result)

def holdout_audit(bot,candidate,original):
    """Cache completed post-freeze evidence, so native runs can proceed separately."""
    inputs=dict(candidate_report=candidate['report_sha256'],original_report=original['report_sha256'],frozen=r.sha(R/(bot+' FROZEN.json')),analysis=r.sha(Path(__file__)),rules=r.sha(B.parent/'EA store/data/prop-rules/ftmo-2step-standard.json'))
    path=R/'mc-cache'/(bot+'.json')
    if path.exists():
        cached=r.load(path)
        if cached['inputs']==inputs:return cached['audit']
    seed=261007+(1 if bot=='vault' else 100)
    result=audit(bot,candidate)
    result['raw_ftmo_comparison']=ftmo(original,seed)
    result['raw_monte_carlo_comparison']=bootstrap(original,seed)
    r.save(path,dict(inputs=inputs,audit=result))
    return result
def portfolio(evaluations):
    a=evaluations['vault']['OOS'];b=evaluations['overnight']['OOS'];start,end=CFG['oos'];days,ar,_=daily(a['trades'],start,end);_,br,_=daily(b['trades'],start,end)
    # Recorded trade risk as fraction of isolated equity; arithmetic daily overlay only.
    def merged(x,y,label):
        rr=x+y;eq=np.cumprod(1+rr);peak=np.maximum.accumulate(np.r_[1,eq])[1:]
        return dict(label=label,return_pct=float((eq[-1]-1)*100),closed_daily_dd=float(np.max(1-eq/peak)*100),daily_calendar_sharpe=float(rr.mean()/rr.std(ddof=1)*np.sqrt(365)),
           scope='Re-sized daily return overlay, not shared MT5 fills/equity, margin or guard replay')
    _,ra,_=daily(evaluations['vault']['Raw OOS']['trades'],start,end);_,rb,_=daily(evaluations['overnight']['Raw OOS']['trades'],start,end)
    overlapping=0;maxopen=0;events=[]
    for bot in ['vault','overnight']:
        for t in evaluations[bot]['OOS']['trades']:events.extend([(t['open_epoch'],1,bot),(t['close_epoch'],-1,bot)])
    state={'vault':0,'overnight':0}
    for epoch,change,bot in sorted(events,key=lambda x:(x[0],x[1])):
        state[bot]+=change;maxopen=max(maxopen,sum(state.values()));overlapping+=int(change==1 and all(state.values()))
    cached=B.parent/'EA store/data/evidence-cache/v1/portfolio/current/3y.json';payload=r.load(cached)
    # Contextual comparison to the frozen, explicitly stale cache; never replace the final OOS with this shorter window.
    cachetrades=r.load(cached.with_name('3y.trades.json'));cacheend=pd.Timestamp(payload['period'].split(' to ')[1])+pd.Timedelta(days=1)
    common=days[days<cacheend];cash=pd.Series(0.,index=common)
    for t in cachetrades:
        d=pd.Timestamp(t['close_time']).normalize()
        if d in cash.index:cash.loc[d]+=t['net_profit']
    # Rebase the old arithmetic portfolio to $10k for context only. This is not its live allocation/risk replay.
    baseprior=(10000+cash.cumsum()).shift(1).fillna(10000);cr=(cash/baseprior).to_numpy();ca=ar[:len(common)];cb=br[:len(common)]
    context=dict(start=str(common[0].date()),end_exclusive=str(cacheend.date()),cached_only=merged(cr,np.zeros(len(cr)),'Stale 34-EA arithmetic cache'),
       plus_vault=merged(cr,ca,'Cache + Vault candidate daily overlay'),plus_overnight=merged(cr,cb,'Cache + Overnight candidate daily overlay'),
       plus_both=merged(cr,ca+cb,'Cache + both candidates daily overlay'),
       correlation_vault=float(np.corrcoef(cr,ca)[0,1]),correlation_overnight=float(np.corrcoef(cr,cb)[0,1]),
       caution='Shortened contextual cache overlap ONLY. Final candidate OOS remains the full two calendar years. Rebased cached cash flows are stale independent-test arithmetic, not current allocations or native shared equity.')
    return dict(daily_return_correlation=float(np.corrcoef(ar,br)[0,1]),overlapping_entry_events=overlapping,max_concurrent_positions=maxopen,stale_cache_context=context,
        raw_pair=merged(ra,rb,'Raw pair'),candidate_pair=merged(ar,br,'Frozen candidate pair'),
        current_portfolio_assessment=dict(status='NOT A CURRENT-PORTFOLIO VALIDATION',cached_label=payload.get('label'),cached_period=payload.get('period'),sha256=r.sha(cached),
          reason='Cached combined evidence ends 2026-08-30 and describes 34 EAs. It does not represent the current reviewed roster/settings or cover the full frozen two-year holdout. No stale/current result is fabricated.'))
def curves(rec):
    _,_,p=daily(rec['trades'],rec['start'],rec['end']);return 10000+np.cumsum(p)
def native_quality(rec):
    data=gzip.decompress((R/'native'/rec['stage']/'report.htm.gz').read_bytes())
    body=data.decode('utf-16') if data[:2] in [b'\xff\xfe',b'\xfe\xff'] else data.decode('utf-8-sig',errors='replace')
    match=re.search(r'History Quality:</td>\s*<td[^>]*>\s*<b>([^<]+)</b>',body,re.I)
    assert match,'Missing native history-quality label'
    return html.unescape(match.group(1)).strip()
def graph(raw,candidate):
    series=[np.r_[10000,curves(x)] for x in [raw,candidate]];lo=min(x.min() for x in series);hi=max(x.max() for x in series);span=max(1,hi-lo)
    paths=[]
    for z in np.linspace(lo,hi,5):
        y=260-(z-lo)/span*230
        paths.append(f'<line x1="85" x2="960" y1="{y:.1f}" y2="{y:.1f}" stroke="#284239"/><text x="78" y="{y+5:.1f}" text-anchor="end" fill="#9cabc3" font-size="14">${z:,.0f}</text>')
    for v,col in zip(series,['#9cabc3','#67efbe']):
        pts=' '.join(f'{85+i/(len(v)-1)*875:.1f},{260-(z-lo)/span*230:.1f}' for i,z in enumerate(v));paths.append(f'<polyline fill="none" stroke="{col}" stroke-width="2" points="{pts}"/>')
    return '<svg viewBox="0 0 1000 310" role="img" aria-label="Raw versus frozen candidate closing-balance curve in US dollars">'+''.join(paths)+f'<text x="85" y="292" fill="#9cabc3">{raw["start"]}</text><text x="960" y="292" text-anchor="end" fill="#9cabc3">2026-10-06</text><text x="590" y="20" fill="#9cabc3">Original</text><text x="740" y="20" fill="#67efbe">Frozen candidate</text></svg>'
def table(rows):
    head='<tr><th>Version / window</th><th>Dates (end exclusive)</th><th>Trades</th><th>/month</th><th>/weekday</th><th>Return</th><th>PF</th><th>Win rate</th><th>Floating DD</th><th>Sharpe*</th><th>Win / loss streak</th></tr>'
    body=[]
    for name,start,end,m in rows:
        f=lambda x,d=2:'—' if x is None or not math.isfinite(x) else f'{x:.{d}f}'
        body.append(f'<tr><td>{html.escape(name)}</td><td>{start} → {end}</td><td>{m["trades"]}</td><td>{f(m["trades_per_month"])}</td><td>{f(m["trades_per_weekday"])}</td><td>{f(m["return_pct"])}%</td><td>{f(m["pf"])}</td><td>{f(m["win_rate"],1)}%</td><td>{f(m["equity_dd"])}%</td><td>{f(m.get("daily_calendar_sharpe",m["daily_balance_sharpe"]))}</td><td>{m["win_streak"]} / {m["loss_streak"]}</td></tr>')
    return '<div class="scroll"><table>'+head+''.join(body)+'</table></div>'
def main():
    evaluations={bot:r.load(R/(bot+' EVALUATION.json')) for bot in ['vault','overnight']};audits={}
    for bot in evaluations:
        r.status('Robustness audit: '+bot);audits[bot]=holdout_audit(bot,evaluations[bot]['OOS'],evaluations[bot]['Raw OOS'])
        audits[bot]['five_year_monte_carlo_context']=bootstrap(evaluations[bot]['5Y'],261500+(1 if bot=='vault' else 100));r.save(R/(bot+' ROBUSTNESS.json'),audits[bot])
    joint=portfolio(evaluations);r.save(R/'PORTFOLIO RESEARCH.json',joint)
    body=['<h1>Vault Break + Overnight Bias ORB</h1><p>Full exploratory research pipeline · frozen 7 October 2026 · US100 / Exness USTEC · $10,000 · 1% planned equity risk per trade.</p>',
      '<aside>Research only. No live bots, BATs or website settings changed. The final two-year holdout (2024-10-07 → 2026-10-07) is retrospective OOS: it was already visible in earlier raw tests. Native Model 4 / 150 ms delay; earlier history contains generated ticks and broker tick-volume proxies, not NQ exchange data.</aside>',
      '<h2>Selection discipline</h2><p>Development: 2021-10-07 → 2023-10-07. Older validation: 2023-10-07 → 2024-10-07. One configuration per bot frozen before OOS; no picking a new winner after seeing recent results. Top-three staged search plus up to 27 Vault / 9 Overnight joint neighbours per finalist; duplicate dimensions collapse and actual counts are reported. Raw failures remain failures; continuation was explicitly authorised.</p>']
    body.append('<p>Revision 3 corrects the H4 midnight anchor and VWAP using completed M1 data; all closed H4 candles are retained for the indicator audit. Original M30/M15 rules are unchanged and reproduced trade for trade. Earlier development evidence remains archived, and its trials count toward the multiple-testing adjustment. Configurations with open positions or pending orders at the test boundary are ineligible; no exit is fabricated.</p>')
    summary=[]
    for bot in evaluations:
        for key,label in [('Raw OOS','Original'),('OOS','Frozen candidate')]:
            x=evaluations[bot][key];summary.append((bot.title()+' · '+label,x['start'],x['end'],x['metrics']))
    body.append('<h2>Two-year holdout comparison — the main decision table</h2>'+table(summary))
    for bot,name in [('vault','Vault Break'),('overnight','Overnight Bias ORB')]:
        e=evaluations[bot];a=audits[bot];f=r.load(R/(bot+' FROZEN.json'));body.append('<h2>'+name+' — '+a['verdict']+'</h2>');rows=[]
        body.append('<p>Native history-quality labels: five years '+html.escape(native_quality(e['5Y']))+'; three years '+html.escape(native_quality(e['3Y']))+'; final two-year OOS '+html.escape(native_quality(e['OOS']))+'. Model 4 does not make generated history into real exchange ticks.</p>')
        for key in ['5Y','3Y','1Y','6M','3M','OOS']:
            candidate=e[key];base=e['Raw OOS'] if key=='OOS' else e['Raw 3M'] if key=='3M' else r.load(R/'native'/('raw-'+bot+'-'+key)/'result.json')
            if key in ['OOS','3M']:m=base['metrics'];start=base['start'];end=base['end']
            else:
                start=base['from'];end=base['end_exclusive'];m=r.metrics(base['trades'],start,end,base['net_metrics']['equity_dd'])
            rows.extend([(f'Raw {key}',start,end,m),(f'Candidate {key}',candidate['start'],candidate['end'],candidate['metrics'])])
        body.extend([table(rows),graph(e['Raw OOS'],e['OOS']),'<p>*Sharpe uses calendar-day closing balance (365) for both raw and candidate, including weekend cash flows. Native floating DD is separate from closing-balance MC risk.</p>'])
        val=f['selected_validation'];body.append('<h3>Frozen settings and older validation</h3><pre>'+html.escape(json.dumps(f['parameters'],indent=2))+'</pre>');body.append(table([('Older validation',val['start'],val['end'],val['metrics'])]))
        body.append(f'<p>{f["tested_unique_configurations"]} recorded unique configurations (including {f.get("prior_revision_unique_configurations",0)} prior-revision development configurations); DSR {a["sharpe"]["deflated_sharpe_pct"]:.1f}%. Plateau profitable-neighbour shares: '+', '.join(f'{x["positive_neighbour_share"]*100:.0f}%' for x in f['plateaus'])+'.</p>')
        import search_plan
        settings={key:search_plan.freeze()['codes'].get(key,{}).get(str(int(value)),value) if key in search_plan.freeze()['codes'] else value for key,value in f['parameters'].items()}
        body.append('<details><summary>Settings in plain language</summary><pre>'+html.escape(json.dumps(settings,indent=2))+'</pre></details>')
        body.append('<h3>Net-loss streak and break-even cost breakdown</h3><pre>'+html.escape(json.dumps(a['exit_mix'],indent=2))+'</pre>')
        body.append('<h3>10,000-path robustness / measured-cost stress</h3><pre>'+html.escape(json.dumps({k:a[k] for k in ['monte_carlo','raw_monte_carlo_comparison','cost_stress','ftmo','raw_ftmo_comparison','gates']},indent=2))+'</pre>')
        search=r.load(R/(bot+' DEVELOPMENT TABLE.json'))
        for stage in dict.fromkeys(x['stage'] for x in search):
            tests=[x for x in search if x['stage']==stage]
            body.append('<details><summary>'+html.escape(stage)+f' · {len(tests)} native screening passes (Model 1)</summary>')
            body.append(table([(f'Case {x["index"]} · '+json.dumps(x['parameters'],separators=(',',':')),x['start'],x['end'],x['metrics']) for x in tests])+'</details>')
        years=[]
        full=e['5Y'];eq=pd.read_csv(io.BytesIO(gzip.decompress((R/'native'/full['stage']/'0-equity.csv.gz').read_bytes())),encoding='utf-16')
        for year in range(2021,2027):
            start=max(full['start'],f'{year}-01-01');end=min(full['end'],f'{year+1}-01-01')
            ts=[t for t in full['trades'] if start<=t['close_time'][:10]<end];initial=10000+sum(t['net_profit'] for t in full['trades'] if t['close_time'][:10]<start)
            m=r.metrics(ts,start,end,initial=initial);a0=pd.Timestamp(start,tz='UTC').timestamp();a1=pd.Timestamp(end,tz='UTC').timestamp();v=np.r_[initial,eq[(eq.epoch>=a0)&(eq.epoch<a1)].equity.to_numpy()];m['equity_dd']=float(np.max(1-v/np.maximum.accumulate(v))*100);years.append((f'Candidate calendar {year}',start,end,m))
        body.append('<h3>Calendar-year slices of the continuous five-year candidate run</h3>'+table(years)+'<p>Year-slice equity drawdowns are reconstructed from minute samples, not separate native per-year tick reruns. Returns use each year’s opening balance; counts include positions closed within that slice.</p>')
        diagnostics=r.load(R/(bot+' DIAGNOSTICS.json'));body.append('<h3>Post-freeze reduced-risk and related-index transfer checks</h3>'+table([(name,x['start'],x['end'],x['metrics']) for name,x in diagnostics.items()])+'<p>These are diagnostic checks, not new selection rounds. Related assets use the same frozen settings; fixed point stops are not silently re-scaled to a new asset. Broker-specific transfer data and costs differ.</p>')
    body.append('<h2>Raw gates, controls and pipeline status</h2><pre>'+html.escape(json.dumps(r.load(R/'RAW GATES.json'),indent=2))+'</pre>')
    body.append('<h2>Portfolio overlap and marginal effect</h2><pre>'+html.escape(json.dumps(joint,indent=2))+'</pre>')
    body.append('<h2>Limits and next step</h2><p>Scheduled exits execute at the next tradable quote, not magically at a closed-market deadline; gaps/slippage can exceed 1%. All positions include entry/exit commissions and swaps; partial exits are grouped into one position. Futures prices, costs and liquidity differ from this CFD reconstruction. Parameter counts, source hashes, actual native inputs, complete optimisation passes and position-level cash reconciliation are retained locally. Final research EAs deliberately refuse live execution. No claim of untouched OOS, guaranteed passing, or deployed performance.</p><p>Review these frozen candidates before any forward test or deployment. Rejected holdout candidates remain rejected; another search would need a new documented experiment.</p>')
    style='body{background:#071713;color:#e6fff4;font:16px system-ui;margin:40px auto;max-width:1300px;padding:0 24px}h1,h2{color:#67efbe}p{line-height:1.6}aside{padding:24px;border:1px solid #a78336;border-radius:14px;color:#ffdfa0}.scroll{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}td,th{padding:12px;text-align:right;border-bottom:1px solid #284239;white-space:nowrap}td:first-child,th:first-child{text-align:left}pre{background:#10261e;padding:20px;border-radius:12px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}svg{width:100%;margin-top:22px}'
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Golden Trio full research pipeline</title><style>'+style+'</style><main>'+''.join(body)+'</main></html>'
    (R/'Results.html').write_text(page,encoding='utf-8');r.save(R/'RESULTS.json',dict(audits=audits,portfolio=joint,live_changes=False,push=False));r.status('Research results report generated; independent verification still required')
if __name__=='__main__':main()
