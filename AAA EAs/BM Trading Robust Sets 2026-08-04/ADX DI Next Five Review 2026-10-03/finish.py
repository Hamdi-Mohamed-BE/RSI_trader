"""After the main runner exits: small-sample quarter diagnostics, never promotion."""
from pathlib import Path
import json
import run
R=Path(__file__).resolve().parent
def main():
    results=run.load(R/'SUMMARY.json');bots=run.load(R/'bots.json');n=run.load(R/'NOMINATIONS.json');checks=[]
    for key,b in bots.items():
        if n[key]['variant']:continue
        alternatives=[r for r in results if r['ea']==key and r['window']=='1y' and r['variant']!='BASE' and not r['original'] and r['stats']['pf'] is not None]
        if not alternatives:continue
        best=max(alternatives,key=lambda r:(r['stats']['pf'],r['stats']['trades']))
        # Highest PF among the PREDEFINED one-year arms, not a new quarter search.
        # This arm FAILED the nomination gate; the extra quarter is descriptive only.
        r=run.case(key,b,best['variant'],'3m');results.append(r)
        checks.append(dict(ea=key,variant=best['variant'],year_trades=best['stats']['trades'],tag=r['tag'],
            eligible=False,reason='No year nominee. Highest-PF predefined arm quarter diagnostic only; not promotion or an untouched holdout.'))
        run.save(R/'SUMMARY.json',results);run.save(R/'QUARTER_DIAGNOSTICS.json',checks)
    import report
    report.main()
    run.status('COMPLETE native screens, quarter diagnostics and descriptive Monte Carlo; production unchanged')
if __name__=='__main__':main()
