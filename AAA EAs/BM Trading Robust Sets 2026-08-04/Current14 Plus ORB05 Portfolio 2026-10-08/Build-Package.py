"""Build isolated unrestricted allocation copies and a true single-file BAT.

No account, terminal process or live MT5 API is accessed. MetaEditor only.
"""
from pathlib import Path
import argparse,base64,hashlib,io,json,re,shutil,subprocess,time,zipfile

R=Path(__file__).resolve().parent; B=R.parent
OLD=B/'FTMO Thirteen EA Deployment 2026-09-27'; FIVE=B/'Five EA Portfolio Standalone 2026-10-07'
TESTER=B/'_Backtests/MT5-DMC-20260811'
ORBS=['us100-h1-orb-13utc','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30']

def read(p):
    raw=p.read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig').replace('\r\n','\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
def write(p,s):p.write_text(s,encoding='utf-8')
def replace_body(text,name,body):
    m=re.search(r'double\s+'+name+r'\s*\([^)]*\)\s*\{',text);assert m,name
    i=m.end();depth=1
    while depth:
        if text[i]=='{':depth+=1
        if text[i]=='}':depth-=1
        i+=1
    return text[:m.end()]+'\n'+body+'\n'+text[i-1:]

def transform_installer(count):
    s=read(FIVE/'Install-FivePortfolio.ps1')
    s=s.replace("[double]$RiskValue = 0,","[double]$RiskValue = 0,\n    [ValidateSet('', 'ON', 'OFF')][string]$NasdaqDIFilter = '',\n    [ValidateSet('', 'ON', 'OFF')][string]$UsdJpyDIFilter = '',")
    a="if ($package.entries.Count -ne 5 -or (@($package.entries.key | Sort-Object -Unique) -join ',') -ne 'E3,H100,H30,N5,RV') { throw 'This must be the exact five-EA package.' }"
    z=f"if ($package.entries.Count -ne {count} -or @($package.entries.key | Sort-Object -Unique).Count -ne {count}) {{ throw 'Portfolio roster is incomplete or duplicated.' }}\n    if (@($package.entries | Where-Object {{ $_.key -in $package.orb_keys -and [double]$_.inputs.InpRewardRisk -ne 0.5 }}).Count -ne 0) {{ throw 'An ORB target is not 0.5R.' }}"
    assert a in s;s=s.replace(a,z)
    s=s.replace(".Count -ne 5) { throw 'Duplicate portfolio magic numbers.' }",f".Count -ne {count}) {{ throw 'Duplicate portfolio magic numbers.' }}")
    s=s.replace("if ($Mode -eq 'FIXED_USD' -and $Probe.account.currency -cne 'USD') { throw 'Fixed USD requires a USD-denominated account; select percentage risk for other account currencies.' }","if ($Mode -eq 'FIXED_USD' -and (([string]$Probe.account.currency) -cnotmatch '^[A-Z]{3}$' -or $Probe.account.currency -in @('USC','EUC','GBC'))) { throw 'Fixed USD cannot infer non-standard/cent currencies; select percentage risk.' }")
    s=s.replace("US30 = @('US30', 'DJ30', 'WS30', 'DJI30', 'DOW30', 'DOWJONES', 'DJIA'); ","USDJPY = @('USDJPY'); ")
    s=s.replace("@('US30', 'USTEC', 'XAUUSD')","@('USDJPY', 'USTEC', 'XAUUSD')")
    s=s.replace("$inputs['InpRiskPercent'] = if ($cash) { '1.0' } else { $RiskValue.ToString('G17', [Globalization.CultureInfo]::InvariantCulture) }","$inputs['InpRiskPercent'] = '0.5' # Native calibration; selected allocation is separate.\n    $inputs['InpPortfolioPercent'] = if ($cash) { '0.5' } else { $RiskValue.ToString('G17', [Globalization.CultureInfo]::InvariantCulture) }")
    before="    if ($Item.Hourly) {"
    s=s.replace(before,"    if ($Item.Key -eq 'nasdaq-5m-candle-momentum') { $inputs['InpRequireDIAgreement']=if ($NasdaqDIFilter -eq 'OFF') { 'false' } else { 'true' } }\n    if ($Item.Key -eq 'usdjpy-london-open-momentum') { $inputs['InpRequireDIAgreement']=if ($UsdJpyDIFilter -eq 'OFF') { 'false' } else { 'true' } }\n"+before)
    s=s.replace('return $ready -eq 5',f'return $ready -eq {count}')
    s=s.replace('1..5 |','1..$portfolio.Count |')
    s=s.replace('CalyxFivePortfolio-','CalyxCurrent14ORB05-').replace('CalyxFiveSetup','CalyxCurrent14ORB05Setup')
    s=s.replace('all five','all selected').replace('All five','All selected').replace('these five','these selected').replace('These five','These selected').replace('five-chart',str(count)+'-chart').replace('five-EA','combined-EA').replace('FIVE EA PORTFOLIO','CURRENT14 + ORB05 PORTFOLIO').replace('these five','these selected')
    s=s.replace("Write-Host 'Hourly EAs have NO stop-loss: sizing uses historical loss distances; future losses are NOT capped.' -ForegroundColor Yellow","Write-Host 'No FTMO restrictions, no shared $400/$450 daily stop. This is NOT the previously simulated guarded portfolio. Three-Way Gold risk applies to each module.' -ForegroundColor Yellow")
    s=s.replace("$candidates=@(Get-Mt5Candidates | Where-Object { $_.Running })","foreach ($parameter in @('NasdaqDIFilter','UsdJpyDIFilter')) {\n        if (-not (Get-Variable -Name $parameter -ValueOnly)) {\n            $label=if ($parameter -eq 'NasdaqDIFilter') {'Nasdaq 5M'} else {'USDJPY London'}\n            $answer=(Read-Host \"$label DI filter ON or OFF [ON]\").Trim().ToUpperInvariant(); if (-not $answer) { $answer='ON' }\n            if ($answer -notin @('ON','OFF')) { throw 'Choose ON or OFF.' }; Set-Variable -Scope Script -Name $parameter -Value $answer\n        }\n    }\n    Write-Host 'DI OFF changes the tested preset. USDJPY ADX20 remains enabled.' -ForegroundColor Yellow\n    $candidates=@(Get-Mt5Candidates | Where-Object { $_.Running })")
    s=s.replace('Nasdaq DI remains ON.','Nasdaq DI=$NasdaqDIFilter; USDJPY DI=$UsdJpyDIFilter.')
    s=s.replace('RiskValue=$RiskValue; Profile=', 'RiskValue=$RiskValue; NasdaqDI=$NasdaqDIFilter; UsdJpyDI=$UsdJpyDIFilter; Profile=')
    s=s.replace('Percentage per trade [1]','Percentage per trade [0.5]').replace("{ $answer='1' }","{ $answer='0.5' }")
    s=s.replace('default: 1%', 'default: 0.5%')
    assert 'FTMOExpected' not in s
    return s

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--include-selective',action='store_true');ap.add_argument('--no-compile',action='store_true');args=ap.parse_args()
    for folder in ['Sources','Experts','Sets']: (R/folder).mkdir(exist_ok=True)
    m=json.loads(read(OLD/'PACKAGE.json'))
    for name,h in m['files'].items(): assert sha(OLD/'package'/name)==h,name
    entries=[];original={str(OLD/'PACKAGE.json'):sha(OLD/'PACKAGE.json')}
    cache={}
    def graph(path):
        path=path.resolve()
        if path in cache:return cache[path]
        original[str(path)]=sha(path)
        name='src_'+hashlib.sha256(str(path).encode()).hexdigest()[:12]+'.mqh';cache[path]=name
        s=read(path)
        if 'double CalyxAdaptiveRiskMultiplier(' in s:
            s=replace_body(s,'CalyxAdaptiveRiskMultiplier','   return UR_RiskMultiplier();')
        s=s.replace('FTMOOrderSend','OrderSend')
        s=s.replace('#include "FTMO_Trade.mqh"','#include <Trade/Trade.mqh>')
        s=re.sub(r'#include\s+"([^"]+)"',lambda z:'#include "'+graph(path.parent/z[1].replace('\\','/'))+'"',s)
        write(R/'Sources'/name,s);return name
    orbplan={x['slug']:x for x in json.loads(read(B/'ORB and Range Breakout RR05 Comparison 2026-10-08/PLAN.json'))['setups']}
    selected=list(m['entries'])
    additions=['xau-orb-new-york-m30']+(['us100-selective-orb-v3'] if args.include_selective else [])
    for key in additions:
        p=orbplan[key]
        selected.append(dict(slug=key,label=p['label'],symbol=p['symbol'],timeframe=p['period'],inputs=dict(p['input_settings']),source=p['source']))
    orbs=ORBS+(['us100-selective-orb-v3'] if args.include_selective else [])
    for e in selected:
        values={k:str(v) for k,v in e['inputs'].items() if not k.startswith('FTMO')}
        values.update(InpRiskPercent='0.5',InpAdaptivePortfolioControls='false')
        if 'InpRiskMode' in values:values['InpRiskMode']='0'
        if 'InpTesterOnly' in values:values['InpTesterOnly']='false'
        if e['slug'] in orbs:values['InpRewardRisk']='0.5'
        values.update(InpPortfolioRiskMode='0',InpPortfolioPercent='0.5',InpPortfolioFixedUSD='50.0',InpPortfolioExpectedLogin='0',InpPortfolioExpectedServer='',InpPortfolioExpectedSymbol='',InpPortfolioInstallNonce='')
        if e['slug'] not in additions:
            wrapper=read(OLD/'package'/e['expert'].replace('.ex5','.mq5'))
            top=re.search(r'#include "(src_[^"]+)"',wrapper)[1];inc=graph(OLD/'package'/top)
        else:inc=graph(Path(e['source']))
        expanded='\n'.join(read(R/'Sources'/n) for n in cache.values())
        # Only transitive dependencies of this entry determine its timer callback.
        def expansion(n,seen=None):
            seen=set() if seen is None else seen
            if n in seen:return ''
            seen.add(n);t=read(R/'Sources'/n)
            return t+'\n'+'\n'.join(expansion(v,seen) for v in re.findall(r'#include "(src_[^"]+)"',t))
        code=expansion(inc);timer=bool(re.search(r'void\s+OnTimer\s*\(',code))
        assert 'CalyxAdaptiveRiskMultiplier(' in code,e['slug']
        name='Calyx Current14 ORB05 - '+e['slug']
        s='#property strict\n#include "../RiskSupport.mqh"\n#define OnInit UR_StrategyInit\n#define OnTick UR_StrategyTick\n#define OnTimer UR_StrategyTimer\n#include "'+inc+'"\n#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
        s+='int OnInit(){if(!UR_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;int r=UR_StrategyInit();if(r==INIT_SUCCEEDED)UR_Heartbeat(InpMagic,true);return r;}\n'
        s+='void OnTick(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTick();}\n'
        if timer:s+='void OnTimer(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTimer();}\n'
        path=R/'Sources'/(name+'.mq5');write(path,s)
        sp=R/'Sets'/(e['slug']+'.set');write(sp,'\n'.join(k+'='+v for k,v in values.items())+'\n')
        if not args.no_compile:
            log=path.with_suffix('.compile.log');began=time.time()
            subprocess.run(f'"{TESTER/"MetaEditor64.exe"}" /portable /compile:"{path}" /log:"{log}"',creationflags=subprocess.CREATE_NO_WINDOW,timeout=120)
            text=read(log);assert '0 errors, 0 warnings' in text,text[-5000:]
            binary=path.with_suffix('.ex5');assert binary.stat().st_mtime>=began-2
            shutil.copy2(binary,R/'Experts'/binary.name)
        expert=R/'Experts'/(name+'.ex5')
        entries.append(dict(key=e['slug'],label=e['label'],canonical=e['symbol'],period={'M1':1,'M5':5,'M15':15,'M30':30,'H1':60,'H4':240}[e['timeframe']],magic=int(values['InpMagic']),hourly=False,expert=str(expert.relative_to(R)).replace('\\','/'),settings=str(sp.relative_to(R)).replace('\\','/'),inputs=values,di_input='InpRequireDIAgreement' if e['slug'] in ['nasdaq-5m-candle-momentum','usdjpy-london-open-momentum'] else None,source=str(path.relative_to(R)).replace('\\','/')))
        print('BUILT '+e['slug'],flush=True)
    count=len(entries);assert count==15+args.include_selective
    assert len({e['key'] for e in entries})==count and len({e['magic'] for e in entries})==count
    shutil.copy2(FIVE/'Installer-Helpers.ps1',R/'Installer-Helpers.ps1')
    shutil.copy2(FIVE/'Probe-MT5.py',R/'Probe-MT5.py')
    write(R/'Install-Portfolio.ps1',transform_installer(count))
    package=dict(version='CURRENT14-ORB05-20261008',profile='Calyx CURRENT14 ORB05',entries=entries,orb_keys=orbs,
        current14_manifest=m['version'],default_percent=.5,required_margin_mode=2,news=False,ftmo_guard=False,shared_daily_stop=False,
        selective_included=args.include_selective,selection='Current14 deduplicated plus only requested 0.5R ORBs',
        compatibility='MT5 demo/live hedging accounts; percentage in account currency, fixed USD with fresh direct currency conversion. Netting and MT4 not supported.',
        no_live_installation=True,original_hashes=original)
    save(R/'Package.json',package)
    hashes={str(p.relative_to(R)).replace('\\','/'):sha(p) for p in [R/'Package.json',R/'Install-Portfolio.ps1',R/'Installer-Helpers.ps1',R/'Probe-MT5.py']+list((R/'Experts').glob('*.ex5'))+list((R/'Sets').glob('*.set'))}
    save(R/'Checksums.json',hashes)
    payload=io.BytesIO()
    with zipfile.ZipFile(payload,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for name in sorted(hashes):z.write(R/name,name)
        z.write(R/'Checksums.json','Checksums.json')
    data=payload.getvalue();digest=hashlib.sha256(data).hexdigest()
    # BAT entry point contains a verified ZIP; only the payload reaches its new temp directory.
    ps="""$ErrorActionPreference='Stop';$raw=[IO.File]::ReadAllText($env:CALYX_BUNDLE_FILE);$encoded=$raw.Substring($raw.LastIndexOf(':CALYX_PAYLOAD_V1')+17).Trim();$data=[Convert]::FromBase64String($encoded);$sha=[Security.Cryptography.SHA256]::Create();try{$hash=[BitConverter]::ToString($sha.ComputeHash($data)).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()};if($hash -ne '__SHA__'){throw 'BAT payload integrity check failed'};$root=Join-Path ([IO.Path]::GetTempPath()) ('CalyxCurrent14ORB05-'+[guid]::NewGuid().ToString('N'));[void][IO.Directory]::CreateDirectory($root);Add-Type -AssemblyName System.IO.Compression;$memory=[IO.MemoryStream]::new($data);$zip=[IO.Compression.ZipArchive]::new($memory,[IO.Compression.ZipArchiveMode]::Read);try{foreach($entry in $zip.Entries){$path=[IO.Path]::GetFullPath((Join-Path $root $entry.FullName));if(-not $path.StartsWith($root+'\\',[StringComparison]::OrdinalIgnoreCase)){throw 'Unsafe archive path'};[void][IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path));$src=$entry.Open();$dst=[IO.File]::Create($path);try{$src.CopyTo($dst)}finally{$src.Dispose();$dst.Dispose()}}}finally{$zip.Dispose();$memory.Dispose()};Write-Host ('Package extracted to '+$root);& (Join-Path $root 'Install-Portfolio.ps1') __ARGS__;exit $LASTEXITCODE"""
    ps=ps.replace('__SHA__',digest)
    # Bind caller options as data, never insert them into PowerShell command text.
    declaration=read(R/'Install-Portfolio.ps1').split("$ErrorActionPreference = 'Stop'",1)[0]
    bootstrap=declaration+ps.replace(' __ARGS__',' @PSBoundParameters')
    # A short CMD line extracts plain PowerShell below EXIT: no 8191-character overflow.
    launcher="$raw=[IO.File]::ReadAllText($env:CALYX_BUNDLE_FILE);$start=$raw.LastIndexOf(':CALYX_BOOTSTRAP_V1')+19;$end=$raw.LastIndexOf(':CALYX_PAYLOAD_V1');if($start -lt 19 -or $end -le $start){throw 'Missing bootstrap'};$data=[Text.Encoding]::UTF8.GetBytes($raw.Substring($start,$end-$start));$stream=[IO.File]::Open($env:CALYX_BOOTSTRAP,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None);try{$stream.Write($data,0,$data.Length)}finally{$stream.Dispose()}"
    header='@echo off\r\nsetlocal\r\ntitle Calyx Current14 plus ORB 0.5R\r\nset "CALYX_BUNDLE_FILE=%~f0"\r\nset "CALYX_BOOTSTRAP=%TEMP%\\CalyxCurrent14ORB05-%RANDOM%-%RANDOM%-%RANDOM%.ps1"\r\npowershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command "'+launcher+'"\r\nif errorlevel 1 exit /b 1\r\npowershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CALYX_BOOTSTRAP%" %*\r\nset "CALYX_EXIT=%ERRORLEVEL%"\r\nif /I not "%~1"=="-ValidateOnly" pause\r\nexit /b %CALYX_EXIT%\r\n:CALYX_BOOTSTRAP_V1\r\n'+bootstrap.replace('\n','\r\n')+'\r\n:CALYX_PAYLOAD_V1\r\n'
    assert max(map(len,header.split('exit /b %CALYX_EXIT%')[0].splitlines()))<8191
    # ValidateOnly remains a no-MT5 invocation; all expert data is embedded below EXIT.
    bat=header+base64.b64encode(data).decode()+'\r\n'
    target=B/'current14_orb05.bat';target.write_bytes(bat.encode('ascii'))
    assert all(sha(Path(p))==h for p,h in original.items())
    save(R/'BUILD.json',dict(eas=count,orbs=len(orbs),all_orbs_rr=.5,duplicates=0,source_files_unchanged=len(original),payload_sha256=digest,payload_bytes=len(data),single_bat=str(target),live_account_access=False,compiled=not args.no_compile))
    print('SINGLE BAT READY '+str(target),flush=True)

if __name__=='__main__':main()
