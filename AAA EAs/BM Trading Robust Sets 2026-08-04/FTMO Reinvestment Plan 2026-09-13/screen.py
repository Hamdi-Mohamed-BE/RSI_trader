import json
from pathlib import Path
import engine as e

OUT=Path(__file__).resolve().parent
BASE={s:v for s,v in e.EAS.items() if s!='news-pulse-xau'}
CANDIDATES={
 'dmc-fresh-reaction-us100':('DMC Fresh Reaction US100','standard'),
 'us100-selective-orb-v3':('US100 Selective ORB V3','standard'),
 'nasdaq-overnight':('Nasdaq Overnight','standard'),
}
e.EAS={**BASE,**CANDIDATES}
rows,audit,_,_=e.load()
result=[]
for slug in CANDIDATES:
    r=e.replay([r for r in rows if r['slug']==slug],e.START,e.END,account=100000,challenge=False,stress=True)
    r10=e.replay([r for r in rows if r['slug']==slug],e.START,e.END,account=10000,challenge=False,stress=True)
    a=next(a for a in audit if a['slug']==slug)
    result.append({'slug':slug,'source':a,'trades':r['closed_trades'],'net':r['net'],
                   'win_rate':r['win_rate'],'pf':r['profit_factor'],'dd':r['max_closed_drawdown_pct'],
                   '10k_net':r10['net'],'10k_trades':r10['closed_trades'],'10k_breach':r10['breach']})
    print(json.dumps(result[-1]))
# Same EA safer variants are alternatives, not independent additions.
for mode in ['standard','safe']:
    e.EAS={**BASE,'xau-squeeze-momentum-standard':('XAU Squeeze '+mode,mode)}
    rr,aa,_,_=e.load()
    rr=[r for r in rr if r['slug']=='xau-squeeze-momentum-standard']
    r=e.replay(rr,e.START,e.END,account=100000,challenge=False,stress=True)
    a=next(a for a in aa if a['slug']=='xau-squeeze-momentum-standard')
    print(json.dumps({'slug':'xau-squeeze-momentum-standard','mode':mode,'N':a['ledger_trades'],'trades':r['closed_trades'],'net':r['net'],'wr':r['win_rate'],'pf':r['profit_factor'],'dd':r['max_closed_drawdown_pct']}))
(OUT/'candidate-screen.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Excluded ORB High Win 0.75R and Squeeze High Win 0.75R: cached trades do not itemize gross P/L, commission and swap.')
