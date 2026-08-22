from __future__ import annotations

import itertools
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
RESULTS = ROOT / "Results"
DATA = ROOT / "Data"
STARTING_BALANCE = 10_000.0
RISK_FRACTION = 0.01
FULL_FROM = pd.Timestamp("2021-08-08", tz="UTC")
FINAL_FROM = pd.Timestamp("2025-08-08", tz="UTC")
TO_DATE = pd.Timestamp("2026-08-08", tz="UTC")
DEVELOPMENT_END = pd.Timestamp("2025-01-01", tz="UTC")
SELECTION_END = FINAL_FROM

APEX_DATA = PROJECT / "Apex Pulse and IVB Research 2026-08-10" / "Data"
SOURCE_MAP = {
    "XAU": (APEX_DATA, "XAU", "MEXAtlantic-XAU-XAUUSD..-M1-*.csv.gz"),
    "US30": (APEX_DATA, "US30", "MEXAtlantic-US30-US30-M1-*.csv.gz"),
    "US100": (APEX_DATA, "US100", "MEXAtlantic-US100-UT100-M1-*.csv.gz"),
    "EURUSD": (APEX_DATA, "EURUSD", "MEXAtlantic-EURUSD-EURUSD..-M1-*.csv.gz"),
}


@dataclass(frozen=True)
class Signal:
    time: pd.Timestamp
    direction: int
    stop: float
    reward_risk: float
    maximum_hold_minutes: int
    force_exit: pd.Timestamp | None = None
    tag: str = ""


def load_asset(label: str) -> tuple[pd.DataFrame, dict]:
    directory, key, pattern = SOURCE_MAP[label]
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))["instruments"][key]
    frames = []
    columns = ["time", "open", "high", "low", "close", "tick_volume", "spread"]
    for path in sorted(directory.glob(pattern)):
        match = re.search(r"M1-(\d{4})\.csv\.gz$", path.name)
        if match and 2021 <= int(match.group(1)) <= 2026:
            frames.append(pd.read_csv(path, compression="gzip", usecols=columns, parse_dates=["time"]))
    if not frames:
        raise FileNotFoundError(f"No local M1 files found for {label}")
    frame = pd.concat(frames, ignore_index=True)
    frame["time"] = pd.to_datetime(frame.time, utc=True)
    frame = frame.loc[(frame.time >= FULL_FROM) & (frame.time < TO_DATE)]
    frame = frame.sort_values("time").drop_duplicates("time", keep="last").reset_index(drop=True)
    return frame, manifest


def resample_bars(m1: pd.DataFrame, minutes: int) -> pd.DataFrame:
    indexed = m1.set_index("time")
    bars = indexed.resample(f"{minutes}min", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"),
        tick_volume=("tick_volume", "sum"),
    ).dropna().reset_index()
    previous = bars.close.shift(1)
    tr = pd.concat([(bars.high-bars.low), (bars.high-previous).abs(), (bars.low-previous).abs()], axis=1).max(axis=1)
    bars["atr"] = tr.rolling(14, min_periods=14).mean()
    bars["end_time"] = bars.time + pd.to_timedelta(minutes, unit="m")
    return bars


