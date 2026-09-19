"""Recompute only the horizon-only supplement after adding NY DST alignment."""
from run import *

def main():
    j=s.read(ROOT/'results.json')
    for row in j['results']:
        stress=row['stress'];d=s.load(stress)
        # Existing historical outputs must remain exactly unchanged.
        four=s.load(stress,start=START,end=END)
        assert s.replay(four,.1,stress,detail=True,start=START,end=END)==row['historical']
        assert s.replay(four,.1,stress,challenge=False,detail=True,start=START,end=END)==row['continuous']
        identity=list(range(9))
        assert s.replay(d,.1,stress,sample=identity)==s.replay(d,.1,stress,sample=identity,preserve_ny_clock=True)
        end=s.START+END-START;n=math.ceil((end-s.week_anchor(s.START))/s.WEEK)
        rng=random.Random(20260919);samples=[[rng.randrange(9) for _ in range(n)] for _ in range(1000)]
        paths=[]
        for i,sample in enumerate(samples):
            paths.append(s.replay(d,.1,stress,sample=sample,start=s.START,end=end,preserve_ny_clock=True))
            if (i+1)%250==0:print('DST HORIZON',stress,i+1,flush=True)
        row['horizon_only_original_pool']=s.aggregate(paths)
        path=ROOT/('paths-stress.json' if stress else 'paths-reference.json')
        saved=s.read(path);saved['horizon_only']=[summarize_path(r) for r in paths];s.save(path,saved)
        print('FINAL HORIZON',stress,json.dumps(row['horizon_only_original_pool']),flush=True)
    j['protocol_sha256']=s.fingerprint(ROOT/'PROTOCOL.md');j['engine_sha256']=s.fingerprint(PRIOR/'study.py')
    s.save(ROOT/'results.json',j)

if __name__=='__main__':main()
