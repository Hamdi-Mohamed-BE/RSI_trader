"""Build a self-contained installer and allocation-only EA copies; never touches a live terminal."""
from pathlib import Path
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time,zipfile
R=Path(__file__).resolve().parent;B=R.parent
spec=importlib.util.spec_from_file_location('freeze_sources',B/'Five EA Shared Portfolio 2026-10-07/build.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
T=B/'_Backtests/MT5-DMC-20260811'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2),encoding='utf-8')
def main():
 (R/'Experts').mkdir(exist_ok=True);(R/'Sets').mkdir(exist_ok=True)
 shutil.copy2(B/'_Shared/CalyxAdaptivePortfolio.mqh',R/'Sources/CalyxAdaptivePortfolio.mqh')
 entries=[]
 names={'H30':'Calyx US30 Hourly Portfolio','H100':'Calyx US100 Hourly Portfolio','N5':'Calyx Nasdaq 5M Portfolio','RV':'Calyx RSI VWAP Gold Portfolio','E3':'Calyx EMA3 Gold Portfolio'}
 for key,label,symbol,tf,source,preset in f.SPECS:
  deps={};s=f.expand(B/source,deps)
  header='#property strict\n#property version "3.00"\n#include <Trade/Trade.mqh>\n#include "CalyxAdaptivePortfolio.mqh"\n#include "RiskSupport.mqh"\n'
  if key=='N5':
   old='double applied_risk=MathMin(InpRiskPercent,1.00);';assert s.count(old)==1;s=s.replace(old,'double applied_risk=InpRiskPercent; // User-selected allocation in this standalone package.')
   s=s.replace('// The research executable is hard-capped at one percent per trade.','// This package uses the selected per-trade allocation; original 1% behavior is retained at 1%.')
   old='double cash=AccountInfoDouble(ACCOUNT_EQUITY)*applied_risk*adaptive/100.0;';assert s.count(old)==1;s=s.replace(old,'double cash=FP_RiskBudget(applied_risk,adaptive);')
  elif key=='RV':
   old='const double risk_money=AccountInfoDouble(ACCOUNT_EQUITY)*InpRiskPercent*adaptive/100.0;';assert s.count(old)==1;s=s.replace(old,'const double risk_money=FP_RiskBudget(InpRiskPercent,adaptive);')
  elif key=='E3':
   old='double risk_cash=AccountInfoDouble(ACCOUNT_EQUITY)*risk_percent*adaptive/100.0;';assert s.count(old)==1;s=s.replace(old,'double risk_cash=FP_RiskBudget(risk_percent,adaptive);')
  s,n=re.subn(r'(int\s+OnInit\s*\(\s*\)\s*\{)',r'\1\n if(!FP_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;',s);assert n==1
  assert s.count('return INIT_SUCCEEDED;')==1;s=s.replace('return INIT_SUCCEEDED;','FP_Heartbeat(InpMagic,true);return INIT_SUCCEEDED;')
  s,n=re.subn(r'(void\s+OnTick\s*\(\s*\)\s*\{)',r'\1\n if(!FP_BindingOK())return;FP_Heartbeat(InpMagic);',s);assert n==1
  if key.startswith('H'):
   s,n=re.subn(r'(void\s+OnTimer\s*\(\s*\)\s*\{)',r'\1\n if(!FP_BindingOK())return;FP_Heartbeat(InpMagic);',s);assert n==1
  path=R/'Sources'/(names[key]+'.mq5');path.write_text(header+s,encoding='utf-8')
  values=f.params(B/preset);values['InpRiskPercent']='1.0';values['InpAdaptivePortfolioControls']='false';values.update(InpPortfolioRiskMode='0',InpPortfolioFixedUSD='50.0',InpPortfolioExpectedLogin='0',InpPortfolioExpectedServer='',InpPortfolioExpectedSymbol='',InpPortfolioInstallNonce='')
  if key.startswith('H'):values['InpAuditTag']='five-standalone-'+key
  sp=R/'Sets'/(key+'.set');sp.write_text('\n'.join(k+'='+v for k,v in values.items())+'\n',encoding='utf-8')
  log=R/'Sources'/(names[key]+'.compile.log');began=time.time()
  subprocess.run(f'"{T/"MetaEditor64.exe"}" /portable /compile:"{path}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=180)
  text=log.read_text(encoding='utf-16');assert '0 errors, 0 warnings' in text,text[-6000:]
  binary=path.with_suffix('.ex5');assert binary.stat().st_mtime>=began-2
  dest=R/'Experts'/binary.name;shutil.copy2(binary,dest)
  entries.append(dict(key=key,label=label,canonical=symbol,period={1:1,5:5,16385:60,16388:240}[tf],magic=int(values['InpMagic']),expert=str(dest.relative_to(R)).replace('\\','/'),settings=str(sp.relative_to(R)).replace('\\','/'),hourly=key.startswith('H'),historical_loss_points=float(values.get('InpHistoricalLossPoints',0)),source=str(path.relative_to(R)).replace('\\','/'),source_sha256=sha(path),expert_sha256=sha(dest),settings_sha256=sha(sp),original_source=source,original_source_sha256=sha(B/source),original_binary_sha256=sha((B/source).with_suffix('.ex5')),original_preset_sha256=sha(B/preset),original_dependencies=deps))
  print('Compiled '+label+': 0 errors, 0 warnings',flush=True)
 # Reuse only pure, proven installer helpers; no installer body is invoked.
 script='''$ast=[Management.Automation.Language.Parser]::ParseFile($args[0],[ref]$null,[ref]$null);$wanted=@('Get-Mt5Candidates','Select-Mt5Candidate','Normalize-Symbol','Find-BrokerSymbol','Read-SetInputs','New-ChartText','Test-ManagedProfile','Close-TargetTerminal','Write-Stage','Stop-WithMessage');$wanted|ForEach-Object{$name=$_;$node=$ast.Find({param($n)$n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq $name},$true);if(-not $node){throw $name};$node.Extent.Text}|ConvertTo-Json'''
  # PowerShell -Command arguments are positional only after a script invocation; use a literal, verified path.
 installer=B/'_Auto Deploy/Install-BMTradingPortfolio.ps1'
 literal=str(installer).replace("'","''");script=script.replace('$args[0]',"'"+literal+"'")
 proc=subprocess.run(['powershell.exe','-NoProfile','-Command',script],capture_output=True,text=True,creationflags=subprocess.CREATE_NO_WINDOW);assert proc.returncode==0,proc.stderr
 helpers=json.loads(proc.stdout);(R/'Installer-Helpers.ps1').write_text('\n\n'.join(helpers).replace('\r\n','\n').replace('\r',''),encoding='utf-8')
 probe=(B/'_Auto Deploy/Probe-MT5.py').read_text(encoding='utf-8')
 probe=probe.replace('Selecting it is read-only.','This subscribes Market Watch, but never sends orders or changes account/login settings.')
 probe=probe.replace('"trade_mode": int(account_dict.get("trade_mode", -1)),','"trade_mode": int(account_dict.get("trade_mode", -1)),\n                    "margin_mode": int(account_dict.get("margin_mode", -1)),\n                    "open_positions": len(mt5.positions_get() or ()),' )
 (R/'Probe-MT5.py').write_text(probe,encoding='utf-8')
 package=dict(version='FIVE-PORTFOLIO-20261007-v3',profile='Calyx FIVE EA PORTFOLIO',entries=entries,default_percent=1,percent_limit=10,required_margin_mode=2,usd_mode_requires_usd_account=True,di_enabled=True,allocation_only_extension=True,no_live_terminal_changed=True)
 save(R/'Package.json',package)
 files=[p for p in R.rglob('*') if p.is_file() and '__pycache__' not in str(p) and not any(x in p.parts for x in ('NativeTests',)) and p.name not in ('Checksums.json','BUILD.json','TESTS.json') and p.suffix!='.log']
 save(R/'Checksums.json',{str(p.relative_to(R)).replace('\\','/'):sha(p) for p in files})
 save(R/'BUILD.json',dict(compile_clean=True,experts=5,original_production_sources_and_binaries_unchanged=all(sha(B/e['original_source'])==e['original_source_sha256'] and sha((B/e['original_source']).with_suffix('.ex5'))==e['original_binary_sha256'] for e in entries),installer_reference_sha256=sha(installer),risk_support_sha256=sha(R/'Sources/RiskSupport.mqh')))
 print('Built self-contained five-EA package. No live terminal accessed.')
if __name__=='__main__':main()
