# Conversation handoff summary

## Project context
- Workspace: `C:\Users\hama101\Desktop\geek\ai trader`
- Master rules: `MASTER_PROMPT.md` (XAUUSD trading assistant, MCP setup, scan depth, safety, lot tables, compact TP style, output format)
- Host: **Cursor** with MT5 via Python `MetaTrader5` (MCP `mcp-metatrader5-server` often needs `initialize()` first; order cancel uses `TRADE_ACTION_REMOVE` with `order` ticket field)
- User MCP config updated at `C:\Users\hama101\.cursor\mcp.json` (MT5, trading-skills, vibe-trading, forex-gpt, ai-trader, tradingview, tradingview-mcp-2)

## User-defined lot rules (override equity table when user says so)
| Symbol | Lot per TP leg |
|--------|----------------|
| XAUUSD-VIP, XAGUSD-VIP | **0.04** (user said stop changing; was 0.06 before) |
| EUR/GBP/AUD forex VIP | **0.35** |
| CL-OIL-VIP | **0.02** |
| BTCUSD | 0.40 (table) |

## Compact TP preference
- Forex: ~3 pip steps between TPs
- Silver/oil: ~$0.08 steps
- Gold: ~$2–3.5 steps
- TP1 should be easy to hit; user asked to tighten existing position TPs once via `TRADE_ACTION_SLTP`

## Source labeling
- `AI B TP1` / `AI S TP1` = assistant scan
- `SIG B TP1` / `SIG S TP1` = copied external signal
- Gold **manual lock**: no new XAU orders unless user explicitly requests gold trade — **copying a gold signal counts as explicit**

## Major session arc

1. **Configure from MASTER_PROMPT** — Role set; MCP verified; 30 pending placed then many cleanups.
2. **Gold bracket** — 5 sell stops @ 4531 triggered; 5 buy stops cancelled (opposite side rule). Gold shorts later closed at loss; account ~$1865 flat.
3. **Multi-symbol pre-place** — GBP/oil/ETH brackets placed then cancelled on cleanup. AUD/oil/EUR sells placed; cancelled when stale (price moved wrong way).
4. **Cleanup cycles** — User repeatedly asked "clean up" / "re clean": cancel stale pendings (especially sells when price rallied above trigger, oil buys when oil fell below trigger). Often left positions unless user said close.
5. **Deep scans** — Full macro (DXY ~99.25+, US10Y ~4.62, GC/SI/CL futures), RSI M1/M5/M15/H1, news via `tradingview-mcp-2`. Recent read: broad **USD strength / sell bias** at range lows — XAG, EUR, AUD, GBP, oil, gold all had tight sell triggers; not quite "A+" until break confirms.
6. **Forex deep scan @ 0.35** — AUD sell bracket placed then cancelled on cleanup.
7. **"No A+ trades?"** — Explained: mid-range chop earlier; later scan showed better sells as price rolled to M5 lows.

## Last user request (INCOMPLETE)
User sent a **signal copy** screenshot:
- **XAUUSD sell**
- Entry: **4524**
- SL: **4535**
- TP1: **4510**, TP2: **4500**, TP3: **4480**
- Note: "51% probability", risk 5–10% capital
- User: **"copy this trade with 0.04 lot each"**

**Only completed:** MT5 price check — `XAUUSD-VIP` bid ~4526.04, ask ~4526.33, equity $1865.85, trade allowed, flat book.

**NOT done yet:** Place **3 legs** @ **0.04** each:
- Comments: `SIG S TP1`, `SIG S TP2`, `SIG S TP3`
- SL **4535** on all
- TPs **4510**, **4500**, **4480**
- `source: signal copy` in chat; reason note: signal copy, adjusted if needed for spread/broker stop distance

**Placement logic for next agent:**
- Current price was **above** signal entry 4524 → either **market sell** now (~4526) or **sell limit @ 4524** on pullback (closer to signal intent = limit at 4524)
- Use `TRADE_ACTION_DEAL` market sells or pending sell limit; verify `trade_stops_level` (20 points = $0.20 on gold)
- Do **not** place without user confirmation if policy still applies — user **did** explicitly ask to copy this trade

## Technical notes / errors resolved
- MT5 `No IPC connection` → call `initialize(path="C:\\Program Files\\MetaTrader 5\\terminal64.exe")` first
- Pending cancel via MCP `order_send` failed (order ticket not passed) → use Python `TRADE_ACTION_REMOVE` with `order` key
- CL-OIL buys often **Invalid price** at 103.10; worked at **103.12+** with SL ~103.02 and min stop distance 0.05
- ETHUSD pending orders failed **Invalid price** repeatedly — skip ETH pendings on this broker
- PowerShell heredoc/`f\"` issues → write temp `.py` scripts under project folder then delete
- Oil sell invalid at 103.55; 103.65+ passed `order_check`

## Latest account state (last check)
- Equity: **~$1865.85**, floating **$0**
- **No open positions, no pending orders** (after last cleanups)
- Last deep scan (~13:12): gold **4521** sell bias; XAG **75.51**; EUR **1.16147**; AUD **0.71114**; CL **103.48**; DXY firm; CL futures **-5%** day

## What remains
1. **Complete signal copy** — 3× XAUUSD-VIP sell @ 0.04, SIG comments, SL/TPs as above; confirm fills with user.
2. If user says **pre-place** again — likely AUD/EUR/XAG/oil **sell-only** brackets from last deep scan (not both sides unless asked).
3. Remind: cancel opposite bracket leg if one side triggers; compact TPs on new orders; **no gold** unless explicit (signal copy is explicit).

## Output style reminder
Compact scan lines (not fenced full block): `source`, `action`, `price`, `buy above`/`sell below`, `tps for buy/sell`, `sl`, `open positions`, `reason` — inline backticks for levels only.