def fast_entry_time(signal: Signal, m5: pd.DataFrame, maximum_wait_minutes: int = 30) -> pd.Timestamp | None:
    starts = m5.time.to_numpy(dtype="datetime64[ns]")
    begin = np.searchsorted(starts, signal.time.to_datetime64(), side="left")
    deadline = signal.time + pd.Timedelta(minutes=maximum_wait_minutes)
    for index in range(begin, min(begin + maximum_wait_minutes // 5 + 2, len(m5))):
        bar = m5.iloc[index]
        if bar.end_time > deadline:
            break
        opposite = bar.close < bar.open if signal.direction > 0 else bar.close > bar.open
        if opposite:
            return bar.end_time
    return None


def fast_exit_time(
    direction: int,
    stop_time: pd.Timestamp,
    deadline: pd.Timestamp,
    m5: pd.DataFrame,
    maximum_wait_minutes: int = 30,
) -> pd.Timestamp | None:
    """Paper-style stop overlay: wait briefly for one candle favourable to the position."""
    starts = m5.time.to_numpy(dtype="datetime64[ns]")
    begin = np.searchsorted(starts, stop_time.to_datetime64(), side="left")
    confirmation_deadline = min(deadline, stop_time + pd.Timedelta(minutes=maximum_wait_minutes))
    for index in range(begin, min(begin + maximum_wait_minutes // 5 + 3, len(m5))):
        bar = m5.iloc[index]
        if bar.end_time > confirmation_deadline:
            break
        favourable = bar.close > bar.open if direction > 0 else bar.close < bar.open
        if favourable and bar.end_time > stop_time:
            return bar.end_time
    return None


def simulate(
    m1: pd.DataFrame,
    spec: dict,
    signals: list[Signal],
    start: pd.Timestamp,
    end: pd.Timestamp,
    fast_overlay: bool,
    break_even_at_r: float = 0.0,
) -> dict:
    times = m1.time.to_numpy(dtype="datetime64[ns]")
    opens = m1.open.to_numpy(float); highs = m1.high.to_numpy(float); lows = m1.low.to_numpy(float); closes = m1.close.to_numpy(float)
    spread_price = m1.spread.to_numpy(float) * float(spec["point"])
    positive_spreads = spread_price[spread_price > 0]
    median_spread = float(np.median(positive_spreads)) if len(positive_spreads) else float(spec["median_spread_price"])
    slippage = 0.25 * median_spread
    m5 = resample_bars(m1, 5) if fast_overlay else pd.DataFrame()
    balance = STARTING_BALANCE; peak = balance; maximum_dd = 0.0
    gross_profit = 0.0; gross_loss = 0.0; wins = 0; losses_count = 0
    last_exit = -1; records: list[dict] = []; equity_points = [(start, balance)]

    for signal in sorted(signals, key=lambda item: item.time):
        if signal.time < start or signal.time >= end:
            continue
        entry_time = fast_entry_time(signal, m5) if fast_overlay else signal.time
        if entry_time is None or entry_time >= end:
            continue
        entry_index = int(np.searchsorted(times, entry_time.to_datetime64(), side="left"))
        if entry_index <= last_exit or entry_index >= len(m1):
            continue
        spread = spread_price[entry_index] if spread_price[entry_index] > 0 else median_spread
        entry = opens[entry_index] + (spread + slippage if signal.direction > 0 else -slippage)
        distance = entry - signal.stop if signal.direction > 0 else signal.stop - entry
        if distance <= max(2.0 * median_spread, 1e-12):
            continue
        target = entry + signal.direction * signal.reward_risk * distance
        active_stop = signal.stop; moved_be = False
        deadline_time = min(
            signal.time + pd.Timedelta(minutes=signal.maximum_hold_minutes),
            signal.force_exit if signal.force_exit is not None else end,
            end,
        )
        exit_limit = min(len(m1)-1, int(np.searchsorted(times, deadline_time.to_datetime64(), side="right") - 1))
        if exit_limit <= entry_index:
            continue
        exit_price = closes[exit_limit] if signal.direction > 0 else closes[exit_limit] + spread_price[exit_limit]
        exit_reason = "time"
        exit_index = exit_limit
        risk_cash = balance * RISK_FRACTION

        deferred_exit_index = None
        for minute in range(entry_index, exit_limit + 1):
            minute_spread = spread_price[minute] if spread_price[minute] > 0 else median_spread
            if deferred_exit_index is not None and minute >= deferred_exit_index:
                exit_price = opens[minute] - slippage if signal.direction > 0 else opens[minute] + minute_spread + slippage
                exit_reason = "fast-alpha stop confirmation"; exit_index = minute; break
            if signal.direction > 0:
                stop_hit = deferred_exit_index is None and lows[minute] <= active_stop
                target_hit = highs[minute] >= target
                mark = closes[minute]
            else:
                stop_hit = deferred_exit_index is None and highs[minute] + minute_spread >= active_stop
                target_hit = lows[minute] + minute_spread <= target
                mark = closes[minute] + minute_spread
            mark_r = signal.direction * (mark-entry) / distance
            marked_equity = balance + risk_cash * mark_r
            peak = max(peak, marked_equity)
            if peak > 0:
                maximum_dd = max(maximum_dd, (peak-marked_equity)/peak*100.0)
            if stop_hit:
                if fast_overlay:
                    stop_timestamp = pd.Timestamp(times[minute], tz="UTC")
                    confirm_time = fast_exit_time(signal.direction, stop_timestamp, deadline_time, m5)
                    if confirm_time is not None:
                        deferred_exit_index = min(exit_limit, int(np.searchsorted(times, confirm_time.to_datetime64(), side="left")))
                        continue
                # Conservative gap handling: a market that opens beyond the stop receives the worse fill.
                if signal.direction > 0:
                    exit_price = min(active_stop, opens[minute]) - slippage
                else:
                    exit_price = max(active_stop, opens[minute] + minute_spread) + slippage
                exit_reason = "stop"; exit_index = minute; break
            if target_hit:
                exit_price = target - slippage if signal.direction > 0 else target + slippage
                exit_reason = "target"; exit_index = minute; break
            if break_even_at_r > 0 and not moved_be:
                favourable = (highs[minute]-entry)/distance if signal.direction > 0 else (entry-(lows[minute]+minute_spread))/distance
                if favourable >= break_even_at_r:
                    active_stop = entry; moved_be = True

        result_r = signal.direction * (exit_price-entry) / distance
        pnl = risk_cash * result_r
        balance += pnl; peak = max(peak, balance)
        maximum_dd = max(maximum_dd, (peak-balance)/peak*100.0 if peak else 0.0)
        if pnl > 0: gross_profit += pnl; wins += 1
        else: gross_loss += pnl; losses_count += 1
        exit_timestamp = pd.Timestamp(times[exit_index], tz="UTC")
        records.append({"entry": str(pd.Timestamp(times[entry_index], tz="UTC")), "exit": str(exit_timestamp),
                        "direction": signal.direction, "pnl": pnl, "r": result_r, "reason": exit_reason, "tag": signal.tag})
        equity_points.append((exit_timestamp, balance)); last_exit = exit_index

    trades = wins + losses_count
    elapsed_years = max((end-start).days/365.25, 1/365.25)
    return_pct = (balance/STARTING_BALANCE-1.0)*100.0
    cagr = ((balance/STARTING_BALANCE)**(1/elapsed_years)-1.0)*100.0 if balance > 0 else -100.0
    pf = gross_profit/abs(gross_loss) if gross_loss < 0 else (999.0 if gross_profit > 0 else 0.0)
    return {
        "initial": STARTING_BALANCE, "final": balance, "net": balance-STARTING_BALANCE,
        "return_pct": return_pct, "cagr_pct": cagr, "max_equity_dd_pct": maximum_dd,
        "profit_factor": pf, "win_rate_pct": wins/trades*100.0 if trades else 0.0,
        "wins": wins, "losses": losses_count, "trades": trades,
        "gross_profit": gross_profit, "gross_loss": gross_loss,
        "first": str(start), "last": str(end), "fast_overlay": fast_overlay,
        "records": records, "equity": [(str(t), value) for t, value in equity_points],
    }


def trend_signals(m1: pd.DataFrame, params: dict) -> list[Signal]:
    bars = resample_bars(m1, 240)
    bars["ema"] = bars.close.ewm(span=params["ema"], adjust=False).mean()
    bars["prior_high"] = bars.high.shift(1).rolling(params["lookback"]).max()
    bars["prior_low"] = bars.low.shift(1).rolling(params["lookback"]).min()
    output = []
    for row in bars.itertuples():
        if not np.isfinite(row.atr) or not np.isfinite(row.prior_high): continue
        direction = 1 if row.close > row.prior_high and row.close > row.ema else -1 if row.close < row.prior_low and row.close < row.ema else 0
        if direction:
            stop = row.close - direction*params["stop_atr"]*row.atr
            output.append(Signal(row.end_time,direction,stop,params["rr"],20*24*60,tag="H4 channel trend"))
    return output


def orb_signals(m1: pd.DataFrame, params: dict) -> list[Signal]:
    bars = resample_bars(m1, 5)
    bars["ny"] = bars.time.dt.tz_convert("America/New_York")
    bars["date"] = bars.ny.dt.date
    output=[]; opening_history=[]
    for _, day in bars.groupby("date", sort=True):
        if day.ny.iloc[0].weekday() >= 5: continue
        minutes = day.ny.dt.hour*60 + day.ny.dt.minute
        opening = day.loc[(minutes>=570) & (minutes<570+params["opening_minutes"])]
        if len(opening) < params["opening_minutes"]//5: continue
        opening_high=float(opening.high.max()); opening_low=float(opening.low.min()); opening_volume=float(opening.tick_volume.sum())
        median_open=float(np.median(opening_history[-20:])) if len(opening_history)>=5 else np.nan
        opening_history.append(opening_volume)
        if not np.isfinite(median_open) or opening_volume < params["opening_rv"]*median_open: continue
        post=day.loc[(minutes>=570+params["opening_minutes"]) & (minutes<690)]
        volumes=list(day.tick_volume)
        for index,row in post.iterrows():
            loc=day.index.get_loc(index)
            prior=np.asarray(volumes[max(0,loc-20):loc],float)
            if len(prior)<10: continue
            bar_rv=row.tick_volume/max(float(np.median(prior)),1.0)
            body=abs(row.close-row.open)/max(row.high-row.low,1e-12)
            direction=1 if row.close>opening_high and row.close>row.open else -1 if row.close<opening_low and row.close<row.open else 0
            if direction and bar_rv>=params["breakout_rv"] and body>=params["body"]:
                stop=opening_low if direction>0 else opening_high
                local=row.ny
                close_ny=pd.Timestamp(year=local.year,month=local.month,day=local.day,hour=15,minute=55,tz="America/New_York")
                output.append(Signal(row.end_time,direction,stop,params["rr"],6*60,close_ny.tz_convert("UTC"),"NY ORB"))
                break
    return output


def vwap_signals(m1: pd.DataFrame, params: dict) -> list[Signal]:
    bars=resample_bars(m1,15); bars["ny"]=bars.time.dt.tz_convert("America/New_York"); bars["date"]=bars.ny.dt.date
    output=[]
    for _,day in bars.groupby("date",sort=True):
        if day.ny.iloc[0].weekday()>=5: continue
        minutes=day.ny.dt.hour*60+day.ny.dt.minute
        session=day.loc[(minutes>=570)&(minutes<930)].copy()
        if len(session)<8: continue
        typical=(session.high+session.low+session.close)/3.0
        session["vwap"]=(typical*session.tick_volume).cumsum()/session.tick_volume.cumsum().clip(lower=1)
        session_open=float(session.open.iloc[0]); used=False
        for row in session.itertuples():
            minute=row.ny.hour*60+row.ny.minute
            if minute<630 or not np.isfinite(row.atr): continue
            upper=row.vwap+params["band_atr"]*row.atr; lower=row.vwap-params["band_atr"]*row.atr
            direction=1 if row.close>upper and row.close>row.open else -1 if row.close<lower and row.close<row.open else 0
            if direction:
                stop=row.vwap if params["stop_mode"]=="vwap" else session_open
                if (direction>0 and stop>=row.close) or (direction<0 and stop<=row.close): continue
                close_ny=pd.Timestamp(year=row.ny.year,month=row.ny.month,day=row.ny.day,hour=15,minute=55,tz="America/New_York")
                output.append(Signal(row.end_time,direction,float(stop),params["rr"],6*60,close_ny.tz_convert("UTC"),"VWAP trend")); used=True; break
        if used: continue
    return output


def supply_demand_signals(m1: pd.DataFrame, params: dict) -> list[Signal]:
    bars=resample_bars(m1,60); output=[]; zone=None
    for i in range(15,len(bars)):
        row=bars.iloc[i]
        if zone is not None:
            zone["age"]+=1
            touched=row.low<=zone["high"] and row.high>=zone["low"]
            invalid=row.close<zone["low"] if zone["direction"]>0 else row.close>zone["high"]
            if invalid or zone["age"]>params["expiry"]: zone=None
            elif touched:
                confirm=row.close>zone["high"] and row.close>row.open if zone["direction"]>0 else row.close<zone["low"] and row.close<row.open
                if confirm:
                    stop=zone["low"]-params["buffer_atr"]*row.atr if zone["direction"]>0 else zone["high"]+params["buffer_atr"]*row.atr
                    output.append(Signal(row.end_time,zone["direction"],float(stop),params["rr"],7*24*60,tag="H1 supply demand retest"))
                zone=None
        prior=bars.iloc[i-1]
        if np.isfinite(prior.atr) and abs(prior.close-prior.open)>=params["impulse_atr"]*prior.atr:
            direction=1 if prior.close>prior.open else -1
            low=prior.low if direction>0 else max(prior.open,prior.close)
            high=min(prior.open,prior.close) if direction>0 else prior.high
            zone={"direction":direction,"low":float(low),"high":float(high),"age":0}
    return output


def paper_atr_open_signals(m1: pd.DataFrame, params: dict) -> list[Signal]:
    m15=resample_bars(m1,15); daily=resample_bars(m1,1440).set_index("time")
    daily_atr=daily.atr.shift(1)
    m15["ny"]=m15.time.dt.tz_convert("America/New_York"); m15["date"]=m15.ny.dt.date
    output=[]
    for _,day in m15.groupby("date",sort=True):
        if day.ny.iloc[0].weekday()>=5: continue
        minutes=day.ny.dt.hour*60+day.ny.dt.minute
        session=day.loc[(minutes>=570)&(minutes<960)]
        if len(session)<8: continue
        session_open=float(session.open.iloc[0]); date_utc=pd.Timestamp(session.time.iloc[0]).floor("D")
        eligible=daily_atr.loc[daily_atr.index<=date_utc]
        if eligible.empty or not np.isfinite(eligible.iloc[-1]): continue
        atr=float(eligible.iloc[-1]); upper=session_open+params["band_atr"]*atr; lower=session_open-params["band_atr"]*atr
        for row in session.itertuples():
            direction=1 if row.close>upper else -1 if row.close<lower else 0
            if not direction: continue
            close_ny=pd.Timestamp(year=row.ny.year,month=row.ny.month,day=row.ny.day,hour=15,minute=55,tz="America/New_York")
            output.append(Signal(row.end_time,direction,session_open,20.0,6*60,close_ny.tz_convert("UTC"),"Paper ATR-open trend"))
            break
    return output


def fred_series(series_id: str) -> pd.Series:
    DATA.mkdir(parents=True,exist_ok=True)
    path=DATA/f"FRED-{series_id}.csv"
    url=f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    if path.exists():
        frame=pd.read_csv(path)
    else:
        frame=pd.read_csv(url)
        frame.to_csv(path,index=False)
    frame.columns=["date",series_id]
    frame["date"]=pd.to_datetime(frame.date,utc=True)
    return pd.to_numeric(frame[series_id],errors="coerce").set_axis(frame.date).dropna()


def macro_signals(m1: pd.DataFrame, params: dict) -> list[Signal]:
    daily=resample_bars(m1,1440).set_index("time")
    macro=pd.concat({name:fred_series(name) for name in ["UNRATE","CPIAUCSL","INDPRO","FEDFUNDS"]},axis=1).sort_index()
    # Conservative publication lag. Values are current revised FRED observations,
    # so this prevents date look-ahead but cannot remove vintage/revision bias.
    macro.index=macro.index+pd.Timedelta(days=params["lag_days"])
    macro["growth"]=(macro.INDPRO.pct_change(3)>0).astype(int)+(macro.UNRATE.diff(3)<0).astype(int)
    macro["inflation"]=(macro.CPIAUCSL.pct_change(3)>macro.CPIAUCSL.pct_change(12)/4.0).astype(int)
    macro["easing"]=(macro.FEDFUNDS.diff(3)<=0).astype(int)
    macro["direction"]=np.where((macro.growth>=1)&(macro.easing>=1),1,np.where((macro.growth==0)&(macro.easing==0),-1,0))
    regime=macro.direction.reindex(daily.index,method="ffill").fillna(0)
    daily["ema"]=daily.close.ewm(span=params["ema"],adjust=False).mean()
    output=[]; last=0
    for time,row in daily.iterrows():
        direction=int(regime.loc[time])
        if params["price_confirm"] and direction>0 and row.close<row.ema: direction=0
        if params["price_confirm"] and direction<0 and row.close>row.ema: direction=0
        if direction and direction!=last and np.isfinite(row.atr):
            stop=row.close-direction*params["stop_atr"]*row.atr
            output.append(Signal(time+pd.Timedelta(days=1),direction,float(stop),params["rr"],90*24*60,tag="lagged macro trend"))
        last=direction
    return output


def choose_parameters(
    family: str,
    asset: str,
    m1: pd.DataFrame,
    spec: dict,
    generator: Callable[[pd.DataFrame,dict],list[Signal]],
    grid: list[dict],
) -> tuple[dict,list[dict]]:
    actual_start=max(FULL_FROM,m1.time.min())
    screens=[]
    for params in grid:
        signals=generator(m1,params)
        dev=simulate(m1,spec,signals,actual_start,DEVELOPMENT_END,False)
        row={"family":family,"asset":asset,"params":params,"signals":len(signals),"development":{k:v for k,v in dev.items() if k not in {"records","equity"}}}
        screens.append(row)
    eligible=[row for row in screens if row["development"]["trades"]>=max(8,grid[0].get("minimum_trades",8))]
    eligible.sort(key=lambda row:(row["development"]["profit_factor"],row["development"]["return_pct"]-row["development"]["max_equity_dd_pct"]),reverse=True)
    finalists=eligible[:min(5,len(eligible))] or screens[:1]
    for row in finalists:
        signals=generator(m1,row["params"])
        selection=simulate(m1,spec,signals,DEVELOPMENT_END,SELECTION_END,False)
        row["selection"]={k:v for k,v in selection.items() if k not in {"records","equity"}}
    finalists.sort(key=lambda row:(min(row["development"]["profit_factor"],row.get("selection",{}).get("profit_factor",0)),
                                    row.get("selection",{}).get("return_pct",-999)),reverse=True)
    return finalists[0]["params"], screens


def compact(result: dict) -> dict:
    return {key:value for key,value in result.items() if key not in {"records","equity"}}


def save_equity(path: Path, title: str, pairs: list[tuple[str,dict]]) -> None:
    plt.figure(figsize=(11,5.2),dpi=150)
    for label,result in pairs:
        points=result["equity"]
        plt.plot(pd.to_datetime([p[0] for p in points]),[p[1] for p in points],label=label,linewidth=1.4)
    plt.axhline(STARTING_BALANCE,color="#666",linewidth=.8,linestyle="--")
    plt.title(title); plt.ylabel("Closed-trade equity (USD)"); plt.grid(alpha=.22); plt.legend(); plt.tight_layout(); plt.savefig(path); plt.close()


def main() -> None:
    RESULTS.mkdir(parents=True,exist_ok=True)
    designs=[
        ("trend_swing","XAU",trend_signals,[{"lookback":l,"ema":e,"stop_atr":s,"rr":r} for l,e,s,r in itertools.product([20,40,80],[50,100],[1.5,2.5],[2.0,3.0])]),
        ("orb","XAU",orb_signals,[{"opening_minutes":o,"opening_rv":rv,"breakout_rv":bv,"body":body,"rr":rr} for o,rv,bv,body,rr in [
            (15,.6,.8,.55,2.5),(15,.8,1.0,.55,2.5),(15,.6,1.0,.7,2.0),(5,.6,1.0,.55,2.0),(30,.6,.8,.55,2.5),
            (15,.4,.8,.4,2.0),(15,.8,1.2,.7,3.0),(5,.8,1.2,.7,2.0)]]),
        ("vwap","US100",vwap_signals,[{"band_atr":b,"stop_mode":sm,"rr":rr} for b,sm,rr in itertools.product([0.0,.25,.5],["vwap","open"],[1.5,2.0,2.5])]),
        ("supply_demand","US30",supply_demand_signals,[{"impulse_atr":i,"expiry":e,"buffer_atr":b,"rr":rr} for i,e,b,rr in itertools.product([.8,1.2],[6,12],[.1,.3],[2.0,3.0])]),
        ("paper_atr_open","US100",paper_atr_open_signals,[{"band_atr":b} for b in [.3,.5,.7]]),
        ("economic_data_trend","US100",macro_signals,[{"lag_days":lag,"ema":ema,"price_confirm":pc,"stop_atr":2.5,"rr":4.0} for lag,ema,pc in itertools.product([15,20],[100,200],[False,True])]),
    ]
    all_results=[]; all_screens=[]
    for family,asset,generator,grid in designs:
        print(f"LOAD {family} {asset}",flush=True)
        m1,spec=load_asset(asset); actual_start=max(FULL_FROM,m1.time.min())
        selected,screens=choose_parameters(family,asset,m1,spec,generator,grid); all_screens.extend(screens)
        signals=generator(m1,selected)
        variants=[]
        for overlay in [False,True]:
            break_even=float(selected.get("break_even_at_r",0.0))
            full=simulate(m1,spec,signals,actual_start,min(TO_DATE,m1.time.max()+pd.Timedelta(minutes=1)),overlay,break_even_at_r=break_even)
            final_start=max(FINAL_FROM,m1.time.min())
            final=simulate(m1,spec,signals,final_start,min(TO_DATE,m1.time.max()+pd.Timedelta(minutes=1)),overlay,break_even_at_r=break_even)
            variants.append({"overlay":"fast_alpha" if overlay else "baseline","full":full,"last_year":final})
            print(f"  {variants[-1]['overlay']:10} full {full['return_pct']:+7.2f}% PF {full['profit_factor']:.2f} DD {full['max_equity_dd_pct']:.2f}% | last {final['return_pct']:+7.2f}% PF {final['profit_factor']:.2f}",flush=True)
        save_equity(RESULTS/f"{family}-equity.png",f"{family.replace('_',' ').title()} - {asset}",[(v["overlay"],v["full"]) for v in variants])
        for variant in variants:
            pd.DataFrame(variant["full"]["records"]).to_csv(RESULTS/f"{family}-{variant['overlay']}-trades.csv",index=False)
        all_results.append({"family":family,"asset":asset,"parameters":selected,"actual_start":str(actual_start),
                            "data_end":str(m1.time.max()),"history_rows":len(m1),"real_volume":int(spec.get("real_volume_sum",0)),
                            "variants":[{"overlay":v["overlay"],"full":compact(v["full"]),"last_year":compact(v["last_year"])} for v in variants]})
    json_default=lambda value: value.item() if isinstance(value,np.generic) else str(value)
    (RESULTS/"all-results.json").write_text(json.dumps(all_results,indent=2,default=json_default),encoding="utf-8")
    (RESULTS/"development-screens.json").write_text(json.dumps(all_screens,indent=2,default=json_default),encoding="utf-8")
    rows=[]
    for item in all_results:
        for variant in item["variants"]:
            row={"family":item["family"],"asset":item["asset"],"overlay":variant["overlay"],"parameters":json.dumps(item["parameters"])}
            row.update({f"full_{k}":v for k,v in variant["full"].items()})
            row.update({f"last_year_{k}":v for k,v in variant["last_year"].items()})
            rows.append(row)
    pd.DataFrame(rows).to_csv(RESULTS/"summary.csv",index=False)


if __name__ == "__main__":
    main()
