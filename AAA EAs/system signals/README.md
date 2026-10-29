# MT5 → Telegram signal forwarder (2026-10-29)

Watches **one MT5 terminal you choose** and posts every trading event of its logged-in account to your Telegram channel.

It is **read-only**:
- it never opens, changes or closes a trade;
- it never starts MT5: the terminal must already be running and logged in;
- it never changes MT5 settings or AutoTrading.

## Two ways to post
| | **User mode (QR login, default)** | Bot mode |
|---|---|---|
| Posts as | your own Telegram account (in a channel, posts show as the channel) | a @BotFather bot |
| Login | scan a QR code with the Telegram app once | bot token in `.env` |
| You need | `TELEGRAM_API_ID` + `TELEGRAM_API_HASH` from **https://my.telegram.org → API development tools** (free, any app name). Telegram requires these for any user-account login; there is no way round it | `TELEGRAM_BOT_TOKEN` from **@BotFather**; add the bot to the channel as **Administrator** |
| Channel | pick it from a list after login, or set `TELEGRAM_CHAT_ID` | `TELEGRAM_CHAT_ID` |
| Alerts (connection lost, errors) | your **Saved Messages** | console, or `TELEGRAM_ADMIN_CHAT_ID` |

**Channel id:** Telegram Web shows it in the address bar. For example, `https://web.telegram.org/a/#-1003961182008` means `TELEGRAM_CHAT_ID=-1003961182008`.

**User-mode security:** the login is saved in `state/telegram-user.session`.
- That file is **full access to your Telegram account**. Never share it or copy it to other PCs.
- To log out, run `"Start Signals.bat" --logout`, or end the "Calyx Signals" device in **Telegram → Settings → Devices**.
- The forwarder only sends messages to the chat you pick.
- Telegram can limit accounts that send automated messages too fast. The forwarder waits whenever Telegram asks it to.

**Also needed:**
- **Python 3** with `MetaTrader5`, `telethon` and `qrcode[pil]`. All are already on this PC. Elsewhere: `python -m pip install MetaTrader5 telethon qrcode[pil]`.
- **The MT5 terminal** running and logged in. The investor (read-only) password is enough.
- No MT5 API key: the MetaTrader5 package talks to the running terminal on the same PC.

## Start (user mode, the default; set `TELEGRAM_MODE=bot` to use a bot token instead)
1. **API id / hash:** if `.env` has none, the forwarder handles it.
   - It offers to reuse the ones in your **`AAA telegram signals`** project (it asks first and never prints them).
   - Otherwise it asks you to paste them.
   - Either way, it saves them to `.env`.
   - It does **not** reuse that project's login session: two programs on one session can get the login revoked.
2. Double-click **`Login Telegram (QR).bat`**, or just **`Start Signals.bat`**, which logs in first when needed. A QR code appears in the window and as an image.
   - About every 2 minutes without a scan, it offers **phone number + code** login instead.
   - On your phone, open Telegram → **Settings → Devices → Link Desktop Device** and scan it.
   - If you use two-step verification, type that password in the window.
   - Choose the channel from the list. The list shows channels where you can post, plus Saved Messages for a private test.
   - You only do this once.
3. Open the MT5 terminal you want to watch and log in.
3. Double-click **`Start Signals.bat`**.
   - It lists every MT5 terminal on the PC as `[RUNNING]` or `[not running]`.
   - Type the number of the terminal to watch.
   - It refuses a terminal that is not running.
4. Leave the window open. Ctrl+C stops it.

**Useful options:**
- `"Start Signals.bat" --test-telegram` sends one test message to check the token and channel.
- `"Start Signals.bat" --dry-run` prints the messages in the window instead of sending them.
- `"Start Signals.bat" --list` shows the terminals only.
- `"Start Signals.bat" --terminal 3` skips the question.

**Several accounts:** run one window per terminal. A lock file stops two forwarders from posting for the same account.

## Messages
Messages use Telegram formatting: bold values, emojis, and a header that names the asset (GOLD, NASDAQ, DOW JONES, BITCOIN…).
```
🚨🔥 NASDAQ ALERT 🔥🚨

🟢 US100 BUY
🤖 Bot: nasdaq 5m

📍 Entry: 25100.00
🎯 TP: 25300.00
🛑 SL: 25000.00

⚠️ Risk management is required: use the minimum available lot size or risk max 5% per trade.
```
The risk note replaces the lot size. Change the text with `SIGNALS_RISK_NOTE`, or leave it empty to turn it off.

