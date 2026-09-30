"""Paired four-week blocks, frozen configurations; synthetic frequencies, not forecasts."""
import json,time
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import numpy as np
import simulate as s
def main():
    root=s.ROOT;a=s.read(root/'AUDIT.json');z=np.load(root/'prepared.npz');tr=z['trades'];pc=z['close'];pl=z['low']
    block=28*s.DAY;pool=list(range(s.epoch(2025,9,29),a['end']//60-block+1,7*s.DAY))
    start=s.epoch(2026,9,28);end=start+180*s.DAY;clock=s.clocks(start,end)
    rng=np.random.default_rng(20260928);draws=rng.integers(0,len(pool),size=(500,7))
    ny=ZoneInfo('America/New_York');samples=[];overlaps=0
    for draw in draws:
        chunks=[]
        for k,p in enumerate(draw):
            src=pool[p];target=start+k*block
            src_off=datetime.fromtimestamp((src+2*s.DAY)*60,timezone.utc).astimezone(ny).utcoffset().total_seconds()/60
            dst_off=datetime.fromtimestamp((target+2*s.DAY)*60,timezone.utc).astimezone(ny).utcoffset().total_seconds()/60
            offset=target-src+src_off-dst_off
            rows=tr[(tr[:,0]>=src)&(tr[:,0]<src+block)].copy()
            overlaps+=int(np.sum(rows[:,1]>=src+block));rows[:,0:2]+=offset
            chunks.append(rows)
        rows=np.concatenate(chunks);rows=rows[(rows[:,0]>=start)&(rows[:,0]<end)]
        rows=rows[np.argsort(rows[:,0],kind='stable')];samples.append(rows)
    result=dict(paths=500,source_blocks=len(pool),block_days=28,seed=20260928,horizons=s.HORIZONS.tolist(),
                whole_trade_tails_kept=True,source_block_crossing_positions=overlaps,configs=[])
    for cfg in s.CONFIGS:
        keys=[a['keys'].index(k) for k in a['core']] if cfg['core'] else list(range(13))
        rr=[r[np.isin(r[:,2],keys)] for r in samples]
        for stress in [False,True]:
            t0=time.time();outs=[]
            for i,rows in enumerate(rr):
                outs.append(s.invoke(rows,pc,pl,start,end,clock,cfg,stress)[0])
                if (i+1)%100==0:print(f'{cfg["name"]} stress={stress} {i+1}/500',flush=True)
            name='c'+str(s.CONFIGS.index(cfg))+'-'+str(int(stress))
            np.savez_compressed(root/(name+'-bootstrap.npz'),snapshots=np.array(outs))
            result['configs'].append(dict(config=cfg,stress=stress,summary=s.summarize(outs),artifact=name+'-bootstrap.npz'))
            s.save(root/'BOOTSTRAP.json',result)
            print(json.dumps(dict(name=cfg['name'],stress=stress,seconds=round(time.time()-t0,1),summary=result['configs'][-1]['summary'][-1])),flush=True)
    print('COMPLETE 7000 paired scenarios',flush=True)
if __name__=='__main__':main()
