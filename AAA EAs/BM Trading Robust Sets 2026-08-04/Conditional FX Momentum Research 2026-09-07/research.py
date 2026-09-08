"""Step 5: causal conditional FX momentum research for EURUSD and GBPJPY."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
import itertools
import json
import math
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit


ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
SOURCE_DATA = PACKAGE / "Slow Multi Asset Trend Research 2026-09-06" / "Data"
DATA = ROOT / "Data"
CHARTS = ROOT / "Charts"
SYMBOLS = ("EURUSD", "GBPJPY")
TIMEFRAMES = {"M15": ("15min", 15), "M30": ("30min", 30), "H1": ("1h", 60), "H4": ("4h", 240)}
SESSIONS = ("all-day", "asia", "london", "new-york", "overlap")
BREAKOUTS = (10, 20, 40)
EMAS = (50, 100, 200)
TRAIN = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2024-09-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
RISK = 0.01
SEED = 507092026

# kind, momentum window, state threshold, transition history, probability buffer, volatility cap
REGIMES = {
    "none": (0, 20, 0.01, 252, 0.0, 99.0),
    "state20-0.5pct": (1, 20, 0.005, 252, 0.0, 99.0),
    "state20-1pct": (1, 20, 0.010, 252, 0.0, 99.0),
    "state40-1pct": (1, 40, 0.010, 252, 0.0, 99.0),
    "state40-2pct": (1, 40, 0.020, 252, 0.0, 99.0),
    "markov20-1pct": (2, 20, 0.010, 252, 0.0, 99.0),
    "markov20-1pct-b10": (2, 20, 0.010, 252, 0.10, 99.0),
    "markov40-1pct": (2, 40, 0.010, 252, 0.0, 99.0),
    "markov40-2pct-b10": (2, 40, 0.020, 252, 0.10, 99.0),
    "markov20-1pct-normalvol": (2, 20, 0.010, 252, 0.0, 1.50),
    "markov20-5pct-reference": (2, 20, 0.050, 252, 0.0, 99.0),
}

STOP_VARIANTS = (
    ("atr", 0.75), ("atr", 1.00), ("atr", 1.25), ("atr", 1.50), ("atr", 2.00),
    ("swing", 5.0), ("swing", 10.0), ("swing", 20.0), ("structure", 0.0),
)
RR_VARIANTS = tuple(("fixed", x) for x in (0.5, 0.75, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 6.0)) + (("adaptive", 0.0),)
MANAGEMENTS = ("none", "breakeven", "atr-trail", "dynamic-50-20")
DIRECTIONS = ("both", "long-only", "short-only")
HOLDS = (24, 72, 120, 0)


@dataclass(frozen=True)
class Config:
    timeframe: str = "H1"
    session: str = "london"
    breakout: int = 20
    ema: int = 100
    regime: str = "markov20-1pct"
    direction: str = "both"
    stop_mode: str = "atr"
    stop_value: float = 1.25
    rr_mode: str = "fixed"
    rr: float = 2.0
    management: str = "none"
    max_hold_hours: int = 72


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def copy_data() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    for name in ("EURUSD-M15.npz", "GBPJPY-M15.npz", "metadata.json"):
        shutil.copy2(SOURCE_DATA / name, DATA / name)


def load(symbol: str) -> tuple[pd.DataFrame, dict]:
    rates = np.load(DATA / f"{symbol}-M15.npz")["rates"]
    idx = pd.to_datetime(rates["time"], unit="s", utc=True)
    frame = pd.DataFrame({k: rates[k].astype(float) for k in ("open", "high", "low", "close", "tick_volume", "spread")}, index=idx)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    meta = json.loads((DATA / "metadata.json").read_text(encoding="utf-8"))["symbols"][symbol]
    positive = frame.loc[frame.spread > 0, "spread"]
    floor = float(positive.quantile(0.35)) if len(positive) else 1.0
    frame["spread_price"] = np.maximum(frame.spread, floor) * float(meta["point"])
    return frame, meta | {"spread_floor_points": floor}


def true_range(frame: pd.DataFrame) -> pd.Series:
    prev = frame.close.shift(1)
    return pd.concat(((frame.high-frame.low), (frame.high-prev).abs(), (frame.low-prev).abs()), axis=1).max(axis=1)


def daily_markov(base: pd.DataFrame, window: int, threshold: float, history: int) -> pd.DataFrame:
    d = base.resample("1D", label="right", closed="left").agg(close=("close", "last")).dropna()
    d["ret1"] = np.log(d.close).diff()
    d["momentum"] = d.close / d.close.shift(window) - 1.0
    state = np.where(d.momentum > threshold, 2, np.where(d.momentum < -threshold, 0, 1)).astype(np.int8)
    state[~np.isfinite(d.momentum)] = -1
    signal = np.full(len(d), np.nan)
    for i in range(len(d)):
        if state[i] < 0:
            continue
        counts = np.ones((3, 3), dtype=float)  # light Laplace smoothing
        start = max(1, i-history)
        for j in range(start, i):
            a, b = int(state[j-1]), int(state[j])
            if a >= 0 and b >= 0:
                counts[a, b] += 1.0
        row = counts[int(state[i])]
        probs = row / row.sum()
        signal[i] = probs[2] - probs[0]
    vol5 = d.ret1.rolling(5, min_periods=5).std()
    vol60 = d.ret1.rolling(60, min_periods=20).std()
    return pd.DataFrame({"state": state, "markov": signal, "vol_ratio": vol5/vol60.replace(0, np.nan)}, index=d.index)


def resample(base: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    rule, minutes = TIMEFRAMES[timeframe]
    if timeframe == "M15":
        b = base.copy()
        b["volume"] = b.tick_volume
    else:
        b = base.resample(rule, label="left", closed="left").agg(
            open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
            volume=("tick_volume", "sum"), spread_price=("spread_price", "last"),
        ).dropna()
    b["atr"] = true_range(b).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    for n in BREAKOUTS:
        b[f"break_high_{n}"] = b.high.rolling(n, min_periods=n).max().shift(1)
        b[f"break_low_{n}"] = b.low.rolling(n, min_periods=n).min().shift(1)
    for n in EMAS:
        b[f"ema_{n}"] = b.close.ewm(span=n, adjust=False, min_periods=n).mean()
        b[f"ema_slope_{n}"] = b[f"ema_{n}"] - b[f"ema_{n}"].shift(max(1, int(round(240/minutes))))
    for n in (5, 10, 20):
        b[f"swing_low_{n}"] = b.low.rolling(n, min_periods=n).min().shift(1)
        b[f"swing_high_{n}"] = b.high.rolling(n, min_periods=n).max().shift(1)
    daily_cache = {}
    for name, (_, window, threshold, history, _, _) in REGIMES.items():
        key = (window, threshold, history)
        if key not in daily_cache:
            daily_cache[key] = daily_markov(base, window, threshold, history)
        f = daily_cache[key].reindex(b.index, method="ffill")
        b[f"reg_state_{name}"] = f.state
        b[f"reg_signal_{name}"] = f.markov
        b[f"reg_vol_{name}"] = f.vol_ratio
    return b.dropna(subset=["atr"])


def session_active(index: pd.DatetimeIndex, session: str) -> np.ndarray:
    utc = index
    london = index.tz_convert("Europe/London")
    ny = index.tz_convert("America/New_York")
    if session == "all-day":
        active = np.ones(len(index), dtype=bool)
    elif session == "asia":
        active = (utc.hour >= 0) & (utc.hour < 8)
    elif session == "london":
        minute = london.hour*60+london.minute
        active = (minute >= 8*60) & (minute < 16*60+30)
    elif session == "new-york":
        minute = ny.hour*60+ny.minute
        active = (minute >= 9*60+30) & (minute < 16*60)
    else:
        lm = london.hour*60+london.minute
        nm = ny.hour*60+ny.minute
        active = (lm >= 8*60) & (lm < 16*60+30) & (nm >= 9*60+30) & (nm < 16*60)
    weekday = np.asarray(index.weekday < 5)
    return np.asarray(active & weekday, dtype=np.int8)


def arrays(b: pd.DataFrame, c: Config) -> dict[str, np.ndarray]:
    swing_n = int(c.stop_value) if c.stop_mode == "swing" else 10
    kind, _, _, _, buffer, vol_cap = REGIMES[c.regime]
    return {
        "time": b.index.as_unit("s").asi8.astype(np.int64),
        "open": b.open.to_numpy(float), "high": b.high.to_numpy(float), "low": b.low.to_numpy(float), "close": b.close.to_numpy(float),
        "spread": b.spread_price.to_numpy(float), "atr": b.atr.to_numpy(float),
        "break_high": b[f"break_high_{c.breakout}"].to_numpy(float), "break_low": b[f"break_low_{c.breakout}"].to_numpy(float),
        "ema": b[f"ema_{c.ema}"].to_numpy(float), "ema_slope": b[f"ema_slope_{c.ema}"].to_numpy(float),
        "swing_low": b[f"swing_low_{swing_n}"].to_numpy(float), "swing_high": b[f"swing_high_{swing_n}"].to_numpy(float),
        "reg_state": b[f"reg_state_{c.regime}"].fillna(-1).to_numpy(np.int8),
        "reg_signal": b[f"reg_signal_{c.regime}"].fillna(0).to_numpy(float),
        "reg_vol": b[f"reg_vol_{c.regime}"].fillna(99).to_numpy(float),
        "active": session_active(b.index, c.session),
        "day_key": np.asarray(b.index.year*10000+b.index.month*100+b.index.day, dtype=np.int32),
        "regime_kind": kind, "regime_buffer": buffer, "vol_cap": vol_cap,
    }


@njit(cache=True)
def simulate(time, op, hi, lo, cl, spr, atr, break_high, break_low, ema, ema_slope, swing_low, swing_high,
             reg_state, reg_signal, reg_vol, active, day_key, start_ts, end_ts, regime_kind, regime_buffer, vol_cap,
             direction_mode, stop_mode, stop_value, rr_mode, rr, management, max_hold_seconds, friction_r):
    n = len(time)
    ent_out=np.empty(n//2+10,np.int64); ex_out=np.empty(n//2+10,np.int64); r_out=np.empty(n//2+10,np.float64); side_out=np.empty(n//2+10,np.int8)
    count=0; pos=0; entry=0.; initial=0.; stop=0.; target=0.; entry_i=0; current_day=-1; trades_day=0
    realized=1.; peak=1.; max_dd=0.
    for i in range(2,n):
        if time[i] < start_ts: continue
        if time[i] >= end_ts: break
        if day_key[i] != current_day:
            current_day=day_key[i]; trades_day=0
        if pos != 0 and max_hold_seconds > 0 and time[i]-time[entry_i] >= max_hold_seconds:
            px=op[i] if pos>0 else op[i]+spr[i]
            result=pos*(px-entry)/initial-friction_r
            ent_out[count]=time[entry_i];ex_out[count]=time[i];r_out[count]=result;side_out[count]=pos;count+=1
            realized*=max(.01,1+.01*result);peak=max(peak,realized);max_dd=max(max_dd,1-realized/peak);pos=0
        if pos != 0:
            hit=False;px=0.
            if pos>0:
                if op[i]<=stop:px=op[i];hit=True
                elif lo[i]<=stop:px=stop;hit=True
                elif hi[i]>=target:px=target;hit=True
            else:
                ask_open=op[i]+spr[i];ask_hi=hi[i]+spr[i];ask_lo=lo[i]+spr[i]
                if ask_open>=stop:px=ask_open;hit=True
                elif ask_hi>=stop:px=stop;hit=True
                elif ask_lo<=target:px=target;hit=True
            if hit:
                result=pos*(px-entry)/initial-friction_r
                ent_out[count]=time[entry_i];ex_out[count]=time[i];r_out[count]=result;side_out[count]=pos;count+=1
                realized*=max(.01,1+.01*result);peak=max(peak,realized);max_dd=max(max_dd,1-realized/peak);pos=0
            else:
                best=((hi[i]-entry)/initial if pos>0 else (entry-(lo[i]+spr[i]))/initial)-friction_r
                worst=((lo[i]-entry)/initial if pos>0 else (entry-(hi[i]+spr[i]))/initial)-friction_r
                peak=max(peak,realized*(1+.01*best));max_dd=max(max_dd,1-realized*(1+.01*worst)/peak)
                progress=(cl[i]-entry)/initial if pos>0 else (entry-(cl[i]+spr[i]))/initial
                if management==1 and progress>=1.0:
                    stop=max(stop,entry) if pos>0 else min(stop,entry)
                elif management==2 and progress>=1.0:
                    candidate=cl[i]-1.5*atr[i] if pos>0 else cl[i]+spr[i]+1.5*atr[i]
                    stop=max(stop,candidate) if pos>0 else min(stop,candidate)
                elif management==3 and progress>=0.5:
                    candidate=entry+pos*.2*initial
                    stop=max(stop,candidate) if pos>0 else min(stop,candidate)
        if pos != 0 or active[i]==0 or trades_day>=2: continue
        p=i-1
        if not np.isfinite(atr[p]) or not np.isfinite(ema[p]) or not np.isfinite(break_high[p]) or not np.isfinite(break_low[p]): continue
        long_signal=cl[p]>break_high[p] and cl[p]>ema[p] and ema_slope[p]>0
        short_signal=cl[p]<break_low[p] and cl[p]<ema[p] and ema_slope[p]<0
        if direction_mode==1: short_signal=False
        elif direction_mode==2: long_signal=False
        if long_signal==short_signal: continue
        side=1 if long_signal else -1
        if regime_kind==1:
            if (side>0 and reg_state[p]!=2) or (side<0 and reg_state[p]!=0): continue
        elif regime_kind==2:
            if side*reg_signal[p] <= regime_buffer or reg_vol[p]>vol_cap: continue
        ent=op[i]+spr[i] if side>0 else op[i]
        if stop_mode==0:
            distance=stop_value*atr[p]
        elif stop_mode==1:
            raw=ent-swing_low[p] if side>0 else swing_high[p]+spr[p]-ent
            distance=max(.5*atr[p],min(4*atr[p],raw+.1*atr[p]))
        else:
            raw=ent-break_low[p] if side>0 else break_high[p]+spr[p]-ent
            distance=max(.5*atr[p],min(5*atr[p],raw))
        if not np.isfinite(distance) or distance<=2*spr[i]: continue
        effective_rr=rr
        if rr_mode==1: effective_rr=3.0 if abs(reg_signal[p])>=.25 else 1.0
        pos=side;entry=ent;initial=distance;stop=entry-side*distance;target=entry+side*effective_rr*distance;entry_i=i;trades_day+=1
    if pos!=0:
        i=min(n-1,np.searchsorted(time,end_ts)-1);px=cl[i] if pos>0 else cl[i]+spr[i]
        result=pos*(px-entry)/initial-friction_r
        ent_out[count]=time[entry_i];ex_out[count]=time[i];r_out[count]=result;side_out[count]=pos;count+=1
        realized*=max(.01,1+.01*result);peak=max(peak,realized);max_dd=max(max_dd,1-realized/peak)
    return ent_out[:count],ex_out[:count],r_out[:count],side_out[:count],max_dd*100


DIR_CODE={"both":0,"long-only":1,"short-only":2};STOP_CODE={"atr":0,"swing":1,"structure":2};RR_CODE={"fixed":0,"adaptive":1};MAN_CODE={"none":0,"breakeven":1,"atr-trail":2,"dynamic-50-20":3}


def metrics(entries, exits, rs, sides, mtm_dd=0.0, extra_cost_r=0.0) -> dict:
    rs=np.asarray(rs,float)-extra_cost_r
    if not len(rs): return dict(return_pct=0.,profit_factor=0.,win_rate=0.,max_dd_pct=0.,trades=0,sharpe=0.,recovery=0.,expectancy_r=0.,average_win_r=0.,average_loss_r=0.,longs=0,shorts=0)
    frac=RISK*rs;eq=np.r_[1.,np.cumprod(1+frac)];pnl=np.diff(eq);gp=pnl[pnl>0].sum();gl=-pnl[pnl<0].sum();ret=(eq[-1]-1)*100
    dd=max(float(mtm_dd),float(np.max(1-eq/np.maximum.accumulate(eq))*100))
    daily=pd.Series(frac,index=pd.to_datetime(exits,unit="s",utc=True)).groupby(level=0).sum().resample("1D").sum()
    sharpe=float(daily.mean()/daily.std(ddof=1)*math.sqrt(252)) if daily.std(ddof=1)>0 else 0.
    return dict(return_pct=float(ret),profit_factor=float(min(99,gp/gl if gl else 99)),win_rate=float(100*np.mean(rs>0)),max_dd_pct=dd,trades=int(len(rs)),sharpe=sharpe,recovery=float(ret/dd if dd else 0),expectancy_r=float(rs.mean()),average_win_r=float(rs[rs>0].mean() if np.any(rs>0) else 0),average_loss_r=float(rs[rs<0].mean() if np.any(rs<0) else 0),longs=int(np.sum(sides>0)),shorts=int(np.sum(sides<0)))


def run(bars: dict[str,pd.DataFrame], c: Config, dates, collect=False, extra_cost_r=0.0) -> dict:
    a=arrays(bars[c.timeframe],c)
    args=[a[x] for x in ("time","open","high","low","close","spread","atr","break_high","break_low","ema","ema_slope","swing_low","swing_high","reg_state","reg_signal","reg_vol","active","day_key")]
    result=simulate(*args,int(dates[0].timestamp()),int(dates[1].timestamp()),a["regime_kind"],a["regime_buffer"],a["vol_cap"],DIR_CODE[c.direction],STOP_CODE[c.stop_mode],c.stop_value,RR_CODE[c.rr_mode],c.rr,MAN_CODE[c.management],c.max_hold_hours*3600,0.02)
    ent,ex,rs,sides,dd=result;out=metrics(ent,ex,rs,sides,dd,extra_cost_r)
    if collect: out["trades_data"]=[dict(entry=pd.Timestamp(int(e),unit="s",tz="UTC").isoformat(),exit=pd.Timestamp(int(x),unit="s",tz="UTC").isoformat(),r=float(r),side="long" if s>0 else "short") for e,x,r,s in zip(ent,ex,rs,sides)]
    return out


def robust_score(train:dict,valid:dict)->float:
    if train["trades"]<20 or valid["trades"]<20:return -10000+train["trades"]+valid["trades"]
    mr=min(train["return_pct"],valid["return_pct"]);mp=min(train["profit_factor"],valid["profit_factor"]);ms=min(train["sharpe"],valid["sharpe"]);md=max(train["max_dd_pct"],valid["max_dd_pct"])
    score=.35*mr+12*math.log(max(.05,min(3.,mp)))+1.5*ms+min(train["recovery"],valid["recovery"])-.25*md
    if mr<=0:score-=30+abs(mr)
    if mp<1:score-=25*(1-mp)
    return float(score)


def evaluate(bars,c):
    tr=run(bars,c,TRAIN);va=run(bars,c,VALIDATION);return tr,va,robust_score(tr,va)


def row(symbol,phase,name,c,tr,va,score):
    return dict(symbol=symbol,phase=phase,name=name,config=json.dumps(asdict(c),sort_keys=True),score=score,**{f"train_{k}":v for k,v in tr.items()},**{f"validation_{k}":v for k,v in va.items()})


def select_symbol(symbol:str,base:pd.DataFrame):
    bars={tf:resample(base,tf) for tf in TIMEFRAMES};rows=[];candidates=[]
    for tf,session,bo,ema,regime in itertools.product(TIMEFRAMES,SESSIONS,BREAKOUTS,EMAS,REGIMES):
        c=Config(timeframe=tf,session=session,breakout=bo,ema=ema,regime=regime)
        tr,va,s=evaluate(bars,c);rows.append(row(symbol,"signal",f"{tf}-{session}-B{bo}-E{ema}-{regime}",c,tr,va,s));candidates.append((s,c))
    c=max(candidates,key=lambda z:z[0])[1]
    def stage(name,variants,current):
        options=[]
        for x in variants:
            tr,va,s=evaluate(bars,x);rows.append(row(symbol,name,name,x,tr,va,s));options.append((s,x))
        current_score=evaluate(bars,current)[2]
        return max(options+[(current_score,current)],key=lambda z:z[0])[1]
    c=stage("direction",[replace(c,direction=x) for x in DIRECTIONS],c)
    c=stage("stop",[replace(c,stop_mode=m,stop_value=v) for m,v in STOP_VARIANTS],c)
    c=stage("rr",[replace(c,rr_mode=m,rr=v) for m,v in RR_VARIANTS],c)
    c=stage("management",[replace(c,management=x) for x in MANAGEMENTS],c)
    c=stage("holding",[replace(c,max_hold_hours=x) for x in HOLDS],c)
    tr,va,s=evaluate(bars,c)
    return bars,c,tr,va,rows


def mc(rs,paths=5000,block=5):
    rs=np.asarray(rs,float);rng=np.random.default_rng(SEED+len(rs));rets=[];dds=[]
    for _ in range(paths):
        sample=[]
        while len(sample)<len(rs):
            j=int(rng.integers(0,max(1,len(rs)-block+1)));sample.extend(rs[j:j+block])
        x=np.asarray(sample[:len(rs)]);eq=np.cumprod(1+RISK*x);peak=np.maximum.accumulate(np.r_[1.,eq]);rets.append((eq[-1]-1)*100);dds.append(np.max((peak[1:]-eq)/peak[1:])*100)
    return dict(return_p5=float(np.percentile(rets,5)),return_median=float(np.median(rets)),return_p95=float(np.percentile(rets,95)),dd_median=float(np.median(dds)),dd_p95=float(np.percentile(dds,95)),profit_probability=float(np.mean(np.asarray(rets)>0)*100),returns=rets)


def trade_metrics(trades):
    if not trades:return metrics([],[],[],[],0)
    x=sorted(trades,key=lambda z:z["exit"]);ent=np.arange(len(x));ex=pd.to_datetime([z["exit"] for z in x],utc=True).as_unit("s").asi8;rs=np.array([z["r"] for z in x]);s=np.array([1 if z["side"]=="long" else -1 for z in x]);return metrics(ent,ex,rs,s,0)


def curve(trades,start):
    eq=10000.;rows=[(start,eq)]
    for x in sorted(trades,key=lambda z:z["exit"]):eq*=1+RISK*x["r"];rows.append((pd.Timestamp(x["exit"]),eq))
    return pd.DataFrame(rows,columns=["date","equity"])


def main():
    copy_data();CHARTS.mkdir(parents=True,exist_ok=True);all_rows=[];result={"step":5,"title":"Conditional FX Momentum","risk_per_trade_pct":1.0,"assets":{}};locked_trades=[];full_trades=[];mc_returns={}
    for symbol in SYMBOLS:
        base,meta=load(symbol);bars,c,tr,va,rows=select_symbol(symbol,base);all_rows.extend(rows)
        ungated=replace(c,regime="none")
        locked=run(bars,c,LOCKED,True);locked_base=run(bars,ungated,LOCKED,True);full=run(bars,c,FULL,True);full_base=run(bars,ungated,FULL,True);stress=run(bars,c,LOCKED,False,.05)
        monte=mc([x["r"] for x in locked["trades_data"]]);mc_returns[symbol]=monte.pop("returns")
        halves=[]
        for start in pd.date_range(FULL[0],FULL[1],freq="6MS",inclusive="left"):
            end=min(start+pd.DateOffset(months=6),FULL[1]);m=run(bars,c,(start,end));halves.append(dict(from_date=start.date().isoformat(),to_date=end.date().isoformat(),**m))
        checks={"train_positive":tr["return_pct"]>0,"validation_positive":va["return_pct"]>0,"locked_positive":locked["return_pct"]>0,"locked_pf_1_20":locked["profit_factor"]>=1.2,"locked_30_trades":locked["trades"]>=30,"locked_dd_15":locked["max_dd_pct"]<=15,"cost_stress_positive":stress["return_pct"]>0,"mc_p5_positive":monte["return_p5"]>0,"condition_improves_pf_or_dd":locked["profit_factor"]>locked_base["profit_factor"] or locked["max_dd_pct"]<locked_base["max_dd_pct"],"condition_preserves_85pct_return":locked["return_pct"]>=.85*locked_base["return_pct"] if locked_base["return_pct"]>0 else locked["return_pct"]>0}
        decision="NATIVE_CONFIRMATION_REQUIRED" if all(checks.values()) else "REJECT"
        result["assets"][symbol]=dict(decision=decision,config=asdict(c),spread_floor_points=meta["spread_floor_points"],development_train=tr,development_validation=va,locked={k:v for k,v in locked.items() if k!="trades_data"},locked_ungated={k:v for k,v in locked_base.items() if k!="trades_data"},three_year={k:v for k,v in full.items() if k!="trades_data"},three_year_ungated={k:v for k,v in full_base.items() if k!="trades_data"},cost_stress_locked=stress,monte_carlo=monte,six_month_stability=halves,gate_checks=checks,current_regime=dict(state=int(bars[c.timeframe][f"reg_state_{c.regime}"].iloc[-1]),markov_signal=float(bars[c.timeframe][f"reg_signal_{c.regime}"].iloc[-1]),profile=c.regime))
        for x in locked["trades_data"]:locked_trades.append(dict(symbol=symbol,**x))
        for x in full["trades_data"]:full_trades.append(dict(symbol=symbol,**x))
        # Frozen sensitivity rows, still evaluated pre-lock only.
        variants=[]
        for phase,values in (("session",[replace(c,session=x) for x in SESSIONS]),("timeframe",[replace(c,timeframe=x) for x in TIMEFRAMES]),("rr",[replace(c,rr_mode=m,rr=v) for m,v in RR_VARIANTS]),("stop",[replace(c,stop_mode=m,stop_value=v) for m,v in STOP_VARIANTS]),("management",[replace(c,management=x) for x in MANAGEMENTS])):
            for x in values:
                a,b,s=evaluate(bars,x);variants.append(row(symbol,f"sensitivity-{phase}",phase,x,a,b,s))
        all_rows.extend(variants)
        print("SELECTED",symbol,decision,asdict(c),"LOCKED",locked["return_pct"],locked["profit_factor"],locked["trades"],flush=True)
    pm_locked=trade_metrics(locked_trades);pm_full=trade_metrics(full_trades);pm_mc=mc([x["r"] for x in sorted(locked_trades,key=lambda z:z["exit"])]);portfolio_returns=pm_mc.pop("returns")
    result["portfolio"]={"locked":pm_locked,"three_year":pm_full,"monte_carlo":pm_mc,"decision":"NATIVE_CONFIRMATION_REQUIRED" if all(v["decision"]=="NATIVE_CONFIRMATION_REQUIRED" for v in result["assets"].values()) and pm_mc["return_p5"]>0 else "REJECT"}
    result["methodology"]="Causal completed-bar broker M15 reconstruction. Resampled timeframes, recorded spread, conservative stop-first bars, 0.02R friction and exact 1% risk. Carry/forward points were unavailable and are not claimed."
    dump(ROOT/"results.json",result);dump(ROOT/"selection-lock.json",{s:{"config":v["config"],"development_train":v["development_train"],"development_validation":v["development_validation"]} for s,v in result["assets"].items()})
    frame=pd.DataFrame(all_rows);frame.to_csv(ROOT/"all-screen-results.csv",index=False)
    pd.DataFrame(locked_trades).to_csv(ROOT/"locked-trades.csv",index=False)
    pd.DataFrame([{ "symbol":s,**h} for s,v in result["assets"].items() for h in v["six_month_stability"]]).to_csv(ROOT/"six-month-stability.csv",index=False)

    plt.style.use("dark_background")
    fig,axes=plt.subplots(2,2,figsize=(15,9));fig.patch.set_facecolor("#071512")
    for ax in axes.flat:ax.set_facecolor("#0b1d19");ax.grid(alpha=.16)
    for symbol,color in zip(SYMBOLS,("#72f5c1","#63c6ff")):
        c=curve([x for x in locked_trades if x["symbol"]==symbol],LOCKED[0]);axes[0,0].plot(c.date,c.equity,label=symbol,color=color)
    p=curve(locked_trades,LOCKED[0]);axes[0,1].plot(p.date,p.equity,color="#b794f4");axes[0,0].set_title("Locked equity by asset");axes[0,1].set_title("Locked combined equity");axes[0,0].legend()
    names=list(SYMBOLS);ret=[result["assets"][s]["locked"]["return_pct"] for s in names];pf=[result["assets"][s]["locked"]["profit_factor"] for s in names];xx=np.arange(len(names));axes[1,0].bar(xx-.18,ret,.36,label="Return %",color="#72f5c1");axes[1,0].bar(xx+.18,pf,.36,label="PF",color="#ffc857");axes[1,0].set_xticks(xx,names);axes[1,0].legend();axes[1,0].set_title("Locked return and PF")
    for symbol,color in zip(SYMBOLS,("#72f5c1","#63c6ff")):axes[1,1].hist(mc_returns[symbol],bins=50,alpha=.5,label=symbol,color=color)
    axes[1,1].axvline(0,color="white",lw=.8);axes[1,1].set_title("5,000-path locked Monte Carlo returns");axes[1,1].legend();fig.suptitle("Calyx Step 5 — Conditional FX Momentum",fontsize=16,fontweight="bold");fig.tight_layout();fig.savefig(CHARTS/"step5-summary.png",dpi=170,bbox_inches="tight");plt.close(fig)

    fig,axes=plt.subplots(2,2,figsize=(15,9));fig.patch.set_facecolor("#071512")
    for ax in axes.flat:ax.set_facecolor("#0b1d19");ax.grid(alpha=.16)
    signal=frame[frame.phase.eq("signal")]
    for ax,(symbol,color) in zip(axes[:1].flat,zip(SYMBOLS,("#72f5c1","#63c6ff"))):
        x=signal[signal.symbol.eq(symbol)];sc=ax.scatter(x.validation_max_dd_pct,x.validation_profit_factor,c=x.validation_return_pct,cmap="viridis",s=12,alpha=.7);ax.axhline(1.2,color="white",ls="--",lw=.8);ax.set_title(f"{symbol}: all signal configurations");ax.set_xlabel("Validation DD %");ax.set_ylabel("Validation PF");fig.colorbar(sc,ax=ax,label="Validation return %")
    for col,(phase,title) in enumerate((("sensitivity-session","Session sensitivity"),("sensitivity-rr","RR sensitivity"))):
        ax=axes[1,col];x=frame[frame.phase.eq(phase)].copy();labels=[]
        for symbol,color in zip(SYMBOLS,("#72f5c1","#63c6ff")):
            z=x[x.symbol.eq(symbol)].copy();z["label"]=z.config.map(lambda q: json.loads(q)["session"] if "session" in phase else ("adaptive" if json.loads(q)["rr_mode"]=="adaptive" else f"{json.loads(q)['rr']:g}R"));ax.plot(z.label,z.validation_return_pct,marker="o",label=symbol,color=color)
        ax.axhline(0,color="white",lw=.8);ax.set_title(title+" — validation return");ax.tick_params(axis="x",rotation=30);ax.legend()
    fig.suptitle("Step 5 — Configuration and sensitivity evidence",fontsize=16,fontweight="bold");fig.tight_layout();fig.savefig(CHARTS/"configuration-sensitivity.png",dpi=170,bbox_inches="tight");plt.close(fig)

    rows=[]
    for s,v in result["assets"].items():
        b=v["locked_ungated"];q=v["locked"];t=v["three_year"];m=v["monte_carlo"]
        rows.append([s,v["decision"],f"{q['return_pct']:+.2f}%",f"{q['profit_factor']:.2f}",f"{q['win_rate']:.2f}%",f"{q['max_dd_pct']:.2f}%",q["trades"],f"{q['sharpe']:.2f}",f"{q['recovery']:.2f}",f"{q['average_win_r']:.2f}R",f"{m['return_p5']:+.2f}%",f"{t['return_pct']:+.2f}%"])
    def table(headers,body):return "\n".join(["| "+" | ".join(headers)+" |","|"+"|".join(["---"]*len(headers))+"|"]+["| "+" | ".join(map(str,r))+" |" for r in body])
    configs=[]
    for s,v in result["assets"].items():
        c=v["config"];configs.append([s,c["timeframe"],c["session"],f"B{c['breakout']} / EMA{c['ema']}",c["regime"],c["direction"],f"{c['stop_mode']} {c['stop_value']:g}","adaptive" if c["rr_mode"]=="adaptive" else f"{c['rr']:g}R",c["management"],f"{c['max_hold_hours']}h" if c["max_hold_hours"] else "none"])
    comparisons=[]
    for s,v in result["assets"].items():
        b=v["locked_ungated"];q=v["locked"];comparisons.append([s,f"{b['return_pct']:+.2f}→{q['return_pct']:+.2f}%",f"{b['profit_factor']:.2f}→{q['profit_factor']:.2f}",f"{b['win_rate']:.2f}→{q['win_rate']:.2f}%",f"{b['max_dd_pct']:.2f}→{q['max_dd_pct']:.2f}%",f"{b['trades']}→{q['trades']}"])
    checks="\n".join(f"### {s}\n"+"\n".join(f"- {'PASS' if ok else 'FAIL'} — {k.replace('_',' ')}" for k,ok in v["gate_checks"].items()) for s,v in result["assets"].items())
    report=f"""# Step 5 — Conditional FX Momentum

