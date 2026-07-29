import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { createServer } from "node:http";
import express from "express";
import { WebSocketServer } from "ws";
import { z } from "zod";
import { CoinbaseProductFeed, fetchCandleHistory, fetchCandles } from "./coinbase-feed.js";
import { config } from "./config.js";
import { runBacktest } from "./core/backtest.js";
import { calculateRisk } from "./core/risk.js";
import { PlanStore } from "./store.js";

const app = express();
app.use(express.json({ limit: "256kb" }));
app.use((_req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  res.setHeader("Access-Control-Allow-Methods", "GET,PUT,POST,OPTIONS");
  next();
});

const plans = new PlanStore();
await plans.load(config.products);
const feeds = new Map(config.products.map((product) => [product, new CoinbaseProductFeed(product, plans)]));

const zoneSchema = z.object({
  id: z.string().min(1),
  kind: z.enum(["POC", "VAH", "VAL", "DEMAND", "SUPPLY", "LIQUIDITY_HIGH", "LIQUIDITY_LOW"]),
  low: z.number().positive(),
  high: z.number().positive(),
  timeframe: z.enum(["W1", "D1", "H4", "H1", "M30", "M15", "M5"]),
  fresh: z.boolean(),
  source: z.enum(["LIVE", "PD", "EPD", "PW", "FIXED", "SWING", "LTF_SWING", "HTF_ZONE"]),
  taps: z.number().int().min(0).max(20),
  tookOutOpposingZone: z.boolean(),
  note: z.string().max(200).optional()
}).refine((zone) => zone.high >= zone.low, "Zone high must be greater than or equal to low");

const planSchema = z.object({
  productId: z.string().min(3),
  bias: z.enum(["bullish", "bearish", "neutral"]),
  structure: z.enum(["reclaim", "rejection", "breakout", "breakdown", "range"]),
  session: z.enum(["Asia", "London", "New York", "Off-hours"]),
  sessionPhase: z.enum(["normal", "pre-open", "late"]),
  newsRisk: z.enum(["clear", "caution", "red"]),
  volumeCondition: z.enum(["low", "normal", "high"]),
  marketPhase: z.enum(["contrarian", "momentum"]),
  auctionPattern: z.enum(["UNSET", "RANGE", "CERC", "CME"]),
  entryModel: z.enum(["AUTO", "EM1", "EM2", "EM3", "EM4"]),
  executionStage: z.enum(["waiting", "touched", "flipped", "confirmed"]),
  zones: z.array(zoneSchema).max(30),
  accountSize: z.number().positive(),
  riskPct: z.number().positive().max(1),
  preferredDirection: z.enum(["long", "short", "both", "none"])
});

app.get("/api/health", (_req, res) => {
  const states = [...feeds.values()].map((feed) => feed.getState());
  res.json({ ok: states.some((state) => ["live", "fallback"].includes(state.status)), executionEnabled: config.liveExecution, products: states.map((state) => ({ productId: state.productId, status: state.status, mode: state.mode })) });
});

app.get("/api/products", (_req, res) => res.json([...feeds.values()].map((feed) => feed.getState())));

app.get("/api/products/:productId", (req, res) => {
  const feed = feeds.get(req.params.productId);
  if (!feed) return res.status(404).json({ error: "Unknown product" });
  res.json(feed.getState());
});

app.get("/api/products/:productId/candles", async (req, res) => {
  try {
    if (!feeds.has(req.params.productId)) return res.status(404).json({ error: "Unknown product" });
    const granularity = Number(req.query.granularity ?? 300);
    if (![60, 300, 900, 3600, 21600, 86400].includes(granularity)) return res.status(400).json({ error: "Unsupported granularity" });
    res.json(await fetchCandles(req.params.productId, granularity));
  } catch (error) {
    res.status(502).json({ error: error instanceof Error ? error.message : "Candle request failed" });
  }
});

