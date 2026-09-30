"""Offline source-trade overlay. No MT5, order or deployment imports."""
from pathlib import Path
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import json, math, time
import numpy as np
from numba import njit
ROOT=Path(__file__).resolve().parent.parent/'Daily Equity Controls Audit 2026-09-29'
UTC=timezone.utc
FIELDS=['ending_equity','balance','return_pct','equity_dd_pct','adverse_envelope_dd_pct','worst_daily_pct',
    'trades','wins','positive','negative','goal_days','loss_stop_days','blocked_day','blocked_risk','blocked_margin','blocked_lot',
    'first_ftmo_breach_minute','adverse_ftmo_flag_minute','forced_closes','max_open_risk','max_concurrent',
    'phase1_minute','phase2_minute','funded_profit','stop_minute','open_at_end','max_loss_overshoot','max_goal_underfill']
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def clock(start,end):
    h=np.arange(start,end+1,60)
    d=[datetime.fromtimestamp(int(t)*60,UTC).astimezone(ZoneInfo('Europe/Prague')).date().toordinal() for t in h]
    return np.repeat(np.array(d,np.int64),60)[:end-start+1]

@njit(cache=True)
def gross(r,px,contract):
    return r[9]*(px-r[5])*contract/(px if int(r[3])==2 else 1.)

