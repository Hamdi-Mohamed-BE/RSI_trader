"""Offline Monte Carlo while frozen comparator runs; hash/count-keyed caches only."""
import audit as a
n=a.n
results=n.load(a.R/'FINAL RESULTS.json')
exacts={k:a.exact(r) for k,r in results.items()}
completed=sum(1 for _ in n.OUT.glob('tuned-comparator-*/results.json'))
finished=sum(len(n.load(p)) for p in n.OUT.glob('*/results.json'))
count=finished+(5-completed)+81+len(list(n.OUT.glob('*/FAILED-ATTEMPT-*-empty.htm')))
print('Offline MC conservative planned count:',count,flush=True)
cost=exacts['1Y']['measured_fill_stop_cash_difference_p95']
for k in ['DEV','VAL','HOLD','5Y','3Y','1Y','6M','3M']:
    a.common(exacts[k],count,cost)
    print('Common MC / DSR cached:',k,flush=True)
for k in ['DEV','VAL','HOLD','1Y','6M','3M']:
    a.monte(exacts[k])
    print('Trade/day block, shuffle and missed-trade MC cached:',k,flush=True)
print('Offline MC ready. Final audit reuses only matching report/code/library/count/cost keys.',flush=True)
