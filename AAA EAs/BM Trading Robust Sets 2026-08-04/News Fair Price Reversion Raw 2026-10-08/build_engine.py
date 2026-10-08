"""Mechanical build of locked calendar and two predeclared raw variants."""
from pathlib import Path
import json
R=Path(__file__).resolve().parent
def build(cases):
 assert all(set(c)=={'allow_longs'} and c['allow_longs'] in [0,1] for c in cases)
 events=json.loads((R/'calendar.json').read_text())['events']
 header='double Cases[][1]={'+','.join('{'+str(c['allow_longs'])+'}' for c in cases)+'};\n'
 header+='long Events[]={'+','.join(str(e['epoch']) for e in events)+'};\n'
 header+='string Kinds[]={'+','.join(json.dumps(e['kind']) for e in events)+'};\n'
 return header+(R/'engine.mq5').read_text(encoding='utf-8')
def support(folder):pass
