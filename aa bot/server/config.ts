import "dotenv/config";

const list = (value: string | undefined, fallback: string[]) =>
  value?.split(",").map((item) => item.trim()).filter(Boolean) ?? fallback;

export const config = {
  port: Number(process.env.PORT ?? 8787),
  restUrl: process.env.COINBASE_REST_URL ?? "https://api.exchange.coinbase.com",
  wsUrl: process.env.COINBASE_WS_URL ?? "wss://ws-feed.exchange.coinbase.com",
  products: list(process.env.COINBASE_PRODUCTS, ["BTC-USD", "ETH-USD"]),
  primaryMode: process.env.COINBASE_PRIMARY_MODE === "level2" ? "level2" : "full",
  restTimeoutMs: Number(process.env.COINBASE_REST_TIMEOUT_MS ?? 15_000),
  liveExecution: process.env.ENABLE_LIVE_EXECUTION === "true",
  defaultAccountSize: Number(process.env.DEFAULT_ACCOUNT_SIZE ?? 50_000),
  maxRiskPct: Number(process.env.MAX_RISK_PCT ?? 0.5),
  coinbaseCredentials: {
    key: process.env.COINBASE_API_KEY ?? "",
    secret: process.env.COINBASE_API_SECRET ?? "",
    passphrase: process.env.COINBASE_API_PASSPHRASE ?? ""
  },
  integrations: {
    coinbase: Boolean(process.env.COINBASE_API_KEY && process.env.COINBASE_API_SECRET),
    openai: Boolean(process.env.OPENAI_API_KEY),
    telegram: Boolean(process.env.TELEGRAM_BOT_TOKEN && process.env.TELEGRAM_CHAT_ID),
    mt5: Boolean(process.env.MT5_BRIDGE_URL && process.env.MT5_BRIDGE_TOKEN)
  }
} as const;
