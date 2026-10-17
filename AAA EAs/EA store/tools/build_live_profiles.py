"""Generate named launchers and isolated research-derived packages. MetaEditor only; no MT5 API/terminal."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.catalog import PACKAGE_ROOT

B = PACKAGE_ROOT
R = B/'_00 Live profiles'
CURRENT = B/'Current14 Plus ORB05 Portfolio 2026-10-08'
OLD_FTMO = B/'FTMO Thirteen EA Deployment 2026-09-27'
EDITOR = B/'_Backtests/MT5-DMC-20260811/MetaEditor64.exe'
POLICY = json.loads((R/'ORB05-policy.json').read_text(encoding='utf-8'))
ORBS = POLICY['slugs']


def read(path):
    raw=path.read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r\n','\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def save(path, value):
    write(path, json.dumps(value, indent=2, allow_nan=False)+'\n')


def compile_ea(path):
    log=path.with_suffix('.compile.log')
    started=time.time()
    subprocess.run(f'"{EDITOR}" /portable /compile:"{path}" /log:"{log}"',
                   creationflags=subprocess.CREATE_NO_WINDOW, timeout=120)
    result=read(log)
    assert '0 errors, 0 warnings' in result, result[-4000:]
    assert path.with_suffix('.ex5').is_file()
    assert path.with_suffix('.ex5').stat().st_mtime >= started-2
    print('COMPILED '+path.stem, flush=True)


def ftmo_package():
    target=R/'Packages/FTMO'
    # The installer and pure roster selector are maintained source files. Check
    # before any copy/compile/write, and never erase later safeguards or the
    # Prop ready subset by regenerating from the older 14-EA installer.
    installer=read(target/'Install-Portfolio.ps1')
    assert "[string]$PortfolioVariant='FTMO17'" in installer
    assert "Profile-Selection.ps1" in installer and 'Get-FTMOProfileEntries' in installer
    assert (target/'Profile-Selection.ps1').is_file()
    shutil.copytree(OLD_FTMO/'package', target/'package', dirs_exist_ok=True)
    guard=read(OLD_FTMO/'CalyxFTMOGuard.mqh')
    allocation='''input int FTMOAllocationMode=0; // 0=fixed USD, 1=current equity percentage
input double FTMOAllocationValue=50.0;
bool FTMOAllocationValid() {
   return FTMOAllocationMode>=0 && FTMOAllocationMode<=1 && MathIsValidNumber(FTMOAllocationValue)
      && FTMOAllocationValue>0 && (FTMOAllocationMode==0 || FTMOAllocationValue<=10);
}
double FTMOAllocationBudget() {
   if(!FTMOAllocationValid())return 0;
   double requested=FTMOAllocationMode==0?FTMOAllocationValue:AccountInfoDouble(ACCOUNT_EQUITY)*FTMOAllocationValue/100.0;
   return MathIsValidNumber(requested)&&requested>0?MathMin(50.0,requested):0;
}
'''
    guard=guard.replace('input long   FTMOExpectedLogin=0;',allocation+'input long   FTMOExpectedLogin=0;')
    assert guard.count('MathMin(FTMO_RISK/unit,')==1
    guard=guard.replace('MathMin(FTMO_RISK/unit,','MathMin(FTMOAllocationBudget()/unit,')
    guard=guard.replace('int FTMOInit() {','int FTMOInit() {\n   if(!FTMOAllocationValid())return INIT_PARAMETERS_INCORRECT;')
    for path in (target/'CalyxFTMOGuard.mqh',target/'package/CalyxFTMOGuard.mqh'):
        write(path, guard)
    manifest=json.loads(read(OLD_FTMO/'PACKAGE.json'))
    manifest['version']='FTMO17-ORB05-LIVE-PROMPTS-20261012'
    plan={p['slug']:p for p in json.loads(read(B/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json'))['setups']}
    cache={}
    def graph(path):
        path=path.resolve()
        if path in cache:return cache[path]
        name='src_orb05_'+hashlib.sha256(str(path.relative_to(B)).encode()).hexdigest()[:12]+'.mqh'
        cache[path]=name
        text=read(path).replace('#include <Trade/Trade.mqh>','#include "FTMO_Trade.mqh"')
        text=re.sub(r'\bOrderSend\(', 'FTMOOrderSend(', text)
        text=re.sub(r'#include\s+"([^"]+)"',lambda m: '#include "FTMO_Trade.mqh"' if m[1]=='FTMO_Trade.mqh' else '#include "'+graph(path.parent/m[1].replace('\\','/'))+'"',text)
        write(target/'package'/name,text)
        return name
    for slug in ORBS:
        if slug in {e['slug'] for e in manifest['entries']}:continue
        p=plan[slug]; include=graph(Path(p['source']))
        name='FTMO13-'+slug
        # Identical account guard and guarded CTrade shim as the retained 14.
        code='#property strict\n#include "CalyxFTMOGuard.mqh"\n#define OnInit FTMO_StrategyInit\n#define OnTick FTMO_StrategyTick\n#define OnTimer FTMO_StrategyTimer\n#include "'+include+'"\n#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
        code+='int OnInit(){if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED;return FTMO_StrategyInit();}\nvoid OnTick(){if(FTMOPulse())FTMO_StrategyTick();}\n'
        def expansion(n,seen=None):
            seen=set() if seen is None else seen
            if n in seen:return ''
            seen.add(n);body=read(target/'package'/n)
            return body+'\n'+'\n'.join(expansion(v,seen) for v in re.findall(r'#include "(src_orb05_[^"]+)"',body))
        expanded=expansion(include)
        if re.search(r'void\s+OnTimer\s*\(', expanded):code+='void OnTimer(){if(FTMOPulse())FTMO_StrategyTimer();}\n'
        write(target/'package'/(name+'.mq5'),code)
        inputs=dict(p['input_settings'],InpRiskPercent='0.5',InpAdaptivePortfolioControls='false',FTMOExpectedLogin='0',FTMOExpectedServer='',FTMOExpectedSymbol='',FTMOPhase='1')
        manifest['entries'].append(dict(slug=slug,label=p['label'],symbol=p['symbol'],timeframe=p['period'],expert=name+'.ex5',settings=name+'.set',inputs=inputs))
    for entry in manifest['entries']:
        path=target/'package'/entry['expert'].replace('.ex5','.mq5')
        compile_ea(path)
        values=dict(entry['inputs'],FTMOAllocationMode='0',FTMOAllocationValue='50')
        if entry['slug'] in ORBS:values['InpRewardRisk']='0.5'
        entry['inputs']=values
        write(target/'package'/entry['settings'], '\n'.join(k+'='+str(v) for k,v in values.items())+'\n')
        entry['expert_sha']=sha(path.with_suffix('.ex5'))
        entry['settings_sha']=sha(target/'package'/entry['settings'])
    manifest['orb_keys']=list(ORBS)
    manifest['guard_sha']=sha(target/'CalyxFTMOGuard.mqh')
    manifest['files']={str(p.relative_to(target/'package')).replace('\\','/'):sha(p)
        for p in (target/'package').rglob('*') if p.is_file() and p.suffix not in ('.log',)}
    save(target/'PACKAGE.json', manifest)
    shutil.copy2(OLD_FTMO/'probe_ftmo.py',target/'probe_ftmo.py')
    return manifest


def orb_package():
    target=R/'Packages/ORB-only'
    publication=json.loads(read(Path(__file__).resolve().parents[1]/'data/portfolios.json'))
    selection=next(p for p in publication['portfolios'] if p['slug']=='orbs-only')
    plan=json.loads(read(B/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json'))
    source_plan={p['slug']:p for p in plan['setups']}
    original={}
    cache={}
    def graph(path):
        path=path.resolve()
        if path in cache:return cache[path]
        original[str(path)]=sha(path)
        name='src_'+hashlib.sha256(str(path.relative_to(B)).encode()).hexdigest()[:12]+'.mqh'
        cache[path]=name
        text=read(path)
        if 'double CalyxAdaptiveRiskMultiplier(' in text:
            pattern=re.search(r'double\s+CalyxAdaptiveRiskMultiplier\s*\([^)]*\)\s*\{',text)
            i=pattern.end();depth=1
            while depth:
                if text[i]=='{':depth+=1
                if text[i]=='}':depth-=1
                i+=1
            text=text[:pattern.end()]+'\n   return UR_RiskMultiplier();\n'+text[i-1:]
        text=re.sub(r'#include\s+"([^"]+)"',lambda m:'#include "'+graph(path.parent/m[1].replace('\\','/'))+'"',text)
        write(target/'Sources'/name,text)
        return name
    entries=[]
    for member in selection['members']:
        source=Path(source_plan[member['slug']]['source'])
        include=graph(source)
        inputs={k:str(v) for k,v in member['inputs'].items()}
        inputs['InpRewardRisk']='0.5'
        inputs.update(InpRiskPercent='0.5',InpAdaptivePortfolioControls='false',InpPortfolioRiskMode='0',
            InpPortfolioPercent='0.5',InpPortfolioFixedUSD='50.0',InpPortfolioExpectedLogin='0',
            InpPortfolioExpectedServer='',InpPortfolioExpectedSymbol='',InpPortfolioInstallNonce='')
        if 'InpRiskMode' in inputs:inputs['InpRiskMode']='0'
        if 'InpTesterOnly' in inputs:inputs['InpTesterOnly']='false'
        def expansion(name, seen=None):
            seen=set() if seen is None else seen
            if name in seen:return ''
            seen.add(name);text=read(target/'Sources'/name)
            return text+'\n'+'\n'.join(expansion(child,seen) for child in re.findall(r'#include "(src_[^"]+)"',text))
        expanded=expansion(include)
        assert 'CalyxAdaptiveRiskMultiplier(' in expanded
        name='Calyx ORB-only - '+member['slug']
        text='#property strict\n#include "../RiskSupport.mqh"\n#define OnInit UR_StrategyInit\n#define OnTick UR_StrategyTick\n#define OnTimer UR_StrategyTimer\n#include "'+include+'"\n#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
        text+='int OnInit(){if(!UR_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;int r=UR_StrategyInit();if(r==INIT_SUCCEEDED)UR_Heartbeat(InpMagic,true);return r;}\n'
        text+='void OnTick(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTick();}\n'
        if re.search(r'void\s+OnTimer\s*\(',expanded):
            text+='void OnTimer(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTimer();}\n'
        write(target/'Sources'/(name+'.mq5'),text)
        write(target/'Sets'/(member['slug']+'.set'),'\n'.join(k+'='+v for k,v in inputs.items())+'\n')
        entries.append(dict(key=member['slug'],label=member['label'],canonical=member['symbol'],
            period={'M1':1,'M5':5,'M15':15,'M30':30,'H1':60,'H4':240}[member['timeframe']],
            magic=int(inputs['InpMagic']),hourly=False,expert='Experts/'+name+'.ex5',
            settings='Sets/'+member['slug']+'.set',inputs=inputs,di_input=None))
    for name in ('RiskSupport.mqh','Installer-Helpers.ps1','Probe-MT5.py'):
        shutil.copy2(CURRENT/name,target/name)
    for entry in entries:
        path=target/'Sources'/Path(entry['expert']).with_suffix('.mq5').name
        compile_ea(path)
        (target/'Experts').mkdir(exist_ok=True)
        shutil.copy2(path.with_suffix('.ex5'),target/entry['expert'])
    installer=read(CURRENT/'Install-Portfolio.ps1')
    installer=re.sub(r'\.Count -ne 17', '.Count -ne 5',installer).replace('return $ready -eq 17','return $ready -eq 5').replace('17-chart','5-chart')
    installer=installer.replace("foreach ($canonical in @('USDJPY', 'USTEC', 'XAUUSD'))",'foreach ($canonical in @($Package.entries.canonical | Sort-Object -Unique))')
    installer=installer.replace('No FTMO restrictions, no shared $400/$450 daily stop. This is NOT the previously simulated guarded portfolio. Three-Way Gold risk applies to each module.',
        'Owner-selected five ORBs, ALL at 0.5R. Previous PF admission screen overridden by owner; NY PF below 1.15 and Selective sample tiny. No shared daily stop or FTMO guard.')
    installer=installer.replace('CalyxCurrent14ORB05Setup','CalyxORBOnlySetup')
    installer=installer.replace("$parameter in @('NasdaqDIFilter','UsdJpyDIFilter')",'$parameter in @()')
    write(target/'Install-Portfolio.ps1',installer)
    manifest=dict(version='ORB-ONLY-ALL5-RR05-20261012',profile='Calyx ORB-only 50pct PF1p15',entries=entries,
        orb_keys=list(ORBS),default_percent=.5,news=False,
        ftmo_guard=False,shared_daily_stop=False,original_hashes=original,selection_window=selection['selection_window'])
    assert len(entries)==5 and len({e['magic'] for e in entries})==5
    save(target/'Package.json',manifest)
    paths=[target/'Package.json',target/'Install-Portfolio.ps1',target/'Installer-Helpers.ps1',target/'Probe-MT5.py']
    paths+=list((target/'Experts').glob('*.ex5'))+list((target/'Sets').glob('*.set'))
    save(target/'Checksums.json',{str(p.relative_to(target)).replace('\\','/'):sha(p) for p in paths})
    assert all(sha(Path(path))==digest for path,digest in original.items())
    return manifest


def named_profiles():
    """Launcher metadata only; safe to inspect without compiling or MT5 access."""
    return [
        dict(slug='ftmo',name='FTMO guarded - Current 14 + ORB 0.5R',file='FTMO guarded - Current 14.bat',default_mode='FIXED_USD',default_percent=.5,default_usd=50,
            default_news_percent=0,di_parameters=['NasdaqDIFilter','UsdJpyDIFilter'],eas=17,
            warning='FTMO USD 10K Swing hedging only. Requested risk is capped at USD50 per trade. Existing daily/exposure/phase guards stay unchanged. No news or hourly EAs.'),
        dict(slug='current14-orb05',name='Current 14 + ORB 0.5R',file='Current 14 + ORB 0.5R.bat',default_mode='PERCENT',default_percent=.5,default_usd=50,
            default_news_percent=0,di_parameters=['NasdaqDIFilter','UsdJpyDIFilter'],eas=17,
            warning='17 unique systems. ALL five ORBs at 0.5R; no shared daily stop or FTMO guard. Owner overrides previous PF admission screen. Risk applies per trade/per 3-Way module.'),
        dict(slug='orbs-only',name='ORB-only - All five at 0.5R',file='ORB-only - 50pct+ PF1.15+.bat',default_mode='PERCENT',default_percent=.5,default_usd=50,
            default_news_percent=0,di_parameters=[],eas=5,
            warning='Owner-selected five ORBs, ALL at 0.5R. NY PF0.97 and five-trade Selective sample remain limitations. No shared loss guard. Legacy BAT filename retained for compatibility.'),
        dict(slug='prop-ready',name='Prop ready - Core 4 + five ORBs 0.5R',file='Prop ready.bat',default_mode='FIXED_USD',default_percent=.5,default_usd=50,
            default_news_percent=0,di_parameters=['NasdaqDIFilter','UsdJpyDIFilter'],eas=9,website_catalog=False,
            warning='Nine selected EAs; all five ORBs at 0.5R. Broker-neutral demo/live MT5 hedging account; fixed cash uses account currency. Planned risk capped at 0.5% of saved initial balance, with scaled daily/exposure guards. Default continuous mode; no phase profit stop. Other brokers/custom risk/DI choices do not inherit FTMO pass rates or guarantee firm compliance.'),
        dict(slug='full-eas',name='Full EA portfolio - Recommended Adaptive',file='Full EA portfolio - Recommended Adaptive.bat',default_mode='PERCENT',default_percent=.25,default_usd=25,
            default_news_percent=.10,di_parameters=['NasdaqDIFilter','UsdJpyDIFilter'],eas=37,
            warning='37-EA normal adaptive roster. Lower starting allocation: 0.25% non-news, separate 0.10% news per ORDER. Nasdaq uses 0.25x selection. Hourly has no SL; minimum lots/gaps can exceed budgets. Not FTMO-safe.'),
    ]


def main():
    assert EDITOR.is_file()
    R.mkdir(exist_ok=True)
    ftmo=ftmo_package()
    from tools.build_prop_ready import main as build_prop_ready
    build_prop_ready()
    prop_ready=json.loads(read(R/'Packages/PropReady/PACKAGE.json'))
    orb=orb_package()
    plan=json.loads(read(B/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json'))
    for item in plan['setups']:
        if item['slug'] not in ORBS:continue
        values=dict(item['input_settings'],InpRewardRisk='0.5')
        write(R/'ORB05 Sets'/(item['slug']+'.set'),'\n'.join(k+'='+str(v) for k,v in values.items())+'\n')
    profiles=named_profiles()
    for p in profiles:
        text='@echo off\r\nsetlocal\r\ntitle Calyx - '+p['name']+'\r\npowershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-LiveProfile.ps1" -Portfolio "'+p['slug']+'" %*\r\nset "CALYX_EXIT=%ERRORLEVEL%"\r\nif /I not "%~1"=="-ValidateOnly" pause\r\nexit /b %CALYX_EXIT%\r\n'
        (R/p['file']).write_bytes(text.encode('ascii'))
    save(R/'Profiles.json',dict(version='2026-10-17',profiles=profiles,live_account_access=False,
        policy='Creating BAT files does not install or start them. No backtest inherits a changed risk/DI choice.',
        packages={'ftmo':ftmo['version'],'prop-ready':prop_ready['version'],'orbs-only':orb['version']}))
    write(R/'README.txt', '''CALYX NAMED PORTFOLIOS - 2026-10-17
Keep this entire folder and its sibling EA folders together; these small BATs are not standalone embedded distributions.
Each BAT asks for risk type/value, then separate DI ON/OFF for Nasdaq and USDJPY where included (ADX20 stays).
FTMO: default fixed USD50, or equity %; all requests remain capped at USD50, with existing guard restrictions.
Prop ready: nine EAs (Core 4 plus five 0.5R ORBs), broker-neutral demo/live hedging accounts. Default fixed 50 in account currency, or 0.5% equity; hard cap 0.5% of persisted initial balance with scaled daily/exposure guards. Default continuous mode, not a phase profit stop. Separate DI prompts; see PROP READY GUIDE.txt. Local launcher only.
Current14+ORB: default 0.5% per trade/module, fixed USD default 50; no shared daily stop.
ALL FIVE ORBS: 0.5R in FTMO (17 EAs), Current14+ORB (17), ORB-only (5), normal/full (37) and reviewed profiles.
ORB-only: same default 0.5%/USD50; owner-approved despite NY PF0.97 and Selective five-trade sample. Legacy filenames retained.
Full: lower starting allocation 0.25% or USD25, news separately 0.10% per order; no-stop hourly exposure remains.
These defaults are starting allocations, not optimal settings or guaranteed maximum losses. Published history is not recalculated for custom selections.
Normal MT5 hedging account required. Installers ask for terminal/account and confirmation; inspect all charts before using Algo Trading.
To check files without accessing MT5, append -ValidateOnly to a BAT. Never use PreflightOnly as an offline test (it reads the account).
''')
    print('Five named BATs and compiled packages ready. No live account accessed.',flush=True)


if __name__=='__main__':
    main()
