param(
    [switch]$DryRun,
    [switch]$PublicTunnel,
    [switch]$LocalOnly,
    [string]$ApiKey = $(if ($env:MCP_PROXY_API_KEY) { $env:MCP_PROXY_API_KEY } else { "mcp-tokens" })
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $PSCommandPath
$RuntimeRoot = Join-Path $ScriptRoot ".mcp-runtime"

if (-not $LocalOnly) {
    $PublicTunnel = $true
}

function Add-ToPathFront {
    param([string]$PathToAdd)
    if (-not $PathToAdd -or -not (Test-Path -LiteralPath $PathToAdd)) {
        return
    }

    $pathParts = $env:Path -split ';' | Where-Object { $_ }
    if ($pathParts -notcontains $PathToAdd) {
        $env:Path = "$PathToAdd;$env:Path"
    }
}

function Refresh-KnownToolPaths {
    Add-ToPathFront (Join-Path $RuntimeRoot "node")
    Add-ToPathFront (Join-Path $RuntimeRoot "mingit\cmd")
    Add-ToPathFront (Join-Path $RuntimeRoot "mingit\mingw64\bin")
    Add-ToPathFront (Join-Path $env:USERPROFILE ".local\bin")
    Add-ToPathFront (Join-Path $env:USERPROFILE ".cargo\bin")
    Add-ToPathFront "C:\Program Files\nodejs"
    Add-ToPathFront "C:\Program Files\Git\cmd"
    Add-ToPathFront "C:\Program Files\Git\bin"
}

function Test-CommandAvailable {
    param([string]$CommandName)
    return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
}

function Install-LocalNode {
    $nodeRoot = Join-Path $RuntimeRoot "node"
    $npxPath = Join-Path $nodeRoot "npx.cmd"
    if (Test-Path -LiteralPath $npxPath) {
        Add-ToPathFront $nodeRoot
        return
    }

    Write-Host "Node.js/npx not found. Downloading a local Node.js runtime..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $releaseIndex = Invoke-RestMethod -Uri "https://nodejs.org/dist/index.json"
    $release = $releaseIndex |
        Where-Object { $_.lts -and ($_.files -contains "win-x64-zip") } |
        Select-Object -First 1

    if (-not $release) {
        throw "Could not find a Windows x64 Node.js LTS download."
    }

    $version = $release.version
    $zipUrl = "https://nodejs.org/dist/$version/node-$version-win-x64.zip"
    $zipPath = Join-Path $RuntimeRoot "node-$version-win-x64.zip"
    $extractPath = Join-Path $RuntimeRoot "node-extract"

    Remove-Item -LiteralPath $extractPath -Recurse -Force -ErrorAction SilentlyContinue
    Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force

    $expandedDir = Get-ChildItem -LiteralPath $extractPath -Directory | Select-Object -First 1
    if (-not $expandedDir) {
        throw "Node.js download extracted, but no Node.js folder was found."
    }

    Remove-Item -LiteralPath $nodeRoot -Recurse -Force -ErrorAction SilentlyContinue
    Move-Item -LiteralPath $expandedDir.FullName -Destination $nodeRoot
    Remove-Item -LiteralPath $extractPath -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue

    Add-ToPathFront $nodeRoot
    Write-Host "Installed local Node.js runtime at $nodeRoot" -ForegroundColor Green
}

function Install-LocalGit {
    $gitRoot = Join-Path $RuntimeRoot "mingit"
    $gitPath = Join-Path $gitRoot "cmd\git.exe"
    if (Test-Path -LiteralPath $gitPath) {
        Add-ToPathFront (Join-Path $gitRoot "cmd")
        Add-ToPathFront (Join-Path $gitRoot "mingw64\bin")
        return
    }

    Write-Host "Downloading portable Git..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $headers = @{ "User-Agent" = "local-mcp-launcher" }
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/git-for-windows/git/releases/latest" -Headers $headers
    $asset = $release.assets |
        Where-Object { $_.name -match '^MinGit-.*-64-bit\.zip$' -and $_.name -notmatch 'busybox' } |
        Select-Object -First 1

    if (-not $asset) {
        throw "Could not find a portable Git release to download."
    }

    $zipPath = Join-Path $RuntimeRoot $asset.name
    $extractPath = Join-Path $RuntimeRoot "mingit-extract"

    Remove-Item -LiteralPath $extractPath -Recurse -Force -ErrorAction SilentlyContinue
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zipPath -Headers $headers
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force

    Remove-Item -LiteralPath $gitRoot -Recurse -Force -ErrorAction SilentlyContinue
    Move-Item -LiteralPath $extractPath -Destination $gitRoot
    Remove-Item -LiteralPath $zipPath -Force -ErrorAction SilentlyContinue

    Add-ToPathFront (Join-Path $gitRoot "cmd")
    Add-ToPathFront (Join-Path $gitRoot "mingw64\bin")
    Write-Host "Installed portable Git at $gitRoot" -ForegroundColor Green
}

function Ensure-Npx {
    Refresh-KnownToolPaths
    if (-not (Test-CommandAvailable "npx.cmd")) {
        Install-LocalNode
    }
    Refresh-KnownToolPaths
    if (-not (Test-CommandAvailable "npx.cmd")) {
        throw "npx.cmd is still not available after installing local Node.js."
    }
}

function Ensure-Uv {
    Refresh-KnownToolPaths
    if ((Test-CommandAvailable "uv") -and (Test-CommandAvailable "uvx")) {
        return
    }

    Write-Host "uv/uvx not found. Installing uv for the current user..." -ForegroundColor Yellow
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

    try {
        powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    } catch {
        Write-Host "uv installer failed. Trying winget..." -ForegroundColor Yellow
        if (Test-CommandAvailable "winget") {
            winget install --id astral-sh.uv -e --source winget --accept-package-agreements --accept-source-agreements
        } else {
            throw
        }
    }

    Refresh-KnownToolPaths
    if (-not ((Test-CommandAvailable "uv") -and (Test-CommandAvailable "uvx"))) {
        throw "uv/uvx are still not available after installation."
    }
}

function Ensure-Git {
    Refresh-KnownToolPaths
    if (Test-CommandAvailable "git") {
        return
    }

    if (Test-CommandAvailable "winget") {
        Write-Host "Git not found. Installing Git with winget..." -ForegroundColor Yellow
        try {
            winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
        } catch {
            Write-Host "winget Git install failed. Falling back to portable Git..." -ForegroundColor Yellow
        }
    }

    Refresh-KnownToolPaths
    if (-not (Test-CommandAvailable "git")) {
        Install-LocalGit
    }

    Refresh-KnownToolPaths
    if (-not (Test-CommandAvailable "git")) {
        throw "Git is still not available after automatic installation."
    }
}

function Test-PortBusy {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Format-Argument {
    param([string]$Value)
    if ($Value -match '[\s"&|<>^]') {
        return '"' + ($Value -replace '"', '\"') + '"'
    }
    return $Value
}

function ConvertTo-ForwardSlashPath {
    param([string]$Path)
    return ($Path -replace '\\', '/')
}

function Escape-SingleQuotedPowerShell {
    param([string]$Value)
    return $Value -replace "'", "''"
}

function Format-PowerShellArrayLiteral {
    param([string[]]$Values)
    $quotedValues = $Values | ForEach-Object { "'" + (Escape-SingleQuotedPowerShell $_) + "'" }
    return "@(" + ($quotedValues -join ", ") + ")"
}

function ConvertTo-NotionMcpUrl {
    param([string]$Url)
    if (-not $Url) {
        return $null
    }

    $cleanUrl = $Url.Trim().TrimEnd('.', ',', ';', ')', ']')
    if ($cleanUrl -match '/mcp($|[?#])') {
        return $cleanUrl
    }

    return $cleanUrl.TrimEnd('/') + "/mcp"
}

function Get-TunnelUrlFromLog {
    param([string]$LogPath)
    if (-not (Test-Path -LiteralPath $LogPath)) {
        return $null
    }

    $content = Get-Content -LiteralPath $LogPath -Raw -ErrorAction SilentlyContinue
    if (-not $content) {
        return $null
    }

    $explicitMatch = [regex]::Match($content, 'tunnel established at\s+(https://[^\s''"<>]+)', 'IgnoreCase')
    if ($explicitMatch.Success) {
        return ConvertTo-NotionMcpUrl $explicitMatch.Groups[1].Value
    }

    $urls = [regex]::Matches($content, 'https://[^\s''"<>]+') | ForEach-Object { $_.Value }
    $tunnelUrl = $urls | Where-Object { $_ -match 'tunnel\.gla\.ma|gla\.ma|pipenet' } | Select-Object -First 1
    if ($tunnelUrl) {
        return ConvertTo-NotionMcpUrl $tunnelUrl
    }

    return $null
}

function Resolve-ProjectPath {
    param(
        [string[]]$EnvNames,
        [string[]]$Candidates,
        [scriptblock]$Validator = { param($Path) return $true }
    )

    foreach ($envName in $EnvNames) {
        $envValue = [Environment]::GetEnvironmentVariable($envName)
        if ($envValue -and (Test-Path -LiteralPath $envValue) -and (& $Validator $envValue)) {
            return (Resolve-Path -LiteralPath $envValue).Path
        }
    }

    foreach ($candidate in $Candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate) -and (& $Validator $candidate)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }

    return $null
}

function Test-PythonPackageProject {
    param(
        [string]$Path,
        [string]$PackageName
    )

    return (
        (Test-Path -LiteralPath (Join-Path $Path "pyproject.toml")) -and
        (
            (Test-Path -LiteralPath (Join-Path $Path $PackageName)) -or
            (Test-Path -LiteralPath (Join-Path $Path "src\$PackageName"))
        )
    )
}

function Add-Server {
    param(
        [System.Collections.ArrayList]$List,
        [string]$Name,
        [int]$Port,
        [string[]]$Command,
        [hashtable]$Env = @{}
    )

    [void]$List.Add([ordered]@{
        Name = $Name
        Port = $Port
        Command = $Command
        Env = $Env
    })
}

function Add-Skipped {
    param(
        [System.Collections.ArrayList]$List,
        [string]$Name,
        [string]$Reason
    )

    [void]$List.Add([ordered]@{
        Name = $Name
        Reason = $Reason
    })
}

$mcpProxyArgsBase = @(
    "-y",
    "mcp-proxy",
    "--host",
    "127.0.0.1",
    "--streamEndpoint",
    "/mcp"
)

if ($PublicTunnel) {
    $mcpProxyArgsBase += "--tunnel"
    if ($ApiKey) {
        $mcpProxyArgsBase += @("--apiKey", $ApiKey)
    }
}

$servers = [System.Collections.ArrayList]::new()
$skipped = [System.Collections.ArrayList]::new()
$parentRoot = Split-Path -Parent $ScriptRoot

Add-Server $servers "mcp-metatrader5-server" 8821 @("uvx", "--from", "git+https://github.com/Qoyyuum/mcp-metatrader5-server", "mt5mcp")
Add-Server $servers "trading-skills" 8822 @("uvx", "--from", "git+https://github.com/staskh/trading_skills.git", "trading-skills-mcp")

$vibeDir = Resolve-ProjectPath `
    -EnvNames @("VIBE_TRADING_DIR") `
    -Candidates @(
        (Join-Path $ScriptRoot "Vibe-Trading"),
        (Join-Path $ScriptRoot "vibe-trading"),
        (Join-Path $parentRoot "vibe trader\Vibe-Trading"),
        (Join-Path $env:USERPROFILE "Desktop\geek\vibe trader\Vibe-Trading")
    )
if ($vibeDir) {
    Add-Server $servers "vibe-trading" 8823 @("uvx", "--from", (ConvertTo-ForwardSlashPath $vibeDir), "vibe-trading-mcp")
} else {
    Add-Skipped $skipped "vibe-trading" "local project folder not found. Set VIBE_TRADING_DIR to its folder."
}

$aiTraderDir = Resolve-ProjectPath `
    -EnvNames @("AI_TRADER_MCP_DIR", "AI_TRADER_DIR") `
    -Candidates @(
        $ScriptRoot,
        (Join-Path $ScriptRoot "ai-trader"),
        (Join-Path $parentRoot "ai-trader"),
        (Join-Path $env:USERPROFILE "Documents\Codex\2026-05-13\hey\ai-trader")
    ) `
    -Validator { param($Path) Test-PythonPackageProject $Path "ai_trader" }
if ($aiTraderDir) {
    Add-Server $servers "ai-trader" 8824 @("uv", "run", "--directory", (ConvertTo-ForwardSlashPath $aiTraderDir), "python", "-m", "ai_trader.mcp")
} else {
    Add-Skipped $skipped "ai-trader" "Python package folder with ai_trader.mcp not found. Set AI_TRADER_MCP_DIR to that project."
}

Add-Server $servers "tradingview" 8825 @("npx.cmd", "-y", "tradingview-mcp-server")
Add-Server $servers "tradingview-mcp-2" 8826 @("uvx", "--from", "tradingview-mcp-server", "tradingview-mcp")

$orderFlowDir = Resolve-ProjectPath `
    -EnvNames @("ORDER_FLOW_MCP_DIR") `
    -Candidates @(
        (Join-Path $ScriptRoot "mcp-order-flow-server"),
        (Join-Path $parentRoot "mcp-order-flow-server"),
        (Join-Path $env:USERPROFILE ".codex\mcp\mcp-order-flow-server")
    ) `
    -Validator { param($Path) Test-Path -LiteralPath (Join-Path $Path "src\mcp_server.py") }
if ($orderFlowDir) {
    Add-Server $servers "mcp-order-flow-server" 8827 `
        @("uv", "run", "--directory", (ConvertTo-ForwardSlashPath $orderFlowDir), "python", "src/mcp_server.py") `
        @{
            DATA_SOURCE = "grpc"
            DATA_BROKER_GRPC_URL = "localhost:9090"
            LOG_LEVEL = "INFO"
        }
} else {
    Add-Skipped $skipped "mcp-order-flow-server" "local project folder not found. Set ORDER_FLOW_MCP_DIR to its folder."
}

Write-Host ""
Write-Host "Local MCP launch list" -ForegroundColor Cyan
Write-Host "====================="
Write-Host ""

Ensure-Npx
Ensure-Uv
Ensure-Git

if ($PublicTunnel -and -not $ApiKey) {
    Write-Host "Warning: PublicTunnel is on but MCP_PROXY_API_KEY is empty. These MCPs may be exposed without an API key." -ForegroundColor Yellow
}

foreach ($server in $servers) {
    $localUrl = "http://127.0.0.1:$($server.Port)/mcp"
    $status = if (Test-PortBusy $server.Port) { "PORT BUSY" } else { "ready" }
    Write-Host ("{0,-24} {1,-10} {2}" -f $server.Name, $status, $localUrl)
}

if ($skipped.Count -gt 0) {
    Write-Host ""
    Write-Host "Skipped local-only MCPs:" -ForegroundColor Yellow
    foreach ($item in $skipped) {
        Write-Host ("{0,-24} {1}" -f $item.Name, $item.Reason) -ForegroundColor Yellow
    }
}

Write-Host ""
if ($PublicTunnel) {
    Write-Host "HTTPS public tunnel mode is ON by default." -ForegroundColor Green
    Write-Host "This launcher will collect the HTTPS tunnel URLs and save them in mcp-links.txt." -ForegroundColor Green
    Write-Host "Default API key/token: $ApiKey" -ForegroundColor Yellow
    Write-Host "In Notion auth, add header X-API-Key with that token." -ForegroundColor Yellow
    Write-Host "To run localhost only instead, use: start-local-mcps.bat -LocalOnly" -ForegroundColor Yellow
} else {
    Write-Host "Local-only mode is ON. Copy/paste the /mcp URLs above if Notion accepts local HTTP URLs." -ForegroundColor Green
    Write-Host "To run HTTPS public tunnels, use: start-local-mcps.bat" -ForegroundColor Yellow
}
Write-Host ""

if ($DryRun) {
    Write-Host "Dry run only. No MCP windows started." -ForegroundColor Cyan
    exit 0
}

$logRoot = Join-Path $ScriptRoot "mcp-logs"
$linksFile = Join-Path $ScriptRoot "mcp-links.txt"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
Remove-Item -Path (Join-Path $logRoot "*.log") -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $linksFile -Force -ErrorAction SilentlyContinue

foreach ($server in $servers) {
    $proxyArgs = @($mcpProxyArgsBase + @("--port", [string]$server.Port, "--") + $server.Command)
    $displayCommand = "npx.cmd " + (($proxyArgs | ForEach-Object { Format-Argument $_ }) -join " ")
    $proxyArgLiteral = Format-PowerShellArrayLiteral $proxyArgs
    $safeLogName = ($server.Name -replace '[^A-Za-z0-9_.-]', '_') + ".log"
    $logPath = Join-Path $logRoot $safeLogName
    $server.LogPath = $logPath

    $envLines = @()
    $envLines += "`$env:Path = '$(Escape-SingleQuotedPowerShell $env:Path)'"
    foreach ($key in $server.Env.Keys) {
        $value = $server.Env[$key]
        $envLines += "`$env:$key = '$(Escape-SingleQuotedPowerShell $value)'"
    }

    $childScriptLines = @()
    $childScriptLines += "Set-Location -LiteralPath '$(Escape-SingleQuotedPowerShell $ScriptRoot)'"
    $childScriptLines += "Write-Host ''"
    $childScriptLines += "Write-Host 'Starting $($server.Name)' -ForegroundColor Cyan"
    $childScriptLines += "Write-Host 'Local MCP URL: http://127.0.0.1:$($server.Port)/mcp' -ForegroundColor Green"
    $childScriptLines += "Write-Host 'Log file: $(Escape-SingleQuotedPowerShell $logPath)' -ForegroundColor DarkGray"
    if ($PublicTunnel) {
        $childScriptLines += "Write-Host 'Public tunnel mode is enabled. This window will print a tunnel URL; the main launcher also saves it to mcp-links.txt.' -ForegroundColor Yellow"
    }
    $childScriptLines += $envLines
    $childScriptLines += "`$proxyArgs = $proxyArgLiteral"
    $childScriptLines += "Write-Host 'Command: $displayCommand' -ForegroundColor DarkGray"
    $childScriptLines += "try {"
    $childScriptLines += "    & npx.cmd @proxyArgs 2>&1 | ForEach-Object { `$line = `$_; Write-Host `$line; `$line | Out-File -LiteralPath '$(Escape-SingleQuotedPowerShell $logPath)' -Append -Encoding UTF8 }"
    $childScriptLines += "} catch {"
    $childScriptLines += "    Write-Host `$_ -ForegroundColor Red"
    $childScriptLines += "    `$_ | Out-File -LiteralPath '$(Escape-SingleQuotedPowerShell $logPath)' -Append -Encoding UTF8"
    $childScriptLines += "}"
    $childScriptLines += "Write-Host 'Proxy stopped. Press any key to close this window.' -ForegroundColor Yellow"
    $childScriptLines += "`$null = `$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')"

    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes(($childScriptLines -join "`r`n")))
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded") -WindowStyle Normal -WorkingDirectory $ScriptRoot
}