@njit(cache=True)
def run(tr,prices,opens,fresh,sp,start,end,days,ftmo,loss,target,cap,stress,compound,lifecycle,delay=1,
        stop_profit=0.,min_days=0,min_age_days=0,edge_haircut=0.,fixed_risk=50.,risk_fraction=.005):
    n=len(tr);active=np.empty(n,np.int64);count=0;lots=np.zeros(n);entrycost=np.zeros(n);exitcost=np.zeros(n)
    swaps=np.zeros(n);committed=np.zeros(n);margin=np.zeros(n)
    logs=np.zeros((n,9));ln=0;daily=np.zeros((end-start+1)//1440+4);di=0
    curve=np.zeros(((end-start)//60+2,4));cn=0
    balance=10000.;daybalance=10000.;peak=10000.;dd=0.;envdd=0.;worst=0.;eq=10000.
    goal_days=0;loss_days=0;blocked_day=0;blocked_risk=0;blocked_margin=0;blocked_lot=0
    firstbreach=-1.;envbreach=-1.;forced=0;maxrisk=0.;maxcount=0;stopped=-1.;reason=0
    daykey=-1;locked=False;liquidate=-1;trigger_day=-1;trigger_floor=0.;trigger_goal=0.
    max_loss_overshoot=0.;max_goal_underfill=0.
    phase=1 if lifecycle else 3;p1=-1.;p2=-1.;ready=start;trading_days=0;last_open_day=-1
    queue=0;first_entry=-1
    while queue<n and tr[queue,0]<start:queue+=1
    for t in range(start,end+1):
        ix=t-start;day=days[ix]
        if day!=daykey:
            if daykey>=0:
                daily[di]=balance-daybalance;di+=1
            daykey=day;daybalance=balance;locked=False
        # Native exits and previously scheduled liquidation use prices now known.
        k=0
        while k<count:
            i=active[k];r=tr[i];s=int(r[3]);close_kind=0;g=0.
            if r[1]<=t:
                g=r[6];close_kind=1;carry=swaps[i]
            elif liquidate>=0 and t>=liquidate and fresh[s,ix]:
                px=opens[s,ix,0]+(opens[s,ix,1] if r[9]<0 else 0.)
                g=gross(r,px,sp[s,0]);close_kind=reason
                carry=swaps[i]*min(1.,max(0.,t-r[0])/max(1.,r[1]-r[0]))
            if close_kind:
                g*=1.-edge_haircut if g>0 else 1.+edge_haircut
                net=(g-entrycost[i]-exitcost[i]+carry)*lots[i]
                balance+=(g-exitcost[i]+carry)*lots[i]
                logs[ln,0]=i;logs[ln,1]=r[0];logs[ln,2]=t;logs[ln,3]=lots[i]
                logs[ln,4]=net;logs[ln,5]=committed[i];logs[ln,6]=close_kind;logs[ln,7]=balance;logs[ln,8]=phase;ln+=1
                if close_kind>1:forced+=1
                count-=1;active[k]=active[count]
            else:k+=1
        if liquidate>=0 and count==0:
            if reason==2:max_loss_overshoot=max(max_loss_overshoot,trigger_floor-balance)
            if reason==3:max_goal_underfill=max(max_goal_underfill,trigger_goal-balance)
            liquidate=-1
            if day==trigger_day:locked=True
        floating=0.;bad=0.;openrisk=0.;usedmargin=0.
        for k in range(count):
            i=active[k];r=tr[i];s=int(r[3])
            px=prices[s,ix,0]+(prices[s,ix,1] if r[9]<0 else 0.)
            lowpx=prices[s,ix,2] if r[9]>0 else prices[s,ix,3]+prices[s,ix,1]
            g=gross(r,px,sp[s,0]);lo=gross(r,lowpx,sp[s,0])
            if t*60-60<r[13]:lo=g # Never use pre-entry bar extremes.
            g*=1.-edge_haircut if g>0 else 1.+edge_haircut
            lo*=1.-edge_haircut if lo>0 else 1.+edge_haircut
            carry=swaps[i]*min(1.,max(0.,t-r[0])/max(1.,r[1]-r[0]))
            floating+=(g-exitcost[i]+carry)*lots[i]
            bad+=(min(g,lo)-exitcost[i]+carry)*lots[i]
            openrisk+=committed[i];usedmargin+=margin[i]
        eq=balance+floating;loweq=balance+bad
        peak=max(peak,eq);dd=max(dd,(peak-eq)/peak*100);envdd=max(envdd,(peak-loweq)/peak*100)
        worst=max(worst,(daybalance-eq)/100.)
        if envbreach<0 and (loweq<9000.-1e-8 or loweq<daybalance-500.-1e-8):envbreach=float(t)
        if firstbreach<0 and (eq<9000.-1e-8 or eq<daybalance-500.-1e-8):firstbreach=float(t)
        if ix%60==0:
            curve[cn,0]=t;curve[cn,1]=eq;curve[cn,2]=balance;curve[cn,3]=openrisk;cn+=1
        if (ftmo and firstbreach>=0) or eq<=0:
            stopped=float(t);break
        # Optional research-stage endpoint. Defaults leave prior audit unchanged.
        stage_ready=(stop_profit>0 and balance>=10000.+stop_profit-1e-8 and trading_days>=min_days
                     and first_entry>=0 and t-first_entry>=min_age_days*1440)
        if stage_ready and count==0:
            stopped=float(t);break
        # Internal controls apply to net equity relative to midnight BALANCE.
        if not locked and liquidate<0:
            if loss>0 and eq<=daybalance-loss+1e-8:
                locked=True;loss_days+=1;reason=2;trigger_floor=daybalance-loss
                trigger_day=day;liquidate=t+delay
            elif target>0 and eq>=daybalance+target-1e-8:
                locked=True;goal_days+=1;reason=3;trigger_goal=daybalance+target
                trigger_day=day;liquidate=t+delay
        # Challenge passage is measured only once flat; no invented target exit.
        if lifecycle and count==0 and t>=ready and phase<3:
            phase_target=11000. if phase==1 else 10500.
            if balance>=phase_target and trading_days>=4:
                if phase==1:p1=float(t)
                else:p2=float(t)
                phase+=1;balance=10000.;eq=10000.;daybalance=10000.;peak=10000.
                trading_days=0;last_open_day=-1;locked=True
                # Start the next phase at next weekday's Prague day, an explicit zero-admin-delay lower bound.
                ready=t+1
                while ready<=end and (days[ready-start]==day or (days[ready-start]-1)%7>=5):ready+=1
        while queue<n and tr[queue,0]<=t:
            i=queue;queue+=1;r=tr[i];s=int(r[3])
            if locked or liquidate>=0 or t<ready or stage_ready:blocked_day+=1;continue
            riskbudget=risk_fraction*eq if compound else fixed_risk
            step=sp[s,3] if ftmo else sp[s,2];minimum=sp[s,5] if ftmo else sp[s,4]
            vol=math.floor((riskbudget/r[4]+1e-10)/step)*step
            if vol<minimum-1e-9 or vol<=0:blocked_lot+=1;continue
            risk=vol*r[4]
            if cap>0 and openrisk+risk>cap+1e-8:blocked_risk+=1;continue
            notional=sp[s,0]*(1. if s==2 else r[5])
            mg=notional*vol*(sp[s,7] if ftmo else sp[s,6])
            if usedmargin+mg>.8*max(0.,eq):blocked_margin+=1;continue
            native=max(0.,-r[7]);cost=native
            if ftmo:
                # Public rates treated conservatively as per-side; record this assumption.
                target_comm=sp[s,8]*2 if s in (2,6) else notional*sp[s,8]*2
                cost=max(native,target_comm)
            extra=sp[s,9]*sp[s,0]/(r[5] if s==2 else 1.) if stress else 0.
            entrycost[i]=cost/2+extra/2;exitcost[i]=cost/2+extra/2
            swaps[i]=r[8]*2 if stress and r[8]<0 else r[8]
            lots[i]=vol;committed[i]=risk;margin[i]=mg
            balance-=entrycost[i]*vol
            active[count]=i;count+=1;openrisk+=risk;usedmargin+=mg
            # Entry spread is already in native fill; don't charge it again here.
            eq-=entrycost[i]*vol
            maxrisk=max(maxrisk,openrisk);maxcount=max(maxcount,count)
            if last_open_day!=day:trading_days+=1;last_open_day=day
            if first_entry<0:first_entry=t
        # Equity after entries is fully remarked at the next observation.
    daily[di]=balance-daybalance;di+=1
    pos=0.;neg=0.;wins=0
    for j in range(ln):
        net=logs[j,4];pos+=max(0.,net);neg+=max(0.,-net);wins+=int(net>0)
    vals=np.array([eq,balance,(eq-10000.)/100.,dd,envdd,worst,ln,wins,pos,neg,goal_days,loss_days,
        blocked_day,blocked_risk,blocked_margin,blocked_lot,firstbreach,envbreach,forced,maxrisk,maxcount,
        p1,p2,balance-10000. if phase==3 and lifecycle else 0.,stopped,count,max_loss_overshoot,max_goal_underfill])
    return vals,logs[:ln],daily[:di],curve[:cn]

def specs():
    src=read(ROOT/'SOURCE_SPECS.json')['symbols'];tar={s['code']:s for s in read(ROOT/'FTMO_SPECS.json')}
    syms=['XAUUSD','USTEC','USDJPY','BTCUSD','ETHUSD','XAGUSD','EURUSD'];codes=['XAU/USD','US100.cash','USD/JPY','BTCUSD','ETHUSD','XAG/USD','EUR/USD']
    slip=[.2,2.,.02,30.,3.,.04,.0002];out=[]
    for i,s in enumerate(syms):
        a=src[s];b=tar[codes[i]];contract=a['trade_contract_size'];ratio=b['contractSize']/contract
        notional=contract*(1 if s=='USDJPY' else a['margin_quote'])
        normal=a['margin_one_lot_current']/notional
        rate=b['commission']/(100 if b['commissionType']=='percent' else ratio)
        out.append([contract,ratio,a['volume_step'],.01*ratio,a['volume_min'],.01*ratio,normal,1/b['leverageSwing'],rate,slip[i]])
    return np.array(out)

def configs():
    return [dict(name='Baseline',loss=0,target=0,cap=0)]+[
        dict(name=f'A loss{loss/100:g} goal{goal/100:g}',loss=loss,target=goal,cap=0) for loss in (200,250) for goal in (400,500)]+[
        dict(name=f'B risk2.5 goal{goal/100:g}',loss=0,target=goal,cap=250) for goal in (400,500)]

def main():
    output=[];sp=specs();save(ROOT/'MODEL_SPECS.json',sp.tolist());tic=time.time()
    for tag in ('','recent-'):
        a=read(ROOT/f'{tag}AUDIT.json');data=np.load(ROOT/f'{tag}prepared.npz');alltr=data['trades'];start=a['start'];end=a['end'];days=clock(start,end)
        groups=['FTMO13'] if tag else ['Broad33','NonNews29','FTMO13']
        for group in groups:
            keep=alltr[:,11]==1 if group=='FTMO13' else alltr[:,10]==0 if group=='NonNews29' else np.ones(len(alltr),bool)
            tr=alltr[keep]
            for ftmo in (False,True):
                for stress in (False,True):
                    for c in configs():
                        v,logs,daily,curve=run(tr,data['prices'],data['opens'],data['fresh'],sp,start,end,days,ftmo,c['loss'],c['target'],c['cap'],stress,False,False)
                        rid=f'{tag}{group}-{int(ftmo)}-{int(stress)}-{c["name"].replace(" ","_")}'
                        np.savez_compressed(ROOT/f'{rid}.npz',trades=tr,logs=logs,daily=daily,curve=curve)
                        row=dict(id=rid,group=group,period=tag or 'common-year',account='FTMO Swing' if ftmo else 'Normal capital',stress=stress,config=c,metrics=dict(zip(FIELDS,map(float,v))))
                        row['metrics']['profit_factor']=float(v[8]/v[9]) if v[9]>0 else None
                        row['metrics']['win_rate']=float(100*v[7]/v[6]) if v[6]>0 else None
                        output.append(row)
                    print(tag,group,ftmo,stress,'done',round(time.time()-tic,1),flush=True)
    save(ROOT/'RESULTS.json',output)

if __name__=='__main__':raise SystemExit('Research engine only; execute study.py in this directory.')
