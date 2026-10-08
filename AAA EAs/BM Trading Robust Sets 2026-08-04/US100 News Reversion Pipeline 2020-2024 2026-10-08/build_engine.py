"""Frozen numeric cases and official calendar; tester-only, no live installer."""
from pathlib import Path
import json, math
R=Path(__file__).resolve().parent
FIELDS=['allow_longs','sl_mult','impulse_mult','body_mult','body_fraction','signal_mode','window_minutes','hold_minutes','target_fraction']
BASE=dict(zip(FIELDS,[1,2,1,.5,.6,0,30,60,1]))

def validate(c):
 assert set(c)==set(FIELDS) and all(math.isfinite(float(v)) for v in c.values())
 assert c['allow_longs']==1
 assert .5<=c['sl_mult']<=6 and .2<=c['impulse_mult']<=3
 assert .1<=c['body_mult']<=2 and .3<=c['body_fraction']<=.9
 assert c['signal_mode'] in [0,1,2] and 5<=c['window_minutes']<=45
 assert 5<=c['hold_minutes']<=90 and .25<=c['target_fraction']<=1

def build(cases):
 for c in cases:validate(c)
 events=json.loads((R/'calendar.json').read_text())['events']
 header='double Cases[][9]={'+','.join('{'+','.join(str(c[k]) for k in FIELDS)+'}' for c in cases)+'};\n'
 header+='long Events[]={'+','.join(str(e['epoch']) for e in events)+'};\n'
 header+='string Kinds[]={'+','.join(json.dumps(e['kind']) for e in events)+'};\n'
 return header+(R/'engine.mq5').read_text(encoding='utf-8')

def support(folder):pass
