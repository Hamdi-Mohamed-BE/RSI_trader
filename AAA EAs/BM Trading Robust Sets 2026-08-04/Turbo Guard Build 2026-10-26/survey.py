"""Survey the 17 Turbo EA sources: EX5 hash matches the tested build, includes, pending orders, OrderSend, OnTimer."""
import hashlib, json, re
from pathlib import Path

B = Path(__file__).resolve().parents[1]
P = json.loads((B / '_00 Live profiles/Turbo 50k Funded Portfolio 2026-10-26/PORTFOLIO.json').read_text(encoding='utf-8'))


def read(p):
    raw = p.read_bytes()
    return raw.decode('utf-16' if raw[:2] in (b'\xff\xfe', b'\xfe\xff') else 'utf-8-sig', errors='replace')


def graph(p, seen):
    if p in seen or not p.is_file(): return ''
    seen.add(p); t = read(p)
    return t + ''.join(graph((p.parent / m).resolve(), seen) for m in re.findall(r'#include\s+"([^"]+)"', t))


seen = set()
for e in P['members']:
    src = B / e['source_expert'].replace('\\', '/'); mq = src.with_suffix('.mq5')
    if mq in seen: continue
    seen.add(mq)
    ok = src.is_file() and hashlib.sha256(src.read_bytes()).hexdigest() == e['expert_sha256']
    t = graph(mq.resolve(), set())
    inc = re.findall(r'#include\s+[<"]([^>"]+)[>"]', t)
    pend = sorted(set(re.findall(r'BuyLimit|SellLimit|BuyStop|SellStop|TRADE_ACTION_PENDING|OrderOpen\(', t)))
    print(e['key'][:34].ljust(34), 'mq5' if mq.is_file() else 'NO-MQ5', 'ex5-ok' if ok else 'EX5-MISMATCH', pend or '-',
          'OrderSend' if re.search(r'\bOrderSend\(', t) else '', 'OnTimer' if re.search(r'void\s+OnTimer', t) else '',
          'OnTradeTx' if 'OnTradeTransaction' in t else '', inc)
