import json,re,base64,subprocess
from build import ROOT,REPO,CLIENT,TESTER,read,sha

def main():
    manifest=json.loads((ROOT/'manifest.json').read_text())
    # No private source paths, source hashes, credentials or owner tooling in the BAT.
    public={'licence':manifest['licence'],'entries':manifest['entries']}
    src=read(REPO/'AAA EAs/EA store/app/store/installer/Install-CalyxBot.ps1')
    chart=src[src.index('function New-ChartText('):src.index('function Update-WebRequestAllowList(')].strip()
    detector=ROOT/'DetectBrokerSymbols.mq5';log=detector.with_suffix('.log')
    subprocess.run(f'"{TESTER/"metaeditor64.exe"}" /portable /compile:"{detector}" /log:"{log}"',timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
    assert re.search(r'\b0 errors, 0 warnings\b',read(log)),read(log)[-2000:]
    compiled=detector.with_suffix('.ex5');assert compiled.exists()
    mapping=read(ROOT/'symbol_mapping.ps1').replace('__DETECTOR_B64__',base64.b64encode(compiled.read_bytes()).decode()).replace('__DETECTOR_SHA256__',sha(compiled))
    automatic=read(ROOT/'auto_setup.ps1').replace('__DETECTOR_B64__',base64.b64encode(compiled.read_bytes()).decode()).replace('__DETECTOR_SHA256__',sha(compiled))
    ps=read(ROOT/'installer.ps1').replace('__CHART_FUNCTION__',chart).replace('__SYMBOL_MAPPING_FUNCTIONS__',mapping).replace('__AUTO_SETUP_FUNCTIONS__',automatic).replace('__MANIFEST_B64__',base64.b64encode(json.dumps(public).encode()).decode())
    (ROOT/'installer.generated.ps1').write_text(ps,encoding='utf-8-sig')
    header='''@echo off
setlocal
set "CALYX_BUNDLE_FILE=%~f0"
set "CALYX_VALIDATE_ONLY=0"
set "CALYX_LIBRARY_ONLY=0"
if /I "%~1"=="--validate" set "CALYX_VALIDATE_ONLY=1"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop';try{$s=[IO.File]::ReadAllText($env:CALYX_BUNDLE_FILE);$marker='#'+' CALYX_POWERSHELL_START';$i=$s.IndexOf($marker);if($i -lt 0){throw 'Installer damaged'};& ([ScriptBlock]::Create($s.Substring($i+$marker.Length)))}catch{Write-Host $_ -ForegroundColor Red;exit 1}"
set "CALYX_EXIT=%errorlevel%"
if not "%~1"=="--validate" pause
exit /b %CALYX_EXIT%
# CALYX_POWERSHELL_START
'''
    (CLIENT/'Install Top 5.bat').write_bytes((header+ps).replace('\n','\r\n').encode('utf-8'))
    print('Built self-contained BAT')
if __name__=='__main__':main()
