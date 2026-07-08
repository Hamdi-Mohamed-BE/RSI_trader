# Environment and keys

Public Coinbase market data works immediately without keys.

Copy `.env.example` to `.env`. Do not paste secrets into source files or the browser.

## Keys to prepare later

Required only for authenticated Coinbase spot execution:

- `COINBASE_API_KEY`
- `COINBASE_API_SECRET`
- `COINBASE_API_PASSPHRASE`

Optional integrations:

- `OPENAI_API_KEY` — narrative review/agent layer
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` — alerts
- `MT5_BRIDGE_URL` and `MT5_BRIDGE_TOKEN` — gold/forex/indices bridge

Keep `ENABLE_LIVE_EXECUTION=false` until paper testing, order validation, exchange permission review and explicit user approval are complete.
