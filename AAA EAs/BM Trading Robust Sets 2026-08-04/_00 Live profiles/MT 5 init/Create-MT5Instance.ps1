param(
    [string]$Name,
    [string]$InstancesRoot = 'C:\MT5 Instances',
    [string]$Source,
    [switch]$NoLaunch,
    [switch]$NoShortcut,
    [switch]$ValidateOnly
)
# Creates a new, empty MetaTrader 5 instance (its own folder, its own data folder, no account) so another account can
# run side by side on this PC/VPS. Copies program files only: never accounts, passwords, EAs, profiles with EAs or history.
# It does not log in, install EAs, change AutoTrading or touch any existing terminal.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Stop-WithMessage([string]$Message) {
    Write-Host ''
    Write-Host ('ERROR: ' + $Message) -ForegroundColor Red
    exit 1
}

function Find-SourceTerminal {
    if ($Source) {
        $path = if ((Test-Path -LiteralPath $Source -PathType Leaf)) { Split-Path -Parent $Source } else { $Source }
        if (-not (Test-Path -LiteralPath (Join-Path $path 'terminal64.exe'))) { Stop-WithMessage "No terminal64.exe in -Source: $path" }
        return [IO.Path]::GetFullPath($path)
    }
    $instancesFull = [IO.Path]::GetFullPath($InstancesRoot).TrimEnd('\') + '\'
    $tempFull = [IO.Path]::GetFullPath($env:TEMP).TrimEnd('\') + '\'
    $candidates = @()
    foreach ($programs in @($env:ProgramFiles, ${env:ProgramFiles(x86)})) {
        if (-not $programs -or -not (Test-Path -LiteralPath $programs)) { continue }
        foreach ($dir in @(Get-ChildItem -LiteralPath $programs -Directory -ErrorAction SilentlyContinue)) {
            if (Test-Path -LiteralPath (Join-Path $dir.FullName 'terminal64.exe')) { $candidates += $dir.FullName }
        }
    }
    $terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    if (Test-Path -LiteralPath $terminalRoot) {
        foreach ($origin in @(Get-ChildItem -LiteralPath $terminalRoot -Recurse -Filter origin.txt -File -ErrorAction SilentlyContinue)) {
            $install = (Get-Content -LiteralPath $origin.FullName -Raw).Trim()
            if ($install -and (Test-Path -LiteralPath (Join-Path $install 'terminal64.exe'))) { $candidates += [IO.Path]::GetFullPath($install) }
        }
    }
    # Never clone Ava (kept separate), research testers, temporary copies or existing instances.
    $usable = @($candidates | Sort-Object -Unique | Where-Object {
        $full = $_.TrimEnd('\') + '\'
        -not $full.StartsWith($instancesFull, [StringComparison]::OrdinalIgnoreCase) -and
        -not $full.StartsWith($tempFull, [StringComparison]::OrdinalIgnoreCase) -and
        $_ -notmatch '(?i)\\_Backtests\\|\\AppData\\Local\\Calyx\\|\bAva\b'
    })
    if ($usable.Count -eq 0) { Stop-WithMessage 'No MetaTrader 5 installation was found. Install MT5 once (any broker), or run with -Source "<MT5 folder>".' }
    # Prefer the plain MetaQuotes install, then any "MetaTrader 5" folder, then the rest (alphabetical).
    $plain = @($usable | Where-Object { (Split-Path -Leaf $_) -ieq 'MetaTrader 5' })
    if ($plain.Count -gt 0) { return $plain[0] }
    $named = @($usable | Where-Object { (Split-Path -Leaf $_) -match '(?i)MetaTrader 5' })
    if ($named.Count -gt 0) { return $named[0] }
    return $usable[0]
}

function Test-InstanceName([string]$Value) {
    if (-not $Value) { return 'The name is empty.' }
    if ($Value -notmatch '^[A-Za-z0-9][A-Za-z0-9 _.-]{0,39}$') { return 'Use 1-40 letters, digits, spaces, "-", "_" or "." (start with a letter or digit).' }
    if ($Value -match '[ .]$') { return 'The name cannot end with a space or a dot.' }
    if ($Value -match '^(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$') { return 'That name is reserved by Windows.' }
    if (Test-Path -LiteralPath (Join-Path $InstancesRoot $Value)) { return ('An instance with that name already exists: ' + (Join-Path $InstancesRoot $Value)) }
    return $null
}

Write-Host ''
Write-Host 'Create a new MT5 instance' -ForegroundColor Cyan
$sourceRoot = Find-SourceTerminal
Write-Host ('Copying program files from: ' + $sourceRoot)
Write-Host ('New instances are created in: ' + $InstancesRoot)
Write-Host ''

if (-not $Name) {
    while ($true) {
        $Name = (Read-Host 'Instance name (for example "Exness Demo 2" or "FTMO 100k")').Trim()
        $problem = Test-InstanceName $Name
        if (-not $problem) { break }
        Write-Host $problem -ForegroundColor Yellow
    }
} else {
    $Name = $Name.Trim()
    $problem = Test-InstanceName $Name
    if ($problem) { Stop-WithMessage $problem }
}
$target = Join-Path $InstancesRoot $Name

# Safe copy list: program files and the stock seed files only.
$copy = @()
foreach ($file in @(Get-ChildItem -LiteralPath $sourceRoot -File | Where-Object { $_.Extension -in @('.exe', '.ico', '.dll') -and $_.Name -ine 'uninstall.exe' })) {
    $copy += [pscustomobject]@{ From = $file.FullName; To = (Join-Path $target $file.Name); Folder = $false }
}
foreach ($rel in @('Config\servers.dat', 'Config\terminal.lic')) {
    $from = Join-Path $sourceRoot $rel
    if (Test-Path -LiteralPath $from -PathType Leaf) { $copy += [pscustomobject]@{ From = $from; To = (Join-Path $target $rel); Folder = $false } }
}
foreach ($rel in @('Sounds', 'Profiles\Templates', 'Profiles\SymbolSets', 'Profiles\Charts\Default', 'Bases\Default')) {
    $from = Join-Path $sourceRoot $rel
    if (Test-Path -LiteralPath $from -PathType Container) { $copy += [pscustomobject]@{ From = $from; To = (Join-Path $target $rel); Folder = $true } }
}
if (-not @($copy | Where-Object { (Split-Path -Leaf $_.From) -ieq 'terminal64.exe' })) { Stop-WithMessage "terminal64.exe not found in $sourceRoot" }

Write-Host ''
Write-Host ('Instance:      ' + $Name) -ForegroundColor Green
Write-Host ('Folder:        ' + $target)
Write-Host ('Program:       ' + (Join-Path $target 'terminal64.exe'))
foreach ($item in $copy) { Write-Host ('  copy ' + $item.From.Substring($sourceRoot.Length).TrimStart('\')) -ForegroundColor DarkGray }
if ($ValidateOnly) {
    Write-Host ''
    Write-Host 'Validation only: nothing was copied, created or started.' -ForegroundColor Green
    exit 0
}

Write-Host ''
Write-Host 'Copying...' -ForegroundColor Cyan
New-Item -ItemType Directory -Path $target -Force | Out-Null
foreach ($item in $copy) {
    if ($item.Folder) {
        New-Item -ItemType Directory -Path $item.To -Force | Out-Null
        Copy-Item -Path (Join-Path $item.From '*') -Destination $item.To -Recurse -Force
    } else {
        New-Item -ItemType Directory -Path (Split-Path -Parent $item.To) -Force | Out-Null
        Copy-Item -LiteralPath $item.From -Destination $item.To -Force
    }
}
$exe = Join-Path $target 'terminal64.exe'
if ((Get-Item -LiteralPath $exe).Length -ne (Get-Item -LiteralPath (Join-Path $sourceRoot 'terminal64.exe')).Length) { Stop-WithMessage 'terminal64.exe copy is incomplete.' }
[pscustomobject]@{
    name = $Name
    created_local = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
    copied_from = $sourceRoot
    note = 'Calyx MT5 instance: program files only (no account, EAs or history). Log in, then apply a Calyx profile BAT.'
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $target 'calyx-instance.json') -Encoding UTF8

if (-not $NoShortcut) {
    $desktop = [Environment]::GetFolderPath('Desktop')
    $link = Join-Path $desktop ('MT5 - ' + $Name + '.lnk')
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($link)
    $shortcut.TargetPath = $exe
    $shortcut.WorkingDirectory = $target
    $shortcut.Description = 'MetaTrader 5 instance: ' + $Name
    $iconPath = Join-Path $target 'Terminal.ico'
    $shortcut.IconLocation = if (Test-Path -LiteralPath $iconPath) { $iconPath } else { $exe + ',0' }
    $shortcut.Save()
    Write-Host ('Desktop shortcut: ' + $link) -ForegroundColor Green
}

if (-not $NoLaunch) {
    Start-Process -FilePath $exe -WorkingDirectory $target
    # MT5 registers its data folder (origin.txt) on first start; the Calyx installers find the instance through it.
    $dataFolder = $null
    $terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    for ($i = 0; $i -lt 40 -and -not $dataFolder; $i++) {
        Start-Sleep -Milliseconds 500
        if (-not (Test-Path -LiteralPath $terminalRoot)) { continue }
        foreach ($origin in @(Get-ChildItem -LiteralPath $terminalRoot -Recurse -Filter origin.txt -File -ErrorAction SilentlyContinue)) {
            if ((Get-Content -LiteralPath $origin.FullName -Raw).Trim().TrimEnd('\') -ieq $target.TrimEnd('\')) { $dataFolder = $origin.DirectoryName; break }
        }
    }
    if ($dataFolder) { Write-Host ('Data folder:   ' + $dataFolder) } else { Write-Host 'MT5 started; its data folder appears after the first start completes.' -ForegroundColor Yellow }
}

Write-Host ''
Write-Host 'Done. Next:' -ForegroundColor Cyan
Write-Host '  1. In the new MT5 window: File > Login to Trade Account (tick "Save password"), or open a demo account.'
Write-Host '  2. Run the Calyx profile BAT you want. If several MT5 terminals are running, pick this path from its list:'
Write-Host ('     ' + $exe)
Write-Host '  3. Never log two terminals into the same account.'
exit 0
