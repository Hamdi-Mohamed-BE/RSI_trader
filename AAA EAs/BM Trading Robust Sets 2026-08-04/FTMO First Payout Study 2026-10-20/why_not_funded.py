import importlib.util, json, sys
from collections import Counter
from datetime import timedelta
from pathlib import Path
R = Path(sys.argv[1])
s = importlib.util.spec_from_file_location('payout', R / 'run.py'); P = importlib.util.module_from_spec(s); s.loader.exec_module(P)
T, D, E = P.T, P.D, P.E
data = json.loads((P.RT / 'INPUTS-DI_OFF.json').read_text(encoding='utf-8'))
plan = T.splan_for(data['window']); ev = E.master_events(plan, data); ep = [x[0] for x in ev]
c = Counter(); d = P.DATA_START; n = 0
while d <= P.E2E_LAST_START:
    if d.weekday() < 5:
        st = P.start_dict(d, P.HORIZON)
        t = D.replay(plan, st, 'recorded_exness', 'next_prague_midnight', P.window(ev, ep, st['epoch'], st['horizon_epoch']), [(-1e9, P.CAP)])
        n += 1
        if t['outcome'] == 'horizon_completed_both': c['funded'] += 1
        elif t['outcome'].startswith('failed'): c['breached'] += 1
        else:
            stuck = t['counts'].get('soft_total_buffer9200', 0) > 0 and t['ending_sampled_equity'] < 9330
            c[('stuck_below_buffer_' if stuck else 'still_trading_') + t['outcome']] += 1
    d += timedelta(days=1)
print(n, {k: f'{v} ({100*v/n:.1f}%)' for k, v in sorted(c.items())})
