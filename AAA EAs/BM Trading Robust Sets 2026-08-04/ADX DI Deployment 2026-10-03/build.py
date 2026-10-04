"""Offline mechanical release. Does not initialize or modify any live terminal.

Research remains immutable. Only audited entry admission is added; portfolio,
exit, sizing and licence policies are retained by their existing wrappers.
"""
from pathlib import Path
import hashlib,json,re,shutil,subprocess,time
R=Path(__file__).resolve().parent; B=R.parent
STUDY=B/'ADX DI Five Bot Review 2026-10-03'
T=B/'_Backtests/MT5-DMC-20260811'
SPECS={
 'ema3':('ema3','AAA Final EMA3','AAA Final EMA3 EA',True,25,False,16388,'ADX25'),
 'asia':('asia-breakout','AAA Final Asia Breakout','AAA Final Asia Breakout EA',False,20,True,16385,'DI_ONLY'),
 'london':('usdjpy-london-open-momentum','USDJPY London Open Momentum','Calyx London Open FX Momentum Pipeline EA',True,20,True,15,'ADX20_DI'),
 'trend':('xau-trend-progression','XAU Trend Progression','Trend Progression EA',False,20,True,16388,'DI_ONLY'),
}
def read(p):
 raw=p.read_bytes();return raw.decode('utf-16' if raw[:2] in (b'\xff\xfe',b'\xfe\xff') else 'utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(read(p))
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2),encoding='utf-8')
def transform(s):
 for old,new in [('StudyInit','CalyxAdmissionInit'),('StudyClose','CalyxAdmissionClose'),('StudyAllow','CalyxAdmissionAllow'),('../StudyFilter.mqh','../CalyxAdmission.mqh')]:s=s.replace(old,new)
 for owner in ('trade','AAA_Trade'):
  for side in ('Buy','Sell'):s=s.replace('Study'+side+'('+owner+',',owner+'.'+side+'(')
 return s
def build():
 bots=load(STUDY/'bots.json');profiles={};builds={}
 for key,(slug,label,name,adx,level,di,tf,variant) in SPECS.items():
  research=STUDY/'EA'/key;folder=R/'EA'/key;folder.mkdir(parents=True,exist_ok=True)
  b=bots[key]
  assert sha(Path(b['source']))==b['source_sha'] and sha(Path(b['original']))==b['original_sha']
  for p in research.glob('*.mqh'):(folder/p.name).write_text(transform(read(p)),encoding='utf-8')
  defaults=f'#define CALYX_DEFAULT_ADX {str(adx).lower()}\n#define CALYX_DEFAULT_ADX_LEVEL {level}.0\n#define CALYX_DEFAULT_DI {str(di).lower()}\n#define CALYX_DEFAULT_ADX_TF ((ENUM_TIMEFRAMES){tf})\n'
  src=folder/(name+'.mq5');src.write_text(defaults+transform(read(research/'Research.mq5')),encoding='utf-8')
  log=src.with_suffix('.log');began=time.time()
  subprocess.run(f'"{T/"metaeditor64.exe"}" /portable /compile:"{src}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
  assert '0 errors, 0 warnings' in read(log),read(log)[-3000:]
  ex=src.with_suffix('.ex5');assert ex.is_file() and ex.stat().st_mtime>=began-2
  inputs=dict(b['inputs']);inputs.update(InpUseADXFilter=str(adx).lower(),InpADXMinimum=str(level),InpRequireDIAgreement=str(di).lower(),InpADXTimeframe=str(tf))
  settings=R/'Sets'/(slug+'.set');settings.parent.mkdir(exist_ok=True);settings.write_text(''.join(f'{k}={v}\n' for k,v in inputs.items()),encoding='utf-8')
  profiles[slug]=dict(key=key,label=label,expert=str(ex.relative_to(B)),expert_sha=sha(ex),source_sha=sha(src),settings=str(settings.relative_to(B)),settings_sha=sha(settings),inputs=inputs,variant=variant,research_case=key+'-'+variant,provisional=key=='trend',website_slug=slug)
  builds[key]=dict(source_sha=sha(src),binary_sha=sha(ex),original_sha=sha(ex),helpers={p.name:sha(p) for p in folder.glob('*.mqh')},compile_tail=read(log)[-350:])
  print('COMPILED',key,'0 errors, 0 warnings',flush=True)
 save(R/'BUILD.json',builds)
 save(R/'SELECTION.json',dict(version='ADXDI-20261003',profiles=profiles,rsi_vwap='Unchanged',live_terminal_changed=False,promotion='Explicit user choice; retrospective one-year screening, not independent validation',study=str(STUDY.relative_to(B))))
 return profiles
if __name__=='__main__':build()
