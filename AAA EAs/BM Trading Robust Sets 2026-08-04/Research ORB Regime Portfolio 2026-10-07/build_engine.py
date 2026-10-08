"""Native tester-only ORB laboratory. No production source/preset is edited."""
from pathlib import Path
R=Path(__file__).resolve().parent
FIELDS=['module','range_minutes','target_r','stop_atr','rvol_min','range_min','range_max','markov','trail_atr','cutoff']
RAW=dict(module=0,range_minutes=15,target_r=2,stop_atr=0,rvol_min=0,range_min=0,range_max=0,markov=0,trail_atr=0,cutoff=1200)
def build(cases):
 assert all(set(c)==set(FIELDS) for c in cases)
 table='double Cases[]['+str(len(FIELDS))+']={\n'+',\n'.join('{'+','.join(str(float(c[k])) for k in FIELDS)+'}' for c in cases)+'\n};\n'
 return table+(R/'engine.mq5').read_text(encoding='utf-8')
def support(folder):pass
