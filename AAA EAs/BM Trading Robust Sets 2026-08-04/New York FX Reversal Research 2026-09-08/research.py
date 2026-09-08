"""Full pipeline for LeBaron and Zhao's hourly New York FX reversal paper."""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
import itertools
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from numba import njit


ROOT = Path(__file__).resolve().parent
SHARED_DATA = ROOT.parent / "Intraday FX Session Effect Research 2026-09-08" / "Data"
CHARTS = ROOT / "Charts"
SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "EURJPY")
TIMEFRAMES = {"M15": ("15min", 15), "M30": ("30min", 30), "H1": ("1h", 60)}
SESSIONS = ("ny-08-13", "ny-09-14", "ny-10-15-paper", "ny-10-16", "ny-11-16", "ny-08-16", "fixed-est-10-15")
MA_LENGTHS = (4, 5, 6, 7, 8, 9, 10, 11, 12, 16, 24)
DEVIATIONS = (0.00, 0.05, 0.10, 0.25, 0.50)
CONFIRMATIONS = ("none", "normal-vol", "low-vol", "relative-volume")
DIRECTIONS = ("reversal", "inverse-trend", "long-only", "short-only")
STOPS = tuple(("atr", x) for x in (0.50, 0.75, 1.00, 1.25, 1.50, 2.00, 3.00, 4.00)) + (("swing", 8.0), ("swing", 16.0))
TARGETS = tuple(("fixed", x) for x in (0.50, 0.75, 1.00, 1.50, 2.00, 3.00, 4.00)) + (("signal-flip", 0.0), ("session-close", 0.0), ("adaptive", 0.0))
MANAGEMENTS = ("none", "breakeven", "atr-trail", "dynamic-50-20")
HOLDS = (1, 2, 4, 8, 0)
WEEKDAYS = ("all", "no-monday", "no-friday", "tue-thu")
TRAIN = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2024-09-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (TRAIN[0], LOCKED[1])
RISK = 0.01
SPREAD_FLOOR_PIPS = 0.60
COMMISSION_SLIPPAGE_PIPS = 0.40
SEED = 8092602


