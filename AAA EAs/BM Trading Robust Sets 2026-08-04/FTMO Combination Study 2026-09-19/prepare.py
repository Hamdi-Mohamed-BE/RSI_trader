"""Offline audit, stop reconstruction, and pre-period candidate selection."""
from __future__ import annotations
import json,sys,re,hashlib,math
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path(__file__).resolve().parent;P=ROOT.parent;STORE=P.parent/'EA store'
sys.path.insert(0,str(STORE))
from app.mt5_evidence_jobs import _read_report,_clean,_number
from app.catalog import get_catalog
CACHE=STORE/'data/evidence-cache/v1'
END=datetime(2026,9,5,tzinfo=timezone.utc).timestamp()
SPLIT=datetime(2024,9,19,tzinfo=timezone.utc).timestamp()
DAY=86400;WEEK=604800;RAW='gold-overnight-value-area/standard'
SPECS={'XAUUSD':(100,15),'XAGUSD':(5000,15),'USTEC':(1,15),'USDJPY':(100000,30),'EURUSD':(100000,30),'BTCUSD':(1,1),'ETHUSD':(10,1)}
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def dt(s):
    d=datetime.fromisoformat(s.replace('Z','+00:00'));return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).timestamp()
def iso(t):return datetime.fromtimestamp(t,timezone.utc).isoformat() if t is not None else None
def orders(path):
    if not path.is_file():return {}
    s=_read_report(path);i=s.lower().find('<b>orders</b>');j=s.lower().find('<b>deals</b>');out=defaultdict(list)
    if i<0:return {}
    for row in re.findall(r'<tr\b[^>]*>(.*?)</tr>',s[i:j],re.I|re.S):
        c=[_clean(v) for v in re.findall(r'<td\b[^>]*>(.*?)</td>',row,re.I|re.S)]
        if len(c)<11 or not re.fullmatch(r'\d{4}\.\d{2}\.\d{2} \d{2}:\d{2}:\d{2}',c[0]) or c[9]!='filled':continue
        if not c[6] or c[3].lower() not in ('buy','sell','buy stop','sell stop','buy limit','sell limit'):continue
        key=(dt(c[8].replace('.','-',2).replace(' ','T')),c[2],'Long' if c[3].startswith('buy') else 'Short')
        out[key].append(dict(stop=_number(c[6]),target=_number(c[7]),order_price=_number(c[5]),order_type=c[3],placed=dt(c[0].replace('.','-',2).replace(' ','T'))))
    return out
def costs(r,stress=False):
    # Values per target-broker lot. Recorded spread and gap fills remain in gross.
    sym=r['symbol'];contract=SPECS[sym][0]
    g=r['unit_gross'];c=r['unit_comm'];s=r['unit_swap']
    if sym in ('BTCUSD','ETHUSD'):c=min(c,-.000325*contract*(r['open_price']+r['close_price']))
    else:c=min(c,-(47.5 if sym=='XAGUSD' else .7 if sym=='USTEC' else 7.))
    extra=0.
    if stress:
        news=r['news']
        g*=.9 if g>0 else 1.1
        slip={'XAUUSD':1. if news else .2,'XAGUSD':.04,'USTEC':2.,'EURUSD':.0002,'USDJPY':.02,'BTCUSD':30.,'ETHUSD':3.}[sym]
        extra=slip*contract/(r['open_price'] if sym=='USDJPY' else 1.)
        s=min(s*2,0.)
        if r['cl']-r['op']>DAY:
            # Explicit additional carry reserve, not historical FTMO swap data.
            notional=contract*(1 if sym=='USDJPY' else r['open_price'])
            s=min(s,-notional*.00015*math.ceil((r['cl']-r['op'])/DAY))
    return g,c,s,extra
