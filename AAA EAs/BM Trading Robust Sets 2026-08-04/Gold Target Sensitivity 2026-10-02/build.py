"""Mechanical research snapshots; never edits original sources or live terminals."""
from pathlib import Path
import hashlib,json,re,shutil
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent
OLD=BASE/'Reel Three Bots Pipeline 2026-10-02'
FILES={
 'T':(BASE/'Trend Progression Research 2026-09-02/EA/Trend Progression EA.mq5',BASE/'Trend Progression Research 2026-09-02/Sets/TrendProgression-xauusd--h4--optimized--locked.set'),
 'S':(BASE/'Slow Multi Asset Trend Research 2026-09-06/EA/Calyx Slow Trend EA.mq5',BASE/'Slow Multi Asset Trend Research 2026-09-06/Sets/xauusd-selected-full-model1.set')}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):
 b=p.read_bytes();return b.decode('utf-16') if b[:2] in (b'\xff\xfe',b'\xfe\xff') else b.decode('utf-8-sig')
assert json.loads((OLD/'SUMMARY.json').read_text())['trials']['passes']>0
provenance={}
for kind,(src,setting) in FILES.items():
 ea=ROOT/('EA-'+kind);ea.mkdir(exist_ok=True)
 text=read(src);values=dict(line.split('=',1) for line in read(setting).splitlines() if '=' in line and not line.startswith(';'))
 changes=[]
 for key,val in values.items():
  pattern=r'(input\s+(\w+)\s+'+re.escape(key)+r'\s*=)[^;]+;'
  match=re.search(pattern,text);assert match,key
  if key=='InpRewardRisk':text=re.sub(pattern,'double InpRewardRisk='+val+';',text);changes.append(key+' becomes case-selected global');continue
  typ=match.group(2);replacement=val if typ in ['double','int','long','ulong','bool','uint'] else '('+typ+')'+val
  text=re.sub(pattern,lambda m:m.group(1)+replacement+';',text)
 # Fixed technical safety setting; absent from Progression settings but already false by default.
 text=re.sub(r'(input\s+bool\s+InpAdaptivePortfolioControls\s*=)[^;]+;',r'\1false;',text)
 text=re.sub(r'^#property[^\n]*\n','',text,flags=re.M)
 for event in ['OnInit','OnTick','OnDeinit']:text=re.sub(r'\b'+event+r'\s*\(', 'Original'+event+'(',text)
 text=text.replace('CTrade trade;','AuditTrade trade;')
 text=text.replace('..\\..\\_Shared\\CalyxAdaptivePortfolio.mqh','AdaptiveSnapshot.mqh')
 (ea/'Core.mqh').write_text(text,encoding='utf-8')
 shutil.copy2(BASE/'_Shared/CalyxAdaptivePortfolio.mqh',ea/'AdaptiveSnapshot.mqh')
 shutil.copy2(ROOT/'Main.mqh',ea/'Main.mqh');shutil.copy2(ROOT/'Extensions.mqh',ea/'Extensions.mqh')
 (ea/'Engine.mqh').write_text('// Locked original: '+sha(src)+'\n// Settings: '+sha(setting)+'\n// Core: '+sha(ea/'Core.mqh')+'\n// Shared helper: '+sha(ea/'AdaptiveSnapshot.mqh')+'\n#include "Core.mqh"\n',encoding='utf-8')
 provenance[kind]=dict(source=str(src),source_sha=sha(src),settings=str(setting),settings_sha=sha(setting),snapshot_sha=sha(ea/'Core.mqh'),changes=changes+['Locked setting defaults','event rename/warm-up wrapper','observational CTrade subclass; return values preserved'])
runner=read(OLD/'native_runner.py')
runner=runner.replace('ReelPipeline20261002','GoldTargets20261002').replace('reel-search-20261002','gold-targets-20261002').replace('Period=M1','Period=H4')
runner=runner.replace("'Main.mqh','Engine.mqh','Extensions.mqh'","'Main.mqh','Engine.mqh','Extensions.mqh','Core.mqh','AdaptiveSnapshot.mqh'")
runner=runner.replace("['Engine.mqh','Extensions.mqh','Main.mqh']","['Engine.mqh','Extensions.mqh','Main.mqh','Core.mqh','AdaptiveSnapshot.mqh']")
runner=runner.replace("EA/'Extensions.mqh'):","EA/'Extensions.mqh',EA/'Core.mqh',EA/'AdaptiveSnapshot.mqh'):")
(ROOT/'native_runner.py').write_text(runner,encoding='utf-8')
shutil.copy2(OLD/'metrics.py',ROOT/'metrics.py')
(ROOT/'SOURCES.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
print('Frozen research snapshots ready.',flush=True)
