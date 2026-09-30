"""Predeclared sizing, latency and evaluation-stage sensitivity, current FTMO13."""
from simulate import *
def main():
    a=read(ROOT/'recent-AUDIT.json');d=np.load(ROOT/'recent-prepared.npz');tr=d['trades'];start=a['start'];end=a['end'];days=clock(start,end);sp=specs();out=[]
    for kind in ('equity-sizing','five-minute-close','two-step'):
        for ftmo in ((True,) if kind=='two-step' else (False,True)):
            for c in configs():
                v,logs,daily,curve=run(tr,d['prices'],d['opens'],d['fresh'],sp,start,end,days,ftmo,c['loss'],c['target'],c['cap'],False,kind=='equity-sizing',kind=='two-step',5 if kind=='five-minute-close' else 1)
                m=dict(zip(FIELDS,map(float,v)))
                out.append(dict(kind=kind,account='FTMO Swing' if ftmo else 'Normal capital',config=c,metrics=m))
    save(ROOT/'SENSITIVITY.json',out)
    for r in out:print(r['kind'],r['account'],r['config']['name'],round(r['metrics']['return_pct'],2),r['metrics']['phase1_minute'],r['metrics']['phase2_minute'],r['metrics']['first_ftmo_breach_minute'])
if __name__=='__main__':main()
