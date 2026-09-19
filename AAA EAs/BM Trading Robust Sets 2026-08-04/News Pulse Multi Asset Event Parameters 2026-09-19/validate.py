"""Serial isolated MT5 confirmation; no active-terminal or website changes."""
from research import ASSETS, ROOT, HOLDOUT, candidates, run

for asset in ASSETS:
 candidates(asset)
 for variant,delay,start in [('Fitted',1,'2025.09.19'),('Train',1,'2025.09.19'),('TrainHoldout',1,HOLDOUT),('BaselineDelay250',250,'2025.09.19'),('FittedDelay250',250,'2025.09.19')]:
  if (ROOT/'native'/(asset+variant)/'stats.json').exists():
   print('EXISTS',asset+variant,flush=True)
  else:run(asset,variant,delay,start)
