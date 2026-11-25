# FIX PYTHON FOR MT5 (owner 2026-11-25, VPS error "Fatal Python error: Failed to import encodings module" at the installer's account preflight).
# The Calyx installers read the account through Python + the MetaTrader5 package. This script makes that work:
#   1. removes a stale PYTHONHOME / PYTHONPATH (the usual cause of "No module named 'encodings'")   [asks first]
#   2. finds a Python that starts; if none, installs Python 3.12 (winget, or the official python.org installer)   [asks first]
#   3. installs / updates the MetaTrader5 package in that Python   [asks first]
#   4. checks: python -c "import encodings, MetaTrader5"
# -CheckOnly: only report, change nothing. Touches no MT5 terminal, account or trade.
param([switch]$CheckOnly, [switch]$Yes)
$ErrorActionPreference = 'Stop'

function Ask([string]$q) { if ($Yes) { return $true }; if ($CheckOnly) { return $false }; return ((Read-Host "$q [Y/n]").Trim().ToUpperInvariant() -in @('', 'Y', 'YES')) }

function Test-Py([string]$exe, [string]$code) {
    $out = ''
    try { $out = (& $exe -c $code 2>&1 | ForEach-Object { [string]$_ }) -join ' ' } catch { $out = [string]$_ }
    return [pscustomobject]@{ ok = ($LASTEXITCODE -eq 0); out = ($out -replace '\s+', ' ').Trim() }
}

function Get-PyCandidates {
    $list = [System.Collections.Generic.List[string]]::new()
    foreach ($c in @(Get-Command python.exe -All -ErrorAction SilentlyContinue)) { if ($c.Source -and $c.Source -notmatch '\\WindowsApps\\') { $list.Add($c.Source) } }
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) { try { $p = (& $py.Source -3 -c "import sys;print(sys.executable)" 2>$null | Select-Object -Last 1); if ($p) { $list.Add(([string]$p).Trim()) } } catch {} }
    foreach ($root in @("$env:LOCALAPPDATA\Programs\Python", $env:ProgramFiles, ${env:ProgramFiles(x86)}, 'C:\')) {
        if ($root -and (Test-Path -LiteralPath $root)) {
            foreach ($d in @(Get-ChildItem -LiteralPath $root -Directory -Filter 'Python3*' -ErrorAction SilentlyContinue)) { $e = Join-Path $d.FullName 'python.exe'; if (Test-Path -LiteralPath $e) { $list.Add($e) } }
        }
    }
    return @($list | Select-Object -Unique)
}

Write-Host 'FIX PYTHON FOR MT5 - makes the Calyx installers able to read your MT5 account' -ForegroundColor Green
if ($CheckOnly) { Write-Host '(check only: nothing will be changed)' -ForegroundColor Yellow }

# 1. stale PYTHONHOME / PYTHONPATH
foreach ($name in @('PYTHONHOME', 'PYTHONPATH')) {
    foreach ($scope in @('Process', 'User', 'Machine')) {
        $v = [Environment]::GetEnvironmentVariable($name, $scope)
        if ($v) {
            Write-Host ("Found {0} ({1}) = {2}" -f $name, $scope, $v) -ForegroundColor Yellow
            if ($scope -eq 'Process') { Remove-Item "Env:$name" -ErrorAction SilentlyContinue; continue }
            if (Ask "Remove $name from the $scope settings? (it breaks every Python install)") {
                try { [Environment]::SetEnvironmentVariable($name, $null, $scope); Write-Host "  removed" }
                catch { Write-Host "  could not remove it (run this BAT as Administrator for Machine settings): $($_.Exception.Message)" -ForegroundColor Red }
            }
            Remove-Item "Env:$name" -ErrorAction SilentlyContinue
        }
    }
}

# 2. a Python that starts
$good = $null
foreach ($exe in Get-PyCandidates) {
    $t = Test-Py $exe 'import encodings, sys; print(sys.version.split()[0])'
    Write-Host ("  {0} -> {1}" -f $exe, $(if ($t.ok) { 'starts, Python ' + $t.out } else { 'BROKEN: ' + $t.out.Substring(0, [Math]::Min(100, $t.out.Length)) }))
    if ($t.ok -and -not $good) { $good = $exe }
}
if (-not $good) {
    Write-Host 'No working Python found.' -ForegroundColor Red
    if (-not (Ask 'Install Python 3.12 now?')) { Write-Host 'Nothing installed. Install Python 3.12 from python.org (tick "Add python.exe to PATH") and run this again.'; exit 1 }
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if ($winget) {
        & $winget.Source install -e --id Python.Python.3.12 --scope machine --accept-package-agreements --accept-source-agreements
    } else {
        $url = 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe'
        $file = Join-Path $env:TEMP 'python-3.12.8-amd64.exe'
        Write-Host "Downloading $url"
        Invoke-WebRequest -Uri $url -OutFile $file -UseBasicParsing
        $sig = Get-AuthenticodeSignature -FilePath $file
        if ($sig.Status -ne 'Valid' -or $sig.SignerCertificate.Subject -notmatch 'Python Software Foundation') { throw "Downloaded file is not signed by the Python Software Foundation ($($sig.Status)); not running it." }
        Start-Process -FilePath $file -ArgumentList '/quiet', 'InstallAllUsers=1', 'PrependPath=1', 'Include_test=0' -Wait
    }
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
    foreach ($exe in Get-PyCandidates) { if ((Test-Py $exe 'import encodings').ok) { $good = $exe; break } }
    if (-not $good) { throw 'Python was installed but still does not start. Restart the VPS (or sign out / in) and run this again.' }
}
Write-Host "Using Python: $good" -ForegroundColor Cyan

# 3. MetaTrader5 package
$t = Test-Py $good 'import MetaTrader5; print(MetaTrader5.__version__)'
if ($t.ok) { Write-Host "MetaTrader5 package: $($t.out)" }
else {
    Write-Host 'The MetaTrader5 package is missing in this Python.' -ForegroundColor Yellow
    if (-not (Ask "Install it now ($good -m pip install MetaTrader5)?")) { Write-Host 'Nothing installed.'; exit 1 }
    & $good -m pip install --upgrade pip
    & $good -m pip install --upgrade MetaTrader5
}

# 4. final check (same test the installers use)
$t = Test-Py $good "import encodings, MetaTrader5; print('CALYX_PY_OK')"
if ($t.ok -and $t.out -match 'CALYX_PY_OK') {
    Write-Host ''; Write-Host "PYTHON OK: $good can run the installers. Now run 'Ready for FTMO.bat' again." -ForegroundColor Green; exit 0
}
Write-Host ''; Write-Host "Still not working: $($t.out)" -ForegroundColor Red; exit 1
