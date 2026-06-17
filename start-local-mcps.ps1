param(
    [switch]$DryRun,
    [switch]$PublicTunnel,
    [string]$ApiKey = $env:MCP_PROXY_API_KEY
)

$ErrorActionPreference = "Stop"

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

function Test-CommandAvailable {
    param([string]$CommandName)
    return [bool](Get-Command $CommandName -ErrorAction SilentlyContinue)
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

Write-Host ""
Write-Host "Local MCP launch list" -ForegroundColor Cyan
Write-Host "====================="
Write-Host ""

if (-not (Test-CommandAvailable "npx.cmd")) {
    throw "npx.cmd was not found. Install Node.js first, then run this again."
}

foreach ($requiredCommand in @("uv", "uvx")) {
    if (-not (Test-CommandAvailable $requiredCommand)) {
        Write-Host "Warning: $requiredCommand was not found. Some MCPs may fail to start." -ForegroundColor Yellow
    }
}

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
