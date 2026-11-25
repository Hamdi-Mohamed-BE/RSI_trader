"""Owner 2026-11-25: keep the minimum-lot fallback or raise the risk? $10k FTMO 1-Step, INPUTS_N75 stream (Best 1-Step as installed, weekend flat).
Per trade on a $10k reference: budget = risk x 10,000 (Nasdaq x0.75); lots = floor(budget / (0.01-lot risk)) x 0.01 (guard rounds DOWN);
if that is 0: SKIP (old guard) / MIN2, MIN3 (trade 0.01 if it risks <= 2x / 3x the budget). The trade's R is scaled by actual risk / budget
(unit_risk divided by the factor, so marks scale too). IDEAL = no rounding (the 93.1% baseline). Writes Multi Firm Funded/INPUTS_ML_<risk>_<mode>.json."""
import json, math
from pathlib import Path
MF = Path(__file__).resolve().parent.parent / 'Multi Firm Funded 2026-11-17'
D = json.loads((MF / 'INPUTS_N75.json').read_text(encoding='utf-8')); meta = {k: v for k, v in D.items() if k != 'candidates'}
NAS = 'nasdaq-5m-candle-momentum'; FN = 0.75; out = {}
for risk in (0.5, 0.75, 1.0):
    for mode in ('IDEAL', 'SKIP', 'MIN2', 'MIN3'):
        cs = []; skipped = minused = 0
        for c in D['candidates']:
            f = FN if c['ea'] == NAS else 1.0
            budget = risk / 100 * 10000 * f; one = 0.01 * c['unit_risk'] / f   # stream R for Nasdaq is already x0.75: unit_risk was scaled by 1/0.75
            if mode == 'IDEAL': cs.append(c); continue
            lots = math.floor(budget / one + 1e-9); scale = lots * one / budget
            if lots == 0:
                if mode == 'SKIP' or one > {'MIN2': 2, 'MIN3': 3}[mode] * budget: skipped += 1; continue
                scale = one / budget; minused += 1
            cs.append(dict(c, unit_risk=c['unit_risk'] / scale))
        name = f"ML_{int(risk * 100)}_{mode}"; (MF / f'INPUTS_{name}.json').write_text(json.dumps(dict(meta, candidates=cs), separators=(',', ':')), encoding='utf-8')
        out[name] = dict(trades=len(cs), skipped=skipped, min_lot_used=minused); print(name, out[name], flush=True)
(Path(__file__).resolve().parent / 'MINLOT_STREAMS.json').write_text(json.dumps(out, indent=1))
