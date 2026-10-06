"""Arithmetic unit checks; no tester, terminal or live API use."""
import importlib.util,json
from pathlib import Path
import numpy as np
R=Path(__file__).resolve().parent
sp=importlib.util.spec_from_file_location('trend_math_helpers',R/'analyze.py')
a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
path=a.pathstats(np.array([[.1,-.1,.2]]))
assert abs(path['return_p50_pct']-18.8)<1e-10
# Simulated cash-weighted PF, not the misleading return-unit PF of3.
assert abs(path['pf_p50']-(.1+.198)/.11)<1e-10
assert abs(path['closed_dd_p95_pct']-10)<1e-10
assert path['win_streak_p50']==1 and path['loss_streak_p50']==1
assert a.stats.streaks([2,3,-1,-2,-3,1,1,1,1])==(4,3)
assert abs(float(a.pf(np.array([10,-5,15,-10])))-25/15)<1e-10
print(json.dumps({'arithmetic_checks':'passed','cash_weighted_pf':path['pf_p50'],'compound_return_pct':path['return_p50_pct']}))
