# Calyx — Claude connectors, skills and machine setup

Snapshot 2026-09-23. **Documentation only: no connector was added, authenticated, launched or
health-tested by this handoff.** Do not expose credentials while checking configuration.

## 1. What is present versus usable

Observed executable paths:
- Claude: `C:\Users\hama101\.local\bin\claude.exe`
- uv: `C:\Users\hama101\.local\bin\uv.exe`
- Python: `C:\Program Files\Python313\python.exe`
- Git: `C:\Program Files\Git\cmd\git.exe`

Presence is not compatibility or login verification. Projects declare their own Python constraints
and lockfiles. Use project-managed environments, not whichever global python happens to resolve.

Existing Claude Desktop configuration:
`C:\Users\hama101\AppData\Roaming\Claude\claude_desktop_config.json`
contains names **metatrader**, **mcp-metatrader5-server**, **trading-skills**.
Only names were inspected/exported; their health, permissions and terminal binding were not checked.
Do not create a duplicate MT5 server before determining what both existing names point to.

`C:\Users\hama101\.claude.json` exists, but no top-level MCP server names were observed.
That does not rule out project-scoped configuration inside it.
No root `.claude` directory or `.mcp.json` existed before this handoff.
None has been created here.

Codex configuration has 14 server tables listed below, but this Codex session exposed trading
tool groups only for FXMacroData, TradingView and order-flow (plus node runtime).
The normal MT5 MCP was NOT callable in this session. A configured entry is not a working tool.
Claude must perform its own discovery; Codex-only app/web/image/runtime tools do not transfer.

## 2. Claude setup model

Use Desktop's **Code** tab with a **Local Windows** project, not a cloud container.
Native MetaTrader5 integration depends on local Windows and an actual terminal.
A WSL/cloud session can see different paths, runtimes and network loopback.

