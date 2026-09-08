"""Full no-lookahead engineering pipeline for the weekend-gap reversal paper."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import itertools
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import MetaTrader5 as mt5
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
SHARED_DATA = ROOT.parent / "Intraday FX Session Effect Research 2026-09-08" / "Data"
DATA = ROOT / "Pipeline Data"
CHARTS = ROOT / "Pipeline Charts"
TERMINAL = Path(r"C:\Program Files\JustMarkets MetaTrader 5\terminal64.exe")
SYMBOLS = ("EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "EURJPY")
TIMEFRAMES = {"M15": "15min", "M30": "30min", "H1": "1h"}
TRAIN = (pd.Timestamp("2023-09-01", tz="UTC"), pd.Timestamp("2024-09-01", tz="UTC"))
VALIDATION = (pd.Timestamp("2024-09-01", tz="UTC"), pd.Timestamp("2025-09-01", tz="UTC"))
LOCKED = (pd.Timestamp("2025-09-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
FULL = (TRAIN[0], LOCKED[1])
RISK = 0.01
SPREAD_FLOOR_PIPS = 0.60
COMMISSION_SLIPPAGE_PIPS = 0.40
SEED = 8092601
ROLLING = (52, 104, 156, 260)
TAILS = (2.5, 5.0, 7.5, 10.0, 15.0)
DELAYS = (0, 1, 2, 4, 8, 12)
CONFIRMATIONS = ("none", "first-bar-reversal", "first-bar-momentum", "ema50", "normal-vol", "rel-volume")
DIRECTIONS = ("paper", "inverse", "long-only", "short-only")
STOPS = tuple(("atr", x) for x in (0.50, 0.75, 1.00, 1.25, 1.50, 2.00, 3.00, 4.00)) + tuple(("gap", x) for x in (1.0, 1.5, 2.0)) + (("swing", 16.0),)
TARGETS = tuple(("fixed", x) for x in (0.50, 0.75, 1.00, 1.50, 2.00, 3.00, 4.00)) + (("timed", 0.0), ("gap-fill", 0.0), ("adaptive", 0.0))
MANAGEMENTS = ("none", "breakeven", "atr-trail", "dynamic-50-20")
HOLDS = (24, 48, 72, 120, 0)
_SIGNAL_CACHE: dict[tuple[str, int, float], list[dict]] = {}


@dataclass(frozen=True)
class Config:
    timeframe: str = "M15"
    rolling_weeks: int = 260
    tail_percent: float = 5.0
    delay_hours: int = 0
    confirmation: str = "none"
    direction: str = "paper"
    stop_mode: str = "atr"
    stop_value: float = 1.50
    target_mode: str = "timed"
    rr: float = 0.0
    management: str = "none"
    max_hold_hours: int = 0


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def resolve(canonical: str, names: list[str]) -> str:
    matches = [name for name in names if name.upper() == canonical or name.upper().startswith(canonical)]
    if not matches: raise RuntimeError(f"No broker symbol for {canonical}")
    return min(matches, key=len)


def prepare_weekly() -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    metadata_path = DATA / "metadata.json"
    if metadata_path.exists() and all((DATA / f"{s}-W1.npz").exists() for s in SYMBOLS):
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    if not mt5.initialize(path=str(TERMINAL)): raise RuntimeError(f"MT5 init failed: {mt5.last_error()}")
    try:
        names = [s.name for s in (mt5.symbols_get() or ())]
        metadata = {"downloaded_at": datetime.now(timezone.utc).isoformat(), "terminal": str(TERMINAL), "symbols": {}}
        for canonical in SYMBOLS:
            actual = resolve(canonical, names)
            mt5.symbol_select(actual, True)
            rates = mt5.copy_rates_from_pos(actual, mt5.TIMEFRAME_W1, 0, 900)
            if rates is None or len(rates) < 420: raise RuntimeError(f"Insufficient W1 data for {actual}")
            np.savez_compressed(DATA / f"{canonical}-W1.npz", rates=rates)
            metadata["symbols"][canonical] = {"broker_symbol": actual, "bars": int(len(rates)), "from": datetime.fromtimestamp(int(rates[0]["time"]), timezone.utc).isoformat(), "to": datetime.fromtimestamp(int(rates[-1]["time"]), timezone.utc).isoformat()}
        dump(metadata_path, metadata)
        return metadata
    finally:
        mt5.shutdown()


def load(canonical: str) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    shared_meta = json.loads((SHARED_DATA / "metadata.json").read_text(encoding="utf-8"))["symbols"][canonical]
    rates = np.load(SHARED_DATA / f"{canonical}-M15.npz")["rates"]
    index = pd.to_datetime(rates["time"], unit="s", utc=True)
    base = pd.DataFrame({k: rates[k].astype(float) for k in ("open", "high", "low", "close", "tick_volume", "spread")}, index=index)
    base = base[~base.index.duplicated(keep="last")].sort_index()
    pip = float(shared_meta["point"])*10.0
    base["spread_price"] = np.maximum(base.spread*float(shared_meta["point"]), SPREAD_FLOOR_PIPS*pip)
    weekly_rates = np.load(DATA / f"{canonical}-W1.npz")["rates"]
    weekly_index = pd.to_datetime(weekly_rates["time"], unit="s", utc=True)
    weekly = pd.DataFrame({k: weekly_rates[k].astype(float) for k in ("open", "high", "low", "close")}, index=weekly_index).sort_index()
    return base, weekly, shared_meta | {"pip": pip}


def true_range(frame: pd.DataFrame) -> pd.Series:
    previous = frame.close.shift(1)
    return pd.concat(((frame.high-frame.low), (frame.high-previous).abs(), (frame.low-previous).abs()), axis=1).max(axis=1)


def make_bars(base: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if timeframe == "M15":
        bars = base.copy(); bars["volume"] = bars.tick_volume
    else:
        bars = base.resample(TIMEFRAMES[timeframe], label="left", closed="left").agg(open=("open","first"), high=("high","max"), low=("low","min"), close=("close","last"), volume=("tick_volume","sum"), spread_price=("spread_price","last")).dropna()
    bars["atr"] = true_range(bars).ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    bars["ema50"] = bars.close.ewm(span=50, adjust=False, min_periods=50).mean()
    bars["atr_ratio"] = bars.atr/bars.atr.rolling(20, min_periods=10).median()
    bars["volume_ratio"] = bars.volume/bars.volume.rolling(20, min_periods=10).median().replace(0,np.nan)
    bars["swing_low"] = bars.low.rolling(16, min_periods=16).min().shift(1)
    bars["swing_high"] = bars.high.rolling(16, min_periods=16).max().shift(1)
    return bars.dropna(subset=["atr","ema50"])


def percentile(values: np.ndarray, probability: float) -> float:
    return float(np.quantile(values, probability, method="linear"))


def signals(canonical: str, weekly: pd.DataFrame, rolling: int, tail: float) -> list[dict]:
    cache_key = (canonical, rolling, tail)
    if cache_key in _SIGNAL_CACHE: return _SIGNAL_CACHE[cache_key]
    gaps = np.log(weekly.open.to_numpy()[1:]/weekly.close.to_numpy()[:-1])
    rows = []
    for i in range(rolling, len(gaps)):
        history = gaps[i-rolling:i]
        lower, upper = percentile(history, tail/100.0), percentile(history, 1.0-tail/100.0)
        gap = float(gaps[i]); bar_index = i+1
        if gap <= lower or gap >= upper:
            rows.append({"week": weekly.index[bar_index], "open": float(weekly.open.iloc[bar_index]), "previous_close": float(weekly.close.iloc[bar_index-1]), "gap": gap, "paper_side": 1 if gap < 0 else -1})
    _SIGNAL_CACHE[cache_key] = rows
    return rows


def side_for(paper_side: int, mode: str) -> int:
    side = -paper_side if mode == "inverse" else paper_side
    if mode == "long-only" and side < 0: return 0
    if mode == "short-only" and side > 0: return 0
    return side


def confirmation_ok(bars: pd.DataFrame, confirmation_bar: int, side: int, mode: str) -> bool:
    """Evaluate a fully closed post-signal bar without looking ahead.

    Earlier revisions passed the intended entry index and then subtracted one.
    At a zero-hour delay that accidentally inspected Friday's final candle rather
    than the first candle after the weekly open.  The caller now supplies the
    exact post-open candle that must close before entry.
    """
    if confirmation_bar < 0 or confirmation_bar >= len(bars): return False
    first = confirmation_bar
    move = float(bars.close.iloc[first]-bars.open.iloc[first])
    if mode == "first-bar-reversal": return side*move > 0
    if mode == "first-bar-momentum": return side*move < 0
    if mode == "ema50": return side*(float(bars.close.iloc[first])-float(bars.ema50.iloc[first])) > 0
    if mode == "normal-vol": return float(bars.atr_ratio.iloc[first]) <= 1.50
    if mode == "rel-volume": return float(bars.volume_ratio.iloc[first]) >= 1.0
    return True


def distance_for(bars: pd.DataFrame, start: int, side: int, entry: float, gap_price: float, config: Config) -> float:
    atr = float(bars.atr.iloc[start-1])
    if config.stop_mode == "atr": return config.stop_value*atr
    if config.stop_mode == "gap": return max(0.50*atr, min(4.0*atr, config.stop_value*gap_price))
    level = float(bars.swing_low.iloc[start-1] if side > 0 else bars.swing_high.iloc[start-1])
    raw = entry-level if side > 0 else level-entry
    return max(0.50*atr, min(4.0*atr, raw+0.10*atr))


def simulate(canonical: str, bars: pd.DataFrame, weekly: pd.DataFrame, meta: dict, config: Config, period, collect=False, extra_cost_pips=0.0) -> dict:
    trades=[]; pip=float(meta["pip"])
    for signal in signals(canonical, weekly, config.rolling_weeks, config.tail_percent):
        entry_time = signal["week"]+pd.Timedelta(hours=config.delay_hours)
        if entry_time < period[0] or entry_time >= period[1]: continue
        start = int(bars.index.searchsorted(entry_time, side="left"))
        if start < 0 or start >= len(bars): continue
        side = side_for(int(signal["paper_side"]), config.direction)
        if side == 0: continue
        if config.confirmation != "none":
            # Wait for the first bar at/after the selected delay to close, then
            # enter at the next bar's open. This is the earliest causal entry.
            if start + 1 >= len(bars) or not confirmation_ok(bars,start,side,config.confirmation): continue
            start += 1
            entry_time = bars.index[start]
        spread=float(bars.spread_price.iloc[start]); entry=float(bars.open.iloc[start])+(spread if side>0 else 0.0)
        gap_price=abs(float(signal["open"])-float(signal["previous_close"]))
        distance=distance_for(bars,start,side,entry,gap_price,config)
        if not math.isfinite(distance) or distance<=2*spread: continue
        stop=entry-side*distance
        if config.target_mode == "fixed": target=entry+side*config.rr*distance
        elif config.target_mode in ("gap-fill","adaptive"):
            raw_target=float(signal["previous_close"])
            target_r=side*(raw_target-entry)/distance
            if config.target_mode == "gap-fill" and target_r < 0.25: continue
            if config.target_mode == "adaptive":
                target_r=max(0.50,min(4.0,target_r)); raw_target=entry+side*target_r*distance
            target=raw_target
        else: target=math.nan
        if config.max_hold_hours:
            end_time=entry_time+pd.Timedelta(hours=config.max_hold_hours)
        else:
            local=entry_time.tz_convert("UTC"); days=(4-local.weekday())%7
            end_time=local.normalize()+pd.Timedelta(days=days,hours=21)
        end=min(len(bars)-1,int(bars.index.searchsorted(end_time,side="left")))
        if end<=start: continue
        exit_index=end; exit_price=float(bars.close.iloc[end])+(float(bars.spread_price.iloc[end]) if side<0 else 0.0); reason="timed"
        for i in range(start,end+1):
            bar_spread=float(bars.spread_price.iloc[i])
            if side>0:
                stop_hit=float(bars.low.iloc[i])<=stop; target_hit=config.target_mode!="timed" and float(bars.high.iloc[i])>=target
            else:
                stop_hit=float(bars.high.iloc[i])+bar_spread>=stop; target_hit=config.target_mode!="timed" and float(bars.low.iloc[i])+bar_spread<=target
            if stop_hit: exit_index,exit_price,reason=i,stop,"stop"; break
            if target_hit: exit_index,exit_price,reason=i,target,"target"; break
            progress=side*(float(bars.close.iloc[i])+(bar_spread if side<0 else 0.0)-entry)/distance
            if config.management=="breakeven" and progress>=1.0: stop=max(stop,entry) if side>0 else min(stop,entry)
            elif config.management=="atr-trail" and progress>=1.0:
                candidate=float(bars.close.iloc[i])-1.5*float(bars.atr.iloc[i]) if side>0 else float(bars.close.iloc[i])+bar_spread+1.5*float(bars.atr.iloc[i]); stop=max(stop,candidate) if side>0 else min(stop,candidate)
            elif config.management=="dynamic-50-20" and progress>=0.50:
                candidate=entry+side*0.20*distance; stop=max(stop,candidate) if side>0 else min(stop,candidate)
        result_r=side*(exit_price-entry)/distance-(COMMISSION_SLIPPAGE_PIPS+extra_cost_pips)*pip/distance
        trades.append({"entry":bars.index[start].isoformat(),"exit":bars.index[exit_index].isoformat(),"side":"long" if side>0 else "short","r":float(result_r),"stop_pips":float(distance/pip),"gap_percent":float(signal["gap"]*100),"reason":reason})
    return metrics(trades,collect)


def metrics(trades,collect=False):
    if not trades: return {"return_pct":0.,"profit_factor":0.,"win_rate":0.,"max_dd_pct":0.,"trades":0,"sharpe":0.,"recovery":0.,"expectancy_r":0.,"average_rr":0.,"max_win_streak":0,"max_loss_streak":0}
    ordered=sorted(trades,key=lambda x:x["exit"]); rs=np.array([x["r"] for x in ordered],float); equity=np.r_[1.,np.cumprod(np.maximum(.01,1+RISK*rs))]; pnl=np.diff(equity); gp=pnl[pnl>0].sum();gl=-pnl[pnl<0].sum();peaks=np.maximum.accumulate(equity);dd=float(np.max(1-equity/peaks)*100)
    exits=pd.to_datetime([x["exit"] for x in ordered],utc=True); weekly=pd.Series(RISK*rs,index=exits).groupby(level=0).sum().resample("7D").sum();sd=weekly.std(ddof=1);sharpe=float(weekly.mean()/sd*math.sqrt(52)) if sd>0 else 0.;mw=ml=cw=cl=0
    for r in rs:
        if r>0:cw+=1;cl=0
        elif r<0:cl+=1;cw=0
        else:cw=cl=0
        mw=max(mw,cw);ml=max(ml,cl)
    result={"return_pct":float((equity[-1]-1)*100),"profit_factor":float(min(99,gp/gl if gl else 99)),"win_rate":float(np.mean(rs>0)*100),"max_dd_pct":dd,"trades":int(len(rs)),"sharpe":sharpe,"recovery":float(((equity[-1]-1)*100)/dd if dd else 0),"expectancy_r":float(rs.mean()),"average_rr":float(rs[rs>0].mean() if np.any(rs>0) else 0),"max_win_streak":mw,"max_loss_streak":ml}
    if collect:result["trades_data"]=ordered
    return result


def score(train,validation):
    if train["trades"]<5 or validation["trades"]<5:return -10000+train["trades"]+validation["trades"]
    mr=min(train["return_pct"],validation["return_pct"]);mp=min(train["profit_factor"],validation["profit_factor"]);md=max(train["max_dd_pct"],validation["max_dd_pct"]);s=.4*mr+10*math.log(max(.05,min(3,mp)))+min(train["recovery"],validation["recovery"])-.3*md
    if mr<=0:s-=40+abs(mr)
    if mp<1:s-=30*(1-mp)
    return float(s)


def evaluate(canonical,bars,weekly,meta,c):
    tr=simulate(canonical,bars[c.timeframe],weekly,meta,c,TRAIN);va=simulate(canonical,bars[c.timeframe],weekly,meta,c,VALIDATION);return tr,va,score(tr,va)


def stage(canonical,bars,weekly,meta,configs,width=20):
    seen=set();out=[];audit=[]
    for c in configs:
        key=tuple(asdict(c).values())
        if key in seen:continue
        seen.add(key);tr,va,s=evaluate(canonical,bars,weekly,meta,c);out.append((s,c));audit.append({"config":asdict(c),"score":s,"train":tr,"validation":va})
    out.sort(key=lambda x:x[0],reverse=True);return [c for _,c in out[:width]],audit


def select(canonical,base,weekly,meta):
    bars={tf:make_bars(base,tf) for tf in TIMEFRAMES};audits=[]
    initial=[Config(timeframe=tf,rolling_weeks=rw,tail_percent=tail,delay_hours=delay,confirmation=confirm) for tf,rw,tail,delay,confirm in itertools.product(TIMEFRAMES,ROLLING,TAILS,DELAYS,CONFIRMATIONS)]
    print(f"  {canonical}: signal/timeframe/gap-distribution ({len(initial)} configs)",flush=True);beam,a=stage(canonical,bars,weekly,meta,initial);audits += [{"stage":"signal",**x} for x in a]
    print(f"  {canonical}: direction",flush=True);beam,a=stage(canonical,bars,weekly,meta,[replace(c,direction=x) for c in beam for x in DIRECTIONS]);audits += [{"stage":"direction",**x} for x in a]
    print(f"  {canonical}: dynamic stops",flush=True);beam,a=stage(canonical,bars,weekly,meta,[replace(c,stop_mode=m,stop_value=v) for c in beam for m,v in STOPS]);audits += [{"stage":"stop",**x} for x in a]
    print(f"  {canonical}: RR/gap-fill/adaptive targets",flush=True);beam,a=stage(canonical,bars,weekly,meta,[replace(c,target_mode=m,rr=v) for c in beam for m,v in TARGETS]);audits += [{"stage":"target",**x} for x in a]
    print(f"  {canonical}: management",flush=True);beam,a=stage(canonical,bars,weekly,meta,[replace(c,management=x) for c in beam for x in MANAGEMENTS]);audits += [{"stage":"management",**x} for x in a]
    print(f"  {canonical}: holding period",flush=True);beam,a=stage(canonical,bars,weekly,meta,[replace(c,max_hold_hours=x) for c in beam for x in HOLDS]);audits += [{"stage":"holding",**x} for x in a]
    selected=beam[0];tr,va,s=evaluate(canonical,bars,weekly,meta,selected);locked=simulate(canonical,bars[selected.timeframe],weekly,meta,selected,LOCKED,True);stress=simulate(canonical,bars[selected.timeframe],weekly,meta,selected,LOCKED,False,1.0);full=simulate(canonical,bars[selected.timeframe],weekly,meta,selected,FULL,True)
    return {"symbol":canonical,"selected":asdict(selected),"selection_score":s,"train":tr,"validation":va,"locked":locked,"locked_cost_stress":stress,"full":full,"audit":audits}


def monte_carlo(trades,paths=5000,block=3):
    rs=np.array([x["r"] for x in trades],float);rng=np.random.default_rng(SEED+len(rs));rets=[];dds=[]
    if not len(rs):return {"paths":paths,"return_p5":-100.,"return_median":-100.,"dd_p95":100.,"profit_probability":0.}
    for _ in range(paths):
        sample=[]
        while len(sample)<len(rs):
            j=int(rng.integers(0,max(1,len(rs)-block+1)));sample.extend(rs[j:j+block])
        eq=np.cumprod(np.maximum(.01,1+RISK*np.array(sample[:len(rs)])));peak=np.maximum.accumulate(np.r_[1.,eq])[1:];rets.append((eq[-1]-1)*100);dds.append(np.max(1-eq/peak)*100)
    return {"paths":paths,"return_p5":float(np.percentile(rets,5)),"return_median":float(np.median(rets)),"return_p95":float(np.percentile(rets,95)),"dd_median":float(np.median(dds)),"dd_p95":float(np.percentile(dds,95)),"profit_probability":float(np.mean(np.array(rets)>0)*100)}


def gate(row):
    failures=[]
    for p in ("train","validation","locked","locked_cost_stress"):
        if row[p]["return_pct"]<=0:failures.append(f"{p} return <= 0")
    if row["locked"]["profit_factor"]<1.2:failures.append("locked PF < 1.20")
    if row["locked"]["trades"]<10:failures.append("locked trades < 10")
    if row["locked"]["max_dd_pct"]>15:failures.append("locked DD > 15%")
    if row["monte_carlo"]["return_p5"]<=0:failures.append("Monte Carlo P5 <= 0")
    return not failures,failures


def chart(row):
    eq=10000.;xs=[FULL[0]];ys=[eq]
    for t in sorted(row["full"]["trades_data"],key=lambda x:x["exit"]):eq*=max(.01,1+RISK*t["r"]);xs.append(pd.Timestamp(t["exit"]));ys.append(eq)
    CHARTS.mkdir(parents=True,exist_ok=True);fig,ax=plt.subplots(figsize=(12,5));fig.patch.set_facecolor("#07110f");ax.set_facecolor("#07110f");ax.plot(xs,ys,color="#74f5ca");ax.axvline(VALIDATION[0],color="#55b6ff",ls="--");ax.axvline(LOCKED[0],color="#f2c14e",ls="--");ax.set_title(f"{row['symbol']} weekend-gap pipeline",color="white");ax.tick_params(colors="#a9c8bf");ax.grid(alpha=.15);fig.tight_layout();fig.savefig(CHARTS/f"{row['symbol'].lower()}-equity.png",dpi=150);plt.close(fig)


def report(payload):
    lines=["# Weekend Gap Reversal — Full Pipeline Report","","Research only. No deployment changes were made.","","| Pair | Train Ret/PF/WR | Validation Ret/PF/WR | Locked Ret/PF/WR | DD | Sharpe | Recovery | Trades | Stress PF | MC P5 | Gate |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in payload["results"]:
        t,v,l,s,m=r["train"],r["validation"],r["locked"],r["locked_cost_stress"],r["monte_carlo"]
        lines.append(f"| {r['symbol']} | {t['return_pct']:+.2f}%/{t['profit_factor']:.2f}/{t['win_rate']:.2f}% | {v['return_pct']:+.2f}%/{v['profit_factor']:.2f}/{v['win_rate']:.2f}% | {l['return_pct']:+.2f}%/{l['profit_factor']:.2f}/{l['win_rate']:.2f}% | {l['max_dd_pct']:.2f}% | {l['sharpe']:.2f} | {l['recovery']:.2f} | {l['trades']} | {s['profit_factor']:.2f} | {m['return_p5']:+.2f}% | {'PASS' if r['promoted'] else 'FAIL'} |")
    lines += ["","## Configurations and decisions",""]
    for r in payload["results"]:lines += [f"### {r['symbol']}","",f"- Selected before locked reveal: `{json.dumps(r['selected'],sort_keys=True)}`",f"- **{'PASS' if r['promoted'] else 'FAIL'}** — {', '.join(r['gate_failures']) if r['gate_failures'] else 'all research gates passed; native Every Tick confirmation remains required'}",""]
    return "\n".join(lines)


def research_symbol(symbol):
    print(f"Researching {symbol}...",flush=True)
    base,weekly,meta=load(symbol)
    row=select(symbol,base,weekly,meta)
    row["monte_carlo"]=monte_carlo(row["locked"]["trades_data"])
    row["promoted"],row["gate_failures"]=gate(row)
    chart(row)
    return row


def main():
    metadata=prepare_weekly();partial=ROOT/"pipeline-partial-results.json"
    results=json.loads(partial.read_text(encoding="utf-8"))["results"] if partial.exists() else []
    completed={row["symbol"] for row in results};todo=[symbol for symbol in SYMBOLS if symbol not in completed]
    with ProcessPoolExecutor(max_workers=min(3,len(todo) or 1)) as pool:
        futures={pool.submit(research_symbol,symbol):symbol for symbol in todo}
        for future in as_completed(futures):
            row=future.result();results.append(row);results.sort(key=lambda x:SYMBOLS.index(x["symbol"]));dump(partial,{"results":results})
    payload={"strategy":"Weekend gap overreaction reversal — full pipeline","generated_at":datetime.now(timezone.utc).isoformat(),"risk_per_trade_pct":1.0,"source":"https://irep.ntu.ac.uk/id/eprint/35555/","broker":metadata,"results":results};dump(ROOT/"pipeline-results.json",payload);(ROOT/"FULL PIPELINE REPORT.md").write_text(report(payload),encoding="utf-8");print(report(payload));return 0


if __name__=="__main__":raise SystemExit(main())