@dataclass(frozen=True)
class Config:
    timeframe: str = "H1"
    session: str = "ny-10-15-paper"
    ma_length: int = 6
    deviation_atr: float = 0.0
    confirmation: str = "none"
    direction: str = "reversal"
    stop_mode: str = "atr"
    stop_value: float = 1.50
    target_mode: str = "signal-flip"
    rr: float = 0.0
    management: str = "none"
    max_hold_hours: int = 0
    weekdays: str = "all"


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def load(symbol: str) -> tuple[pd.DataFrame, dict]:
    metadata = json.loads((SHARED_DATA / "metadata.json").read_text(encoding="utf-8"))["symbols"][symbol]
    rates = np.load(SHARED_DATA / f"{symbol}-M15.npz")["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    frame = pd.DataFrame({k: rates[k].astype(float) for k in ("open", "high", "low", "close", "tick_volume", "spread")}, index=index)
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    pip = float(metadata["point"])*10.0
    frame["spread_price"] = np.maximum(frame.spread*float(metadata["point"]), SPREAD_FLOOR_PIPS*pip)
    return frame, metadata | {"pip": pip}


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous = frame.close.shift(1)
    return pd.concat(((frame.high-frame.low), (frame.high-previous).abs(), (frame.low-previous).abs()), axis=1).max(axis=1)


def resample(base: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if timeframe == "M15":
        bars = base.copy(); bars["volume"] = bars.tick_volume
    else:
        bars = base.resample(TIMEFRAMES[timeframe][0], label="left", closed="left").agg(open=("open","first"), high=("high","max"), low=("low","min"), close=("close","last"), volume=("tick_volume","sum"), spread_price=("spread_price","last")).dropna()
    bars["atr"] = true_range(bars).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    bars["atr_ratio"] = bars.atr/bars.atr.rolling(20, min_periods=10).median()
    bars["volume_ratio"] = bars.volume/bars.volume.rolling(20, min_periods=10).median().replace(0,np.nan)
    for length in MA_LENGTHS:
        bars[f"sma_{length}"] = bars.close.rolling(length, min_periods=length).mean()
    for length in (8,16):
        bars[f"swing_low_{length}"] = bars.low.rolling(length, min_periods=length).min().shift(1)
        bars[f"swing_high_{length}"] = bars.high.rolling(length, min_periods=length).max().shift(1)
    return bars.dropna(subset=["atr"])


def session_active(index: pd.DatetimeIndex, session: str, weekdays: str) -> np.ndarray:
    if session == "fixed-est-10-15":
        active = (index.hour >= 15) & (index.hour < 20)
    else:
        local = index.tz_convert("America/New_York")
        label = session.removeprefix("ny-")
        start, end = (int(x) for x in label.replace("-paper","").split("-")[:2])
        active = (local.hour >= start) & (local.hour < end)
    day = index.weekday
    if weekdays == "no-monday": day_ok = day != 0
    elif weekdays == "no-friday": day_ok = day != 4
    elif weekdays == "tue-thu": day_ok = (day >= 1) & (day <= 3)
    else: day_ok = day < 5
    return np.asarray(active & day_ok, dtype=np.int8)


def arrays(bars: pd.DataFrame, config: Config) -> dict:
    swing = int(config.stop_value) if config.stop_mode == "swing" else 8
    return {
        "time": bars.index.as_unit("s").asi8.astype(np.int64), "open": bars.open.to_numpy(float), "high": bars.high.to_numpy(float), "low": bars.low.to_numpy(float), "close": bars.close.to_numpy(float),
        "spread": bars.spread_price.to_numpy(float), "atr": bars.atr.to_numpy(float), "atr_ratio": bars.atr_ratio.fillna(99).to_numpy(float), "volume_ratio": bars.volume_ratio.fillna(0).to_numpy(float),
        "sma": bars[f"sma_{config.ma_length}"].to_numpy(float), "swing_low": bars[f"swing_low_{swing}"].to_numpy(float), "swing_high": bars[f"swing_high_{swing}"].to_numpy(float),
        "active": session_active(bars.index,config.session,config.weekdays), "day_key": np.asarray(bars.index.year*10000+bars.index.month*100+bars.index.day,dtype=np.int32),
    }


@njit(cache=True)
def engine(time,op,hi,lo,cl,spr,atr,atr_ratio,volume_ratio,sma,swing_low,swing_high,active,day_key,start_ts,end_ts,deviation_atr,confirmation,direction,stop_mode,stop_value,target_mode,rr,management,max_hold_seconds,commission_price,extra_cost_price):
    n=len(time);cap=n//2+10;entries=np.empty(cap,np.int64);exits=np.empty(cap,np.int64);results=np.empty(cap,np.float64);sides=np.empty(cap,np.int8);stops_out=np.empty(cap,np.float64);count=0
    pos=0;entry=0.;initial=0.;stop=0.;target=0.;entry_i=0;previous_active=0
    for i in range(2,n):
        if time[i]<start_ts:previous_active=active[i];continue
        if time[i]>=end_ts:break
        p=i-1;signal=0
        if active[i]==1 and np.isfinite(sma[p]) and np.isfinite(atr[p]) and atr[p]>0:
            deviation=(cl[p]-sma[p])/atr[p]
            if abs(deviation)>=deviation_atr:
                signal=-1 if deviation>0 else (1 if deviation<0 else 0)
            if direction==1:signal=-signal
            elif direction==2 and signal<0:signal=0
            elif direction==3 and signal>0:signal=0
            if confirmation==1 and atr_ratio[p]>1.5:signal=0
            elif confirmation==2 and atr_ratio[p]>1.0:signal=0
            elif confirmation==3 and volume_ratio[p]<1.0:signal=0
        must_close=False
        if pos!=0:
            if active[i]==0:must_close=True
            elif max_hold_seconds>0 and time[i]-time[entry_i]>=max_hold_seconds:must_close=True
            elif target_mode==1 and signal!=0 and signal!=pos:must_close=True
        if must_close:
            px=op[i] if pos>0 else op[i]+spr[i];result=pos*(px-entry)/initial-(commission_price+extra_cost_price)/initial
            entries[count]=time[entry_i];exits[count]=time[i];results[count]=result;sides[count]=pos;stops_out[count]=initial;count+=1;pos=0
        if pos==0 and active[i]==1 and signal!=0:
            ent=op[i]+spr[i] if signal>0 else op[i]
            if stop_mode==0:distance=stop_value*atr[p]
            else:
                raw=ent-swing_low[p] if signal>0 else swing_high[p]+spr[p]-ent
                distance=max(.5*atr[p],min(4*atr[p],raw+.1*atr[p]))
            if np.isfinite(distance) and distance>2*spr[i]:
                pos=signal;entry=ent;initial=distance;stop=entry-pos*distance;entry_i=i
                effective_rr=rr
                if target_mode==3:effective_rr=2.0 if atr_ratio[p]<=1.0 else .75
                target=entry+pos*effective_rr*distance
        if pos!=0:
            hit=0;px=0.
            if pos>0:
                if lo[i]<=stop:hit=1;px=stop
                elif target_mode in (0,3) and hi[i]>=target:hit=2;px=target
            else:
                if hi[i]+spr[i]>=stop:hit=1;px=stop
                elif target_mode in (0,3) and lo[i]+spr[i]<=target:hit=2;px=target
            if hit:
                result=pos*(px-entry)/initial-(commission_price+extra_cost_price)/initial
                entries[count]=time[entry_i];exits[count]=time[i];results[count]=result;sides[count]=pos;stops_out[count]=initial;count+=1;pos=0
            else:
                progress=pos*(cl[i]+(spr[i] if pos<0 else 0.)-entry)/initial
                if management==1 and progress>=1.:stop=max(stop,entry) if pos>0 else min(stop,entry)
                elif management==2 and progress>=1.:
                    candidate=cl[i]-1.5*atr[i] if pos>0 else cl[i]+spr[i]+1.5*atr[i];stop=max(stop,candidate) if pos>0 else min(stop,candidate)
                elif management==3 and progress>=.5:
                    candidate=entry+pos*.2*initial;stop=max(stop,candidate) if pos>0 else min(stop,candidate)
        previous_active=active[i]
    if pos!=0:
        i=min(n-1,np.searchsorted(time,end_ts)-1);px=cl[i] if pos>0 else cl[i]+spr[i];result=pos*(px-entry)/initial-(commission_price+extra_cost_price)/initial;entries[count]=time[entry_i];exits[count]=time[i];results[count]=result;sides[count]=pos;stops_out[count]=initial;count+=1
    return entries[:count],exits[:count],results[:count],sides[:count],stops_out[:count]


CONFIRM_CODE={"none":0,"normal-vol":1,"low-vol":2,"relative-volume":3};DIRECTION_CODE={"reversal":0,"inverse-trend":1,"long-only":2,"short-only":3};STOP_CODE={"atr":0,"swing":1};TARGET_CODE={"fixed":0,"signal-flip":1,"session-close":2,"adaptive":3};MAN_CODE={"none":0,"breakeven":1,"atr-trail":2,"dynamic-50-20":3}


def metrics(entries,exits,rs,sides,stop_distances,pip,collect=False):
    rs=np.asarray(rs,float)
    if not len(rs):return {"return_pct":0.,"profit_factor":0.,"win_rate":0.,"max_dd_pct":0.,"trades":0,"sharpe":0.,"recovery":0.,"expectancy_r":0.,"average_rr":0.,"max_win_streak":0,"max_loss_streak":0}
    equity=np.r_[1.,np.cumprod(np.maximum(.01,1+RISK*rs))];pnl=np.diff(equity);gp=pnl[pnl>0].sum();gl=-pnl[pnl<0].sum();peak=np.maximum.accumulate(equity);dd=float(np.max(1-equity/peak)*100);idx=pd.to_datetime(exits,unit="s",utc=True);daily=pd.Series(RISK*rs,index=idx).groupby(level=0).sum().resample("1D").sum();sd=daily.std(ddof=1);sharpe=float(daily.mean()/sd*math.sqrt(252)) if sd>0 else 0.;mw=ml=cw=closs=0
    for value in rs:
        if value>0:cw+=1;closs=0
        elif value<0:closs+=1;cw=0
        else:cw=closs=0
        mw=max(mw,cw);ml=max(ml,closs)
    result={"return_pct":float((equity[-1]-1)*100),"profit_factor":float(min(99,gp/gl if gl else 99)),"win_rate":float(np.mean(rs>0)*100),"max_dd_pct":dd,"trades":int(len(rs)),"sharpe":sharpe,"recovery":float(((equity[-1]-1)*100)/dd if dd else 0),"expectancy_r":float(rs.mean()),"average_rr":float(rs[rs>0].mean() if np.any(rs>0) else 0),"max_win_streak":mw,"max_loss_streak":ml}
    if collect:result["trades_data"]=[{"entry":pd.Timestamp(int(e),unit="s",tz="UTC").isoformat(),"exit":pd.Timestamp(int(x),unit="s",tz="UTC").isoformat(),"r":float(r),"side":"long" if s>0 else "short","stop_pips":float(d/pip)} for e,x,r,s,d in zip(entries,exits,rs,sides,stop_distances)]
    return result


def run(bars,meta,c,period,collect=False,extra_cost_pips=0.):
    a=arrays(bars[c.timeframe],c);args=[a[x] for x in ("time","open","high","low","close","spread","atr","atr_ratio","volume_ratio","sma","swing_low","swing_high","active","day_key")];pip=float(meta["pip"])
    e,x,r,s,d=engine(*args,int(period[0].timestamp()),int(period[1].timestamp()),c.deviation_atr,CONFIRM_CODE[c.confirmation],DIRECTION_CODE[c.direction],STOP_CODE[c.stop_mode],c.stop_value,TARGET_CODE[c.target_mode],c.rr,MAN_CODE[c.management],c.max_hold_hours*3600,COMMISSION_SLIPPAGE_PIPS*pip,extra_cost_pips*pip)
    return metrics(e,x,r,s,d,pip,collect)


def score(train,validation):
    if train["trades"]<50 or validation["trades"]<50:return -10000+train["trades"]+validation["trades"]
    mr=min(train["return_pct"],validation["return_pct"]);mp=min(train["profit_factor"],validation["profit_factor"]);ms=min(train["sharpe"],validation["sharpe"]);md=max(train["max_dd_pct"],validation["max_dd_pct"]);value=.35*mr+12*math.log(max(.05,min(3,mp)))+1.5*ms+min(train["recovery"],validation["recovery"])-.25*md
    if mr<=0:value-=35+abs(mr)
    if mp<1:value-=30*(1-mp)
    return float(value)


def evaluate(bars,meta,c):
    tr=run(bars,meta,c,TRAIN);va=run(bars,meta,c,VALIDATION);return tr,va,score(tr,va)


def stage(bars,meta,configs,width=20):
    seen=set();ranked=[];audit=[]
    for c in configs:
        key=tuple(asdict(c).values())
        if key in seen:continue
        seen.add(key);tr,va,s=evaluate(bars,meta,c);ranked.append((s,c));audit.append({"config":asdict(c),"score":s,"train":tr,"validation":va})
    ranked.sort(key=lambda x:x[0],reverse=True);return [c for _,c in ranked[:width]],audit


def neighbours(c):
    mas=sorted(set([max(4,c.ma_length-1),c.ma_length,min(24,c.ma_length+1)]));devs=sorted(set([max(0,c.deviation_atr-.05),c.deviation_atr,min(.5,c.deviation_atr+.05)]));stops=sorted(set([max(.5,c.stop_value-.25),c.stop_value,min(4,c.stop_value+.25)])) if c.stop_mode=="atr" else [c.stop_value];rrs=sorted(set([max(.5,c.rr-.25),c.rr,min(4,c.rr+.25)])) if c.target_mode=="fixed" else [c.rr]
    return [replace(c,ma_length=ma,deviation_atr=dev,stop_value=stop,rr=rr) for ma,dev,stop,rr in itertools.product(mas,devs,stops,rrs)]


def select(symbol,base,meta):
    bars={tf:resample(base,tf) for tf in TIMEFRAMES};audits=[];initial=[Config(timeframe=tf,session=session,ma_length=ma,deviation_atr=dev,confirmation=confirm) for tf,session,ma,dev,confirm in itertools.product(TIMEFRAMES,SESSIONS,MA_LENGTHS,DEVIATIONS,CONFIRMATIONS)]
    print(f"  {symbol}: timeframe/session/MA/deviation ({len(initial)} configs)",flush=True);beam,a=stage(bars,meta,initial);audits += [{"stage":"signal",**x} for x in a]
    print(f"  {symbol}: direction",flush=True);beam,a=stage(bars,meta,[replace(c,direction=x) for c in beam for x in DIRECTIONS]);audits += [{"stage":"direction",**x} for x in a]
    print(f"  {symbol}: dynamic stops",flush=True);beam,a=stage(bars,meta,[replace(c,stop_mode=m,stop_value=v) for c in beam for m,v in STOPS]);audits += [{"stage":"stop",**x} for x in a]
    print(f"  {symbol}: RR/signal exits",flush=True);beam,a=stage(bars,meta,[replace(c,target_mode=m,rr=v) for c in beam for m,v in TARGETS]);audits += [{"stage":"target",**x} for x in a]
    print(f"  {symbol}: management/hold/weekdays",flush=True);beam,a=stage(bars,meta,[replace(c,management=m,max_hold_hours=h,weekdays=w) for c in beam for m,h,w in itertools.product(MANAGEMENTS,HOLDS,WEEKDAYS)]);audits += [{"stage":"management",**x} for x in a]
    selected=beam[0];tr,va,s=evaluate(bars,meta,selected);locked=run(bars,meta,selected,LOCKED,True);stress=run(bars,meta,selected,LOCKED,False,1.0);full=run(bars,meta,selected,FULL,True)
    neighbour_rows=[]
    for nc in neighbours(selected):
        result=run(bars,meta,nc,LOCKED);neighbour_rows.append({"config":asdict(nc),"metrics":result})
    stability={"tested":len(neighbour_rows),"profitable_pct":float(100*np.mean([x["metrics"]["return_pct"]>0 for x in neighbour_rows])),"median_return_pct":float(np.median([x["metrics"]["return_pct"] for x in neighbour_rows])),"median_profit_factor":float(np.median([x["metrics"]["profit_factor"] for x in neighbour_rows])),"rows":neighbour_rows}
    return {"symbol":symbol,"selected":asdict(selected),"selection_score":s,"train":tr,"validation":va,"locked":locked,"locked_cost_stress":stress,"full":full,"neighbour_stability":stability,"audit":audits}


def monte_carlo(trades,paths=5000,block=5):
    rs=np.array([x["r"] for x in trades],float);rng=np.random.default_rng(SEED+len(rs));rets=[];dds=[]
    if not len(rs):return {"paths":paths,"return_p5":-100.,"return_median":-100.,"dd_p95":100.,"profit_probability":0.}
    for _ in range(paths):
        sample=[]
        while len(sample)<len(rs):j=int(rng.integers(0,max(1,len(rs)-block+1)));sample.extend(rs[j:j+block])
        eq=np.cumprod(np.maximum(.01,1+RISK*np.array(sample[:len(rs)])));peak=np.maximum.accumulate(np.r_[1.,eq])[1:];rets.append((eq[-1]-1)*100);dds.append(np.max(1-eq/peak)*100)
    return {"paths":paths,"return_p5":float(np.percentile(rets,5)),"return_median":float(np.median(rets)),"return_p95":float(np.percentile(rets,95)),"dd_median":float(np.median(dds)),"dd_p95":float(np.percentile(dds,95)),"profit_probability":float(np.mean(np.array(rets)>0)*100)}


def gate(row):
    failures=[]
    for p in ("train","validation","locked","locked_cost_stress"):
        if row[p]["return_pct"]<=0:failures.append(f"{p} return <= 0")
    if row["locked"]["profit_factor"]<1.2:failures.append("locked PF < 1.20")
    if row["locked"]["trades"]<80:failures.append("locked trades < 80")
    if row["locked"]["max_dd_pct"]>15:failures.append("locked DD > 15%")
    if row["monte_carlo"]["return_p5"]<=0:failures.append("Monte Carlo P5 <= 0")
    if row["neighbour_stability"]["profitable_pct"]<60:failures.append("fewer than 60% profitable neighbours")
    return not failures,failures


def chart(row):
    eq=10000.;xs=[FULL[0]];ys=[eq]
    for t in sorted(row["full"]["trades_data"],key=lambda x:x["exit"]):eq*=max(.01,1+RISK*t["r"]);xs.append(pd.Timestamp(t["exit"]));ys.append(eq)
    CHARTS.mkdir(parents=True,exist_ok=True);fig,ax=plt.subplots(figsize=(12,5));fig.patch.set_facecolor("#07110f");ax.set_facecolor("#07110f");ax.plot(xs,ys,color="#55b6ff");ax.axvline(VALIDATION[0],color="#74f5ca",ls="--");ax.axvline(LOCKED[0],color="#f2c14e",ls="--");ax.set_title(f"{row['symbol']} New York reversal",color="white");ax.tick_params(colors="#a9c8bf");ax.grid(alpha=.15);fig.tight_layout();fig.savefig(CHARTS/f"{row['symbol'].lower()}-equity.png",dpi=150);plt.close(fig)


def research_symbol(symbol):
    print(f"Researching {symbol}...",flush=True);base,meta=load(symbol);row=select(symbol,base,meta);row["monte_carlo"]=monte_carlo(row["locked"]["trades_data"]);row["promoted"],row["gate_failures"]=gate(row);chart(row);return row


def report(payload):
    lines=["# New York FX Reversal — Full Pipeline Report","","Research only. No deployment changes were made.","","| Pair | Train Ret/PF/WR | Validation Ret/PF/WR | Locked Ret/PF/WR | DD | Sharpe | Recovery | Trades | Stress PF | MC P5 | Neighbours profitable | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in payload["results"]:
        t,v,l,s,m,n=r["train"],r["validation"],r["locked"],r["locked_cost_stress"],r["monte_carlo"],r["neighbour_stability"]
        lines.append(f"| {r['symbol']} | {t['return_pct']:+.2f}%/{t['profit_factor']:.2f}/{t['win_rate']:.2f}% | {v['return_pct']:+.2f}%/{v['profit_factor']:.2f}/{v['win_rate']:.2f}% | {l['return_pct']:+.2f}%/{l['profit_factor']:.2f}/{l['win_rate']:.2f}% | {l['max_dd_pct']:.2f}% | {l['sharpe']:.2f} | {l['recovery']:.2f} | {l['trades']} | {s['profit_factor']:.2f} | {m['return_p5']:+.2f}% | {n['profitable_pct']:.1f}% | {'PASS' if r['promoted'] else 'FAIL'} |")
    lines += ["","## Configurations and decisions",""]
    for r in payload["results"]:lines += [f"### {r['symbol']}","",f"- Selected before locked reveal: `{json.dumps(r['selected'],sort_keys=True)}`",f"- **{'PASS' if r['promoted'] else 'FAIL'}** — {', '.join(r['gate_failures']) if r['gate_failures'] else 'all research gates passed; native Every Tick confirmation remains required'}",""]
    return "\n".join(lines)


def main():
    partial=ROOT/"partial-results.json";results=json.loads(partial.read_text(encoding="utf-8"))["results"] if partial.exists() else [];completed={r["symbol"] for r in results};todo=[s for s in SYMBOLS if s not in completed]
    with ProcessPoolExecutor(max_workers=min(3,len(todo) or 1)) as pool:
        futures={pool.submit(research_symbol,s):s for s in todo}
        for future in as_completed(futures):row=future.result();results.append(row);results.sort(key=lambda x:SYMBOLS.index(x["symbol"]));dump(partial,{"results":results})
    metadata=json.loads((SHARED_DATA/"metadata.json").read_text(encoding="utf-8"));payload={"strategy":"LeBaron-Zhao New York hourly FX reversal","source":"https://people.brandeis.edu/~blebaron/wps/fxnyc.pdf","generated_at":datetime.now(timezone.utc).isoformat(),"risk_per_trade_pct":1.0,"broker":metadata,"results":results};dump(ROOT/"results.json",payload);(ROOT/"FULL REPORT.md").write_text(report(payload),encoding="utf-8");print(report(payload));return 0


if __name__=="__main__":raise SystemExit(main())