Updates and closes are **replies** to the original signal:
- **Update:** `✏️ TRADE UPDATE` with `🛑 SL moved → 25100.00`, plus `🔒 risk-free` when the stop reaches entry.
- **Partial close:** `💰 PARTIAL CLOSE` with `📤 Exit`, `✂️ Closed: 50% of the position` and `📊 Result: +1.00R (+100.00)`.
- **Close:** the headline depends on the result:
  - `✅ TAKE PROFIT HIT`;
  - `🛑 STOP LOSS HIT`;
  - `🔒 STOPPED IN PROFIT` (a trailing stop);
  - `⚪ CLOSED AT BREAKEVEN`;
  - `✅ CLOSED IN PROFIT` / `❌ CLOSED AT A LOSS`;
  - `⛔ STOP OUT`.

  Then `📤 Exit`, `📊 Result` in R and price, an optional `💵 Profit`, and `ℹ️` with the reason.
- **Pending orders:**
  - `⏳ PENDING ORDER` with entry, TP, SL, expiry and the risk note;
  - `✏️ ORDER UPDATE` when it changes;
  - `⚡ SELL LIMIT FILLED`, followed by the full signal;
  - `🚫 ORDER CANCELLED`, `EXPIRED` or `REJECTED`.
- **Positions without a TP** show `🎯 TP: open (the bot manages the exit)`.

## Bot names
`bots.json` maps each magic number to a name (48 entries):
- the catalog EAs;
- the client Top 5 magics;
- `0` = manual.

The `short` name is what the message shows; edit it freely. To rebuild after new EAs, run `python build_bots.py`; it keeps your short names. If a magic number is unknown, the message shows the order comment, or `magic <number>`. Symbols are cleaned up: `USTEC` / `NAS100` → `US100`, and suffixes like `XAUUSDm` or `EURUSD.raw` are removed. Add more names with `SIGNALS_SYMBOL_ALIASES`.

## Privacy defaults (change them in `.env`)
- **Lot sizes:** never posted; the risk note (`SIGNALS_RISK_NOTE`) replaces them.
- **Money results:** hidden (`SIGNALS_SHOW_PROFIT=false`), because they reveal the account size.
- **Deposits and withdrawals:** not posted (`SIGNALS_SHOW_ACCOUNT_EVENTS=false`).
- **Account number:** never posted. Alerts show only the last 4 digits.
- **Choosing bots:** use `SIGNALS_ONLY_MAGICS` or `SIGNALS_IGNORE_MAGICS` to pick which bots appear. Manual trades (magic 0) are included unless ignored.

## Reliability
- **Polling:** every second (`SIGNALS_POLL_SECONDS`). Each event is detected from the account's deal history and the open positions / orders, so nothing depends on the EA.
- **First start:** silent. Positions that are already open are recorded but not posted, unless `SIGNALS_ANNOUNCE_OPEN_ON_START=true`.
- **Restart:** state is saved in `state/<server>-<login>.json`. Events that happened while the forwarder was off are posted once, marked **(delayed)**. Events older than `SIGNALS_CATCHUP_HOURS` (24) are logged, not posted. Nothing is posted twice.
- **Telegram down:** messages wait in an outbox and are sent later. Telegram rate limits (429) are respected.
- **Log:** every event is also written to `logs/events-YYYY-MM-DD.jsonl`.
- **MT5 disconnects:** an alert goes to the admin chat. If the terminal closes, the forwarder waits for you to start it again; it never launches it.

## Limits
- **Delay:** signals arrive about 1–2 s after the fill (polling plus Telegram), so followers get a worse price than the account.
- **Windows only:** the PC (or VPS) running the terminal must also run this window. Closing it stops the signals.
- **Telegram limits:** about 20 messages a minute per channel. Bursts are queued, not dropped.
- **Netting accounts:** scale-ins are not posted separately; the forwarder is built for hedging accounts.
- **Testing done:** 6 scenario tests against a simulated MT5 (`python -m pytest tests -q`):
  - a full trade lifecycle;
  - pending fill and cancel, including history lag;
  - restart catch-up without duplicates;
  - open and close between two polls;
  - filters and privacy;
  - connection alerts.
- **Not yet tested:** a run on a live terminal with a real Telegram channel. Run `--dry-run` first.
