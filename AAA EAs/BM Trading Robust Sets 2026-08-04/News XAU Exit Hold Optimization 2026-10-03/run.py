"""Expanded native exit study; reuse the audited optimizer/export engine.
An 18-case menu tests holding time, $40+ price targets and trailing. No live writes.
"""
from pathlib import Path
import importlib.util,inspect,json,re,shutil,subprocess,time

R=Path(__file__).resolve().parent;PILOT=R.parent/'News XAU Exit Optimization 2026-10-03'
if (R/'CANCELLED.txt').exists():
 raise SystemExit('Expanded exit study cancelled by latest user request; current exit settings retained.')
spec=importlib.util.spec_from_file_location('news_exit_engine',PILOT/'run.py')
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
engine.R=R;engine.NAME='NewsExitHoldResearch'
engine.DEST=engine.T/'MQL5/Experts/AAA Research/NewsExitHold20261003'
engine.MENU=[
 ('Current exits / 30s',None,None,None),
 ('Current exits / 60s',None,None,None),
 ('Current exits / 120s',None,None,None),
 ('$40 TP / no trail / 60s',4,0,0),
 ('$40 TP / no trail / 120s',4,0,0),
 ('$60 TP / no trail / 60s',6,0,0),
 ('$60 TP / no trail / 120s',6,0,0),
 ('$80 TP / no trail / 120s',8,0,0),
 ('No TP / no trail / 120s',0,0,0),
 ('No TP / trail 0.5R / $2 gap / 60s',0,.5,2),
 ('No TP / trail 0.5R / $2 gap / 120s',0,.5,2),
 ('No TP / trail 0.5R / $4 gap / 120s',0,.5,4),
 ('No TP / trail 1R / $4 gap / 120s',0,1,4),
 ('$40 TP / trail 0.5R / $4 gap / 120s',4,.5,4),
 ('$60 TP / trail 1R / $4 gap / 120s',6,1,4),
 ('No TP / trail 1.5R / $6 gap / 120s',0,1.5,6),
 ('$80 TP / trail 1.5R / $6 gap / 120s',8,1.5,6),
 ('No TP / trail 1R / $4 gap / 60s',0,1,4),
]
HOLDS=[30,60,120,60,120,60,120,120,120,60,120,120,120,120,120,120,120,60]
assert len(HOLDS)==len(engine.MENU)==18 and max(HOLDS)<=120
engine.HOLDS=HOLDS
old_fingerprint=engine.fingerprint
def fingerprint():return {**old_fingerprint(),'holding_seconds':HOLDS,'engine_sha':engine.sha(PILOT/'run.py')}
engine.fingerprint=fingerprint

# Mechanical reuse of the same native-deal reconciliation and net-risk parser,
# changing only its timer-bound assertion to the requested candidate hold.
parser=inspect.getsource(engine.parse_case)
needle="assert exit_time<=int(parts[1])+33,'Late exit beyond 30s plus execution tolerance'"
assert needle in parser
exec(parser.replace(needle,"assert exit_time<=int(parts[1])+HOLDS[case]+3,'Late exit beyond selected hold plus execution tolerance'"),engine.__dict__)

def prepare():
 engine.free();folder=R/'snapshot';folder.mkdir(exist_ok=True)
 base=engine.read(engine.OLD/'snapshot/New-fixed-test.mq5').replace('\r\n','\n')
 current=engine.read(engine.SOURCE).replace('\r\n','\n')
 current=re.sub(r'#include "[^"\r\n]*[/\\]([^"/\\]+)"',r'#include "\1"',current)
 current=current.replace('int OnInit()\n{','int OnInit()\n{\n   if(!(bool)MQLInfoInteger(MQL_TESTER)) return INIT_FAILED;')
 assert current==base,'Production differs from frozen v2.20 baseline'
 for p in (engine.OLD/'snapshot').glob('*.mqh'):shutil.copy2(p,folder/p.name)
 audit=engine.read(PILOT/'ResearchAudit.mqh')
 if not (R/'ResearchAudit.mqh').exists():shutil.copy2(PILOT/'ResearchAudit.mqh',R/'ResearchAudit.mqh')
 base=base.replace('void NP_ApplyEventParameters(const string kind)','void NP_BaseEventParameters(const string kind)',1)
 body='void NP_ApplyEventParameters(const string kind)\n{\n NP_BaseEventParameters(kind);\n'
 for case,(_,tp,start,gap) in enumerate(engine.MENU):
  if not case:continue
  body+=f' if(InpExitCase=={case}){{g_np_hold={HOLDS[case]};'
  if tp is not None:body+=f'g_np_tp={tp};g_np_trail_start={start};g_np_trail_distance={gap};'
  body+='}\n'
 body+='}\n'
 anchor='string NP_KindFromComment(const string comment)';assert anchor in base
 base=base.replace(anchor,body+anchor,1)
 inputs='input int InpExitCase=0;\ninput long InpResearchRun=0;\n'
 audit=audit.replace('input int InpExitCase=0;','').replace('input long InpResearchRun=0;','')
 base=base.replace('input group "Trading"',inputs+'\ninput group "Trading"',1)
 i=base.index('double OnTester()');brace=base.index('{',i);depth=1;j=brace+1
 while depth:depth+=(base[j]=='{')-(base[j]=='}');j+=1
 base=base[:i]+audit+'\ndouble OnTester(){return NR_WriteAudit();}\n'+base[j:]
 source=folder/(engine.NAME+'.mq5');source.write_text(base)
 manifest=R/'FROZEN.json';f=fingerprint()
 if manifest.exists():assert json.loads(manifest.read_text())==json.loads(json.dumps(f)),'Frozen study changed'
 else:engine.save(manifest,f)
 log=R/'compile.log';began=time.time()
 subprocess.run(f'"{engine.T/"metaeditor64.exe"}" /portable /compile:"{source}" /log:"{log}"',
  startupinfo=engine.hidden(),creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
 assert '0 errors, 0 warnings' in engine.read(log),engine.read(log)[-5000:]
 assert source.with_suffix('.ex5').stat().st_mtime>=began-2
 engine.DEST.mkdir(parents=True,exist_ok=True);shutil.copy2(source.with_suffix('.ex5'),engine.DEST/(engine.NAME+'.ex5'))
 engine.save(R/'BUILD.json',dict(source=engine.sha(source),binary=engine.sha(engine.DEST/(engine.NAME+'.ex5'))))
 engine.status('COMPILED expanded 18-case hold/exit tester-only build, zero errors/warnings')
engine.prepare=prepare

# Point the generic engine's native configuration at this separate private EA.
batch_source=inspect.getsource(engine.batch)
assert 'NewsExits20261003' in batch_source
exec(batch_source.replace('NewsExits20261003','NewsExitHold20261003').replace('npexits20261003','npexitholds20261003'),engine.__dict__)

if __name__=='__main__':engine.main()
