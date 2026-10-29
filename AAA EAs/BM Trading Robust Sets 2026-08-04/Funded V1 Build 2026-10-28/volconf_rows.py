"""ORB VP Volume Confirmed 0.5R 5y native run -> per-trade simulation rows (unit risk / unit net per 1 lot), same convention as RISK_ROWS.
Entry orders (with their S/L) and deals come from the native MT5 report; a position = an entry order + its closing deal(s) matched by
position ticket in the deals table. Net includes commission and swap. python volconf_rows.py -> VOLCONF_05R_ROWS.json"""
import gzip, json, re
from datetime import datetime, timezone
from html import unescape
from pathlib import Path

R = Path(__file__).resolve().parent
D = R / 'native/nw-XAUUSD-volconf-05R-5y'
html = gzip.decompress((D / 'nw-XAUUSD-volconf-05R-5y.htm.gz').read_bytes())
html = html.decode('utf-16' if html[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8', errors='replace')
def table(chunk):
    out = []
    for tr in re.findall(r'<tr[^>]*>(.*?)</tr>', chunk, re.S | re.I):
        cells = [unescape(re.sub(r'<[^>]+>', '', c)).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S | re.I)]
        if cells and re.match(r'\d{4}\.\d\d\.\d\d', cells[0]): out.append(cells)
    return out
o, d = html.find('<b>Orders</b>'), html.find('<b>Deals</b>')       # section headers are <th> cells
orders = [r for r in table(html[o:d]) if len(r) >= 10]
deals = [r for r in table(html[d:]) if len(r) >= 13]
ts = lambda s: datetime.strptime(s, '%Y.%m.%d %H:%M:%S').replace(tzinfo=timezone.utc).timestamp()  # noqa: E731
num = lambda s: float(s.replace(' ', '')) if s not in ('', None) else 0.0  # noqa: E731
sl_by_order = {r[1]: num(r[6]) for r in orders}
# Deals: Time, Deal, Symbol, Type, Direction, Volume, Price, Order, Commission, Swap, Profit, Balance, Comment
pos = {}
for r in deals:
    if r[3] not in ('buy', 'sell'): continue
    t, direction, vol, price, order, comm, swap, prof = ts(r[0]), r[4], num(r[5]), num(r[6]), r[7], num(r[8]), num(r[9]), num(r[10])
    if direction == 'in':
        pos[order] = dict(op=t, side=r[3], vol=vol, open=price, sl=sl_by_order.get(order, 0.0), net=comm, closes=0.0, cl=None)
    else:
        # closing deal: attach to the earliest open position of the opposite side that is not fully closed (FIFO; one position at a time per EA)
        cand = [p for p in pos.values() if p['cl'] is None and p['side'] != r[3]]
        p = min(cand, key=lambda x: x['op']); p['net'] += comm + swap + prof; p['closes'] += vol
        if p['closes'] >= p['vol'] - 1e-9: p['cl'] = t
out = []
for p in sorted(pos.values(), key=lambda x: x['op']):
    if p['cl'] is None or p['sl'] <= 0: continue
    unit_risk = abs(p['open'] - p['sl']) * 100.0                     # XAUUSD contract 100 oz, USD account
    out.append(dict(op=p['op'], cl=p['cl'], side=p['side'], unit_risk=round(unit_risk, 6), unit_net=round(p['net'] / p['vol'], 6), vol=p['vol'], net=round(p['net'], 2)))
total = round(sum(r['net'] for r in out), 2)
meta = json.loads((D / 'run.json').read_text())
(R / 'VOLCONF_05R_ROWS.json').write_text(json.dumps(dict(source=str(D.name), positions=len(out), net=total, native_net=meta['metrics']['net_profit'],
                                                         native_trades=meta['metrics']['trades'], rows=out), indent=1), encoding='utf-8')
print('positions', len(out), 'net', total, 'native net', meta['metrics']['net_profit'], 'native trades', meta['metrics']['trades'])