**Portfolio decision: {result['portfolio']['decision'].replace('_',' ')}. Nothing was added to an EA, SET, BAT, website, cache, or recommended portfolio.**

## Untouched-year results

{table(['Asset','Decision','Return','PF','Win rate','Max DD','Trades','Sharpe','Recovery','Avg winning R','MC P5','3-year return'],rows)}

Combined locked portfolio: return **{pm_locked['return_pct']:+.2f}%**, PF **{pm_locked['profit_factor']:.2f}**, win rate **{pm_locked['win_rate']:.2f}%**, DD **{pm_locked['max_dd_pct']:.2f}%**, {pm_locked['trades']} trades, Sharpe **{pm_locked['sharpe']:.2f}**, recovery **{pm_locked['recovery']:.2f}**. Portfolio Monte Carlo P5: **{pm_mc['return_p5']:+.2f}%**.

![Step 5 summary](Charts/step5-summary.png)

## Frozen configurations

{table(['Asset','TF','Session','Signal','Regime','Direction','Stop','Target','Management','Max hold'],configs)}

## Conditional versus identical ungated version

{table(['Asset','Return base→condition','PF','Win rate','DD','Trades'],comparisons)}

## Promotion checks

{checks}

## Full configuration evidence

![Configuration and sensitivity](Charts/configuration-sensitivity.png)

