"""Offline, minute-equity, paired prop-firm scenario replay. NO trading imports."""
"""Versioned research fork: corrected minimum lots, causal multipliers, conservative QuickStrike block."""
from pathlib import Path
import json, math, hashlib, time, sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np
from numba import njit
ROOT=Path(__file__).resolve().parent
DAY=1440
HORIZONS=np.array([30,60,120,180],dtype=np.int64)
UTC=timezone.utc
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def epoch(y,m,d):return int(datetime(y,m,d,tzinfo=UTC).timestamp()/60)
CONFIGS=[
 dict(name='FTMO full13 0.25%',firm='FTMO',capital=10000,risk=.0025,core=False,existing=False,withdraw_all=False),
 dict(name='FTMO full13 0.50%',firm='FTMO',capital=10000,risk=.005,core=False,existing=False,withdraw_all=False),
 dict(name='FTMO existing guards 0.50%',firm='FTMO',capital=10000,risk=.005,core=False,existing=True,withdraw_all=False),
 dict(name='Instant full13 0.15%',firm='Instant',capital=5000,risk=.0015,core=False,existing=False,withdraw_all=False),
 dict(name='Instant full13 0.25%',firm='Instant',capital=5000,risk=.0025,core=False,existing=False,withdraw_all=False),
 dict(name='Instant core4 0.25%',firm='Instant',capital=5000,risk=.0025,core=True,existing=False,withdraw_all=False),
 dict(name='Instant core4 0.25% all-profit withdrawal',firm='Instant',capital=5000,risk=.0025,core=True,existing=False,withdraw_all=True),
]
# snapshot fields are intentionally explicit; percentages always use all starts.
FIELDS=['balance','phase','trades','wins','positive','negative','sampled_dd_pct','envelope_dd_pct','worst_daily_pct',
        'phase1_minute','phase2_minute','funded_minute','first_request_minute','first_cash','total_cash','breach_minute',
        'breach_phase','max_win_streak','max_loss_streak','payout_count','minimum_headroom','news_deducted','quickstrike_blocked',
        'last_entry_minute','ending_loss_floor','open_positions','compliance_block_minute']
REJECT=['lot','margin','risk','daily','loss_stop','phase_wait','same_ea','payout_pause']

def clocks(start,end):
    # Precomputed civil-midnight and weekday clocks; no assumed fixed Prague UTC offset.
    n=end-start+1
    minute=np.arange(start,end+1)
    dates=[datetime.fromtimestamp(int(t)*60,UTC) for t in range(start,end+1,60)]
    def series(zone):
        vals=np.array([x.astimezone(zone).date().toordinal() for x in dates],dtype=np.int32)
        # Local DST offsets change only on hour boundaries. All starts are UTC midnight.
        return np.repeat(vals,60)[:n]
    prague=series(ZoneInfo('Europe/Prague'))
    server=series(ZoneInfo('Europe/Helsinki'))
    weekday=np.repeat(np.array([x.weekday() for x in dates],dtype=np.int32),60)[:n]
    return np.column_stack([prague,server,weekday])

@njit(cache=True)
def business_ready(t,n,start,clock):
    while n>0:
        t+=DAY
        j=t-start
        if j>=len(clock) or clock[j,2]<5:n-=1
    return t

@njit(cache=True)
def fees(r,instant,stress):
    sym=int(r[3]);price=r[5];native=abs(r[7]);native_swap=min(r[8],0.)
    duration=max(1.,r[1]-r[0])
    if instant:
        commission=max(native, .000016*100*price if sym==0 else 7. if sym==2 else .7)
        entry=commission;exitfee=0.
    else:
        commission=max(native, .000014*100*price*2 if sym==0 else 10. if sym==2 else .7)
        entry=commission/2;exitfee=commission/2
    extra=0.
    swap=native_swap
    if stress:
        extra=20. if sym==0 else 2. if sym==1 else .02*100000/price
        notional=100*price if sym==0 else price if sym==1 else 100000.
        swap=min(native_swap*2,-notional*.00015*math.ceil(duration/DAY)) if duration>DAY else native_swap*2
    return entry+extra/2,exitfee+extra/2,swap

