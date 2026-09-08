"""Check ONLY the available 2026-01-01 to 2026-09-01 recorded-tick window."""
import json
from native import ROOT,compile_ea,run,dump

if __name__=='__main__':
    choices=json.loads((ROOT/'selection.json').read_text());compile_ea()
    for pair in ('XAU-XAG','BTC-ETH'):
        try:run(pair,'selected',choices[pair]['config'],'recent',4)
        except RuntimeError as exc:
            print('RECORDED TICKS UNAVAILABLE:',pair,str(exc),flush=True)
            # Failure is retained; never manufacture a row of zero returns.
            dump(ROOT/'Native'/f'{pair}-selected-recent-model4'/'unavailable.json',dict(pair=pair,stage='recent',model=4,status='no_accepted_result',error=str(exc)))
