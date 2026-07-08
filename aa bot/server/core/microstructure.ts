import type { CoinbaseFullEvent, MicrostructureSignal, Side, TradePrint } from "../types.js";
import { MboBook } from "./mbo-book.js";

interface WatchedOrder {
  side: Side;
  openedAt: number;
  initialSize: number;
  matchedSize: number;
}

const median = (values: number[]) => {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  return sorted[Math.floor(sorted.length / 2)] ?? 0;
};

export class MicrostructureEngine {
  private trades: TradePrint[] = [];
  private watchedOrders = new Map<string, WatchedOrder>();
  private bidRefreshTimes: number[] = [];
  private askRefreshTimes: number[] = [];
  private lastAggressiveSellAt = 0;
  private lastAggressiveBuyAt = 0;
  private spoofUntil = 0;
  private spoofSide: Side | null = null;

  ingest(event: CoinbaseFullEvent, book: MboBook) {
    const now = event.time ? Date.parse(event.time) : Date.now();
    const viewBefore = book.top(10);
    const beforeBestBid = viewBefore.bids[0]?.price;
    const beforeBestAsk = viewBefore.asks[0]?.price;

    if (event.type === "match" && event.price && event.size && event.side) {
      const aggressor: Side = event.side === "sell" ? "buy" : "sell";
      const trade: TradePrint = {
        time: now,
        price: Number(event.price),
        size: Number(event.size),
        aggressor,
        makerOrderId: event.maker_order_id
      };
      this.trades.push(trade);
      if (aggressor === "sell") this.lastAggressiveSellAt = now;
      else this.lastAggressiveBuyAt = now;
      if (event.maker_order_id) {
        const watched = this.watchedOrders.get(event.maker_order_id);
        if (watched) watched.matchedSize += trade.size;
      }
    }

    if (event.type === "open" && event.order_id && event.side && event.price && event.remaining_size) {
      const size = Number(event.remaining_size);
      const sideLevels = event.side === "buy" ? viewBefore.bids : viewBefore.asks;
      const typical = median(sideLevels.map((level) => level.size));
      if (typical > 0 && size >= typical * 3) {
        this.watchedOrders.set(event.order_id, { side: event.side, openedAt: now, initialSize: size, matchedSize: 0 });
      }
      const price = Number(event.price);
      if (event.side === "buy" && now - this.lastAggressiveSellAt < 2_500 && beforeBestBid && price >= beforeBestBid) {
        this.bidRefreshTimes.push(now);
      }
      if (event.side === "sell" && now - this.lastAggressiveBuyAt < 2_500 && beforeBestAsk && price <= beforeBestAsk) {
        this.askRefreshTimes.push(now);
      }
    }

    if (event.type === "done") {
      const id = event.order_id;
      const watched = id ? this.watchedOrders.get(id) : undefined;
      if (id && watched) {
        const age = now - watched.openedAt;
        const executedRatio = watched.initialSize > 0 ? watched.matchedSize / watched.initialSize : 1;
        if (age < 8_000 && executedRatio < 0.1) {
          this.spoofUntil = now + 15_000;
          this.spoofSide = watched.side;
        }
        this.watchedOrders.delete(id);
      }
    }

    this.prune(now);
  }

  private prune(now: number) {
    this.trades = this.trades.filter((trade) => trade.time >= now - 60_000);
    this.bidRefreshTimes = this.bidRefreshTimes.filter((time) => time >= now - 15_000);
    this.askRefreshTimes = this.askRefreshTimes.filter((time) => time >= now - 15_000);
    for (const [id, order] of this.watchedOrders) if (order.openedAt < now - 60_000) this.watchedOrders.delete(id);
    if (this.spoofUntil < now) this.spoofSide = null;
  }

