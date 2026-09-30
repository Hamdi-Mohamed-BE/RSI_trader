"""Same-period original benchmark; no parameter selection or live API."""
import json
import msvcrt
import search as s


if __name__=='__main__':
    assert (s.ROOT/'VERDICT.json').exists(), 'Wait for search/evaluation decision'
    with (s.TESTER/'nasdaq-trend-research.lock').open('a+b') as h:
        h.seek(0);msvcrt.locking(h.fileno(),msvcrt.LK_NBLCK,1)
        if any(s.OUT.glob('validation-*/results.json')):
            s.batch('baseline-validation',[s.DEFAULT],*s.VAL,4,False)
        v=json.loads((s.ROOT/'VERDICT.json').read_text())
        if 'holdout' in v:s.batch('baseline-older',[s.DEFAULT],'2019.09.27','2021.09.27',4,False)
        s.status('Benchmark comparisons complete',verdict=v['status'])
