"""Declared before observing development P&L; no event-group selection."""
from build_engine import BASE
STAGES=[
 ('stop','sl_mult',[1,1.5,2,2.5,3,4]),
 ('impulse','impulse_mult',[.5,1,1.5,2]),
 ('body','body_mult',[.25,.5,.75,1]),
 ('strength','body_fraction',[.5,.6,.75]),
 ('signal','signal_mode',[0,1,2]),
 ('window','window_minutes',[10,20,30]),
 ('hold','hold_minutes',[15,30,45,60]),
 ('target','target_fraction',[.5,.75,1])]
PLAN=dict(baseline=BASE,stages=STAGES,beam_width=2,finalists=3,
 neighbourhood=['sl_mult','impulse_mult','hold_minutes'],neighbourhood_factors=[.8,1,1.2],
 objective='PF stability and positive years first; shrink sparse win rates, penalise drawdown and too few trades. No OOS or event-group reselection.',
 finalists_validation='2024 only; average development/2024 score with no-trade/negative/PF<=1 penalty.',
 minimum_development_trades=30,minimum_validation_trades=10)

def score(row,minimum=30):
 m=row['metrics'];n=m['trades'];pf=m['pf'] or 0
 if n==0:return -100
 positive=sum(x['net']>0 for x in m['yearly'])/max(1,len(m['yearly']))
 wr=(m['win_rate_pct']*n+50*30)/(n+30)
 return (min(pf,4)-1)*2+positive+.005*wr-.035*m['equity_dd']+min(n/minimum,1)*.5-(2 if n<minimum else 0)-(2 if m['net']<=0 else 0)
