$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$env:PYTHONDONTWRITEBYTECODE = '1'

$uv = Get-Command uv.exe -ErrorAction SilentlyContinue
if (-not $uv) {
    foreach ($candidate in @(
        "$env:USERPROFILE\.local\bin\uv.exe",
        "$env:USERPROFILE\.cargo\bin\uv.exe"
    )) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            $uv = Get-Item -LiteralPath $candidate
            break
        }
    }
}
if (-not $uv) {
    throw 'uv.exe was not found. Run INSTALL_AND_RUN_GOLD_NEWS_V9.bat to repair the installation.'
}

Set-Location -LiteralPath $root
$uvPath = if ($uv -is [Management.Automation.CommandInfo]) { $uv.Source } else { $uv.FullName }
& $uvPath run --quiet python -u server_supervisor.py
exit $LASTEXITCODE
