"""Owner 2026-11-04: run the new stage-6 three-way Monte Carlo (reshuffle / resample / randomize, robustness.three_monte_carlo,
policy three_way_monte_carlo) on the picked prop portfolio: FTMO17 (Prop Portfolio Selection 2026-11-03 CHOICE.json pick; also the
roster of the ftmo 1_step profile). Source = its frozen trade stream INPUTS-FTMO17.json (native Model 4 long-history runs,
2021-10-07 -> 2026-10-06, recorded Exness costs). R = (gross + commission + swap) / initial stop risk, per lot.
Fixed risk per trade, no guard admission, no compounding: % of balance = R x risk. -> RESULTS.json
Run: python run.py"""
import json, statistics, sys
from datetime import datetime, timezone
from pathlib import Path

H = Path(__file__).resolve().parent
sys.path.insert(0, str(H.parents[1] / 'Calyx Research Pipeline'))
from robustness import three_monte_carlo  # noqa: E402

SRC = H.parent / 'Prop Portfolio Selection 2026-11-03' / 'INPUTS-FTMO17.json'
data = json.loads(SRC.read_text(encoding='utf-8')); open_at_end = [t['id'] for t in data['candidates'] if t['cl'] is None]   # still open at the data end: excluded
rows = sorted((t for t in data['candidates'] if t['cl'] is not None), key=lambda t: (t['cl'], t['id']))
R = [(t['unit_gross'] + t['unit_commission'] + t['unit_swap']) / t['unit_risk'] for t in rows]
first, last = (datetime.fromtimestamp(rows[i]['cl'], timezone.utc) for i in (0, -1))
years = (data['year_end_exclusive_epoch'] - data['year_begin_epoch']) / (365.25 * 86400)
weekdays = sum(1 for d in range(int((data['year_end_exclusive_epoch'] - data['year_begin_epoch']) // 86400))
               if datetime.fromtimestamp(data['year_begin_epoch'] + d * 86400, timezone.utc).weekday() < 5)
per_year = round(len(R) / years)
out = dict(excluded_open_at_end=open_at_end, source=str(SRC.relative_to(H.parents[1])), window=data['window'], trades=len(R), years=round(years, 3),
           trades_per_month=round(len(R) / (years * 12), 1), trades_per_weekday=round(len(R) / weekdays, 2),
           mean_r=round(statistics.fmean(R), 4), total_r=round(sum(R), 2),
           recorded_commission_r_mean=round(statistics.fmean(-t['unit_commission'] / t['unit_risk'] for t in rows), 4),
           win_pct=round(100 * sum(v > 0 for v in R) / len(R), 2),
           pf=round(sum(v for v in R if v > 0) / -sum(v for v in R if v < 0), 3))
out['full'] = three_monte_carlo(R)
out['one_year'] = three_monte_carlo(R, horizon=per_year)
out['cost_ladder'] = {f'{c:.2f}': dict(full=three_monte_carlo(R, extra_cost=c)['randomize'],
                                        one_year=three_monte_carlo(R, extra_cost=c, horizon=per_year)['randomize'])
                      for c in (0.02, 0.05, 0.10, 0.20)}
out['break_even_extra_cost_r'] = round(statistics.fmean(R), 4)   # mean extra cost that takes the expected total to 0
(H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
print(json.dumps({k: v for k, v in out.items() if k not in ('cost_ladder',)}, indent=1)[:6000])
