"""Post-freeze holdout analysis only; no tester, account API or selection calls."""
import json,sys
import runner as r
import finish
bot=sys.argv[1]
candidate=r.load(r.R/'native'/(bot+'-candidate-OOS')/'results.json')[0]
original=r.load(r.R/'native'/(bot+'-raw-OOS')/'results.json')[0]
result=finish.holdout_audit(bot,candidate,original)
print(json.dumps({k:result[k] for k in ['verdict','sharpe','monte_carlo','cost_stress','gates','ftmo','raw_ftmo_comparison']},indent=2),flush=True)
