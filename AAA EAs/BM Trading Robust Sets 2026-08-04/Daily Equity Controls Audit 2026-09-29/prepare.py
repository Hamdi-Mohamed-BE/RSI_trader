"""Construct audited source trades and causal minute marks; no trading API."""
from pathlib import Path
from datetime import datetime,timezone
import importlib.util,json,hashlib,math
import sys
import numpy as np
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
CACHE=BASE.parent/'EA store/data/evidence-cache/v1'
SYMS=['XAUUSD','USTEC','USDJPY','BTCUSD','ETHUSD','XAGUSD','EURUSD']
START=int(datetime(2025,8,31,tzinfo=timezone.utc).timestamp()/60)
END=int(datetime(2026,8,31,tzinfo=timezone.utc).timestamp()/60)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def epoch(v):return datetime.fromisoformat(v).replace(tzinfo=timezone.utc).timestamp()

def main():
    global START,END
    recent='--recent' in sys.argv
    if recent:
        START=int(datetime(2025,9,27,tzinfo=timezone.utc).timestamp()/60)
        END=int(datetime(2026,9,25,tzinfo=timezone.utc).timestamp()/60)
    tag='recent-' if recent else ''
    spec=importlib.util.spec_from_file_location('order_audit',BASE/'FTMO Fourteen EA Study 2026-09-27/prepare.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    inv=read(ROOT/'INVENTORY.json'); specs=read(ROOT/'SOURCE_SPECS.json')['symbols']
    pkg=read(BASE/'FTMO Thirteen EA Deployment 2026-09-27/PACKAGE.json')
    ftmo_keys=[e['slug'] for e in pkg['entries']]
    rates={s:np.load(ROOT/f'{s}-M1.npz')['rates'] for s in SYMS}
    # Dense price arrays: values at t use only completed bars whose opening time <t.
    n=END-START+1;price=np.zeros((7,n,4),dtype=np.float64);fresh=np.zeros((7,n),bool)
    for si,s in enumerate(SYMS):
        a=rates[s];stamps=np.arange(START,END+1)*60
        idx=np.searchsorted(a['time'],stamps-60,side='right')-1
        assert idx.min()>=0
        b=a[idx];point=specs[s]['point']
        price[si,:,0]=b['close'];price[si,:,1]=b['spread']*point
        price[si,:,2]=b['low'];price[si,:,3]=b['high']
        nxt=np.searchsorted(a['time'],stamps)
        valid=nxt<len(a);fresh[si,valid]=a['time'][nxt[valid]]==stamps[valid]
        # Execution prices at observed minute opens are NOT forward-filled.
        if si==0:opens=np.zeros((7,n,2))
        opens[si,fresh[si],0]=a['open'][nxt[fresh[si]]]
        opens[si,fresh[si],1]=a['spread'][nxt[fresh[si]]]*point
    rows=[];audit=[];excluded=[]
    for e in inv:
        key=e['slug'];p=e['product'];mode=e['mode']
        choices=[c for c in e['choices'] if c['period']=='3y']
        if not choices:
            excluded.append(dict(ea=key,reason='No native comparable historical signal ledger'));continue
        c=choices[0];f=Path(c['trades']);native=CACHE/'source-runs'/key/mode/'3y.htm'
        oo=old.orders(native) if native.exists() else {}
        rr=[r for r in read(f) if START*60<=epoch(r['open_time'])<END*60]
        errors=[];out=[];mismatch=[]
        ep=p.get('dynamic_expert_source') if mode=='dynamic' else p['expert_source']
        ep=ep or p['expert_source']
        sp=p.get('dynamic_set_source') if mode=='dynamic' else p.get('safe_set_source') if mode=='safe' else p['set_source']
        sp=sp or p['set_source']
        for typ,rel in [('expert',ep),('settings',sp)]:
            path=BASE/rel;cached=c['meta'].get(typ+'_sha256')
            if cached and path.exists() and cached!=sha(path):mismatch.append(typ)
        for r in rr:
            op=epoch(r['open_time']);cl=epoch(r['close_time']);sym=e['symbol'];sgn=1 if r['side']=='Long' else -1
            found=oo.get((op,r['symbol'],r['side']),[])
            sl=r.get('stop') if key=='gold-overnight-value-area' else found[0]['stop'] if len(found)==1 else None
            if sl is None or sl<=0 or sgn*(r['open_price']-sl)<=0:
                errors.append(dict(number=r['number'],reason='missing/ambiguous/invalid original stop'));continue
            contract=specs[sym]['trade_contract_size'];move=sgn*(r['close_price']-r['open_price']);conv=r['close_price'] if sym=='USDJPY' else 1.
            expected=move*contract*r['volume']/conv
            ratio=1.
            if abs(expected-r['gross_profit'])>max(.1,abs(r['gross_profit'])*.005):
                # Contract units changed in some historic ETH source reports.
                inferred=(r['gross_profit']*conv/(move*r['volume'])) if abs(move)>1e-9 else 0
                rounded=min((1,10,100,5000,100000),key=lambda x:abs(x-inferred))
                if abs(inferred-rounded)>rounded*.005:
                    errors.append(dict(number=r['number'],reason='cash/price contract reconciliation failed'));continue
                ratio=contract/rounded
            assert abs(r['gross_profit']+r['commission']+r['swap']-r['net_profit'])<.05
            row=dict(r,key=key,symbol=sym,op=op,cl=cl,stop=sl,contract=contract,
                unit_risk=abs(r['open_price']-sl)*contract/(r['open_price'] if sym=='USDJPY' else 1),
                unit_gross=r['gross_profit']/r['volume']*ratio,unit_comm=r['commission']/r['volume']*ratio,
                unit_swap=r['swap']/r['volume']*ratio,news=key.startswith('news-'),ftmo=key in ftmo_keys)
            out.append(row)
        # Exclude the entire EA if any size-critical entry is missing: do not cherry-pick easy rows.
        if errors:excluded.append(dict(ea=key,reason='Incomplete initial stop/cash audit',errors=errors));out=[]
        rows+=out
        audit.append(dict(ea=key,mode=mode,source_rows=len(rr),accepted_rows=len(out),hash_mismatch=mismatch,
            trade_file=str(f),trade_sha=sha(f),report=str(native) if native.exists() else None,
            report_sha=sha(native) if native.exists() else None,source_meta=c['meta']))
    if recent:
        rows=read(BASE/'FTMO vs Stellar Instant Study 2026-09-28/rows.json')
        for r in rows:
            r.update(ftmo=True,news=False,contract=specs[r['symbol']]['trade_contract_size'])
        audit=[dict(note='Exact current FTMO13 source ledger reused; see source AUDIT.json',
            source=str(BASE/'FTMO vs Stellar Instant Study 2026-09-28/AUDIT.json'),
            source_sha=sha(BASE/'FTMO vs Stellar Instant Study 2026-09-28/rows.json'))]
        excluded=[]
    rows.sort(key=lambda r:(r['op'],r['key'],r['number']))
    keys=[e['slug'] for e in inv]
    # Trade matrix: entry/exit minute, key, symbol, initial risk/lot, entry, native gross/lot,
    # commission/lot, swap/lot, sign, news flag, FTMO membership, native exit, raw entry timestamp.
    tr=[]
    for r in rows:
        op=math.ceil(r['op']/60);cl=max(op+1,math.ceil(r['cl']/60))
        tr.append([op,cl,keys.index(r['key']),SYMS.index(r['symbol']),r['unit_risk'],r['open_price'],
            r['unit_gross'],r['unit_comm'],r['unit_swap'],1 if r['side']=='Long' else -1,int(r['news']),int(r['ftmo']),r['close_price'],r['op']])
    np.savez_compressed(ROOT/f'{tag}prepared.npz',trades=np.asarray(tr),prices=price,opens=opens,fresh=fresh)
    save(ROOT/f'{tag}ROWS.json',rows)
    save(ROOT/f'{tag}AUDIT.json',dict(start=START,end=END,keys=keys,symbols=SYMS,ftmo_keys=ftmo_keys,
        count=len(rows),eas=audit,excluded=excluded,method='M1 marked source-trade overlay, no regenerated EA signals',
        actual_attached_eas='Not verifiable via Python API; current catalogue/BAT basket, not proof all are attached locally'))
    print(json.dumps(dict(trades=len(rows),ftmo=sum(r['ftmo'] for r in rows),eas=len(set(r['key'] for r in rows)),excluded=excluded,
        mismatches=[(x['ea'],x['hash_mismatch']) for x in audit if x.get('hash_mismatch')])),flush=True)

if __name__=='__main__':main()
