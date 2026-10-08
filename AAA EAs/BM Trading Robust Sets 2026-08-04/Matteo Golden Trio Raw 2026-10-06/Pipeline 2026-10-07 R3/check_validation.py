"""Read-only independent verification of all older-validation finalists."""
import sys
import runner as r
import verify as v

bot=sys.argv[1]
checks={}
for i in range(3):
    folder=r.R/'native'/f'{bot}-validation-{i}'
    if not (folder/'results.json').exists():continue
    rec=r.load(folder/'results.json')[0]
    assert rec['start']==r.CONFIG['validation'][0] and rec['end']==r.CONFIG['validation'][1]
    assert rec['complete_positions'] and rec['clean']
    anchor=v.csv(folder,'0-anchor-bars') if rec['parameters']['tf']==240 else None
    checks[str(i)]=v.candles(v.csv(folder,'0-decisions'),v.csv(folder,'0-bars'),v.csv(folder,'0-sessions'),rec['parameters'],anchor)
assert checks,'No completed validation evidence'
r.save(r.R/(bot+' VALIDATION INDEPENDENT VERIFICATION.json'),dict(ok=True,checks=checks,older_validation_only=True))
print(bot,checks,flush=True)
