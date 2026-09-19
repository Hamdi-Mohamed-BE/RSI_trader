"""Offline extension, same parameters; imports the regression-tested prior engine."""
import json,sys,random,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
PRIOR=ROOT.parent/'Gold Raw Plus News FTMO Two Month Study 2026-09-19'
sys.path.insert(0,str(PRIOR))
import study as s

START=s.dt('2026-05-19T00:00:00Z');END=s.END

def verify_old():
    saved=s.read(PRIOR/'results.json')
    checks=[]
    for stress in (False,True):
        d=s.load(stress)
        for row in [r for r in saved['results'] if r['stress']==stress]:
            risk=row['news_risk_percent_per_order']
            assert s.replay(d,risk,stress,detail=True)==row['historical']
            assert s.replay(d,risk,stress,challenge=False,detail=True)==row['continuous']
            checks.append([stress,row['name']])
    return checks

def summarize_path(r):return {k:v for k,v in r.items() if k not in ('log','by_ea')}

def main():
    regression=verify_old();print('REGRESSION',len(regression),'old scenarios unchanged',flush=True)
    rows=[]
    for stress in (False,True):
        data=s.load(stress,start=START,end=END)
        assert len(data[3])==18
        assert len(set(p['epoch'] for p in data[1]))==11
        assert len(data[1])==22
        anchor=s.week_anchor(START)
        for r in data[0]:
            assert int((r['op']-anchor)//s.WEEK)==int((r['cl']-anchor)//s.WEEK),'Position crosses week boundary'
        for p in data[1]:
            assert int((p['t']-anchor)//s.WEEK)==int((p['until']-anchor)//s.WEEK)
        hist=s.replay(data,.1,stress,detail=True,start=START,end=END)
        continuous=s.replay(data,.1,stress,challenge=False,detail=True,start=START,end=END)
        identity=s.replay(data,.1,stress,detail=True,sample=list(range(18)),start=START,end=END)
        assert identity==hist,'Identity week sequence differs from historical path'
        print('HIST',stress,json.dumps(summarize_path(hist)),flush=True)
        rng=random.Random(20260919)
        samples=[[rng.randrange(1,18) for _ in range(18)] for _ in range(1000)]
        paths=[]
        for i,sample in enumerate(samples):
            paths.append(s.replay(data,.1,stress,sample=sample,start=START,end=END))
            if (i+1)%250==0:print('FOUR MONTH',stress,i+1,flush=True)
        pooled=s.aggregate(paths)
        print('BOOTSTRAP',stress,json.dumps(pooled),flush=True)
        # Hold the original July–September source pool constant, change only horizon.
        original=s.load(stress);horizon_end=s.START+(END-START)
        n=math.ceil((horizon_end-s.week_anchor(s.START))/s.WEEK)
        rng=random.Random(20260919)
        samples2=[[rng.randrange(9) for _ in range(n)] for _ in range(1000)]
        extended=[]
        for i,sample in enumerate(samples2):
            extended.append(s.replay(original,.1,stress,sample=sample,start=s.START,end=horizon_end,preserve_ny_clock=True))
            if (i+1)%250==0:print('HORIZON ONLY',stress,i+1,flush=True)
        horizon_only=s.aggregate(extended)
        print('HORIZON',stress,json.dumps(horizon_only),flush=True)
        rows.append(dict(stress=stress,historical=hist,continuous=continuous,bootstrap=pooled,horizon_only_original_pool=horizon_only,audit=data[-1]))
        s.save(ROOT/('paths-stress.json' if stress else 'paths-reference.json'),dict(bootstrap=[summarize_path(r) for r in paths],horizon_only=[summarize_path(r) for r in extended]))
        s.save(ROOT/'results.json',dict(start=s.iso(START),end_exclusive=s.iso(END),calendar_days=(END-START)/s.DAY,regression=regression,results=rows,protocol_sha256=s.fingerprint(ROOT/'PROTOCOL.md'),engine_sha256=s.fingerprint(PRIOR/'study.py')))
    print('SAVED',ROOT/'results.json',flush=True)

if __name__=='__main__':main()
