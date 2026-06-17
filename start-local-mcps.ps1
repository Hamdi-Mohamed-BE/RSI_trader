param(
    [switch]$DryRun,
    [switch]$PublicTunnel,
    [string]$ApiKey = $env:MCP_PROXY_API_KEY
)

$ErrorActionPreference = "Stop"

$ScriptRoot = Split-Path -Parent $PSCommandPath
$RuntimeRoot = Join-Path $ScriptRoot ".mcp-runtime"

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

$servers = @(
    @{
        Name = "mcp-metatrader5-server"
        Port = 8821
        Command = @("uvx", "--from", "git+https://github.com/Qoyyuum/mcp-metatrader5-server", "mt5mcp")
        Env = @{}
    },
    @{
        Name = "trading-skills"
        Port = 8822
        Command = @("uvx", "--from", "git+https://github.com/staskh/trading_skills.git", "trading-skills-mcp")
        Env = @{}
    },
    @{
        Name = "vibe-trading"
        Port = 8823
        Command = @("uvx", "--from", "C:/Users/hama101/Desktop/geek/vibe trader/Vibe-Trading", "vibe-trading-mcp")
        Env = @{}
    },
    @{
        Name = "ai-trader"
        Port = 8824
        Command = @("uv", "run", "--directory", "C:/Users/hama101/Documents/Codex/2026-05-13/hey/ai-trader", "python", "-m", "ai_trader.mcp")
        Env = @{}
    },
    @{
        Name = "tradingview"
        Port = 8825
        Command = @("npx.cmd", "-y", "tradingview-mcp-server")
        Env = @{}
    },
    @{
        Name = "tradingview-mcp-2"
        Port = 8826
        Command = @("uvx", "--from", "tradingview-mcp-server", "tradingview-mcp")
        Env = @{}
    },
    @{
        Name = "mcp-order-flow-server"
        Port = 8827
        Command = @("uv", "run", "--directory", "C:/Users/hama101/.codex/mcp/mcp-order-flow-server", "python", "src/mcp_server.py")
        Env = @{
            DATA_SOURCE = "grpc"
            DATA_BROKER_GRPC_URL = "localhost:9090"
            LOG_LEVEL = "INFO"
        }
    }
)

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

Write-Host ""
Write-Host "Copy/paste the /mcp URLs above into Notion if Notion accepts local HTTP URLs." -ForegroundColor Green
Write-Host "If Notion rejects localhost or requires HTTPS, run: start-local-mcps.bat -PublicTunnel" -ForegroundColor Yellow
Write-Host "For public tunnel mode, set MCP_PROXY_API_KEY first and add that key in Notion auth." -ForegroundColor Yellow
Write-Host ""

if ($DryRun) {
    Write-Host "Dry run only. No MCP windows started." -ForegroundColor Cyan
    exit 0
}

foreach ($server in $servers) {
    $proxyArgs = @($mcpProxyArgsBase + @("--port", [string]$server.Port, "--") + $server.Command)
    $displayCommand = "npx.cmd " + (($proxyArgs | ForEach-Object { Format-Argument $_ }) -join " ")

    $envLines = @()
    foreach ($key in $server.Env.Keys) {
        $value = $server.Env[$key]
        $envLines += "`$env:$key = '$value'"
    }

    $childScriptLines = @()
    $childScriptLines += "Write-Host ''"
    $childScriptLines += "Write-Host 'Starting $($server.Name)' -ForegroundColor Cyan"
    $childScriptLines += "Write-Host 'Local MCP URL: http://127.0.0.1:$($server.Port)/mcp' -ForegroundColor Green"
    if ($PublicTunnel) {
        $childScriptLines += "Write-Host 'Public tunnel mode is enabled. Copy the HTTPS tunnel URL printed by mcp-proxy if Notion needs HTTPS.' -ForegroundColor Yellow"
    }
    $childScriptLines += $envLines
    $childScriptLines += $displayCommand

    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes(($childScriptLines -join "`r`n")))
    Start-Process -FilePath "cmd.exe" -ArgumentList @("/k", "powershell.exe -NoProfile -ExecutionPolicy Bypass -EncodedCommand $encoded") -WindowStyle Normal
}

Write-Host "Started $($servers.Count) MCP windows." -ForegroundColor Green
Write-Host "Keep those windows open while using the MCPs." -ForegroundColor Green
