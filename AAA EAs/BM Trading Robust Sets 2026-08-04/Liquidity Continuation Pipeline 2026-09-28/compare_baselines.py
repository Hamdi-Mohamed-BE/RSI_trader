"""Same-window Model 4 raw controls for evaluated finalists, never retuning."""
import json
import search

def main():
    completion=search.ROOT/'SEARCH COMPLETION.json'
    state=json.loads((completion if completion.exists() else search.ROOT/'status.json').read_text())
    assert state['message']=='SEARCH COMPLETE','Finish the owned search before starting comparison tests'
    search.save(completion,state)
    finals=json.loads((search.ROOT/'FINALISTS.json').read_text())
    assert len(finals)==3
    result=[]
    for asset,symbol,strategy in search.TARGETS:
        if not list(search.OUT.glob(asset+'-validation-*/results.json')):continue
        r=search.batch(asset,symbol,strategy,'raw-validation',[search.DEFAULT],
            '2024.03.27','2025.09.27',4,False)[0]
        result.append(r)
        search.save(search.ROOT/'RAW VALIDATION COMPARISONS.json',result)
    search.status('BASELINE COMPARISONS COMPLETE',assets=[r['asset'] for r in result],
        search_trials=state['trials'],results=state['results'])

if __name__=='__main__':main()