def stats(rr,stress=False):
    vals=[sum(costs(r,stress)[:3])-costs(r,stress)[3] for r in rr]
    vals=[v/r['unit_risk'] for v,r in zip(vals,rr)]
    pos=sum(max(0,v) for v in vals);neg=-sum(min(0,v) for v in vals)
    peak=bal=dd=0.;ws=ls=mw=ml=0
    for v in vals:
        bal+=v;peak=max(peak,bal);dd=max(dd,peak-bal)
        ws=ws+1 if v>0 else 0;ls=ls+1 if v<0 else 0;mw=max(mw,ws);ml=max(ml,ls)
    return dict(trades=len(rr),win_rate=100*sum(v>0 for v in vals)/len(vals) if vals else 0,pf=pos/neg if neg else None,sum_r=sum(vals),dd_r=dd,max_win_streak=mw,max_loss_streak=ml)
def prepare():
    active={p.slug for p in get_catalog()};rows={};audit=[];excluded=[]
    for path in sorted((CACHE/'products').glob('*/*/5y.trades.json')):
        slug,mode=path.parts[-3:-1];key=slug+'/'+mode
        if slug.startswith('news-pulse-'):continue
        rr=read(path);original=len(rr);native=orders(CACHE/'source-runs'/slug/mode/'5y.htm');out=[];missing=0;bad=0
        if not rr or any(any(k not in r for k in ('gross_profit','commission','swap','volume','open_price','close_price')) for r in rr):
            excluded.append(dict(key=key,reason='Incomplete native cost/volume/price fields'));continue
        for raw in rr:
            sym=raw['symbol'].rstrip('r');sym='USTEC' if sym in ('US100','NAS100','USTEC') else sym
            if sym not in SPECS:bad+=1;continue
            r=dict(raw,symbol=sym,key=key,news=False,op=dt(raw['open_time']),cl=dt(raw['close_time']))
            if r['op']>=END:continue
            if r['cl']<=r['op']:r['cl']=r['op']+.001
            contract=SPECS[sym][0]
            # Contract inferred from native cash/price is robust to ETH's 1->10 conversion.
            move=abs(r['close_price']-r['open_price']);inferred=abs(r['gross_profit'])/move/r['volume'] if move>.0000001 and abs(r['gross_profit'])>.05 else contract
            source_contract=(100000 if sym=='USDJPY' else min((1,10,100,5000,100000),key=lambda c:abs(c-inferred)))
            conversion=contract/source_contract
            match=native.get((r['op'],raw['symbol'],r['side']),[])
            if key==RAW:stop=r['stop'];quality='native_entry_audit'
            elif len(match)==1:stop=match[0]['stop'];quality='native_entry_order'
            else:missing+=1;continue # do not silently size from website estimated R
            sign=1 if r['side']=='Long' else -1
            if sign*(r['open_price']-stop)<=0:bad+=1;continue
            r.update(stop=stop,unit_risk=abs(r['open_price']-stop)*contract/(r['open_price'] if sym=='USDJPY' else 1.),risk_quality=quality)
            for name in ('gross_profit','commission','swap'):
                r[{'gross_profit':'unit_gross','commission':'unit_comm','swap':'unit_swap'}[name]]=r[name]/r['volume']*conversion
            assert abs(r['gross_profit']+r['commission']+r['swap']-r['net_profit'])<.04
            out.append(r)
        if not out or (missing+bad)/max(1,original)>.05:
            excluded.append(dict(key=key,reason='Missing/ambiguous initial stop or unsupported asset on >5% of rows',total=original,missing=missing,bad=bad));continue
        out.sort(key=lambda r:r['cl']);rows[key]=out
        audit.append(dict(key=key,active=slug in active,original=original,accepted=len(out),missing=missing,bad=bad,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          train=stats([r for r in out if r['cl']<SPLIT],True),recent=stats([r for r in out if r['op']>=SPLIT],True),full=stats(out),full_stress=stats(out,True)))
    # Read current, event-fitted native research trades and logged pre-event placements.
    placements=[]
    roots={'xau':P/'News Pulse Event Parameters Research 2026-09-19','xag':P/'News Pulse Multi Asset Event Parameters 2026-09-19','btc':P/'News Pulse Multi Asset Event Parameters 2026-09-19','eurusd':P/'News Pulse Multi Asset Event Parameters 2026-09-19'}
    params=read(P/'AAA Final EAs/AAA Final News Pulse Multi Asset Event EA/EVENT PARAMETERS.json')
    pat=r'News Pulse: (NFP|CPI|FOMC) two-sided orders placed\. Buy ([\d.]+), sell ([\d.]+), SL distance \$([\d.]+),.*?Server placement=([\d.]+ [\d:]+), event=([\d.]+ [\d:]+), lead=(\d+)s'
    for asset,folder in roots.items():
        key=f'news-pulse-{asset}/standard';native=folder/'native'/('NativeFullBestV2' if asset=='xau' else asset.upper()+'Fitted')
        ps={}
        for m in re.finditer(pat,(native/'journal.txt').read_text(encoding='utf-8')):
            kind,buy,sell,sl,placed,epoch,lead=m.groups();epoch=dt(epoch.replace('.','-',2).replace(' ','T'));placed=dt(placed.replace('.','-',2).replace(' ','T'))
            hold=(300 if kind=='CPI' else 120 if kind=='FOMC' else 60) if asset=='xau' else params[asset.upper()][kind][7]
            if epoch>=END:continue
            exact_sl=2. if asset=='xau' else params[asset.upper()][kind][3]
            ps[epoch]=dict(key=key,kind=kind,epoch=epoch,op=placed,until=epoch+hold+1,buy=float(buy),sell=float(sell),sl=exact_sl,symbol=asset.upper()+'USD' if asset!='eurusd' else 'EURUSD')
        placements+=list(ps.values());out=[]
        for raw in read(native/'trades.json'):
            event=int(raw['entry_comment'].split('|')[1]);op=dt(raw['open_time']);cl=dt(raw['close_time'])
            if op>=END:continue
            if event not in ps:raise AssertionError((key,event))
            sym=ps[event]['symbol'];contract=SPECS[sym][0]
            r=dict(raw,key=key,news=True,op=op,cl=max(op+.001,cl),symbol=sym,event=event,unit_risk=ps[event]['sl']*contract,risk_quality='native_logged_placement')
            for name in ('gross_profit','commission','swap'):r[{'gross_profit':'unit_gross','commission':'unit_comm','swap':'unit_swap'}[name]]=r[name]/r['volume']
            out.append(r)
        rows[key]=out;audit.append(dict(key=key,active=True,accepted=len(out),selection_bias='full-year hindsight fit',full=stats(out),full_stress=stats(out,True)))
    eligible=[a for a in audit if 'train' in a and a['train']['trades']>=50 and a['train']['sum_r']>0 and (a['train']['pf'] or 0)>1.05]
    best={}
    for a in eligible:
        slug=a['key'].split('/')[0];score=a['train']['sum_r']/max(5,a['train']['dd_r'])
        if slug not in best or score>best[slug][0]:best[slug]=(score,a)
    ranked=sorted(best.values(),key=lambda x:x[0],reverse=True)
    high=sorted(best.values(),key=lambda x:(x[1]['train']['win_rate'],x[0]),reverse=True)
    save(ROOT/'prepared.json',dict(rows=rows,placements=placements))
    save(ROOT/'audit.json',dict(end_exclusive=iso(END),train_before=iso(SPLIT),eas=audit,excluded=excluded,ranked=[v[1]['key'] for v in ranked],high_win=[v[1]['key'] for v in high]))
    print('PREPARED',len(rows),'variants; excluded',len(excluded),flush=True)
    print('RANKED',[(v[1]['key'],v[1]['train']) for v in ranked[:8]],flush=True)
    print('HIGH WIN',[(v[1]['key'],v[1]['train']['win_rate']) for v in high[:6]],flush=True)
if __name__=='__main__':prepare()
