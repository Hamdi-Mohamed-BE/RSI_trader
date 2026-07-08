import type { BookView, CoinbaseFullEvent, MboOrder, PriceLevel, Side } from "../types.js";

interface MutableLevel {
  size: number;
  orders: Set<string>;
}

export class MboBook {
  private orders = new Map<string, MboOrder>();
  private bids = new Map<number, MutableLevel>();
  private asks = new Map<number, MutableLevel>();
  private aggregatedBids = new Map<number, number>();
  private aggregatedAsks = new Map<number, number>();
  sequence = 0;
  synced = false;
  mode: "full" | "level2" = "full";

  reset(mode: "full" | "level2" = "full") {
    this.orders.clear();
    this.bids.clear();
    this.asks.clear();
    this.aggregatedBids.clear();
    this.aggregatedAsks.clear();
    this.sequence = 0;
    this.synced = false;
    this.mode = mode;
  }

  loadLevel3(snapshot: {
    sequence: number;
    bids: Array<[string, string, string]>;
    asks: Array<[string, string, string]>;
  }) {
    this.reset("full");
    for (const [price, size, id] of snapshot.bids) this.add({ id, side: "buy", price: Number(price), size: Number(size) });
    for (const [price, size, id] of snapshot.asks) this.add({ id, side: "sell", price: Number(price), size: Number(size) });
    this.sequence = snapshot.sequence;
    this.synced = true;
  }

  loadLevel2(snapshot: { bids: Array<[string, string]>; asks: Array<[string, string]> }) {
    this.reset("level2");
    for (const [price, size] of snapshot.bids) this.aggregatedBids.set(Number(price), Number(size));
    for (const [price, size] of snapshot.asks) this.aggregatedAsks.set(Number(price), Number(size));
    this.synced = true;
  }

  apply(event: CoinbaseFullEvent): { gap: boolean; applied: boolean } {
    if (this.mode === "level2") return this.applyLevel2(event);
    if (typeof event.sequence !== "number") return { gap: false, applied: false };
    if (event.sequence <= this.sequence) return { gap: false, applied: false };
    if (this.synced && event.sequence !== this.sequence + 1) return { gap: true, applied: false };

    const id = event.order_id ?? event.maker_order_id;
    switch (event.type) {
      case "open":
        if (id && event.side && event.price && event.remaining_size) {
          this.add({ id, side: event.side, price: Number(event.price), size: Number(event.remaining_size) });
        }
        break;
      case "done":
        if (id) this.remove(id);
        break;
      case "match":
        if (id && event.size) this.reduce(id, Number(event.size));
        break;
      case "change":
        if (id && event.new_size) this.resize(id, Number(event.new_size));
        break;
      case "received":
      case "activate":
        break;
      default:
        return { gap: false, applied: false };
    }
    this.sequence = event.sequence;
    return { gap: false, applied: true };
  }

  private applyLevel2(event: CoinbaseFullEvent) {
    if (event.type === "snapshot" && event.bids && event.asks) {
      this.loadLevel2({ bids: event.bids, asks: event.asks });
      return { gap: false, applied: true };
    }
    if (event.type !== "l2update" || !event.changes) return { gap: false, applied: false };
    for (const [side, priceText, sizeText] of event.changes) {
      const price = Number(priceText);
      const size = Number(sizeText);
      const levels = side === "buy" ? this.aggregatedBids : this.aggregatedAsks;
      if (size === 0) levels.delete(price);
      else levels.set(price, size);
    }
    return { gap: false, applied: true };
  }

  private add(order: MboOrder) {
    if (!Number.isFinite(order.price) || !Number.isFinite(order.size) || order.size <= 0) return;
    if (this.orders.has(order.id)) this.remove(order.id);
    this.orders.set(order.id, order);
    const side = order.side === "buy" ? this.bids : this.asks;
    const level = side.get(order.price) ?? { size: 0, orders: new Set<string>() };
    level.size += order.size;
    level.orders.add(order.id);
    side.set(order.price, level);
  }

  private remove(id: string) {
    const order = this.orders.get(id);
    if (!order) return;
    const side = order.side === "buy" ? this.bids : this.asks;
    const level = side.get(order.price);
    if (level) {
      level.size = Math.max(0, level.size - order.size);
      level.orders.delete(id);
      if (level.orders.size === 0 || level.size < 1e-12) side.delete(order.price);
    }
    this.orders.delete(id);
  }

  private reduce(id: string, amount: number) {
    const order = this.orders.get(id);
    if (!order || !Number.isFinite(amount) || amount <= 0) return;
    this.resize(id, Math.max(0, order.size - amount));
  }

  private resize(id: string, newSize: number) {
    const order = this.orders.get(id);
    if (!order) return;
    if (newSize <= 1e-12) return this.remove(id);
    const side = order.side === "buy" ? this.bids : this.asks;
    const level = side.get(order.price);
    if (level) level.size = Math.max(0, level.size + newSize - order.size);
    order.size = newSize;
  }

  top(depth = 20): BookView {
    const fromMbo = (levels: Map<number, MutableLevel>, side: Side): PriceLevel[] =>
      [...levels.entries()]
        .sort(([a], [b]) => side === "buy" ? b - a : a - b)
        .slice(0, depth)
        .map(([price, level]) => ({ price, size: level.size, orders: level.orders.size }));
    const fromL2 = (levels: Map<number, number>, side: Side): PriceLevel[] =>
      [...levels.entries()]
        .sort(([a], [b]) => side === "buy" ? b - a : a - b)
        .slice(0, depth)
        .map(([price, size]) => ({ price, size, orders: 0 }));

    return {
      bids: this.mode === "full" ? fromMbo(this.bids, "buy") : fromL2(this.aggregatedBids, "buy"),
      asks: this.mode === "full" ? fromMbo(this.asks, "sell") : fromL2(this.aggregatedAsks, "sell"),
      sequence: this.sequence,
      mode: this.mode,
      synced: this.synced
    };
  }

  getOrder(id: string) {
    return this.orders.get(id);
  }

  get orderCount() {
    return this.orders.size;
  }
}