  tradeFrom(event: CoinbaseFullEvent): TradePrint | null {
    if (event.type !== "match" || !event.price || !event.size || !event.side) return null;
    return {
      time: event.time ? Date.parse(event.time) : Date.now(),
      price: Number(event.price),
      size: Number(event.size),
      aggressor: event.side === "sell" ? "buy" : "sell",
      makerOrderId: event.maker_order_id
    };
  }

  snapshot(book: MboBook, now = Date.now()): MicrostructureSignal {
    this.prune(now);
    const view = book.top(15);
    const bidSize = view.bids.reduce((sum, level) => sum + level.size, 0);
    const askSize = view.asks.reduce((sum, level) => sum + level.size, 0);
    const imbalance = bidSize + askSize > 0 ? (bidSize - askSize) / (bidSize + askSize) : 0;
    const delta = (windowMs: number) => this.trades
      .filter((trade) => trade.time >= now - windowMs)
      .reduce((sum, trade) => sum + (trade.aggressor === "buy" ? trade.size : -trade.size), 0);
    const delta5s = delta(5_000);
    const delta30s = delta(30_000);
    const recent = this.trades.filter((trade) => trade.time >= now - 10_000);
    const high = recent.length ? Math.max(...recent.map((trade) => trade.price)) : 0;
    const low = recent.length ? Math.min(...recent.map((trade) => trade.price)) : 0;
    const mid = ((view.bids[0]?.price ?? 0) + (view.asks[0]?.price ?? 0)) / 2;
    const rangeBps = mid > 0 ? (high - low) / mid * 10_000 : Infinity;

    let absorption: "long" | "short" | "none" = "none";
    if (delta30s < 0 && this.bidRefreshTimes.length >= 2 && rangeBps < 5) absorption = "long";
    if (delta30s > 0 && this.askRefreshTimes.length >= 2 && rangeBps < 5) absorption = "short";

    const bidMedian = median(view.bids.map((level) => level.size));
    const askMedian = median(view.asks.map((level) => level.size));
    const stackedBidLevels = view.bids.slice(0, 8).filter((level) => bidMedian > 0 && level.size > bidMedian * 1.6).length;
    const stackedAskLevels = view.asks.slice(0, 8).filter((level) => askMedian > 0 && level.size > askMedian * 1.6).length;
    const bestBid = view.bids[0]?.price ?? 0;
    const bestAsk = view.asks[0]?.price ?? 0;
    const spreadBps = bestBid > 0 ? (bestAsk - bestBid) / bestBid * 10_000 : 0;
    const spoofWarning = this.spoofUntil >= now;

    let score = imbalance * 35 + Math.max(-25, Math.min(25, delta30s * 2));
    if (absorption === "long") score += 30;
    if (absorption === "short") score -= 30;
    score += (stackedBidLevels - stackedAskLevels) * 4;
    if (spoofWarning) score *= 0.65;
    score = Math.round(Math.max(-100, Math.min(100, score)));

    const reasons: string[] = [];
    if (Math.abs(imbalance) > 0.2) reasons.push(`${imbalance > 0 ? "Bid" : "Ask"} imbalance ${(Math.abs(imbalance) * 100).toFixed(0)}%`);
    if (absorption !== "none") reasons.push(`${absorption === "long" ? "Sell" : "Buy"} aggression is being absorbed`);
    if (stackedBidLevels >= 2) reasons.push("Stacked bid liquidity");
    if (stackedAskLevels >= 2) reasons.push("Stacked ask liquidity");
    if (spoofWarning) reasons.push(`${this.spoofSide ?? "Unknown"} wall pulled without meaningful execution`);

    return {
      timestamp: now,
      score,
      imbalance,
      delta5s,
      delta30s,
      bidRefreshes: this.bidRefreshTimes.length,
      askRefreshes: this.askRefreshTimes.length,
      absorption,
      spoofWarning,
      spoofSide: this.spoofSide,
      stackedBidLevels,
      stackedAskLevels,
      spreadBps,
      reasons
    };
  }
}