app.put("/api/products/:productId/plan", async (req, res) => {
  const parsed = planSchema.safeParse({ ...req.body, productId: req.params.productId });
  if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });
  if (!feeds.has(parsed.data.productId)) return res.status(404).json({ error: "Unknown product" });
  await plans.set(parsed.data);
  const state = feeds.get(parsed.data.productId)!.getState();
  broadcast({ type: "state", payload: state });
  res.json(state);
});

app.post("/api/risk", (req, res) => {
  try { res.json(calculateRisk(req.body)); }
  catch (error) { res.status(400).json({ error: error instanceof Error ? error.message : "Invalid risk input" }); }
});

const backtestSchema = z.object({
  strategyMode: z.enum(["lta", "h4-retest"]).optional().default("lta"),
  productId: z.string().min(3),
  granularity: z.union([z.literal(300), z.literal(900), z.literal(3600), z.literal(21600), z.literal(86400)]),
  bars: z.number().int().min(150).max(20000),
  direction: z.enum(["long", "short", "both"]),
  model: z.enum(["all", "EM1", "EM2", "EM3", "EM4"]),
  quality: z.enum(["A", "A+"]),
  lookback: z.number().int().min(20).max(120),
  targetR: z.number().min(1.5).max(5),
  riskPct: z.number().positive().max(10),
  accountSize: z.number().positive(),
  maxHoldBars: z.number().int().min(4).max(120),
  sessionFilter: z.enum(["ALL", "ASIA", "LONDON", "NY", "LONDON_NY", "NY_EXT"]).optional().default("ALL"),
  trendFilter: z.enum(["raw", "trend", "strict"]).optional().default("raw")
});

app.post("/api/backtest", async (req, res) => {
  const parsed = backtestSchema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: parsed.error.flatten() });
  if (!feeds.has(parsed.data.productId)) return res.status(404).json({ error: "Unknown product" });
  try {
    const candles = await fetchCandleHistory(parsed.data.productId, parsed.data.granularity, parsed.data.bars);
    res.json(runBacktest(candles, parsed.data));
  } catch (error) {
    res.status(502).json({ error: error instanceof Error ? error.message : "Backtest failed" });
  }
});

app.get("/api/settings", (_req, res) => res.json({
  products: config.products,
  publicDataNeedsKeys: false,
  executionEnabled: config.liveExecution,
  integrations: config.integrations,
  safety: {
    mode: config.liveExecution ? "live" : "analysis/paper",
    maxRiskPct: config.maxRiskPct,
    spotShortingEnabled: false
  }
}));

app.post("/api/orders", (_req, res) => {
  res.status(403).json({ error: "Live execution is intentionally disabled. Configure credentials and explicitly enable it after paper verification." });
});

const dist = resolve(process.cwd(), "web", "dist");
if (existsSync(dist)) {
  app.use(express.static(dist));
  app.get("*path", (_req, res) => res.sendFile(resolve(dist, "index.html")));
}

const server = createServer(app);
const wss = new WebSocketServer({ server, path: "/stream" });

function broadcast(message: unknown) {
  const data = JSON.stringify(message);
  for (const client of wss.clients) if (client.readyState === client.OPEN) client.send(data);
}

wss.on("connection", (socket) => {
  socket.send(JSON.stringify({ type: "snapshot", payload: [...feeds.values()].map((feed) => feed.getState()) }));
});

for (const feed of feeds.values()) {
  feed.on("state", (state) => broadcast({ type: "state", payload: state }));
  feed.start();
}

server.listen(config.port, () => {
  console.log(`HamaForex API listening on http://localhost:${config.port}`);
  console.log(`Mode: ${config.liveExecution ? "LIVE EXECUTION" : "analysis/paper"}`);
});

const shutdown = () => {
  for (const feed of feeds.values()) feed.stop();
  wss.close();
  server.close(() => process.exit(0));
};
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
