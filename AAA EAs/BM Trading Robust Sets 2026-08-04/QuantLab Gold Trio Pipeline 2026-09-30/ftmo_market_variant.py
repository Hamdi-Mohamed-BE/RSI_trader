"""Diagnostic (added 2026-09-30 after freezing): BEST trio with MARKET entries for A and B, because the FTMO guard
admits market entries only. Not a new selection; every run is counted in TRIAL ACCOUNTING. Isolated tester only."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import search  # noqa: E402

frozen = json.loads((search.ROOT / 'FROZEN PICKS.json').read_text())
cases = [dict(frozen['A-best']['parameters'], entry=0, offset=0), dict(frozen['B-best']['parameters'], entry=0, offset=0), frozen['C-best']['parameters']]
out = {}
for label, (s, e) in [('5y', search.WEB['5y']), ('holdout', search.HOLD), ('1y', search.WEB['1y'])]:
    r = search.batch(f'ftmo-market-variant-{label}', cases, s, e, model=4, optimize=False, slots=[0, 1, 2])[0]
    d = search.read_ledger(f'ftmo-market-variant-{label}')
    out[label] = dict(total=r['stats'], clean=r['clean'], modules={m: search.stats(d[d.module == m], s, e) for m in sorted(d.module.unique())})
    print(label, r['stats']['trades'], r['stats']['return_pct'], r['stats']['pf'], r['stats']['win_pct'], r['stats']['equity_dd_pct'], flush=True)
(search.ROOT / 'FTMO MARKET VARIANT.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
n, u = search.trial_count()
(search.ROOT / 'TRIAL ACCOUNTING.json').write_text(json.dumps(dict(passes=n, unique_or_single=u), indent=2), encoding='utf-8')
