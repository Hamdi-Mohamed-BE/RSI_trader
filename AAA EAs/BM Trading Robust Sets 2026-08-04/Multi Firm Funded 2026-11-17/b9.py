"""Owner 2026-11-17 roster (Best 1-Step BEST1STEP-20261117, 9 EAs): Gold Band Wave + XAU Squeeze removed; EMA3 + RSI VWAP kept.
_B9 = the 9 EAs as installed (no opposite-trade rule); _B9NH = with the no-opposite-trade rule (needed at FundingPips). python b9.py"""
import json
import gold as G

DROP = ['gold-band-wave', 'xau-squeeze-momentum-standard']
c = [x for x in G.D['candidates'] if x['ea'] not in DROP]; out = {}
for name, cands in (('B9', c), ('B9NH', G.nohedge(c))):
    (G.H / f'INPUTS_{name}.json').write_text(json.dumps(dict({k: v for k, v in G.D.items() if k != 'candidates'}, candidates=cands), separators=(',', ':')), encoding='utf-8')
    per = {}
    for ea in sorted({x['ea'] for x in cands}):
        m = [x for x in cands if x['ea'] == ea]; per[ea] = dict(all=G.stats(m), last_year=G.stats(m, G.LY))
    out[name] = dict(eas=sorted({x['ea'] for x in cands}), all=G.stats(cands), last_year=G.stats(cands, G.LY), per_ea=per)
    print(name, len(out[name]['eas']), 'ALL', out[name]['all'], 'LY', out[name]['last_year'])
(G.H / 'B9.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
