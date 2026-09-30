"""Writes FTMO_ENTRY.json (entry 14 for the guarded FTMO package) from the parity-verified production binary."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = ROOT.parent
EXPERT = Path('3 Way Gold EA') / '3 Way Gold EA.ex5'
SETTINGS = Path('3 Way Gold Deployment 2026-09-30') / 'Sets' / '3 Way Gold - FTMO MARKET ENTRIES.set'


def sha(p):
    return hashlib.sha256((BASE / p).read_bytes()).hexdigest()


parity = json.loads((ROOT / 'PARITY.json').read_text())
assert all(v['exact'] for v in parity.values()), 'Parity must pass before packaging'
assert all(v['ex5_sha'] == sha(EXPERT) for v in parity.values()), 'Binary differs from the parity-tested build'
inputs = {}
for line in (BASE / SETTINGS).read_text(encoding='utf-8').splitlines():
    if '=' in line and not line.startswith(';'):
        k, v = line.split('=', 1)
        inputs[k.strip()] = v.split('||')[0].strip()
assert inputs['InpMarketEntries'] == 'true'
entry = dict(slug='3-way-gold', label='3 Way Gold', symbol='XAUUSD', timeframe='M15', expert=str(EXPERT), expert_sha=sha(EXPERT),
             settings=str(SETTINGS), settings_sha=sha(SETTINGS), inputs=inputs)
(ROOT / 'FTMO_ENTRY.json').write_text(json.dumps([entry], indent=2), encoding='utf-8')
print(json.dumps(entry, indent=1))
