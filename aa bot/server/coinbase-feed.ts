import { EventEmitter } from "node:events";
import { createHmac } from "node:crypto";
import WebSocket from "ws";
import { config } from "./config.js";
import { MboBook } from "./core/mbo-book.js";
import { MicrostructureEngine } from "./core/microstructure.js";
import { rankSetup } from "./core/strategy.js";
import { RollingVolumeProfile } from "./core/volume-profile.js";
import { PlanStore } from "./store.js";
import type { CoinbaseFullEvent, ProductState } from "./types.js";

const FULL_TYPES = new Set(["received", "open", "done", "match", "change", "activate"]);

export class CoinbaseProductFeed extends EventEmitter {
  readonly book = new MboBook();
  readonly micro = new MicrostructureEngine();
  readonly profile = new RollingVolumeProfile();
  private ws: WebSocket | null = null;
  private status: ProductState["status"] = "connecting";
  private mode: "full" | "level2";
  private lastMessageAt: number | null = null;
  private reconnects = 0;
  private sequenceGaps = 0;
  private consecutiveFailures = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private watchdog: NodeJS.Timeout | null = null;
  private queued: CoinbaseFullEvent[] = [];
  private syncing = false;
  private stopped = false;
  private emitTimer: NodeJS.Timeout | null = null;
  private ticker = { price: null as number | null, bid: null as number | null, ask: null as number | null };

  constructor(readonly productId: string, private readonly plans: PlanStore) {
    super();
    this.mode = config.primaryMode;
  }

  start() {
    this.stopped = false;
    this.connect();
    this.watchdog = setInterval(() => {
      if (this.lastMessageAt && Date.now() - this.lastMessageAt > 20_000) this.reconnect("feed heartbeat timeout");
    }, 5_000);
  }

  stop() {
    this.stopped = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    if (this.watchdog) clearInterval(this.watchdog);
    this.ws?.close();
    this.ws = null;
  }

  private connect() {
    if (this.stopped) return;
    this.status = "connecting";
    this.scheduleEmit(true);
    const ws = new WebSocket(config.wsUrl, { handshakeTimeout: 12_000 });
    this.ws = ws;

    ws.on("open", () => {
      this.lastMessageAt = Date.now();
      const channels = this.mode === "full" ? ["full", "ticker", "heartbeat"] : ["level2_batch", "ticker", "heartbeat"];
      const subscription: Record<string, unknown> = { type: "subscribe", product_ids: [this.productId], channels };
      const credentials = config.coinbaseCredentials;
      if (this.mode === "full" && credentials.key && credentials.secret && credentials.passphrase) {
        const timestamp = (Date.now() / 1000).toFixed(3);
        const signature = createHmac("sha256", Buffer.from(credentials.secret, "base64"))
          .update(`${timestamp}GET/users/self/verify`).digest("base64");
        Object.assign(subscription, { key: credentials.key, passphrase: credentials.passphrase, timestamp, signature });
      }
      ws.send(JSON.stringify(subscription));
      if (this.mode === "full") void this.rebuildLevel3();
      else {
        this.status = "fallback";
        this.book.reset("level2");
      }
    });

    ws.on("message", (raw) => {
      this.lastMessageAt = Date.now();
      let event: CoinbaseFullEvent;
      try { event = JSON.parse(raw.toString()) as CoinbaseFullEvent; } catch { return; }
      if (event.product_id && event.product_id !== this.productId) return;
      if (event.type === "error") {
        if (this.mode === "full") this.mode = "level2";
        return this.reconnect(`Coinbase subscription error: ${(event as CoinbaseFullEvent & { message?: string }).message ?? "unknown"}`);
      }
      if (event.type === "ticker") {
        const tickerEvent = event as CoinbaseFullEvent & { best_bid?: string; best_ask?: string; last_size?: string };
        this.ticker = {
          price: event.price ? Number(event.price) : this.ticker.price,
          bid: tickerEvent.best_bid ? Number(tickerEvent.best_bid) : this.ticker.bid,
          ask: tickerEvent.best_ask ? Number(tickerEvent.best_ask) : this.ticker.ask
        };
        if (this.mode === "level2" && event.price && tickerEvent.last_size && event.side) {
          const synthetic: CoinbaseFullEvent = {
            type: "match", product_id: this.productId, price: event.price, size: tickerEvent.last_size,
            side: event.side === "buy" ? "sell" : "buy", time: event.time
          };
          this.micro.ingest(synthetic, this.book);
          const trade = this.micro.tradeFrom(synthetic);
          if (trade) this.profile.ingest(trade);
        }
        return this.scheduleEmit();
      }
      if (this.mode === "level2") {
        this.book.apply(event);
        if (this.book.synced) this.status = "fallback";
        return this.scheduleEmit();
      }
      if (!FULL_TYPES.has(event.type)) return;
      if (this.syncing || !this.book.synced) {
        this.queued.push(event);
        return;
      }
      this.applyFull(event);
    });

    ws.on("error", () => this.reconnect("websocket error"));
    ws.on("close", () => this.reconnect("websocket closed"));
  }

  private applyFull(event: CoinbaseFullEvent) {
    this.micro.ingest(event, this.book);
    const result = this.book.apply(event);
    if (result.gap) {
      this.sequenceGaps++;
      this.queued = [event];
      void this.rebuildLevel3();
      return;
    }
    if (result.applied) {
      const trade = this.micro.tradeFrom(event);
      if (trade) {
        this.profile.ingest(trade);
        this.ticker.price = trade.price;
      }
      this.status = "live";
      this.consecutiveFailures = 0;
      this.scheduleEmit();
    }
  }