@njit(cache=True)
def run(tr, pc, pl, start,end,clock,capital,risk,instant,existing,withdraw_all,stress,envelope,lifecycle,horizons):
    n=len(tr)
    active=np.full(32,-1,np.int64);lots=np.zeros(n);opening_fee=np.zeros(n);closing_fee=np.zeros(n);swaps=np.zeros(n)
    accepted=np.zeros(13,np.int64);rejected=np.zeros((13,8),np.int64)
    logs=np.zeros((n,7));logn=0
    snapshots=np.full((len(horizons),27),np.nan)
    bal=capital;floor=capital*(.94 if instant else .90);high=capital;ratchet_offset=0.
    phase=3 if instant or not lifecycle else 1
    phase1=-1.;phase2=-1.;funded=0. if instant or not lifecycle else -1.
    first_request=-1.;first_cash=0.;cash=0.;breach=-1.;breach_phase=0
    ready=start;cycle_start=-1;cycle_base=capital;trade_days=0;last_open_day=-1
    daybal=capital;daykey=-1;lossesday=0;entriesday=0
    peak=capital;dd=0.;lowdd=0.;dailyworst=0.;minhead=capital-floor
    trades=0;wins=0;positive=0.;negative=0.;ws=0;ls=0;mw=0;ml=0;payouts=0;newsdeduct=0.;quickblocked=0
    cycle_wins=0.;cycle_quick=0.;queue=0;nh=0;countactive=0
    last_entry=-1.;compliance=-1.
    while queue<n and tr[queue,0]<start:queue+=1
    for t in range(start,end+1):
        ix=t-start
        day=int(clock[ix,1 if instant else 0])
        if day!=daykey:
            daykey=day;daybal=bal;lossesday=0;entriesday=0
        is_eod=ix>0 and clock[ix,1]!=clock[ix-1,1]
        if not instant and lifecycle and phase==3 and funded<0 and t>=ready:funded=float(t-start)
        floating=0.;adverse=0.;reserved=0.;usedmargin=0.;symrisk=np.zeros(3)
        for slot in range(32):
            i=active[slot]
            if i<0:continue
            r=tr[i];age=t-int(r[0]);p=min(max(0,age-1),int(r[10])-1)+int(r[9])
            g=float(pc[p]);lo=float(pl[p])
            if age==0:g=0.;lo=0.
            if stress:
                g*=.9 if g>0 else 1.1;lo*=.9 if lo>0 else 1.1
            carry=swaps[i]*min(1.,age/max(1.,r[1]-r[0]))
            floating+=(g+carry-closing_fee[i])*lots[i]
            adverse+=(lo+carry-closing_fee[i])*lots[i]
            rr=r[4]*lots[i]
            reserved+=rr*1.25+capital*.0005
            symrisk[int(r[3])]+=rr
            lev=7.5 if instant and r[3]==0 else 5. if instant and r[3]==1 else 30. if r[3]==2 else 15.
            usedmargin+=lots[i]*(100*r[5] if r[3]==0 else r[5] if r[3]==1 else 100000.)/lev
        eq=bal+floating;loweq=bal+adverse
        peak=max(peak,eq);dd=max(dd,(peak-eq)/capital*100);lowdd=max(lowdd,(peak-loweq)/capital*100)
        dailyworst=max(dailyworst,(daybal-loweq)/capital*100)
        minhead=min(minhead,loweq-floor)
        checked=loweq if envelope else eq
        if breach<0 and (checked<=floor+1e-8 or (not instant and checked<=daybal-.05*capital+1e-8)):
            breach=float(t-start);breach_phase=phase
        # Close at the audited native exit, after checking the previous minute's equity.
        if breach<0:
            for slot in range(32):
                i=active[slot]
                if i<0 or tr[i,1]>t:continue
                r=tr[i];gross=r[6]*(.9 if stress and r[6]>0 else 1.1 if stress else 1.)
                net=(gross-opening_fee[i]-closing_fee[i]+swaps[i])*lots[i]
                close_cash=(gross-closing_fee[i]+swaps[i])*lots[i]
                # Raise Instant floor on pre-deduction profit; take deductions immediately, conservatively.
                if instant:
                    high=max(high,bal+close_cash+ratchet_offset);floor=max(floor,min(capital,high-.06*capital))
                deduction=0.
                if instant and net>0:
                    deduction=net*(.6 if r[12]>0 else .10 if stress else 0.)
                if net>0:cycle_wins+=net;cycle_quick+=net if r[13]>0 else 0.
                net-=deduction;newsdeduct+=deduction
                bal+=close_cash-deduction
                trades+=1;wins+=int(net>0);positive+=max(0.,net);negative+=max(0.,-net)
                if net>0:ws+=1;ls=0
                elif net<0:ls+=1;ws=0;lossesday+=1
                else:ws=0;ls=0
                mw=max(mw,ws);ml=max(ml,ls)
                logs[logn,0]=i;logs[logn,1]=r[0];logs[logn,2]=t;logs[logn,3]=lots[i];logs[logn,4]=net;logs[logn,5]=r[4]*lots[i];logs[logn,6]=bal;logn+=1
                active[slot]=-1;countactive-=1
            if bal<=floor+1e-8:
                breach=float(t-start);breach_phase=phase
        # Lifecycle actions require no open positions; no unobserved liquidation assumed.
        if breach<0 and countactive==0 and t>=ready:
            if lifecycle and not instant and phase<3:
                target=capital*(1.10 if phase==1 else 1.05)
                if bal>=target and trade_days>=4:
                    if phase==1:phase1=float(t-start)
                    else:phase2=float(t-start)
                    ready=business_ready(t,2 if phase==1 else 5,start,clock)
                    phase+=1;bal=capital;daybal=capital;floor=.9*capital;high=capital;peak=capital
                    trade_days=0;last_open_day=-1;lossesday=0;entriesday=0;cycle_start=-1;cycle_base=capital;cycle_wins=0.;cycle_quick=0.
            elif lifecycle and phase==3 and cycle_start>=0:
                aged=t-cycle_start>=14*DAY
                growth=bal-cycle_base
                eligible=(growth>=.01*capital and aged) or (instant and growth>=.05*capital and is_eod)
                if not instant:eligible=aged and bal-capital>=25.
                if eligible:
                    if instant and cycle_wins>0 and cycle_quick/cycle_wins>=.30 and min(bal-capital,bal-floor-.03*capital)>=.01*capital:
                        quickblocked+=1;compliance=float(t-start)
                    else:
                        gross=max(0.,bal-capital)
                        if instant and not withdraw_all:gross=min(gross,max(0.,bal-floor-.03*capital))
                        minimum=.01*capital if instant else 25.
                        if gross+1e-8>=minimum:
                            paid=gross*(.7 if instant else .8)
                            if first_request<0:first_request=float(t-start);first_cash=paid
                            bal-=gross;daybal-=gross;cash+=paid;payouts+=1
                            # Post-withdrawal anchor: conservative cycle-relative ratchet, never lower the floor.
                            if instant:
                                high=floor+.06*capital;ratchet_offset=high-bal
                            cycle_base=bal;cycle_start=-1;cycle_wins=0.;cycle_quick=0.;peak=bal
                            if bal<=floor+1e-8:breach=float(t-start);breach_phase=phase
        while queue<n and tr[queue,0]<=t:
            i=queue;queue+=1;r=tr[i];key=int(r[2]);sym=int(r[3])
            if r[0]<start or breach>=0 or compliance>=0:continue
            if t<ready:rejected[key,5]+=1;continue
            if lifecycle and not instant and phase<3 and bal>=capital*(1.10 if phase==1 else 1.05) and trade_days>=4:
                rejected[key,7]+=1;continue
            # Pause new entries when a withdrawal would be possible once existing trades finish.
            if lifecycle and phase==3 and cycle_start>=0:
                if (t-cycle_start>=14*DAY and bal-cycle_base>=(capital*.01 if instant else 25.)) or (instant and bal-cycle_base>=.05*capital):
                    # Do not freeze a retained-buffer policy forever if there is nothing withdrawable.
                    available=bal-capital
                    if instant and not withdraw_all:available=min(available,bal-floor-.03*capital)
                    quick_ok=(not instant) or cycle_wins<=0 or cycle_quick/cycle_wins<.30
                    if available>=(capital*.01 if instant else 25.) and quick_ok:rejected[key,7]+=1;continue
            duplicate=False
            for slot in range(32):
                j=active[slot]
                if j>=0 and int(tr[j,2])==key:duplicate=True
            if duplicate:rejected[key,6]+=1;continue
            if lossesday>=3:rejected[key,4]+=1;continue
            if entriesday>=7:rejected[key,3]+=1;continue
            # Rebuild open risk/margin after closes and earlier same-minute entries.
            rr_total=0.;rr_sym=0.;reserved=0.;usedmargin=0.;floating=0.
            for slot in range(32):
                j=active[slot]
                if j<0:continue
                q=tr[j];rr=q[4]*lots[j];rr_total+=rr;rr_sym+=rr if int(q[3])==sym else 0.
                reserved+=rr*1.25+capital*.0005
                lev=7.5 if instant and q[3]==0 else 5. if instant and q[3]==1 else 30. if q[3]==2 else 15.
                usedmargin+=lots[j]*(100*q[5] if q[3]==0 else q[5] if q[3]==1 else 100000.)/lev
                age=t-int(q[0]);p=min(max(0,age-1),int(q[10])-1)+int(q[9]);g=float(pc[p]) if age>0 else 0.
                if stress:g*=.9 if g>0 else 1.1
                floating+=(g+swaps[j]*min(1.,age/max(1.,q[1]-q[0]))-closing_fee[j])*lots[j]
            eq=bal+floating
            head=max(0.,min(eq,bal)-floor-capital*.002)
            risk_cap=min(capital*risk*r[14],.05*head) if instant else capital*risk*r[14]
            lot=math.floor(risk_cap/r[4]/.01+1e-9)*.01
            if lot<(.05 if sym==1 else .01)-1e-9:rejected[key,0]+=1;continue
            wanted=r[4]*lot;newreserve=wanted*1.25+capital*.0005
            agg=.2*head if instant else capital*(.0225 if existing else .015)
            cap_sym=.1*head if instant else capital*(.015 if existing else .0075)
            riskcheck=reserved+newreserve if instant else rr_total+wanted
            if riskcheck>agg+1e-8 or rr_sym+wanted>cap_sym+1e-8 or min(eq,bal-reserved)-newreserve<=floor+(.002 if instant else .02)*capital:
                rejected[key,2]+=1;continue
            if min(eq,bal-reserved)-newreserve<=daybal-capital*(.0075 if instant else .03 if existing else .015):
                rejected[key,3]+=1;continue
            lev=7.5 if instant and sym==0 else 5. if instant and sym==1 else 30. if sym==2 else 15.
            margin=lot*(100*r[5] if sym==0 else r[5] if sym==1 else 100000.)/lev
            if usedmargin+margin>min(eq,bal)*(.8 if existing else .3):rejected[key,1]+=1;continue
            efee,cfee,swap=fees(r,instant,stress)
            slots=np.where(active<0)[0]
            if len(slots)==0:rejected[key,2]+=1;continue
            active[slots[0]]=i;lots[i]=lot;opening_fee[i]=efee;closing_fee[i]=cfee;swaps[i]=swap
            bal-=efee*lot;countactive+=1;accepted[key]+=1;entriesday+=1
            last_entry=float(t-start)
            if last_open_day!=day:trade_days+=1;last_open_day=day
            if cycle_start<0:cycle_start=t
        while nh<len(horizons) and t-start>=horizons[nh]*DAY:
            snapshots[nh]=np.array([bal,float(phase),float(trades),float(wins),positive,negative,dd,lowdd,dailyworst,
                phase1,phase2,funded,first_request,first_cash,cash,breach,float(breach_phase),float(mw),float(ml),float(payouts),minhead,newsdeduct,float(quickblocked),last_entry,floor,float(countactive),compliance])
            nh+=1
        if nh==len(horizons):break
        if breach>=0 or compliance>=0:
            # Absorbing breach or conservative compliance block: carry state to later horizons without post-failure trading.
            while nh<len(horizons) and horizons[nh]*DAY<=end-start:
                snapshots[nh]=np.array([bal,float(phase),float(trades),float(wins),positive,negative,dd,lowdd,dailyworst,
                    phase1,phase2,funded,first_request,first_cash,cash,breach,float(breach_phase),float(mw),float(ml),float(payouts),minhead,newsdeduct,float(quickblocked),last_entry,floor,float(countactive),compliance])
                nh+=1
            break
    return snapshots,accepted,rejected,logs[:logn]