Write-Host "Started $($servers.Count) MCP windows." -ForegroundColor Green
Write-Host "Keep those windows open while using the MCPs." -ForegroundColor Green

if ($PublicTunnel) {
    Write-Host ""
    Write-Host "Waiting for HTTPS tunnel links..." -ForegroundColor Cyan

    $deadline = (Get-Date).AddSeconds(90)
    $foundLinks = @{}
    do {
        foreach ($server in $servers) {
            if (-not $foundLinks.ContainsKey($server.Name)) {
                $url = Get-TunnelUrlFromLog $server.LogPath
                if ($url) {
                    $foundLinks[$server.Name] = $url
                }
            }
        }

        if ($foundLinks.Count -ge $servers.Count) {
            break
        }

        Start-Sleep -Seconds 2
    } while ((Get-Date) -lt $deadline)

    $summary = [System.Collections.Generic.List[string]]::new()
    $summary.Add("Notion MCP HTTPS links")
    $summary.Add("======================")
    $summary.Add("")
    $summary.Add("Authentication")
    $summary.Add("Key: X-API-Key")
    $summary.Add("Value: $ApiKey")
    $summary.Add("")

    Write-Host ""
    Write-Host "Notion-ready HTTPS links" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Cyan
    Write-Host "Auth header: X-API-Key = $ApiKey" -ForegroundColor Yellow
    Write-Host ""

    foreach ($server in $servers) {
        if ($foundLinks.ContainsKey($server.Name)) {
            $line = ("{0,-24} {1}" -f $server.Name, $foundLinks[$server.Name])
            Write-Host $line -ForegroundColor Green
            $summary.Add($line)
        } else {
            $line = ("{0,-24} {1}" -f $server.Name, "No HTTPS tunnel URL found yet. Check mcp-logs\$($server.Name -replace '[^A-Za-z0-9_.-]', '_').log")
            Write-Host $line -ForegroundColor Yellow
            $summary.Add($line)
        }
    }

    $summary.Add("")
    $summary.Add("Local fallbacks")
    foreach ($server in $servers) {
        $summary.Add(("{0,-24} http://127.0.0.1:{1}/mcp" -f $server.Name, $server.Port))
    }

    Set-Content -LiteralPath $linksFile -Value $summary -Encoding UTF8
    Write-Host ""
    Write-Host "Saved the same list here: $linksFile" -ForegroundColor Green
}
