"""Local native parameter stability; never changes frozen selected settings."""
import json
from params import *
import native

def main():
    c=json.loads((ROOT/'frozen-selection.json').read_text())['config'];checks=[]
    variants=[('pullback',{'InpPullbackEMA':10 if c['InpPullbackEMA']!=10 else 20}),
      ('strength',{'InpADXMin':c['InpADXMin']+5 if c['InpADXMin']<35 else 30}),
      ('channel',{'InpBreakoutBars':30 if c['InpBreakoutBars']!=30 else 20}),
      ('momentum-stop',{'InpMomentumStopATR':2.5 if c['InpMomentumStopATR']!=2.5 else 2.})]
    native.prepare()
    for name,delta in variants:
        r=native.run({**c,**delta},TRAIN,'neighbor-'+name);checks.append(dict(change=delta,result=r));save(ROOT/'native-neighborhood.json',checks)
    print('NATIVE NEIGHBORHOOD FINISHED; SELECTION UNCHANGED',flush=True)

if __name__=='__main__':main()