Claude's project instructions live in `CLAUDE.md`; project MCP configuration can live in
`.mcp.json`. Local/user entries can live in `~/.claude.json`.
Current Desktop docs also describe loading `claude_desktop_config.json` in local Code sessions;
the standalone CLI does not read that file directly. Avoid conflicting definitions under one name.
Check the installed version's behavior before migrating config.
[Official memory docs](https://code.claude.com/docs/en/memory)
[Official Desktop docs](https://code.claude.com/docs/en/desktop)

A prompt does not configure tools or grant access. Keep initial permissions Plan/Manual.
Do not use permission-bypass mode to make trading integration convenient.

## 3. Historical/current-configured server inventory

The table's roles and launch recipes come from the retained Calyx setup documentation.
Server names were verified in Codex config; recipe versions and services were NOT freshly tested.
Verify local paths, upstream versions, licensing, transport and credentials before setup.

| Server | Role | Documented recipe / endpoint | Migration notes |
|---|---|---|---|
| mcp-metatrader5-server | Normal MT5 account, specs, prices, orders/deals | `uvx --from git+https://github.com/Qoyyuum/mcp-metatrader5-server mt5mcp` | Existing Claude entry; inspect before adding; initialize exact intended terminal |
| ava-mt5-mcp | Separate Ava terminal | Same upstream MT5 package, separate binding | Do NOT connect normal and Ava through an assumed shared default terminal; Ava is out of normal scope |
| trading-skills | Supporting analytics | `uvx --from git+https://github.com/staskh/trading_skills.git trading-skills-mcp` | Existing Claude entry; not native MT5 truth |
| vibe-trading | Supporting local research | `uvx --from "C:/Users/hama101/Desktop/geek/vibe trader/Vibe-Trading" vibe-trading-mcp` | Verify repo exists before proposing |
| forex-gpt | Macro/sentiment context | `https://mcp.forex-gpt.ai/mcp` | Remote; verify auth and freshness |
| ai-trader | Custom local orchestration | `uv run --directory C:/Users/hama101/Documents/Codex/2026-05-13/hey/ai-trader python -m ai_trader.mcp` | Package may be absent; no invented tool access |
| tradingview | Chart/indicator inspection | `node C:/Users/hama101/.codex/mcp/tradingview-mcp-jackson/src/server.js` | Local browser/session dependency; verify transport and session |
| mcp-order-flow-server | Exchange order book/flow | `uv run --directory C:/Users/hama101/.codex/mcp/mcp-order-flow-server python src/mcp_server.py` | Centralized exchange flow is not XAU CFD centralized volume |
| openbb | Supporting market/macro data | `uvx --from openbb-mcp-server --with openbb openbb-mcp --transport stdio --tool-discovery --default-categories admin` | Provider credentials/subscriptions may be required |
| kinocut | Media/transcript support | `powershell -NoProfile -ExecutionPolicy Bypass -File C:/Users/hama101/.codex/mcp/kinocut-start.ps1` | Inspect script and dependencies before execution |
| node_repl | Codex runtime infrastructure | Codex-managed versioned runtime | Do not transplant; replace with Claude-supported execution tools |
| ninjatrader-demo | Separate futures/demo context | `https://mcp-demo.tradovateapi.com/mcp` | Not CFD/MT5 execution truth; do not assume it is live |
| quantconnect | Separate research platform | `http://localhost:3001/` | Requires its own running service/auth |
| fxmacrodata | Point-in-time official macro/calendar context | `https://mcp.fxmacrodata.com` | Free recent USD coverage is not full historical entitlement |

Additional historical launcher entry, not one of those 14 global tables:
`tradingview-mcp-2`: `uvx --from tradingview-mcp-server tradingview-mcp`.
Verify the installed package's actual capabilities; it is not interchangeable with the Jackson chart MCP.

Do not execute every recipe. Start with the capabilities needed for the next approved task.

## 4. How to add a missing server later

**These commands change Claude configuration. They are examples, not part of onboarding.**
Run from the intended project only after reviewing existing entries and receiving setup approval.

```powershell
claude mcp add --transport http --scope local fxmacrodata https://mcp.fxmacrodata.com
claude mcp add --transport stdio --scope local mcp-metatrader5-server -- uvx --from git+https://github.com/Qoyyuum/mcp-metatrader5-server mt5mcp
```

For another table entry, use the same HTTP form with its endpoint, or stdio form with the
documented executable/arguments. Confirm current `claude mcp add --help` first.
Do not paste passwords/API keys into shell history. Use a supported private authentication
mechanism; never commit real secrets in project config.

After authorized setup, `claude mcp list` and Claude's `/mcp` view can check status.
They may start/contact configured servers: do not treat them as purely offline file inspection.
Then verify one harmless relevant read, not an order-placement call.
[Official MCP instructions](https://code.claude.com/docs/en/mcp)

## 5. Local bridge launcher and network safety

Historical `start-local-mcps.bat` / `start-local-mcps.ps1` defines:
- 8821 normal MT5
- 8822 trading-skills
- 8823 vibe-trading
- 8824 ai-trader
- 8825 TradingView
- 8826 secondary TradingView
- 8827 order-flow

Use no launcher during onboarding. For an authorized setup, inspect its current implementation.
Its documented `-LocalOnly` mode avoids public tunnels; the ordinary mode can create tunnels.
Do not create public tunnels, export mcp-links.txt or copy tokenized URLs into prompts.
A port number is not a verified MCP transport/path. Check actual protocol and service ownership.

Separate application ports:
- 8080: Calyx EA Store
- 8799: Gold News V9 prediction service
- 3001: historical QuantConnect gateway

Do not kill unrelated processes or reuse busy ports without checking ownership.

## 6. Portable and nonportable skills

A skill is instructions/assets/scripts, not a tool server.
Read the selected SKILL.md completely before using it; inspect referenced dependencies.
The presence of a skill does not grant access to its expected APIs or make it Claude-compatible.

Directly useful local source packages:
| Skill | Location | Role |
|---|---|---|
| lpx-set-analyzer | `C:/Users/hama101/.codex/skills/lpx-set-analyzer/SKILL.md` | MT5 optimization XML/backtest validation |
| mt5-trading-journal | `C:/Users/hama101/.codex/skills/mt5-trading-journal/SKILL.md` | Account journal and calendar |
| regime | `C:/Users/hama101/.codex/skills/regime/SKILL.md` | Causal regime/Markov research |
| tokenmaxxer | `C:/Users/hama101/.codex/skills/tokenmaxxer/SKILL.md` | Explicit deep-work workflow; not automatic on every request |
| linkedin-marketing | `C:/Users/hama101/.codex/skills/linkedin-marketing/SKILL.md` | Content routing and approved publishing |

LinkedIn subskills in `linkedin-marketing/skills/<name>/SKILL.md`:
comment-drafter, content-planner, employee-advocacy, engager-analytics, hook-extractor, humanizer,
interviewer, post-writer, profile-optimizer, reply-handler, repurposer, thread-monitor;
each directory name is prefixed `linkedin-`.

Codex system skill source location: `C:/Users/hama101/.codex/skills/.system`.
Observed: imagegen, openai-docs, plugin-creator, review-agent, skill-creator, skill-installer.
Those may depend on Codex-only tools or policy. Do not import their instructions wholesale or
assert their tools exist in Claude. Use platform-appropriate documented equivalents.

Bundled skills were also available to the prior agent, via versioned plugin caches:
computer-use, visualize, documents, pdf, presentations, spreadsheets, excel-live-control,
plugin-management, sites-building/sites-hosting/sites-preview-troubleshooting, template-creator.
These are NOT all under the local skill root and were not copied/exported.
Cache roots:
- `C:/Users/hama101/.codex/plugins/cache/openai-bundled`
- `C:/Users/hama101/.codex/plugins/cache/openai-primary-runtime`
- `C:/Users/hama101/.codex/plugins/cache/openai-curated-remote`

Some older documentation lists deep-research and artifact-template packages. Treat those as
historical, not current exposed capabilities. Do not quote a stale “55 skills” count.

If asked to migrate skills: inspect licensing, scripts, required runtimes, environment variables
and tool assumptions; adapt only relevant packages to Claude's supported skill format after
approval. Do not bulk-copy every plugin cache or credential file.
[Claude skills reference](https://code.claude.com/docs/en/skills)

The inventory document records 36 discovered local SKILL.md paths, including duplicate
marketplace copies. That is not 36 unique active skills, nor proof every one was used.

## 7. Repositories and dependencies to preserve

| Purpose | Local reference | Upstream |
|---|---|---|
| Main Calyx repo | Current workspace | https://github.com/Hamdi-Mohamed-BE/RSI_trader.git |
| TradingView MCP | `.codex/mcp/tradingview-mcp-jackson` under user profile | https://github.com/LewisWJackson/tradingview-mcp-jackson |
| Order-flow MCP | `.codex/mcp/mcp-order-flow-server` under user profile | https://github.com/fintools-ai/mcp-order-flow-server |
| Vibe Trading | `Desktop/geek/vibe trader/Vibe-Trading` | https://github.com/HKUDS/Vibe-Trading |
| AI Trader | `Documents/Codex/2026-05-13/hey/ai-trader` | https://github.com/whchien/ai-trader |
| Statistical reading/reference | Research pipeline README | https://github.com/cybergeekgyan/Quant-Developers-Resources |
| Janus strategy reference | Janus research folder | https://github.com/karimkhemkapital/janus-anti-fragility-strategy |
| Crypto replay foundation | Saved plan only | https://github.com/nkaz001/hftbacktest |
| Crypto execution prototype | Saved plan only | https://github.com/hummingbot/hummingbot |
| Optional collector | Saved plan only | https://github.com/bmoscon/cryptofeed |

Except the main origin, these upstream identities are inherited documented references, not fresh
remote health checks or declarations that their code is currently installed.
Check actual origin, commit, dirty state and license before reuse; pin versions for evidence.
Do not auto-clone or pull repositories just because they appear here.

## 8. Required capability report for the first Claude session

Report these independently:
1. Can read/edit the local workspace? Initial task remains read-only.
2. Can use local Windows PowerShell, uv and the project Python environment?
3. Which configured connectors are actually exposed? Which require setup?
4. Can read normal MT5 safely, without changing terminal/account? Not needed merely to onboard.
5. Is native MT5 tester/compiler available for future authorized isolated tests?
6. Are macro history entitlements sufficient for the requested dates?
7. Can render/check local web pages without publishing them?
8. Can create user-visible plots/artifacts, rather than only printing an invisible file path?
9. Which skills are compatible, adapted, unavailable or platform-specific?

Do not repair missing capabilities or claim migration completed just from a connector name.
The correct outcome may be “repository context ready; MT5 connector needs verification.”