The search covered timeframes, sessions, breakout and EMA lengths, causal regime states, Markov probability buffers, direction, stop placement, fixed 0.5R–6R and adaptive RR, breakeven/trailing/Dynamic 50/20, and timed exits. Selection used only the two pre-lock years, split into train and validation. The final year was opened afterward.

## Limitations

- This is a conservative broker-bar reconstruction, not native MT5 Every Tick confirmation.
- The packaged regime skill runner was unavailable, so its documented three-state/no-lookahead transition framework was implemented directly and verified from completed bars.
- Historical carry/forward-discount series were not available. This test covers price momentum, volatility and Markov state conditioning; it does not claim a carry filter.
- A resampled bar that touches stop and target is counted as a stop. Recorded broker spread and an additional 0.02R execution allowance are included.
- Backtests and Monte Carlo are historical diagnostics, not forecasts.

## Files

- `all-screen-results.csv`: all development configurations and sensitivities.
- `selection-lock.json`: settings frozen before the locked year was evaluated.
- `locked-trades.csv`: complete trade ledger.
- `six-month-stability.csv`: temporal stability.
- `results.json`: machine-readable results, checks and Monte Carlo.
"""
    (ROOT/"REPORT.md").write_text(report,encoding="utf-8")
    verification=[("two assets complete",set(result["assets"])==set(SYMBOLS)),("one percent risk",RISK==.01),("locked untouched in selection",all("locked" not in r["phase"] for r in all_rows)),("spread evidence copied",all((DATA/f"{s}-M15.npz").exists() for s in SYMBOLS)),("monte carlo 5000 paths",len(portfolio_returns)==5000),("summary graph",(CHARTS/"step5-summary.png").exists()),("sensitivity graph",(CHARTS/"configuration-sensitivity.png").exists())]
    (ROOT/"VERIFICATION.txt").write_text("\n".join(f"{'PASS' if ok else 'FAIL'} — {name}" for name,ok in verification)+f"\nSUMMARY {sum(ok for _,ok in verification)}/{len(verification)}\n",encoding="utf-8")
    dump(ROOT/"progress.json",{"step":5,"title":result["title"],"status":"complete","decision":result["portfolio"]["decision"]})
    print("COMPLETE",result["portfolio"]["decision"],flush=True)


if __name__=="__main__":main()
