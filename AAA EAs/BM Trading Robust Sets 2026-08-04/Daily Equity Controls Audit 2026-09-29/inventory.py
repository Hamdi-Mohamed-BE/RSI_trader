"""Read-only evidence inventory; never starts or changes an EA."""
from pathlib import Path
import json, urllib.request

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
CACHE = BASE.parent / 'EA store/data/evidence-cache/v1'

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    products = json.load(urllib.request.urlopen('http://127.0.0.1:8080/api/eas'))
    out = []
    for p in products:
        mode = 'dynamic' if p['recommended_dynamic_mode'] else 'safe' if p['recommended_safe_mode'] else 'standard'
        choices = []
        for period in ('1y', '3y', '5y'):
            f = CACHE/'products'/p['slug']/mode/f'{period}.trades.json'
            meta = CACHE/'source-runs'/p['slug']/mode/f'{period}.meta.json'
            if f.exists():
                rows=read(f); m=read(meta) if meta.exists() else {}
                choices.append(dict(period=period, count=len(rows), start=m.get('from'), end=m.get('to'), first=min((r['open_time'] for r in rows),default=None), last=max((r['close_time'] for r in rows),default=None), trades=str(f),meta=m))
        out.append(dict(slug=p['slug'], mode=mode, symbol=p['canonical'], product=p,choices=choices))
    (ROOT/'INVENTORY.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    for x in out:
        print(x['slug'],x['mode'],[(c['period'],c['count'],c['start'],c['end']) for c in x['choices']])

if __name__=='__main__':main()