  private async rebuildLevel3() {
    if (this.syncing || this.mode !== "full" || this.stopped) return;
    this.syncing = true;
    this.status = "syncing";
    this.scheduleEmit(true);
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), config.restTimeoutMs);
      const response = await fetch(`${config.restUrl}/products/${this.productId}/book?level=3`, {
        signal: controller.signal,
        headers: { "User-Agent": "HamaForex-LTA-MBO/0.1", Accept: "application/json" }
      });
      clearTimeout(timeout);
      if (!response.ok) throw new Error(`snapshot ${response.status}`);
      const snapshot = await response.json() as { sequence: number; bids: Array<[string, string, string]>; asks: Array<[string, string, string]> };
      this.book.loadLevel3(snapshot);
      const queued = this.queued.sort((a, b) => (a.sequence ?? 0) - (b.sequence ?? 0));
      this.queued = [];
      for (const event of queued) if ((event.sequence ?? 0) > snapshot.sequence) {
        const result = this.book.apply(event);
        if (result.gap) throw new Error("gap while replaying queued messages");
      }
      this.status = "live";
      this.consecutiveFailures = 0;
    } catch {
      this.consecutiveFailures++;
      if (this.consecutiveFailures >= 3) {
        this.mode = "level2";
        this.reconnect("Level 3 unavailable; switching to Level 2");
      } else {
        setTimeout(() => void this.rebuildLevel3(), Math.min(5_000, 500 * 2 ** this.consecutiveFailures));
      }
    } finally {
      this.syncing = false;
      this.scheduleEmit(true);
    }
  }

  private reconnect(reason: string) {
    if (this.stopped || this.reconnectTimer) return;
    console.warn(`[${this.productId}] ${reason}; reconnecting in ${this.mode} mode`);
    this.status = "reconnecting";
    this.reconnects++;
    this.ws?.removeAllListeners();
    this.ws?.close();
    this.ws = null;
    const delay = Math.min(30_000, 500 * 2 ** Math.min(this.reconnects, 6)) + Math.random() * 500;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
    this.scheduleEmit(true);
  }

  private scheduleEmit(immediate = false) {
    if (immediate) {
      if (this.emitTimer) clearTimeout(this.emitTimer);
      this.emitTimer = null;
      this.emit("state", this.getState());
      return;
    }
    if (this.emitTimer) return;
    this.emitTimer = setTimeout(() => {
      this.emitTimer = null;
      this.emit("state", this.getState());
    }, 250);
  }

  getState(): ProductState {
    const book = this.book.top(24);
    const micro = this.micro.snapshot(this.book);
    const profile = this.profile.calculate();
    const plan = this.plans.get(this.productId);
    const livePrice = this.ticker.price ?? book.asks[0]?.price ?? book.bids[0]?.price ?? null;
    return {
      productId: this.productId,
      status: this.status,
      mode: this.mode,
      lastMessageAt: this.lastMessageAt,
      reconnects: this.reconnects,
      sequenceGaps: this.sequenceGaps,
      ticker: {
        price: livePrice,
        bid: this.ticker.bid ?? book.bids[0]?.price ?? null,
        ask: this.ticker.ask ?? book.asks[0]?.price ?? null
      },
      book,
      micro,
      profile,
      plan,
      setup: rankSetup(livePrice, plan, micro, profile)
    };
  }
}

export async function fetchCandles(productId: string, granularity: number) {
  const url = `${config.restUrl}/products/${productId}/candles?granularity=${granularity}`;
  const response = await fetch(url, { headers: { "User-Agent": "HamaForex-LTA-MBO/0.1" } });
  if (!response.ok) throw new Error(`Coinbase candles request failed: ${response.status}`);
  const rows = await response.json() as Array<[number, number, number, number, number, number]>;
  return rows
    .map(([time, low, high, open, close, volume]) => ({ time, low, high, open, close, volume }))
    .sort((a, b) => a.time - b.time);
}

export async function fetchCandleHistory(productId: string, granularity: number, requestedBars: number) {
  const candles = new Map<number, { time: number; low: number; high: number; open: number; close: number; volume: number }>();
  let end = Math.floor(Date.now() / 1000 / granularity) * granularity;
  const cappedBars = Math.min(requestedBars, 20_000);
  const maxPages = Math.ceil(cappedBars / 290) + 1;
  for (let page = 0; page < maxPages && candles.size < requestedBars; page++) {
    const start = end - granularity * 290;
    const query = new URLSearchParams({ granularity: String(granularity), start: new Date(start * 1000).toISOString(), end: new Date(end * 1000).toISOString() });
    const response = await fetch(`${config.restUrl}/products/${productId}/candles?${query}`, { headers: { "User-Agent": "HamaForex-LTA-MBO/0.1" } });
    if (!response.ok) throw new Error(`Coinbase candle history failed: ${response.status}`);
    const rows = await response.json() as Array<[number, number, number, number, number, number]>;
    for (const [time, low, high, open, close, volume] of rows) candles.set(time, { time, low, high, open, close, volume });
    if (rows.length === 0) break;
    end = start - granularity;
    if (page < maxPages - 1) await new Promise((resolve) => setTimeout(resolve, 180));
  }
  return [...candles.values()].sort((a, b) => a.time - b.time).slice(-cappedBars);
}
