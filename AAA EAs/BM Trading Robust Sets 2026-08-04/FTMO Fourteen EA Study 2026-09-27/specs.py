"""Read public FTMO instrument specifications; no account access."""
from pathlib import Path
from urllib.request import Request,urlopen
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parent
url='https://ftmo.com/wp-json/ftmo/symbols'
raw=urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
data=json.loads(raw)
selected=[s for s in data['data']['symbols'] if s['code'] in ('XAU/USD','US100.cash','USD/JPY')]
assert len(selected)==3
out=dict(source=url,fetched_at=datetime.now(timezone.utc).isoformat(),raw_sha256=hashlib.sha256(raw).hexdigest(),symbols=selected)
(ROOT/'FTMO_PUBLIC_SPECS.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps([{k:s[k] for k in ('code','contractSize','leverageSwing','commission','commissionType')} for s in selected]))
