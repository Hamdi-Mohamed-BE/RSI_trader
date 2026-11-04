"""Owner 2026-11-04: E10 installed WITHOUT guards -> funded income from both portfolios. Frozen prop_select.funded (FTMO funded
$100k, First Payout income model, 36-month MC + history) with guard=False (compare.py unguarded model: FTMO account rules and broker
margin only, lots rounded up, as CUR17 / C7U in the selection study):
  E10U  = INPUTS-E10.json (this folder), no guard;   CUR17 = the FTMO17 stream (identical file), no guard.
  E10 / FTMO17 = the same streams WITH the Prop Ready guard (used for the 0.75% rows; 0.5 / 1.0 guarded come from the earlier runs).
-> FU-<E10U|CUR17>-<risk>.json here.  Run from EA store: uv run --with pandas --with numpy python "<this>" E10U 0.50"""
import importlib.util, json, sys
from pathlib import Path

H = Path(__file__).resolve().parent; SEL = H.parent / 'Prop Portfolio Selection 2026-11-03'
spec = importlib.util.spec_from_file_location('prop_select', SEL / 'prop_select.py'); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
STREAM = {'E10U': H / 'INPUTS-E10.json', 'CUR17': SEL / 'INPUTS-CUR17.json', 'E10': H / 'INPUTS-E10.json', 'FTMO17': SEL / 'INPUTS-FTMO17.json'}
S.CANDIDATES['E10U'] = dict(label='Edge 10, no guard', guard=False, risks=('0.25', '0.50', '1.00'), members='INPUTS-E10.json')
assert S.CANDIDATES['CUR17']['guard'] is False
S.CANDIDATES['E10'] = dict(label='Edge 10, guarded', guard=True, risks=('0.50', '0.75', '1.00'), members='INPUTS-E10.json')   # 0.75 added 2026-11-04
assert S.CANDIDATES['FTMO17']['guard'] is True


def setup(name):                                         # prop_select.setup, reading the stream from its own folder
    data = json.loads(STREAM[name].read_text(encoding='utf-8'))
    plan = S.T.splan_for(data['window']); eas = sorted({c['ea'] for c in data['candidates']})
    plan['baskets'][name] = eas; plan['candidate_priority'] = plan['candidate_priority'] + [s for s in eas if s not in plan['candidate_priority']]
    events = S.E.master_events(plan, data)
    return data, plan, events, [x[0] for x in events]


S.setup = setup; S.R = H
if __name__ == '__main__':
    S.funded(sys.argv[1], sys.argv[2])
