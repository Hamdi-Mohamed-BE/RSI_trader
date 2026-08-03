# MT5 and TradingView MCP Agent Setup Guide

Last verified: 2 August 2026

The safest setup is:

- **MT5 MCP:** access the locally running MetaTrader 5 terminal.
- **TradingView Data MCP:** research, indicators, screening, and backtesting.
- Keep MT5 **read-only and demo-only initially**.
- Require explicit confirmation before any order.

These are community MCP projects, not official MetaQuotes, TradingView, or OpenAI integrations.

## Copy-paste prompt for the other agent

```text
Configure this Windows computer with MetaTrader 5 and TradingView MCP access.

Environment:
- MCP client: Codex or another MCP-compatible agent
- Primary market: US100/NAS100/NQ
- MT5 terminal path: C:\Program Files\MetaTrader 5\terminal64.exe
- Account mode: DEMO ONLY
- Risk per trade: maximum 0.25% of current equity
- Maximum daily loss: 0.75% of starting daily equity
- Maximum simultaneous positions: 1

Installation requirements:

1. Check whether Git, uv/uvx, Python 3.13, Node.js 18+, MetaTrader 5, and TradingView Desktop are installed.
2. Ask before installing missing system-wide software.
3. Install these pinned MCP servers:
   - MT5: mcp-metatrader5-server==0.1.8
   - TradingView market-data server: tradingview-mcp-server==0.8.0
4. Configure them as local STDIO MCP servers in this client.
5. Set the MT5 server to prompt for every tool call and disable `login` and `order_send` initially.
6. Restart or refresh the MCP client and verify both servers.
7. Do not place, modify, or cancel any order during installation or testing.

MT5 operating rules:

- Call `initialize` with the exact terminal64.exe path before any other MT5 tool.
- Use the account already logged into the terminal. Never request, print, log, or store my trading password.
- Call `get_account_info` and clearly identify whether the account is demo or live.
- If it is live, remain completely read-only.
- Discover the broker's actual Nasdaq symbol rather than assuming it is named US100.
- Read-only operations include prices, symbols, bars, ticks, positions, orders, account details, and history.
- Never call `order_send` unless it has been enabled separately, the account is confirmed as demo, and I approve the exact order in the current conversation.
- Before requesting confirmation, show symbol, direction, order type, volume, entry, stop loss, take profit, spread, cash risk, equity percentage risk, estimated margin, expiration, and worst reasonable slippage.
- Run `order_check` before any approved demo order.
- After submission, inspect the returned retcode and verify the position or pending-order ticket. Never assume a successful function call means the trade was filled.
- No martingale, grid recovery, averaging down, removing stop losses, or increasing risk after losses.

TradingView rules:

- Use TradingView data tools for research, technical indicators, screening, and backtesting.
- Do not claim that the data MCP controls my logged-in TradingView account.
- If the optional TradingView Desktop bridge is installed, use it only for chart reading, Pine Script, screenshots, drawings, replay, and human-supervised chart actions.
- Do not use undocumented TradingView access for automated trading, bulk extraction, redistribution, or anything that may violate TradingView's terms.
- Never create or delete alerts, drawings, layouts, or Pine scripts without confirmation.

Research rules:

- Broker MT5 data is the source of truth for executable symbol names, spreads, contract sizes, stops levels, and fills.
- Always identify timezone and bar-close status.
- Separate development, validation, and unseen test periods.
- Include commissions, spread, slippage, swaps, and rollover costs.
- Report profit factor, win rate, maximum drawdown, trade count, expectancy, profitable-day percentage, and uncertainty.
- Never promise daily profits or guaranteed returns.

Verification test:

1. List both MCP servers and their available tools.
2. Initialize MT5.
3. Display sanitized account information without login number, name, or credentials.
4. Confirm demo versus live.
5. Discover possible US100/NAS100 symbols.
6. Retrieve the latest tick and 100 completed M5 bars without trading.
7. Run a harmless TradingView market-data query for Nasdaq.
8. Report what works, what failed, and the exact configuration location.
9. Stop without placing any order.
```

## Windows installation guide

### 1. Install prerequisites

