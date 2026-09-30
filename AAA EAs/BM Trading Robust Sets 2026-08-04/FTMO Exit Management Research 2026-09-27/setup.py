"""Freeze inputs and mechanically clone six EAs for isolated exit-only research."""
from pathlib import Path
import ast,hashlib,html,json,re,sys
from collections import defaultdict
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE/'FTMO Paper Application 2026-09-26'))
import six_ea as six
import compare as c
CACHE=six.CACHE
SOURCES={
 'gold':BASE/'Gold Overnight Value Area EA/EA/Gold Overnight Value Area EA.mq5',
 'overnight':BASE/'Nasdaq Overnight Negative Day EA/Nasdaq Overnight Negative Day EA.mq5',
 'ema':BASE/'AAA Final EAs/AAA Final EMA3 EA/AAA Final EMA3 EA.mq5',
 'orb':BASE/'ORB Volume Data EA/ORB Volume Data EA.mq5',
 'xau':BASE/'News Pulse Event Parameters Research 2026-09-19/NativeFullBestV2.mq5',
 'xag':BASE/'News Pulse Multi Asset Event Parameters 2026-09-19/XAGFitted.mq5'}
KEYS=dict(zip(SOURCES,[c.RAW,six.OVERNIGHT,six.EMA,six.ORB,*c.NEWS]))
def text(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def report_inputs(p):
 s=text(p);start=s.lower().find('inputs:');end=s.lower().find('company:',start);out={}
 for v in re.findall(r'<b>(Inp[^<]+)</b>',s[start:end],re.I|re.S):
  v=html.unescape(re.sub('<[^>]+>','',v)).replace('\r','').replace('\n','')
  if '=' in v:k,x=v.split('=',1);out[k.strip()]=x.strip()
 return out
copied={}
def clone(p):
 p=p.resolve();p.relative_to(BASE)
 if str(p) in copied:return
 raw=text(p);target=ROOT/'snapshot'/p.relative_to(BASE);target.parent.mkdir(parents=True,exist_ok=True)
 copied[str(p)]={'sha256':sha(p),'clone':str(target)}
 for inc in re.findall(r'^\s*#include\s+"([^"]+)"',raw,re.M):
  child=(p.parent/inc.replace('\\','/')).resolve()
  assert child.exists(),(p,child)
  clone(child)
 # Only object class is replaced; native entry logic, prices and time exits are preserved.
 raw=re.sub(r'\bCTrade\b','EMTrade',raw)
 target.write_text(raw,encoding='utf-8')

def main():
 frozen={'date':'2026-09-27','from':'2026.03.02','to':'2026.08.31','model':4,'delay_ms':150,
 'note':'Native individual entry-signal reruns on isolated Exness tester; subsequent strict-$10K FTMO portfolio overlay. Not live deployment or independent validation.',
 'initial_risk':'Original initial stop and native sizing retained for signal ledgers; same strict dollar-risk overlay as prior report.',
 'variants':{'native':{'InpEMMode':0},'rr075':{'InpEMMode':1,'InpEMTargetR':.75},'rr050':{'InpEMMode':1,'InpEMTargetR':.5},
             'atr':{'InpEMMode':2,'InpEMActivateR':1,'InpEMATRMultiple':2},
             'profile':{'InpEMMode':3,'InpEMActivateR':.5,'InpEMATRMultiple':2}},
 'accounts':'No normal or Ava terminal connections. Only existing isolated tester profile. No credentials exported.',
 'reporting':'All alternatives are exploratory; this previously examined period is not untouched holdout.', 'eas':{}}
 for name,p in SOURCES.items():
  clone(p)
  inputs={};report=None
  if name in ('overnight','ema','orb'):
   report=CACHE/'source-runs'/KEYS[name]/'5y.htm';inputs=report_inputs(report)
  elif name=='gold':
   settings=BASE/'Selected Portfolio Settings 2026-09-01/24 Gold Overnight Value Area - RAW - 1PCT.set'
   inputs={k:v.split('||')[0] for k,v in (l.split('=',1) for l in text(settings).splitlines() if l.startswith('Inp') and '=' in l)}
  else:
   folder=p.parent/'native'/p.stem
   report=next(folder.glob('*.htm'));inputs=report_inputs(report)
   inputs.update(InpTesterFromDateUTC='20260302',InpTesterToDateUTC='20260830')
  inputs['InpAdaptivePortfolioControls']='false'
  # Reports materialize full SAFE-mode settings, not the current website default.
  assert len(inputs)>10,(name,inputs)
  dest=ROOT/'snapshot'/p.relative_to(BASE)
  source=text(p)
  timer=('void OnTimer' in source) or name in ('xau','xag')
  include=dest.relative_to(ROOT).as_posix().replace('/','\\')
  if name in ('xau','xag'):
   body=text(dest)
   for old,new in [('OnInit','EM_BaseInit'),('OnTick','EM_BaseTick'),('OnTimer','EM_BaseTimer'),('OnDeinit','EM_BaseDeinit')]:
    body=re.sub(r'\b(int|void) '+old+r'\(',lambda m:m[1]+' '+new+'(',body)
   dest.write_text(body,encoding='utf-8')
   pre=''
  else:pre='\n'.join('#define '+a+' '+b for a,b in [('OnInit','EM_BaseInit'),('OnTick','EM_BaseTick'),('OnTimer','EM_BaseTimer'),('OnDeinit','EM_BaseDeinit')])+'\n'
  wrapper='#property strict\n#include "ExitManagement.mqh"\n'+pre+'#include "'+include+'"\n'
  wrapper+='\n'.join('#undef '+n for n in ('OnInit','OnTick','OnTimer','OnDeinit'))+'\n'
  wrapper+='int OnInit(){if(!EM_Init())return INIT_FAILED;return EM_BaseInit();}\n'
  wrapper+='void OnTick(){EM_Run();EM_BaseTick();EM_Run();}\n'
  if timer:wrapper+='void OnTimer(){EM_Run();EM_BaseTimer();EM_Run();}\n'
  wrapper+='void OnDeinit(const int r){'+('' if name=='ema' else 'EM_BaseDeinit(r);')+'EM_End();}\n'
  (ROOT/(name+'.mq5')).write_text(wrapper,encoding='utf-8')
  variants=['native','rr075','rr050']+(['atr'] if name not in ('xau','xag') else [])+(['profile'] if name in ('gold','orb') else [])
  frozen['eas'][name]={'key':KEYS[name],'source':str(p),'wrapper':name+'.mq5','inputs':inputs,
    'source_report':str(report) if report else None,'symbol':'USTEC' if name=='overnight' else 'XAGUSD' if name=='xag' else 'XAUUSD',
    'timeframe':'H4' if name=='ema' else 'M5' if name in ('gold','orb') else 'M1','variants':variants}
 frozen['source_files']=copied
 (ROOT/'run-config.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
 print(json.dumps({n:{'cases':e['variants'],'inputs':len(e['inputs']),'safe':e['inputs'].get('InpUseMarkovRegimeFilter')} for n,e in frozen['eas'].items()},indent=2))
 print('Source files',len(copied),'native cases',sum(len(e['variants']) for e in frozen['eas'].values()))
if __name__=='__main__':main()