def clean(v):
    if isinstance(v,np.bool_):return bool(v)
    if isinstance(v,np.ndarray):return clean(v.tolist())
    if isinstance(v,list):return [clean(x) for x in v]
    if isinstance(v,dict):return {k:clean(x) for k,x in v.items()}
    if isinstance(v,(float,np.floating)):return None if not np.isfinite(v) else float(v)
    if isinstance(v,np.integer):return int(v)
    return v
def summarize(out):
    ans=[]
    for hi,h in enumerate(HORIZONS):
        xs=np.array([p[hi] for p in out]);xs=xs[~np.isnan(xs[:,0])]
        if not len(xs):continue
        col=lambda name:xs[:,FIELDS.index(name)]
        paid=col('first_request_minute')>=0;failed=col('breach_minute')>=0;blocked=col('compliance_block_minute')>=0
        before=failed & (~paid | (col('breach_minute')<col('first_request_minute')))
        after=failed & paid & ~before
        def timing(name):
            v=col(name);v=v[v>=0]/DAY
            return dict(n=len(v),p10=float(np.quantile(v,.1)),median=float(np.median(v)),p90=float(np.quantile(v,.9))) if len(v) else None
        ans.append(dict(days=int(h),starts=len(xs),phase1=int(sum(col('phase1_minute')>=0)),phase2=int(sum(col('phase2_minute')>=0)),
                        funded=int(sum(col('funded_minute')>=0)),payout=int(sum(paid)),breach_before=int(sum(before)),breach_after=int(sum(after)),
                        compliance_blocked=int(sum(blocked)),unresolved=int(sum(~paid & ~failed & ~blocked)),payout_pct=100*float(np.mean(paid)),breach_before_pct=100*float(np.mean(before)),
                        breach_total_pct=100*float(np.mean(failed)),funded_pct=100*float(np.mean(col('funded_minute')>=0)),
                        timing={name:timing(name) for name in ['phase1_minute','phase2_minute','funded_minute','first_request_minute']},
                        mean_cash=float(np.mean(col('total_cash'))),median_cash_if_paid=float(np.median(col('total_cash')[paid])) if paid.any() else None,
                        mean_first_cash=float(np.mean(np.where(paid,col('first_cash'),0))),
                        base_fee_recovered=int(sum(col('total_cash')>=104.99)),fee_plus25_recovered=int(sum(col('total_cash')>=129.99)),
                        fee_plus50_recovered=int(sum(col('total_cash')>=154.99)),regular_fee_recovered=int(sum(col('total_cash')>=149.99)),
                        median_trades=float(np.median(col('trades'))),max_sampled_dd=float(np.max(col('sampled_dd_pct'))),max_envelope_dd=float(np.max(col('envelope_dd_pct')))))
        ans[-1]['no_entry_last30days']=int(sum((~failed)&((col('last_entry_minute')<0)|(col('last_entry_minute')<(h-30)*DAY))))
        ans[-1]['median_ending_balance_headroom']=float(np.median(col('balance')-col('ending_loss_floor')))
        first=col('first_cash')[paid]
        ans[-1]['median_first_cash_if_paid']=float(np.median(first)) if len(first) else None
    return ans

def scenario_matrix(tr,audit,cfg):
    keys=audit['keys'];allowed=[keys.index(k) for k in audit['core']] if cfg['core'] else list(range(13))
    return tr[np.isin(tr[:,2],allowed)].copy()
def invoke(tr,pc,pl,start,end,clock,cfg,stress,envelope=True,lifecycle=True,horizons=HORIZONS):
    return run(tr,pc,pl,start,end,clock,float(cfg['capital']),cfg['risk'],cfg['firm']=='Instant',cfg['existing'],cfg['withdraw_all'],stress,envelope,lifecycle,horizons)