Install MetaTrader 5 from the [official MetaTrader website](https://www.metatrader5.com/en/download). Log into a **demo account** and leave the terminal running.

Install `uv`, which manages isolated Python environments:

```powershell
winget install --id=astral-sh.uv -e
uv python install 3.13
uv --version
uvx --version
```

The installer and alternative methods are documented by [Astral](https://docs.astral.sh/uv/getting-started/installation/).

For the optional TradingView Desktop controller, also install:

- [Git for Windows](https://git-scm.com/download/win)
- [Node.js LTS](https://nodejs.org/en/download)
- [TradingView Desktop](https://www.tradingview.com/desktop/)

Close and reopen PowerShell after installation.

### 2. Add the MT5 MCP to Codex

The recommended community repository is [Qoyyuum/mcp-metatrader5-server](https://github.com/Qoyyuum/mcp-metatrader5-server). It supports prices, bars, ticks, account information, history, positions, and orders. Version `0.1.8` is published on [PyPI](https://pypi.org/project/mcp-metatrader5-server/).

Run:

```powershell
codex mcp add mt5 -- uvx --python 3.13 --from mcp-metatrader5-server==0.1.8 mt5mcp
```

Verify registration:

```powershell
codex mcp list
codex mcp get mt5 --json
```

Codex stores MCP configuration in `%USERPROFILE%\.codex\config.toml`, shared by the desktop app, CLI, and IDE extension. See the [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp).

### 3. Lock MT5 to read-only

Open:

```text
C:\Users\YOUR_USERNAME\.codex\config.toml
```

The entry should resemble:

```toml
[mcp_servers.mt5]
command = "uvx"
args = [
  "--python",
  "3.13",
  "--from",
  "mcp-metatrader5-server==0.1.8",
  "mt5mcp"
]
enabled = true
startup_timeout_sec = 60
tool_timeout_sec = 120
default_tools_approval_mode = "prompt"
disabled_tools = ["login", "order_send"]
```

This prevents account switching and trade submission at the MCP layer.

In MT5, also open:

```text
Tools → Options → Expert Advisors
```

Keep **Disable automated trading via external Python API** enabled during research. MetaQuotes documents that the Python integration can retrieve market data and send trading requests; disabling external Python trading provides an additional terminal-level barrier. See the [official Python integration documentation](https://www.mql5.com/en/docs/python_metatrader5).

Do not put the MT5 password in:

- The agent prompt
- `config.toml`
- Command-line arguments
- Screenshots
- Chat messages

Use the account already logged into the terminal.

### 4. Add the recommended TradingView data MCP

This version does not log into or control your TradingView account. It provides research, indicators, screeners, and backtesting through public and third-party data.

Repository: [atilaahmettaner/tradingview-mcp](https://github.com/atilaahmettaner/tradingview-mcp)

Install version `0.8.0`:

```powershell
codex mcp add tradingview-data -- uvx --python 3.13 --from tradingview-mcp-server==0.8.0 tradingview-mcp
```

Its Codex configuration should resemble:

```toml
[mcp_servers.tradingview-data]
command = "uvx"
args = [
  "--python",
  "3.13",
  "--from",
  "tradingview-mcp-server==0.8.0",
  "tradingview-mcp"
]
enabled = true
startup_timeout_sec = 60
tool_timeout_sec = 120
default_tools_approval_mode = "auto"
```

This is the recommended TradingView option for automated research because it does not touch your TradingView session.

### 5. Optional: control TradingView Desktop

Only install this if you need the agent to inspect charts, compile Pine Script, take screenshots, manage drawings, or operate replay mode.

Repository: [tradesdontlie/tradingview-mcp](https://github.com/tradesdontlie/tradingview-mcp)

The repository states that it:

- Uses undocumented TradingView Desktop interfaces
- May break after TradingView updates
- Does not execute real trades
- May conflict with TradingView's terms if used for automated collection or algorithmic decisions

Install:

```powershell
New-Item -ItemType Directory -Path C:\MCP -Force
Set-Location C:\MCP
git clone https://github.com/tradesdontlie/tradingview-mcp.git
Set-Location C:\MCP\tradingview-mcp
npm install
```

Save any open TradingView work, then launch it with the debugging connection:

```powershell
C:\MCP\tradingview-mcp\scripts\launch_tv_debug.bat
```

Register the server:

```powershell
codex mcp add tradingview-desktop -- node C:\MCP\tradingview-mcp\src\server.js
```

Verify it later by asking the agent:

```text
Use tv_health_check. Do not modify my chart.
```

Port `9222` exposes control of the local TradingView application. Do not expose it through your router, VPN tunnel, port forwarding, or public firewall rules.

### 6. Restart and verify

Completely restart Codex, then open a new task and run:

```text
List the connected MT5 and TradingView MCP tools. Do not perform any write action.
```

Then:

```text
Initialize MT5 using:
C:\Program Files\MetaTrader 5\terminal64.exe

Show sanitized account information, confirm demo or live, discover all symbols containing NAS, USTEC, US100, NDX, or TECH, and retrieve the latest tick plus 100 completed M5 bars. Do not place an order.
```

For TradingView data:

```text
Use the TradingView data MCP to find the available Nasdaq-100, NQ, and QQQ symbols. Retrieve a technical summary without making any account or chart changes.
```

For the optional desktop bridge:

```text
Run tv_health_check and chart_get_state. Do not change the symbol, timeframe, indicators, drawings, alerts, or scripts.
```

### 7. Enabling demo orders later

Only after read-only verification:

1. Confirm MT5 is logged into a demo account.
2. Remove `order_send` from `disabled_tools`.
3. Keep `default_tools_approval_mode = "prompt"`.
4. In MT5, disable the external-Python trading protection only on that demo terminal.
5. Restart Codex.
6. Test `order_check` first.
7. Use the broker's minimum volume.

Never enable `order_send` on a live account until the complete system has passed broker-data backtesting and extended forward testing. MetaQuotes notes that a successful order request does not automatically prove that the trade was filled; returned execution codes must be checked. See the [official OrderSend documentation](https://www.mql5.com/en/docs/trading/ordersend).

## Generic MCP configuration

For another agent that expects JSON instead of Codex TOML:

```json
{
  "mcpServers": {
    "mt5": {
      "command": "uvx",
      "args": [
        "--python",
        "3.13",
        "--from",
        "mcp-metatrader5-server==0.1.8",
        "mt5mcp"
      ]
    },
    "tradingview-data": {
      "command": "uvx",
      "args": [
        "--python",
        "3.13",
        "--from",
        "tradingview-mcp-server==0.8.0",
        "tradingview-mcp"
      ]
    }
  }
}
```

The exact JSON file location depends on the client. Codex uses `config.toml`, not this JSON format.

## Troubleshooting

### `uvx` is not recognized

Restart PowerShell after installing `uv`. If it still fails, try the full path:

```text
C:\Users\YOUR_USERNAME\.local\bin\uvx.exe
```

Use that path as the MCP server's `command`.

### MT5 reports `No IPC connection`

1. Confirm MT5 is installed and running.
2. Call `initialize` first.
3. Supply the full path to the correct broker terminal's `terminal64.exe`.
4. Confirm Codex and MT5 are running under the same Windows user.

### The US100 symbol is not found

Broker names vary. Search for names containing:

```text
NAS
NASDAQ
US100
USTEC
NDX
TECH
```

Then inspect each candidate with `get_symbol_info` and confirm contract size, tick size, spread, minimum volume, and trading mode.

### The MCP server times out on first launch

The first `uvx` run may need to download Python packages. Run each server once from PowerShell to warm its cache:

```powershell
uvx --python 3.13 --from mcp-metatrader5-server==0.1.8 mt5mcp
```

Stop it with `Ctrl+C`, then run:

```powershell
uvx --python 3.13 --from tradingview-mcp-server==0.8.0 tradingview-mcp
```

Stop it with `Ctrl+C`, restart Codex, and retry.

### TradingView Desktop health check fails

1. Exit all TradingView Desktop processes.
2. Run `C:\MCP\tradingview-mcp\scripts\launch_tv_debug.bat`.
3. Confirm TradingView opens and is logged in.
4. Verify nothing else is using local port `9222`.
5. Restart the MCP client and run `tv_health_check` again.

## Source links

- [Codex MCP documentation](https://learn.chatgpt.com/docs/extend/mcp)
- [MT5 MCP repository](https://github.com/Qoyyuum/mcp-metatrader5-server)
- [MT5 MCP package](https://pypi.org/project/mcp-metatrader5-server/)
- [Official MetaTrader 5 Python integration](https://www.mql5.com/en/docs/python_metatrader5)
- [Official MetaTrader 5 download](https://www.metatrader5.com/en/download)
- [TradingView data MCP repository](https://github.com/atilaahmettaner/tradingview-mcp)
- [TradingView data MCP package](https://pypi.org/project/tradingview-mcp-server/)
- [TradingView Desktop bridge repository](https://github.com/tradesdontlie/tradingview-mcp)
- [Official TradingView Desktop download](https://www.tradingview.com/desktop/)
- [Official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/)
