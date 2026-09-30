from pathlib import Path
import json,hashlib
import numpy as np
import pandas as pd
import prop_engine as pe
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT.parent/'FTMO vs Stellar Instant Study 2026-09-28'
def save(name,obj): (ROOT/name).write_text(json.dumps(pe.clean(obj),indent=2,allow_nan=False),encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def stamp(s):return int(pd.Timestamp(s,tz='UTC').timestamp())
def stats(v,days):
    v=np.array(v,float);pos=v[v>0];neg=v[v<0];equity=np.r_[0.,np.cumsum(v)];draw=np.maximum.accumulate(equity)-equity
    mw=ml=w=l=0
    for x in v:
        w=w+1 if x>0 else 0;l=l+1 if x<0 else 0;mw=max(mw,w);ml=max(ml,l)
    gross=float(sum(pos));loss=-float(sum(neg))
    return dict(trades=len(v),trades_month=len(v)/max(days/30.4375,1e-9),trades_weekday=len(v)/max(days*5/7,1),net_r=float(sum(v)),
                expectancy=float(np.mean(v)) if len(v) else None,pf=gross/loss if loss else None,
                pf_without_best=(gross-max(pos))/loss if loss and len(pos) else None,win_rate=100*len(pos)/len(v) if len(v) else None,
                closed_cash_dd_r=float(max(draw)),max_win_streak=mw,max_loss_streak=ml)


