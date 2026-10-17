"""Predeclared bounded full-dimension search; no recent-period ranking."""
from pathlib import Path
import hashlib, itertools, json
R=Path(__file__).resolve().parent
FIELDS=['tf','reference','fraction','buffer','entry','stop','stop_scale','management','trigger','trail',
        'exit','rr','session','direction','filter','threshold','daily_cap','hold','flat','dow','width','ema_fast','ema_slow']
COMMON=dict(tf=15,reference=16408,fraction=.125,buffer=.1,entry=0,stop=0,stop_scale=1.5,
 management=0,trigger=1,trail=1,exit=0,rr=2,session=0,direction=0,filter=0,threshold=20,
 daily_cap=1,hold=480,flat=1,dow=0,width=1,ema_fast=12,ema_slow=26)
RAW={'gold':COMMON.copy(),'us100':COMMON|dict(tf=60,exit=1),
     'btc':COMMON|dict(reference=32769,fraction=.25)}
SYMBOL={'gold':'XAUUSD','us100':'USTEC','btc':'BTCUSD'}
IDEA={'gold':0,'us100':4,'btc':6}
STAGES=['timeframe','entry','stop','management','exit','session','direction','filters','holding','source']

def variants(stage,bot):
 if stage=='timeframe':return [dict(tf=x) for x in [1,3,5,15,30,60,240]]
 if stage=='entry':return [dict(entry=x) for x in [0,1,2,3]]
 if stage=='stop':return [dict(stop=0)]+[dict(stop=1,stop_scale=x) for x in [.5,.75,1,1.5,2,3,4]]+[dict(stop=x) for x in [2,3,4,5]]
 if stage=='management':return [dict(management=0)]+[dict(management=1,trigger=x) for x in [.5,1,1.5]]+[dict(management=x,trigger=1,trail=1) for x in [2,3,4,5,6,7]]
 if stage=='exit':return [dict(exit=1,rr=x) for x in [.5,.75,1,1.25,1.5,2,2.5,3,4,5,6]]+[dict(exit=2,management=2),dict(exit=3)]+([] if bot=='us100' else [dict(exit=0)])
 if stage=='session':return [dict(session=x,dow=0) for x in range(6)]+[dict(session=0,dow=x) for x in [1,2,3]]
 if stage=='direction':return [dict(direction=x) for x in [0,1,-1]]
 if stage=='filters':return [dict(filter=0)]+[dict(filter=1,threshold=x) for x in [15,20,25,30]]+[dict(filter=x,threshold=20) for x in [2,3,4,5,6]]
 if stage=='holding':return [dict(daily_cap=x) for x in [1,2,3]]+[dict(hold=x) for x in [60,240,480,1440]]+[dict(flat=x) for x in [0,1]]
 if stage=='source':
  if bot=='us100':return [dict(width=x) for x in [0,1,2]]+[dict(ema_fast=x,ema_slow=y) for x,y in [(10,24),(12,26),(16,32)]]
  fractions=[.1,.125,1/6] if bot=='gold' else [.2,.25,1/3]
  return [dict(fraction=x) for x in fractions]+[dict(buffer=x) for x in [.05,.1,.2]]+[dict(reference=x) for x in [16408,32769]]
 raise ValueError(stage)

def freeze():
 plan=dict(fields=FIELDS,baseline=RAW,stages={b:{s:variants(s,b) for s in STAGES} for b in RAW},
  procedure='Top 3 at each staged development search; joint stop/target/source neighbourhood; pre-OOS validation chooses one, frozen before final two years. Minimum30 development and30 validation whole positions; no relaxed sample gate.',
  risk='1% current closed balance; floor broker volume step, never minimum-lot oversizing. Risk reduced .5% post-freeze diagnostic only.',
  code_labels=dict(entry={'0':'next tick after close (baseline)','1':'one further completed confirming candle','2':'conditional market after 0.25ATR retrace within two bars','3':'conditional market after signal high/low breakout within two bars'},
   stop={'0':'original reference-range/signal extreme; cycle original1.5ATR','1':'ATR multiple','2':'signal wick plus buffer','3':'0.2% of requested price','4':'fixed price distance (Gold10/US10050/BTC500)','5':'last confirmed H4 swing plus buffer'},
   management={'0':'none','1':'BE at trigger R','2':'post-entry peak ATR trail','3':'post-entry peak0.1% price trail','4':'completed EMA12 trail','5':'last3 completed signal-bar swing trail','6':'step lock50% favourable movement after1R','7':'50% partial at1R then ATR trail'},
   exit={'0':'prior-reference midpoint','1':'fixed R','2':'no TP plus ATR trail','3':'time/day-flat only'},
   session={'0':'all until20:30UTC','1':'Asia00-08UTC','2':'London07-16UTC','3':'NewYork09:30-16ET','4':'London-NewYork overlap10-12ET','5':'NewYork open09:30-10:30ET'},
   filter={'0':'none','1':'ADX minimum','2':'directional DI','3':'ADX20 and DI','4':'H4EMA50 aligned slope','5':'ATR14/ATR50 in0.8-2.0','6':'spread <=0.1signalATR'}),
  omitted={'D1':'Signal closes at midnight; same-day intraday semantics would no longer represent raw entry; H4 still tested and subject to minimum counts.',
   'resting pending orders':'Conditional market quote triggers are tested and distinctly labelled; no claim of resting limit fill priority.',
   'news blackout':'No predeclared complete point-in-time event feed for all assets; not fabricated.',
   'pyramiding':'Excluded to preserve original one-position cash-risk and causal signal accounting; daily caps1/2/3 are tested.',
   'ATR percentile':'ATR short/long regime is tested instead; not mislabeled a fitted percentile.',
   'risk optimisation':'Risk does not select edge. Standardised1%, post-freeze0.5% diagnostic.',
   'extra Gann clock centres':'Keep8/16/32clock hypothesis; only width and EMA parameters tested; seeded equal-exposure control retained.'},
  prior_exposure='42 raw Gann/control configurations and recent charts already inspected; these count toward selection-risk disclosure.',
  frozen_before_search=True)
 p=R/'SEARCH PLAN.json'
 if p.exists():assert json.loads(p.read_text())==plan,'Frozen search plan changed'
 else:p.write_text(json.dumps(plan,indent=2),encoding='utf-8')
 return plan

def digest(c):return hashlib.sha256(json.dumps(c,sort_keys=True).encode()).hexdigest()
def dedupe(cases):return list({digest(c):c for c in cases}.values())
def neighbours(c,bot):
 source='width' if bot=='us100' else 'fraction'
 vals=[max(0,c[source]-1),c[source],c[source]+1] if bot=='us100' else [c[source]*.8,c[source],min(.45,c[source]*1.2)]
 return dedupe([c|dict(stop_scale=c['stop_scale']*s,rr=c['rr']*q,**{source:v}) for s,q,v in itertools.product([.8,1,1.2],[.8,1,1.2],vals)])
