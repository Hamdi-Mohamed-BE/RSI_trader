"""Public research data only. Never connects to or reads an MT5 account."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib, json, lzma, time, threading
import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'Data'
DATA.mkdir(exist_ok=True)
BASE = 'https://datafeed.dukascopy.com/datafeed/JPNIDXJPY'
DTYPE = np.dtype([('t','>i4'),('o','>i4'),('c','>i4'),('l','>i4'),('h','>i4'),('v','>f4')])
RATE_LIMIT=threading.Event()

def get_day(day, side):
    path = DATA / 'japan-bi5' / f'{day.date()}-{side}.bi5'
    path.parent.mkdir(exist_ok=True)
    url = f'{BASE}/{day.year}/{day.month-1:02d}/{day.day:02d}/{side}_candles_min_1.bi5'
    if path.exists():
        b = path.read_bytes()
    else:
        for attempt in range(3):
            if RATE_LIMIT.is_set(): return str(day.date()), side, None, 'not requested after rate limit'
            try:
                r = requests.get(url, timeout=18)
                if r.status_code==429:
                    RATE_LIMIT.set()
                    return str(day.date()), side, None, 'HTTP 429; stopped requests; retry-after='+str(r.headers.get('Retry-After'))
                if r.status_code in (404,204): return str(day.date()), side, None, f'HTTP {r.status_code}'
                r.raise_for_status(); b = r.content
                if b: lzma.decompress(b)
                path.write_bytes(b)
                break
            except Exception as e:
                if attempt == 2: return str(day.date()), side, None, str(e)
                time.sleep(0.5 * (attempt+1))
    if not b: return str(day.date()), side, None, 'empty'
    raw = lzma.decompress(b)
    assert len(raw) % 24 == 0
    a = np.frombuffer(raw, DTYPE)
    out = np.column_stack([day.timestamp()+a['t'],a['o']/1000,a['h']/1000,a['l']/1000,a['c']/1000,a['v']])
    assert (out[:,2] >= out[:,3]).all() and (np.diff(out[:,0]) > 0).all()
    return str(day.date()), side, out, hashlib.sha256(b).hexdigest()

def main():
    for name,url in {
        'SP500.csv':'https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500&cosd=2021-05-01&coed=2026-09-01',
        'ftmo-symbols.json':'https://ftmo.com/wp-json/ftmo/symbols',
    }.items():
        p=DATA/name
        if not p.exists():
            r=requests.get(url,timeout=30); r.raise_for_status(); p.write_bytes(r.content)
    days=[d for d in pd.date_range('2021-06-01','2026-08-31',tz='UTC') if d.weekday()!=5]
    jobs=[(d,s) for d in days for s in ('BID','ASK')]
    arrays={'BID':[],'ASK':[]}; manifest=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        fs=[pool.submit(get_day,*j) for j in jobs]
        for i,f in enumerate(as_completed(fs),1):
            day,side,a,status=f.result()
            manifest.append({'day':day,'side':side,'rows':0 if a is None else len(a),'status':status})
            if a is not None: arrays[side].append(a)
            if i%100==0: print(f'{i}/{len(jobs)} daily files inspected',flush=True)
    merged={s:np.concatenate(a) for s,a in arrays.items()}
    for s in merged: merged[s]=merged[s][np.argsort(merged[s][:,0])]
    incomplete=RATE_LIMIT.is_set() or any(x['rows']==0 and x['status'] not in ('empty','HTTP 404','HTTP 204') for x in manifest)
    np.savez_compressed(DATA/('japan-m1.partial.npz' if incomplete else 'japan-m1.npz'),**merged)
    (DATA/'download-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (DATA/'acquisition-status.json').write_text(json.dumps({'complete':not incomplete,'rate_limited':RATE_LIMIT.is_set(),'inspected_files':len(manifest)},indent=2),encoding='utf-8')
    print({s:a.shape for s,a in merged.items()},flush=True)

if __name__=='__main__': main()
